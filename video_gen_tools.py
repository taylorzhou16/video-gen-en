#!/usr/bin/env python3
"""
Vico Tools - Video Creation API Command-Line Toolset

Usage:
  python video_gen_tools.py setup                                          # Interactive API provider configuration
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

# Set up logging
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
        image_path: Image path
        output_path: Output path (auto-generated if None)
        min_size: Minimum dimension limit (images smaller than this will be enlarged)
        max_size: Maximum dimension limit (images larger than this will be shrunk)
        target_size: Target size (used when enlarging)

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
        logger.warning("PIL not installed, skipping image size check")
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
            logger.info(f"Image size too small {w}x{h}, needs to be enlarged to at least {min_size}px")
        elif max_dim > max_size:
            scale = max_size / max_dim
            need_resize = True
            logger.info(f"Image size too large {w}x{h}, needs to be shrunk to at most {max_size}px")

        if need_resize:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)

            if output_path is None:
                base, ext = os.path.splitext(image_path)
                output_path = f"{base}_resized{ext}"

            img_resized.save(output_path, quality=95)
            logger.info(f"Image size adjusted: {w}x{h} -> {new_w}x{new_h}")

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
        logger.error(f"Image size processing failed: {e}")
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
    """Load config from config file and environment variables (config file takes priority)"""

    _cached_config = None

    @classmethod
    def _get_config(cls) -> Dict[str, str]:
        if cls._cached_config is None:
            cls._cached_config = load_config()
        return cls._cached_config

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """Get from config file first, then environment variable"""
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
    SUNO_MODEL: str = os.getenv("SUNO_MODEL", "V4_5")

    # Volcengine TTS
    @property
    def VOLCENGINE_TTS_APP_ID(self) -> str:
        return self.get("VOLCENGINE_TTS_APP_ID", "")

    @property
    def VOLCENGINE_TTS_TOKEN(self) -> str:
        return self.get("VOLCENGINE_TTS_ACCESS_TOKEN", "")

    VOLCENGINE_TTS_CLUSTER: str = os.getenv("VOLCENGINE_TTS_CLUSTER", "volcano_tts")

    # Gemini Image (via Yunwu API, shares YUNWU_API_KEY)
    @property
    def GEMINI_API_KEY(self) -> str:
        return self.get("YUNWU_API_KEY", "")

    GEMINI_IMAGE_URL: str = "https://yunwu.ai/v1beta/models/gemini-3.1-flash-image-preview:generateContent"

    # Compass API
    @property
    def COMPASS_API_KEY(self) -> str:
        return self.get("COMPASS_API_KEY", "")

    COMPASS_IMAGE_URL: str = "https://compass.llm.shopee.io/compass-api/v1/publishers/google/models/gemini-3.1-flash-image-preview:generateContent"
    COMPASS_VIDEO_URL: str = "https://compass.llm.shopee.io/compass-api/v1/publishers/google/models/veo-3.1-generate-001"

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

    # Seedance API (via piapi)
    @property
    def SEEDANCE_API_KEY(self) -> str:
        return self.get("SEEDANCE_API_KEY", "")

    SEEDANCE_BASE_URL: str = "https://api.piapi.ai"
    SEEDANCE_MODEL: str = "seedance-2-fast"  # or seedance-2 (high quality)


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


def load_storyboard(storyboard_path: str) -> Optional[Dict[str, Any]]:
    """Load storyboard.json"""
    try:
        with open(storyboard_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Unable to load storyboard: {e}")
        return None


# ============== Storyboard Validation ==============

VALID_ASPECT_RATIOS = ["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]

MODE_BACKEND_MAP = {
    "seedance-video": "seedance",
    "omni-video": "kling-omni",
    "img2video": "kling",
    "text2video": "kling",
    "veo3-text2video": "veo3",
    "veo3-img2video": "veo3",
}

BACKEND_PROVIDER_KEYS = {
    "seedance": ["SEEDANCE_API_KEY"],
    "kling": ["KLING_ACCESS_KEY", "FAL_API_KEY"],
    "kling-omni": ["KLING_ACCESS_KEY", "FAL_API_KEY"],
    "veo3": ["COMPASS_API_KEY"],
}


def validate_storyboard(storyboard_path: str) -> Dict[str, Any]:
    """�� storyboard.json， {valid, errors, warnings}"""
    errors = []
    warnings = []

    data = load_storyboard(storyboard_path)
    if data is None:
        return {"valid": False, "errors": [f"Cannot load file: {storyboard_path}"], "warnings": []}

    # --- Schema basics ---
    if "scenes" not in data or not isinstance(data.get("scenes"), list):
        errors.append("Missing scenes array")
    if "aspect_ratio" not in data:
        errors.append("Missing�� aspect_ratio field")
    elif data["aspect_ratio"] not in VALID_ASPECT_RATIOS:
        errors.append(f"aspect_ratio '{data['aspect_ratio']}' invalid, supported: {VALID_ASPECT_RATIOS}")

    scenes = data.get("scenes", [])
    if not scenes:
        errors.append("scenes array is empty")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    # --- Collect element IDs ---
    characters = data.get("elements", {}).get("characters", [])
    known_element_ids = {c.get("element_id") for c in characters if c.get("element_id")}

    # --- Validate each Scene ---
    for scene in scenes:
        scene_id = scene.get("scene_id", "unknown")
        shots = scene.get("shots", [])
        if not shots:
            warnings.append(f"[{scene_id}] No shots")
            continue

        # Collect each shotbackend info
        seedance_shots = []
        for shot in shots:
            shot_id = shot.get("shot_id", "unknown")
            duration = shot.get("duration")
            backend = shot.get("generation_backend", "")
            mode = shot.get("generation_mode", "")

            # Duration check
            if duration is None:
                errors.append(f"[{shot_id}] Missing��� duration")
                continue

            # Backend-mode consistency
            expected_backend = MODE_BACKEND_MAP.get(mode)
            if expected_backend and expected_backend != backend:
                errors.append(
                    f"[{shot_id}] generation_mode '{mode}' should use backend '{expected_backend}'，"
                    f"but got '{backend}'"
                )

            # by backend typeValidate duration
            if backend in ("kling", "kling-omni"):
                if duration < 3 or duration > 15:
                    errors.append(f"[{shot_id}] Kling duration must be 3-15s，current {duration}s")
            elif backend == "veo3":
                if duration not in [4, 6, 8]:
                    errors.append(f"[{shot_id}] Veo3 duration must be 4/6/8s，current {duration}s")

            # Collect Seedance shots (will aggregate by scene)
            if backend == "seedance":
                seedance_shots.append(shot)

            # Check reference image existence
            for ref in shot.get("reference_images", []):
                if ref and not os.path.exists(ref):
                    warnings.append(f"[{shot_id}] ��: {ref}")

            # video_prompt must exist
            if not shot.get("video_prompt"):
                warnings.append(f"[{shot_id}] Missing video_prompt")

            # Character reference check
            for char in shot.get("characters", []):
                char_id = char if isinstance(char, str) else char.get("element_id", "")
                if char_id and char_id not in known_element_ids:
                    warnings.append(f"[{shot_id}] Referenced unregistered character: {char_id}")

        # --- Seedance scene total duration validation ---
        if seedance_shots:
            scene_total_duration = sum(s.get("duration", 0) for s in seedance_shots)
            if scene_total_duration < 4 or scene_total_duration > 15:
                errors.append(
                    f"[{scene_id}] Seedance scene Total duration must be in 4-15s range，current {scene_total_duration}s"
                )

    # --- Provider availability ---
    used_backends = set()
    for scene in scenes:
        for shot in scene.get("shots", []):
            b = shot.get("generation_backend")
            if b:
                used_backends.add(b)

    for backend in used_backends:
        required_keys = BACKEND_PROVIDER_KEYS.get(backend, [])
        if required_keys and not any(getattr(Config, k, "") for k in required_keys):
            warnings.append(f"backend '{backend}' No available API key（requires: {' or '.join(required_keys)}）")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# ============== Seedance Prompt Auto-Assembly ==============

def build_seedance_prompt(scene: Dict[str, Any], storyboard: Dict[str, Any], storyboard_path: str = None) -> tuple:
    """
    Auto-assemble Seedance time-segmented prompt based on storyboard scene.

    Args:
        scene: scene object
        storyboard: complete storyboard object
        storyboard_path: storyboard.json file path (for calculating absolute paths)

    Returns:
        (prompt: str, image_urls: list[str], duration: int)
    """
    scene_id = scene.get("scene_id", "scene_1")
    shots = scene.get("shots", [])
    aspect_ratio = storyboard.get("aspect_ratio", "16:9")

    # Calculate storyboard directory (for converting relative paths to absolute paths)
    project_dir = None
    if storyboard_path:
        project_dir = os.path.dirname(os.path.dirname(storyboard_path))  # parent directory of storyboard/

    def resolve_path(path: str) -> str:
        """Convert relative path to absolute path"""
        if not path or path.startswith(('http://', 'https://')):
            return path
        if os.path.isabs(path):
            return path
        if project_dir:
            abs_path = os.path.join(project_dir, path)
            if os.path.exists(abs_path):
                return abs_path
        return path

    # --- Calculate total duration ---
    total_duration = sum(s.get("duration", 0) for s in shots)
    # Validate duration range (4-15s)
    valid_duration = max(4, min(15, total_duration))
    if valid_duration != total_duration:
        logger.warning(f"Scene {scene_id} total duration {total_duration}s -> adjusted to {valid_duration}s")

    # --- Collect character reference images ---
    char_mapping = storyboard.get("character_image_mapping", {})
    characters = storyboard.get("elements", {}).get("characters", [])

    if not char_mapping and characters:
        logger.warning("character_image_mapping is empty, character reference images will not be included in prompt")

    # Find character reference images for this scene (maintain image_N order)
    scene_char_refs = []
    scene_char_tags = []
    for char in characters:
        eid = char.get("element_id", "")
        tag = char_mapping.get(eid)
        refs = char.get("reference_images", [])
        if tag and refs:
            scene_char_refs.append(resolve_path(refs[0]))
            scene_char_tags.append((tag, char.get("name", ""), eid))

    # --- Find storyboard frame image ---
    frame_image = None
    # First check reference_images from first shot for storyboard frame
    if shots and shots[0].get("reference_images"):
        first_refs = shots[0]["reference_images"]
        for ref in first_refs:
            if "frame" in ref.lower() or "frames" in ref.lower():
                frame_image = resolve_path(ref)
                break
        if not frame_image:
            # If first image is not a character reference, use it as storyboard frame
            if first_refs[0] not in scene_char_refs:
                frame_image = resolve_path(first_refs[0])

    # --- Assemble image_urls ---
    image_urls = []
    if frame_image:
        image_urls.append(frame_image)
    image_urls.extend(scene_char_refs)

    # --- Assemble character description lines ---
    char_desc_parts = []
    for tag, name, eid in scene_char_tags:
        tag_str = f"@image{tag.replace('image_', '')}" if tag.startswith("image_") else f"@{tag}"
        char_desc_parts.append(f"{tag_str} ({name})")
    char_line = ", ".join(char_desc_parts) if char_desc_parts else ""

    # --- Assemble visual/style line (from scene or first shot) ---
    visual_style = scene.get("visual_style", "")
    narrative_goal = scene.get("narrative_goal", "")
    style_desc = visual_style or narrative_goal or ""

    # --- Assemble time segments ---
    time_offset = 0
    segments = []
    for idx, shot in enumerate(shots):
        d = shot.get("duration", 0)
        start = time_offset
        end = time_offset + d
        prompt_text = shot.get("video_prompt", shot.get("description", ""))
        segments.append(f"{start}-{end}s：{prompt_text}；")
        time_offset = end

    # --- Assemble complete prompt ---
    lines = []

    # Referencing line
    if frame_image:
        lines.append(f"Referencing the {scene_id}_frame composition for scene layout and character positioning.")
        lines.append("")

    # Character reference line
    if char_line:
        lines.append(f"{char_line}, {style_desc};" if style_desc else f"{char_line};")
        lines.append("")

    # Overall overview
    scene_desc = scene.get("scene_name", "") or scene.get("narrative_goal", "")
    if scene_desc:
        lines.append(f"Overall: {scene_desc}")
        lines.append("")

    # Segmented actions
    lines.append(f"Segmented actions ({valid_duration}s):")
    lines.extend(segments)
    lines.append("")

    # Ratio constraint
    ratio_name = "landscape" if aspect_ratio == "16:9" else "portrait" if aspect_ratio == "9:16" else ""
    lines.append(f"Maintain {ratio_name} {aspect_ratio} composition, preserve aspect ratio")
    lines.append("No background music.")

    prompt = "\n".join(lines)

    logger.info(f"Seedance prompt auto-assembly complete ({scene_id}, {valid_duration}s, {len(image_urls)} images)")
    logger.debug(f"Prompt:\n{prompt}")

    return prompt, image_urls, valid_duration


# ============== Vidu Video Generation (Deprecated) ==============


class ViduClient:
    """
    Vidu video generation client (via Yunwu API)

    .. deprecated::
        Vidu backend is deprecated and no longer supported. Please use Kling, Kling-Omni, Seedance or Veo3.
        This class is retained for backward compatibility only and will be removed in a future version.
    """

    IMG2VIDEO_PATH = "/ent/v2/img2video"
    TEXT2VIDEO_PATH = "/ent/v2/text2video"
    QUERY_PATH = "/ent/v2/tasks/{task_id}/creations"

    def __init__(self):
        import warnings
        warnings.warn(
            "ViduClient is deprecated, please use KlingClient, KlingOmniClient, SeedanceClient or Veo3Client",
            DeprecationWarning,
            stacklevel=2
        )
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
        """Image-to-video generation"""
        resolution = resolution or Config.VIDU_RESOLUTION

        # Prepare image
        if image_path.startswith(('http://', 'https://')):
            image_input = image_path
        else:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image does not exist: {image_path}"}

            with open(image_path, 'rb') as f:
                image_data = f.read()

            base64_data = base64.b64encode(image_data).decode('utf-8')
            ext = os.path.splitext(image_path)[1].lower()
            # HEIC/HEIF needs conversion first
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

        logger.info(f"Creating image-to-video task: {prompt[:50]}...")

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

            logger.info(f"Task created: {task_id}")

            # Wait for completion
            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"Image-to-video generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        audio: bool = False,
        output: str = None
    ) -> Dict[str, Any]:
        """Text-to-video generation"""
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

        logger.info(f"Creating text-to-video task: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{Config.YUNWU_BASE_URL}{self.TEXT2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )

            # If viduq3-pro is not supported, fallback to viduq2
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

            logger.info(f"Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"Text-to-video generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """Wait for task completion"""
        import time
        start_time = time.monotonic()

        logger.info(f"Waiting for task completion: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"Task timeout ({max_wait}s)")
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
                        logger.info(f"Task complete (elapsed: {int(elapsed)}s)")
                        return video_url

                elif state == "failed":
                    logger.error(f"Task failed: {result.get('fail_reason')}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"Query failed: {e}")
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
        logger.info(f"Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Yunwu Kling Video Generation (Deprecated) ==============


class YunwuKlingClient:
    """
    Kling v3 video generation client (via Yunwu API)

    .. deprecated::
        Yunwu provider is deprecated and no longer supported. Please use Kling official API or fal provider.
        This class is retained for backward compatibility only and will be removed in a future version.

    Only supports kling-v3 model, for text2video and img2video.

    Key differences from official API:
    - Uses `model` parameter instead of `model_name`
    - Bearer Token authentication (reuses YUNWU_API_KEY)
    - Base URL: https://yunwu.ai
    """

    TEXT2VIDEO_PATH = "/kling/v1/videos/text2video"
    IMAGE2VIDEO_PATH = "/kling/v1/videos/image2video"
    QUERY_PATH = "/kling/v1/videos/text2video/{task_id}"

    MODEL = "kling-v3"  # Fixed to use kling-v3

    def __init__(self):
        import warnings
        warnings.warn(
            "YunwuKlingClient is deprecated, please use KlingClient (official API) or fal provider",
            DeprecationWarning,
            stacklevel=2
        )
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
        Text-to-video generation

        Args:
            prompt: Video description
            duration: Duration (3-15 seconds)
            mode: std or pro
            aspect_ratio: Aspect ratio (16:9, 9:16, 1:1)
            audio: Whether to generate audio
            multi_shot: Whether to enable multi-shot
            shot_type: intelligence (AI auto storyboard) or customize (custom storyboard)
            multi_prompt: List of shots for custom storyboard
            output: Output file path
        """
        payload = {
            "model": self.MODEL,  # Note: yunwu kling-v3 uses model instead of model_name
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

        logger.info(f"📤 Creating Yunwu Kling text-to-video task: {prompt[:50]}...")

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

            logger.info(f"Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id, "text2video")

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "Concurrent task limit exceeded, please wait for existing tasks to complete"
            logger.error(f"Yunwu Kling text-to-video failed: {error_msg}")
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
        Image-to-video generation (supports first/last frame control)

        Args:
            image_path: Image path or URL
            prompt: Video description
            duration: Duration (3-15 seconds)
            mode: std or pro
            audio: Whether to generate audio
            image_tail: Last frame image path or URL
            output: Output file path
        """
        # Prepare images
        image_url = await self._prepare_image(image_path)

        payload = {
            "model": self.MODEL,
            "image": image_url,
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "audio": audio
        }

        # First-last frame control
        if image_tail:
            tail_url = await self._prepare_image(image_tail)
            payload["image_tail"] = tail_url

        logger.info(f"📤 Creating Yunwu Kling image-to-video task: {prompt[:50]}...")

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

            logger.info(f"Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id, "image2video")

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Yunwu Kling image-to-video failed: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _prepare_image(self, image_path: str) -> str:
        """Prepare image (URL or base64)"""
        if image_path.startswith(('http://', 'https://')):
            return image_path

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image does not exist: {image_path}")

        # Validate and resize image dimensions
        result = validate_and_resize_image(image_path)
        if not result["success"]:
            raise ValueError(f"Image processing failed: {result.get('error')}")

        with open(result["output_path"], 'rb') as f:
            image_data = f.read()

        base64_data = base64.b64encode(image_data).decode('utf-8')
        ext = os.path.splitext(result["output_path"])[1].lower()
        mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
        mime_type = mime_map.get(ext, 'image/jpeg')

        return f"data:{mime_type};base64,{base64_data}"

    async def _wait_for_completion(self, task_id: str, task_type: str = "text2video", max_wait: int = 600) -> Optional[str]:
        """Wait for task completion"""
        import time
        start_time = time.monotonic()

        query_path = self.QUERY_PATH.replace("{task_id}", task_id)
        if task_type == "image2video":
            query_path = self.IMAGE2VIDEO_PATH + f"/{task_id}"

        logger.info(f"⏳ Waiting for Yunwu Kling task completion: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"Task timeout ({max_wait}s)")
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
                    logger.error(f"❌ Task query failed: {result.get('message')}")
                    return None

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"Task complete (elapsed: {int(elapsed)}s)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "unknown")
                    logger.error(f"❌ Task failed: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"Query failed: {e}")
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
        logger.info(f"Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class YunwuKlingOmniClient:
    """
    Kling v3 Omni video generation client (via Yunwu API)

    .. deprecated::
        Yunwu provider is deprecated and no longer supported. Please use Kling Omni official API or fal provider.
        This class is kept for backward compatibility only and will be removed in future versions.

    Only supports kling-v3-omni model, for multi-reference video generation.

    Key differences from official API:
    - Uses `model_name` parameter (same as official API)
    - Bearer Token authentication (reuses YUNWU_API_KEY)
    - Base URL: https://yunwu.ai
    """

    OMNI_VIDEO_PATH = "/kling/v1/videos/omni-video"
    QUERY_PATH = "/kling/v1/videos/omni-video/{task_id}"

    MODEL = "kling-v3-omni"  # Fixed to kling-v3-omni

    def __init__(self):
        import warnings
        warnings.warn(
            "YunwuKlingOmniClient Deprecated, please use KlingOmniClient (official API) or fal provider",
            DeprecationWarning,
            stacklevel=2
        )
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
        Omni-Video generation (supports multi-reference)

        Args:
            prompt: Video description, can use <<<image_1>>> to reference images
            duration: Duration (3-15 seconds)
            mode: std or pro
            aspect_ratio: Aspect ratio (16:9, 9:16, 1:1)
            audio: Generate audio or not
            image_list: Image path list, for character consistency
            multi_shot: Multi-shot or not
            shot_type: intelligence or customize
            multi_prompt: Custom shot list for storyboard
            output: Output file path
        """
        payload = {
            "model_name": self.MODEL,  # Note: yunwu kling-v3-omni uses model_name
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "sound": "on" if audio else "off",  # API requires sound parameter with value "on"/"off"
            "aspect_ratio": aspect_ratio
        }

        # Process image_list (format: [{"image_url": url_or_base64}, ...])
        if image_list:
            processed_images = await self._prepare_image_list(image_list)
            if processed_images:
                payload["image_list"] = processed_images
                logger.info(f"📎 Using {len(processed_images)} reference images")

        # Process multi-shot parameters
        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt and shot_type == "customize":
                payload["multi_prompt"] = multi_prompt

        logger.info(f"📤 Creating Yunwu Kling Omni-Video task: {prompt[:50]}...")

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

            logger.info(f"Omni-Video task created: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "Concurrent task limit exceeded, please wait for existing tasks to complete"
            logger.error(f"❌ Yunwu Kling Omni-Video failed: {error_msg}")
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
                logger.warning(f"⚠️ Reference image processing failed: {img_path}, {e}")
        return result

    async def _file_to_base64(self, file_path: str) -> Optional[str]:
        """Convert file to base64 (pure base64 string for yunwu API)"""
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ File does not exist: {file_path}")
            return None

        # Validate and resize image dimensions
        result = validate_and_resize_image(file_path)
        if not result["success"]:
            logger.warning(f"⚠️ Image processing failed: {file_path}, {result.get('error')}")
            return None

        with open(result["output_path"], 'rb') as f:
            image_data = f.read()

        # Return pure base64 string (without data URI prefix)
        # yunwu API expects pure base64, not data:image/xxx;base64,... format
        return base64.b64encode(image_data).decode('utf-8')

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """Wait for task completion"""
        import time
        start_time = time.monotonic()

        query_path = self.QUERY_PATH.replace("{task_id}", task_id)

        logger.info(f"⏳ Waiting for Yunwu Kling Omni task completion: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"Task timeout ({max_wait}s)")
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
                    logger.error(f"❌ Task query failed: {result.get('message')}")
                    return None

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"Task complete (elapsed: {int(elapsed)}s)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "unknown")
                    logger.error(f"❌ Task failed: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"Query failed: {e}")
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
        logger.info(f"Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Kling Video Generation ==============

class KlingClient:
    """
    Kling video generation client (kling-v3)

    Uses /v1/videos/text2video and /v1/videos/image2video endpoints.
    Supports text-to-video, image-to-video (first frame/first-last frame), multi-shot, audio-video synchronized output.
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
        """Generate JWT authentication token"""
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
        """Get valid token (with caching)"""
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
        Text-to-video generation

        Args:
            prompt: Video description
            duration: Duration (3-15 seconds)
            mode: std or pro
            aspect_ratio: Aspect ratio (16:9, 9:16, 1:1)
            sound: on or off
            multi_shot: Whether to enable multi-shot
            shot_type: intelligence (AI auto storyboard) or customize (custom storyboard)
            multi_prompt: List of shots for custom storyboard, format [{"index": 1, "prompt": "...", "duration": "3"}, ...]
            output: Output file path
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

        logger.info(f"Creating Kling text-to-video task: {prompt[:50]}...")

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

            logger.info(f"Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "Concurrent task limit exceeded, please wait for existing tasks to complete"
            elif "1201" in error_msg:
                error_msg = "Model not supported or parameter error, please check model_name and mode"
            logger.error(f"Kling text-to-video failed: {error_msg}")
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
        Image-to-video generation

        Args:
            image_path: Image path or URL
            prompt: Video description
            duration: Duration (3-15 seconds)
            mode: std or pro
            sound: on or off
            tail_image_path: Last frame image path (for first-last frame control)
            output: Output file path
            multi_shot: Whether to enable multi-shot
            shot_type: Multi-shot type (intelligence/customize)
            multi_prompt: Multi-shot configuration list
        """
        # Prepare images
        if image_path.startswith(('http://', 'https://')):
            image_url = image_path
        else:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image does not exist: {image_path}"}

            # Validate and resize image
            result = validate_and_resize_image(image_path)
            if not result["success"]:
                return {"success": False, "error": f"Image processing failed: {result.get('error')}"}

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

        # Process multi-shot parameters
        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt:
                payload["multi_prompt"] = multi_prompt

        # Process tail image (First-last frame control)
        if tail_image_path:
            if tail_image_path.startswith(('http://', 'https://')):
                tail_image_url = tail_image_path
            else:
                if not os.path.exists(tail_image_path):
                    return {"success": False, "error": f"Last frame image does not exist: {tail_image_path}"}

                # Validate and resize last frame image
                tail_result = validate_and_resize_image(tail_image_path)
                if not tail_result["success"]:
                    return {"success": False, "error": f"Last frame image processing failed: {tail_result.get('error')}"}

                with open(tail_result["output_path"], 'rb') as f:
                    tail_image_data = f.read()

                tail_image_url = base64.b64encode(tail_image_data).decode('utf-8')

            payload["image_tail"] = tail_image_url
            logger.info(f"Creating Kling image-to-video task (with last frame): {prompt[:50]}...")
        else:
            logger.info(f"Creating Kling image-to-video task: {prompt[:50]}...")

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

            logger.info(f"Task created: {task_id}")

            video_url = await self._wait_for_completion(task_id, query_path=self.IMAGE2VIDEO_QUERY_PATH)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "Concurrent task limit exceeded, please wait for existing tasks to complete"
            elif "1201" in error_msg:
                error_msg = "Model not supported or parameter error, please check model_name and mode"
            logger.error(f"Kling image-to-video failed: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _wait_for_completion(self, task_id: str, query_path: str = None, max_wait: int = 600) -> Optional[str]:
        """Wait for task completion"""
        import time
        if query_path is None:
            query_path = self.TEXT2VIDEO_QUERY_PATH
        start_time = time.monotonic()

        logger.info(f"Waiting for Kling task completion: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"Task timeout ({max_wait}s)")
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
                        logger.info(f"Kling task complete (elapsed: {int(elapsed)}s)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "Unknown error")
                    logger.error(f"Kling task failed: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"Query failed: {e}")
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
        logger.info(f"Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class KlingOmniClient:
    """
    Kling Omni-Video video generation client (kling-v3-omni)
    Uses /v1/videos/omni-video endpoint, supports image_list and multi_shot

    Features:
    - Text-to-video (3-15 seconds)
    - Image-to-video (supports image_list for multiple reference images)
    - Multi-shot video (multi_shot)
    - Audio-video synchronized output (sound: on/off)
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
        """Generate JWT authentication token"""
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
        """Get valid token (with caching)"""
        import time
        if not self._token or time.time() > self._token_expire - 60:
            self._token = self._generate_token()
            self._token_expire = time.time() + 3600
        return self._token

    def _file_to_base64(self, file_path: str) -> str:
        """Convert file to pure base64 string (without data URI prefix)"""
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
        Omni-Video generation (supports image_list + multi_shot)

        Args:
            prompt: Video description, can use <<<image_1>>> to reference images
            duration: Duration (3-15 seconds)
            mode: std or pro
            aspect_ratio: Aspect ratio (16:9, 9:16, 1:1)
            sound: on or off
            image_list: List of image paths for character consistency
            multi_shot: Whether to enable multi-shot
            shot_type: intelligence (AI auto storyboard) or customize (custom storyboard)
            multi_prompt: List of shots for custom storyboard, format [{"index": 1, "prompt": "...", "duration": "3"}, ...]
            output: Output file path
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

        # Handle image_list (pure base64, without data URI prefix)
        if image_list:
            processed_images = []
            for img_path in image_list:
                if not os.path.exists(img_path):
                    logger.warning(f"Reference image does not exist: {img_path}")
                    continue

                # Validate and resize image
                result = validate_and_resize_image(img_path)
                if not result["success"]:
                    logger.warning(f"Image processing failed: {img_path}, {result.get('error')}")
                    continue

                processed_images.append({
                    "image_url": self._file_to_base64(result["output_path"])
                })

            payload["image_list"] = processed_images
            logger.info(f"Using {len(processed_images)} reference images")

        # Handle multi-shot parameters
        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt and shot_type == "customize":
                payload["multi_prompt"] = multi_prompt

        logger.info(f"Creating Kling Omni-Video task: {prompt[:50]}...")

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

            logger.info(f"Omni-Video task created: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "Concurrent task limit exceeded, please wait for existing tasks to complete"
            elif "1201" in error_msg:
                error_msg = "Model not supported or parameter error"
            logger.error(f"Kling Omni-Video failed: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """Wait for task completion"""
        import time
        start_time = time.monotonic()

        logger.info(f"Waiting for Kling Omni-Video task completion: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"Task timeout ({max_wait}s)")
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
                        logger.info(f"Omni-Video task complete (elapsed: {int(elapsed)}s)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "Unknown error")
                    logger.error(f"Omni-Video task failed: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"Query failed: {e}")
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
        logger.info(f"Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class FalKlingClient:
    """
    Kling video generation client (via fal.ai proxy)

    Fully consistent with official Kling API:
    - Identical prompt writing
    - Identical parameter fields (duration, aspect_ratio, generate_audio, etc.)
    - Identical image input method

    Only difference: use --provider fal instead of --provider kling

    Supported features:
    - Text-to-video: only pass prompt
    - Single image generation: pass image_url
    - Multiple reference images: pass image_urls list
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
        image_url: str = None,        # First frame / single image
        image_urls: List[str] = None,  # Multiple reference images
        tail_image_url: str = None,    # Last frame
        output: str = None
    ) -> Dict[str, Any]:
        """
        Unified video generation method

        Args:
            prompt: Video description
            duration: Duration (3-15 seconds)
            aspect_ratio: Aspect ratio (16:9, 9:16, 1:1)
            generate_audio: Whether to generate audio
            image_url: First frame image (path or URL)
            image_urls: List of reference images (path or URL)
            tail_image_url: Last frame image (path or URL)
            output: Output file path
        """
        payload = {
            "prompt": prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
            "generate_audio": generate_audio
        }

        # First frame / single image (fal.ai uses start_image_url)
        if image_url:
            payload["start_image_url"] = self._prepare_image_url(image_url)

        # Multiple reference images (fal.ai uses image_urls, reference with @Image1 in prompt)
        if image_urls:
            payload["image_urls"] = [self._prepare_image_url(img) for img in image_urls]

        # Last frame (fal.ai uses end_image_url)
        if tail_image_url:
            payload["end_image_url"] = self._prepare_image_url(tail_image_url)

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

        logger.info(f"Creating fal Kling task: {payload.get('prompt', '')[:50]}...")

        try:
            # Submit task with fal_client, returns AsyncRequestHandle
            handle = await self.fal_client.submit(self.MODEL_ID, arguments=payload)
            request_id = handle.request_id
            logger.info(f"fal task submitted: {request_id}")
        except Exception as e:
            logger.error(f"fal task submission failed: {e}")
            return {"success": False, "error": str(e)}

        # Wait for completion
        video_url = await self._wait_for_completion(handle)

        if video_url and output:
            await self._download_file(video_url, output)
            return {"success": True, "video_url": video_url, "output": output, "request_id": request_id}

        return {"success": bool(video_url), "video_url": video_url, "request_id": request_id}

    async def _wait_for_completion(self, handle, max_wait: int = 600) -> Optional[str]:
        """Wait for task completion"""
        import time

        logger.info(f"Waiting for fal task completion: {handle.request_id}")
        start_time = time.monotonic()

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"fal task timeout ({max_wait}s)")
                return None

            try:
                # Use handle.status() to check status
                status = await handle.status()
                # status is an object, e.g., InProgress or Completed
                status_class = status.__class__.__name__
                logger.info(f"   [{int(elapsed)}s] Status: {status_class}")

                if status_class == "Completed":
                    # Use handle.get() to get result
                    result = await handle.get()
                    video_url = result.get("video", {}).get("url")
                    if video_url:
                        logger.info(f"fal task complete (elapsed: {int(elapsed)}s)")
                        return video_url
                    else:
                        logger.error(f"No video URL in fal task result: {result}")
                        return None
                elif status_class == "Failed":
                    error = getattr(status, 'error', None) or "Unknown error"
                    logger.error(f"fal task failed: {error}")
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
        logger.info(f"Saved to: {output_path}")

    async def close(self):
        await self.http_client.aclose()


class SeedanceClient:
    """
    Seedance 2 video generation client (via piapi.ai proxy)

    Core capabilities:
    - Text-to-Video: directly pass prompt (mode: text_to_video)
    - First/Last Frames: 1-2 images as first/last frames (mode: first_last_frames)
    - Omni Reference: multimodal reference - images/videos/audio (mode: omni_reference)

    Key parameters:
    - model: "seedance" (fixed)
    - task_type: "seedance-2-fast" (fast) or "seedance-2" (high quality)
    - mode: "text_to_video" | "first_last_frames" | "omni_reference" (required)
    - duration: 4-15 seconds (any integer)
    - aspect_ratio: 21:9 | 16:9 | 4:3 | 1:1 | 3:4 | 9:16 | auto
    - image_urls: up to 12 reference images
    - video_urls: up to 1 reference video (omni_reference mode)
    - audio_urls: audio reference (omni_reference mode, mp3/wav, <=15s)

    Prompt syntax:
    - Image reference: "@image1" references the first image
    - Video reference: "@video1" references the video
    - Audio reference: "@audio1" references the audio
    """

    TASK_PATH = "/api/v1/task"
    STATUS_PATH = "/api/v1/task/{task_id}"

    VALID_ASPECT_RATIOS = ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "auto"]

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    async def submit_task(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_urls: List[str] = None,
        video_urls: List[str] = None,
        audio_urls: List[str] = None,
        mode: str = None,
        model: str = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        Submit video generation task

        Args:
            prompt: Video description (supports @imageN / @videoN / @audioN references)
            duration: Duration (4-15 seconds, any integer)
            aspect_ratio: Aspect ratio (21:9 | 16:9 | 4:3 | 1:1 | 3:4 | 9:16 | auto)
            image_urls: List of reference images (up to 12)
            video_urls: List of reference videos (omni_reference mode)
            audio_urls: List of reference audio (omni_reference mode, mp3/wav, <=15s)
            mode: Generation mode (text_to_video | first_last_frames | omni_reference)
            model: "seedance-2-fast" or "seedance-2"
            output: Output file path
        """
        # Auto-infer mode
        if mode is None:
            if video_urls or audio_urls:
                mode = "omni_reference"
            elif image_urls:
                mode = "omni_reference"
            else:
                mode = "text_to_video"

        # duration validation (4-15)
        duration = max(4, min(15, duration))

        # aspect_ratio validation
        if aspect_ratio not in self.VALID_ASPECT_RATIOS:
            logger.warning(f"aspect_ratio {aspect_ratio} not in supported list, using 16:9")
            aspect_ratio = "16:9"

        model = model or Config.SEEDANCE_MODEL

        payload = {
            "model": "seedance",
            "task_type": model,
            "input": {
                "prompt": prompt,
                "mode": mode,
                "aspect_ratio": aspect_ratio,
                "duration": duration,
            }
        }

        # Prepare reference resources
        if image_urls:
            payload["input"]["image_urls"] = [self._prepare_url(img) for img in image_urls]

        if video_urls:
            payload["input"]["video_urls"] = [self._prepare_url(v) for v in video_urls]

        if audio_urls:
            payload["input"]["audio_urls"] = [self._prepare_url(a) for a in audio_urls]

        logger.info(f"Creating Seedance task: {prompt[:80]}...")
        logger.info(f"   Parameters: mode={mode}, duration={duration}s, aspect_ratio={aspect_ratio}, model={model}")

        try:
            response = await self.client.post(
                f"{Config.SEEDANCE_BASE_URL}{self.TASK_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.SEEDANCE_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            task_id = result.get("data", {}).get("task_id")
            if not task_id:
                error = result.get("data", {}).get("error", {})
                logger.error(f"API did not return task_id: {error}")
                return {"success": False, "error": error.get("message", "Unknown error")}

            logger.info(f"Seedance task created: {task_id}")

            # Wait for completion
            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": bool(video_url), "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"Seedance task failed: {e}")
            return {"success": False, "error": str(e)}

    async def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_urls: List[str] = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        Complete video generation workflow (shortcut method)
        """
        return await self.submit_task(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            image_urls=image_urls,
            output=output
        )

    async def check_task(self, task_id: str) -> Dict[str, Any]:
        """Query task status"""
        try:
            response = await self.client.get(
                f"{Config.SEEDANCE_BASE_URL}{self.STATUS_PATH.format(task_id=task_id)}",
                headers={"Authorization": f"Bearer {Config.SEEDANCE_API_KEY}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to query task status: {e}")
            return {"error": str(e)}

    def _prepare_url(self, path: str) -> str:
        """Prepare URL (convert local file to data URI)"""
        if path.startswith(('http://', 'https://')):
            return path
        return self._file_to_data_uri(path)

    def _file_to_data_uri(self, file_path: str) -> str:
        """Convert local file to data URI format base64

        Note: piapi.ai has request body size limit, large images need compression
        """
        # Check file size
        file_size = os.path.getsize(file_path)
        max_size = 100 * 1024  # 100KB threshold

        if file_size > max_size:
            # Compress image
            logger.info(f"Image is large ({file_size/1024:.1f}KB), compressing...")
            try:
                from PIL import Image
                import io

                img = Image.open(file_path)
                # Shrink to within 512x512
                img.thumbnail((512, 512), Image.Resampling.LANCZOS)
                # Convert to RGB (remove alpha channel)
                img = img.convert('RGB')

                # Save as JPEG
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=70)
                data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                logger.info(f"Compression complete ({len(data)/1024:.1f}KB)")
                return f"data:image/jpeg;base64,{data}"
            except Exception as e:
                logger.warning(f"Image compression failed, using original image: {e}")

        # Small image, read directly
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        with open(file_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/{ext};base64,{data}"

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """Wait for task completion"""
        import time
        start_time = time.monotonic()

        logger.info(f"Waiting for Seedance task completion: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"Seedance task timeout ({max_wait}s)")
                return None

            try:
                result = await self.check_task(task_id)
                data = result.get("data", {})
                status = data.get("status", "unknown")

                logger.info(f"   [{int(elapsed)}s] Status: {status}")

                if status == "completed":
                    video_url = data.get("output", {}).get("video")
                    if video_url:
                        logger.info(f"Seedance task complete (elapsed: {int(elapsed)}s)")
                        return video_url
                    else:
                        logger.error(f"No video URL in result: {data}")
                        return None

                elif status == "failed":
                    error = data.get("error", {})
                    logs = data.get("logs", [])
                    # logs usually contains more detailed error reason
                    error_detail = error.get("message", "Unknown")
                    if logs:
                        # Find first non-empty meaningful log
                        for log in logs:
                            if log and "restored" not in log.lower():
                                error_detail = log
                                break
                    logger.error(f"❌ Seedance task failed: {error_detail}")
                    return None

                await asyncio.sleep(10)

            except Exception as e:
                logger.warning(f"Query exception: {e}")
                await asyncio.sleep(10)

    async def _download_file(self, url: str, output_path: str):
        """Download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class Veo3Client:
    """Google Veo3 video generation client (via Compass proxy)"""

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))
        self.api_key = Config.COMPASS_API_KEY
        self.base_url = Config.COMPASS_VIDEO_URL

    async def close(self):
        await self.client.aclose()

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        output: str = "output.mp4"
    ) -> Dict[str, Any]:
        """Text-to-video generation"""
        return await self._generate(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            output=output
        )

    async def create_image2video(
        self,
        image_path: str,
        prompt: str,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        output: str = "output.mp4"
    ) -> Dict[str, Any]:
        """Image-to-video generation (first frame image)"""
        image_data = self._encode_image(image_path)
        instance = {
            "prompt": prompt,
            "image": {
                "inlineData": {
                    "mimeType": self._get_mime_type(image_path),
                    "data": image_data
                }
            }
        }
        return await self._generate(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            output=output,
            instance_override=instance
        )

    async def _generate(
        self,
        prompt: str,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        output: str = "output.mp4",
        instance_override: Dict = None
    ) -> Dict[str, Any]:
        """Core generation workflow: submit -> poll -> download"""
        # Validate duration
        valid_durations = [4, 6, 8]
        if duration not in valid_durations:
            closest = min(valid_durations, key=lambda x: abs(x - duration))
            logger.warning(f"Veo3 duration {duration}s not supported, adjusting to {closest}s")
            duration = closest

        instance = instance_override or {"prompt": prompt}
        if "prompt" not in instance:
            instance["prompt"] = prompt

        payload = {
            "instances": [instance],
            "parameters": {
                "aspectRatio": aspect_ratio,
                "durationSeconds": duration,
                "personGeneration": "allow_all"
            }
        }

        logger.info(f"Veo3 video generation: {prompt[:50]}... ({duration}s, {aspect_ratio})")

        try:
            response = await self.client.post(
                f"{self.base_url}:predictLongRunning",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            return {"success": False, "error": f"Veo3 submission failed: {e}"}

        operation_name = result.get("name")
        if not operation_name:
            return {"success": False, "error": f"No operation name: {result}"}

        logger.info(f"Task submitted, waiting for generation...")

        # Poll
        video_url = await self._wait_for_completion(operation_name)
        if not video_url:
            return {"success": False, "error": "Veo3 generation failed or timed out"}

        # Download
        await self._download_file(video_url, output)
        return {
            "success": True,
            "output": output,
            "video_url": video_url,
            "duration": duration
        }

    async def _wait_for_completion(self, operation_name: str, max_wait: int = 600) -> Optional[str]:
        """Poll task status"""
        import time
        start_time = time.monotonic()

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"Veo3 task timeout ({max_wait}s)")
                return None

            try:
                response = await self.client.post(
                    f"{self.base_url}:fetchPredictOperation",
                    json={"operationName": operation_name},
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                )
                response.raise_for_status()
                result = response.json()

                if result.get("done"):
                    # Check for errors
                    if "error" in result:
                        error_msg = result["error"].get("message", "Unknown error")
                        logger.error(f"Veo3 task failed: {error_msg}")
                        return None

                    # Extract video URL
                    videos = result.get("response", {}).get("videos", [])
                    if videos:
                        video_url = videos[0].get("uri") or videos[0].get("gcsUri")
                        cost = result.get("priceCostUsd", 0)
                        logger.info(f"Veo3 generation complete (elapsed: {int(elapsed)}s, cost: ${cost})")
                        return video_url
                    else:
                        logger.error(f"No video in response: {result}")
                        return None

                logger.info(f"   [{int(elapsed)}s] Generating...")
                await asyncio.sleep(10)

            except Exception as e:
                logger.warning(f"Polling exception: {e}")
                await asyncio.sleep(10)

    async def _download_file(self, url: str, output_path: str):
        """Download video file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=300.0) as dl_client:
            response = await dl_client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"Saved to: {output_path}")

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _get_mime_type(self, image_path: str) -> str:
        """Get image MIME type"""
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
        return mime_map.get(ext, 'image/png')


class SunoClient:
    """Suno music generation client"""

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

        # Truncate long prompt (to avoid long logs), does not affect parameters passed to API
        display_prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
        logger.info(f"Creating music generation task - description: {display_prompt}, style: {style}")

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
            logger.info(f"Task created: {task_id}")

            audio_url = await self._wait_for_completion(task_id)

            if audio_url and output:
                await self._download_file(audio_url, output)
                return {"success": True, "audio_url": audio_url, "output": output}

            return {"success": True, "audio_url": audio_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"Music generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 300) -> Optional[str]:
        """Wait for task completion"""
        import time
        start_time = time.monotonic()

        logger.info(f"Waiting for music generation...")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"Task timeout ({max_wait}s)")
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
                        logger.info(f"Music generation complete (elapsed: {int(elapsed)}s)")
                        return audio_url

                elif status == "FAILED":
                    logger.error("Music generation failed")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"Query failed: {e}")
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
        logger.info(f"Saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Volcengine TTS (Deprecated) ==============


class TTSClient:
    """
    Volcengine TTS client

    .. deprecated::
        Volcengine TTS is deprecated and no longer supported. Please use Gemini TTS (requires COMPASS_API_KEY).
        This class is retained for backward compatibility only and will be removed in a future version.
    """

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

    def __init__(self):
        import warnings
        warnings.warn(
            "TTSClient (Volcengine) is deprecated, please use GeminiTTSClient",
            DeprecationWarning,
            stacklevel=2
        )

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

        logger.info(f"TTS synthesis: {text[:30]}...")

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
            logger.info(f"TTS saved: {output} ({duration_ms}ms)")

            return {"success": True, "output": output, "duration_ms": duration_ms}

        except Exception as e:
            logger.error(f"TTS failed: {e}")
            return {"success": False, "error": str(e)}


# ============== Gemini TTS (via Compass API) ==============

class GeminiTTSClient:
    """Gemini TTS client (via Compass API)"""

    # Gemini TTS voices
    VOICE_TYPES = {
        # Female voices
        "female_narrator": ("Kore", "cmn-CN"),      # Standard female
        "female_gentle": ("Aoede", "cmn-CN"),        # Clear female
        "female_soft": ("Zephyr", "cmn-CN"),         # Soft female
        "female_bright": ("Leda", "cmn-CN"),         # Bright female
        # Male voices
        "male_narrator": ("Charon", "cmn-CN"),       # Standard male
        "male_warm": ("Orus", "cmn-CN"),             # Deep male
        "male_deep": ("Fenrir", "cmn-CN"),           # Deep male
        "male_bright": ("Puck", "cmn-CN"),           # Bright male
    }

    async def synthesize(
        self,
        text: str,
        output: str,
        voice: str = "female_narrator",
        emotion: str = None,
        speed: float = 1.0,
        prompt: str = None,
        language_code: str = "cmn-CN",
    ) -> Dict[str, Any]:
        """
        Synthesize speech

        Args:
            text: Text to read, supports inline emotion markers like [brightly], [sigh], [pause]
            output: Output file path
            voice: Voice name or preset (female_narrator, male_narrator, etc.)
            emotion: Deprecated, please use prompt or inline markers
            speed: Speech rate (Gemini TTS does not support this yet)
            prompt: Style instruction to control accent/emotion/tone/persona
            language_code: Language code (cmn-CN, en-US, ja-JP, etc.)
        """
        from google.cloud import texttospeech
        from google.api_core import client_options

        if not Config.COMPASS_API_KEY:
            return {
                "success": False,
                "error": "COMPASS_API_KEY not configured",
                "hint": "Please add COMPASS_API_KEY in config.json"
            }

        # Auto-add speaking rate instruction for Chinese narration
        if language_code == "cmn-CN" and not prompt:
            prompt = "Speak at a slightly faster pace, crisp and clear, natural flow"
            logger.info(f"Auto-added prompt for Chinese narration: {prompt}")

        # Get voice configuration
        voice_name = voice
        lang_code = language_code
        if voice in self.VOICE_TYPES:
            voice_name, lang_code = self.VOICE_TYPES[voice]

        logger.info(f"Gemini TTS synthesis: {text[:30]}... (voice: {voice_name})")

        try:
            # Create client
            client = texttospeech.TextToSpeechClient(
                client_options=client_options.ClientOptions(
                    api_endpoint="https://compass.llm.shopee.io/compass-api/v1",
                    api_key=Config.COMPASS_API_KEY,
                ),
                transport="rest",
            )

            # Build input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            if prompt:
                synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

            # Voice configuration
            voice_params = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                name=voice_name,
                model_name="gemini-2.5-flash-tts",
            )

            # Audio configuration
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
            )

            # Synthesize speech
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )

            # Save file
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, "wb") as f:
                f.write(response.audio_content)

            # Get precise duration using ffprobe
            duration = get_audio_duration(output)
            duration_ms = int(duration * 1000)
            logger.info(f"Gemini TTS saved: {output} ({duration:.2f}s)")

            return {"success": True, "output": output, "duration": duration, "duration_ms": duration_ms}

        except Exception as e:
            logger.error(f"Gemini TTS failed: {e}")
            return {"success": False, "error": str(e)}


def get_audio_duration(audio_path: str) -> float:
    """
    Get precise audio duration using ffprobe (in seconds)

    Args:
        audio_path: Path to audio file

    Returns:
        Duration in seconds (float)
    """
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def get_video_duration(video_path: str) -> float:
    """
    Get precise video duration using ffprobe (in seconds)

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds (float)
    """
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


# ============== Gemini Image Generation (via Yunwu API) ==============

class ImageClient:
    """Gemini image generation client (via Yunwu API)"""

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
        """Generate image with multiple reference images support"""
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
        logger.info(f"Image generation{ref_info}: {prompt[:30]}...")

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
                logger.info(f"Image saved: {output}")
                return {"success": True, "output": output}

            return {"success": True, "image_base64": image_data}

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {"success": False, "error": str(e)}


class FalImageClient:
    """
    Gemini image generation client (via fal.ai API)

    .. deprecated::
        Fal Image is deprecated and no longer supported. Please use CompassImageClient (requires COMPASS_API_KEY).
    """

    def __init__(self):
        import warnings
        warnings.warn(
            "FalImageClient is deprecated, please use CompassImageClient",
            DeprecationWarning,
            stacklevel=2
        )

    FAL_IMAGE_URL = "https://fal.run/fal-ai/gemini-3.1-flash-image-preview"
    FAL_IMAGE_EDIT_URL = "https://fal.run/fal-ai/gemini-3.1-flash-image-preview/edit"

    STYLE_PRESETS = {
        "cinematic": "cinematic style, film grain, dramatic lighting, movie still",
        "realistic": "photorealistic, natural lighting, high detail, 8k",
        "anime": "anime style, vibrant colors, clean lines, studio ghibli inspired",
        "artistic": "artistic style, painterly, expressive brushstrokes, impressionist",
    }

    # fal supported aspect_ratio
    ASPECT_RATIOS = ["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16", "4:1", "1:4", "8:1", "1:8"]

    async def generate(
        self,
        prompt: str,
        output: str = None,
        style: str = "cinematic",
        aspect_ratio: str = "9:16",
        reference_images: List[str] = None
    ) -> Dict[str, Any]:
        """Generate image with multiple reference images support"""
        import httpx

        style_suffix = self.STYLE_PRESETS.get(style, style)
        full_prompt = f"{prompt}, {style_suffix}"

        # fal aspect_ratio format
        fal_aspect = aspect_ratio if aspect_ratio in self.ASPECT_RATIOS else "auto"

        payload = {
            "prompt": full_prompt,
            "aspect_ratio": fal_aspect,
            "num_images": 1,
        }

        # Image-to-image mode: use edit endpoint when there are reference images
        is_edit_mode = reference_images and len(reference_images) > 0
        url = self.FAL_IMAGE_EDIT_URL if is_edit_mode else self.FAL_IMAGE_URL

        if is_edit_mode:
            # Upload reference images to temp storage or use base64
            image_urls = []
            for ref_path in reference_images:
                if os.path.exists(ref_path):
                    # Convert to base64 data URI
                    with open(ref_path, 'rb') as f:
                        img_data = f.read()
                    ext = os.path.splitext(ref_path)[1].lower()
                    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
                    mime_type = mime_map.get(ext, 'image/jpeg')
                    data_uri = f"data:{mime_type};base64,{base64.b64encode(img_data).decode('utf-8')}"
                    image_urls.append(data_uri)

            payload["image_urls"] = image_urls
            logger.info(f"Image generation (fal edit, {len(image_urls)} reference images): {prompt[:30]}...")
        else:
            logger.info(f"Image generation (fal t2i): {prompt[:30]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Key {Config.FAL_API_KEY}",
                    }
                )
                response.raise_for_status()
                result = response.json()

            images = result.get("images", [])
            if not images:
                return {"success": False, "error": "No image generated"}

            image_url = images[0].get("url")
            if not image_url:
                return {"success": False, "error": "No image URL in response"}

            # Download image
            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as dl_client:
                    dl_resp = await dl_client.get(image_url)
                    dl_resp.raise_for_status()
                    with open(output, "wb") as f:
                        f.write(dl_resp.content)
                logger.info(f"Image saved: {output}")
                return {"success": True, "output": output, "url": image_url}

            return {"success": True, "url": image_url}

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {"success": False, "error": str(e)}


class CompassImageClient:
    """Gemini image generation client (via Compass API)"""

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
        """Generate image with multiple reference images support"""
        import httpx

        style_suffix = self.STYLE_PRESETS.get(style, style)
        full_prompt = f"{prompt}, {style_suffix}"

        # Build parts array
        parts = []

        # Add reference images (image-to-image mode)
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
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"]
            }
        }

        ref_info = f" (with {len(reference_images)} reference images)" if reference_images else ""
        logger.info(f"Image generation (compass{ref_info}): {prompt[:30]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    Config.COMPASS_IMAGE_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {Config.COMPASS_API_KEY}",
                    }
                )
                response.raise_for_status()
                result = response.json()

            candidates = result.get("candidates", [])
            if not candidates:
                return {"success": False, "error": "No candidates in response"}

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
                logger.info(f"Image saved: {output}")
                return {"success": True, "output": output}

            return {"success": True, "image_base64": image_data}

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {"success": False, "error": str(e)}


# ============== Character/Persona Management (Optional Tool) ==============

class PersonaManager:
    """
    Character/Persona Manager (Optional Tool)

    Used to manage character reference images in projects.
    Only use when video involves characters; pure landscape/object videos don't need it.

    Usage:
        manager = PersonaManager(project_dir)
        manager.register("Alice", "female", "path/to/reference.jpg", "long hair, round face, glasses")
        ref_path = manager.get_reference("Alice")
    """

    def __init__(self, project_dir: str = None):
        self.project_dir = Path(project_dir) if project_dir else None
        self.personas = {}  # {persona_id: {name, gender, features, reference_image}}
        self._persona_file = None

        if self.project_dir:
            self._persona_file = self.project_dir / "personas.json"
            self._load()

    def _load(self):
        """Load persona data from file"""
        if self._persona_file and self._persona_file.exists():
            try:
                with open(self._persona_file, "r", encoding="utf-8") as f:
                    self.personas = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load personas.json: {e}")
                self.personas = {}

    def _save(self):
        """Save persona data to file"""
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
        Register a character/persona

        Args:
            name: Character name
            gender: Gender (male/female)
            reference_image: Reference image path (can be None, will be added in Phase 2)
            features: Physical appearance description

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
            logger.info(f"Character registered: {name} (ID: {persona_id}, reference image: {reference_image})")
        else:
            logger.info(f"Character registered: {name} (ID: {persona_id}, no reference image)")

        return persona_id

    def update_reference_image(self, persona_id: str, reference_image: str) -> bool:
        """
        Update character reference image (for Phase 2)

        Args:
            persona_id: Character ID
            reference_image: New reference image path

        Returns:
            Whether successful
        """
        if persona_id not in self.personas:
            logger.warning(f"Character does not exist: {persona_id}")
            return False

        self.personas[persona_id]["reference_image"] = reference_image
        self._save()
        logger.info(f"Updated reference image for {persona_id}: {reference_image}")
        return True

    def has_reference_image(self, persona_id: str) -> bool:
        """Check if character has a reference image"""
        persona = self.personas.get(persona_id)
        if persona:
            return bool(persona.get("reference_image"))
        return False

    def list_personas_without_reference(self) -> List[str]:
        """Return list of all character IDs without reference images"""
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
            Feature description string, e.g., "young woman with long hair, round face, glasses"
        """
        persona = self.personas.get(persona_id)
        if not persona:
            return ""

        parts = []

        # Gender
        gender = persona.get("gender", "")
        if gender == "female":
            parts.append("woman")
        elif gender == "male":
            parts.append("man")

        # Features
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
        Get persona prompt for Vidu/Gemini

        Format: "Reference for {GENDER} ({name}): MUST preserve exact appearance - {features}"
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
        Export to storyboard.json compatible characters format

        Returns:
            List in storyboard.json elements.characters format
        """
        characters = []
        for pid, pdata in self.personas.items():
            name = pdata.get("name", "")
            # Generate name_en (pinyin/English)
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
        Generate character_image_mapping (for storyboard.json)

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


# ============== Multimodal Image Analysis (Built-in Vision Capability) ==============

class VisionClient:
    """
    Multimodal image analysis client.

    Fallback for non-multimodal models, supports Kimi K2.5, GPT-4o and other vision models.
    Uses Anthropic API compatible format.

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
        prompt: str = "Please describe the content of this image in detail, including scene, subject, colors, atmosphere, etc.",
    ) -> Dict[str, Any]:
        """Analyze a single image"""
        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image does not exist: {image_path}"}

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
        prompt: str = "Please describe the content of this image in detail, including scene, subject, colors, atmosphere, etc."
    ) -> List[Dict[str, Any]]:
        """Batch analyze multiple images"""
        results = []
        for path in image_paths:
            result = await self.analyze_image(path, prompt)
            results.append(result)
        return results

    async def close(self):
        await self.client.aclose()


# ============== CLI Entry Point ==============

async def cmd_vision(args):
    """Image analysis command"""
    api_key = Config.get("VISION_API_KEY", "")
    if not api_key:
        print(json.dumps({
            "success": False,
            "error": "VISION_API_KEY not configured",
            "hint": "Please add VISION_API_KEY in config.json",
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
                    "error": f"Directory does not exist: {args.image}"
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


# ============== CLI entry point ==============

async def cmd_video(args):
    """Video generation command"""
    # Parameter validation: must specify --prompt or (--storyboard + --scene)
    has_prompt = bool(args.prompt)
    has_scene = bool(getattr(args, 'scene', None) and getattr(args, 'storyboard', None))
    if not has_prompt and not has_scene:
        print(json.dumps({
            "success": False,
            "error": "Must specify --prompt or --storyboard + --scene"
        }, indent=2, ensure_ascii=False))
        return 1

    provider = getattr(args, 'provider', None)
    backend = getattr(args, 'backend', 'kling')

    # Provider auto-selection logic (if user not specified)
    if provider is None:
        if backend == 'seedance':
            provider = 'piapi'  # seedance only has piapi provider
        elif backend == 'veo3':
            provider = 'compass'  # veo3 only has compass provider
        elif Config.KLING_ACCESS_KEY and Config.KLING_SECRET_KEY:
            provider = 'official'  # Prefer official API
        elif Config.FAL_API_KEY:
            provider = 'fal'       # Secondarily use fal
        else:
            provider = 'official'  # Default, will prompt for configuration

    logger.info(f"🔧 Using provider: {provider}, backend: {backend}")

    # Priority: CLI > storyboard.json > default
    aspect_ratio = args.aspect_ratio
    if aspect_ratio is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect_ratio = get_aspect_from_storyboard(args.storyboard)
        if aspect_ratio:
            logger.info(f"📐 Aspect ratio from storyboard.json: {aspect_ratio}")
    if aspect_ratio is None:
        aspect_ratio = "9:16"  # Final default
        logger.info(f"📐 Using default aspect ratio: {aspect_ratio}")

    # ==================== fal.ai provider ====================
    # fal Uses unified Kling model, parameters and prompt format identical to official
    if provider == 'fal':
        if not Config.FAL_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "FAL_API_KEY not configured",
                "hint": "Please add FAL_API_KEY in config.json",
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
                print(f"Error: {result.get('error')}")
                return 1
        finally:
            await client.close()

    # ==================== kling provider (Official API) ====================
    # BackendRouter: Force switch by feature requirements
    # - image-list: both kling-omni and seedance support, no forced switch
    # - tail-image: only kling supports, requires forced switch
    image_list = getattr(args, 'image_list', None)
    tail_image = getattr(args, 'tail_image', None)
    if tail_image and backend not in ['kling']:
        backend = 'kling'
        logger.info("🔀 Detected --tail-image, auto-switching to kling backend")

    # ==================== official provider (Official API) ====================
    # Check API key for corresponding backend
    if backend == 'kling':
        if not Config.KLING_ACCESS_KEY or not Config.KLING_SECRET_KEY:
            print(json.dumps({
                "success": False,
                "error": "Kling API credentials not configured",
                "hint": "Please add KLING_ACCESS_KEY and KLING_SECRET_KEY in config.json",
                "get_key": "Visit https://klingai.kuaishou.com to get API credentials"
            }, indent=2, ensure_ascii=False))
            return 1

        client = KlingClient()
        try:
            # Kling parameter conversion: audio -> sound
            sound = "on" if args.audio else "off"
            # Kling duration range: 3-15s
            duration = max(3, min(15, args.duration))

            # Process multi-shot parameters
            multi_shot = getattr(args, 'multi_shot', False)
            shot_type = getattr(args, 'shot_type', None)
            multi_prompt = None
            if getattr(args, 'multi_prompt', None):
                try:
                    multi_prompt = json.loads(args.multi_prompt)
                except json.JSONDecodeError:
                    print(json.dumps({
                        "success": False,
                        "error": "Failed to parse multi_prompt JSON"
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
                print(f"Error: {result.get('error')}")
                return 1
        finally:
            await client.close()

    elif backend == 'kling-omni':
        if not Config.KLING_ACCESS_KEY or not Config.KLING_SECRET_KEY:
            print(json.dumps({
                "success": False,
                "error": "Kling API credentials not configured",
                "hint": "Please add KLING_ACCESS_KEY and KLING_SECRET_KEY in config.json",
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
                        "error": "Failed to parse multi_prompt JSON"
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
                print(f"Error: {result.get('error')}")
                return 1
        finally:
            await client.close()

    elif backend == 'seedance':
        if not Config.SEEDANCE_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "SEEDANCE_API_KEY not configured",
                "hint": "Please add SEEDANCE_API_KEY in config.json",
                "get_key": "Seedance uses piapi.ai proxy, visit https://piapi.ai to register and get API key"
            }, indent=2, ensure_ascii=False))
            return 1

        client = SeedanceClient()
        try:
            scene_id = getattr(args, 'scene', None)
            storyboard_path = getattr(args, 'storyboard', None)

            # --- Auto-assembly mode: --storyboard + --scene ---
            if storyboard_path and scene_id:
                storyboard_data = load_storyboard(storyboard_path)
                if not storyboard_data:
                    print(json.dumps({
                        "success": False,
                        "error": f"Cannot load storyboard: {storyboard_path}"
                    }, indent=2, ensure_ascii=False))
                    return 1

                # Find specified scene
                target_scene = None
                for sc in storyboard_data.get("scenes", []):
                    if sc.get("scene_id") == scene_id:
                        target_scene = sc
                        break
                if not target_scene:
                    print(json.dumps({
                        "success": False,
                        "error": f"Scene not found: {scene_id}",
                        "available": [s.get("scene_id") for s in storyboard_data.get("scenes", [])]
                    }, indent=2, ensure_ascii=False))
                    return 1

                # Auto-assemble prompt, image_urls, duration
                prompt, image_urls, duration = build_seedance_prompt(target_scene, storyboard_data, storyboard_path)
                aspect_ratio = storyboard_data.get("aspect_ratio", aspect_ratio)

                logger.info(f"🎬 Seedance auto-assembly: scene={scene_id}, duration={duration}s, images={len(image_urls)}")

                result = await client.submit_task(
                    prompt=prompt,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    image_urls=image_urls if image_urls else None,
                    output=args.output
                )
            else:
                # --- Manual mode (backward compatible)---
                # Seedance 2 supports any integer 4-15s
                duration = max(4, min(15, args.duration))
                if duration != args.duration:
                    logger.warning(f"⚠️ Seedance 2 duration adjusted to {duration}s (range 4-15s)")

                image_list = getattr(args, 'image_list', None)
                mode = getattr(args, 'mode', 'text_to_video')
                # If mode is Kling std/pro, auto-select based on reference images
                if mode in ['std', 'pro']:
                    if image_list:
                        mode = 'omni_reference'  # Use omni_reference when having reference images
                    else:
                        mode = 'text_to_video'  # Pure text-to-video
                audio_urls = getattr(args, 'audio_urls', None)
                video_urls = getattr(args, 'video_urls', None)

                result = await client.submit_task(
                    prompt=args.prompt,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    image_urls=image_list,
                    mode=mode,
                    audio_urls=audio_urls,
                    video_urls=video_urls,
                    output=args.output
                )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"Error: {result.get('error')}")
                return 1
        finally:
            await client.close()

    elif backend == 'veo3':
        if not Config.COMPASS_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "COMPASS_API_KEY not configured",
                "hint": "Please add COMPASS_API_KEY in config.json",
                "get_key": "Compass API key is used to access Veo3 video generation"
            }, indent=2, ensure_ascii=False))
            return 1

        client = Veo3Client()
        try:
            if args.image:
                result = await client.create_image2video(
                    image_path=args.image,
                    prompt=args.prompt,
                    duration=args.duration,
                    aspect_ratio=aspect_ratio,
                    output=args.output
                )
            else:
                result = await client.create_text2video(
                    prompt=args.prompt,
                    duration=args.duration,
                    aspect_ratio=aspect_ratio,
                    output=args.output
                )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"Error: {result.get('error')}")
                return 1
        finally:
            await client.close()

    # Unknown backend
    print(json.dumps({
        "success": False,
        "error": f"Unsupported backend: {backend}",
        "supported_backends": ["kling", "kling-omni", "seedance", "veo3"]
    }, indent=2, ensure_ascii=False))
    return 1


async def cmd_music(args):
    """Music generation command"""
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
                    logger.info(f"🎵 Music description from creative.json: {prompt[:50]}...")
            if style is None:
                style = config.get("style")
                if style:
                    logger.info(f"🎵 Music style from creative.json: {style}")

    # prompt must be provided
    if prompt is None:
        print(json.dumps({
            "success": False,
            "error": "Must provide music description",
            "hint": "Please provide music description via --prompt or --creative"
        }, indent=2, ensure_ascii=False))
        return 1

    # style must be provided
    if style is None:
        print(json.dumps({
            "success": False,
            "error": "Must provide music style",
            "hint": "Please provide music style via --style or --creative"
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
            print(f"Error: {result.get('error')}")
            return 1
    finally:
        await client.close()


async def cmd_tts(args):
    """TTS synthesis command - uses Gemini TTS (via Compass API)"""
    if not Config.COMPASS_API_KEY:
        print(json.dumps({
            "success": False,
            "error": "COMPASS_API_KEY not configured",
            "hint": "Please configure COMPASS_API_KEY to use Gemini TTS",
            "get_key": "Visit compass.llm.shopee.io to get API key"
        }, indent=2, ensure_ascii=False))
        return 1

    logger.info("🔧 Using Gemini TTS (Compass)")
    client = GeminiTTSClient()
    result = await client.synthesize(
        text=args.text,
        output=args.output,
        voice=args.voice,
        emotion=args.emotion,
        speed=args.speed,
        prompt=getattr(args, 'prompt', None),
    )

    if result.get("success"):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    else:
        print(f"Error: {result.get('error')}")
        return 1


async def cmd_image(args):
    """Image generation command"""
    # Provider auto-selection logic
    provider = getattr(args, 'provider', None)
    if provider is None:
        # Priority: compass → yunwu
        if Config.COMPASS_API_KEY:
            provider = 'compass'
        elif Config.GEMINI_API_KEY:  # GEMINI_API_KEY is actually YUNWU_API_KEY
            provider = 'yunwu'
        else:
            provider = 'compass'  # Default, will prompt for configuration

    logger.info(f"🔧 Using provider: {provider}")

    # Priority: CLI > storyboard.json > default
    aspect_ratio = args.aspect_ratio
    if aspect_ratio is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect_ratio = get_aspect_from_storyboard(args.storyboard)
        if aspect_ratio:
            logger.info(f"📐 Aspect ratio from storyboard.json: {aspect_ratio}")
    if aspect_ratio is None:
        aspect_ratio = "9:16"  # Final default
        logger.info(f"📐 Using default aspect ratio: {aspect_ratio}")

    # compass provider
    if provider == 'compass':
        if not Config.COMPASS_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "COMPASS_API_KEY not configured",
                "hint": "Please add COMPASS_API_KEY in config.json"
            }, indent=2, ensure_ascii=False))
            return 1

        client = CompassImageClient()
        result = await client.generate(
            prompt=args.prompt,
            output=args.output,
            style=args.style,
            aspect_ratio=aspect_ratio,
            reference_images=args.reference
        )

    # yunwu provider (Gemini via Yunwu)
    else:
        if not Config.GEMINI_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "YUNWU_API_KEY not configured（for Gemini image generation）",
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
        print(f"Error: {result.get('error')}")
        return 1


async def cmd_setup(args):
    """Interactive API provider and key configuration"""

    # Define all available video generation providers and their required keys
    VIDEO_PROVIDERS = {
        "1": {
            "name": "Seedance (ByteDance, recommended for fiction/shorts/MV)",
            "backend": "seedance",
            "provider": "piapi",
            "keys": [
                {"key": "SEEDANCE_API_KEY", "label": "Seedance API Key (piapi)", "url": "https://piapi.ai"}
            ]
        },
        "2": {
            "name": "Kling Official API (Kuaishou, recommended for realistic/ads)",
            "backend": "kling",
            "provider": "official",
            "keys": [
                {"key": "KLING_ACCESS_KEY", "label": "Kling Access Key", "url": "https://klingai.kuaishou.com"},
                {"key": "KLING_SECRET_KEY", "label": "Kling Secret Key", "url": "https://klingai.kuaishou.com"}
            ]
        },
        "3": {
            "name": "Kling via fal.ai (bypass official concurrency limit)",
            "backend": "kling-omni",
            "provider": "fal",
            "keys": [
                {"key": "FAL_API_KEY", "label": "fal.ai API Key", "url": "https://fal.ai"}
            ]
        },
        "4": {
            "name": "Veo3 via Compass (Google Veo3, high-quality realistic shorts)",
            "backend": "veo3",
            "provider": "compass",
            "keys": [
                {"key": "COMPASS_API_KEY", "label": "Compass API Key", "url": "https://compass.llm.shopee.io"}
            ]
        },
    }

    OPTIONAL_SERVICES = {
        "music": {
            "name": "Suno music generation",
            "keys": [
                {"key": "SUNO_API_KEY", "label": "Suno API Key", "url": "https://sunoapi.org"}
            ]
        },
    }

    config = load_config()

    # Output as JSON for Claude parsing
    setup_info = {
        "action": "setup",
        "video_providers": {},
        "optional_services": {},
        "current_config": {}
    }

    for num, p in VIDEO_PROVIDERS.items():
        setup_info["video_providers"][num] = {
            "name": p["name"],
            "backend": p["backend"],
            "provider": p["provider"],
            "required_keys": [{"key": k["key"], "label": k["label"], "url": k["url"],
                               "configured": bool(config.get(k["key"]) or os.getenv(k["key"]))}
                              for k in p["keys"]]
        }

    for svc_id, svc in OPTIONAL_SERVICES.items():
        setup_info["optional_services"][svc_id] = {
            "name": svc["name"],
            "required_keys": [{"key": k["key"], "label": k["label"], "url": k["url"],
                               "configured": bool(config.get(k["key"]) or os.getenv(k["key"]))}
                              for k in svc["keys"]]
        }

    # Show currently configured keys
    for key in ["SEEDANCE_API_KEY", "KLING_ACCESS_KEY", "KLING_SECRET_KEY", "FAL_API_KEY",
                "YUNWU_API_KEY", "SUNO_API_KEY", "VOLCENGINE_TTS_APP_ID",
                "VOLCENGINE_TTS_ACCESS_TOKEN", "COMPASS_API_KEY"]:
        val = config.get(key) or os.getenv(key, "")
        setup_info["current_config"][key] = f"{val[:4]}***" if val else "Not set"

    # Non-interactive mode: direct config with --provider parameter
    provider_choice = getattr(args, 'provider_choice', None)
    set_keys = getattr(args, 'set_key', None) or []

    if set_keys:
        for kv in set_keys:
            if "=" in kv:
                k, v = kv.split("=", 1)
                config[k] = v
                setup_info["saved"] = setup_info.get("saved", [])
                setup_info["saved"].append(k)
        save_config(config)
        Config._cached_config = None  # Clear cache
        setup_info["status"] = "keys_saved"
    elif provider_choice and provider_choice in VIDEO_PROVIDERS:
        p = VIDEO_PROVIDERS[provider_choice]
        setup_info["selected_provider"] = p["name"]
        setup_info["need_keys"] = [k for k in p["keys"]
                                   if not (config.get(k["key"]) or os.getenv(k["key"]))]
        setup_info["status"] = "provider_selected"
    else:
        setup_info["status"] = "awaiting_selection"

    print(json.dumps(setup_info, indent=2, ensure_ascii=False))
    return 0


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
        "SEEDANCE_API_KEY": {
            "value": Config.SEEDANCE_API_KEY,
            "purpose": "Seedance video generation (piapi.ai proxy)",
            "get_key": "https://piapi.ai"
        },
        "COMPASS_API_KEY": {
            "value": Config.COMPASS_API_KEY,
            "purpose": "Veo3 video + Gemini image + Gemini TTS (Compass proxy)",
            "get_key": "https://compass.llm.shopee.io"
        },
        "YUNWU_API_KEY": {
            "value": Config.YUNWU_API_KEY,
            "purpose": "Vidu video generation + Gemini image generation",
            "get_key": "https://yunwu.ai"
        },
        "KLING_ACCESS_KEY": {
            "value": Config.KLING_ACCESS_KEY,
            "purpose": "Kling video generation Access Key",
            "get_key": "https://klingai.kuaishou.com"
        },
        "KLING_SECRET_KEY": {
            "value": Config.KLING_SECRET_KEY,
            "purpose": "Kling video generation Secret Key",
            "get_key": "https://klingai.kuaishou.com"
        },
        "FAL_API_KEY": {
            "value": Config.FAL_API_KEY,
            "purpose": "fal.ai Kling video generation proxy (bypass official concurrency limit)",
            "get_key": "https://fal.ai"
        },
        "SUNO_API_KEY": {
            "value": Config.SUNO_API_KEY,
            "purpose": "Suno music generation",
            "get_key": "https://sunoapi.org"
        },
    }

    for name, info in env_vars.items():
        is_set = bool(info["value"])
        masked = f"{info['value'][:4]}***" if is_set else "Not set"
        results["api_keys"][name] = {
            "set": is_set,
            "masked_value": masked,
            "purpose": info["purpose"],
            "get_key_url": info["get_key"]
        }

    # Check if at least one video provider is available
    has_video_provider = any([
        Config.SEEDANCE_API_KEY,
        Config.COMPASS_API_KEY,
        Config.KLING_ACCESS_KEY and Config.KLING_SECRET_KEY,
        Config.FAL_API_KEY,
    ])
    results["has_video_provider"] = has_video_provider
    if not has_video_provider:
        results["ready"] = False
        results["missing"].append("No video generation API key configured")
        results["hints"].append("Please run setup command to configure API first: python video_gen_tools.py setup")

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results["ready"] else 1


async def cmd_validate(args):
    """Validate storyboard.json"""
    result = validate_storyboard(args.storyboard)

    # Output result
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result["errors"]:
        logger.error(f"❌ Validation failed: {len(result['errors'])} errors")
    if result["warnings"]:
        logger.warning(f"⚠️ {len(result['warnings'])} warnings")
    if result["valid"]:
        logger.info("✅ Validation passed")

    return 0 if result["valid"] else 1


def main():
    parser = argparse.ArgumentParser(
        description="Vico Tools - Video Creation API Command-Line Toolset",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # setup subcommand (interactive provider + API key configuration)
    setup_parser = subparsers.add_parser("setup", help="Interactive API provider and key configuration")
    setup_parser.add_argument("--provider", dest="provider_choice", choices=["1", "2", "3", "4"],
                              help="Select video provider: 1=Seedance, 2=Kling Official, 3=Kling(fal), 4=Veo3(compass)")
    setup_parser.add_argument("--set-key", nargs="+", metavar="KEY=VALUE",
                              help="Set API key, format: KEY=VALUE (multiple allowed)")

    # check subcommand
    subparsers.add_parser("check", help="Check environment dependencies and configuration")

    # video subcommand
    video_parser = subparsers.add_parser("video", help="Generate video")
    video_parser.add_argument("--image", "-i", help="Input image path or URL (image-to-video)")
    video_parser.add_argument("--prompt", "-p", default=None, help="Video description (optional in Seedance --scene mode)")
    video_parser.add_argument("--duration", "-d", type=int, default=5, help="Duration (seconds)")
    video_parser.add_argument("--resolution", "-r", default="720p", help="Resolution")
    video_parser.add_argument("--aspect-ratio", "-a", default=None, help="Aspect ratio (e.g., 16:9, 9:16)")
    video_parser.add_argument("--storyboard", "-s", help="storyboard.json path, auto-read aspect_ratio")
    video_parser.add_argument("--audio", action="store_true", help="Generate native audio")
    video_parser.add_argument("--output", "-o", help="Output file path")
    video_parser.add_argument("--provider", choices=["official", "fal", "compass"], default=None,
                              help="API provider (auto-selected by default; veo3 only supports compass)")
    video_parser.add_argument("--backend", "-b", choices=["kling", "kling-omni", "seedance", "veo3"], default="kling",
                              help="Video generation backend (default kling; kling-omni for reference images; seedance for intelligent shot switching; veo3 for high-quality realistic shorts)")
    video_parser.add_argument("--mode", "-m", choices=["std", "pro", "text_to_video", "first_last_frames", "omni_reference"], default="std",
                              help="Generation mode (Kling: std or pro; Seedance: text_to_video, first_last_frames, omni_reference)")
    video_parser.add_argument("--multi-shot", action="store_true",
                              help="Enable Kling multi-shot mode")
    video_parser.add_argument("--shot-type", choices=["intelligence", "customize"],
                              help="Multi-shot type (intelligence: AI auto, customize: custom)")
    video_parser.add_argument("--multi-prompt", type=str,
                              help="Multi-shot prompt list (JSON format)")
    video_parser.add_argument("--tail-image", type=str,
                              help="Tail frame image path (for first-last frame control)")
    video_parser.add_argument("--image-list", nargs="+",
                              help="Omni-Video multi-reference image path list (kling-omni only); or Seedance first-last frame images")
    video_parser.add_argument("--scene", help="Scene ID (Seedance only: auto-assemble time-segment prompt with --storyboard)")
    video_parser.add_argument("--audio-urls", nargs="+",
                              help="Audio reference URL list (Seedance 2 only)")
    video_parser.add_argument("--video-urls", nargs="+",
                              help="Video reference URL list (Seedance 2 only)")

    # music subcommand
    music_parser = subparsers.add_parser("music", help="Generate music")
    music_parser.add_argument("--prompt", "-p", default=None, help="Music description (auto-read from creative.json)")
    music_parser.add_argument("--style", "-s", default=None, help="Music style (auto-read from creative.json)")
    music_parser.add_argument("--creative", "-c", help="creative.json path, auto-read prompt and style")
    music_parser.add_argument("--no-instrumental", dest="instrumental", action="store_false", help="Include vocals (default instrumental)")
    music_parser.set_defaults(instrumental=True)
    music_parser.add_argument("--output", "-o", help="Output file path")

    # tts subcommand
    tts_parser = subparsers.add_parser("tts", help="Generate speech")
    tts_parser.add_argument("--text", "-t", required=True, help="Text to synthesize")
    tts_parser.add_argument("--output", "-o", required=True, help="Output file path")
    tts_parser.add_argument("--voice", "-v", default="female_narrator",
                           choices=["female_narrator", "female_gentle", "female_soft", "female_bright",
                                    "male_narrator", "male_warm", "male_deep", "male_bright"],
                           help="Voice preset")
    tts_parser.add_argument("--emotion", "-e", choices=["neutral", "happy", "sad", "gentle", "serious"],
                           help="Emotion (deprecated, recommend using --prompt)")
    tts_parser.add_argument("--prompt", "-p", help="Style instruction, controls accent/emotion/tone/persona (e.g., humorous commentary, slightly teasing)")
    tts_parser.add_argument("--speed", type=float, default=1.0, help="Speech speed")

    # image subcommand
    image_parser = subparsers.add_parser("image", help="Generate image")
    image_parser.add_argument("--prompt", "-p", required=True, help="Image description")
    image_parser.add_argument("--output", "-o", help="Output file path")
    image_parser.add_argument("--style", "-s", default="cinematic",
                              help="Style (free text, e.g., cinematic, watercolor illustration)")
    image_parser.add_argument("--aspect-ratio", "-a", default=None, help="Aspect ratio")
    image_parser.add_argument("--storyboard", help="storyboard.json path, auto-read aspect_ratio")
    image_parser.add_argument("--reference", "-r", nargs="+", help="Reference image paths (supports multiple, important characters at the end)")
    image_parser.add_argument("--provider", choices=["compass", "yunwu"], default=None,
                              help="API provider (auto-selected by default: compass preferred)")

    # vision subcommand (built-in multimodal analysis)
    vision_parser = subparsers.add_parser("vision", help="Analyze image content")
    vision_parser.add_argument("image", help="Image path or directory")
    vision_parser.add_argument("--batch", "-b", action="store_true", help="Batch analyze images in directory")
    vision_parser.add_argument("--prompt", "-p", default="Please describe this image in detail, including scene, subject, colors, atmosphere, etc.", help="Analysis prompt")

    # validate subcommand
    validate_parser = subparsers.add_parser("validate", help="Validate storyboard.json")
    validate_parser.add_argument("--storyboard", "-s", required=True, help="storyboard.json path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run corresponding command
    commands = {
        "setup": cmd_setup,
        "check": cmd_check,
        "video": cmd_video,
        "music": cmd_music,
        "tts": cmd_tts,
        "image": cmd_image,
        "vision": cmd_vision,
        "validate": cmd_validate,
    }

    return asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    sys.exit(main())