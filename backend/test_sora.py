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
API_KEY = config.get("openai_video_api_key") or config.get("openai_image_api_key")
BASE_URL = config.get("openai_video_api_base") or "https://api.vectorengine.ai"

if not API_KEY:
    print("Error: API Key not found in config")
    sys.exit(1)

def test_sora_connection():
    print(f"Testing connection to {BASE_URL} with model sora-2-all...")
    
    # Try the specific endpoint for sora-2-all
    endpoints_to_try = [
        config.get("openai_video_endpoint") or "/v1/video/create",
        "/v1/video/sora-video",
        "/videos/generations"
    ]
    
    # Remove duplicates
    endpoints_to_try = list(dict.fromkeys(endpoints_to_try))
    
    payload = {
        "model": "sora-2-all",
        "prompt": "A cinematic drone shot of a futuristic city at sunset, neon lights, 720p",
        "aspectRatio": "16:9",
        "duration": 10,
        "size": "1280x720", # 720p for sora-2-all
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

    for endpoint in endpoints_to_try:
        # Smart URL joining to avoid double /v1
        current_endpoint = endpoint
        if BASE_URL.rstrip("/").endswith("/v1") and current_endpoint.startswith("/v1/"):
            current_endpoint = current_endpoint[len("/v1"):]
            
        url = f"{BASE_URL.rstrip('/')}/{current_endpoint.lstrip('/')}"
        
        print(f"\nTrying endpoint: {url}")
        
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
                    if "id" in data:
                        task_id = data['id']
                        print(f"Task ID received: {task_id}")
                        
                        # Test Polling
                        # For sora-2-all, polling URL is /v1/video/query?id={id}
                        poll_url = f"{BASE_URL.rstrip('/')}/v1/video/query?id={task_id}"
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
                                    # print(f"Polling Response: {poll_content[:200]}...")
                                    
                                    poll_data = json.loads(poll_content)
                                    status = poll_data.get("status")
                                    print(f"Task Status: {status}")
                                    
                                    if status == "succeeded" or status == "completed":
                                        print("Generation Succeeded!")
                                        print(f"Full Final Response: {json.dumps(poll_data, indent=2)}")
                                        
                                        # Check for video URL
                                        video_url = poll_data.get("video_url") or poll_data.get("url")
                                        if isinstance(poll_data.get("result"), dict):
                                             video_url = poll_data["result"].get("video_url") or poll_data["result"].get("url")
                                        
                                        if video_url:
                                            print(f"Video URL found: {video_url}")
                                        else:
                                            print("WARNING: Status is succeeded but no video_url found in top level or result object.")
                                        break
                                    elif status == "failed":
                                        print(f"Generation Failed: {poll_data.get('error') or poll_data.get('failure_reason')}")
                                        break
                                    
                                    time.sleep(10)
                            except urllib.error.HTTPError as e:
                                print(f"Polling Failed: {e.code} {e.reason}")
                                time.sleep(5)
                        else:
                             print("Polling timed out.")
                            
                    elif "url" in data:
                        print(f"Video URL received: {data['url']}")
                except Exception as e:
                    print(f"Error parsing response or polling: {e}")
                
                return # Stop after first success

        except urllib.error.HTTPError as e:
            print(f"HTTP Error: {e.code} {e.reason}")
            try:
                print(f"Error Body: {e.read().decode('utf-8')}")
            except:
                pass
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_sora_connection()
