import asyncio
import uuid
import os
import json
import shutil
import base64
import imghdr
import io
import urllib.request
import re
from urllib.parse import urlparse, unquote
from typing import List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import AsyncOpenAI
from volcengine.visual.VisualService import VisualService
from models import Project, Shot, Character, Scene, ShotCreate, ShotUpdate, GenerateRequest, GenerationStatus, AssetGenerateRequest, CharacterUpdate, SceneUpdate, VideoItem
from providers import generate_image, generate_video
class ProjectCreate(BaseModel):
    name: str
    style: str = "anime"
class ProjectUpdate(BaseModel):
    name: str | None = None
    style: str | None = None
    default_scene_id: str | None = None
    default_panel_layout: str | None = None
    default_image_count: int | None = None

load_dotenv()

app = FastAPI(title="MochiAni Backend", version="1.0.0")

# --- Static Files ---
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- API Config Management ---
API_CONFIG_FILE = os.path.join("data", "api_config.json")

class ApiConfig(BaseModel):
    dashscope_api_key: str = ""
    volc_access_key: str = ""
    volc_secret_key: str = ""
    text_provider: str = "openai"
    image_provider: str = "openai"
    video_provider: str = "openai"
    # OpenAI Compatible
    openai_api_base: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    openai_image_api_base: str = ""
    openai_image_api_key: str = ""
    openai_image_model: str = ""
    openai_video_api_base: str = ""
    openai_video_api_key: str = ""
    openai_video_model: str = ""
    openai_video_endpoint: str = ""
    # Volcengine Models
    volc_image_model: str = "jimeng_t2i_v30"
    volc_video_model: str = "jimeng_i2v_first_v30"
    # VectorEngine (Fal-ai Proxy)
    vectorengine_api_key: str = ""
    vectorengine_image_model: str = "flux-1/dev"
    vectorengine_api_base: str = "https://api.vectorengine.ai"

class ApiPreset(BaseModel):
    name: str
    type: str  # text, image, video
    config: Dict[str, Any]

PRESETS_FILE = os.path.join("data", "api_presets.json")

def load_presets() -> List[ApiPreset]:
    if not os.path.exists(PRESETS_FILE):
        return []
    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [ApiPreset(**item) for item in data.get("presets", [])]
    except Exception as e:
        print(f"Failed to load presets: {e}")
        return []

def save_presets(presets: List[ApiPreset]):
    os.makedirs(os.path.dirname(PRESETS_FILE), exist_ok=True)
    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump({"presets": [p.dict() for p in presets]}, f, ensure_ascii=False, indent=2)

current_api_config = ApiConfig()
current_llm_model = "qwen-plus" # Default to Qwen if using DashScope

def load_api_config():
    global current_api_config
    # 1. Load from Env vars as defaults
    current_api_config.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY", "")
    current_api_config.volc_access_key = os.getenv("VOLC_ACCESSKEY", "")
    current_api_config.volc_secret_key = os.getenv("VOLC_SECRETKEY", "")
    current_api_config.text_provider = os.getenv("TEXT_PROVIDER", "openai")
    current_api_config.image_provider = os.getenv("IMAGE_PROVIDER", "openai")
    current_api_config.video_provider = os.getenv("VIDEO_PROVIDER", "openai")
    current_api_config.openai_api_base = os.getenv("OPENAI_API_BASE", "")
    current_api_config.openai_api_key = os.getenv("OPENAI_API_KEY", "")
    current_api_config.openai_model = os.getenv("OPENAI_MODEL", "")
    current_api_config.openai_image_api_base = os.getenv("OPENAI_IMAGE_API_BASE", "")
    current_api_config.openai_image_api_key = os.getenv("OPENAI_IMAGE_API_KEY", "")
    current_api_config.openai_image_model = os.getenv("OPENAI_IMAGE_MODEL", "")
    current_api_config.openai_video_api_base = os.getenv("OPENAI_VIDEO_API_BASE", "")
    current_api_config.openai_video_api_key = os.getenv("OPENAI_VIDEO_API_KEY", "")
    current_api_config.openai_video_model = os.getenv("OPENAI_VIDEO_MODEL", "")
    current_api_config.openai_video_endpoint = os.getenv("OPENAI_VIDEO_ENDPOINT", "")
    current_api_config.volc_image_model = os.getenv("VOLC_IMAGE_MODEL", "jimeng_t2i_v30")
    current_api_config.volc_video_model = os.getenv("VOLC_VIDEO_MODEL", "jimeng_i2v_first_v30")
    current_api_config.vectorengine_api_key = os.getenv("VECTORENGINE_API_KEY", "")
    current_api_config.vectorengine_image_model = os.getenv("VECTORENGINE_IMAGE_MODEL", "flux-1/dev")
    current_api_config.vectorengine_api_base = os.getenv("VECTORENGINE_API_BASE", "https://api.vectorengine.ai")

    # 2. Override with config file if exists
    if os.path.exists(API_CONFIG_FILE):
        try:
            with open(API_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("dashscope_api_key"):
                    current_api_config.dashscope_api_key = data["dashscope_api_key"]
                if data.get("volc_access_key"):
                    current_api_config.volc_access_key = data["volc_access_key"]
                if data.get("volc_secret_key"):
                    current_api_config.volc_secret_key = data["volc_secret_key"]
                if data.get("text_provider"):
                    current_api_config.text_provider = data["text_provider"]
                if data.get("image_provider"):
                    current_api_config.image_provider = data["image_provider"]
                if data.get("video_provider"):
                    current_api_config.video_provider = data["video_provider"]
                if data.get("openai_api_base"):
                    current_api_config.openai_api_base = data["openai_api_base"]
                if data.get("openai_api_key"):
                    current_api_config.openai_api_key = data["openai_api_key"]
                if data.get("openai_model"):
                    current_api_config.openai_model = data["openai_model"]
                if data.get("openai_image_api_base"):
                    current_api_config.openai_image_api_base = data["openai_image_api_base"]
                if data.get("openai_image_api_key"):
                    current_api_config.openai_image_api_key = data["openai_image_api_key"]
                if data.get("openai_image_model"):
                    current_api_config.openai_image_model = data["openai_image_model"]
                if data.get("openai_video_api_base"):
                    current_api_config.openai_video_api_base = data["openai_video_api_base"]
                if data.get("openai_video_api_key"):
                    current_api_config.openai_video_api_key = data["openai_video_api_key"]
                if data.get("openai_video_model"):
                    current_api_config.openai_video_model = data["openai_video_model"]
                if data.get("openai_video_endpoint"):
                    current_api_config.openai_video_endpoint = data["openai_video_endpoint"]
                if data.get("volc_image_model"):
                    current_api_config.volc_image_model = data["volc_image_model"]
                if data.get("volc_video_model"):
                    current_api_config.volc_video_model = data["volc_video_model"]
                if data.get("vectorengine_api_key"):
                    current_api_config.vectorengine_api_key = data["vectorengine_api_key"]
                if data.get("vectorengine_image_model"):
                    current_api_config.vectorengine_image_model = data["vectorengine_image_model"]
                if data.get("vectorengine_api_base"):
                    current_api_config.vectorengine_api_base = data["vectorengine_api_base"]
        except Exception as e:
            print(f"Failed to load API Config: {e}")

def save_api_config(config: ApiConfig):
    global current_api_config
    current_api_config = config
    os.makedirs(os.path.dirname(API_CONFIG_FILE), exist_ok=True)
    with open(API_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config.dict(), f, ensure_ascii=False, indent=2)
    # Re-init clients
    init_ai_clients()

# --- AI Client Setup ---
client = None
image_client = None
video_client = None
visual_service = None

def init_ai_clients():
    global client, image_client, video_client, visual_service, current_llm_model
    
    # 1. LLM Client (OpenAI or DashScope)
    if current_api_config.text_provider == "openai" and current_api_config.openai_api_key:
        try:
            base_url = current_api_config.openai_api_base if current_api_config.openai_api_base else "https://api.openai.com/v1"
            client = AsyncOpenAI(
                api_key=current_api_config.openai_api_key,
                base_url=base_url,
                timeout=120.0
            )
            current_llm_model = current_api_config.openai_model if current_api_config.openai_model else "gpt-3.5-turbo"
            print(f"OpenAI Compatible client initialized. Model: {current_llm_model}")
        except Exception as e:
             print(f"Failed to init OpenAI client: {e}")
             client = None

    elif current_api_config.text_provider == "dashscope" and current_api_config.dashscope_api_key:
        try:
            client = AsyncOpenAI(
                api_key=current_api_config.dashscope_api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                timeout=120.0
            )
            current_llm_model = "qwen-plus"
            print("DashScope client initialized.")
        except Exception as e:
            print(f"Failed to init DashScope: {e}")
            client = None
    else:
        print("LLM API Key missing (selected provider not configured).")
        client = None

    if current_api_config.image_provider == "openai" and (current_api_config.openai_image_api_key or (current_api_config.openai_api_key and current_api_config.openai_image_model)):
        try:
            image_base = current_api_config.openai_image_api_base or current_api_config.openai_api_base or "https://api.openai.com/v1"
            image_key = current_api_config.openai_image_api_key or current_api_config.openai_api_key
            image_client = AsyncOpenAI(
                api_key=image_key,
                base_url=image_base,
                timeout=180.0
            )
            print("OpenAI Compatible image client initialized.")
        except Exception as e:
            print(f"Failed to init OpenAI image client: {e}")
            image_client = None
    else:
        image_client = None

    if current_api_config.video_provider == "openai" and (current_api_config.openai_video_api_key or (current_api_config.openai_api_key and current_api_config.openai_video_model)):
        try:
            video_base = current_api_config.openai_video_api_base or current_api_config.openai_api_base or "https://api.openai.com/v1"
            video_key = current_api_config.openai_video_api_key or current_api_config.openai_api_key
            video_client = AsyncOpenAI(
                api_key=video_key,
                base_url=video_base,
                timeout=600.0
            )
            print("OpenAI Compatible video client initialized.")
        except Exception as e:
            print(f"Failed to init OpenAI video client: {e}")
            video_client = None
    else:
        video_client = None

    # 2. Volcengine
    if (current_api_config.image_provider == "volcengine" or current_api_config.video_provider == "volcengine") and current_api_config.volc_access_key and current_api_config.volc_secret_key:
        try:
            visual_service = VisualService()
            visual_service.set_ak(current_api_config.volc_access_key)
            visual_service.set_sk(current_api_config.volc_secret_key)
            print("Volcengine service initialized.")
        except Exception as e:
            print(f"Failed to initialize Volcengine: {e}")
            visual_service = None
    else:
        print("Volcengine keys missing (selected provider not configured).")
        visual_service = None

load_api_config()
init_ai_clients()

# CORS Setup (Allow Frontend to access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-Memory Database with Persistence ---
DB: Dict[str, Project] = {}
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "projects.json")

