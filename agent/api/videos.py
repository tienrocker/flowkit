from fastapi import APIRouter, HTTPException
from agent.models.video import Video, VideoCreate, VideoUpdate
from agent.db import crud

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("", response_model=Video)
def create(body: VideoCreate):
    return crud.create_video(**body.model_dump(exclude_none=True))


@router.get("", response_model=list[Video])
def list_by_project(project_id: str):
    return crud.list_videos(project_id)


@router.get("/{vid}", response_model=Video)
def get(vid: str):
    v = crud.get_video(vid)
    if not v:
        raise HTTPException(404, "Video not found")
    return v


@router.patch("/{vid}", response_model=Video)
def update(vid: str, body: VideoUpdate):
    v = crud.update_video(vid, **body.model_dump(exclude_none=True))
    if not v:
        raise HTTPException(404, "Video not found")
    return v


@router.delete("/{vid}")
def delete(vid: str):
    if not crud.delete_video(vid):
        raise HTTPException(404, "Video not found")
    return {"ok": True}
