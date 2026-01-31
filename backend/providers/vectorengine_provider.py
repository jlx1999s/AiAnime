import json
import time
import urllib.error
import urllib.request
from typing import Callable

def generate_image(prompt: str, negative_prompt: str, sub_dir: str | None, config, save_image_from_url: Callable[[str, str | None], str]) -> str:
    api_key = config.vectorengine_api_key
    base_url = config.vectorengine_api_base.rstrip("/")
    model = config.vectorengine_image_model or "flux-1/dev"
    if not api_key:
        raise Exception("VectorEngine API key not configured")
    url = f"{base_url}/fal-ai/{model}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "num_images": 1
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    print(f"[VectorEngine] Creating task: {url}")
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"[VectorEngine] HTTP Error Body: {error_body}")
        raise Exception(f"VectorEngine task creation failed: {e} - Body: {error_body}")
    except Exception as e:
        raise Exception(f"VectorEngine task creation failed: {e}")
    request_id = data.get("request_id")
    status_url = data.get("status_url")
    response_url = data.get("response_url")
    poll_url = status_url or response_url
    if not poll_url and request_id:
        poll_url = f"{base_url}/fal-ai/{model}/requests/{request_id}/status"
    if poll_url:
        poll_url = poll_url.replace("https://queue.fal.run", base_url)
    print(f"[VectorEngine] Polling: {poll_url}")
    for _ in range(60):
        time.sleep(2)
        req = urllib.request.Request(poll_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"Polling failed: {e}")
            continue
        status = data.get("status")
        if status == "COMPLETED":
            images = data.get("images", [])
            if images and images[0].get("url"):
                return save_image_from_url(images[0]["url"], sub_dir=sub_dir)
            break
        elif status in ("IN_QUEUE", "IN_PROGRESS"):
            continue
        else:
            raise Exception(f"VectorEngine failed with status: {status}")
    raise Exception("VectorEngine timeout")