def save_db():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        # Convert Project objects to dicts
        data = {pid: project.model_dump() for pid, project in DB.items()}
        
        # Atomic write: write to temp file then rename
        temp_file = f"{DATA_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Replace original file atomically (or near-atomically on Windows)
        if os.path.exists(DATA_FILE):
            os.replace(temp_file, DATA_FILE)
        else:
            os.rename(temp_file, DATA_FILE)
            
    except Exception as e:
        print(f"Error saving DB: {e}")

def _sanitize_url(url: str | None) -> str | None:
    if not url:
        return url
    cleaned = url.strip().strip("`\"'")
    return cleaned.strip()

def _save_base64_video(b64_data: str, sub_dir: str = None) -> str:
    video_data = base64.b64decode(b64_data)
    filename = f"{uuid.uuid4()}.mp4"
    if sub_dir:
        dir_path = os.path.join("static", "uploads", sub_dir)
        os.makedirs(dir_path, exist_ok=True)
        filepath = os.path.join(dir_path, filename)
        url_path = f"/static/uploads/{sub_dir}/{filename}"
    else:
        filepath = f"static/uploads/{filename}"
        url_path = f"/static/uploads/{filename}"
    with open(filepath, "wb") as f:
        f.write(video_data)
    return url_path

def _save_video_bytes(video_data: bytes, sub_dir: str = None) -> str:
    filename = f"{uuid.uuid4()}.mp4"
    if sub_dir:
        dir_path = os.path.join("static", "uploads", sub_dir)
        os.makedirs(dir_path, exist_ok=True)
        filepath = os.path.join(dir_path, filename)
        url_path = f"/static/uploads/{sub_dir}/{filename}"
    else:
        filepath = f"static/uploads/{filename}"
        url_path = f"/static/uploads/{filename}"
    with open(filepath, "wb") as f:
        f.write(video_data)
    return url_path

def _normalize_video_url(video_url: str | None, sub_dir: str = None) -> str | None:
    if not video_url:
        return video_url
    if video_url.startswith("http://localhost") or video_url.startswith("https://localhost") or video_url.startswith("http://127.0.0.1") or video_url.startswith("https://127.0.0.1"):
        return video_url
    if not (video_url.startswith("http://") or video_url.startswith("https://")):
        return video_url
    try:
        req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=240) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if not content_type.startswith("video/") and content_type != "application/octet-stream":
                return video_url
            video_bytes = resp.read()
        if video_bytes:
            return _save_video_bytes(video_bytes, sub_dir=sub_dir)
    except Exception as e:
        print(f"Normalize video url failed: {e}")
    return video_url

def _normalize_project_videos(project: Project) -> dict:
    updated = 0
    total = 0
    for shot in project.shots or []:
        if shot.video_url:
            total += 1
            normalized = _normalize_video_url(_sanitize_url(shot.video_url), sub_dir=project.id)
            if normalized and normalized != shot.video_url:
                shot.video_url = normalized
                updated += 1
        if isinstance(shot.video_items, list):
            for item in shot.video_items:
                if item.url:
                    total += 1
                    normalized_item = _normalize_video_url(_sanitize_url(item.url), sub_dir=project.id)
                    if normalized_item and normalized_item != item.url:
                        item.url = normalized_item
                        updated += 1
    return {"updated": updated, "total": total}

def _video_url_to_local_path(url: str | None) -> str | None:
    if not url:
        return None
    url = _sanitize_url(url)
    if url.startswith("http://localhost:8001/static/uploads/") or url.startswith("http://127.0.0.1:8001/static/uploads/") or url.startswith("/static/uploads/"):
        if "/static/uploads/" in url:
            rel = url.split("/static/uploads/")[-1].lstrip("/")
            candidate = os.path.join("static", "uploads", rel)
            return candidate if os.path.exists(candidate) else None
        filename = url.split("/")[-1]
        candidate = os.path.join("static", "uploads", filename)
        return candidate if os.path.exists(candidate) else None
    return None

def _export_project_video(project: Project) -> tuple[str, str]:
    os.makedirs("static/uploads", exist_ok=True)
    shots = sorted(project.shots or [], key=lambda s: (s.order if isinstance(s.order, int) else 0))
    segments = []
    for s in shots:
        # prefer active video_url, else first video item with url
        video_url = _sanitize_url(s.video_url) if s.video_url else None
        if not video_url and isinstance(s.video_items, list):
            first = next((v.url for v in s.video_items if getattr(v, "url", None)), None)
            video_url = _sanitize_url(first) if first else None
        if not video_url:
            continue
        # normalize remote to local file
        normalized = _normalize_video_url(video_url, sub_dir=project.id) or video_url
        local_path = _video_url_to_local_path(normalized)
        if local_path and os.path.exists(local_path):
            segments.append({"shot_id": s.id, "path": os.path.abspath(local_path)})
    if not segments:
        raise Exception("No videos available to export")
    
    # Zip export only (per user request)
    import zipfile
    zip_path = os.path.abspath(os.path.join("static", "uploads", f"{uuid.uuid4()}.zip"))
    
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # add videos with ordered names
        for idx, seg in enumerate(segments):
            # ext = os.path.splitext(seg["path"])[1]
            # Use .mp4 as default extension if missing, though typically it is mp4
            arcname = f"{idx+1:02d}_{seg['shot_id']}.mp4"
            z.write(seg["path"], arcname=arcname)
            
    url = f"http://localhost:8001/static/uploads/{os.path.basename(zip_path)}"
    return url, "zip"

def load_db():
    global DB
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            if not content:
                print("Warning: DB file is empty")
                return
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                print("Warning: DB file contains invalid JSON")
                return
                
            DB.clear()
            for pid, project_data in data.items():
                DB[pid] = Project(**project_data)
                project = DB[pid]
                for shot in project.shots or []:
                    shot.image_url = _sanitize_url(shot.image_url)
                    if isinstance(shot.image_candidates, list):
                        shot.image_candidates = [u for u in (_sanitize_url(x) for x in shot.image_candidates) if u]
                    shot.video_url = _sanitize_url(shot.video_url)
                    if isinstance(shot.video_items, list):
                        for item in shot.video_items:
                            item.url = _sanitize_url(item.url)
                    if (not shot.video_items) and shot.video_url:
                        shot.video_items = [VideoItem(id="legacy", url=shot.video_url, progress=shot.video_progress, status=str(shot.status))]
        print(f"Loaded {len(DB)} projects from {DATA_FILE}")
    except Exception as e:
        print(f"Failed to load DB: {e}")

