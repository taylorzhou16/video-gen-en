#!/usr/bin/env python3
"""
Vico Tools - Video Creation API Command Line Tools

Usage:
  python video_gen_tools.py video --image <path> --prompt <text> --duration <seconds>
  python video_gen_tools.py music --prompt <text> --style <style>
  python video_gen_tools.py tts --text <text> --voice <voice_type>
  python video_gen_tools.py image --prompt <text> --style <style>
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== Image Size Validation and Processing ==============

def validate_and_resize_image(
    image_path: str,
    output_path: str = None,
    min_size: int = 720,
    max_size: int = 2048,
    target_size: int = 1280
) -> Dict[str, Any]:
    """
    Validate and resize image dimensions

    Args:
        image_path: image path
        output_path: output path (auto-generated if None)
        min_size: minimum dimension limit (upscale if smaller)
        max_size: maximum dimension limit (downscale if larger)
        target_size: target size (used when upscaling)

    Returns:
        {
            "success": True,
            "original_size": (w, h),
            "new_size": (w, h),
            "resized": True/False,
            "output_path": "..."
        }
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("⚠️ PIL not installed, skipping image size check")
        return {
            "success": True,
            "original_size": None,
            "new_size": None,
            "resized": False,
            "output_path": image_path
        }

    try:
        img = Image.open(image_path)
        w, h = img.size

        min_dim = min(w, h)
        max_dim = max(w, h)

        need_resize = False
        scale = 1.0

        if min_dim < min_size:
            scale = target_size / min_dim
            need_resize = True
            logger.info(f"📐 Image size too small {w}x{h}，need to upscale to at least {min_size}px")
        elif max_dim > max_size:
            scale = max_size / max_dim
            need_resize = True
            logger.info(f"📐 Image size too large {w}x{h}，need to downscale to at most {max_size}px")

        if need_resize:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)

            if output_path is None:
                base, ext = os.path.splitext(image_path)
                output_path = f"{base}_resized{ext}"

            img_resized.save(output_path, quality=95)
            logger.info(f"📐 Image size adjusted: {w}x{h} → {new_w}x{new_h}")

            return {
                "success": True,
                "original_size": (w, h),
                "new_size": (new_w, new_h),
                "resized": True,
                "output_path": output_path
            }

        return {
            "success": True,
            "original_size": (w, h),
            "new_size": (w, h),
            "resized": False,
            "output_path": image_path
        }
    except Exception as e:
        logger.error(f"❌ Image size processing failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "original_size": None,
            "new_size": None,
            "resized": False,
            "output_path": image_path
        }

# ============== Configuration Management ==============

CONFIG_FILE = Path.home() / ".claude" / "skills" / "video-gen" / "config.json"


def load_config() -> Dict[str, str]:
    """Load API keys from config file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_config(config: Dict[str, str]):
    """Save config to file"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


class Config:
    """Load config from file and env vars (file takes priority)"""

    _cached_config = None

    @classmethod
    def _get_config(cls) -> Dict[str, str]:
        if cls._cached_config is None:
            cls._cached_config = load_config()
        return cls._cached_config

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """Get from config file first, then env vars"""
        config = cls._get_config()
        return config.get(key, os.getenv(key, default))

    # Vidu (Yunwu) API
    @property
    def YUNWU_API_KEY(self) -> str:
        return self.get("YUNWU_API_KEY", "")

    YUNWU_BASE_URL: str = os.getenv("YUNWU_BASE_URL", "https://yunwu.ai")
    VIDU_MODEL: str = os.getenv("VIDU_MODEL", "viduq3-pro")
    VIDU_RESOLUTION: str = os.getenv("VIDU_RESOLUTION", "720p")

    # Suno API
    @property
    def SUNO_API_KEY(self) -> str:
        return self.get("SUNO_API_KEY", "")

    SUNO_API_URL: str = os.getenv("SUNO_API_URL", "https://api.sunoapi.org/api/v1")
    SUNO_MODEL: str = os.getenv("SUNO_MODEL", "V3_5")

    # Volcengine TTS
    @property
    def VOLCENGINE_TTS_APP_ID(self) -> str:
        return self.get("VOLCENGINE_TTS_APP_ID", "")

    @property
    def VOLCENGINE_TTS_TOKEN(self) -> str:
        return self.get("VOLCENGINE_TTS_ACCESS_TOKEN", "")

    VOLCENGINE_TTS_CLUSTER: str = os.getenv("VOLCENGINE_TTS_CLUSTER", "volcano_tts")

    # Gemini Image (via Yunwu API, shared YUNWU_API_KEY)
    @property
    def GEMINI_API_KEY(self) -> str:
        return self.get("YUNWU_API_KEY", "")

    GEMINI_IMAGE_URL: str = "https://yunwu.ai/v1beta/models/gemini-3.1-flash-image-preview:generateContent"

    # Kling API
    @property
    def KLING_ACCESS_KEY(self) -> str:
        return self.get("KLING_ACCESS_KEY", "")

    @property
    def KLING_SECRET_KEY(self) -> str:
        return self.get("KLING_SECRET_KEY", "")

    KLING_BASE_URL: str = "https://api-beijing.klingai.com"
    KLING_MODEL: str = "kling-v3"  # kling-v3 (v3-omni) or kling-v1-5 or kling-v1

    # fal.ai API
    @property
    def FAL_API_KEY(self) -> str:
        return self.get("FAL_API_KEY", "")


Config = Config()


# ============== Storyboard / Creative Reading Tools ==============

