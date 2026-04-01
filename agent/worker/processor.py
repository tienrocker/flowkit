"""Background worker that processes pending requests via the Flow extension."""
import asyncio
import logging
from agent.db import crud
from agent.services.flow_client import get_flow_client
from agent.config import POLL_INTERVAL, MAX_RETRIES

logger = logging.getLogger(__name__)


async def process_pending_requests():
    """Main worker loop: pick up pending requests and dispatch to extension."""
    client = get_flow_client()
    await client.connect()

    while True:
        pending = crud.list_pending_requests()
        for req in pending:
            await _process_one(client, req)
        await asyncio.sleep(POLL_INTERVAL)


async def _process_one(client, req: dict):
    """Process a single request."""
    rid = req["id"]
    req_type = req["type"]
    orientation = req.get("orientation", "VERTICAL")

    logger.info("Processing request %s type=%s", rid[:8], req_type)
    crud.update_request(rid, status="PROCESSING")

    try:
        if req_type == "GENERATE_IMAGES":
            result = await _handle_generate_image(client, req, orientation)
        elif req_type == "GENERATE_VIDEO":
            result = await _handle_generate_video(client, req, orientation)
        elif req_type == "UPSCALE_VIDEO":
            result = await _handle_upscale_video(client, req, orientation)
        elif req_type == "GENERATE_CHARACTER_IMAGE":
            result = await _handle_generate_character_image(client, req)
        else:
            result = {"error": f"Unknown request type: {req_type}"}

        if "error" in result:
            retry = req.get("retry_count", 0) + 1
            if retry < MAX_RETRIES:
                crud.update_request(rid, status="PENDING", retry_count=retry,
                                     error_message=result["error"])
                logger.warning("Request %s failed (retry %d/%d): %s", rid[:8], retry, MAX_RETRIES, result["error"])
            else:
                crud.update_request(rid, status="FAILED", error_message=result["error"])
                logger.error("Request %s FAILED permanently: %s", rid[:8], result["error"])
        else:
            media_gen_id = result.get("mediaGenerationId", "")
            output_url = result.get("imageUrl") or result.get("videoUrl", "")
            crud.update_request(rid, status="COMPLETED", media_gen_id=media_gen_id, output_url=output_url)

            # Update scene with results
            _update_scene_from_result(req, orientation, media_gen_id, output_url)
            logger.info("Request %s COMPLETED: media_gen=%s", rid[:8], media_gen_id[:20] if media_gen_id else "?")

    except Exception as e:
        logger.exception("Request %s exception: %s", rid[:8], e)
        crud.update_request(rid, status="FAILED", error_message=str(e))


async def _handle_generate_image(client, req: dict, orientation: str) -> dict:
    scene = crud.get_scene(req["scene_id"]) if req.get("scene_id") else None
    if not scene:
        return {"error": "Scene not found"}

    # Get characters for this scene
    import json
    char_names = json.loads(scene.get("character_names") or "[]")
    characters = []
    if req.get("project_id"):
        project_chars = crud.get_project_characters(req["project_id"])
        characters = [
            {"name": c["name"], "media_gen_id": c.get("media_gen_id", "")}
            for c in project_chars if c["name"] in char_names
        ]

    return await client.generate_image(
        prompt=scene["prompt"],
        characters=characters,
        orientation=orientation,
    )


async def _handle_generate_video(client, req: dict, orientation: str) -> dict:
    scene = crud.get_scene(req["scene_id"]) if req.get("scene_id") else None
    if not scene:
        return {"error": "Scene not found"}

    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    image_media_gen_id = scene.get(f"{prefix}_image_media_gen_id")
    if not image_media_gen_id:
        return {"error": f"No {prefix} image media_gen_id for scene"}

    end_scene_id = scene.get(f"{prefix}_end_scene_media_gen_id")

    return await client.generate_video(
        media_gen_id=image_media_gen_id,
        prompt=scene["prompt"],
        orientation=orientation,
        end_scene_media_gen_id=end_scene_id,
    )


async def _handle_upscale_video(client, req: dict, orientation: str) -> dict:
    scene = crud.get_scene(req["scene_id"]) if req.get("scene_id") else None
    if not scene:
        return {"error": "Scene not found"}

    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    video_media_gen_id = scene.get(f"{prefix}_video_media_gen_id")
    if not video_media_gen_id:
        return {"error": f"No {prefix} video media_gen_id for scene"}

    return await client.upscale_video(
        media_gen_id=video_media_gen_id,
        orientation=orientation,
    )


async def _handle_generate_character_image(client, req: dict) -> dict:
    char = crud.get_character(req["character_id"]) if req.get("character_id") else None
    if not char:
        return {"error": "Character not found"}

    result = await client.generate_character_image(
        name=char["name"],
        description=char.get("description", ""),
    )

    if "mediaGenerationId" in result:
        crud.update_character(char["id"],
                               media_gen_id=result["mediaGenerationId"],
                               reference_image_url=result.get("imageUrl", ""))
    return result


def _update_scene_from_result(req: dict, orientation: str, media_gen_id: str, output_url: str):
    """Update scene fields based on completed request."""
    scene_id = req.get("scene_id")
    if not scene_id:
        return

    prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
    req_type = req["type"]

    updates = {}
    if req_type == "GENERATE_IMAGES":
        updates[f"{prefix}_image_media_gen_id"] = media_gen_id
        updates[f"{prefix}_image_url"] = output_url
        updates[f"{prefix}_image_status"] = "COMPLETED"
    elif req_type == "GENERATE_VIDEO":
        updates[f"{prefix}_video_media_gen_id"] = media_gen_id
        updates[f"{prefix}_video_url"] = output_url
        updates[f"{prefix}_video_status"] = "COMPLETED"
    elif req_type == "UPSCALE_VIDEO":
        updates[f"{prefix}_upscale_media_gen_id"] = media_gen_id
        updates[f"{prefix}_upscale_url"] = output_url

    if updates:
        crud.update_scene(scene_id, **updates)