# Seed Data
def seed_data():
    # Only seed if DB is empty AND file doesn't exist (to avoid overwriting corrupted file)
    if DB: 
        return
    
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
         # File exists and is not empty, but DB is empty. 
         # This implies load failed or file is invalid JSON.
         # Do NOT overwrite to prevent data loss.
         print("DB is empty but data file exists. Skipping seed to preserve data.")
         return

    project_id = "default_project"
    
    # Create default project directory
    project_dir = os.path.join("static", "uploads", project_id)
    os.makedirs(project_dir, exist_ok=True)
    
    chars = [
        Character(id="c1", name="陈远 (外门弟子)", avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=Chen"),
        Character(id="c2", name="神秘师兄", avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=Brother"),
        Character(id="c3", name="陈远 (剑主)", avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=ChenMaster"),
    ]
    shots = [
        Shot(
            id=str(uuid.uuid4()), order=0,
            prompt="0.1-3秒: 低角度，快速推拉镜头。陆远受到重力冲击向后滑行...",
            dialogue="陆远：滚去黑暗剑冢里自生自灭吧！",
            characters=["c1"],
            image_url="https://placehold.co/300x169/25262b/FFF?text=Shot+1"
        ),
        Shot(
            id=str(uuid.uuid4()), order=1,
            prompt="镜头仰拍刻家入口，巨石上“刻家”二字布满剑痕...",
            dialogue="(深吸一口气)",
            characters=["c1"],
            image_url="https://placehold.co/300x169/25262b/FFF?text=Shot+2"
        )
    ]
    DB[project_id] = Project(id=project_id, name="守墓五年", shots=shots, characters=chars)
    save_db()

load_db()
seed_data()

# --- Helpers ---
def get_project_or_404(project_id: str) -> Project:
    if project_id not in DB:
        raise HTTPException(status_code=404, detail="Project not found")
    return DB[project_id]

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": "MochiAni API is running"}

@app.get("/api/config", response_model=ApiConfig)
async def get_api_config():
    return current_api_config

@app.post("/api/config", response_model=ApiConfig)
async def update_api_config(config: ApiConfig):
    save_api_config(config)
    return current_api_config

@app.get("/api/presets", response_model=List[ApiPreset])
async def get_api_presets():
    return load_presets()

@app.post("/api/presets", response_model=ApiPreset)
async def save_api_preset(preset: ApiPreset):
    presets = load_presets()
    # Check if exists (same name AND same type), update or append
    existing = next((p for p in presets if p.name == preset.name and p.type == preset.type), None)
    if existing:
        existing.config = preset.config
    else:
        presets.append(preset)
    save_presets(presets)
    return preset

@app.delete("/api/presets/{type}/{name}")
async def delete_api_preset(type: str, name: str):
    presets = load_presets()
    new_presets = [p for p in presets if not (p.name == name and p.type == type)]
    if len(new_presets) == len(presets):
        raise HTTPException(status_code=404, detail="Preset not found")
    save_presets(new_presets)
    return {"status": "success"}

@app.get("/projects", response_model=List[Project])
async def list_projects():
    return list(DB.values())

@app.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    return get_project_or_404(project_id)

@app.post("/projects/{project_id}/normalize-videos")
async def normalize_project_videos(project_id: str):
    project = get_project_or_404(project_id)
    result = _normalize_project_videos(project)
    if result["updated"] > 0:
        save_db()
    return result

@app.post("/projects/{project_id}/export-video")
async def export_project_video(project_id: str):
    project = get_project_or_404(project_id)
    try:
        # Ensure videos normalized locally
        norm = _normalize_project_videos(project)
        if norm.get("updated"):
            save_db()
        url, kind = _export_project_video(project)
        return {"url": url, "type": kind}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/projects", response_model=Project)
async def create_project(data: ProjectCreate):
    project_id = str(uuid.uuid4())
    if project_id in DB:
        raise HTTPException(status_code=400, detail="Project ID conflict")
    
    # Create project specific directory
    project_dir = os.path.join("static", "uploads", project_id)
    os.makedirs(project_dir, exist_ok=True)
    
    DB[project_id] = Project(id=project_id, name=data.name, style=data.style, shots=[], characters=[], scenes=[])
    save_db()
    return DB[project_id]

@app.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, data: ProjectUpdate):
    project = get_project_or_404(project_id)
    if data.name is not None:
        project.name = data.name
    if data.style is not None:
        project.style = data.style
    if data.default_scene_id is not None:
        project.default_scene_id = data.default_scene_id
    if data.default_panel_layout is not None:
        project.default_panel_layout = data.default_panel_layout
    if data.default_image_count is not None:
        project.default_image_count = data.default_image_count
    save_db()
    return project

@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    if project_id not in DB:
        raise HTTPException(status_code=404, detail="Project not found")
    del DB[project_id]
    save_db()
    return {"ok": True}

@app.post("/projects/{project_id}/shots", response_model=Shot)
async def create_shot(project_id: str, shot_data: ShotCreate):
    project = get_project_or_404(project_id)
    # Filter out fields that are not in Shot model (like 'scene' name string)
    shot_dict = shot_data.dict()
    if 'scene' in shot_dict:
        del shot_dict['scene']
        
    new_shot = Shot(
        id=str(uuid.uuid4()),
        order=len(project.shots),
        **shot_dict
    )
    # Default placeholder
    if not new_shot.image_url:
        new_shot.image_url = f"https://placehold.co/300x169/25262b/FFF?text=New+Shot"
    project.shots.append(new_shot)
    save_db()
    return new_shot

class ReorderShotsRequest(BaseModel):
    shot_ids: List[str]

@app.put("/projects/{project_id}/shots/reorder", response_model=List[Shot])
async def reorder_shots(project_id: str, request: ReorderShotsRequest):
    project = get_project_or_404(project_id)
    
    # Validate all shot IDs exist
    current_ids = {s.id for s in project.shots}
    if len(request.shot_ids) != len(current_ids) or set(request.shot_ids) != current_ids:
        raise HTTPException(status_code=400, detail="Shot IDs mismatch or incomplete")
    
    # Reorder
    shot_map = {s.id: s for s in project.shots}
    project.shots = [shot_map[sid] for sid in request.shot_ids]
    
    # Update order field
    for i, shot in enumerate(project.shots):
        shot.order = i
        
    save_db()
    return project.shots

@app.put("/shots/{project_id}/{shot_id}", response_model=Shot)
async def update_shot(project_id: str, shot_id: str, update_data: ShotUpdate):
    project = get_project_or_404(project_id)
    for shot in project.shots:
        if shot.id == shot_id:
            # Update fields
            updated_data = update_data.dict(exclude_unset=True)
            for k, v in updated_data.items():
                setattr(shot, k, v)
            if "image_url" in updated_data:
                shot.image_url = _sanitize_url(shot.image_url)
            if "image_candidates" in updated_data and isinstance(shot.image_candidates, list):
                shot.image_candidates = [u for u in (_sanitize_url(x) for x in shot.image_candidates) if u]
            if "video_url" in updated_data:
                shot.video_url = _sanitize_url(shot.video_url)
            if "custom_image_url" in updated_data:
                shot.custom_image_url = _sanitize_url(shot.custom_image_url)
            save_db()
            return shot
    raise HTTPException(status_code=404, detail="Shot not found")

@app.delete("/shots/{project_id}/{shot_id}")
async def delete_shot(project_id: str, shot_id: str):
    project = get_project_or_404(project_id)
    project.shots = [s for s in project.shots if s.id != shot_id]
    save_db()
    return {"status": "success"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), project_id: str | None = None):
    # Check if file is already uploaded by checking hash or filename
    # But for simplicity, we just save it.
    # However, user mentioned "use previous image hosting url if uploaded locally without url"
    # The current logic ALREADY returns a local URL: /static/uploads/...
    # If the user means "upload to external hosting" that's different.
    # Assuming the user means: Ensure local uploads have valid URLs that can be used by the model.
    # Our local URLs /static/uploads/... are handled by _image_url_to_base64 correctly now.
    
    filename = f"{uuid.uuid4()}_{file.filename}"
    if project_id:
        dir_path = os.path.join("static", "uploads", project_id)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, filename)
        url = f"/static/uploads/{project_id}/{filename}"
    else:
        os.makedirs("static/uploads", exist_ok=True)
        file_path = f"static/uploads/{filename}"
        url = f"/static/uploads/{filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": url}

@app.post("/projects/{project_id}/characters", response_model=Character)
async def create_character(project_id: str, character: Character):
    project = get_project_or_404(project_id)
    # Check if exists (by ID)
    if any(c.id == character.id for c in project.characters):
        raise HTTPException(status_code=400, detail="Character ID already exists")
    if getattr(character, "avatar_url", None):
        character.avatar_url = _sanitize_url(character.avatar_url)
        if isinstance(character.avatar_url, str) and character.avatar_url and character.avatar_url.startswith("http"):
            character.avatar_url = _save_image_from_url(character.avatar_url, sub_dir=project_id)
    project.characters.append(character)
    save_db()
    return character

@app.post("/projects/{project_id}/characters/import_from_md")
async def import_characters_from_md(project_id: str, file: UploadFile = File(...)):
    project = get_project_or_404(project_id)
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except:
        text = content.decode("gbk", errors="ignore")
    
    lines = text.split("\n")
    new_characters = []
    
    header_found = False
    name_idx = -1
    desc_idx = -1
    prompt_idx = -1
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        parts = [p.strip() for p in line.split("|")]
        # Remove empty first/last elements if they are just from the boundary pipes
        if len(parts) > 0 and parts[0] == "":
            parts.pop(0)
        if len(parts) > 0 and parts[-1] == "":
            parts.pop()
            
        if not parts:
            continue

        # Check for header
        if not header_found:
            for i, p in enumerate(parts):
                if "角色名" in p:
                    name_idx = i
                    header_found = True
                elif "描述" in p:
                    desc_idx = i
                elif "提示词" in p:
                    prompt_idx = i
            continue
            
        # Check for separator
        if all(c in "- :" for c in "".join(parts)):
            continue
            
        # Data row
        if name_idx != -1 and len(parts) > name_idx:
            name = parts[name_idx]
            if "角色名" in name: continue
            
            desc = parts[desc_idx] if desc_idx != -1 and len(parts) > desc_idx else ""
            prompt = parts[prompt_idx] if prompt_idx != -1 and len(parts) > prompt_idx else ""
            
            if name:
                char_id = str(uuid.uuid4())
                avatar_url = f"https://api.dicebear.com/7.x/adventurer/svg?seed={name}"
                
                new_char = Character(
                    id=char_id,
                    name=name,
                    avatar_url=avatar_url,
                    prompt=prompt,
                    description=desc
                )
                new_characters.append(new_char)

    if new_characters:
        project.characters.extend(new_characters)
        save_db()
        
    return {"added": len(new_characters), "characters": new_characters}


