import asyncio
import base64
import imghdr
import json
import mimetypes
import os
import re
import urllib.request
import urllib.error
import uuid
from typing import Callable

def _openai_parse_sse_json(raw: bytes) -> list[dict]:
    items = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith(b"data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == b"[DONE]":
            continue
        try:
            items.append(json.loads(payload.decode("utf-8")))
        except Exception:
            continue
    return items

def _openai_parse_response(raw: bytes, content_type: str) -> tuple[dict | None, bytes | None]:
    if not raw:
        return None, None
    if content_type.startswith("video/") or content_type == "application/octet-stream":
        return None, raw
    try:
        parsed = json.loads(raw.decode("utf-8"))
        if isinstance(parsed, dict) and isinstance(parsed.get("data"), dict):
            return parsed["data"], None
        return parsed, None
    except json.JSONDecodeError:
        items = _openai_parse_sse_json(raw)
        if items:
            last = items[-1]
            if isinstance(last, dict) and isinstance(last.get("data"), dict):
                return last["data"], None
            return last, None
    return None, None

def _debug_openai_video_response(label: str, raw: bytes | None = None, content_type: str = "", data: dict | None = None) -> None:
    try:
        if data is not None:
            print(f"{label}: {json.dumps(data, ensure_ascii=False)}")
            return
        if raw is None:
            print(f"{label}: <empty>")
            return
        if content_type.startswith("video/") or content_type == "application/octet-stream":
            print(f"{label}: <binary {len(raw)} bytes>")
            return
        text = raw.decode("utf-8", errors="replace")
        print(f"{label}: {text}")
    except Exception as e:
        print(f"{label}: <failed to log response: {e}>")

def _openai_extract_url_or_base64(response: dict) -> tuple[str | None, str | None]:
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, list) and data:
            item = data[0]
            if isinstance(item, dict):
                if isinstance(item.get("url"), str) and item.get("url"):
                    return item["url"], None
                if isinstance(item.get("original_video_url"), str) and item.get("original_video_url"):
                    return item["original_video_url"], None
                if isinstance(item.get("video_url"), str) and item.get("video_url"):
                    return item["video_url"], None
                if isinstance(item.get("video"), str) and item.get("video"):
                    return item["video"], None
                if isinstance(item.get("b64_json"), str) and item.get("b64_json"):
                    return None, item["b64_json"]
        if isinstance(data, dict):
            if isinstance(data.get("url"), str) and data.get("url"):
                return data["url"], None
            if isinstance(data.get("original_video_url"), str) and data.get("original_video_url"):
                return data["original_video_url"], None
            if isinstance(data.get("video_url"), str) and data.get("video_url"):
                return data["video_url"], None
            if isinstance(data.get("video"), str) and data.get("video"):
                return data["video"], None
            if isinstance(data.get("b64_json"), str) and data.get("b64_json"):
                return None, data["b64_json"]
        results = response.get("results")
        if isinstance(results, list) and results:
            item = results[0]
            if isinstance(item, dict):
                if isinstance(item.get("url"), str) and item.get("url"):
                    return item["url"], None
                if isinstance(item.get("b64_json"), str) and item.get("b64_json"):
                    return None, item["b64_json"]
                if isinstance(item.get("video_url"), str) and item.get("video_url"):
                    return item["video_url"], None
                if isinstance(item.get("original_video_url"), str) and item.get("original_video_url"):
                    return item["original_video_url"], None
                if isinstance(item.get("video"), str) and item.get("video"):
                    return item["video"], None
        output = response.get("output")
        if isinstance(output, list) and output:
            item = output[0]
            if isinstance(item, dict):
                if isinstance(item.get("url"), str) and item.get("url"):
                    return item["url"], None
                if isinstance(item.get("b64_json"), str) and item.get("b64_json"):
                    return None, item["b64_json"]
                if isinstance(item.get("original_video_url"), str) and item.get("original_video_url"):
                    return item["original_video_url"], None
                if isinstance(item.get("video_url"), str) and item.get("video_url"):
                    return item["video_url"], None
                if isinstance(item.get("video"), str) and item.get("video"):
                    return item["video"], None
        if isinstance(output, dict):
            if isinstance(output.get("url"), str) and output.get("url"):
                return output["url"], None
            if isinstance(output.get("b64_json"), str) and output.get("b64_json"):
                return None, output["b64_json"]
            if isinstance(output.get("original_video_url"), str) and output.get("original_video_url"):
                return output["original_video_url"], None
            if isinstance(output.get("video_url"), str) and output.get("video_url"):
                return output["video_url"], None
            if isinstance(output.get("video"), str) and output.get("video"):
                return output["video"], None
        result = response.get("result")
        if isinstance(result, dict):
            if isinstance(result.get("url"), str) and result.get("url"):
                return result["url"], None
            if isinstance(result.get("b64_json"), str) and result.get("b64_json"):
                return None, result["b64_json"]
            if isinstance(result.get("original_video_url"), str) and result.get("original_video_url"):
                return result["original_video_url"], None
            if isinstance(result.get("video_url"), str) and result.get("video_url"):
                return result["video_url"], None
            if isinstance(result.get("video"), str) and result.get("video"):
                return result["video"], None
        if isinstance(response.get("url"), str) and response.get("url"):
            return response["url"], None
        if isinstance(response.get("original_video_url"), str) and response.get("original_video_url"):
            return response["original_video_url"], None
        if isinstance(response.get("video_url"), str) and response.get("video_url"):
            return response["video_url"], None
        if isinstance(response.get("video"), str) and response.get("video"):
            return response["video"], None
        if isinstance(response.get("b64_json"), str) and response.get("b64_json"):
            return None, response["b64_json"]
    return None, None

