from typing import List, Optional

from pydantic import BaseModel


class SkillFileIn(BaseModel):
    path: str
    content: str


class SkillCreate(BaseModel):
    name: str
    content: str
    description: Optional[str] = None
    category: Optional[str] = None
    files: Optional[List[SkillFileIn]] = None


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    files: Optional[List[SkillFileIn]] = None


class SkillFileOut(BaseModel):
    path: str
    size: int
    type: str = "file"


class SkillTreeNode(BaseModel):
    name: str
    path: str
    type: str
    size: Optional[int] = None


class SkillOut(BaseModel):
    scope: str
    package_path: str
    name: str
    description: str
    package_status: str
    error: Optional[str] = None
    content_hash: Optional[str] = None
    mount_path: str
    files: List[SkillFileOut] = []


class SkillFileContentOut(BaseModel):
    scope: str
    package_path: str
    path: str
    content: str
    size: int