@app.post("/projects/{project_id}/scenes", response_model=Scene)
async def create_scene(project_id: str, scene: Scene):
    project = get_project_or_404(project_id)
    # Check if exists (by ID)
    if any(s.id == scene.id for s in project.scenes):
        raise HTTPException(status_code=400, detail="Scene ID already exists")
    if getattr(scene, "image_url", None):
        scene.image_url = _sanitize_url(scene.image_url)
        if isinstance(scene.image_url, str) and scene.image_url and scene.image_url.startswith("http"):
            scene.image_url = _save_image_from_url(scene.image_url, sub_dir=project_id)
    project.scenes.append(scene)
    save_db()
    return scene

@app.post("/projects/{project_id}/scenes/import_from_md")
async def import_scenes_from_md(project_id: str, file: UploadFile = File(...)):
    project = get_project_or_404(project_id)
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except:
        text = content.decode("gbk", errors="ignore")
    
    lines = text.split("\n")
    new_scenes = []
    
    header_found = False
    name_idx = -1
    desc_idx = -1
    prompt_idx = -1
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) > 0 and parts[0] == "":
            parts.pop(0)
        if len(parts) > 0 and parts[-1] == "":
            parts.pop()
        if not parts:
            continue
        
        if not header_found:
            for i, p in enumerate(parts):
                if "场景名" in p:
                    name_idx = i
                    header_found = True
                elif "描述" in p:
                    desc_idx = i
                elif "提示词" in p or "生图提示词" in p:
                    prompt_idx = i
            continue
        
        if all(c in "- :" for c in "".join(parts)):
            continue
        
        if name_idx != -1 and len(parts) > name_idx:
            name = parts[name_idx]
            if "场景名" in name:
                continue
            desc = parts[desc_idx] if desc_idx != -1 and len(parts) > desc_idx else ""
            prompt = parts[prompt_idx] if prompt_idx != -1 and len(parts) > prompt_idx else ""
            if name:
                scene_id = str(uuid.uuid4())
                new_scene = Scene(
                    id=scene_id,
                    name=name,
                    image_url="",
                    prompt=prompt,
                    description=desc,
                    tags=[]
                )
                new_scenes.append(new_scene)
    
    if new_scenes:
        project.scenes.extend(new_scenes)
        save_db()
    
    return {"added": len(new_scenes), "scenes": new_scenes}

@app.post("/projects/{project_id}/shots/import_from_md")
async def import_shots_from_md(project_id: str, file: UploadFile = File(...)):
    project = get_project_or_404(project_id)
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except:
        text = content.decode("gbk", errors="ignore")
    
    lines = text.split("\n")
    rows = []
    
    header_found = False
    idx_no = -1
    idx_chars = -1
    idx_scene = -1
    idx_prompt = -1
    idx_video = -1
    
    print("DEBUG: Starting MD Import parsing")

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        parts = [p.strip() for p in line.split("|")]
        # Remove empty first/last elements if they are just from the boundary pipes
        if len(parts) > 0 and parts[0] == "":
            parts.pop(0)
        if len(parts) > 0 and parts[-1] == "":
            parts.pop()
            
        if not parts:
            continue

        # Check for header
        if not header_found:
            # Clean parts for checking (remove spaces inside words too?)
            clean_parts = [p.replace(" ", "").replace("\t", "") for p in parts]
            print(f"DEBUG: Checking header candidate: {clean_parts}")
            
            temp_idx_no = -1
            temp_idx_chars = -1
            temp_idx_scene = -1
            temp_idx_prompt = -1
            temp_idx_video = -1

            for i, p in enumerate(clean_parts):
                if "编号" in p or "序号" in p: temp_idx_no = i
                elif "出场人物" in p or "角色" in p: temp_idx_chars = i
                elif "场景" in p: temp_idx_scene = i
                elif "视频提示词" in p: temp_idx_video = i
                elif "分镜提示词" in p: temp_idx_prompt = i
                # Fallback for "提示词" only if not matched specific ones
                elif "提示词" in p and temp_idx_prompt == -1 and temp_idx_video == -1: temp_idx_prompt = i

            # If we found at least a few key columns, assume it's the header
            if temp_idx_chars != -1 or temp_idx_prompt != -1 or temp_idx_video != -1:
                idx_no = temp_idx_no
                idx_chars = temp_idx_chars
                idx_scene = temp_idx_scene
                idx_prompt = temp_idx_prompt
                idx_video = temp_idx_video
                header_found = True
                print(f"DEBUG: Header Found! Indices: no={idx_no}, chars={idx_chars}, scene={idx_scene}, prompt={idx_prompt}, video={idx_video}")
            continue
            
        # Check for separator
        joined = "".join(parts)
        if all(c in "- :|" for c in joined):
            continue
            
        # Data row
        number = None
        if idx_no != -1 and len(parts) > idx_no:
            try:
                number = int(parts[idx_no])
            except:
                pass 
        
        char_names = []
        if idx_chars != -1 and len(parts) > idx_chars:
            raw = parts[idx_chars]
            for sep in ["、", ",", "，", "/", "|"]:
                raw = raw.replace(sep, " ")
            char_names = [x.strip() for x in raw.split() if x.strip()]
            
        scene_name = parts[idx_scene].strip() if idx_scene != -1 and len(parts) > idx_scene else ""
        prompt = parts[idx_prompt].strip() if idx_prompt != -1 and len(parts) > idx_prompt else ""
        video_prompt = parts[idx_video].strip() if idx_video != -1 and len(parts) > idx_video else ""
        
        if char_names or scene_name or prompt or video_prompt:
            rows.append({
                "number": number,
                "char_names": char_names,
                "scene_name": scene_name,
                "prompt": prompt,
                "video_prompt": video_prompt,
            })

    print(f"DEBUG: Parsed {len(rows)} rows")
    rows.sort(key=lambda r: (r["number"] if isinstance(r["number"], int) else 1_000_000))
    
    def normalize(s):
        if not s: return ""
        s = s.strip().lower()
        # Remove common punctuation and whitespace
        for char in [" ", "\t", "，", ",", "。", ".", "：", ":", "“", "”", "'", '"', "（", "）", "(", ")", "-", "_"]:
            s = s.replace(char, "")
        return s

    # Resolve IDs
    name_to_char = {c.name.strip(): c.id for c in (project.characters or [])}
    norm_to_char = {normalize(c.name): c.id for c in (project.characters or [])}
    id_to_char_obj = {c.id: c for c in (project.characters or [])}

    name_to_scene = {s.name.strip(): s.id for s in (project.scenes or [])}
    norm_to_scene = {normalize(s.name): s.id for s in (project.scenes or [])}
    id_to_scene_obj = {s.id: s for s in (project.scenes or [])}
    
    new_shots = []
    for r in rows:
        char_ids = []
        for n in r["char_names"]:
            n_clean = n.strip()
            # 1. Exact match
            if n_clean in name_to_char:
                char_ids.append(name_to_char[n_clean])
            # 2. Normalized match
            elif normalize(n_clean) in norm_to_char:
                char_ids.append(norm_to_char[normalize(n_clean)])
            else:
                # 3. Try to find if one contains the other (fallback)
                found = False
                n_norm = normalize(n_clean)
                for c_name, c_id in name_to_char.items():
                    c_norm = normalize(c_name)
                    if n_norm and (n_norm in c_norm or c_norm in n_norm):
                        char_ids.append(c_id)
                        found = True
                        break
                if not found:
                    print(f"DEBUG: Character '{n}' not found")

        scene_id = None
        if r["scene_name"]:
            s_name = r["scene_name"].strip()
            # 1. Exact match
            if s_name in name_to_scene:
                scene_id = name_to_scene[s_name]
            # 2. Normalized match
            elif normalize(s_name) in norm_to_scene:
                scene_id = norm_to_scene[normalize(s_name)]
            else:
                # 3. Try partial match
                found = False
                s_norm = normalize(s_name)
                for sc_name, sc_id in name_to_scene.items():
                    sc_norm = normalize(sc_name)
                    if s_norm and (s_norm in sc_norm or sc_norm in s_norm):
                        scene_id = sc_id
                        found = True
                        break
                if not found:
                    print(f"DEBUG: Scene '{s_name}' not found")

        # Auto-append asset prompts
        final_prompt = r["prompt"]
        for cid in char_ids:
            c = id_to_char_obj.get(cid)
            if c and c.prompt:
                final_prompt += f" [{c.name}: {c.prompt}]"
        
        if scene_id:
            s = id_to_scene_obj.get(scene_id)
            if s and s.prompt:
                final_prompt += f" [{s.name}: {s.prompt}]"

        shot_dict = {
            "prompt": final_prompt,
            "dialogue": "",
            "audio_prompt": r["video_prompt"] if r["video_prompt"] else None,
            "use_scene_ref": True,
            "custom_image_url": None,
            "panel_layout": project.default_panel_layout or "3-panel",
            "characters": char_ids,
            "scene_id": scene_id,
        }
        
        new_shot = Shot(
            id=str(uuid.uuid4()),
            order=len(project.shots),
            **shot_dict
        )
        if not new_shot.image_url:
            new_shot.image_url = f"https://placehold.co/300x169/25262b/FFF?text=New+Shot"
            
        project.shots.append(new_shot)
        new_shots.append(new_shot)
        
    save_db()
    return {"added": len(new_shots), "shots": new_shots}