def _openai_normalize_poll_url(callback_url: str | None, base_url: str, default_url: str) -> str:
    if callback_url:
        if callback_url.startswith("http://") or callback_url.startswith("https://"):
            return callback_url
        return f"{base_url.rstrip('/')}/{callback_url.lstrip('/')}"
    return default_url

async def _openai_poll_video_result(poll_url: str, headers: dict, method: str = "GET", payload: dict | None = None) -> tuple[dict | None, bytes | None]:
    last_data = None
    consecutive_errors = 0
    for _ in range(150):  # Increase polling duration to 12.5 minutes for slow queues
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(poll_url, headers=headers, method=method, data=body)
        try:
            with urllib.request.urlopen(req, timeout=240) as resp:
                consecutive_errors = 0  # Reset error count on success
                raw = resp.read()
                content_type = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            raw = e.read()
            content_type = e.headers.get("Content-Type", "")
            data, _ = _openai_parse_response(raw, content_type)
            if isinstance(data, dict):
                _debug_openai_video_response("OpenAI video poll error response", data=data)
                error_msg = data.get("message") or data.get("error") or data.get("detail") or data.get("msg")
                if not error_msg and isinstance(data.get("error"), dict):
                    error_msg = data["error"].get("message")
                if not error_msg:
                    error_msg = json.dumps(data, ensure_ascii=False)
            else:
                _debug_openai_video_response("OpenAI video poll error response", raw=raw, content_type=content_type)
                error_msg = raw.decode("utf-8", errors="replace").strip()
            raise Exception(f"OpenAI video poll failed ({e.code}): {error_msg[:300]}")
        except urllib.error.URLError as e:
            consecutive_errors += 1
            if consecutive_errors > 10:
                raise Exception(f"OpenAI video poll failed after 10 retries: {e}")
            _debug_openai_video_response(f"OpenAI video poll network error (retry {consecutive_errors}/10): {e}")
            await asyncio.sleep(5)
            continue
        data, video_bytes = _openai_parse_response(raw, content_type)
        if video_bytes:
            return None, video_bytes
        if isinstance(data, dict):
            # Flatten nested data list if present (e.g. apimart.ai)
            if isinstance(data.get("data"), list) and data["data"]:
                first_item = data["data"][0]
                if isinstance(first_item, dict):
                    if not data.get("status"):
                        data["status"] = first_item.get("status")
                    if not data.get("url"):
                        data["url"] = first_item.get("url") or first_item.get("video_url") or first_item.get("video") or first_item.get("original_video_url")
                    if not data.get("failure_reason"):
                        data["failure_reason"] = first_item.get("failure_reason") or first_item.get("error")

            last_data = data
            media_url, media_b64 = _openai_extract_url_or_base64(data)
            if media_url or media_b64:
                return data, None
            status = data.get("status")
            if status in ("succeeded", "completed", "success", "SUCCESS", "failed", "error", "canceled", "cancelled"):
                return data, None
            if status == "QUEUED" or status == "submitted" or status == "IN_PROGRESS":
                 # Some providers (apimart) return QUEUED for a long time, treat as running
                 pass
            # Debug log for intermediate polling status
            if status not in ("running", "queued", "processing", "submitted", "IN_PROGRESS", "QUEUED"):
                _debug_openai_video_response(f"OpenAI video polling unknown status: {status}", data=data)
        await asyncio.sleep(5)
    return last_data, None

