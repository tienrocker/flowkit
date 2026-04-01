import logging
from fastapi import APIRouter, HTTPException
from agent.models.project import Project, ProjectCreate, ProjectUpdate
from agent.models.character import Character
from agent.db import crud
from agent.services.flow_client import get_flow_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


def _build_character_profile(char_name: str, char_desc: str | None, story: str, style: str = "3D") -> dict:
    """Build a rich character profile (description + image_prompt) from the story context."""
    base_desc = char_desc or char_name

    description = (
        f"{char_name}: {base_desc}. "
        f"Story context: {story}"
    )

    image_prompt = (
        f"Full body character portrait of {base_desc}, "
        f"{style} animated style, Pixar-quality rendering, "
        f"detailed character design sheet, clean background, "
        f"expressive face, dynamic pose, studio lighting"
    )

    return {"description": description, "image_prompt": image_prompt}


async def _detect_user_tier(client) -> str:
    """Auto-detect user paygate tier from Flow credits API."""
    try:
        result = await client.get_credits()
        data = result.get("data", result)
        tier = data.get("userPaygateTier", "PAYGATE_TIER_ONE")
        logger.info("Auto-detected user tier: %s", tier)
        return tier
    except Exception as e:
        logger.warning("Failed to detect tier, defaulting to TIER_ONE: %s", e)
        return "PAYGATE_TIER_ONE"


@router.post("", response_model=Project)
async def create(body: ProjectCreate):
    # Step 1: Create project on Google Flow to get the real projectId
    client = get_flow_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected — cannot create project on Google Flow")

    # Auto-detect tier if not explicitly set (default was TIER_TWO which may be wrong)
    detected_tier = await _detect_user_tier(client)

    flow_result = await client.create_project(body.name, body.tool_name)
    if flow_result.get("error"):
        raise HTTPException(502, f"Flow API error: {flow_result['error']}")

    # Extract projectId from tRPC response
    try:
        data = flow_result.get("data", {})
        result = data["result"]["data"]["json"]["result"]
        flow_project_id = result["projectId"]
    except (KeyError, TypeError) as e:
        logger.error("Unexpected Flow response: %s", flow_result)
        raise HTTPException(502, f"Failed to parse Flow response: {e}")

    logger.info("Flow project created: %s", flow_project_id)

    # Step 2: Create local project with the Flow-assigned ID and detected tier
    create_data = body.model_dump(exclude_none=True)
    create_data.pop("tool_name", None)
    characters_input = create_data.pop("characters", None)
    create_data["id"] = flow_project_id
    create_data["user_paygate_tier"] = detected_tier
    project = await crud.create_project(**create_data)

    # Step 3: Create characters with profiles built from story context
    if characters_input and body.story:
        for char_input in characters_input:
            profile = _build_character_profile(
                char_input["name"],
                char_input.get("description"),
                body.story,
            )
            char = await crud.create_character(
                name=char_input["name"],
                description=profile["description"],
                image_prompt=profile["image_prompt"],
            )
            await crud.link_character_to_project(flow_project_id, char["id"])
            logger.info("Character '%s' created and linked: %s", char_input["name"], char["id"])

    return project


@router.get("", response_model=list[Project])
async def list_all(status: str = None):
    return await crud.list_projects(status)


@router.get("/{pid}", response_model=Project)
async def get(pid: str):
    p = await crud.get_project(pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.patch("/{pid}", response_model=Project)
async def update(pid: str, body: ProjectUpdate):
    p = await crud.update_project(pid, **body.model_dump(exclude_unset=True))
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.delete("/{pid}")
async def delete(pid: str):
    if not await crud.delete_project(pid):
        raise HTTPException(404, "Project not found")
    return {"ok": True}


@router.post("/{pid}/characters/{cid}")
async def link_character(pid: str, cid: str):
    if not await crud.link_character_to_project(pid, cid):
        raise HTTPException(400, "Failed to link character")
    return {"ok": True}


@router.delete("/{pid}/characters/{cid}")
async def unlink_character(pid: str, cid: str):
    if not await crud.unlink_character_from_project(pid, cid):
        raise HTTPException(404, "Link not found")
    return {"ok": True}


@router.get("/{pid}/characters", response_model=list[Character])
async def get_characters(pid: str):
    return await crud.get_project_characters(pid)