@app.put("/characters/{project_id}/{char_id}", response_model=Character)
async def update_character(project_id: str, char_id: str, updates: CharacterUpdate):
    project = get_project_or_404(project_id)
    for char in project.characters:
        if char.id == char_id:
            updated_data = updates.dict(exclude_unset=True)
            for k, v in updated_data.items():
                setattr(char, k, v)
            if "avatar_url" in updated_data and getattr(char, "avatar_url", None):
                char.avatar_url = _sanitize_url(char.avatar_url)
                if isinstance(char.avatar_url, str) and char.avatar_url and char.avatar_url.startswith("http"):
                    char.avatar_url = _save_image_from_url(char.avatar_url, sub_dir=project_id)
            save_db()
            return char
    raise HTTPException(status_code=404, detail="Character not found")

@app.delete("/characters/{project_id}/{char_id}")
async def delete_character(project_id: str, char_id: str):
    project = get_project_or_404(project_id)
    before_len = len(project.characters)
    project.characters = [c for c in project.characters if c.id != char_id]
    for shot in project.shots:
        if isinstance(shot.characters, list):
            shot.characters = [cid for cid in shot.characters if cid != char_id]
    if len(project.characters) == before_len:
        raise HTTPException(status_code=404, detail="Character not found")
    save_db()
    return {"ok": True}

@app.put("/scenes/{project_id}/{scene_id}", response_model=Scene)
async def update_scene(project_id: str, scene_id: str, updates: SceneUpdate):
    project = get_project_or_404(project_id)
    for scene in project.scenes:
        if scene.id == scene_id:
            updated_data = updates.dict(exclude_unset=True)
            for k, v in updated_data.items():
                setattr(scene, k, v)
            if "image_url" in updated_data and getattr(scene, "image_url", None):
                scene.image_url = _sanitize_url(scene.image_url)
                if isinstance(scene.image_url, str) and scene.image_url and scene.image_url.startswith("http"):
                    scene.image_url = _save_image_from_url(scene.image_url, sub_dir=project_id)
            save_db()
            return scene
    raise HTTPException(status_code=404, detail="Scene not found")

class ScriptRequest(BaseModel):
    content: str

class ParsedCharacter(BaseModel):
    name: str
    prompt: str

class ParsedScene(BaseModel):
    name: str
    prompt: str

class ScriptParseResponse(BaseModel):
    shots: List[ShotCreate]
    characters: List[ParsedCharacter] = []
    scenes: List[ParsedScene] = []

@app.post("/api/parse-script", response_model=ScriptParseResponse)
async def parse_script(request: ScriptRequest):
    """
    Parse script using Aliyun Bailian (Qwen) if API key is present.
    Fallback to simple splitting if not.
    """
    if client:
        try:
            system_prompt = """
            你是一位专业的动画分镜导演。请将用户提供的剧本解析为一系列分镜镜头，并提取出所有出现的角色和场景及其详细视觉描述。
            
            输出必须是一个JSON对象，包含三个字段：
            1. "shots": 镜头列表，每个镜头包含：
               - prompt: 详细的画面描述，包含镜头角度、光影、人物动作、场景细节。适合用于AI生图。
               - dialogue: 该镜头的台词（如果有）。
               - characters: 该镜头中出现的角色名字列表（例如：["陈远", "神秘师兄"]）。如果无角色则为空列表。
               - scene: 该镜头发生的场景名称（例如："外门练武场", "刻家入口"）。
            
            2. "characters": 角色列表，包含剧本中出现的所有角色。每个角色包含：
               - name: 角色名字。
               - prompt: 角色的详细外貌描述（发型、发色、眼睛、衣着、配饰、气质等），用于AI生图。
            
            3. "scenes": 场景列表，包含剧本中出现的所有场景。每个场景包含：
               - name: 场景名字。
               - prompt: 场景的详细环境描述（建筑风格、天气、光照、氛围、关键物体等），用于AI生图。
            
            请直接返回JSON对象，不要包含任何Markdown格式或额外文字。
            """
            
            response = await client.chat.completions.create(
                model=current_llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.content}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            # Clean up potential markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            data = json.loads(content)
            
            shots = []
            for item in data.get("shots", []):
                shots.append(ShotCreate(
                    prompt=item.get("prompt", ""),
                    dialogue=item.get("dialogue", ""),
                    characters=item.get("characters", []),
                    scene=item.get("scene", None)
                ))
            
            parsed_chars = []
            for item in data.get("characters", []):
                parsed_chars.append(ParsedCharacter(
                    name=item.get("name", ""),
                    prompt=item.get("prompt", "")
                ))
                
            parsed_scenes = []
            for item in data.get("scenes", []):
                parsed_scenes.append(ParsedScene(
                    name=item.get("name", ""),
                    prompt=item.get("prompt", "")
                ))
                
            return ScriptParseResponse(
                shots=shots,
                characters=parsed_chars,
                scenes=parsed_scenes
            )
            
        except Exception as e:
            print(f"AI Parse Error: {e}")
            # Fallback to mock if error
            pass

    # Mock/Fallback Implementation
    lines = [line.strip() for line in request.content.split('\n') if line.strip()]
    shots = []
    current_scene = None
    
    # Simple extraction sets
    found_chars = set()
    found_scenes = set()
    
    for line in lines:
        # Simple Scene Detection
        if line.startswith("场景：") or line.startswith("Scene:") or line.startswith("场景:"):
            # Extract scene name
            parts = line.split(":", 1)
            if len(parts) > 1:
                current_scene = parts[1].strip()
                found_scenes.add(current_scene)
            continue
            
        # Simple Character Detection (very basic, looks for Name: Dialogue)
        characters = []
        dialogue = ""
        prompt = line
        
        if "：" in line or ":" in line:
            parts = line.replace("：", ":").split(":", 1)
            potential_name = parts[0].strip()
            # If name is short, assume it's a character
            if len(potential_name) < 10 and " " not in potential_name:
                characters.append(potential_name)
                found_chars.add(potential_name)
                dialogue = parts[1].strip()
        
        shots.append(ShotCreate(
            prompt=prompt,
            dialogue=dialogue,
            characters=characters,
            scene=current_scene
        ))
    
    # Mock profiles for fallback
    return ScriptParseResponse(
        shots=shots,
        characters=[ParsedCharacter(name=c, prompt=f"{c}, anime style character, detailed") for c in found_chars],
        scenes=[ParsedScene(name=s, prompt=f"{s}, anime style background, detailed") for s in found_scenes]
    )

# --- AI Services ---

CANDIDATE_IMAGE_COUNT = 3


def _image_url_to_base64(url: str) -> str | None:
    if not url:
        return None

    def normalize_image_bytes(raw: bytes) -> bytes | None:
        if not raw:
            return None

        kind = imghdr.what(None, h=raw)
        if kind in ("jpeg", "png"):
            return raw

        try:
            from PIL import Image
        except Exception:
            return None

        try:
            img = Image.open(io.BytesIO(raw))
            img = img.convert("RGB")
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=95)
            return out.getvalue()
        except Exception:
            return None

    try:
        if url.startswith("http://localhost:8001/static/uploads/") or url.startswith("http://127.0.0.1:8001/static/uploads/") or url.startswith("/static/uploads/"):
            if url.startswith("/static/uploads/"):
                rel = url.split("/static/uploads/")[-1].lstrip("/")
                rel = unquote(rel)
                local_path = os.path.join("static", "uploads", rel)
            else:
                if "/static/uploads/" in url:
                    rel = url.split("/static/uploads/")[-1]
                    rel = unquote(rel)
                    local_path = os.path.join("static", "uploads", rel)
                else:
                    filename = url.split("/")[-1]
                    filename = unquote(filename)
                    local_path = os.path.join("static", "uploads", filename)
            
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    raw = f.read()
                    normalized = normalize_image_bytes(raw)
                    if not normalized:
                        print(f"[DEBUG] _image_url_to_base64: Failed to normalize {local_path}")
                        return None
                    return base64.b64encode(normalized).decode("utf-8")
            else:
                 print(f"[DEBUG] _image_url_to_base64: File not found at {local_path} (url: {url})")
                 return None

        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                if not raw:
                    return None
                normalized = normalize_image_bytes(raw)
                if not normalized:
                    return None
                return base64.b64encode(normalized).decode("utf-8")
    except Exception:
        return None

    return None

