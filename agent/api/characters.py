from fastapi import APIRouter, HTTPException
from agent.models.character import Character, CharacterCreate, CharacterUpdate
from agent.db import crud

router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("", response_model=Character)
def create(body: CharacterCreate):
    return crud.create_character(**body.model_dump(exclude_none=True))


@router.get("", response_model=list[Character])
def list_all():
    return crud.list_characters()


@router.get("/{cid}", response_model=Character)
def get(cid: str):
    c = crud.get_character(cid)
    if not c:
        raise HTTPException(404, "Character not found")
    return c


@router.patch("/{cid}", response_model=Character)
def update(cid: str, body: CharacterUpdate):
    c = crud.update_character(cid, **body.model_dump(exclude_none=True))
    if not c:
        raise HTTPException(404, "Character not found")
    return c


@router.delete("/{cid}")
def delete(cid: str):
    if not crud.delete_character(cid):
        raise HTTPException(404, "Character not found")
    return {"ok": True}
