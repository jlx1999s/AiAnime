import urllib.request
import urllib.error
import json
import os
import time
from main import load_api_config, current_api_config

def test_vectorengine():
    print("Loading Config...")
    load_api_config()
    
    api_key = current_api_config.vectorengine_api_key
    base_url = current_api_config.vectorengine_api_base.rstrip("/")
    model = current_api_config.vectorengine_image_model or "flux-1/dev"
    
    print(f"Config: URL={base_url}, Model={model}")
    
    if not api_key:
        print("Error: API Key is missing.")
        return

    url = f"{base_url}/fal-ai/{model}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": "A cute cat",
        "num_images": 1
    }
    
    print(f"Testing connectivity to: {url}")
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Status: {resp.status}")
            response_body = resp.read().decode("utf-8")
            print(f"Response: {response_body}")
            data = json.loads(response_body)
            print("Successfully connected and created task.")
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        error_body = e.read().decode("utf-8")
        print(f"Error Body: {error_body}")
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    test_vectorengine()
