import requests
import sys

BASE_URL = "http://localhost:8001"

def test_reorder():
    # 1. Create a project
    print("Creating project...")
    res = requests.post(f"{BASE_URL}/projects", json={"name": "Test Reorder", "style": "anime"})
    if res.status_code != 200:
        print(f"Failed to create project: {res.text}")
        return
    project = res.json()
    project_id = project["id"]
    print(f"Project created: {project_id}")

    # 2. Create 3 shots
    shot_ids = []
    for i in range(3):
        res = requests.post(f"{BASE_URL}/projects/{project_id}/shots", json={"prompt": f"Shot {i}"})
        if res.status_code != 200:
            print(f"Failed to create shot {i}: {res.text}")
            return
        shot = res.json()
        shot_ids.append(shot["id"])
        print(f"Created shot {i}: {shot['id']}")

    print(f"Original order: {shot_ids}")

    # 3. Reorder: Swap 0 and 2
    new_order = [shot_ids[2], shot_ids[1], shot_ids[0]]
    print(f"Requesting new order: {new_order}")
    
    res = requests.put(f"{BASE_URL}/projects/{project_id}/shots/reorder", json={"shot_ids": new_order})
    if res.status_code != 200:
        print(f"Reorder failed: {res.text}")
        sys.exit(1)
    
    reordered_shots = res.json()
    reordered_ids = [s["id"] for s in reordered_shots]
    print(f"Response order: {reordered_ids}")

    if reordered_ids == new_order:
        print("Reorder SUCCESS")
    else:
        print("Reorder FAILED - mismatch")
        sys.exit(1)

    # 4. Verify persistence (get project again)
    res = requests.get(f"{BASE_URL}/projects/{project_id}")
    project = res.json()
    saved_ids = [s["id"] for s in project["shots"]]
    print(f"Saved order: {saved_ids}")
    
    if saved_ids == new_order:
        print("Persistence SUCCESS")
    else:
        print("Persistence FAILED")
        sys.exit(1)

    # Clean up
    requests.delete(f"{BASE_URL}/projects/{project_id}")

if __name__ == "__main__":
    try:
        test_reorder()
    except Exception as e:
        print(f"Test failed with exception: {e}")
        sys.exit(1)
