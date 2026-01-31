import json
import urllib.error
import urllib.request

def generate_video(prompt: str, source_url: str | None, config) -> str:
    token = config.rongyiyun_token
    if not token:
        raise Exception("RongYiYun token not configured")
    base_url = (config.rongyiyun_api_base or "https://zcbservice.aizfw.cn/kyyApi").rstrip("/")
    endpoint = f"{base_url}/apiAiProject/createSora2"
    payload = {
        "prompt": prompt,
        "ratio": config.rongyiyun_ratio or "16:9",
        "duration": config.rongyiyun_duration or 10
    }
    if source_url and (source_url.startswith("http://") or source_url.startswith("https://")):
        payload["imgUrl"] = source_url
    headers = {
        "token": token,
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"RongYiYun request failed: {e} - Body: {error_body}")
    except Exception as e:
        raise Exception(f"RongYiYun request failed: {e}")
    if data.get("code") != 0:
        raise Exception(f"RongYiYun API Error: {data}")
    project_id = (data.get("data") or {}).get("projectId")
    if not project_id:
        raise Exception(f"RongYiYun missing projectId: {data}")
    return project_id

def get_task_result(project_id: str, config) -> dict:
    token = config.rongyiyun_token
    if not token:
        raise Exception("RongYiYun token not configured")
    base_url = (config.rongyiyun_api_base or "https://zcbservice.aizfw.cn/kyyApi").rstrip("/")
    endpoint = f"{base_url}/apiAiProject/getAiTaskResult?projectId={project_id}"
    headers = {
        "token": token,
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(endpoint, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"RongYiYun query failed: {e} - Body: {error_body}")
    except Exception as e:
        raise Exception(f"RongYiYun query failed: {e}")
    if data.get("code") != 0:
        raise Exception(f"RongYiYun query error: {data}")
    payload = data.get("data") or {}
    return {
        "status": payload.get("status"),
        "mediaUrl": payload.get("mediaUrl") or payload.get("resultUrl"),
        "projectId": payload.get("projectId"),
        "pid": payload.get("pid"),
        "reason": payload.get("reason")
    }
