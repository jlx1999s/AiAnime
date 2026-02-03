from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
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
    description: str = ""
    status: GenerationStatus = GenerationStatus.IDLE

class Scene(BaseModel):
    id: str
    name: str
    image_url: str
    tags: List[str] = []
    prompt: str = ""
    description: str = ""
    status: GenerationStatus = GenerationStatus.IDLE

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
    description: Optional[str] = None

class ShotBase(BaseModel):
    prompt: str = ""
    dialogue: str = ""
    audio_prompt: Optional[str] = None
    use_scene_ref: bool = True
    custom_image_url: Optional[str] = None
    first_frame_url: Optional[str] = None
    last_frame_url: Optional[str] = None
    panel_layout: str = "1-panel" # 1-panel, 2-panel, 3-panel, 4-panel

class ShotCreate(ShotBase):
    characters: List[str] = []
    scene: Optional[str] = None # Scene name from parsing
    scene_id: Optional[str] = None

class ShotUpdate(ShotBase):
    characters: Optional[List[str]] = None
    scene_id: Optional[str] = None

class ImportShotsAutoRequest(BaseModel):
    root: str
    project_name: str = Field(alias="projectName")

    class Config:
        allow_population_by_field_name = True

class VideoItem(BaseModel):
    id: str
    url: Optional[str] = None
    task_id: Optional[str] = None
    progress: Optional[int] = None
    status: Optional[str] = None

class User(BaseModel):
    id: str
    username: str
    password_hash: str
    created_at: float
    is_admin: bool = False
    api_config: Optional[Dict[str, Any]] = None

class UserPublic(BaseModel):
    id: str
    username: str
    is_admin: bool = False

class Shot(ShotBase):
    id: str
    order: int
    characters: List[str] = []
    scene_id: Optional[str] = None
    
    # Generation Results
    image_url: Optional[str] = None
    original_image_url: Optional[str] = None
    image_candidates: List[str] = []
    video_url: Optional[str] = None
    video_progress: Optional[int] = None
    video_items: List[VideoItem] = []
    status: GenerationStatus = GenerationStatus.IDLE

class Project(BaseModel):
    id: str
    name: str
    style: str = "anime"
    owner_id: Optional[str] = None
    shots: List[Shot] = []
    characters: List[Character] = []
    scenes: List[Scene] = []
    
    # Project Settings
    default_scene_id: Optional[str] = None
    default_panel_layout: str = "1-panel"
    default_image_count: int = 1

# API Request/Response Models
class GenerateRequest(BaseModel):
    project_id: Optional[str] = None
    shot_id: str
    type: str = "image" # image or video
    count: Optional[int] = None
    video_aspect_ratio: Optional[str] = "16:9" # 16:9, 9:16
    video_resolution: Optional[str] = "720p" # 720p, 1080p

class AssetGenerateRequest(BaseModel):
    project_id: Optional[str] = None
    prompt: str
    type: str = "character" # character or scene
    asset_id: Optional[str] = None
    name: Optional[str] = None