def get_aspect_from_storyboard(storyboard_path: str) -> Optional[str]:
    """Read aspect_ratio from storyboard.json"""
    try:
        with open(storyboard_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("aspect_ratio")
    except Exception:
        return None


def get_music_config_from_creative(creative_path: str) -> Optional[Dict[str, Any]]:
    """Read music config from creative.json"""
    try:
        with open(creative_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            music = data.get("music", {})
            return {
                "need_bgm": music.get("need_bgm", True),
                "style": music.get("style"),
                "prompt": music.get("prompt")  # optional detailed description
            }
    except Exception:
        return None


# ============== Vidu Video Generation ==============

class ViduClient:
    """Vidu Video Generation Client（via Yunwu API）"""

    IMG2VIDEO_PATH = "/ent/v2/img2video"
    TEXT2VIDEO_PATH = "/ent/v2/text2video"
    QUERY_PATH = "/ent/v2/tasks/{task_id}/creations"

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    async def create_img2video(
        self,
        image_path: str,
        prompt: str,
        duration: int = 5,
        resolution: str = None,
        audio: bool = False,
        output: str = None
    ) -> Dict[str, Any]:
        """Image-to-video"""
        resolution = resolution or Config.VIDU_RESOLUTION

        # Prepareimage
        if image_path.startswith(('http://', 'https://')):
            image_input = image_path
        else:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}

            with open(image_path, 'rb') as f:
                image_data = f.read()

            base64_data = base64.b64encode(image_data).decode('utf-8')
            ext = os.path.splitext(image_path)[1].lower()
            # HEIC/HEIF need to be converted first
            if ext in ['.heic', '.heif']:
                import subprocess
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                subprocess.run(['ffmpeg', '-i', image_path, '-q:v', '2', tmp_path, '-y'],
                              capture_output=True, check=True)
                with open(tmp_path, 'rb') as f:
                    image_data = f.read()
                os.unlink(tmp_path)
                ext = '.jpg'

            mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                       '.webp': 'image/webp', '.heic': 'image/jpeg', '.heif': 'image/jpeg'}
            mime_type = mime_map.get(ext, 'image/jpeg')
            image_input = f"data:{mime_type};base64,{base64_data}"

        payload = {
            "model": Config.VIDU_MODEL,
            "images": [image_input],
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "audio": audio,
            "off_peak": False,
            "watermark": False
        }

        logger.info(f"📤 createImage-to-videotask: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{Config.YUNWU_BASE_URL}{self.IMG2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            task_id = result.get("task_id")
            if not task_id:
                return {"success": False, "error": "API did not return task_id"}

            logger.info(f"✅ Task created: {task_id}")

            # waitcomplete
            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ Image-to-videofailure: {e}")
            return {"success": False, "error": str(e)}

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        audio: bool = False,
        output: str = None
    ) -> Dict[str, Any]:
        """Text-to-video"""
        payload = {
            "model": Config.VIDU_MODEL,
            "prompt": prompt,
            "duration": duration,
            "resolution": Config.VIDU_RESOLUTION,
            "aspect_ratio": aspect_ratio,
            "bgm": audio,
            "off_peak": False,
            "watermark": False
        }

        logger.info(f"📤 createText-to-videotask: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{Config.YUNWU_BASE_URL}{self.TEXT2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )

            # If viduq3-pro does not support，fallback to viduq2
            if response.status_code in [400, 422]:
                payload["model"] = "viduq2"
                response = await self.client.post(
                    f"{Config.YUNWU_BASE_URL}{self.TEXT2VIDEO_PATH}",
                    json=payload,
                    headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
                )

            response.raise_for_status()
            result = response.json()

            task_id = result.get("task_id")
            if not task_id:
                return {"success": False, "error": "API did not return task_id"}

            logger.info(f"✅ Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ Text-to-videofailure: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """Waiting for task completion"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ Waiting for task completion: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Task timeout ({max_wait}seconds)")
                return None

            try:
                response = await self.client.get(
                    f"{Config.YUNWU_BASE_URL}{self.QUERY_PATH.format(task_id=task_id)}",
                    headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
                )
                response.raise_for_status()
                result = response.json()

                state = result.get("state")

                if state == "success":
                    creations = result.get("creations", [])
                    if creations:
                        video_url = creations[0].get("url")
                        logger.info(f"✅ Task completed (elapsed time: {int(elapsed)}seconds)")
                        return video_url

                elif state == "failed":
                    logger.error(f"❌ Task failed: {result.get('fail_reason')}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ Query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """Download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Yunwu Kling Video Generation ==============

class YunwuKlingClient:
    """
    Kling v3 Video Generation Client（via Yunwu API）

    Only supports kling-v3 model, for text2video and img2video。

    Key differences from official API:
    - Using `model` parameter instead of `model_name`
    - Bearer Token auth (reuses YUNWU_API_KEY）
    - Base URL: https://yunwu.ai
    """

    TEXT2VIDEO_PATH = "/kling/v1/videos/text2video"
    IMAGE2VIDEO_PATH = "/kling/v1/videos/image2video"
    QUERY_PATH = "/kling/v1/videos/text2video/{task_id}"

    MODEL = "kling-v3"  # fixedUsing kling-v3

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        self.base_url = Config.YUNWU_BASE_URL  # https://yunwu.ai

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        aspect_ratio: str = "9:16",
        audio: bool = False,
        multi_shot: bool = False,
        shot_type: str = None,
        multi_prompt: List[Dict] = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        Text-to-video

        Args:
            prompt: video description
            duration: duration (3-15 seconds)
            mode: std or pro
            aspect_ratio: aspect ratio (16:9, 9:16, 1:1)
            audio: whether to generate audio
            multi_shot: whether multi-shot
            shot_type: intelligence（AI auto storyboarding）or customize（custom storyboarding）
            multi_prompt: custom storyboard shot list
            output: output file path
        """
        payload = {
            "model": self.MODEL,  # Note: Yunwu kling-v3 uses 'model' instead of 'model_name'
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "audio": audio,
            "aspect_ratio": aspect_ratio
        }

        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt and shot_type == "customize":
                payload["multi_prompt"] = multi_prompt

        logger.info(f"📤 create Yunwu Kling Text-to-videotask: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{self.base_url}{self.TEXT2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API did not return task_id"}

            logger.info(f"✅ Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id, "text2video")

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "concurrent task limit exceeded，please wait for existing tasks to complete before retrying"
            logger.error(f"❌ Yunwu Kling Text-to-videofailure: {error_msg}")
            return {"success": False, "error": error_msg}

    async def create_image2video(
        self,
        image_path: str,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        audio: bool = False,
        image_tail: str = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        Image-to-video（supportsfirst/last frame control）

        Args:
            image_path: image pathorURL
            prompt: video description
            duration: duration (3-15 seconds)
            mode: std or pro
            audio: whether to generate audio
            image_tail: last frameimage pathorURL
            output: output file path
        """
        # Prepareimage
        image_url = await self._prepare_image(image_path)

        payload = {
            "model": self.MODEL,
            "image": image_url,
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "audio": audio
        }

        # first/last frame control
        if image_tail:
            tail_url = await self._prepare_image(image_tail)
            payload["image_tail"] = tail_url

        logger.info(f"📤 create Yunwu Kling Image-to-videotask: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{self.base_url}{self.IMAGE2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API did not return task_id"}

            logger.info(f"✅ Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id, "image2video")

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Yunwu Kling Image-to-videofailure: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _prepare_image(self, image_path: str) -> str:
        """Prepare image (URL or base64)"""
        if image_path.startswith(('http://', 'https://')):
            return image_path

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Validate and resize image dimensions
        result = validate_and_resize_image(image_path)
        if not result["success"]:
            raise ValueError(f"imageprocessfailure: {result.get('error')}")

        with open(result["output_path"], 'rb') as f:
            image_data = f.read()

        base64_data = base64.b64encode(image_data).decode('utf-8')
        ext = os.path.splitext(result["output_path"])[1].lower()
        mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
        mime_type = mime_map.get(ext, 'image/jpeg')

        return f"data:{mime_type};base64,{base64_data}"

    async def _wait_for_completion(self, task_id: str, task_type: str = "text2video", max_wait: int = 600) -> Optional[str]:
        """Waiting for task completion"""
        import time
        start_time = time.monotonic()

        query_path = self.QUERY_PATH.replace("{task_id}", task_id)
        if task_type == "image2video":
            query_path = self.IMAGE2VIDEO_PATH + f"/{task_id}"

        logger.info(f"⏳ wait Yunwu Kling Task completed: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Task timeout ({max_wait}seconds)")
                return None

            try:
                response = await self.client.get(
                    f"{self.base_url}{query_path}",
                    headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
                )
                response.raise_for_status()
                result = response.json()

                code = result.get("code")
                if code != 0:
                    logger.error(f"❌ taskQuery failed: {result.get('message')}")
                    return None

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ Task completed (elapsed time: {int(elapsed)}seconds)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "unknown")
                    logger.error(f"❌ Task failed: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ Query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """Download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class YunwuKlingOmniClient:
    """
    Kling v3 Omni Video Generation Client（via Yunwu API）

    Only supports kling-v3-omni model, forMulti-reference imagesVideo Generation。

    Key differences from official API:
    - Using `model_name` parameter（same as official API）
    - Bearer Token auth (reuses YUNWU_API_KEY）
    - Base URL: https://yunwu.ai
    """

    OMNI_VIDEO_PATH = "/kling/v1/videos/omni-video"
    QUERY_PATH = "/kling/v1/videos/omni-video/{task_id}"

    MODEL = "kling-v3-omni"  # fixedUsing kling-v3-omni

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        self.base_url = Config.YUNWU_BASE_URL  # https://yunwu.ai

    async def create_omni_video(
        self,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        aspect_ratio: str = "9:16",
        audio: bool = False,
        image_list: List[str] = None,
        multi_shot: bool = False,
        shot_type: str = None,
        multi_prompt: List[Dict] = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        Omni-Video generate（supportsMulti-reference images）

        Args:
            prompt: video description, can use <<<image_1>>> to reference images
            duration: duration (3-15 seconds)
            mode: std or pro
            aspect_ratio: aspect ratio (16:9, 9:16, 1:1)
            audio: whether to generate audio
            image_list: image path list，for character consistency
            multi_shot: whether multi-shot
            shot_type: intelligence or customize
            multi_prompt: custom storyboard shot list
            output: output file path
        """
        payload = {
            "model_name": self.MODEL,  # Note: Yunwu kling-v3-omni uses 'model_name'
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "audio": audio,
            "aspect_ratio": aspect_ratio
        }

        # process image_list（format：[{"image_url": url_or_base64}, ...]）
        if image_list:
            processed_images = await self._prepare_image_list(image_list)
            if processed_images:
                payload["image_list"] = processed_images
                logger.info(f"📎 Using {len(processed_images)} reference images")

        # processmulti-shotparameter
        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt and shot_type == "customize":
                payload["multi_prompt"] = multi_prompt

        logger.info(f"📤 create Yunwu Kling Omni-Video task: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{self.base_url}{self.OMNI_VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API did not return task_id"}

            logger.info(f"✅ Omni-Video Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "concurrent task limit exceeded，please wait for existing tasks to complete before retrying"
            logger.error(f"❌ Yunwu Kling Omni-Video failure: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _prepare_image_list(self, image_paths: List[str]) -> List[Dict]:
        """Prepare image_list parameter"""
        result = []
        for img_path in image_paths:
            try:
                if img_path.startswith(('http://', 'https://')):
                    result.append({"image_url": img_path})
                else:
                    # Convert local file to base64
                    base64_data = await self._file_to_base64(img_path)
                    if base64_data:
                        result.append({"image_url": base64_data})
            except Exception as e:
                logger.warning(f"⚠️ reference imageprocessfailure: {img_path}, {e}")
        return result

    async def _file_to_base64(self, file_path: str) -> Optional[str]:
        """Convert file to base64"""
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ file does not exist: {file_path}")
            return None

        # Validate and resize image dimensions
        result = validate_and_resize_image(file_path)
        if not result["success"]:
            logger.warning(f"⚠️ imageprocessfailure: {file_path}, {result.get('error')}")
            return None

        with open(result["output_path"], 'rb') as f:
            image_data = f.read()

        base64_data = base64.b64encode(image_data).decode('utf-8')
        ext = os.path.splitext(result["output_path"])[1].lower()
        mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
        mime_type = mime_map.get(ext, 'image/jpeg')

        return f"data:{mime_type};base64,{base64_data}"

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """Waiting for task completion"""
        import time
        start_time = time.monotonic()

        query_path = self.QUERY_PATH.replace("{task_id}", task_id)

        logger.info(f"⏳ wait Yunwu Kling Omni Task completed: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Task timeout ({max_wait}seconds)")
                return None

            try:
                response = await self.client.get(
                    f"{self.base_url}{query_path}",
                    headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
                )
                response.raise_for_status()
                result = response.json()

                code = result.get("code")
                if code != 0:
                    logger.error(f"❌ taskQuery failed: {result.get('message')}")
                    return None

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ Task completed (elapsed time: {int(elapsed)}seconds)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "unknown")
                    logger.error(f"❌ Task failed: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ Query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """Download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Kling Video Generation ==============

class KlingClient:
    """
    Kling Video Generation Client (kling-v3)

    Using /v1/videos/text2video and /v1/videos/image2video endpoint。
    supports text-to-video, image-to-video（first frame/first and last frame）、multi-shot, audio-video sync output。
    """

    TEXT2VIDEO_PATH = "/v1/videos/text2video"
    IMAGE2VIDEO_PATH = "/v1/videos/image2video"
    TEXT2VIDEO_QUERY_PATH = "/v1/videos/text2video/{task_id}"
    IMAGE2VIDEO_QUERY_PATH = "/v1/videos/image2video/{task_id}"

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
            }
        )
        self._token = None
        self._token_expire = 0

    def _generate_token(self) -> str:
        """Generate JWT auth token"""
        import jwt
        import time

        now = int(time.time())
        payload = {
            "iss": Config.KLING_ACCESS_KEY,
            "iat": now,
            "exp": now + 3600,
            "nbf": now - 5
        }
        return jwt.encode(payload, Config.KLING_SECRET_KEY, algorithm="HS256")

    def _get_token(self) -> str:
        """Get valid token (with cache)"""
        import time
        if not self._token or time.time() > self._token_expire - 60:
            self._token = self._generate_token()
            self._token_expire = time.time() + 3600
        return self._token

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        aspect_ratio: str = "9:16",
        sound: str = "on",
        multi_shot: bool = False,
        shot_type: str = None,
        multi_prompt: List[Dict] = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        Text-to-video

        Args:
            prompt: video description
            duration: duration (3-15 seconds)
            mode: std or pro
            aspect_ratio: aspect ratio (16:9, 9:16, 1:1)
            sound: on or off
            multi_shot: whether multi-shot
            shot_type: intelligence（AI auto storyboarding）or customize（custom storyboarding）
            multi_prompt: custom storyboard shot list，format [{"index": 1, "prompt": "...", "duration": "3"}, ...]
            output: output file path
        """
        payload = {
            "model_name": Config.KLING_MODEL,
            "prompt": prompt,
            "negative_prompt": "",
            "duration": str(duration),
            "mode": mode,
            "sound": sound,
            "aspect_ratio": aspect_ratio
        }

        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt and shot_type == "customize":
                payload["multi_prompt"] = multi_prompt

        logger.info(f"📤 create Kling Text-to-videotask: {prompt[:50]}...")

        try:
            token = self._get_token()
            response = await self.client.post(
                f"{Config.KLING_BASE_URL}{self.TEXT2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API did not return task_id"}

            logger.info(f"✅ Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "concurrent task limit exceeded，please wait for existing tasks to complete before retrying"
            elif "1201" in error_msg:
                error_msg = "model not supported or parameter error，please check model_name and mode parameter"
            logger.error(f"❌ Kling Text-to-videofailure: {error_msg}")
            return {"success": False, "error": error_msg}

    async def create_image2video(
        self,
        image_path: str,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        sound: str = "on",
        tail_image_path: str = None,
        output: str = None,
        multi_shot: bool = False,
        shot_type: str = None,
        multi_prompt: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Image-to-video

        Args:
            image_path: image pathorURL
            prompt: video description
            duration: duration (3-15 seconds)
            mode: std or pro
            sound: on or off
            tail_image_path: last frameimage path（used forfirst/last frame control）
            output: output file path
            multi_shot: whether multi-shot
            shot_type: Multi-shot type (intelligence/customize)
            multi_prompt: Multi-shot config list
        """
        # Prepareimage
        if image_path.startswith(('http://', 'https://')):
            image_url = image_path
        else:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}

            # Validate and resize image dimensions
            result = validate_and_resize_image(image_path)
            if not result["success"]:
                return {"success": False, "error": f"imageprocessfailure: {result.get('error')}"}

            processed_path = result["output_path"]

            with open(processed_path, 'rb') as f:
                image_data = f.read()

            ext = os.path.splitext(processed_path)[1].lower()
            if ext in ['.heic', '.heif']:
                import subprocess
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                subprocess.run(['ffmpeg', '-i', processed_path, '-q:v', '2', tmp_path, '-y'],
                              capture_output=True, check=True)
                with open(tmp_path, 'rb') as f:
                    image_data = f.read()
                os.unlink(tmp_path)

            image_url = base64.b64encode(image_data).decode('utf-8')

        payload = {
            "model_name": Config.KLING_MODEL,
            "image": image_url,
            "prompt": prompt,
            "negative_prompt": "",
            "duration": str(duration),
            "mode": mode,
            "sound": sound
        }

        # processmulti-shotparameter
        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt:
                payload["multi_prompt"] = multi_prompt

        # processlast frameimage（first/last frame control）
        if tail_image_path:
            if tail_image_path.startswith(('http://', 'https://')):
                tail_image_url = tail_image_path
            else:
                if not os.path.exists(tail_image_path):
                    return {"success": False, "error": f"last frameImage not found: {tail_image_path}"}

                # validate and adjust last frame image size
                tail_result = validate_and_resize_image(tail_image_path)
                if not tail_result["success"]:
                    return {"success": False, "error": f"last frameimageprocessfailure: {tail_result.get('error')}"}

                with open(tail_result["output_path"], 'rb') as f:
                    tail_image_data = f.read()

                tail_image_url = base64.b64encode(tail_image_data).decode('utf-8')

            payload["image_tail"] = tail_image_url
            logger.info(f"📤 create Kling image-to-video task（with last frame）: {prompt[:50]}...")
        else:
            logger.info(f"📤 create Kling image-to-video task: {prompt[:50]}...")

        try:
            token = self._get_token()
            response = await self.client.post(
                f"{Config.KLING_BASE_URL}{self.IMAGE2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API did not return task_id"}

            logger.info(f"✅ Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id, query_path=self.IMAGE2VIDEO_QUERY_PATH)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "concurrent task limit exceeded，please wait for existing tasks to complete before retrying"
            elif "1201" in error_msg:
                error_msg = "model not supported or parameter error，please check model_name and mode parameter"
            logger.error(f"❌ Kling Image-to-videofailure: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _wait_for_completion(self, task_id: str, query_path: str = None, max_wait: int = 600) -> Optional[str]:
        """Waiting for task completion"""
        import time
        if query_path is None:
            query_path = self.TEXT2VIDEO_QUERY_PATH
        start_time = time.monotonic()

        logger.info(f"⏳ wait Kling Task completed: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Task timeout ({max_wait}seconds)")
                return None

            try:
                token = self._get_token()
                response = await self.client.get(
                    f"{Config.KLING_BASE_URL}{query_path.format(task_id=task_id)}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                result = response.json()

                code = result.get("code")
                if code != 0:
                    logger.warning(f"⚠️ Query failed: {result.get('message')}")
                    await asyncio.sleep(5)
                    continue

                data = result.get("data", {})
                task_status = data.get("task_status")

                # Kling status: submitted, processing, succeed, failed
                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ Kling Task completed (elapsed time: {int(elapsed)}seconds)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "Unknown error")
                    logger.error(f"❌ Kling Task failed: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ Query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """Download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class KlingOmniClient:
    """
    Kling Omni-Video Generation Client (kling-v3-omni)
    Using /v1/videos/omni-video endpoint，supports image_list and multi_shot

    Features:
    - Text-to-video（3-15seconds）
    - Image-to-video（supports image_list Multi-reference images）
    - multi-shotvideo（multi_shot）
    - audio-video sync output（sound: on/off）
    """

    OMNI_VIDEO_PATH = "/v1/videos/omni-video"
    QUERY_PATH = "/v1/videos/omni-video/{task_id}"

    DEFAULT_MODEL = "kling-v3-omni"

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
            }
        )
        self._token = None
        self._token_expire = 0

    def _generate_token(self) -> str:
        """Generate JWT auth token"""
        import jwt
        import time

        now = int(time.time())
        payload = {
            "iss": Config.KLING_ACCESS_KEY,
            "iat": now,
            "exp": now + 3600,
            "nbf": now - 5
        }
        return jwt.encode(payload, Config.KLING_SECRET_KEY, algorithm="HS256")

    def _get_token(self) -> str:
        """Get valid token (with cache)"""
        import time
        if not self._token or time.time() > self._token_expire - 60:
            self._token = self._generate_token()
            self._token_expire = time.time() + 3600
        return self._token

    def _file_to_base64(self, file_path: str) -> str:
        """Convert file to pure base64 string (no data URI prefix)"""
        with open(file_path, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode('utf-8')

    async def create_omni_video(
        self,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        aspect_ratio: str = "9:16",
        sound: str = "on",
        image_list: List[str] = None,
        multi_shot: bool = False,
        shot_type: str = None,
        multi_prompt: List[Dict] = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        Omni-Video generate（supports image_list + multi_shot）

        Args:
            prompt: video description, can use <<<image_1>>> to reference images
            duration: duration (3-15 seconds)
            mode: std or pro
            aspect_ratio: aspect ratio (16:9, 9:16, 1:1)
            sound: on or off
            image_list: image path list，for character consistency
            multi_shot: whether multi-shot
            shot_type: intelligence（AI auto storyboarding）or customize（custom storyboarding）
            multi_prompt: custom storyboard shot list，format [{"index": 1, "prompt": "...", "duration": "3"}, ...]
            output: output file path
        """
        payload = {
            "model_name": self.DEFAULT_MODEL,
            "prompt": prompt,
            "negative_prompt": "",
            "duration": str(duration),
            "mode": mode,
            "sound": sound,
            "aspect_ratio": aspect_ratio
        }

        # process image_list（pure base64, without data URI prefix）
        if image_list:
            processed_images = []
            for img_path in image_list:
                if not os.path.exists(img_path):
                    logger.warning(f"⚠️ Reference image not found: {img_path}")
                    continue

                # Validate and resize image dimensions
                result = validate_and_resize_image(img_path)
                if not result["success"]:
                    logger.warning(f"⚠️ imageprocessfailure: {img_path}, {result.get('error')}")
                    continue

                processed_images.append({
                    "image_url": self._file_to_base64(result["output_path"])
                })

            payload["image_list"] = processed_images
            logger.info(f"📎 Using {len(processed_images)} reference images")

        # processmulti-shotparameter
        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt and shot_type == "customize":
                payload["multi_prompt"] = multi_prompt

        logger.info(f"📤 create Kling Omni-Video task: {prompt[:50]}...")

        try:
            token = self._get_token()
            response = await self.client.post(
                f"{Config.KLING_BASE_URL}{self.OMNI_VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API did not return task_id"}

            logger.info(f"✅ Omni-Video Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "concurrent task limit exceeded，please wait for existing tasks to complete before retrying"
            elif "1201" in error_msg:
                error_msg = "model not supported or parameter error"
            logger.error(f"❌ Kling Omni-Video failure: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """Waiting for task completion"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ wait Kling Omni-Video Task completed: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Task timeout ({max_wait}seconds)")
                return None

            try:
                token = self._get_token()
                response = await self.client.get(
                    f"{Config.KLING_BASE_URL}{self.QUERY_PATH.format(task_id=task_id)}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                result = response.json()

                code = result.get("code")
                if code != 0:
                    logger.warning(f"⚠️ Query failed: {result.get('message')}")
                    await asyncio.sleep(5)
                    continue

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ Omni-Video Task completed (elapsed time: {int(elapsed)}seconds)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "Unknown error")
                    logger.error(f"❌ Omni-Video Task failed: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ Query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """Download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class FalKlingClient:
    """
    Kling Video Generation Client (via fal.ai proxy)

    Fully consistent with official Kling API:
    - prompt writing is consistent
    - parameter fields are consistent(duration, aspect_ratio, generate_audio, etc.)
    - Image input method is consistent

    The only difference: Using --provider fal instead of --provider kling

    Supported features:
    - Text-to-video: only pass prompt
    - Single image generation: pass image_url
    - Multi-reference: pass image_urls list
    - First-last frame: pass image_url + tail_image_url
    """

    MODEL_ID = "fal-ai/kling-video/o3/pro/reference-to-video"

    def __init__(self):
        import fal_client
        import httpx
        self.fal_client = fal_client.AsyncClient(key=Config.FAL_API_KEY)
        self.http_client = httpx.AsyncClient(timeout=300.0)

    async def create_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        generate_audio: bool = True,
        image_url: str = None,        # First frame/single image
        image_urls: List[str] = None,  # Multi-reference images
        tail_image_url: str = None,    # last frame
        output: str = None
    ) -> Dict[str, Any]:
        """
        Unified video generation method

        Args:
            prompt: video description
            duration: duration (3-15 seconds)
            aspect_ratio: aspect ratio (16:9, 9:16, 1:1)
            generate_audio: whether to generate audio
            image_url: first frameimage（pathor URL）
            image_urls: reference imagelist（pathor URL）
            tail_image_url: last frameimage（pathor URL）
            output: output file path
        """
        payload = {
            "prompt": prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
            "generate_audio": generate_audio
        }

        # First frame/single image
        if image_url:
            payload["image_url"] = self._prepare_image_url(image_url)

        # Multi-reference images
        if image_urls:
            payload["image_urls"] = [self._prepare_image_url(img) for img in image_urls]

        # last frame
        if tail_image_url:
            payload["tail_image_url"] = self._prepare_image_url(tail_image_url)

        return await self._submit_and_wait(payload, output)

    def _prepare_image_url(self, image_path: str) -> str:
        """Prepare image URL (convert local file to data URI)"""
        if image_path.startswith(('http://', 'https://')):
            return image_path
        return self._file_to_data_uri(image_path)

    def _file_to_data_uri(self, file_path: str) -> str:
        """Convert local file to data URI format base64"""
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        with open(file_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/{ext};base64,{data}"

    async def _submit_and_wait(self, payload: dict, output: str = None) -> Dict[str, Any]:
        """Submit task and wait for completion"""
        import time

        logger.info(f"📤 create fal Kling task: {payload.get('prompt', '')[:50]}...")

        try:
            # Using fal_client to submit task, returns AsyncRequestHandle
            handle = await self.fal_client.submit(self.MODEL_ID, arguments=payload)
            request_id = handle.request_id
            logger.info(f"✅ fal task submitted: {request_id}")
        except Exception as e:
            logger.error(f"❌ fal task submission failed: {e}")
            return {"success": False, "error": str(e)}

        # waitcomplete
        video_url = await self._wait_for_completion(handle)

        if video_url and output:
            await self._download_file(video_url, output)
            return {"success": True, "video_url": video_url, "output": output, "request_id": request_id}

        return {"success": bool(video_url), "video_url": video_url, "request_id": request_id}

    async def _wait_for_completion(self, handle, max_wait: int = 600) -> Optional[str]:
        """Waiting for task completion"""
        import time

        logger.info(f"⏳ wait fal Task completed: {handle.request_id}")
        start_time = time.monotonic()

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ fal Task timeout ({max_wait}seconds)")
                return None

            try:
                # Using handle.status() checkstatus
                status = await handle.status()
                # status is an object, e.g., InProgress or Completed
                status_class = status.__class__.__name__
                logger.info(f"   [{int(elapsed)}s] status: {status_class}")

                if status_class == "Completed":
                    # Using handle.get() to get result
                    result = await handle.get()
                    video_url = result.get("video", {}).get("url")
                    if video_url:
                        logger.info(f"✅ fal Task completed (elapsed time: {int(elapsed)}seconds)")
                        return video_url
                    else:
                        logger.error(f"❌ fal No video URL in task result: {result}")
                        return None
                elif status_class == "Failed":
                    error = getattr(status, 'error', None) or "Unknown error"
                    logger.error(f"❌ fal Task failed: {error}")
                    return None
            except Exception as e:
                logger.warning(f"   Query status exception: {e}")

            await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """Download file"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        response = await self.http_client.get(url)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"✅ Saved to: {output_path}")

    async def close(self):
        await self.http_client.aclose()


class SunoClient:
    """Suno Music generation client"""

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        prompt: str,
        style: str = "Lo-fi, Chill",
        instrumental: bool = True,
        output: str = None
    ) -> Dict[str, Any]:
        """Generate music"""
        payload = {
            "prompt": prompt,
            "instrumental": instrumental,
            "model": Config.SUNO_MODEL,
            "customMode": True,
            "style": style,
            "callbackUrl": "https://example.com/callback"
        }

        # Truncate long prompt (to avoid excessive logs)，does not affect API parameters
        display_prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
        logger.info(f"📤 createmusicgeneratetask - description: {display_prompt}, style: {style}")

        try:
            response = await self.client.post(
                f"{Config.SUNO_API_URL}/generate",
                json=payload,
                headers={"Authorization": f"Bearer {Config.SUNO_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                return {"success": False, "error": result.get("msg", "Unknown error")}

            task_id = result["data"]["taskId"]
            logger.info(f"✅ Task created: {task_id}")

            audio_url = await self._wait_for_completion(task_id)

            if audio_url and output:
                await self._download_file(audio_url, output)
                return {"success": True, "audio_url": audio_url, "output": output}

            return {"success": True, "audio_url": audio_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ musicgeneratefailure: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 300) -> Optional[str]:
        """Waiting for task completion"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ waitmusicgenerate...")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Task timeout ({max_wait}seconds)")
                return None

            try:
                response = await self.client.get(
                    f"{Config.SUNO_API_URL}/generate/record-info?taskId={task_id}",
                    headers={"Authorization": f"Bearer {Config.SUNO_API_KEY}"}
                )
                response.raise_for_status()
                result = response.json()

                if result.get("code") != 200:
                    logger.warning(f"⚠️ Query failed: {result.get('msg')}")
                    await asyncio.sleep(5)
                    continue

                data = result.get("data", {})
                status = data.get("status")

                if status == "SUCCESS":
                    tracks = data.get("response", {}).get("sunoData", [])
                    if tracks:
                        audio_url = tracks[0].get("audioUrl")
                        logger.info(f"✅ Music generation completed (elapsed time: {int(elapsed)}seconds)")
                        return audio_url

                elif status == "FAILED":
                    logger.error("❌ musicgeneratefailure")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ Query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """Download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Volcengine TTS ==============

class TTSClient:
    """Volcano Engine TTS client"""

    API_URL = "https://openspeech.bytedance.com/api/v1/tts"

    VOICE_TYPES = {
        "female_narrator": "BV700_streaming",
        "female_gentle": "BV034_streaming",
        "male_narrator": "BV701_streaming",
        "male_warm": "BV033_streaming",
    }

    EMOTION_MAP = {
        "neutral": None,
        "happy": "happy",
        "sad": "sad",
        "gentle": "gentle",
        "serious": "serious",
    }

    async def synthesize(
        self,
        text: str,
        output: str,
        voice: str = "female_narrator",
        emotion: str = None,
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """Synthesize speech"""
        import httpx

        voice_type = self.VOICE_TYPES.get(voice, voice)

        payload = {
            "app": {
                "appid": Config.VOLCENGINE_TTS_APP_ID,
                "token": "access_token",
                "cluster": Config.VOLCENGINE_TTS_CLUSTER,
            },
            "user": {"uid": "vico_tts_user"},
            "audio": {
                "voice_type": voice_type,
                "encoding": "mp3",
                "rate": 24000,
                "speed_ratio": speed,
                "volume_ratio": 1.0,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "query",
            },
        }

        if emotion and emotion in self.EMOTION_MAP and self.EMOTION_MAP[emotion]:
            payload["audio"]["emotion"] = self.EMOTION_MAP[emotion]

        logger.info(f"📤 TTS synthesis: {text[:30]}...")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.API_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer;{Config.VOLCENGINE_TTS_TOKEN}",
                    }
                )
                response.raise_for_status()
                result = response.json()

            code = result.get("code", -1)
            if code != 3000:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            audio_data = base64.b64decode(result.get("data", ""))
            if not audio_data:
                return {"success": False, "error": "Empty audio data"}

            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, "wb") as f:
                f.write(audio_data)

            duration_ms = int(result.get("addition", {}).get("duration", "0"))
            logger.info(f"✅ TTS saved: {output} ({duration_ms}ms)")

            return {"success": True, "output": output, "duration_ms": duration_ms}

        except Exception as e:
            logger.error(f"❌ TTSfailure: {e}")
            return {"success": False, "error": str(e)}


# ============== Gemini Image generation（via Yunwu API）==============

class ImageClient:
    """Gemini Image generation client（via Yunwu API）"""

    STYLE_PRESETS = {
        "cinematic": "cinematic style, film grain, dramatic lighting, movie still",
        "realistic": "photorealistic, natural lighting, high detail, 8k",
        "anime": "anime style, vibrant colors, clean lines, studio ghibli inspired",
        "artistic": "artistic style, painterly, expressive brushstrokes, impressionist",
    }

    async def generate(
        self,
        prompt: str,
        output: str = None,
        style: str = "cinematic",
        aspect_ratio: str = "9:16",
        reference_images: List[str] = None
    ) -> Dict[str, Any]:
        """generateimage，supportsMulti-reference images"""
        import httpx

        style_suffix = self.STYLE_PRESETS.get(style, style)
        full_prompt = f"{prompt}, {style_suffix}"

        # Build parts array
        parts = []

        # Add reference images (Gemini gives more weight to the last reference image, so put important characters at the end)
        if reference_images:
            for ref_path in reference_images:
                if os.path.exists(ref_path):
                    with open(ref_path, 'rb') as f:
                        img_data = f.read()
                    ext = os.path.splitext(ref_path)[1].lower()
                    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
                    mime_type = mime_map.get(ext, 'image/jpeg')
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64.b64encode(img_data).decode('utf-8')
                        }
                    })

        # Add text prompt
        parts.append({"text": full_prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
                "responseMimeType": "text/plain",
            }
        }

        ref_info = f" (with {len(reference_images)} reference images)" if reference_images else ""
        logger.info(f"📤 Image generation{ref_info}: {prompt[:30]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    Config.GEMINI_IMAGE_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": Config.GEMINI_API_KEY,
                    }
                )
                response.raise_for_status()
                result = response.json()

            candidates = result.get("candidates", [])
            if not candidates:
                return {"success": False, "error": "No image generated"}

            parts = candidates[0].get("content", {}).get("parts", [])
            image_data = None
            for part in parts:
                if "inlineData" in part:
                    image_data = part["inlineData"].get("data")
                    break

            if not image_data:
                return {"success": False, "error": "No image data in response"}

            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                with open(output, "wb") as f:
                    f.write(base64.b64decode(image_data))
                logger.info(f"✅ Image saved: {output}")
                return {"success": True, "output": output}

            return {"success": True, "image_base64": image_data}

        except Exception as e:
            logger.error(f"❌ Image generationfailure: {e}")
            return {"success": False, "error": str(e)}


# ============== Character management (optional tool)==============

class PersonaManager:
    """
    Character persona manager (optional tool)

    Used to manage character reference images in projects.
    Only use when video involves characters，pure landscape/object videos don't need this。

    Usage:
        manager = PersonaManager(project_dir)
        manager.register("Xiaomei", "female", "path/to/reference.jpg", "long hair, round face, glasses")
        ref_path = manager.get_reference("Xiaomei")
    """

    def __init__(self, project_dir: str = None):
        self.project_dir = Path(project_dir) if project_dir else None
        self.personas = {}  # {persona_id: {name, gender, features, reference_image}}
        self._persona_file = None

        if self.project_dir:
            self._persona_file = self.project_dir / "personas.json"
            self._load()

    def _load(self):
        """Load character data from file"""
        if self._persona_file and self._persona_file.exists():
            try:
                with open(self._persona_file, "r", encoding="utf-8") as f:
                    self.personas = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ load personas.json failure: {e}")
                self.personas = {}

    def _save(self):
        """Save character data to file"""
        if self._persona_file:
            self._persona_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persona_file, "w", encoding="utf-8") as f:
                json.dump(self.personas, f, indent=2, ensure_ascii=False)

    def register(
        self,
        name: str,
        gender: str,
        reference_image: Optional[str] = None,
        features: str = ""
    ) -> str:
        """
        Register character persona

        Args:
            name: character name
            gender: gender (male/female)
            reference_image: Reference image path (can be None, supplemented in Phase 2)
            features: appearance feature description

        Returns:
            persona_id
        """
        # Generate unique ID
        persona_id = name.lower().replace(" ", "_")
        counter = 1
        original_id = persona_id
        while persona_id in self.personas:
            persona_id = f"{original_id}_{counter}"
            counter += 1

        self.personas[persona_id] = {
            "name": name,
            "gender": gender,
            "reference_image": reference_image,
            "features": features
        }

        self._save()
        if reference_image:
            logger.info(f"✅ Character registered: {name} (ID: {persona_id}, reference image: {reference_image})")
        else:
            logger.info(f"✅ Character registered: {name} (ID: {persona_id}, no reference image)")

        return persona_id

    def update_reference_image(self, persona_id: str, reference_image: str) -> bool:
        """
        updatecharacterreference image（Phase 2 Using）

        Args:
            persona_id: characterID
            reference_image: new reference image path

        Returns:
            Whether successful
        """
        if persona_id not in self.personas:
            logger.warning(f"⚠️ Character not found: {persona_id}")
            return False

        self.personas[persona_id]["reference_image"] = reference_image
        self._save()
        logger.info(f"✅ Updated {persona_id} reference image: {reference_image}")
        return True

    def has_reference_image(self, persona_id: str) -> bool:
        """Check if character has reference image"""
        persona = self.personas.get(persona_id)
        if persona:
            return bool(persona.get("reference_image"))
        return False

    def list_personas_without_reference(self) -> List[str]:
        """Return list of character IDs without reference images"""
        return [
            pid for pid, data in self.personas.items()
            if not data.get("reference_image")
        ]

    def get_reference(self, persona_id: str) -> Optional[str]:
        """Get character reference image path"""
        persona = self.personas.get(persona_id)
        if persona:
            return persona.get("reference_image")
        return None

    def get_features(self, persona_id: str) -> str:
        """
        Get character feature description (for prompt)

        Returns:
            features description string, e.g., "young woman with long hair, round face, glasses"
        """
        persona = self.personas.get(persona_id)
        if not persona:
            return ""

        parts = []

        # gender
        gender = persona.get("gender", "")
        if gender == "female":
            parts.append("woman")
        elif gender == "male":
            parts.append("man")

        # features
        features = persona.get("features", "")
        if features:
            parts.append(features)

        # Name as reference identifier
        name = persona.get("name", "")
        if name:
            return f"{', '.join(parts)} (reference: {name})"

        return ", ".join(parts)

    def get_persona_prompt(self, persona_id: str) -> str:
        """
        Get character prompt for Vidu/Gemini

        format: "Reference for {GENDER} ({name}): MUST preserve exact appearance - {features}"
        """
        persona = self.personas.get(persona_id)
        if not persona:
            return ""

        gender = persona.get("gender", "person")
        name = persona.get("name", "")
        features = persona.get("features", "")

        gender_upper = "WOMAN" if gender == "female" else "MAN" if gender == "male" else "PERSON"

        prompt = f"Reference for {gender_upper} ({name}): MUST preserve exact appearance"
        if features:
            prompt += f" - {features}"

        return prompt

    def list_personas(self) -> List[dict]:
        """List all characters"""
        return [
            {"id": pid, **pdata}
            for pid, pdata in self.personas.items()
        ]

    def export_for_storyboard(self) -> List[Dict[str, Any]]:
        """
        Export as storyboard.json compatible characters format

        Returns:
            List matching storyboard.json elements.characters format
        """
        characters = []
        for pid, pdata in self.personas.items():
            name = pdata.get("name", "")
            # Generate name_en(pinyin/English)
            name_en = pid.replace("_", " ").title().replace(" ", "")

            ref_image = pdata.get("reference_image")
            reference_images = [ref_image] if ref_image else []

            characters.append({
                "element_id": f"Element_{name_en}",
                "name": name,
                "name_en": name_en,
                "reference_images": reference_images,
                "visual_description": pdata.get("features", "")
            })

        return characters

    def get_character_image_mapping(self) -> Dict[str, str]:
        """
        generate character_image_mapping（used for storyboard.json）

        Returns:
            {Element_Name: image_1, ...}
        """
        mapping = {}
        for i, (pid, pdata) in enumerate(self.personas.items()):
            name_en = pid.replace("_", " ").title().replace(" ", "")
            element_id = f"Element_{name_en}"
            mapping[element_id] = f"image_{i + 1}"
        return mapping

    def has_personas(self) -> bool:
        """Whether any characters are registered"""
        return len(self.personas) > 0

    def remove(self, persona_id: str) -> bool:
        """Delete character"""
        if persona_id in self.personas:
            del self.personas[persona_id]
            self._save()
            return True
        return False

    def clear(self):
        """Clear all characters"""
        self.personas = {}
        self._save()


# ============== Multimodal image analysis (built-in Vision capability)==============

class VisionClient:
    """
    Multimodal image analysis client

    Fallback for non-multimodal models, supports Kimi K2.5, GPT-4o and other vision models.
    Using Anthropic API compatibleformat。

    Usage:
        client = VisionClient()
        result = await client.analyze_image("path/to/image.jpg", "Describe this image")
        results = await client.analyze_batch(["img1.jpg", "img2.jpg"])
    """

    # Supported image formats
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(timeout=60.0)

    async def analyze_image(
        self,
        image_path: str,
        prompt: str = "Please describe this image in detail, including scene, subject, colors, atmosphere, etc.",
    ) -> Dict[str, Any]:
        """Analyze single image"""
        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image not found: {image_path}"}

        # Read and encode image
        with open(image_path, 'rb') as f:
            image_data = f.read()

        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp'
        }
        media_type = mime_map.get(ext, 'image/jpeg')

        base64_image = base64.b64encode(image_data).decode('utf-8')

        # Get configuration
        api_key = Config.get("VISION_API_KEY", "")
        base_url = Config.get("VISION_BASE_URL", "https://coding.dashscope.aliyuncs.com/apps/anthropic")
        model = Config.get("VISION_MODEL", "kimi-k2.5")

        if not api_key:
            return {"success": False, "error": "VISION_API_KEY not configured"}

        # Build API request (Anthropic API compatible format)
        payload = {
            "model": model,
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        try:
            response = await self.client.post(
                f"{base_url}/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                },
                json=payload
            )

            if response.status_code != 200:
                error_text = response.text
                return {
                    "success": False,
                    "error": f"API error {response.status_code}: {error_text[:200]}"
                }

            result = response.json()

            # Extract response text
            content = result.get("content", [])
            description = None
            for item in content:
                if item.get("type") == "text":
                    description = item.get("text", "")
                    break

            if not description:
                description = "Unable to parse response"

            return {
                "success": True,
                "image_path": image_path,
                "description": description
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def analyze_batch(
        self,
        image_paths: List[str],
        prompt: str = "Please describe this image in detail, including scene, subject, colors, atmosphere, etc."
    ) -> List[Dict[str, Any]]:
        """Batch analyze multiple images"""
        results = []
        for path in image_paths:
            result = await self.analyze_image(path, prompt)
            results.append(result)
        return results

    async def close(self):
        await self.client.aclose()


# ============== Command Line Entry ==============

async def cmd_vision(args):
    """Image analysis command"""
    api_key = Config.get("VISION_API_KEY", "")
    if not api_key:
        print(json.dumps({
            "success": False,
            "error": "VISION_API_KEY not configured",
            "hint": "Please add in config.json VISION_API_KEY",
            "config_file": str(CONFIG_FILE)
        }, indent=2, ensure_ascii=False))
        return 1

    client = VisionClient()
    try:
        if args.batch:
            # Batch analyze directory
            directory = Path(args.image)
            if not directory.is_dir():
                print(json.dumps({
                    "success": False,
                    "error": f"Directory not found: {args.image}"
                }, indent=2, ensure_ascii=False))
                return 1

            image_files = []
            for ext in VisionClient.SUPPORTED_FORMATS:
                image_files.extend(directory.glob(f"*{ext}"))
                image_files.extend(directory.glob(f"*{ext.upper()}"))

            if not image_files:
                print(json.dumps({
                    "success": False,
                    "error": f"No image files found in directory: {args.image}"
                }, indent=2, ensure_ascii=False))
                return 1

            logger.info(f"Found {len(image_files)} images, starting analysis...")
            results = await client.analyze_batch(
                [str(f) for f in sorted(image_files)],
                args.prompt
            )

            output = {"success": True, "total": len(results), "results": []}
            for r in results:
                if r.get("success"):
                    output["results"].append({
                        "image": r.get("image_path"),
                        "description": r.get("description")
                    })
                else:
                    output["results"].append({
                        "image": r.get("image_path", "unknown"),
                        "error": r.get("error")
                    })

            print(json.dumps(output, indent=2, ensure_ascii=False))
            return 0
        else:
            # Single image analysis
            result = await client.analyze_image(args.image, args.prompt)
            if result.get("success"):
                output = {
                    "success": True,
                    "image": args.image,
                    "analysis": result.get("description")
                }
                print(json.dumps(output, indent=2, ensure_ascii=False))
                return 0
            else:
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 1
    finally:
        await client.close()


# ============== Command Line Entry ==============

async def cmd_video(args):
    """Video Generationcommand"""
    provider = getattr(args, 'provider', None)
    backend = getattr(args, 'backend', 'kling')

    # Provider auto-selection logic (if user doesn't specify)
    if provider is None:
        if backend == 'vidu':
            provider = 'yunwu'  # vidu only has yunwu provider
        elif Config.KLING_ACCESS_KEY and Config.KLING_SECRET_KEY:
            provider = 'official'  # Prefer official API
        elif Config.YUNWU_API_KEY:
            provider = 'yunwu'  # Then use yunwu
        elif Config.FAL_API_KEY:
            provider = 'fal'  # Finally use fal
        else:
            provider = 'official'  # Default, will error with config prompt

    logger.info(f"🔧 Using provider: {provider}, backend: {backend}")

    # Priority: CLI > storyboard.json > default value
    aspect_ratio = args.aspect_ratio
    if aspect_ratio is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect_ratio = get_aspect_from_storyboard(args.storyboard)
        if aspect_ratio:
            logger.info(f"📐 Read aspect ratio from storyboard.json: {aspect_ratio}")
    if aspect_ratio is None:
        aspect_ratio = "9:16"  # final default value
        logger.info(f"📐 Usingdefaultaspect ratio: {aspect_ratio}")

    # ==================== fal.ai provider ====================
    # fal uses unified Kling model, parameters and prompt format same as official
    if provider == 'fal':
        if not Config.FAL_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "FAL_API_KEY not configured",
                "hint": "Please add in config.json FAL_API_KEY",
                "get_key": "Visit https://fal.ai to get API key"
            }, indent=2, ensure_ascii=False))
            return 1

        client = FalKlingClient()
        try:
            generate_audio = args.audio if hasattr(args, 'audio') else False
            duration = max(3, min(15, args.duration))

            result = await client.create_video(
                prompt=args.prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                generate_audio=generate_audio,
                image_url=args.image if args.image else None,
                image_urls=getattr(args, 'image_list', None),
                tail_image_url=getattr(args, 'tail_image', None),
                output=args.output
            )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"error: {result.get('error')}")
                return 1
        finally:
            await client.close()

    # ==================== kling provider (official API or yunwu) ====================
    # BackendRouter: Force switch based on functional requirements（image-list only supported by omni，tail-image only supported by kling）
    image_list = getattr(args, 'image_list', None)
    tail_image = getattr(args, 'tail_image', None)
    if image_list and backend != 'kling-omni':
        backend = 'kling-omni'
        logger.info("🔀 Detected --image-list, auto-switching to kling-omni backend")
    elif tail_image and backend != 'kling':
        backend = 'kling'
        logger.info("🔀 Detected --tail-image, auto-switching to kling backend")

    # ==================== yunwu provider ====================
    if provider == 'yunwu':
        if not Config.YUNWU_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "YUNWU_API_KEY not configured",
                "hint": "Please add in config.json YUNWU_API_KEY",
                "get_key": "Visit https://yunwu.ai to register and get API key"
            }, indent=2, ensure_ascii=False))
            return 1

        audio = args.audio if hasattr(args, 'audio') else False
        duration = max(3, min(15, args.duration))

        # processmulti-shotparameter
        multi_shot = getattr(args, 'multi_shot', False)
        shot_type = getattr(args, 'shot_type', None)
        multi_prompt = None
        if getattr(args, 'multi_prompt', None):
            try:
                multi_prompt = json.loads(args.multi_prompt)
            except json.JSONDecodeError:
                print(json.dumps({
                    "success": False,
                    "error": "multi_prompt JSON parsing failed"
                }, indent=2, ensure_ascii=False))
                return 1

        if backend == 'kling-omni':
            client = YunwuKlingOmniClient()
            try:
                image_list = getattr(args, 'image_list', None)
                result = await client.create_omni_video(
                    prompt=args.prompt,
                    duration=duration,
                    mode=args.mode if hasattr(args, 'mode') else "std",
                    aspect_ratio=aspect_ratio,
                    audio=audio,
                    image_list=image_list,
                    multi_shot=multi_shot,
                    shot_type=shot_type,
                    multi_prompt=multi_prompt,
                    output=args.output
                )
            finally:
                await client.close()
        else:
            # kling backend
            client = YunwuKlingClient()
            try:
                if args.image:
                    result = await client.create_image2video(
                        image_path=args.image,
                        prompt=args.prompt,
                        duration=duration,
                        mode=args.mode if hasattr(args, 'mode') else "std",
                        audio=audio,
                        image_tail=getattr(args, 'tail_image', None),
                        output=args.output
                    )
                else:
                    result = await client.create_text2video(
                        prompt=args.prompt,
                        duration=duration,
                        mode=args.mode if hasattr(args, 'mode') else "std",
                        aspect_ratio=aspect_ratio,
                        audio=audio,
                        multi_shot=multi_shot,
                        shot_type=shot_type,
                        multi_prompt=multi_prompt,
                        output=args.output
                    )
            finally:
                await client.close()

        if result.get("success"):
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        else:
            print(f"error: {result.get('error')}")
            return 1

    # ==================== official provider (official API) ====================
    # Check API key for corresponding backend
    if backend == 'kling':
        if not Config.KLING_ACCESS_KEY or not Config.KLING_SECRET_KEY:
            print(json.dumps({
                "success": False,
                "error": "Kling API credentialsnot configured",
                "hint": "Please add in config.json KLING_ACCESS_KEY and KLING_SECRET_KEY",
                "get_key": "Visit https://klingai.kuaishou.com to get API credentials"
            }, indent=2, ensure_ascii=False))
            return 1

        client = KlingClient()
        try:
            # Kling parameterconvert：audio -> sound
            sound = "on" if args.audio else "off"
            # Kling duration range: 3-15s
            duration = max(3, min(15, args.duration))

            # processmulti-shotparameter
            multi_shot = getattr(args, 'multi_shot', False)
            shot_type = getattr(args, 'shot_type', None)
            multi_prompt = None
            if getattr(args, 'multi_prompt', None):
                try:
                    multi_prompt = json.loads(args.multi_prompt)
                except json.JSONDecodeError:
                    print(json.dumps({
                        "success": False,
                        "error": "multi_prompt JSON parsing failed"
                    }, indent=2, ensure_ascii=False))
                    return 1

            if args.image:
                result = await client.create_image2video(
                    image_path=args.image,
                    prompt=args.prompt,
                    duration=duration,
                    mode=args.mode if hasattr(args, 'mode') else "std",
                    sound=sound,
                    tail_image_path=getattr(args, 'tail_image', None),
                    output=args.output,
                    multi_shot=multi_shot,
                    shot_type=shot_type,
                    multi_prompt=multi_prompt
                )
            else:
                result = await client.create_text2video(
                    prompt=args.prompt,
                    duration=duration,
                    mode=args.mode if hasattr(args, 'mode') else "std",
                    aspect_ratio=aspect_ratio,
                    sound=sound,
                    multi_shot=multi_shot,
                    shot_type=shot_type,
                    multi_prompt=multi_prompt,
                    output=args.output
                )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"error: {result.get('error')}")
                return 1
        finally:
            await client.close()

    elif backend == 'kling-omni':
        if not Config.KLING_ACCESS_KEY or not Config.KLING_SECRET_KEY:
            print(json.dumps({
                "success": False,
                "error": "Kling API credentialsnot configured",
                "hint": "Please add in config.json KLING_ACCESS_KEY and KLING_SECRET_KEY",
                "get_key": "Visit https://klingai.kuaishou.com to get API credentials"
            }, indent=2, ensure_ascii=False))
            return 1

        client = KlingOmniClient()
        try:
            sound = "on" if args.audio else "off"
            duration = max(3, min(15, args.duration))

            multi_shot = getattr(args, 'multi_shot', False)
            shot_type = getattr(args, 'shot_type', None)
            multi_prompt = None
            if getattr(args, 'multi_prompt', None):
                try:
                    multi_prompt = json.loads(args.multi_prompt)
                except json.JSONDecodeError:
                    print(json.dumps({
                        "success": False,
                        "error": "multi_prompt JSON parsing failed"
                    }, indent=2, ensure_ascii=False))
                    return 1

            image_list = getattr(args, 'image_list', None)

            result = await client.create_omni_video(
                prompt=args.prompt,
                duration=duration,
                mode=args.mode if hasattr(args, 'mode') else "std",
                aspect_ratio=aspect_ratio,
                sound=sound,
                image_list=image_list,
                multi_shot=multi_shot,
                shot_type=shot_type,
                multi_prompt=multi_prompt,
                output=args.output
            )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"error: {result.get('error')}")
                return 1
        finally:
            await client.close()

    else:
        # Vidu (Yunwu) backend
        if not Config.YUNWU_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "YUNWU_API_KEY not configured",
                "hint": "Please set environment variable: export YUNWU_API_KEY='your-api-key'",
                "get_key": "Visit https://yunwu.ai to register and get API key"
            }, indent=2, ensure_ascii=False))
            return 1

        client = ViduClient()
        try:
            if args.image:
                result = await client.create_img2video(
                    image_path=args.image,
                    prompt=args.prompt,
                    duration=args.duration,
                    resolution=args.resolution,
                    audio=args.audio,
                    output=args.output
                )
            else:
                result = await client.create_text2video(
                    prompt=args.prompt,
                    duration=args.duration,
                    aspect_ratio=aspect_ratio,
                    audio=args.audio,
                    output=args.output
                )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"error: {result.get('error')}")
                return 1
        finally:
            await client.close()


async def cmd_music(args):
    """musicgeneratecommand"""
    # Priority: CLI > creative.json > error
    prompt = args.prompt
    style = args.style

    # Read prompt and style from creative.json
    if hasattr(args, 'creative') and args.creative:
        config = get_music_config_from_creative(args.creative)
        if config:
            if prompt is None:
                prompt = config.get("prompt")
                if prompt:
                    logger.info(f"🎵 Read music description from creative.json: {prompt[:50]}...")
            if style is None:
                style = config.get("style")
                if style:
                    logger.info(f"🎵 Read music style from creative.json: {style}")

    # prompt mustprovide
    if prompt is None:
        print(json.dumps({
            "success": False,
            "error": "Music description is required",
            "hint": "Please use --prompt or --creative parameter to provide music description"
        }, indent=2, ensure_ascii=False))
        return 1

    # style mustprovide
    if style is None:
        print(json.dumps({
            "success": False,
            "error": "Music style is required",
            "hint": "Please use --style or --creative parameter to provide music style"
        }, indent=2, ensure_ascii=False))
        return 1

    if not Config.SUNO_API_KEY:
        print(json.dumps({
            "success": False,
            "error": "SUNO_API_KEY not configured",
            "hint": "Please set environment variable: export SUNO_API_KEY='your-api-key'",
            "get_key": "Visit https://sunoapi.org to get API key"
        }, indent=2, ensure_ascii=False))
        return 1

    client = SunoClient()
    try:
        result = await client.generate(
            prompt=prompt,
            style=style,
            instrumental=args.instrumental,
            output=args.output
        )

        if result.get("success"):
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        else:
            print(f"error: {result.get('error')}")
            return 1
    finally:
        await client.close()


async def cmd_tts(args):
    """TTS synthesiscommand"""
    if not Config.VOLCENGINE_TTS_APP_ID or not Config.VOLCENGINE_TTS_TOKEN:
        print(json.dumps({
            "success": False,
            "error": "Volcengine TTS credentials not configured",
            "hint": "Please set environment variable:\n  export VOLCENGINE_TTS_APP_ID='your-app-id'\n  export VOLCENGINE_TTS_ACCESS_TOKEN='your-token'",
            "get_key": "Visit https://www.volcengine.com/docs/656/79823 to get credentials"
        }, indent=2, ensure_ascii=False))
        return 1

    client = TTSClient()
    result = await client.synthesize(
        text=args.text,
        output=args.output,
        voice=args.voice,
        emotion=args.emotion,
        speed=args.speed
    )

    if result.get("success"):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    else:
        print(f"error: {result.get('error')}")
        return 1


async def cmd_image(args):
    """Image generationcommand"""
    # Priority: CLI > storyboard.json > default value
    aspect_ratio = args.aspect_ratio
    if aspect_ratio is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect_ratio = get_aspect_from_storyboard(args.storyboard)
        if aspect_ratio:
            logger.info(f"📐 Read aspect ratio from storyboard.json: {aspect_ratio}")
    if aspect_ratio is None:
        aspect_ratio = "9:16"  # final default value
        logger.info(f"📐 Usingdefaultaspect ratio: {aspect_ratio}")

    if not Config.GEMINI_API_KEY:
        print(json.dumps({
            "success": False,
            "error": "YUNWU_API_KEY not configured（used for Gemini Image generation）",
            "hint": "Please set environment variable: export YUNWU_API_KEY='your-api-key'",
            "get_key": "Visit https://yunwu.ai to register and get API key"
        }, indent=2, ensure_ascii=False))
        return 1

    client = ImageClient()
    result = await client.generate(
        prompt=args.prompt,
        output=args.output,
        style=args.style,
        aspect_ratio=aspect_ratio,
        reference_images=args.reference
    )

    if result.get("success"):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    else:
        print(f"error: {result.get('error')}")
        return 1


async def cmd_check(args):
    """Environment check command"""
    import shutil
    import platform

    results = {
        "ready": True,
        "checks": {},
        "missing": [],
        "api_keys": {},
        "hints": []
    }

    # Python version
    py_ver = platform.python_version()
    py_ok = sys.version_info >= (3, 9)
    results["checks"]["python"] = {"version": py_ver, "ok": py_ok}
    if not py_ok:
        results["ready"] = False
        results["missing"].append(f"Python 3.9+ required (got {py_ver})")

    # FFmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    results["checks"]["ffmpeg"] = {
        "installed": ffmpeg_path is not None,
        "ffmpeg_path": ffmpeg_path,
        "ffprobe_path": ffprobe_path
    }
    if not ffmpeg_path:
        results["ready"] = False
        results["missing"].append("FFmpeg not found in PATH")
        results["hints"].append("Install FFmpeg: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)")

    # httpx
    try:
        import httpx
        results["checks"]["httpx"] = {"installed": True, "version": httpx.__version__}
    except ImportError:
        results["checks"]["httpx"] = {"installed": False}
        results["ready"] = False
        results["missing"].append("httpx not installed")
        results["hints"].append("Install httpx: pip install httpx")

    # Environment variables (informational only)
    env_vars = {
        "YUNWU_API_KEY": {
            "value": Config.YUNWU_API_KEY,
            "purpose": "Vidu Video Generation + Gemini Image generation",
            "get_key": "https://yunwu.ai"
        },
        "KLING_ACCESS_KEY": {
            "value": Config.KLING_ACCESS_KEY,
            "purpose": "Kling Video Generation Access Key",
            "get_key": "https://klingai.kuaishou.com"
        },
        "KLING_SECRET_KEY": {
            "value": Config.KLING_SECRET_KEY,
            "purpose": "Kling Video Generation Secret Key",
            "get_key": "https://klingai.kuaishou.com"
        },
        "FAL_API_KEY": {
            "value": Config.FAL_API_KEY,
            "purpose": "fal.ai Kling Video Generation proxy (bypass official concurrency limits)",
            "get_key": "https://fal.ai"
        },
        "SUNO_API_KEY": {
            "value": Config.SUNO_API_KEY,
            "purpose": "Suno musicgenerate",
            "get_key": "https://sunoapi.org"
        },
        "VOLCENGINE_TTS_APP_ID": {
            "value": Config.VOLCENGINE_TTS_APP_ID,
            "purpose": "Volcano Engine TTS App ID",
            "get_key": "https://www.volcengine.com/docs/656/79823"
        },
        "VOLCENGINE_TTS_ACCESS_TOKEN": {
            "value": Config.VOLCENGINE_TTS_TOKEN,
            "purpose": "Volcano Engine TTS Access Token",
            "get_key": "https://www.volcengine.com/docs/656/79823"
        },
    }

    for name, info in env_vars.items():
        is_set = bool(info["value"])
        masked = f"{info['value'][:4]}***" if is_set else "not set"
        results["api_keys"][name] = {
            "set": is_set,
            "masked_value": masked,
            "purpose": info["purpose"],
            "get_key_url": info["get_key"]
        }

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results["ready"] else 1


def main():
    parser = argparse.ArgumentParser(
        description="Vico Tools - Video Creation API Command Line Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Check sub-command
    subparsers.add_parser("check", help="Check environment dependencies and config")

    # Video sub-command
    video_parser = subparsers.add_parser("video", help="generatevideo")
    video_parser.add_argument("--image", "-i", help="inputimage pathorURL（Image-to-video）")
    video_parser.add_argument("--prompt", "-p", required=True, help="video description")
    video_parser.add_argument("--duration", "-d", type=int, default=5, help="duration(seconds)")
    video_parser.add_argument("--resolution", "-r", default="720p", help="Resolution")
    video_parser.add_argument("--aspect-ratio", "-a", default=None, help="aspect ratio (e.g., 16:9, 9:16)")
    video_parser.add_argument("--storyboard", "-s", help="storyboard.json path, auto-read aspect_ratio")
    video_parser.add_argument("--audio", action="store_true", help="Generate native audio")
    video_parser.add_argument("--output", "-o", help="output file path")
    video_parser.add_argument("--provider", choices=["official", "yunwu", "fal"], default=None,
                              help="API provider (auto-selected by default; vidu only supports yunwu)")
    video_parser.add_argument("--backend", "-b", choices=["vidu", "kling", "kling-omni"], default="kling",
                              help="Video generation backend (default kling; vidu as fallback; kling-omni for reference images")
    video_parser.add_argument("--mode", "-m", choices=["std", "pro"], default="std",
                              help="Generation mode (Kling only: std or pro)")
    video_parser.add_argument("--multi-shot", action="store_true",
                              help="Enable Kling multi-shot mode")
    video_parser.add_argument("--shot-type", choices=["intelligence", "customize"],
                              help="Multi-shot storyboard type (intelligence: AI auto, customize: custom)")
    video_parser.add_argument("--multi-prompt", type=str,
                              help="Multi-shot prompt list (JSON format)")
    video_parser.add_argument("--tail-image", type=str,
                              help="last frameimage path（used forfirst/last frame control）")
    video_parser.add_argument("--image-list", nargs="+",
                              help="Omni-Video Multi-reference imagespathlist（kling-omni only）")

    # Music sub-command
    music_parser = subparsers.add_parser("music", help="Generate music")
    music_parser.add_argument("--prompt", "-p", default=None, help="Music description (auto-read from creative.json)")
    music_parser.add_argument("--style", "-s", default=None, help="Music style (auto-read from creative.json)")
    music_parser.add_argument("--creative", "-c", help="creative.json path, auto-read prompt and style")
    music_parser.add_argument("--no-instrumental", dest="instrumental", action="store_false", help="Include vocals (default instrumental)")
    music_parser.set_defaults(instrumental=True)
    music_parser.add_argument("--output", "-o", help="output file path")

    # TTS sub-command
    tts_parser = subparsers.add_parser("tts", help="generatespeech")
    tts_parser.add_argument("--text", "-t", required=True, help="Text to synthesize")
    tts_parser.add_argument("--output", "-o", required=True, help="output file path")
    tts_parser.add_argument("--voice", "-v", default="female_narrator",
                           choices=["female_narrator", "female_gentle", "male_narrator", "male_warm"],
                           help="Voice")
    tts_parser.add_argument("--emotion", "-e", choices=["neutral", "happy", "sad", "gentle", "serious"],
                           help="Emotion")
    tts_parser.add_argument("--speed", type=float, default=1.0, help="Speech speed")

    # Image sub-command
    image_parser = subparsers.add_parser("image", help="generateimage")
    image_parser.add_argument("--prompt", "-p", required=True, help="Image description")
    image_parser.add_argument("--output", "-o", help="output file path")
    image_parser.add_argument("--style", "-s", default="cinematic",
                              help="Style (free text, e.g. cinematic, watercolor illustration, etc.)")
    image_parser.add_argument("--aspect-ratio", "-a", default=None, help="aspect ratio")
    image_parser.add_argument("--storyboard", help="storyboard.json path, auto-read aspect_ratio")
    image_parser.add_argument("--reference", "-r", nargs="+", help="Reference image paths (supports multiple, put important characters at the end)")

    # Vision sub-command (built-in multimodal analysis)
    vision_parser = subparsers.add_parser("vision", help="Analyze image content")
    vision_parser.add_argument("image", help="image pathordirectory")
    vision_parser.add_argument("--batch", "-b", action="store_true", help="Batch analyze images in directory")
    vision_parser.add_argument("--prompt", "-p", default="Please describe this image in detail, including scene, subject, colors, atmosphere, etc.", help="Analysis prompt")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run corresponding command
    commands = {
        "check": cmd_check,
        "video": cmd_video,
        "music": cmd_music,
        "tts": cmd_tts,
        "image": cmd_image,
        "vision": cmd_vision,
    }

    return asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    sys.exit(main())