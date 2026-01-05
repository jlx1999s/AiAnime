import requests
import time
import uuid

BASE_URL = "http://localhost:8001"
PROJECT_ID = "default_project"

def print_pass(message):
    print(f"✅ PASS: {message}")

def print_fail(message):
    print(f"❌ FAIL: {message}")

def test_api():
    print("--- Starting API Tests ---")

    # 1. Test GET /projects
    try:
        response = requests.get(f"{BASE_URL}/projects")
        if response.status_code == 200 and len(response.json()) > 0:
            print_pass("List Projects")
        else:
            print_fail(f"List Projects (Status: {response.status_code})")
    except Exception as e:
        print_fail(f"List Projects Connection Error: {e}")
        return

    # 2. Test GET /projects/{id}
    try:
        response = requests.get(f"{BASE_URL}/projects/{PROJECT_ID}")
        if response.status_code == 200:
            project = response.json()
            if project['id'] == PROJECT_ID and len(project['shots']) > 0:
                print_pass("Get Project Details")
            else:
                print_fail("Get Project Details - Invalid Content")
        else:
            print_fail(f"Get Project Details (Status: {response.status_code})")
    except Exception as e:
        print_fail(f"Get Project Error: {e}")

    # 3. Test POST /projects/{id}/shots (Create Shot)
    new_shot_id = None
    try:
        payload = {
            "prompt": "Test Shot Prompt",
            "dialogue": "Test Dialogue",
            "characters": ["c1"]
        }
        response = requests.post(f"{BASE_URL}/projects/{PROJECT_ID}/shots", json=payload)
        if response.status_code == 200:
            shot = response.json()
            new_shot_id = shot['id']
            if shot['prompt'] == "Test Shot Prompt":
                print_pass("Create Shot")
            else:
                print_fail("Create Shot - Content Mismatch")
        else:
            print_fail(f"Create Shot (Status: {response.status_code})")
    except Exception as e:
        print_fail(f"Create Shot Error: {e}")

    if not new_shot_id:
        print("Skipping dependent tests (Update/Delete/Generate) due to Create failure.")
        return

    # 4. Test PUT /shots/{project_id}/{shot_id} (Update Shot)
    try:
        payload = {
            "dialogue": "Updated Dialogue"
        }
        response = requests.put(f"{BASE_URL}/shots/{PROJECT_ID}/{new_shot_id}", json=payload)
        if response.status_code == 200:
            shot = response.json()
            if shot['dialogue'] == "Updated Dialogue":
                print_pass("Update Shot")
            else:
                print_fail("Update Shot - Content Mismatch")
        else:
            print_fail(f"Update Shot (Status: {response.status_code})")
    except Exception as e:
        print_fail(f"Update Shot Error: {e}")

    # 5. Test POST /generate (Mock AI Generation)
    try:
        payload = {
            "shot_id": new_shot_id,
            "type": "image"
        }
        response = requests.post(f"{BASE_URL}/generate", json=payload)
        if response.status_code == 200:
            print_pass("Trigger Generation Task")
            
            # Wait for async task
            print("   Waiting 4 seconds for generation...")
            time.sleep(4)
            
            # Verify result
            response = requests.get(f"{BASE_URL}/projects/{PROJECT_ID}")
            project = response.json()
            target_shot = next((s for s in project['shots'] if s['id'] == new_shot_id), None)
            
            if target_shot and "picsum.photos" in target_shot['image_url']:
                 print_pass("Generation Result Verified")
            else:
                 print_fail("Generation Result Verification Failed (Image URL not updated)")

        else:
            print_fail(f"Trigger Generation (Status: {response.status_code})")
    except Exception as e:
        print_fail(f"Generation Test Error: {e}")

    # 6. Test DELETE /shots/{project_id}/{shot_id}
    try:
        response = requests.delete(f"{BASE_URL}/shots/{PROJECT_ID}/{new_shot_id}")
        if response.status_code == 200:
            # Verify it's gone
            response = requests.get(f"{BASE_URL}/projects/{PROJECT_ID}")
            project = response.json()
            target_shot = next((s for s in project['shots'] if s['id'] == new_shot_id), None)
            if not target_shot:
                print_pass("Delete Shot")
            else:
                print_fail("Delete Shot - Shot still exists")
        else:
             print_fail(f"Delete Shot (Status: {response.status_code})")
    except Exception as e:
        print_fail(f"Delete Shot Error: {e}")

    print("--- Tests Completed ---")

if __name__ == "__main__":
    test_api()