def _image_url_to_local_file(url: str) -> str | None:
    if not url:
        return None

    def normalize_image_bytes(raw: bytes) -> bytes | None:
        if not raw:
            return None

        kind = imghdr.what(None, h=raw)
        if kind in ("jpeg", "png"):
            return raw

        try:
            from PIL import Image
        except Exception:
            return None

        try:
            img = Image.open(io.BytesIO(raw))
            img = img.convert("RGB")
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=95)
            return out.getvalue()
        except Exception:
            return None

    try:
        raw = None
        if url.startswith("http://localhost:8001/static/uploads/") or url.startswith("http://127.0.0.1:8001/static/uploads/") or url.startswith("/static/uploads/"):
            if url.startswith("/static/uploads/"):
                rel = url.split("/static/uploads/")[-1].lstrip("/")
                rel = unquote(rel)
                local_path = os.path.join("static", "uploads", rel)
            else:
                if "/static/uploads/" in url:
                    rel = url.split("/static/uploads/")[-1]
                    rel = unquote(rel)
                    local_path = os.path.join("static", "uploads", rel)
                else:
                    filename = url.split("/")[-1]
                    filename = unquote(filename)
                    local_path = os.path.join("static", "uploads", filename)
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    raw = f.read()
        else:
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https"):
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = resp.read()

        normalized = normalize_image_bytes(raw or b"")
        if not normalized:
            return None

        ext = imghdr.what(None, h=normalized) or "jpg"
        ext = "jpg" if ext == "jpeg" else ext
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join("static", "uploads", filename)
        with open(filepath, "wb") as f:
            f.write(normalized)
        return filepath
    except Exception:
        return None

def _resolve_video_image_path(shot: Shot, project: Project) -> str | None:
    def resolve_from_url(url: str | None) -> str | None:
        if not url:
            return None
        if url.startswith("http://localhost") or url.startswith("http://127.0.0.1") or url.startswith("/static/uploads/"):
            rel = None
            if "/static/uploads/" in url:
                rel = url.split("/static/uploads/")[-1].lstrip("/")
            else:
                rel = url.split("/")[-1]
            rel = unquote(rel)
            candidate = os.path.join("static", "uploads", rel)
            if os.path.exists(candidate):
                return candidate
        local_file = _image_url_to_local_file(url)
        if local_file:
            return local_file
        b64 = _image_url_to_base64(url)
        if b64:
            return _save_base64_image_file(b64, sub_dir=project.id)
        return None

    tried = set()
    def try_url(url: str | None) -> str | None:
        if not url or url in tried:
            return None
        tried.add(url)
        return resolve_from_url(url)

    image_path = try_url(shot.image_url)
    if image_path:
        return image_path
    return None

def _save_base64_image(b64_data: str, sub_dir: str = None) -> str:
    image_data = base64.b64decode(b64_data)
    filename = f"{uuid.uuid4()}.png"
    if sub_dir:
        dir_path = os.path.join("static", "uploads", sub_dir)
        os.makedirs(dir_path, exist_ok=True)
        filepath = os.path.join(dir_path, filename)
        url_path = f"/static/uploads/{sub_dir}/{filename}"
    else:
        filepath = f"static/uploads/{filename}"
        url_path = f"/static/uploads/{filename}"
    with open(filepath, "wb") as f:
        f.write(image_data)
    return url_path

def _save_base64_image_file(b64_data: str, sub_dir: str = None) -> str:
    image_data = base64.b64decode(b64_data)
    ext = imghdr.what(None, h=image_data) or "png"
    ext = "jpg" if ext == "jpeg" else ext
    filename = f"{uuid.uuid4()}.{ext}"
    if sub_dir:
        dir_path = os.path.join("static", "uploads", sub_dir)
        os.makedirs(dir_path, exist_ok=True)
        filepath = os.path.join(dir_path, filename)
    else:
        filepath = os.path.join("static", "uploads", filename)
    with open(filepath, "wb") as f:
        f.write(image_data)
    return filepath

def _save_image_from_url(url: str, sub_dir: str = None) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "")
        
        ext = ".png"
        if "jpeg" in content_type or "jpg" in content_type:
            ext = ".jpg"
        elif "webp" in content_type:
            ext = ".webp"
            
        filename = f"{uuid.uuid4()}{ext}"
        if sub_dir:
            dir_path = os.path.join("static", "uploads", sub_dir)
            os.makedirs(dir_path, exist_ok=True)
            filepath = os.path.join(dir_path, filename)
            url_path = f"/static/uploads/{sub_dir}/{filename}"
        else:
            os.makedirs("static/uploads", exist_ok=True)
            filepath = f"static/uploads/{filename}"
            url_path = f"/static/uploads/{filename}"
            
        with open(filepath, "wb") as f:
            f.write(data)
        return url_path
    except Exception as e:
        print(f"Failed to save image from url: {e}")
        return url

async def _describe_image_with_vision(image_url: str) -> str:
    if not client:
        return ""
    
    # Simple heuristic to skip models known not to support vision to save time/errors
    # If uncertain, we try anyway.
    if "gpt-3.5" in current_llm_model and "turbo" in current_llm_model and "16k" not in current_llm_model:
        # Most basic 3.5 doesn't support vision, but let's just try-catch to be safe
        pass

    print(f"[Vision] Analyzing custom reference image: {image_url}")
    b64 = _image_url_to_base64(image_url)
    if not b64:
        print(f"[Vision] Failed to load image for analysis")
        return ""
        
    try:
        response = await client.chat.completions.create(
            model=current_llm_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe the visual style, composition, lighting, and key elements of this image concisely. This description will be used as a style reference for generating a new image."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]
                }
            ],
            max_tokens=200
        )
        description = response.choices[0].message.content
        print(f"[Vision] Generated description: {description[:50]}...")
        return description
    except Exception as e:
        print(f"[Vision] Failed to describe image: {e}")
        return ""

