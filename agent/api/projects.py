from fastapi import APIRouter, HTTPException
from agent.models.project import Project, ProjectCreate, ProjectUpdate
from agent.models.character import Character
from agent.db import crud

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=Project)
def create(body: ProjectCreate):
    return crud.create_project(**body.model_dump(exclude_none=True))


@router.get("", response_model=list[Project])
def list_all(status: str = None):
    return crud.list_projects(status)


@router.get("/{pid}", response_model=Project)
def get(pid: str):
    p = crud.get_project(pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.patch("/{pid}", response_model=Project)
def update(pid: str, body: ProjectUpdate):
    p = crud.update_project(pid, **body.model_dump(exclude_none=True))
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.delete("/{pid}")
def delete(pid: str):
    if not crud.delete_project(pid):
        raise HTTPException(404, "Project not found")
    return {"ok": True}


@router.post("/{pid}/characters/{cid}")
def link_character(pid: str, cid: str):
    if not crud.link_character_to_project(pid, cid):
        raise HTTPException(400, "Failed to link character")
    return {"ok": True}


@router.delete("/{pid}/characters/{cid}")
def unlink_character(pid: str, cid: str):
    if not crud.unlink_character_from_project(pid, cid):
        raise HTTPException(404, "Link not found")
    return {"ok": True}


@router.get("/{pid}/characters", response_model=list[Character])
def get_characters(pid: str):
    return crud.get_project_characters(pid)
