from pydantic import BaseModel
from typing import Optional


class SceneCreate(BaseModel):
    video_id: str
    display_order: int = 0
    prompt: str
    character_names: Optional[list[str]] = None
    parent_scene_id: Optional[str] = None
    chain_type: str = "ROOT"


class SceneUpdate(BaseModel):
    prompt: Optional[str] = None
    character_names: Optional[list[str]] = None
    chain_type: Optional[str] = None

    # Vertical
    vertical_image_url: Optional[str] = None
    vertical_video_url: Optional[str] = None
    vertical_upscale_url: Optional[str] = None
    vertical_image_media_gen_id: Optional[str] = None
    vertical_video_media_gen_id: Optional[str] = None
    vertical_upscale_media_gen_id: Optional[str] = None
    vertical_image_status: Optional[str] = None
    vertical_video_status: Optional[str] = None

    # Horizontal
    horizontal_image_url: Optional[str] = None
    horizontal_video_url: Optional[str] = None
    horizontal_upscale_url: Optional[str] = None
    horizontal_image_media_gen_id: Optional[str] = None
    horizontal_video_media_gen_id: Optional[str] = None
    horizontal_upscale_media_gen_id: Optional[str] = None
    horizontal_image_status: Optional[str] = None
    horizontal_video_status: Optional[str] = None

    # Chain source
    vertical_end_scene_media_gen_id: Optional[str] = None
    horizontal_end_scene_media_gen_id: Optional[str] = None

    # Trim
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    duration: Optional[float] = None


class Scene(BaseModel):
    id: str
    video_id: str
    display_order: int = 0
    prompt: Optional[str] = None
    character_names: Optional[str] = None
    parent_scene_id: Optional[str] = None
    chain_type: str = "ROOT"

    vertical_image_url: Optional[str] = None
    vertical_video_url: Optional[str] = None
    vertical_upscale_url: Optional[str] = None
    vertical_image_media_gen_id: Optional[str] = None
    vertical_video_media_gen_id: Optional[str] = None
    vertical_upscale_media_gen_id: Optional[str] = None
    vertical_image_status: str = "PENDING"
    vertical_video_status: str = "PENDING"

    horizontal_image_url: Optional[str] = None
    horizontal_video_url: Optional[str] = None
    horizontal_upscale_url: Optional[str] = None
    horizontal_image_media_gen_id: Optional[str] = None
    horizontal_video_media_gen_id: Optional[str] = None
    horizontal_upscale_media_gen_id: Optional[str] = None
    horizontal_image_status: str = "PENDING"
    horizontal_video_status: str = "PENDING"

    vertical_end_scene_media_gen_id: Optional[str] = None
    horizontal_end_scene_media_gen_id: Optional[str] = None

    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    duration: Optional[float] = None

    created_at: Optional[str] = None
    updated_at: Optional[str] = None