async def _runninghub_generate_video(prompt: str, image_path: str | None, api_key: str, base_url: str, source_url: str | None = None) -> str:
    first_image_url = None
    if source_url and (source_url.startswith("http://") or source_url.startswith("https://")) and "localhost" not in source_url and "127.0.0.1" not in source_url:
        first_image_url = source_url
    if not first_image_url and image_path and os.path.exists(image_path):
        print(f"[RunningHub] Local image detected. Attempting to upload to temporary host...")
        try:
            import requests
            try:
                with open(image_path, "rb") as f:
                    print(f"[RunningHub] Uploading to Catbox.moe...")
                    response = requests.post(
                        "https://catbox.moe/user/api.php",
                        data={"reqtype": "fileupload"},
                        files={"fileToUpload": f},
                        timeout=60
                    )
                    if response.status_code == 200 and response.text.startswith("http"):
                        first_image_url = response.text.strip()
                        print(f"[RunningHub] Upload success: {first_image_url}")
            except Exception as e:
                print(f"[RunningHub] Catbox upload failed: {e}")

            if not first_image_url:
                try:
                    with open(image_path, "rb") as f:
                        print(f"[RunningHub] Uploading to File.io...")
                        response = requests.post(
                            "https://file.io",
                            files={"file": f},
                            timeout=60
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("success") and data.get("link"):
                                first_image_url = data.get("link")
                                print(f"[RunningHub] Upload success: {first_image_url}")
                except Exception as e:
                    print(f"[RunningHub] File.io upload failed: {e}")
        except Exception as e:
            print(f"[RunningHub] Temporary upload failed: {e}")

        if not first_image_url:
            print("[RunningHub] Uploads failed, falling back to Data URI optimization...")
            try:
                from PIL import Image
                import io
                with Image.open(image_path) as img:
                    max_size = 1280
                    if max(img.size) > max_size:
                        ratio = max_size / max(img.size)
                        new_size = (int(img.width * ratio), int(img.height * ratio))
                        img = img.resize(new_size, Image.Resampling.LANCZOS)
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=85)
                    img_bytes = buffer.getvalue()
                    print(f"[RunningHub] Optimized image size: {len(img_bytes)} bytes (JPEG)")
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                first_image_url = f"data:image/jpeg;base64,{img_b64}"
            except Exception as e:
                print(f"[RunningHub] Failed to optimize image: {e}")
            try:
                with open(image_path, "rb") as f:
                    img_bytes = f.read()
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                mime_type, _ = mimetypes.guess_type(image_path)
                if not mime_type:
                    mime_type = "image/png"
                first_image_url = f"data:{mime_type};base64,{img_b64}"
            except Exception as e2:
                print(f"[RunningHub] Failed to create raw Data URI: {e2}")

    if not first_image_url:
        raise Exception("RunningHub requires a remote URL or valid local image for video generation")

    url = f"{base_url.rstrip('/')}/openapi/v2/kling-video-o1/image-to-video"
    duration = "5"
    if "long" in prompt.lower() or "10s" in prompt.lower():
        duration = "10"
    payload = {
        "prompt": prompt,
        "aspectRatio": "16:9",
        "duration": duration,
        "firstImageUrl": first_image_url,
        "mode": "std"
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    print(f"[RunningHub] Submitting video task to {url}")
    if first_image_url:
        print(f"[RunningHub] firstImageUrl type: {'Remote URL' if first_image_url.startswith('http') else 'Data URI'}")
        if first_image_url.startswith('data:'):
            print(f"[RunningHub] Data URI length: {len(first_image_url)}")
        else:
            print(f"[RunningHub] Remote URL: {first_image_url}")
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise Exception(f"RunningHub submission failed: {e}")
    if data.get("code") and data.get("code") != 0:
        raise Exception(f"RunningHub API Error: {data}")
    task_id = data.get("taskId")
    if not task_id:
        if data.get("errorMessage"):
            raise Exception(f"RunningHub error: {data.get('errorMessage')}")
        raise Exception(f"No taskId returned: {data}")
    print(f"[RunningHub] Task submitted: {task_id}")
    query_url = f"{base_url.rstrip('/')}/openapi/v2/query"
    for _ in range(120):
        await asyncio.sleep(5)
        q_req = urllib.request.Request(query_url, data=json.dumps({"taskId": task_id}).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(q_req, timeout=30) as q_resp:
                q_data = json.loads(q_resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[RunningHub] Poll request failed: {e}")
            continue
        status = q_data.get("status")
        if status == "SUCCESS":
            results = q_data.get("results")
            if results and len(results) > 0:
                return results[0].get("url")
            raise Exception("RunningHub reported success but no results found")
        elif status == "FAILED":
            print(f"[RunningHub] Task Failed Full Response: {json.dumps(q_data)}")
            raise Exception(f"RunningHub task failed: {q_data.get('errorMessage')} {q_data.get('failedReason')}")
        elif status not in ("QUEUED", "RUNNING"):
            print(f"[RunningHub] Unknown status: {status}")
    raise Exception("RunningHub task timed out")

async def generate_image(prompt: str, sub_dir: str | None, reference_image_url: str | None, image_client, config, image_url_to_base64: Callable[[str], str | None], save_image_from_url: Callable[[str, str | None], str], save_base64_image: Callable[[str, str | None], str]) -> str:
    print(f"openai_generate_image called with ref_url: {reference_image_url}")
    if not image_client:
        raise Exception("OpenAI image client not initialized")
    model = config.openai_image_model or "gpt-image-1"
    try:
        if "gemini" in model.lower() and "image" in model.lower():
            print(f"Using Chat Completion for image generation with model: {model}")
            messages_content = [{"type": "text", "text": prompt}]
            if reference_image_url:
                print(f"[Gemini] Using reference image: {reference_image_url}")
                b64 = image_url_to_base64(reference_image_url)
                if b64:
                    messages_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    })
                    messages_content[0]["text"] += " (Use the attached image as a style and composition reference)"
                else:
                    print(f"[Gemini] Failed to load reference image: {reference_image_url}")
            resp = await image_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": messages_content}],
                max_tokens=100000
            )
            content = resp.choices[0].message.content
            if not content:
                raise Exception("Empty response from chat completion")
            match = re.search(r"!\[.*?\]\((.*?)\)", content)
            if match:
                url_or_data = match.group(1)
                if url_or_data.startswith("data:image"):
                    return save_base64_image(url_or_data.split(",", 1)[1], sub_dir=sub_dir)
                return url_or_data
            clean_content = content.strip().replace("\n", "").replace("\r", "")
            if len(clean_content) > 100 and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in clean_content[:50]):
                return save_base64_image(clean_content, sub_dir=sub_dir)
            if content.strip().startswith("http"):
                return save_image_from_url(content.strip(), sub_dir=sub_dir)
            print(f"Gemini response content prefix: {content[:200]}...")
            raise Exception("Could not identify image in Gemini response")
        resp = await image_client.images.generate(
            model=model,
            prompt=prompt,
            size="1024x1024"
        )
        data = getattr(resp, "data", [])
        if data and getattr(data[0], "url", None):
            return save_image_from_url(data[0].url, sub_dir=sub_dir)
        if data and getattr(data[0], "b64_json", None):
            return save_base64_image(data[0].b64_json, sub_dir=sub_dir)
        raise Exception("No image content returned from OpenAI image")
    except Exception as e:
        print(f"OpenAI Image Generation Failed: {e}")
        await asyncio.sleep(1)
        return f"https://picsum.photos/seed/{uuid.uuid4()}/512/512"

