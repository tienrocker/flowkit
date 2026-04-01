from pydantic import BaseModel
from typing import Optional


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    language: str = "en"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    language: Optional[str] = None
    status: Optional[str] = None


class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    language: str = "en"
    status: str = "ACTIVE"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
