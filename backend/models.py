from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class GenerationStatus(str, Enum):
    IDLE = "idle"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class Character(BaseModel):
    id: str
    name: str
    avatar_url: str
    tags: List[str] = []
    prompt: str = ""

class Scene(BaseModel):
    id: str
    name: str
    image_url: str
    tags: List[str] = []
    prompt: str = ""

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    tags: Optional[List[str]] = None
    prompt: Optional[str] = None

class SceneUpdate(BaseModel):
    name: Optional[str] = None
    image_url: Optional[str] = None
    tags: Optional[List[str]] = None
    prompt: Optional[str] = None

class ShotBase(BaseModel):
    prompt: str = ""
    dialogue: str = ""
    audio_prompt: Optional[str] = None
    use_scene_ref: bool = False
    panel_layout: str = "3-panel" # 1-panel, 2-panel, 3-panel, 4-panel

class ShotCreate(ShotBase):
    characters: List[str] = []
    scene: Optional[str] = None # Scene name from parsing
    scene_id: Optional[str] = None

class ShotUpdate(ShotBase):
    characters: Optional[List[str]] = None
    scene_id: Optional[str] = None

class Shot(ShotBase):
    id: str
    order: int
    characters: List[str] = []
    scene_id: Optional[str] = None
    
    # Generation Results
    image_url: Optional[str] = None
    image_candidates: List[str] = []
    video_url: Optional[str] = None
    status: GenerationStatus = GenerationStatus.IDLE

class Project(BaseModel):
    id: str
    name: str
    style: str = "anime"
    shots: List[Shot] = []
    characters: List[Character] = []
    scenes: List[Scene] = []

# API Request/Response Models
class GenerateRequest(BaseModel):
    project_id: Optional[str] = None
    shot_id: str
    type: str = "image" # image or video
    count: Optional[int] = None

class AssetGenerateRequest(BaseModel):
    prompt: str
    type: str = "character" # character or scene
