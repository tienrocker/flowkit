"""Scene chaining logic — create continuation scenes from parent video mediaGenerationId."""
import json
import logging
from agent.db import crud

logger = logging.getLogger(__name__)


def create_continuation_scene(video_id: str, parent_scene_id: str, prompt: str,
                                character_names: list[str] = None, display_order: int = None) -> dict:
    """
    Create a CONTINUATION scene that chains from parent scene's video.
    
    The parent scene's video mediaGenerationId will be used as endScene
    when generating video for this continuation scene.
    """
    parent = crud.get_scene(parent_scene_id)
    if not parent:
        raise ValueError(f"Parent scene {parent_scene_id} not found")

    if display_order is None:
        # Insert after parent
        scenes = crud.list_scenes(video_id)
        display_order = parent["display_order"] + 1
        # Shift subsequent scenes
        for s in scenes:
            if s["display_order"] >= display_order and s["id"] != parent_scene_id:
                crud.update_scene(s["id"], display_order=s["display_order"] + 1)

    scene = crud.create_scene(
        video_id=video_id,
        display_order=display_order,
        prompt=prompt,
        character_names=character_names,
        parent_scene_id=parent_scene_id,
        chain_type="CONTINUATION",
    )

    # Set end_scene_media_gen_id from parent's video media gen IDs
    updates = {}
    if parent.get("vertical_video_media_gen_id"):
        updates["vertical_end_scene_media_gen_id"] = parent["vertical_video_media_gen_id"]
    if parent.get("horizontal_video_media_gen_id"):
        updates["horizontal_end_scene_media_gen_id"] = parent["horizontal_video_media_gen_id"]

    if updates:
        scene = crud.update_scene(scene["id"], **updates)

    logger.info("Created continuation scene %s from parent %s", scene["id"], parent_scene_id)
    return scene


def create_insert_scene(video_id: str, after_scene_id: str, prompt: str,
                         character_names: list[str] = None) -> dict:
    """
    Create an INSERT scene between two existing scenes.
    Uses the previous scene's video as endScene for smooth transition.
    """
    return create_continuation_scene(
        video_id=video_id,
        parent_scene_id=after_scene_id,
        prompt=prompt,
        character_names=character_names,
    )
    # The scene is created with chain_type=CONTINUATION, caller can update to INSERT if needed


def get_chain_info(scene_id: str) -> dict:
    """Get chain info for a scene — parent, children, end_scene refs."""
    scene = crud.get_scene(scene_id)
    if not scene:
        return {}

    from agent.db.schema import get_db
    db = get_db()
    children = db.execute(
        "SELECT id, display_order, chain_type FROM scene WHERE parent_scene_id=? ORDER BY display_order",
        (scene_id,),
    ).fetchall()
    db.close()

    return {
        "scene_id": scene_id,
        "chain_type": scene.get("chain_type"),
        "parent_scene_id": scene.get("parent_scene_id"),
        "vertical_end_scene_media_gen_id": scene.get("vertical_end_scene_media_gen_id"),
        "horizontal_end_scene_media_gen_id": scene.get("horizontal_end_scene_media_gen_id"),
        "children": [dict(c) for c in children],
    }