async def generate_video(prompt: str, image_path: str | None, sub_dir: str | None, source_url: str | None, video_client, config, save_video_bytes: Callable[[bytes, str | None], str], save_base64_video: Callable[[str, str | None], str]) -> str:
    if not video_client:
        pass
    base_url = config.openai_video_api_base or config.openai_api_base or "https://api.openai.com/v1"
    api_key = config.openai_video_api_key or config.openai_api_key
    if not api_key:
        raise Exception("OpenAI video API key not configured")
    model = config.openai_video_model
    if not model:
        raise Exception("OpenAI video model not configured")
    if "runninghub" in base_url or "kling" in model.lower():
        return await _runninghub_generate_video(prompt, image_path, api_key, base_url, source_url)
    if not video_client:
        raise Exception("OpenAI video client not initialized")
    payload = {"model": model, "prompt": prompt}
    is_apimarket = "apimarket.ai" in base_url.lower() or "apimart.ai" in base_url.lower()
    image_url = None
    if source_url and (source_url.startswith("http://") or source_url.startswith("https://")) and "localhost" not in source_url and "127.0.0.1" not in source_url:
        image_url = source_url
    if not image_url and image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        img_type = imghdr.what(None, h=img_bytes) or "png"
        image_url = f"data:image/{img_type};base64,{img_b64}"
    if image_url:
        if is_apimarket:
            payload["image_url"] = image_url
        else:
            payload["url"] = image_url
    payload.setdefault("aspectRatio", "16:9")
    if "sora" in model.lower():
        payload.setdefault("duration", 10)
        if "sora-2-all" in model.lower():
            payload["size"] = "1280x720"
        else:
            payload.setdefault("size", "1920x1080")
    elif "veo" in model.lower():
        payload.setdefault("duration", 10)
        payload.setdefault("support_audio", True)
    else:
        payload.setdefault("duration", 10)
        payload.setdefault("size", "small")
    payload.setdefault("webHook", "-1")
    payload.setdefault("shutProgress", False)
    default_endpoint = "/videos/generations"
    if model.lower().startswith("sora"):
        if "sora-2-all" in model.lower():
            default_endpoint = "/v1/video/create"
        else:
            default_endpoint = "/v1/video/sora-video"
    elif "veo" in model.lower():
        default_endpoint = "/v1/videos"
    endpoint = config.openai_video_endpoint or default_endpoint
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        url = endpoint
    else:
        if base_url.rstrip("/").endswith("/v1") and endpoint.startswith("/v1/"):
            endpoint = endpoint[len("/v1"):]
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["api-key"] = api_key
        headers["x-api-key"] = api_key
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw = e.read()
        content_type = e.headers.get("Content-Type", "")
        data, _ = _openai_parse_response(raw, content_type)
        if isinstance(data, dict):
            _debug_openai_video_response("OpenAI video error response", data=data)
            error_msg = data.get("message") or data.get("error") or data.get("detail") or data.get("msg")
            if not error_msg and isinstance(data.get("error"), dict):
                error_msg = data["error"].get("message")
            if not error_msg:
                error_msg = json.dumps(data, ensure_ascii=False)
        else:
            _debug_openai_video_response("OpenAI video error response", raw=raw, content_type=content_type)
            error_msg = raw.decode("utf-8", errors="replace").strip()
        raise Exception(f"OpenAI video request failed ({e.code}): {error_msg[:300]}")
    except urllib.error.URLError as e:
        raise Exception(f"OpenAI video request failed: {e}")
    data, video_bytes = _openai_parse_response(raw, content_type)
    if video_bytes:
        return save_video_bytes(video_bytes, sub_dir=sub_dir)
    if not data:
        _debug_openai_video_response("OpenAI video raw response", raw=raw, content_type=content_type)
        text = raw.decode("utf-8", errors="replace").strip()
        raise Exception(f"Non-JSON response from OpenAI video: {text[:200]}")
    media_url, media_b64 = _openai_extract_url_or_base64(data)
    if media_url:
        return media_url
    if media_b64:
        return save_base64_video(media_b64, sub_dir=sub_dir)

    # Handle nested data list (e.g. apimart.ai returns {data: [{task_id: ...}]})
    if isinstance(data.get("data"), list) and data["data"]:
        first_item = data["data"][0]
        if isinstance(first_item, dict):
            if not data.get("id"):
                data["id"] = first_item.get("task_id") or first_item.get("id")
            if not data.get("status"):
                data["status"] = first_item.get("status")

    status = data.get("status")
    task_id = data.get("id")
    callback_url = data.get("callback_url")
    if callback_url is None and "webHook" in data:
        callback_url = data.get("webHook")
    if task_id:
        # Debug base_url for troubleshooting
        _debug_openai_video_response(f"OpenAI video polling init. Model: {model}, Base URL: {base_url}")
        
        if "sora-2-all" not in model.lower():
            try:
                result_endpoint = f"{base_url.rstrip('/')}/v1/draw/result"
                result_data, result_video = await _openai_poll_video_result(result_endpoint, headers, method="POST", payload={"id": task_id})
                if result_video:
                    return save_video_bytes(result_video, sub_dir=sub_dir)
                if isinstance(result_data, dict):
                    media_url, media_b64 = _openai_extract_url_or_base64(result_data)
                    if media_url:
                        return media_url
                    if media_b64:
                        return save_base64_video(media_b64, sub_dir=sub_dir)
            except Exception:
                pass
        if status in ("running", "queued", "processing", "submitted", "QUEUED", "IN_PROGRESS"):
            if "sora-2-all" in model.lower():
                poll_url = f"{base_url.rstrip('/')}/v1/video/query?id={task_id}"
            else:
                default_poll_url = f"{url.rstrip('/')}/{task_id}"
                poll_url = _openai_normalize_poll_url(callback_url, base_url, default_poll_url)
            polled_data, polled_video = await _openai_poll_video_result(poll_url, headers)
            if polled_video:
                return save_video_bytes(polled_video, sub_dir=sub_dir)
            if isinstance(polled_data, dict):
                media_url, media_b64 = _openai_extract_url_or_base64(polled_data)
                if media_url:
                    return media_url
                if media_b64:
                    return save_base64_video(media_b64, sub_dir=sub_dir)
                failure_reason = polled_data.get("failure_reason") or polled_data.get("error") or polled_data.get("message")
                if failure_reason:
                    _debug_openai_video_response("OpenAI video poll response", data=polled_data)
                    raise Exception(f"OpenAI video failed: {failure_reason}")
                last_status = polled_data.get("status")
                if last_status:
                    _debug_openai_video_response("OpenAI video poll timeout", data=polled_data)
                    raise Exception(f"OpenAI video polling timed out. Last status: {last_status}")
                _debug_openai_video_response("OpenAI video poll timeout", data=polled_data)
                raise Exception("OpenAI video polling timed out without result")
    
    _debug_openai_video_response("OpenAI video final unhandled response", data=data)
    raise Exception("No video content returned from OpenAI video")
