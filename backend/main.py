import asyncio
import uuid
import os
import json
import shutil
import base64
import imghdr
import io
import urllib.request
from urllib.parse import urlparse
from typing import List, Dict
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import AsyncOpenAI
from volcengine.visual.VisualService import VisualService
from models import Project, Shot, Character, Scene, ShotCreate, ShotUpdate, GenerateRequest, GenerationStatus, AssetGenerateRequest

load_dotenv()

app = FastAPI(title="MochiAni Backend", version="1.0.0")

# --- Static Files ---
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- AI Client Setup ---
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
client = None
if DASHSCOPE_API_KEY:
    client = AsyncOpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

# Volcengine Setup
VOLC_ACCESSKEY = os.getenv("VOLC_ACCESSKEY")
VOLC_SECRETKEY = os.getenv("VOLC_SECRETKEY")
visual_service = None
if VOLC_ACCESSKEY and VOLC_SECRETKEY:
    try:
        visual_service = VisualService()
        visual_service.set_ak(VOLC_ACCESSKEY)
        visual_service.set_sk(VOLC_SECRETKEY)
    except Exception as e:
        print(f"Failed to initialize Volcengine: {e}")
else:
    print("Warning: VOLC_ACCESSKEY/SECRETKEY not found. Generation will use mock data.")

# CORS Setup (Allow Frontend to access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-Memory Database ---
DB: Dict[str, Project] = {}

# Seed Data
def seed_data():
    project_id = "default_project"
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

@app.get("/projects", response_model=List[Project])
async def list_projects():
    return list(DB.values())

@app.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    return get_project_or_404(project_id)

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
    return new_shot

@app.put("/shots/{project_id}/{shot_id}", response_model=Shot)
async def update_shot(project_id: str, shot_id: str, update_data: ShotUpdate):
    project = get_project_or_404(project_id)
    for shot in project.shots:
        if shot.id == shot_id:
            # Update fields
            updated_data = update_data.dict(exclude_unset=True)
            for k, v in updated_data.items():
                setattr(shot, k, v)
            return shot
    raise HTTPException(status_code=404, detail="Shot not found")