async def ai_generation_task(project_id: str, shot_id: str, type: str, count: int | None = None, video_id: str | None = None):
    project = DB.get(project_id)
    if not project: return

    target_shot = next((s for s in project.shots if s.id == shot_id), None)
    if not target_shot: return

    try:
        prompt = (target_shot.audio_prompt or target_shot.prompt or "") if type == "video" else (target_shot.prompt or "")
        
        # Clean existing layout keywords to avoid conflicts with selected panel_layout
        remove_patterns = [
            r"3-panel storyboard", r"3-panel", r"3 panel", r"triptych", r"three frames", r"three panel",
            r"comic panel layout", r"clean gutters", r"no text", r"no watermark",
            r"1-panel", r"single panel", r"1 panel", r"full shot", r"one frame",
            r"2-panel", r"diptych", r"2 panel", r"two frames", r"two panel",
            r"4-panel", r"2x2 grid", r"4 panel", r"four frames", r"four panel", r"yonkoma style",
            r"vertical split", r"horizontal split"
        ]
        for pattern in remove_patterns:
            prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)
            
        # Clean up punctuation
        prompt = re.sub(r",\s*,", ",", prompt)
        prompt = re.sub(r"\s+", " ", prompt).strip().strip(",")
        
        style_prompts = {
            "real": "photorealistic, raw photo, real person, 8k uhd, dslr, soft lighting, film grain, hyperrealistic",
            "anime": "anime style, japanese anime, vibrant colors, cel shading, high quality, highly detailed, masterpiece, 2d, beautiful composition",
            "manga": "manga style, japanese comic, black and white, line art, screentones, ink drawing, high contrast, monochrome, detailed lines, high quality",
            "realistic": "3d animation style, cgi, unreal engine 5, octane render, detailed texture, volumetric lighting, 8k, pixar style, disney style, 3d render",
            "chinese_anime": "chinese anime style, guofeng, donghua, ancient chinese aesthetics, elegant, vibrant, 2d"
        }
        style_desc = style_prompts.get(project.style, f"{project.style} style")
        
        # Adjust layout prompts based on style
        is_real = project.style == "real" or project.style == "realistic"
        
        layout_prompts = {
            "1-panel": "single panel, full shot, one frame, cinematic composition" if is_real else "single panel, full shot, one frame, cinematic composition, detailed background, no split screen",
            "2-panel": "split screen, side by side, diptych" if is_real else "2-panel storyboard, diptych, two frames, comic panel layout, vertical split or horizontal split, clean gutters",
            "3-panel": "collage of 3 images, triptych" if is_real else "3-panel storyboard, triptych, three frames, comic panel layout, clean gutters",
            "4-panel": "2x2 grid, collage of 4 images" if is_real else "4-panel storyboard, 2x2 grid, four frames, comic panel layout, yonkoma style, clean gutters"
        }
        layout_prompt = layout_prompts.get(target_shot.panel_layout, layout_prompts["3-panel"])
        
        # Auto-inject Character and Scene prompts
        additional_prompts = []
        
        # 1. Add Scene Prompt
        if target_shot.scene_id:
            scene_by_id = {s.id: s for s in (project.scenes or [])}
            scene = scene_by_id.get(target_shot.scene_id)
            if scene and scene.prompt:
                additional_prompts.append(f"Scene location: {scene.prompt}")
                
        # 2. Add Character Prompts
        if target_shot.characters:
            char_by_id = {c.id: c for c in (project.characters or [])}
            for char_id in target_shot.characters:
                char = char_by_id.get(char_id)
                if char and char.prompt:
                    additional_prompts.append(f"Character {char.name}: {char.prompt}")

        # Construct base prompt - Put style FIRST, then user prompt, then injected context, then layout
        base_parts = [style_desc, prompt]
        if additional_prompts:
            base_parts.extend(additional_prompts)
        base_parts.append(layout_prompt)
        base_parts.append("high quality, detailed")
        
        base_prompt = ", ".join(base_parts)
        
        negative_prompt = ""
        if project.style == "real":
            negative_prompt = "anime, cartoon, drawing, illustration, painting, sketch, 2d, flat, deformed, ugly, 3d render, cgi"
        elif project.style == "realistic":
            negative_prompt = "2d, flat, sketch, drawing, painting, anime, manga, japanese anime, photograph, real photo, live action"
        else:
            negative_prompt = "photorealistic, real photo, 3d, bad anatomy, bad hands, text, watermark"
        
        if type == "image":
            provider = current_api_config.image_provider or "openai"
            if provider == "openai":
                if not image_client:
                    raise Exception("OpenAI image provider not configured")
                
                # Gemini/OpenAI Native Image-to-Image Support
                # If the underlying model (like Gemini) supports image input, we pass it directly.
                # We do NOT use the Vision-to-Text fallback here anymore as requested by user.
                
                # OpenAI doesn't support negative_prompt natively usually, append to prompt
                final_prompt = f"{base_prompt}. Exclude: {negative_prompt}"
                
                images = []
                candidate_count = count or CANDIDATE_IMAGE_COUNT
                candidate_count = max(1, min(8, candidate_count))
                
                # Generate in parallel
                tasks = [
                    generate_image(
                        provider,
                        final_prompt,
                        sub_dir=project.id,
                        config=current_api_config,
                        image_client=image_client,
                        visual_service=visual_service,
                        negative_prompt=negative_prompt,
                        reference_images=None,
                        reference_image_url=target_shot.custom_image_url,
                        image_url_to_base64=_image_url_to_base64,
                        save_image_from_url=_save_image_from_url,
                        save_base64_image=_save_base64_image
                    )
                    for _ in range(candidate_count)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for res in results:
                    if isinstance(res, str) and res:
                        images.append(res)
                    elif isinstance(res, Exception):
                        print(f"OpenAI Image Gen failed: {res}")

                if images:
                    if target_shot.image_candidates is None:
                        target_shot.image_candidates = []
                    
                    # Store original remote URLs before downloading
                    remote_urls = list(images)
                    if not target_shot.original_image_url and remote_urls:
                         target_shot.original_image_url = remote_urls[0]

                    # Download and replace with local URLs
                    local_urls = []
                    for url in images:
                        if url.startswith("http"):
                            local = await _save_image_from_url(url, sub_dir=project.id)
                            local_urls.append(local)
                        else:
                            local_urls.append(url)
                            
                    target_shot.image_candidates.extend(local_urls)
                    target_shot.image_url = local_urls[0]
            elif provider == "vectorengine":
                images = []
                candidate_count = count or CANDIDATE_IMAGE_COUNT
                candidate_count = max(1, min(8, candidate_count))
                
                # Generate in parallel
                tasks = [
                    generate_image(
                        provider,
                        base_prompt,
                        sub_dir=project.id,
                        config=current_api_config,
                        image_client=image_client,
                        visual_service=visual_service,
                        negative_prompt=negative_prompt,
                        reference_images=None,
                        reference_image_url=None,
                        image_url_to_base64=_image_url_to_base64,
                        save_image_from_url=_save_image_from_url,
                        save_base64_image=_save_base64_image
                    )
                    for _ in range(candidate_count)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for res in results:
                    if isinstance(res, str) and res:
                        images.append(res)
                    elif isinstance(res, Exception):
                        print(f"VectorEngine gen failed: {res}")
                
                if images:
                    if target_shot.image_candidates is None:
                        target_shot.image_candidates = []
                    
                    # Store original remote URLs before downloading
                    remote_urls = list(images)
                    if not target_shot.original_image_url and remote_urls:
                         target_shot.original_image_url = remote_urls[0]

                    # Download and replace with local URLs
                    local_urls = []
                    for url in images:
                        if url.startswith("http"):
                            local = await _save_image_from_url(url, sub_dir=project.id)
                            local_urls.append(local)
                        else:
                            local_urls.append(url)

                    target_shot.image_candidates.extend(local_urls)
                    target_shot.image_url = local_urls[0]

            elif provider == "volcengine":
                if not visual_service:
                    raise Exception("Volcengine image provider not configured")
                
                # Use base_prompt constructed above
                prompt = base_prompt
                
                reference_images = []
                if isinstance(target_shot.characters, list) and target_shot.characters:
                    char_by_id = {c.id: c for c in (project.characters or []) if getattr(c, "id", None)}
                    # Use ALL characters, not just top 3
                    for cid in target_shot.characters:
                        c = char_by_id.get(cid)
                        if not c:
                            continue
                        b64 = _image_url_to_base64(getattr(c, "avatar_url", "") or "")
                        if b64:
                            reference_images.append({"name": c.name, "b64": b64})

                if target_shot.use_scene_ref and target_shot.scene_id:
                    scene_by_id = {s.id: s for s in (project.scenes or [])}
                    scene = scene_by_id.get(target_shot.scene_id)
                    print(f"[DEBUG] Checking Scene Ref: id={target_shot.scene_id}, found={scene is not None}, url={scene.image_url if scene else 'N/A'}")
                    if scene and scene.image_url:
                        b64 = _image_url_to_base64(scene.image_url)
                        if b64:
                            print(f"[DEBUG] Added scene reference: {scene.name}")
                            reference_images.append({"name": scene.name, "b64": b64})
                        else:
                            print(f"[DEBUG] Failed to convert scene image to base64: {scene.image_url}")

                # Add custom image reference
                if target_shot.custom_image_url:
                    print(f"[DEBUG] Checking Custom Ref: url={target_shot.custom_image_url}")
                    b64 = _image_url_to_base64(target_shot.custom_image_url)
                    if b64:
                        print(f"[DEBUG] Added custom reference")
                        reference_images.append({"name": "Custom Reference", "b64": b64})
                    else:
                        print(f"[DEBUG] Failed to convert custom image to base64: {target_shot.custom_image_url}")

                print(f"[DEBUG] Final Reference Images: {[r.get('name') for r in reference_images]}")

                if not reference_images:
                    print("[DEBUG] No reference images found (characters or scene). Using text-only generation.")

                images = []
                candidate_count = count or CANDIDATE_IMAGE_COUNT
                candidate_count = max(1, min(8, candidate_count))
                # Generate in parallel
                tasks = [
                    generate_image(
                        provider,
                        prompt,
                        sub_dir=project.id,
                        config=current_api_config,
                        image_client=image_client,
                        visual_service=visual_service,
                        negative_prompt=negative_prompt,
                        reference_images=reference_images,
                        reference_image_url=None,
                        image_url_to_base64=_image_url_to_base64,
                        save_image_from_url=_save_image_from_url,
                        save_base64_image=_save_base64_image
                    )
                    for _ in range(candidate_count)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for res in results:
                    if isinstance(res, str) and res:
                        images.append(res)
                    elif isinstance(res, Exception):
                        print(f"Volcengine gen failed: {res}")

                if images:
                    if target_shot.image_candidates is None:
                        target_shot.image_candidates = []
                    
                    # Store original remote URLs before downloading
                    remote_urls = list(images)
                    if not target_shot.original_image_url and remote_urls:
                         target_shot.original_image_url = remote_urls[0]

                    # Download and replace with local URLs
                    local_urls = []
                    for url in images:
                        if url.startswith("http"):
                            local = await _save_image_from_url(url, sub_dir=project.id)
                            local_urls.append(local)
                        else:
                            local_urls.append(url)
                            
                    target_shot.image_candidates.extend(local_urls)
                    target_shot.image_url = local_urls[0]
            else:
                raise Exception(f"Unsupported image provider: {provider}")
                
        elif type == "video":
            target_shot.video_progress = 0
            if video_id:
                if target_shot.video_items is None:
                    target_shot.video_items = []
                item = next((v for v in target_shot.video_items if v.id == video_id), None)
                if not item:
                    target_shot.video_items.append(VideoItem(id=video_id, progress=0, status="generating"))
                else:
                    item.progress = 0
                    item.status = "generating"
            provider = current_api_config.video_provider or "openai"
            image_path = _resolve_video_image_path(target_shot, project)
            if provider == "openai":
                if not video_client or not current_api_config.openai_video_model:
                    raise Exception("OpenAI video provider not configured")
                
                # Use style-enhanced prompt for video too, but skip layout prompts
                video_prompt = f"{style_desc}, {prompt}, high quality, detailed"
                if is_real:
                     video_prompt += f". Exclude: {negative_prompt}"
                
                # Determine source_url: prefer original_image_url (remote) over image_url (local)
                source_url = target_shot.original_image_url if target_shot.original_image_url else target_shot.image_url

                video_url = await generate_video(
                    provider,
                    video_prompt,
                    image_path,
                    sub_dir=project.id,
                    source_url=source_url,
                    config=current_api_config,
                    video_client=video_client,
                    visual_service=visual_service,
                    save_video_bytes=_save_video_bytes,
                    save_base64_video=_save_base64_video,
                    progress_callback=None
                )
                video_url = _normalize_video_url(video_url, sub_dir=project.id)
                target_shot.video_url = video_url
                target_shot.video_progress = 100
                if video_id and target_shot.video_items:
                    item = next((v for v in target_shot.video_items if v.id == video_id), None)
                    if item:
                        item.url = video_url
                        item.progress = 100
                        item.status = "completed"
            elif provider == "volcengine":
                if not visual_service:
                    raise Exception("Volcengine video provider not configured")
                if not image_path:
                    raise Exception(f"Image is required for video generation. shot image_url={target_shot.image_url}")

                def handle_progress(progress, status):
                    target_shot.video_progress = progress
                    if video_id and target_shot.video_items:
                        item = next((v for v in target_shot.video_items if v.id == video_id), None)
                        if item:
                            item.progress = progress
                            item.status = status if status else "generating"
                    save_db()

                # Use style-enhanced prompt for video too, but skip layout prompts which might confuse video generation
                video_prompt = f"{style_desc}, {prompt}, high quality, detailed"
                if is_real:
                     video_prompt += f" --no {negative_prompt}" # Some video models support --no for negative prompts, or just append it
                
                video_url = await generate_video(
                    provider,
                    video_prompt,
                    image_path,
                    sub_dir=project.id,
                    source_url=None,
                    config=current_api_config,
                    video_client=video_client,
                    visual_service=visual_service,
                    save_video_bytes=_save_video_bytes,
                    save_base64_video=_save_base64_video,
                    progress_callback=handle_progress
                )
                video_url = _normalize_video_url(video_url, sub_dir=project.id)
                target_shot.video_url = video_url
                target_shot.video_progress = 100
                if video_id and target_shot.video_items:
                    item = next((v for v in target_shot.video_items if v.id == video_id), None)
                    if item:
                        item.url = video_url
                        item.progress = 100
                        item.status = "completed"
            else:
                raise Exception(f"Unsupported video provider: {provider}")

        if type == "image":
            target_shot.status = GenerationStatus.COMPLETED
        save_db()
        
    except Exception as e:
        print(f"Generation Task Failed: {e}")
        if type == "image":
            target_shot.status = GenerationStatus.FAILED
        target_shot.video_progress = None
        if video_id and target_shot.video_items:
            item = next((v for v in target_shot.video_items if v.id == video_id), None)
            if item:
                item.status = "failed"
        save_db()

@app.post("/generate")
async def generate_asset(request: GenerateRequest, background_tasks: BackgroundTasks):
    project_id = request.project_id or "default_project"
    project = get_project_or_404(project_id)
    
    target_shot = next((s for s in project.shots if s.id == request.shot_id), None)
    if not target_shot:
        raise HTTPException(status_code=404, detail="Shot not found")
        
    if request.type == "image":
        target_shot.status = GenerationStatus.GENERATING
    video_id = None
    if request.type == "video":
        target_shot.video_progress = 0
        video_id = str(uuid.uuid4())
        if target_shot.video_items is None:
            target_shot.video_items = []
        target_shot.video_items.append(VideoItem(id=video_id, progress=0, status="generating"))
    save_db()

    background_tasks.add_task(ai_generation_task, project_id, request.shot_id, request.type, request.count, video_id)
    
    return {"status": "queued", "message": f"{request.type} generation started", "video_id": video_id}

class ShotImageSelectRequest(BaseModel):
    image_url: str

class ShotImageRemoveRequest(BaseModel):
    image_url: str | None = None
    remove_all: bool = False

class ShotVideoRemoveRequest(BaseModel):
    video_id: str | None = None
    url: str | None = None
    remove_all: bool = False

@app.post("/shots/{project_id}/{shot_id}/select-image", response_model=Shot)
async def select_shot_image(project_id: str, shot_id: str, data: ShotImageSelectRequest):
    project = get_project_or_404(project_id)
    target_shot = next((s for s in project.shots if s.id == shot_id), None)
    if not target_shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    target_shot.image_url = _sanitize_url(data.image_url)
    save_db()
    return target_shot

@app.post("/shots/{project_id}/{shot_id}/remove-image", response_model=Shot)
async def remove_shot_image(project_id: str, shot_id: str, data: ShotImageRemoveRequest):
    project = get_project_or_404(project_id)
    target_shot = next((s for s in project.shots if s.id == shot_id), None)
    if not target_shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    if data.remove_all or not data.image_url:
        target_shot.image_url = None
        target_shot.image_candidates = []
    else:
        image_url = _sanitize_url(data.image_url)
        if isinstance(target_shot.image_candidates, list):
            target_shot.image_candidates = [u for u in target_shot.image_candidates if _sanitize_url(u) != image_url]
        if _sanitize_url(target_shot.image_url) == image_url:
            target_shot.image_url = target_shot.image_candidates[0] if target_shot.image_candidates else None
    save_db()
    return target_shot

@app.post("/shots/{project_id}/{shot_id}/remove-video", response_model=Shot)
async def remove_shot_video(project_id: str, shot_id: str, data: ShotVideoRemoveRequest):
    project = get_project_or_404(project_id)
    target_shot = next((s for s in project.shots if s.id == shot_id), None)
    if not target_shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    if data.remove_all or (not data.video_id and not data.url):
        target_shot.video_url = None
        target_shot.video_progress = None
        target_shot.video_items = []
        target_shot.status = GenerationStatus.IDLE
        save_db()
        return target_shot
    if data.video_id and isinstance(target_shot.video_items, list):
        target_shot.video_items = [v for v in target_shot.video_items if v.id != data.video_id]
    if data.url:
        target_url = _sanitize_url(data.url)
        if isinstance(target_shot.video_items, list):
            target_shot.video_items = [v for v in target_shot.video_items if _sanitize_url(v.url) != target_url]
        if _sanitize_url(target_shot.video_url) == target_url:
            target_shot.video_url = None
    if target_shot.video_items:
        first_url = next((v.url for v in target_shot.video_items if v.url), None)
        if first_url:
            target_shot.video_url = first_url
    else:
        target_shot.video_url = None
        target_shot.video_progress = None
    save_db()
    return target_shot

@app.post("/api/generate-asset")
async def generate_asset_raw(request: AssetGenerateRequest):
    try:
        project_style = "anime"
        if request.project_id:
            project = DB.get(request.project_id)
            if project:
                project_style = project.style

        prompt = request.prompt
        
        # Style logic
        style_prompts = {
            "real": "photorealistic, raw photo, real person, 8k uhd, dslr, soft lighting, film grain, hyperrealistic",
            "anime": "anime style, japanese anime, vibrant colors, cel shading",
            "manga": "manga style, black and white, line art, comic book",
            "realistic": "realistic style, detailed texture, 3d render, unreal engine 5",
            "chinese_anime": "chinese anime style, guofeng, donghua, ancient chinese aesthetics, elegant, vibrant, 2d"
        }
        style_desc = style_prompts.get(project_style, f"{project_style} style")
        is_real = project_style == "real" or project_style == "realistic"

        if request.type == "character":
            prompt += f", character design, full body, white background, detailed, {style_desc}"
        elif request.type == "scene":
            prompt += f", scene background, scenery, detailed, {style_desc}"
        else:
            prompt += f", {style_desc}"

        negative_prompt = ""
        if is_real:
            negative_prompt = "anime, cartoon, drawing, illustration, painting, sketch, 2d, flat, deformed, ugly"
        else:
            negative_prompt = "photorealistic, real photo, 3d, bad anatomy, bad hands, text, watermark"
            
        provider = current_api_config.image_provider or "openai"
        if provider == "openai":
            if not image_client:
                raise HTTPException(status_code=400, detail="OpenAI image provider not configured")
            final_prompt = f"{prompt}. Exclude: {negative_prompt}"
            image_url = await generate_image(
                provider,
                final_prompt,
                sub_dir=request.project_id,
                config=current_api_config,
                image_client=image_client,
                visual_service=visual_service,
                negative_prompt=negative_prompt,
                reference_images=None,
                reference_image_url=None,
                image_url_to_base64=_image_url_to_base64,
                save_image_from_url=_save_image_from_url,
                save_base64_image=_save_base64_image
            )
            return {"url": image_url}
        elif provider == "vectorengine":
            image_url = await generate_image(
                provider,
                prompt,
                sub_dir=request.project_id,
                config=current_api_config,
                image_client=image_client,
                visual_service=visual_service,
                negative_prompt=negative_prompt,
                reference_images=None,
                reference_image_url=None,
                image_url_to_base64=_image_url_to_base64,
                save_image_from_url=_save_image_from_url,
                save_base64_image=_save_base64_image
            )
            return {"url": image_url}
        elif provider == "volcengine":
            if not visual_service:
                raise HTTPException(status_code=400, detail="Volcengine image provider not configured")
            image_url = await generate_image(
                provider,
                prompt,
                sub_dir=request.project_id,
                config=current_api_config,
                image_client=image_client,
                visual_service=visual_service,
                negative_prompt=negative_prompt,
                reference_images=None,
                reference_image_url=None,
                image_url_to_base64=_image_url_to_base64,
                save_image_from_url=_save_image_from_url,
                save_base64_image=_save_base64_image
            )
            return {"url": image_url}
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported image provider: {provider}")
            
    except Exception as e:
        print(f"Asset Generation Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/presets")
async def get_presets():
    return load_presets()

@app.post("/api/presets")
async def create_preset(preset: ApiPreset):
    presets = load_presets()
    # Update if exists, else append
    existing = next((p for p in presets if p.name == preset.name), None)
    if existing:
        existing.config = preset.config
    else:
        presets.append(preset)
    save_presets(presets)
    return preset

@app.delete("/api/presets/{name}")
async def delete_preset(name: str):
    presets = load_presets()
    new_presets = [p for p in presets if p.name != name]
    if len(new_presets) == len(presets):
        raise HTTPException(status_code=404, detail="Preset not found")
    save_presets(new_presets)
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
