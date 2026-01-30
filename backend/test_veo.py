import urllib.request
import json
import os
import sys
import time

# Load config from data/api_config.json
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "data", "api_config.json")
config = {}
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            print(f"Loaded config from {CONFIG_FILE}")
    except Exception as e:
        print(f"Failed to load config file: {e}")

# Use config values or fallback
API_KEY = config.get("openai_video_api_key")
BASE_URL = config.get("openai_video_api_base") or "https://api.vectorengine.ai"
# Allow overriding model from args or config
MODEL = config.get("openai_video_model") or "veo_3_1-fast"

if not API_KEY:
    print("Error: API Key not found in config")
    sys.exit(1)

def test_veo_connection():
    print(f"Testing connection to {BASE_URL} with model {MODEL}...")
    
    endpoint = "/v1/videos"
    
    payload = {
        "model": MODEL,
        "prompt": "A cinematic drone shot of a futuristic city at sunset, neon lights, 4k",
        "aspectRatio": "16:9",
        "duration": 10,
        "support_audio": True, # Specific for Veo
        "webHook": "-1",
        "shutProgress": False
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "api-key": API_KEY,
        "x-api-key": API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Smart URL joining
    current_endpoint = endpoint
    if BASE_URL.rstrip("/").endswith("/v1") and current_endpoint.startswith("/v1/"):
        current_endpoint = current_endpoint[len("/v1"):]
        
    url = f"{BASE_URL.rstrip('/')}/{current_endpoint.lstrip('/')}"
    
    print(f"\nTrying endpoint: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status_code = response.getcode()
            content = response.read().decode('utf-8')
            
            print(f"Success! Status Code: {status_code}")
            print(f"Response: {content}")

            # Parse response to see if we got a task ID or URL
            try:
                data = json.loads(content)
                task_id = data.get('id')
                
                if task_id:
                    print(f"Task ID received: {task_id}")
                    
                    # Test Polling
                    poll_url = f"{url}/{task_id}"
                    print(f"Testing polling at: {poll_url}")
                    
                    # Wait a bit before polling
                    time.sleep(5)
                    
                    max_retries = 100
                    for i in range(max_retries):
                        print(f"Polling attempt {i+1}/{max_retries}...")
                        req_poll = urllib.request.Request(
                            poll_url,
                            headers=headers,
                            method="GET"
                        )
                        try:
                            with urllib.request.urlopen(req_poll, timeout=30) as resp_poll:
                                poll_content = resp_poll.read().decode('utf-8')
                                print(f"Polling Status: {resp_poll.getcode()}")
                                
                                poll_data = json.loads(poll_content)
                                status = poll_data.get("status")
                                print(f"Task Status: {status}")
                                
                                if status == "succeeded" or status == "completed":
                                    print("Generation Succeeded!")
                                    print(f"Full Final Response: {json.dumps(poll_data, indent=2)}")
                                    break
                                elif status == "failed":
                                    print(f"Generation Failed: {poll_data.get('error') or poll_data.get('failure_reason')}")
                                    break
                                
                                time.sleep(5)
                        except urllib.error.HTTPError as e:
                            print(f"Polling Failed: {e.code} {e.reason}")
                            # If 404, maybe it takes time to appear?
                            if e.code == 404:
                                print("Task not found yet, retrying...")
                            else:
                                break
                            time.sleep(5)
                    else:
                        print("Polling timed out.")
                else:
                    print("No 'id' found in response.")
            except json.JSONDecodeError:
                print("Failed to decode JSON response")
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        try:
            error_content = e.read().decode('utf-8')
            print(f"Error Content: {error_content}")
        except:
            pass
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    test_veo_connection()
