
import os

FILE_PATH = "backend/main.py"
DATA_PATH = "backend/data/projects.json"

def replace_in_file(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    
    print(f"Processing {path}...")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = content.replace("http://localhost:8001/static/", "/static/")
    # Also handle the https variant just in case, though unlikely for localhost
    new_content = new_content.replace("http://127.0.0.1:8001/static/", "/static/")
    
    if content != new_content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {path}")
    else:
        print(f"No changes in {path}")

replace_in_file(FILE_PATH)
replace_in_file(DATA_PATH)