@app.delete("/shots/{project_id}/{shot_id}")
async def delete_shot(project_id: str, shot_id: str):
    project = get_project_or_404(project_id)
    project.shots = [s for s in project.shots if s.id != shot_id]
    return {"status": "success"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = f"static/uploads/{filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Return absolute URL (assuming localhost for now, in prod use env var)
    return {"url": f"http://localhost:8001/static/uploads/{filename}"}

@app.post("/projects/{project_id}/characters", response_model=Character)
async def create_character(project_id: str, character: Character):
    project = get_project_or_404(project_id)
    # Check if exists (by ID)
    if any(c.id == character.id for c in project.characters):
        raise HTTPException(status_code=400, detail="Character ID already exists")
    project.characters.append(character)
    return character

@app.post("/projects/{project_id}/scenes", response_model=Scene)
async def create_scene(project_id: str, scene: Scene):
    project = get_project_or_404(project_id)
    # Check if exists (by ID)
    if any(s.id == scene.id for s in project.scenes):
        raise HTTPException(status_code=400, detail="Scene ID already exists")
    project.scenes.append(scene)
    return scene

@app.put("/characters/{project_id}/{char_id}", response_model=Character)
async def update_character(project_id: str, char_id: str, updates: Character):
    project = get_project_or_404(project_id)
    for char in project.characters:
        if char.id == char_id:
            char.name = updates.name
            char.avatar_url = updates.avatar_url
            char.tags = updates.tags
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
    return {"ok": True}

@app.put("/scenes/{project_id}/{scene_id}", response_model=Scene)
async def update_scene(project_id: str, scene_id: str, updates: Scene):
    project = get_project_or_404(project_id)
    for scene in project.scenes:
        if scene.id == scene_id:
            scene.name = updates.name
            scene.image_url = updates.image_url
            scene.tags = updates.tags
            return scene
    raise HTTPException(status_code=404, detail="Scene not found")

class ScriptRequest(BaseModel):
    content: str

@app.post("/api/parse-script", response_model=List[ShotCreate])
async def parse_script(request: ScriptRequest):
    """
    Parse script using Aliyun Bailian (Qwen) if API key is present.
    Fallback to simple splitting if not.
    """
    if client:
        try:
            system_prompt = """
            你是一位专业的动画分镜导演。请将用户提供的剧本解析为一系列分镜镜头。
            每个镜头包含：
            - prompt: 详细的画面描述，包含镜头角度、光影、人物动作、场景细节。适合用于AI生图。
            - dialogue: 该镜头的台词（如果有）。
            - characters: 该镜头中出现的角色名字列表（例如：["陈远", "神秘师兄"]）。如果无角色则为空列表。
            - scene: 该镜头发生的场景名称（例如："外门练武场", "刻家入口"）。
            
            请直接返回一个JSON数组，格式如下，不要包含任何Markdown格式或额外文字：
            [
                {"prompt": "...", "dialogue": "...", "characters": ["Name1", "Name2"], "scene": "SceneName"}
            ]
            """
            
            response = await client.chat.completions.create(
                model="qwen-plus",
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
            for item in data:
                shots.append(ShotCreate(
                    prompt=item.get("prompt", ""),
                    dialogue=item.get("dialogue", ""),
                    characters=item.get("characters", []),
                    scene=item.get("scene", None)
                ))
            return shots
            
        except Exception as e:
            print(f"AI Parse Error: {e}")
            # Fallback to mock if error
            pass

    # Mock/Fallback Implementation
    lines = [line.strip() for line in request.content.split('\n') if line.strip()]
    shots = []
    current_scene = None
    
    for line in lines:
        # Simple Scene Detection
        if line.startswith("场景：") or line.startswith("Scene:") or line.startswith("场景:"):
            # Extract scene name
            parts = line.split(":", 1)
            if len(parts) > 1:
                current_scene = parts[1].strip()
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
                dialogue = parts[1].strip()
                # If dialogue is present, maybe prompt is just the action? 
                # For fallback, let's keep prompt as full line or just action if possible.
                # But simple is better: Prompt = full line
        
        shots.append(ShotCreate(
            prompt=prompt,
            dialogue=dialogue,
            characters=characters,
            scene=current_scene
        ))
    return shots

# --- AI Services ---

def _volcengine_extract_url_or_base64(response: dict) -> tuple[str | None, str | None]:
    current = response
    for _ in range(3):
        if isinstance(current, dict) and ("Result" in current or "result" in current):
            current = current.get("Result") or current.get("result")
        else:
            break

    if isinstance(current, dict):
        data = current.get("data") if isinstance(current.get("data"), dict) else current

        for k in ("image_url", "video_url", "url"):
            v = data.get(k)
            if isinstance(v, str) and v:
                return v, None

        for k in ("image_urls", "urls"):
            v = data.get(k)
            if isinstance(v, list) and v and isinstance(v[0], str) and v[0]:
                return v[0], None

        b64_list = data.get("binary_data_base64")
        if isinstance(b64_list, list) and b64_list and isinstance(b64_list[0], str) and b64_list[0]:
            return None, b64_list[0]

    return None, None

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
        if url.startswith("http://localhost:8001/static/uploads/") or url.startswith("http://127.0.0.1:8001/static/uploads/"):
            filename = url.split("/")[-1]
            local_path = os.path.join("static", "uploads", filename)
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    raw = f.read()
                    normalized = normalize_image_bytes(raw)
                    if not normalized:
                        return None
                    return base64.b64encode(normalized).decode("utf-8")

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

def _volcengine_sync2async_generate(req_key: str, submit_form: dict, req_json: dict | None = None, timeout_s: float = 120.0, poll_s: float = 1.0) -> tuple[str | None, str | None]:
    if not visual_service:
        raise Exception("Volcengine service not initialized")

    import time

    submit_form = dict(submit_form or {})
    submit_form["req_key"] = req_key
    submit_resp = visual_service.cv_sync2async_submit_task(submit_form)
    if not isinstance(submit_resp, dict) or submit_resp.get("code") != 10000:
        raise Exception(submit_resp)

    data = submit_resp.get("data") if isinstance(submit_resp.get("data"), dict) else {}
    task_id = data.get("task_id")
    if not task_id:
        raise Exception(submit_resp)

    deadline = time.time() + timeout_s
    last_resp = None

    while time.time() < deadline:
        get_form = {"req_key": req_key, "task_id": task_id}
        if req_json is not None:
            get_form["req_json"] = json.dumps(req_json, ensure_ascii=False)

        resp = visual_service.cv_sync2async_get_result(get_form)
        last_resp = resp

        if not isinstance(resp, dict) or resp.get("code") != 10000:
            raise Exception(resp)

        url, b64 = _volcengine_extract_url_or_base64(resp)
        if url or b64:
            return url, b64

        resp_data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
        status = resp_data.get("status") or resp_data.get("task_status") or resp_data.get("state")
        if isinstance(status, str) and status.lower() in ("failed", "error", "canceled", "cancelled"):
            raise Exception(resp)

        time.sleep(poll_s)

    raise Exception(last_resp or "Volcengine task timeout")

def volcengine_generate_image(prompt: str, reference_images_b64: list[str] | None = None) -> str:
    if not visual_service:
        raise Exception("Volcengine service not initialized")
    
    print(f"Generating image for prompt: {prompt[:50]}...")
    
    try:
        reference_images_b64 = [b for b in (reference_images_b64 or []) if isinstance(b, str) and b]
        
        if reference_images_b64:
            try:
                body = {
                    "prompt": prompt,
                    "binary_data_base64": [reference_images_b64[0]],
                    "seed": -1,
                    "scale": 0.5
                }
                print("Attempting I2I (jimeng_i2i_v30)...")
                url, image_data_b64 = _volcengine_sync2async_generate("jimeng_i2i_v30", body, req_json={"return_url": True}, timeout_s=120.0, poll_s=1.0)
                if url:
                    return url
                if image_data_b64:
                    return _save_base64_image(image_data_b64)
            except Exception as e:
                print(f"I2I Generation Failed (Fallback to T2I): {e}")

        print("Using T2I (jimeng_t2i_v30)...")
        body = {
            "prompt": prompt,
            "seed": -1
        }
        url, image_data_b64 = _volcengine_sync2async_generate("jimeng_t2i_v30", body, req_json={"return_url": True}, timeout_s=120.0, poll_s=1.0)
        if url:
            return url
        if image_data_b64:
             return _save_base64_image(image_data_b64)
            
        raise Exception("No image content returned from Volcengine")
        
    except Exception as e:
        print(f"Image Generation Failed: {e}")
        print("Falling back to Mock Image due to API error...")
        import time
        time.sleep(1)
        return f"https://picsum.photos/seed/{uuid.uuid4()}/512/512"

def _save_base64_image(b64_data: str) -> str:
    image_data = base64.b64decode(b64_data)
    filename = f"{uuid.uuid4()}.png"
    filepath = f"static/uploads/{filename}"
    with open(filepath, "wb") as f:
        f.write(image_data)
    return f"http://localhost:8001/static/uploads/{filename}"

def volcengine_generate_video(prompt: str, image_path: str = None) -> str:
    if not visual_service:
        raise Exception("Volcengine service not initialized")
        
    print(f"Generating video for prompt: {prompt[:50]}...")
    
    try:
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            body = {
                "prompt": prompt,
                "binary_data_base64": [img_b64],
                "seed": -1,
                "frames": 121
            }
            url, video_data_b64 = _volcengine_sync2async_generate("jimeng_i2v_first_v30", body, req_json=None, timeout_s=240.0, poll_s=2.0)
            if url:
                return url
            if video_data_b64:
                video_data = base64.b64decode(video_data_b64)
                filename = f"{uuid.uuid4()}.mp4"
                filepath = f"static/uploads/{filename}"
                with open(filepath, "wb") as f:
                    f.write(video_data)
                return f"http://localhost:8001/static/uploads/{filename}"

            raise Exception("No video content returned from Volcengine")

        raise Exception("Image is required for jimeng_i2v_first_v30")

    except Exception as e:
        print(f"Video Generation Failed: {e}")
        print("Falling back to mock video due to error.")
        return "https://www.w3schools.com/html/mov_bbb.mp4"

async def ai_generation_task(project_id: str, shot_id: str, type: str):
    project = DB.get(project_id)
    if not project: return

    target_shot = next((s for s in project.shots if s.id == shot_id), None)
    if not target_shot: return

    try:
        prompt = target_shot.prompt
        prompt = f"{prompt}, {project.style} style, high quality, detailed"
        
        if type == "image":
            if visual_service:
                prompt = f"{prompt}, 3-panel storyboard, triptych, three frames, comic panel layout, clean gutters, no text, no watermark"
                reference_images_b64 = []
                if isinstance(target_shot.characters, list) and target_shot.characters:
                    char_by_id = {c.id: c for c in (project.characters or []) if getattr(c, "id", None)}
                    for cid in target_shot.characters[:3]:
                        c = char_by_id.get(cid)
                        if not c:
                            continue
                        b64 = _image_url_to_base64(getattr(c, "avatar_url", "") or "")
                        if b64:
                            reference_images_b64.append(b64)

                image_url = await asyncio.to_thread(volcengine_generate_image, prompt, reference_images_b64)
                target_shot.image_url = image_url
            else:
                await asyncio.sleep(2)
                target_shot.image_url = f"https://picsum.photos/seed/{uuid.uuid4()}/600/338"
                
        elif type == "video":
            if visual_service:
                image_path = None
                if target_shot.image_url and "localhost" in target_shot.image_url:
                    filename = target_shot.image_url.split("/")[-1]
                    image_path = f"static/uploads/{filename}"
                
                video_url = await asyncio.to_thread(volcengine_generate_video, prompt, image_path)
                target_shot.video_url = video_url
            else:
                await asyncio.sleep(2)
                target_shot.video_url = "https://www.w3schools.com/html/mov_bbb.mp4"

        target_shot.status = GenerationStatus.COMPLETED
        
    except Exception as e:
        print(f"Generation Task Failed: {e}")
        target_shot.status = GenerationStatus.FAILED

@app.post("/generate")
async def generate_asset(request: GenerateRequest, background_tasks: BackgroundTasks):
    project_id = "default_project" 
    project = get_project_or_404(project_id)
    
    target_shot = next((s for s in project.shots if s.id == request.shot_id), None)
    if not target_shot:
        raise HTTPException(status_code=404, detail="Shot not found")
        
    target_shot.status = GenerationStatus.GENERATING
    
    # Run in background
    background_tasks.add_task(ai_generation_task, project_id, request.shot_id, request.type)
    
    return {"status": "queued", "message": f"{request.type} generation started"}

@app.post("/api/generate-asset")
async def generate_asset_raw(request: AssetGenerateRequest):
    try:
        prompt = request.prompt
        if request.type == "character":
            prompt += ", character design, full body, white background, detailed, anime style"
        elif request.type == "scene":
            prompt += ", scene background, scenery, detailed, anime style"
            
        if visual_service:
            image_url = await asyncio.to_thread(volcengine_generate_image, prompt)
            return {"url": image_url}
        else:
            await asyncio.sleep(2)
            return {"url": f"https://picsum.photos/seed/{uuid.uuid4()}/500/500"}
            
    except Exception as e:
        print(f"Asset Generation Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
