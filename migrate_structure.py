
import json
import os
import shutil
import urllib.parse

PROJECTS_FILE = "backend/data/projects.json"
STATIC_ROOT = "backend/static/uploads"

def load_projects():
    if not os.path.exists(PROJECTS_FILE):
        return {}
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_projects(data):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_local_file(url):
    if not url:
        return False
    return "static/uploads/" in url

def get_filename(url):
    # Remove query params
    clean_url = url.split("?")[0]
    return os.path.basename(clean_url)

def process_url(url, project_id):
    if not is_local_file(url):
        return url
    
    filename = get_filename(url)
    
    # Check if already in project folder
    if f"/static/uploads/{project_id}/" in url:
        # Just ensure it's a relative path
        return f"/static/uploads/{project_id}/{filename}"
    
    # Check if it's in another project folder (should not happen if logic is correct, but safe to check)
    # If it is, we might be sharing files. For now, assume flat structure migration.
    
    source_path = os.path.join(STATIC_ROOT, filename)
    dest_dir = os.path.join(STATIC_ROOT, project_id)
    dest_path = os.path.join(dest_dir, filename)
    
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        
    if os.path.exists(source_path):
        try:
            shutil.move(source_path, dest_path)
            print(f"Moved {filename} to {project_id}/")
        except Exception as e:
            print(f"Failed to move {filename}: {e}")
            return url # Keep original if move failed
    elif os.path.exists(dest_path):
        # Already moved
        pass
    else:
        # File not found in source or dest.
        # It might be missing. We still update URL to point to where it SHOULD be?
        # Or maybe it was already relative but not in a folder?
        # If we can't find the file, maybe don't change the URL structure to avoid breaking it further?
        # But if it's localhost, we want to fix it.
        # Let's check if it exists in root.
        pass

    return f"/static/uploads/{project_id}/{filename}"

def main():
    print("Starting migration...")
    projects = load_projects()
    
    for pid, project in projects.items():
        print(f"Processing project: {project.get('name', pid)} ({pid})")
        
        # Characters
        for char in project.get("characters", []):
            char["avatar_url"] = process_url(char.get("avatar_url"), pid)
            
        # Scenes
        for scene in project.get("scenes", []):
            scene["image_url"] = process_url(scene.get("image_url"), pid)
            
        # Shots
        for shot in project.get("shots", []):
            shot["image_url"] = process_url(shot.get("image_url"), pid)
            shot["video_url"] = process_url(shot.get("video_url"), pid)
            
            # Video items
            if shot.get("video_items"):
                for item in shot["video_items"]:
                    item["url"] = process_url(item.get("url"), pid)
                    
            # Image candidates
            if shot.get("image_candidates"):
                shot["image_candidates"] = [process_url(url, pid) for url in shot["image_candidates"]]

    save_projects(projects)
    print("Migration completed.")

if __name__ == "__main__":
    main()
