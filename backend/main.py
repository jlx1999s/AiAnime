import asyncio
import uuid
from typing import List, Dict
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from models import Project, Shot, Character, ShotCreate, ShotUpdate, GenerateRequest, GenerationStatus

app = FastAPI(title="MochiAni Backend", version="1.0.0")

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
    new_shot = Shot(
        id=str(uuid.uuid4()),
        order=len(project.shots),
        **shot_data.dict()
    )
    # Default placeholder
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

class ScriptRequest(BaseModel):
    content: str

@app.post("/api/parse-script", response_model=List[ShotCreate])
async def parse_script(request: ScriptRequest):
    """
    Mock LLM Script Parsing.
    In a real scenario, this would call OpenAI/Anthropic API.
    """
    # Simple heuristic: Split by newlines, treat as prompts
    lines = [line.strip() for line in request.content.split('\n') if line.strip()]
    shots = []
    
    # If the script is very short, maybe it's just one scene?
    # Let's try to be a bit smarter: combine lines if they look like continuation? 
    # For now, 1 line = 1 shot is a good starting point for a "rough" parse.
    
    for line in lines:
        # If line contains "：" or ":", it might be dialogue, but user wants to focus on visual prompt.
        # We'll put the whole line in prompt for reference.
        shots.append(ShotCreate(
            prompt=line,
            dialogue="" 
        ))
        
    return shots

# --- AI Mock Services ---

async def mock_generation_task(project_id: str, shot_id: str, type: str):
    """Simulates a long-running AI generation task"""
    await asyncio.sleep(3) # Simulate 3s delay
    
    project = DB.get(project_id)
    if not project: return

    for shot in project.shots:
        if shot.id == shot_id:
            if type == "image":
                shot.image_url = f"https://picsum.photos/seed/{uuid.uuid4()}/600/338"
            elif type == "video":
                shot.video_url = "https://www.w3schools.com/html/mov_bbb.mp4" # Mock video
            shot.status = GenerationStatus.COMPLETED
            break

@app.post("/generate")
async def generate_asset(request: GenerateRequest, background_tasks: BackgroundTasks):
    # In a real app, you would verify project ownership here
    project_id = "default_project" 
    project = get_project_or_404(project_id)
    
    target_shot = next((s for s in project.shots if s.id == request.shot_id), None)
    if not target_shot:
        raise HTTPException(status_code=404, detail="Shot not found")
        
    target_shot.status = GenerationStatus.GENERATING
    
    # Run in background
    background_tasks.add_task(mock_generation_task, project_id, request.shot_id, request.type)
    
    return {"status": "queued", "message": f"{request.type} generation started"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
