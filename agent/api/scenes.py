from fastapi import APIRouter, HTTPException
from agent.models.scene import Scene, SceneCreate, SceneUpdate
from agent.db import crud
import json

router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.post("", response_model=Scene)
def create(body: SceneCreate):
    return crud.create_scene(**body.model_dump(exclude_none=True))


@router.get("", response_model=list[Scene])
def list_by_video(video_id: str):
    return crud.list_scenes(video_id)


@router.get("/{sid}", response_model=Scene)
def get(sid: str):
    s = crud.get_scene(sid)
    if not s:
        raise HTTPException(404, "Scene not found")
    return s


@router.patch("/{sid}", response_model=Scene)
def update(sid: str, body: SceneUpdate):
    data = body.model_dump(exclude_none=True)
    if "character_names" in data and isinstance(data["character_names"], list):
        data["character_names"] = json.dumps(data["character_names"])
    s = crud.update_scene(sid, **data)
    if not s:
        raise HTTPException(404, "Scene not found")
    return s


@router.delete("/{sid}")
def delete(sid: str):
    if not crud.delete_scene(sid):
        raise HTTPException(404, "Scene not found")
    return {"ok": True}
