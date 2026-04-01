from fastapi import APIRouter, HTTPException
from agent.models.request import Request, RequestCreate
from agent.db import crud

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("", response_model=Request)
def create(body: RequestCreate):
    return crud.create_request(**body.model_dump(exclude_none=True))


@router.get("", response_model=list[Request])
def list_all(scene_id: str = None, status: str = None):
    return crud.list_requests(scene_id=scene_id, status=status)


@router.get("/pending", response_model=list[Request])
def list_pending():
    return crud.list_pending_requests()


@router.get("/{rid}", response_model=Request)
def get(rid: str):
    r = crud.get_request(rid)
    if not r:
        raise HTTPException(404, "Request not found")
    return r


@router.patch("/{rid}", response_model=Request)
def update(rid: str, status: str = None, media_gen_id: str = None, output_url: str = None, error_message: str = None):
    kwargs = {}
    if status:
        kwargs["status"] = status
    if media_gen_id:
        kwargs["media_gen_id"] = media_gen_id
    if output_url:
        kwargs["output_url"] = output_url
    if error_message:
        kwargs["error_message"] = error_message
    r = crud.update_request(rid, **kwargs)
    if not r:
        raise HTTPException(404, "Request not found")
    return r
