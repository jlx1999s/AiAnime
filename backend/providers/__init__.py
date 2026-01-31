import asyncio
from . import openai_provider
from . import volcengine_provider
from . import vectorengine_provider

async def generate_image(provider: str, prompt: str, sub_dir: str | None, config, image_client, visual_service, negative_prompt: str = "", reference_images: list[dict] | None = None, reference_image_url: str | None = None, image_url_to_base64=None, save_image_from_url=None, save_base64_image=None) -> str:
    if provider == "openai":
        return await openai_provider.generate_image(
            prompt=prompt,
            sub_dir=sub_dir,
            reference_image_url=reference_image_url,
            image_client=image_client,
            config=config,
            image_url_to_base64=image_url_to_base64,
            save_image_from_url=save_image_from_url,
            save_base64_image=save_base64_image
        )
    if provider == "vectorengine":
        return await asyncio.to_thread(
            vectorengine_provider.generate_image,
            prompt,
            negative_prompt,
            sub_dir,
            config,
            save_image_from_url
        )
    if provider == "volcengine":
        return await asyncio.to_thread(
            volcengine_provider.generate_image,
            prompt,
            reference_images,
            sub_dir,
            visual_service,
            config,
            save_image_from_url,
            save_base64_image
        )
    raise Exception(f"Unsupported image provider: {provider}")

async def generate_video(provider: str, prompt: str, image_path: str | None, sub_dir: str | None, source_url: str | None, config, video_client, visual_service, save_video_bytes=None, save_base64_video=None, progress_callback=None) -> str:
    if provider == "openai":
        return await openai_provider.generate_video(
            prompt=prompt,
            image_path=image_path,
            sub_dir=sub_dir,
            source_url=source_url,
            video_client=video_client,
            config=config,
            save_video_bytes=save_video_bytes,
            save_base64_video=save_base64_video
        )
    if provider == "volcengine":
        return await asyncio.to_thread(
            volcengine_provider.generate_video,
            prompt,
            image_path,
            progress_callback,
            sub_dir,
            visual_service,
            config,
            save_base64_video
        )
    raise Exception(f"Unsupported video provider: {provider}")
