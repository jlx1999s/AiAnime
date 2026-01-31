import base64
import json
import os
import time
import uuid
from typing import Callable

def _volcengine_extract_url_or_base64(response: dict) -> tuple[str | None, str | None]:
    current = response
    for _ in range(3):
        if isinstance(current, dict) and ("Result" in current or "result" in current):
            current = current.get("Result") or current.get("result")
        else:
            break
    if isinstance(current, dict):
        data = current.get("data") if isinstance(current.get("data"), dict) else current
        for k in ("image_url", "video_url", "url"):
            v = data.get(k)
            if isinstance(v, str) and v:
                if v.startswith("http://") or v.startswith("https://"):
                    return v, None
                if len(v) > 1000 and " " not in v:
                    return None, v
        for k in ("image_urls", "urls"):
            v = data.get(k)
            if isinstance(v, list) and v and isinstance(v[0], str) and v[0]:
                if v[0].startswith("http://") or v[0].startswith("https://"):
                    return v[0], None
                if len(v[0]) > 1000 and " " not in v[0]:
                    return None, v[0]
                return v[0], None
        b64_list = data.get("binary_data_base64")
        if isinstance(b64_list, list) and b64_list and isinstance(b64_list[0], str) and b64_list[0]:
            return None, b64_list[0]
    return None, None

def _volcengine_extract_progress(response: dict) -> int | None:
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    candidates = [
        data.get("progress"),
        data.get("progress_percent"),
        data.get("progress_percentage"),
        data.get("percent"),
        data.get("process"),
        data.get("task_progress"),
        data.get("progress_ratio")
    ]
    for value in candidates:
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip().replace("%", "")
            try:
                value = float(value)
            except Exception:
                continue
        if isinstance(value, (int, float)):
            if value <= 1:
                value = value * 100
            progress = int(round(value))
            if progress < 0:
                return 0
            if progress > 100:
                return 100
            return progress
    return None

def _volcengine_sync2async_generate(visual_service, req_key: str, submit_form: dict, req_json: dict | None = None, timeout_s: float = 120.0, poll_s: float = 1.0, on_progress: Callable[[int | None, str | None], None] | None = None) -> tuple[str | None, str | None]:
    if not visual_service:
        raise Exception("Volcengine service not initialized")
    submit_form = dict(submit_form or {})
    submit_form["req_key"] = req_key
    submit_resp = visual_service.cv_sync2async_submit_task(submit_form)
    if not isinstance(submit_resp, dict) or submit_resp.get("code") != 10000:
        raise Exception(submit_resp)
    data = submit_resp.get("data") if isinstance(submit_resp.get("data"), dict) else {}
    task_id = data.get("task_id")
    if not task_id:
        raise Exception(submit_resp)
    deadline = time.time() + timeout_s
    last_resp = None
    last_progress = None
    last_status = None
    while time.time() < deadline:
        get_form = {"req_key": req_key, "task_id": task_id}
        if req_json is not None:
            get_form["req_json"] = json.dumps(req_json, ensure_ascii=False)
        resp = visual_service.cv_sync2async_get_result(get_form)
        last_resp = resp
        if not isinstance(resp, dict) or resp.get("code") != 10000:
            raise Exception(resp)
        url, b64 = _volcengine_extract_url_or_base64(resp)
        if url or b64:
            return url, b64
        resp_data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
        status = resp_data.get("status") or resp_data.get("task_status") or resp_data.get("state")
        progress = _volcengine_extract_progress(resp)
        if on_progress and (progress != last_progress or status != last_status):
            on_progress(progress, status if isinstance(status, str) else None)
            last_progress = progress
            last_status = status
        if isinstance(status, str) and status.lower() in ("failed", "error", "canceled", "cancelled"):
            raise Exception(resp)
        time.sleep(poll_s)
    raise Exception(last_resp or "Volcengine task timeout")

def generate_image(prompt: str, reference_images: list[dict] | None, sub_dir: str | None, visual_service, config, save_image_from_url: Callable[[str, str | None], str], save_base64_image: Callable[[str, str | None], str]) -> str:
    if not visual_service:
        raise Exception("Volcengine service not initialized")
    print(f"Generating image for prompt: {prompt[:50]}...")
    try:
        valid_refs = [r for r in (reference_images or []) if isinstance(r, dict) and r.get("b64")]
        if valid_refs:
            try:
                ref_desc = []
                b64_list = []
                for i, ref in enumerate(valid_refs):
                    name = ref.get("name", f"Character_{i+1}")
                    if name in ["Custom Reference", "Reference Image"]:
                        ref_desc.append(f"Reference Image {i+1}")
                    else:
                        ref_desc.append(f"Reference Image {i+1} is {name}")
                    b64_list.append(ref["b64"])
                marked_prompt = f"{prompt}. References: {', '.join(ref_desc)}."
                print(f"Using Multi-Reference Generation with {len(valid_refs)} images.")
                print(f"Augmented Prompt: {marked_prompt}")
                body = {
                    "prompt": marked_prompt,
                    "binary_data_base64": b64_list,
                    "seed": -1,
                    "scale": 1.0
                }
                model_version = "jimeng_t2i_v40" 
                if "jimeng_t2i" in config.volc_image_model:
                    model_version = config.volc_image_model
                print(f"Attempting Generation with {model_version}...")
                url, image_data_b64 = _volcengine_sync2async_generate(visual_service, model_version, body, req_json={"return_url": True}, timeout_s=180.0, poll_s=2.0)
                if url:
                    return save_image_from_url(url, sub_dir=sub_dir)
                if image_data_b64:
                    return save_base64_image(image_data_b64, sub_dir=sub_dir)
            except Exception as e:
                print(f"Multi-Reference Generation Failed: {e}")
                import traceback
                traceback.print_exc()
        print(f"Using Standard T2I ({config.volc_image_model})...")
        body = {
            "prompt": prompt,
            "seed": -1
        }
        url, image_data_b64 = _volcengine_sync2async_generate(visual_service, config.volc_image_model, body, req_json={"return_url": True}, timeout_s=120.0, poll_s=1.0)
        if url:
            return save_image_from_url(url, sub_dir=sub_dir)
        if image_data_b64:
            return save_base64_image(image_data_b64, sub_dir=sub_dir)
        raise Exception("No image content returned from Volcengine")
    except Exception as e:
        print(f"Image Generation Failed: {e}")
        print("Falling back to Mock Image due to API error...")
        time.sleep(1)
        return f"https://picsum.photos/seed/{uuid.uuid4()}/512/512"

def generate_video(prompt: str, image_path: str | None, progress_callback: Callable[[int | None, str | None], None] | None, sub_dir: str | None, visual_service, config, save_base64_video: Callable[[str, str | None], str]) -> str:
    if not visual_service:
        raise Exception("Volcengine service not initialized")
    print(f"Generating video for prompt: {prompt[:50]}...")
    try:
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            body = {
                "prompt": prompt,
                "binary_data_base64": [img_b64],
                "seed": -1,
                "frames": 121
            }
            url, video_data_b64 = _volcengine_sync2async_generate(visual_service, config.volc_video_model, body, req_json=None, timeout_s=600.0, poll_s=5.0, on_progress=progress_callback)
            if url:
                return url
            if video_data_b64:
                return save_base64_video(video_data_b64, sub_dir=sub_dir)
            raise Exception("No video content returned from Volcengine")
    except Exception as e:
        print(f"Video Generation Failed: {e}")
        raise
