#!/usr/bin/env python3
"""
Vico Tools - Video Creation API Command Line Toolset

Usage:
  python video_gen_tools.py setup                                          # Interactive API provider setup
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

# ============== Image Size Validation & Processing ==============

def validate_and_resize_image(
    image_path: str,
    output_path: str = None,
    min_size: int = 720,
    max_size: int = 2048,
    target_size: int = 1280
) -> Dict[str, Any]:
    """
    Validate and adjust image size

    Args:
        image_path: image path
        output_path: output path（auto-generated when None）
        min_size: minimum side length limit (will enlarge if smaller)
        max_size: maximum side length limit (will shrink if larger)
        target_size: target size (used when enlarging)

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
            logger.info(f"📐 image size too small {w}x{h}，needs to be enlarged to at least {min_size}px")
        elif max_dim > max_size:
            scale = max_size / max_dim
            need_resize = True
            logger.info(f"📐 image size too large {w}x{h}，needs to be reduced to at most {max_size}px")

        if need_resize:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)

            if output_path is None:
                base, ext = os.path.splitext(image_path)
                output_path = f"{base}_resized{ext}"

            img_resized.save(output_path, quality=95)
            logger.info(f"📐 image size adjusted: {w}x{h} → {new_w}x{new_h}")

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
        logger.error(f"❌ image size processing failed: {e}")
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
    """Load config from file and environment variables（config file takes priority）"""

    _cached_config = None

    @classmethod
    def _get_config(cls) -> Dict[str, str]:
        if cls._cached_config is None:
            cls._cached_config = load_config()
        return cls._cached_config

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """priority from config file, then environment variables"""
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

    # Gemini Image（via Yunwu API，sharing YUNWU_API_KEY）
    @property
    def GEMINI_API_KEY(self) -> str:
        return self.get("YUNWU_API_KEY", "")

    GEMINI_IMAGE_URL: str = "https://yunwu.ai/v1beta/models/gemini-3.1-flash-image-preview:generateContent"

    # Migoo LLM API
    @property
    def MIGOO_API_KEY(self) -> str:
        return self.get("MIGOO_API_KEY", "")

    MIGOO_IMAGE_URL: str = "https://inner-api.us.migoo.shopee.io/inbeeai/compass-api/v1/publishers/google/models/gemini-3.1-flash-image-preview:generateContent"
    MIGOO_VIDEO_URL: str = "https://inner-api.us.migoo.shopee.io/inbeeai/compass-api/v1/publishers/google/models/veo-3.1-generate-001"

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
    SEEDANCE_MODEL: str = "seedance-2-fast"  # or seedance-2（high quality）


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
        logger.error(f"❌ cannot load storyboard: {e}")
        return None


# ============== Storyboard Validation ==============

VALID_ASPECT_RATIOS = ["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]

MODE_BACKEND_MAP = {
    "seedance-video": "seedance",
    "omni-video": "kling-omni",
    "img2video": "kling",
    "text2video": "kling",
    # veo3 deprecated and no longer supported
}

BACKEND_PROVIDER_KEYS = {
    "seedance": ["FAL_API_KEY", "SEEDANCE_API_KEY"],  # fal priority
    "kling": ["KLING_ACCESS_KEY", "FAL_API_KEY"],
    "kling-omni": ["KLING_ACCESS_KEY", "FAL_API_KEY"],
    # veo3 deprecated，MIGOO_API_KEY only for Gemini image/TTS
}


def validate_storyboard(storyboard_path: str) -> Dict[str, Any]:
    """��Validate storyboard.json，return {valid, errors, warnings}"""
    errors = []
    warnings = []

    data = load_storyboard(storyboard_path)
    if data is None:
        return {"valid": False, "errors": [f"cannot load file: {storyboard_path}"], "warnings": []}

    # --- Schema basics ---
    if "scenes" not in data or not isinstance(data.get("scenes"), list):
        errors.append("missing scenes array")
    if "aspect_ratio" not in data:
        errors.append("missing aspect_ratio field")
    elif data["aspect_ratio"] not in VALID_ASPECT_RATIOS:
        errors.append(f"aspect_ratio '{data['aspect_ratio']}' invalid，support: {VALID_ASPECT_RATIOS}")

    scenes = data.get("scenes", [])
    if not scenes:
        errors.append("scenes array is empty")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    # --- collect element IDs ---
    characters = data.get("elements", {}).get("characters", [])
    known_element_ids = {c.get("element_id") for c in characters if c.get("element_id")}

    # --- validate each Scene ---
    for scene in scenes:
        scene_id = scene.get("scene_id", "unknown")
        shots = scene.get("shots", [])
        if not shots:
            warnings.append(f"[{scene_id}] no shots")
            continue

        # collect backend info for each shot
        seedance_shots = []
        for shot in shots:
            shot_id = shot.get("shot_id", "unknown")
            duration = shot.get("duration")
            backend = shot.get("generation_backend", "")
            mode = shot.get("generation_mode", "")

            # durationcheck
            if duration is None:
                errors.append(f"[{shot_id}] missing duration")
                continue

            # Backend-mode consistency
            expected_backend = MODE_BACKEND_MAP.get(mode)
            if expected_backend and expected_backend != backend:
                errors.append(
                    f"[{shot_id}] generation_mode '{mode}' should use backend '{expected_backend}'，"
                    f"actually is '{backend}'"
                )

            # validate duration by backend type
            if backend in ("kling", "kling-omni"):
                if duration < 3 or duration > 15:
                    errors.append(f"[{shot_id}] Kling duration must be 3-15s，current {duration}s")
            # veo3 deprecated，validation skipped

            # Seedance shots collection (later aggregated by scene)
            if backend == "seedance":
                seedance_shots.append(shot)

            # reference imagefile exists
            for ref in shot.get("reference_images", []):
                if ref and not os.path.exists(ref):
                    warnings.append(f"[{shot_id}] ��reference image does not exist: {ref}")

            # video_prompt must exist
            if not shot.get("video_prompt"):
                warnings.append(f"[{shot_id}] missing video_prompt")

            # character reference check
            for char in shot.get("characters", []):
                char_id = char if isinstance(char, str) else char.get("element_id", "")
                if char_id and char_id not in known_element_ids:
                    warnings.append(f"[{shot_id}] referenced unregistered character: {char_id}")

            # --- link consistency check: Kling-Omni shot-level structure ---
            if backend == "kling-omni" and mode in ("omni-video", "reference2video"):
                # must have image_prompt（for generatingstoryboard frame）
                if not shot.get("image_prompt"):
                    errors.append(f"[{shot_id}] Kling-Omni must have image_prompt（shot-level storyboard structure）")

                # must have frame_path（storyboard frameoutput path）
                if not shot.get("frame_path"):
                    errors.append(f"[{shot_id}] Kling-Omni must have frame_path (shot-level storyboard frame)")

                # check if misusing Seedance scene storyboard frame
                ref_images = shot.get("reference_images", [])
                if ref_images:
                    first_ref = ref_images[0]
                    # if path is scene_x_frame instead of shot_x_frame，indicates Seedance structure
                    if "_frame" in first_ref and "shot_" not in first_ref and "scene_" in first_ref:
                        warnings.append(
                            f"[{shot_id}] possibly using Seedance scene storyboard frame '{first_ref}'，"
                            f"Kling-Omni requires shot-level storyboard frame（like {shot_id}_frame.png）"
                        )

        # --- Seedance scene total duration validation ---
        if seedance_shots:
            scene_total_duration = sum(s.get("duration", 0) for s in seedance_shots)
            if scene_total_duration < 4 or scene_total_duration > 15:
                errors.append(
                    f"[{scene_id}] Seedance scene total duration must be in 4-15s range，current {scene_total_duration}s"
                )

    # --- Provider available ---
    used_backends = set()
    for scene in scenes:
        for shot in scene.get("shots", []):
            b = shot.get("generation_backend")
            if b:
                used_backends.add(b)

    for backend in used_backends:
        required_keys = BACKEND_PROVIDER_KEYS.get(backend, [])
        if required_keys and not any(getattr(Config, k, "") for k in required_keys):
            warnings.append(f"backend '{backend}' no available API key（need: {' or '.join(required_keys)}）")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# ============== Seedance Prompt auto assemble ==============

def build_seedance_prompt(scene: Dict[str, Any], storyboard: Dict[str, Any], storyboard_path: str = None) -> tuple:
    """
    based on storyboard scene auto assemble Seedance time segment prompt。

    Args:
        scene: scene object
        storyboard: complete storyboard object
        storyboard_path: storyboard.json file path（used to calculate absolute path）

    Returns:
        (prompt: str, image_urls: list[str], duration: int)
    """
    scene_id = scene.get("scene_id", "scene_1")
    shots = scene.get("shots", [])
    aspect_ratio = storyboard.get("aspect_ratio", "16:9")

    # calculate storyboard directory（for conversionrelative path to absolute path）
    project_dir = None
    if storyboard_path:
        project_dir = os.path.dirname(os.path.dirname(storyboard_path))  # storyboard/ parent directory

    def resolve_path(path: str) -> str:
        """convert relative path to absolute path"""
        if not path or path.startswith(('http://', 'https://')):
            return path
        if os.path.isabs(path):
            return path
        if project_dir:
            abs_path = os.path.join(project_dir, path)
            if os.path.exists(abs_path):
                return abs_path
        return path

    # --- calculate total duration ---
    total_duration = sum(s.get("duration", 0) for s in shots)
    # validate duration range（4-15s）
    valid_duration = max(4, min(15, total_duration))
    if valid_duration != total_duration:
        logger.warning(f"⚠️ Scene {scene_id} total duration {total_duration}s → adjusted to {valid_duration}s")

    # --- collectcharacter reference image ---
    char_mapping = storyboard.get("character_image_mapping", {})
    characters = storyboard.get("elements", {}).get("characters", [])

    if not char_mapping and characters:
        logger.warning("⚠️ character_image_mapping empty，character reference imagewill not be included in prompt ")

    # find this scene involvedcharacter reference image（keep image_N order）
    scene_char_refs = []
    scene_char_tags = []
    for char in characters:
        eid = char.get("element_id", "")
        tag = char_mapping.get(eid)
        refs = char.get("reference_images", [])
        if tag and refs:
            scene_char_refs.append(resolve_path(refs[0]))
            scene_char_tags.append((tag, char.get("name", ""), eid))

    # --- find storyboard frame ---
    frame_image = None
    # priority from first shot reference_images find storyboard frame
    if shots and shots[0].get("reference_images"):
        first_refs = shots[0]["reference_images"]
        for ref in first_refs:
            if "frame" in ref.lower() or "frames" in ref.lower():
                frame_image = resolve_path(ref)
                break
        if not frame_image:
            # first onelikeif not character reference image，treat as storyboard frame
            if first_refs[0] not in scene_char_refs:
                frame_image = resolve_path(first_refs[0])

    # --- assemble image_urls ---
    image_urls = []
    if frame_image:
        image_urls.append(frame_image)
    image_urls.extend(scene_char_refs)

    # --- assemble character description lines ---
    char_desc_parts = []
    for tag, name, eid in scene_char_tags:
        tag_str = f"@Image{tag.replace('image_', '')}" if tag.startswith("image_") else f"@{tag}"
        char_desc_parts.append(f"{tag_str}（{name}）")
    char_line = "，".join(char_desc_parts) if char_desc_parts else ""

    # --- assemble view/style scene orfirst shot extract）---
    visual_style = scene.get("visual_style", "")
    narrative_goal = scene.get("narrative_goal", "")
    style_desc = visual_style or narrative_goal or ""

    # --- assemble time segments ---
    time_offset = 0
    segments = []
    for idx, shot in enumerate(shots):
        d = shot.get("duration", 0)
        start = time_offset
        end = time_offset + d
        prompt_text = shot.get("video_prompt", shot.get("description", ""))
        segments.append(f"{start}-{end}s：{prompt_text}；")
        time_offset = end

    # --- assemble complete prompt ---
    lines = []

    # Referencing line
    if frame_image:
        lines.append(f"Referencing the {scene_id}_frame composition for scene layout and character positioning.")
        lines.append("")

    # character reference line
    if char_line:
        lines.append(f"{char_line}，{style_desc}；" if style_desc else f"{char_line}；")
        lines.append("")

    # overall overview
    scene_desc = scene.get("scene_name", "") or scene.get("narrative_goal", "")
    if scene_desc:
        lines.append(f"overall：{scene_desc}")
        lines.append("")

    # segment action
    lines.append(f"segment action（{valid_duration}s）：")
    lines.extend(segments)
    lines.append("")

    # ratio constraint
    ratio_name = "horizontal" if aspect_ratio == "16:9" else "vertical" if aspect_ratio == "9:16" else ""
    lines.append(f"keep{ratio_name}{aspect_ratio}composition，without breaking visual ratio")
    lines.append("No background music.")

    prompt = "\n".join(lines)

    logger.info(f"📝 Seedance prompt auto assembly completed ({scene_id}, {valid_duration}s, {len(image_urls)} images)")
    logger.debug(f"Prompt:\n{prompt}")

    return prompt, image_urls, valid_duration


# ============== Vidu Video Generation (Deprecated) ==============


class ViduClient:
    """
    Vidu video generation client（via Yunwu API）

    .. deprecated::
        Vidu backenddeprecated and no longer supported。please use Kling、Kling-Omni or Seedance。
        this typekept only for backward compatibility，will be removed in future version。
    """

    IMG2VIDEO_PATH = "/ent/v2/img2video"
    TEXT2VIDEO_PATH = "/ent/v2/text2video"
    QUERY_PATH = "/ent/v2/tasks/{task_id}/creations"

    def __init__(self):
        import warnings
        warnings.warn(
            "ViduClient deprecated, please use KlingClient、KlingOmniClient or SeedanceClient",
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
        """image-to-video"""
        resolution = resolution or Config.VIDU_RESOLUTION

        # prepare images
        if image_path.startswith(('http://', 'https://')):
            image_input = image_path
        else:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"image does not exist: {image_path}"}

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

        logger.info(f"📤 create image-to-video task: {prompt[:50]}...")

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
                return {"success": False, "error": "APInot returnedtask_id"}

            logger.info(f"✅ task created: {task_id}")

            # wait for completion
            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ image-to-video failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        audio: bool = False,
        output: str = None
    ) -> Dict[str, Any]:
        """text-to-video"""
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

        logger.info(f"📤 create text-to-video task: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{Config.YUNWU_BASE_URL}{self.TEXT2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )

            # Ifviduq3-pronot supported，fallback toviduq2
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
                return {"success": False, "error": "APInot returnedtask_id"}

            logger.info(f"✅ task created: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ text-to-videofailed: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """waittask complete"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ waittask complete: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ task timeout ({max_wait}s)")
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
                        logger.info(f"✅ task complete (takes time: {int(elapsed)}s)")
                        return video_url

                elif state == "failed":
                    logger.error(f"❌ task fail: {result.get('fail_reason')}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Yunwu Kling Video Generation (Deprecated) ==============


class YunwuKlingClient:
    """
    Kling v3 video generation client（via Yunwu API）

    .. deprecated::
        Yunwu provider deprecated and no longer supported。please use Kling official API or fal provider。
        this typekept only for backward compatibility，will be removed in future version。

    only supports kling-v3 model，for text2video and img2video。

    with official API key differences：
    - use `model` parameter not `model_name`
    - Bearer Token auth（reuse YUNWU_API_KEY）
    - Base URL: https://yunwu.ai
    """

    TEXT2VIDEO_PATH = "/kling/v1/videos/text2video"
    IMAGE2VIDEO_PATH = "/kling/v1/videos/image2video"
    QUERY_PATH = "/kling/v1/videos/text2video/{task_id}"

    MODEL = "kling-v3"  # fixed use kling-v3

    def __init__(self):
        import warnings
        warnings.warn(
            "YunwuKlingClient deprecated, please use KlingClient(official API)or fal provider",
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
        text-to-video

        Args:
            prompt: videodescription
            duration: duration(3-15s)
            mode: std or pro
            aspect_ratio: aspect ratio (16:9, 9:16, 1:1)
            audio: whether to generate audio
            multi_shot: whethermulti-shot
            shot_type: intelligence（AIauto storyboard）or customize（custom storyboard）
            multi_prompt: custom storyboard shot list
            output: output file path
        """
        payload = {
            "model": self.MODEL,  # note：yunwu kling-v3 uses model rather than model_name
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

        logger.info(f"📤 create Yunwu Kling text-to-videotask: {prompt[:50]}...")

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
                return {"success": False, "error": "APInot returnedtask_id"}

            logger.info(f"✅ task created: {task_id}")

            video_url = await self._wait_for_completion(task_id, "text2video")

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "concurrent task limit exceeded，please wait for existing tasks to complete before retrying"
            logger.error(f"❌ Yunwu Kling text-to-videofailed: {error_msg}")
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
        image-to-video（supports firstlast framecontrol）

        Args:
            image_path: image pathorURL
            prompt: videodescription
            duration: duration(3-15s)
            mode: std or pro
            audio: whether to generate audio
            image_tail: last frameimage pathorURL
            output: output file path
        """
        # prepare images
        image_url = await self._prepare_image(image_path)

        payload = {
            "model": self.MODEL,
            "image": image_url,
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "audio": audio
        }

        # first/last framecontrol
        if image_tail:
            tail_url = await self._prepare_image(image_tail)
            payload["image_tail"] = tail_url

        logger.info(f"📤 create Yunwu Kling image-to-videotask: {prompt[:50]}...")

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
                return {"success": False, "error": "APInot returnedtask_id"}

            logger.info(f"✅ task created: {task_id}")

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
        """prepare images（URL or base64）"""
        if image_path.startswith(('http://', 'https://')):
            return image_path

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"image does not exist: {image_path}")

        # Validate and adjust image size
        result = validate_and_resize_image(image_path)
        if not result["success"]:
            raise ValueError(f"imageprocessing failed: {result.get('error')}")

        with open(result["output_path"], 'rb') as f:
            image_data = f.read()

        base64_data = base64.b64encode(image_data).decode('utf-8')
        ext = os.path.splitext(result["output_path"])[1].lower()
        mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
        mime_type = mime_map.get(ext, 'image/jpeg')

        return f"data:{mime_type};base64,{base64_data}"

    async def _wait_for_completion(self, task_id: str, task_type: str = "text2video", max_wait: int = 600) -> Optional[str]:
        """waittask complete"""
        import time
        start_time = time.monotonic()

        query_path = self.QUERY_PATH.replace("{task_id}", task_id)
        if task_type == "image2video":
            query_path = self.IMAGE2VIDEO_PATH + f"/{task_id}"

        logger.info(f"⏳ wait Yunwu Kling task complete: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ task timeout ({max_wait}s)")
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
                    logger.error(f"❌ task query failed: {result.get('message')}")
                    return None

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ task complete (takes time: {int(elapsed)}s)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "unknown")
                    logger.error(f"❌ task fail: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class YunwuKlingOmniClient:
    """
    Kling v3 Omni video generation client（via Yunwu API）

    .. deprecated::
        Yunwu provider deprecated and no longer supported。please use Kling Omni official API or fal provider。
        this typekept only for backward compatibility，will be removed in future version。

    only supports kling-v3-omni model，for multi-reference image video generation。

    with official API key differences：
    - use `model_name` parameter（with official API same）
    - Bearer Token auth（reuse YUNWU_API_KEY）
    - Base URL: https://yunwu.ai
    """

    OMNI_VIDEO_PATH = "/kling/v1/videos/omni-video"
    QUERY_PATH = "/kling/v1/videos/omni-video/{task_id}"

    MODEL = "kling-v3-omni"  # fixed use kling-v3-omni

    def __init__(self):
        import warnings
        warnings.warn(
            "YunwuKlingOmniClient deprecated, please use KlingOmniClient(official API)or fal provider",
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
        Omni-Video generate（supportmulti reference image）

        Args:
            prompt: videodescription，can use <<<image_1>>> reference image
            duration: duration(3-15s)
            mode: std or pro
            aspect_ratio: aspect ratio (16:9, 9:16, 1:1)
            audio: whether to generate audio
            image_list: image pathlist，forcharacter consistency
            multi_shot: whethermulti-shot
            shot_type: intelligence or customize
            multi_prompt: custom storyboard shot list
            output: output file path
        """
        payload = {
            "model_name": self.MODEL,  # note：yunwu kling-v3-omni uses model_name
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "sound": "on" if audio else "off",  # APIstandardrequirement sound parameter，value is "on"/"off"
            "aspect_ratio": aspect_ratio
        }

        # handle image_list（format：[{"image_url": url_or_base64}, ...]）
        if image_list:
            processed_images = await self._prepare_image_list(image_list)
            if processed_images:
                payload["image_list"] = processed_images
                logger.info(f"📎 use {len(processed_images)} reference images")

        # process multi-shot params
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
                return {"success": False, "error": "APInot returnedtask_id"}

            logger.info(f"✅ Omni-Video task created: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "concurrent task limit exceeded，please wait for existing tasks to complete before retrying"
            logger.error(f"❌ Yunwu Kling Omni-Video failed: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _prepare_image_list(self, image_paths: List[str]) -> List[Dict]:
        """prepare image_list parameter"""
        result = []
        for img_path in image_paths:
            try:
                if img_path.startswith(('http://', 'https://')):
                    result.append({"image_url": img_path})
                else:
                    # local file convert base64
                    base64_data = await self._file_to_base64(img_path)
                    if base64_data:
                        result.append({"image_url": base64_data})
            except Exception as e:
                logger.warning(f"⚠️ reference image processing failed: {img_path}, {e}")
        return result

    async def _file_to_base64(self, file_path: str) -> Optional[str]:
        """file to base64(pure base64string，for Yunwu API use）"""
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ file does not exist: {file_path}")
            return None

        # Validate and adjust image size
        result = validate_and_resize_image(file_path)
        if not result["success"]:
            logger.warning(f"⚠️ imageprocessing failed: {file_path}, {result.get('error')}")
            return None

        with open(result["output_path"], 'rb') as f:
            image_data = f.read()

        # return purebase64string（do notdata URIprefix）
        # yunwu APIexpect purebase64，rather than data:image/xxx;base64,... format
        return base64.b64encode(image_data).decode('utf-8')

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """waittask complete"""
        import time
        start_time = time.monotonic()

        query_path = self.QUERY_PATH.replace("{task_id}", task_id)

        logger.info(f"⏳ wait Yunwu Kling Omni task complete: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ task timeout ({max_wait}s)")
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
                    logger.error(f"❌ task query failed: {result.get('message')}")
                    return None

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ task complete (takes time: {int(elapsed)}s)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "unknown")
                    logger.error(f"❌ task fail: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Kling video generation ==============

class KlingClient:
    """
    Kling video generation client (kling-v3)

    use /v1/videos/text2video and /v1/videos/image2video endpoint。
    supporttext-to-video、image-to-video（first frame/first/last frame）、multi-shot、audio-visual simultaneous。
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
        """generate JWT auth token"""
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
        """get valid token（with cache）"""
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
        text-to-video

        Args:
            prompt: videodescription
            duration: duration(3-15s)
            mode: std or pro
            aspect_ratio: aspect ratio (16:9, 9:16, 1:1)
            sound: on or off
            multi_shot: whethermulti-shot
            shot_type: intelligence（AIauto storyboard）or customize（custom storyboard）
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

        logger.info(f"📤 create Kling text-to-videotask: {prompt[:50]}...")

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
                return {"success": False, "error": "APInot returnedtask_id"}

            logger.info(f"✅ task created: {task_id}")

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
            logger.error(f"❌ Kling text-to-videofailed: {error_msg}")
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
        image-to-video

        Args:
            image_path: image pathorURL
            prompt: videodescription
            duration: duration(3-15s)
            mode: std or pro
            sound: on or off
            tail_image_path: last frameimage path（forfirst/last framecontrol）
            output: output file path
            multi_shot: whethermulti-shot
            shot_type: multi-shottype (intelligence/customize)
            multi_prompt: multi-shotconfig list
        """
        # prepare images
        if image_path.startswith(('http://', 'https://')):
            image_url = image_path
        else:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"image does not exist: {image_path}"}

            # Validate and adjust image size
            result = validate_and_resize_image(image_path)
            if not result["success"]:
                return {"success": False, "error": f"imageprocessing failed: {result.get('error')}"}

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

        # process multi-shot params
        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt:
                payload["multi_prompt"] = multi_prompt

        # handlelast frameimage（first/last framecontrol）
        if tail_image_path:
            if tail_image_path.startswith(('http://', 'https://')):
                tail_image_url = tail_image_path
            else:
                if not os.path.exists(tail_image_path):
                    return {"success": False, "error": f"last frame image does not exist: {tail_image_path}"}

                # validate and adjust last frame image size
                tail_result = validate_and_resize_image(tail_image_path)
                if not tail_result["success"]:
                    return {"success": False, "error": f"last frame image processing failed: {tail_result.get('error')}"}

                with open(tail_result["output_path"], 'rb') as f:
                    tail_image_data = f.read()

                tail_image_url = base64.b64encode(tail_image_data).decode('utf-8')

            payload["image_tail"] = tail_image_url
            logger.info(f"📤 create Kling image-to-videotask(with last frame）: {prompt[:50]}...")
        else:
            logger.info(f"📤 create Kling image-to-videotask: {prompt[:50]}...")

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
                return {"success": False, "error": "APInot returnedtask_id"}

            logger.info(f"✅ task created: {task_id}")

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
            logger.error(f"❌ Kling image-to-video failed: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _wait_for_completion(self, task_id: str, query_path: str = None, max_wait: int = 600) -> Optional[str]:
        """waittask complete"""
        import time
        if query_path is None:
            query_path = self.TEXT2VIDEO_QUERY_PATH
        start_time = time.monotonic()

        logger.info(f"⏳ wait Kling task complete: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ task timeout ({max_wait}s)")
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
                    logger.warning(f"⚠️ query failed: {result.get('message')}")
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
                        logger.info(f"✅ Kling task complete (takes time: {int(elapsed)}s)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "Unknown error")
                    logger.error(f"❌ Kling task fail: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class KlingOmniClient:
    """
    Kling Omni-Video video generation client (kling-v3-omni)
    use /v1/videos/omni-video endpoint，support image_list and multi_shot

    features：
    - text-to-video(3-15s)
    - image-to-video（support image_list multi reference image）
    - multi-shotvideo（multi_shot）
    - audio-visual simultaneous（sound: on/off）
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
        """generate JWT auth token"""
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
        """get valid token（with cache）"""
        import time
        if not self._token or time.time() > self._token_expire - 60:
            self._token = self._generate_token()
            self._token_expire = time.time() + 3600
        return self._token

    def _file_to_base64(self, file_path: str) -> str:
        """convert file to pure base64 string（without data URI prefix）"""
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
        Omni-Video generate（support image_list + multi_shot）

        Args:
            prompt: videodescription，can use <<<image_1>>> reference image
            duration: duration(3-15s)
            mode: std or pro
            aspect_ratio: aspect ratio (16:9, 9:16, 1:1)
            sound: on or off
            image_list: image pathlist，forcharacter consistency
            multi_shot: whethermulti-shot
            shot_type: intelligence（AIauto storyboard）or customize（custom storyboard）
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

        # handle image_list(pure base64, without data URI prefix)
        if image_list:
            processed_images = []
            for img_path in image_list:
                if not os.path.exists(img_path):
                    logger.warning(f"⚠️ reference image does not exist: {img_path}")
                    continue

                # Validate and adjust image size
                result = validate_and_resize_image(img_path)
                if not result["success"]:
                    logger.warning(f"⚠️ imageprocessing failed: {img_path}, {result.get('error')}")
                    continue

                processed_images.append({
                    "image_url": self._file_to_base64(result["output_path"])
                })

            payload["image_list"] = processed_images
            logger.info(f"📎 use {len(processed_images)} reference images")

        # process multi-shot params
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
                return {"success": False, "error": "APInot returnedtask_id"}

            logger.info(f"✅ Omni-Video task created: {task_id}")

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
            logger.error(f"❌ Kling Omni-Video failed: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """waittask complete"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ wait Kling Omni-Video task complete: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ task timeout ({max_wait}s)")
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
                    logger.warning(f"⚠️ query failed: {result.get('message')}")
                    await asyncio.sleep(5)
                    continue

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ Omni-Video task complete (takes time: {int(elapsed)}s)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "Unknown error")
                    logger.error(f"❌ Omni-Video task fail: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class FalKlingClient:
    """
    Kling video generation client (via fal.ai proxy)

    with official Kling API exactly same：
    - prompt consistent notation
    - param field consistent（duration, aspect_ratio, generate_audio, etc）
    - imageinput method consistent

    only difference：use --provider fal rather than --provider kling

    supported features：
    - text-to-video：only pass prompt
    - single image-to-video：pass image_url
    - multi reference image：pass image_urls list
    - first/last frame：pass image_url + tail_image_url
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
        image_url: str = None,        # first frame/single image
        image_urls: List[str] = None,  # multi reference image
        tail_image_url: str = None,    # last frame
        output: str = None
    ) -> Dict[str, Any]:
        """
        unified video generation method

        Args:
            prompt: videodescription
            duration: duration(3-15s)
            aspect_ratio: aspect ratio (16:9, 9:16, 1:1)
            generate_audio: whether to generate audio
            image_url: first frameimage（pathor URL）
            image_urls: reference image list（pathor URL）
            tail_image_url: last frameimage（pathor URL）
            output: output file path
        """
        payload = {
            "prompt": prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
            "generate_audio": generate_audio
        }

        # first frame/single image (fal.ai use start_image_url)
        if image_url:
            payload["start_image_url"] = self._prepare_image_url(image_url)

        # multi reference image (fal.ai use image_urls，prompt used in @Image1 reference)
        if image_urls:
            payload["image_urls"] = [self._prepare_image_url(img) for img in image_urls]

        # last frame (fal.ai use end_image_url)
        if tail_image_url:
            payload["end_image_url"] = self._prepare_image_url(tail_image_url)

        return await self._submit_and_wait(payload, output)

    def _prepare_image_url(self, image_path: str) -> str:
        """prepare images URL（local file convert data URI）"""
        if image_path.startswith(('http://', 'https://')):
            return image_path
        return self._file_to_data_uri(image_path)

    def _file_to_data_uri(self, file_path: str) -> str:
        """convert local file to data URI format base64"""
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        with open(file_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/{ext};base64,{data}"

    async def _submit_and_wait(self, payload: dict, output: str = None) -> Dict[str, Any]:
        """submit task and wait for completion"""
        import time

        logger.info(f"📤 create fal Kling task: {payload.get('prompt', '')[:50]}...")

        try:
            # use fal_client submit task，return AsyncRequestHandle
            handle = await self.fal_client.submit(self.MODEL_ID, arguments=payload)
            request_id = handle.request_id
            logger.info(f"✅ fal task submitted: {request_id}")
        except Exception as e:
            logger.error(f"❌ fal task submitfailed: {e}")
            return {"success": False, "error": str(e)}

        # wait for completion
        video_url = await self._wait_for_completion(handle)

        if video_url and output:
            await self._download_file(video_url, output)
            return {"success": True, "video_url": video_url, "output": output, "request_id": request_id}

        return {"success": bool(video_url), "video_url": video_url, "request_id": request_id}

    async def _wait_for_completion(self, handle, max_wait: int = 600) -> Optional[str]:
        """waittask complete"""
        import time

        logger.info(f"⏳ wait fal task complete: {handle.request_id}")
        start_time = time.monotonic()

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ fal task timeout ({max_wait}s)")
                return None

            try:
                # use handle.status() check status
                status = await handle.status()
                # status is an object，like InProgress or Completed
                status_class = status.__class__.__name__
                logger.info(f"   [{int(elapsed)}s] status: {status_class}")

                if status_class == "Completed":
                    # use handle.get() get result
                    result = await handle.get()
                    video_url = result.get("video", {}).get("url")
                    if video_url:
                        logger.info(f"✅ fal task complete (takes time: {int(elapsed)}s)")
                        return video_url
                    else:
                        logger.error(f"❌ fal task resultno videoURL: {result}")
                        return None
                elif status_class == "Failed":
                    error = getattr(status, 'error', None) or "Unknown error"
                    logger.error(f"❌ fal task fail: {error}")
                    return None
            except Exception as e:
                logger.warning(f"   query statusexception: {e}")

            await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """download file"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        response = await self.http_client.get(url)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"✅ saved to: {output_path}")

    async def close(self):
        await self.http_client.aclose()


class SeedanceClient:
    """
    Seedance 2 video generation client（via piapi.ai proxy）

    core capability：
    - Text-to-Video: directly pass prompt（mode: text_to_video）
    - First/Last Frames: 1-2 images as first/last frames（mode: first_last_frames）
    - Omni Reference: multimodal reference - image/video/audio（mode: omni_reference）

    key parameter：
    - model: "seedance"（fixed）
    - task_type: "seedance-2-fast"（fast）or "seedance-2"（high quality）
    - mode: "text_to_video" | "first_last_frames" | "omni_reference"（required）
    - duration: 4-15s（any integer）
    - aspect_ratio: 21:9 | 16:9 | 4:3 | 1:1 | 3:4 | 9:16 | auto
    - image_urls: max 12 reference images
    - video_urls: max 1 reference videos（omni_reference mode）
    - audio_urls: audioreference（omni_reference mode，mp3/wav，≤15s）

    Prompt syntax：
    - imagereference: "@image1" reference first image
    - video reference: "@video1" reference video
    - audioreference: "@audio1" reference audio
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
        submit video generation task

        Args:
            prompt: videodescription（support @imageN / @videoN / @audioN reference）
            duration: duration（4-15s，any integer）
            aspect_ratio: aspect ratio（21:9 | 16:9 | 4:3 | 1:1 | 3:4 | 9:16 | auto）
            image_urls: reference image list（max 12）
            video_urls: referencevideo list（omni_reference mode）
            audio_urls: referenceaudio list（omni_reference mode，mp3/wav，≤15s）
            mode: generation mode（text_to_video | first_last_frames | omni_reference）
            model: "seedance-2-fast" or "seedance-2"
            output: output file path
        """
        # autoinfer mode
        if mode is None:
            if video_urls or audio_urls:
                mode = "omni_reference"
            elif image_urls:
                mode = "omni_reference"
            else:
                mode = "text_to_video"

        # duration validation（4-15）
        duration = max(4, min(15, duration))

        # aspect_ratio validation
        if aspect_ratio not in self.VALID_ASPECT_RATIOS:
            logger.warning(f"⚠️ aspect_ratio {aspect_ratio} not in support list，use 16:9")
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

        # prepare reference resources
        if image_urls:
            payload["input"]["image_urls"] = [self._prepare_url(img) for img in image_urls]

        if video_urls:
            payload["input"]["video_urls"] = [self._prepare_url(v) for v in video_urls]

        if audio_urls:
            payload["input"]["audio_urls"] = [self._prepare_url(a) for a in audio_urls]

        logger.info(f"📤 create Seedance task: {prompt[:80]}...")
        logger.info(f"   parameter: mode={mode}, duration={duration}s, aspect_ratio={aspect_ratio}, model={model}")

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
                logger.error(f"❌ API not returned task_id: {error}")
                return {"success": False, "error": error.get("message", "Unknown error")}

            logger.info(f"✅ Seedance task created: {task_id}")

            # wait for completion
            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": bool(video_url), "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ Seedance task fail: {e}")
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
        completevideogeneration flow（shortcut method）
        """
        return await self.submit_task(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            image_urls=image_urls,
            output=output
        )

    async def check_task(self, task_id: str) -> Dict[str, Any]:
        """querytask status"""
        try:
            response = await self.client.get(
                f"{Config.SEEDANCE_BASE_URL}{self.STATUS_PATH.format(task_id=task_id)}",
                headers={"Authorization": f"Bearer {Config.SEEDANCE_API_KEY}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"⚠️ query taskstatus failure: {e}")
            return {"error": str(e)}

    def _prepare_url(self, path: str) -> str:
        """prepare URL（local file convert data URI）"""
        if path.startswith(('http://', 'https://')):
            return path
        return self._file_to_data_uri(path)

    def _file_to_data_uri(self, file_path: str) -> str:
        """convert local file to data URI format base64

        note：piapi.ai for requestbody size has limit，large imageneeds compression
        but image resolution cannot be too small，otherwise error "material is too small" error
        """
        # check file size
        file_size = os.path.getsize(file_path)
        max_size = 100 * 1024  # 100KB threshold

        if file_size > max_size:
            # compress image
            logger.info(f"📦 image is large ({file_size/1024:.1f}KB)，compressing...")
            try:
                from PIL import Image
                import io

                img = Image.open(file_path)

                # first try without changing resolution，only adjust JPEG quality
                # If quality=50 still exceeds 100KB，then consider reducing resolution
                for quality in [70, 50, 30]:
                    buffer = io.BytesIO()
                    img_rgb = img.convert('RGB') if img.mode != 'RGB' else img
                    img_rgb.save(buffer, format='JPEG', quality=quality)
                    compressed_size = buffer.tell()

                    if compressed_size <= max_size:
                        data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        logger.info(f"✅ compressingcompletion ({len(data)/1024:.1f}KB, quality={quality})")
                        return f"data:image/jpeg;base64,{data}"

                # If quality=30 stilltoo large，then reduce resolution（but keep minimum side >= 720px）
                img_resized = img.copy()
                while True:
                    w, h = img_resized.size
                    min_dim = min(w, h)
                    if min_dim <= 720:
                        # already small enough 720px，cannot be smaller
                        break
                    # shrink 20%
                    new_w, new_h = int(w * 0.8), int(h * 0.8)
                    img_resized = img_resized.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    buffer = io.BytesIO()
                    img_rgb = img_resized.convert('RGB') if img_resized.mode != 'RGB' else img_resized
                    img_rgb.save(buffer, format='JPEG', quality=50)
                    if buffer.tell() <= max_size:
                        break

                data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                logger.info(f"✅ compressingcompletion ({len(data)/1024:.1f}KB, resized to {img_resized.size})")
                return f"data:image/jpeg;base64,{data}"
            except Exception as e:
                logger.warning(f"⚠️ image compression failed，use original image: {e}")

        # directly read small image
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        with open(file_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/{ext};base64,{data}"

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """waittask complete"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ wait Seedance task complete: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Seedance task timeout ({max_wait}s)")
                return None

            try:
                result = await self.check_task(task_id)
                data = result.get("data", {})
                status = data.get("status", "unknown")

                logger.info(f"   [{int(elapsed)}s] status: {status}")

                if status == "completed":
                    video_url = data.get("output", {}).get("video")
                    if video_url:
                        logger.info(f"✅ Seedance task complete (takes time: {int(elapsed)}s)")
                        return video_url
                    else:
                        logger.error(f"❌ no video in result URL: {data}")
                        return None

                elif status == "failed":
                    error = data.get("error", {})
                    logs = data.get("logs", [])
                    # logs usually contains more detailederror reason
                    error_detail = error.get("message", "Unknown")
                    if logs:
                        # find the first non-empty meaningfullog
                        for log in logs:
                            if log and "restored" not in log.lower():
                                error_detail = log
                                break
                    logger.error(f"❌ Seedance task fail: {error_detail}")
                    return None

                await asyncio.sleep(10)

            except Exception as e:
                logger.warning(f"⚠️ query exception: {e}")
                await asyncio.sleep(10)

    async def _download_file(self, url: str, output_path: str):
        """download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


class FalSeedanceClient:
    """
    Seedance 2.0 video generation client（passed fal.ai）

    only use reference-to-video endpoint：
    - fast: https://queue.fal.run/bytedance/seedance-2.0/fast/reference-to-video
    - high_quality: https://queue.fal.run/bytedance/seedance-2.0/reference-to-video

    parameter:
    - prompt: videodescription（support @Image1/@Video1/@Audio1 reference）
    - image_urls: reference image list（max 9，each≤30MB）
    - video_urls: referencevideo list（max 3，total duration2-15s）
    - audio_urls: referenceaudio list（max 3，total duration≤15s）
    - resolution: "480p" | "720p"
    - duration: "auto" | 4-15
    - aspect_ratio: auto/21:9/16:9/4:3/1:1/3:4/9:16
    - generate_audio: boolean
    - seed: integer
    - end_user_id: string
    - model: "fast" | "high_quality"

    mode distinction（passed image_urls parameter）：
    - not pass image_urls → text-to-video（pure text-to）
    - pass image_urls → reference-to-video（reference image generate）
    """

    BASE_URL = "https://queue.fal.run/bytedance/seedance-2.0"
    ENDPOINT_FAST = "/fast/reference-to-video"
    ENDPOINT_HIGH_QUALITY = "/reference-to-video"

    VALID_ASPECT_RATIOS = ["auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]
    VALID_RESOLUTIONS = ["480p", "720p"]

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )

    def _select_endpoint(self, model: str = "fast") -> str:
        if model == "high_quality":
            return self.BASE_URL + self.ENDPOINT_HIGH_QUALITY
        return self.BASE_URL + self.ENDPOINT_FAST

    def _prepare_url(self, path: str) -> str:
        if path.startswith(('http://', 'https://')):
            return path
        return self._file_to_data_uri(path)

    def _file_to_data_uri(self, file_path: str) -> str:
        try:
            from PIL import Image
            import io
            file_size = os.path.getsize(file_path)
            max_size = 100 * 1024
            if file_size > max_size:
                logger.info(f"📦 image is large ({file_size/1024:.1f}KB)，compressing...")
                img = Image.open(file_path)
                for quality in [70, 50, 30]:
                    buffer = io.BytesIO()
                    img_rgb = img.convert('RGB') if img.mode != 'RGB' else img
                    img_rgb.save(buffer, format='JPEG', quality=quality)
                    if buffer.tell() <= max_size:
                        data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        return f"data:image/jpeg;base64,{data}"
                img_resized = img.copy()
                while min(img_resized.size) > 720:
                    w, h = img_resized.size
                    img_resized = img_resized.resize((int(w*0.8), int(h*0.8)), Image.Resampling.LANCZOS)
                    buffer = io.BytesIO()
                    img_rgb = img_resized.convert('RGB') if img_resized.mode != 'RGB' else img_resized
                    img_rgb.save(buffer, format='JPEG', quality=50)
                    if buffer.tell() <= max_size:
                        break
                data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return f"data:image/jpeg;base64,{data}"
            ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            if ext == 'jpg': ext = 'jpeg'
            with open(file_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/{ext};base64,{data}"
        except Exception as e:
            logger.warning(f"⚠️ imageprocessing failed: {e}")
            ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            if ext == 'jpg': ext = 'jpeg'
            with open(file_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/{ext};base64,{data}"

    async def submit_task(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_urls: List[str] = None,
        video_urls: List[str] = None,
        audio_urls: List[str] = None,
        resolution: str = "720p",
        seed: int = None,
        end_user_id: str = None,
        generate_audio: bool = True,
        model: str = "fast",
        output: str = None
    ) -> Dict[str, Any]:
        endpoint = self._select_endpoint(model)
        if aspect_ratio not in self.VALID_ASPECT_RATIOS:
            aspect_ratio = "16:9"
        if resolution not in self.VALID_RESOLUTIONS:
            resolution = "720p"

        payload = {
            "prompt": prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "generate_audio": generate_audio
        }
        if image_urls:
            payload["image_urls"] = [self._prepare_url(img) for img in image_urls]
        if video_urls:
            payload["video_urls"] = [self._prepare_url(v) for v in video_urls]
        if audio_urls:
            payload["audio_urls"] = [self._prepare_url(a) for a in audio_urls]
        if seed is not None:
            payload["seed"] = seed
        if end_user_id:
            payload["end_user_id"] = end_user_id

        logger.info(f"📤 create FalSeedance task: {prompt[:60]}...")
        logger.info(f"   Endpoint: {endpoint}, duration={duration}s, resolution={resolution}")

        try:
            response = await self.client.post(
                endpoint,
                json=payload,
                headers={"Authorization": f"Key {Config.FAL_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()
            request_id = result.get("request_id")
            if not request_id:
                return {"success": False, "error": "No request_id returned"}

            video_result = await self._wait_for_completion(request_id)
            # check return type：str = success，dict = error
            if isinstance(video_result, dict) and "error" in video_result:
                # return completeerror message
                return {
                    "success": False,
                    "error": video_result.get("error"),
                    "message": video_result.get("message"),
                    "ctx": video_result.get("ctx"),
                    "request_id": request_id
                }
            elif video_result and isinstance(video_result, str) and output:
                await self._download_file(video_result, output)
                return {"success": True, "video_url": video_result, "output": output, "request_id": request_id}
            return {"success": bool(video_result), "video_url": video_result, "request_id": request_id}
        except Exception as e:
            logger.error(f"❌ FalSeedance task fail: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_completion(self, request_id: str, max_wait: int = 600) -> Optional[str]:
        import time
        start = time.monotonic()
        status_url = f"{self.BASE_URL}/requests/{request_id}/status"
        result_url = f"{self.BASE_URL}/requests/{request_id}"
        logger.info(f"⏳ wait FalSeedance task: {request_id}")

        while True:
            elapsed = time.monotonic() - start
            if elapsed > max_wait:
                logger.error(f"❌ FalSeedance task timeout")
                return None
            try:
                resp = await self.client.get(status_url, headers={"Authorization": f"Key {Config.FAL_API_KEY}"})
                data = resp.json()
                status = data.get("status", "unknown")
                logger.info(f"   [{int(elapsed)}s] {status}")
                if status == "COMPLETED":
                    resp = await self.client.get(result_url, headers={"Authorization": f"Key {Config.FAL_API_KEY}"})
                    result = resp.json()
                    # check if there is API error（like content_policy_violation）
                    if resp.status_code != 200 or "detail" in result:
                        error_detail = result.get("detail", [])
                        if error_detail and isinstance(error_detail, list):
                            # extract details of the first error
                            err = error_detail[0]
                            error_type = err.get("type", "unknown")
                            error_msg = err.get("msg", str(err))
                            error_ctx = err.get("ctx", {})
                            logger.error(f"❌ FalSeedance API error: [{error_type}] {error_msg}")
                            if error_ctx:
                                logger.error(f"   details: {error_ctx}")
                            # return containingerror messagestructure，let upper layer handle
                            return {"error": error_type, "message": error_msg, "ctx": error_ctx}
                        logger.error(f"❌ FalSeedance API error: {result}")
                        return {"error": "api_error", "message": str(result)}
                    url = result.get("video", {}).get("url")
                    if url:
                        logger.info(f"✅ FalSeedance completion (takes time: {int(elapsed)}s)")
                        return url
                    return {"error": "no_video_url", "message": "Result has no video URL"}
                elif status == "FAILED":
                    logger.error(f"❌ FalSeedance failed: {data}")
                    return None
                await asyncio.sleep(10)
            except Exception as e:
                logger.warning(f"⚠️ query exception: {e}")
                await asyncio.sleep(10)

    async def _download_file(self, url: str, output_path: str):
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(resp.content)
        logger.info(f"✅ saved: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Veo3 Video Generation (Deprecated) ==============


class Veo3Client:
    """
    Google Veo3 video generation client（via Migoo LLM PROXY）

    .. deprecated::
        Veo3 backenddeprecated and no longer supported。please use Kling、Kling-Omni or Seedance。
        this typekept only for backward compatibility，will be removed in future version。
    """

    def __init__(self):
        import warnings
        warnings.warn(
            "Veo3Client deprecated, please use KlingClient、KlingOmniClient or SeedanceClient",
            DeprecationWarning,
            stacklevel=2
        )
        import httpx
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))
        self.api_key = Config.MIGOO_API_KEY
        self.base_url = Config.MIGOO_VIDEO_URL

    async def close(self):
        await self.client.aclose()

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        output: str = "output.mp4"
    ) -> Dict[str, Any]:
        """text-to-video"""
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
        """image-to-video（first frame image）"""
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
        """coregeneration flow：submit → poll → download"""
        # validationduration
        valid_durations = [4, 6, 8]
        if duration not in valid_durations:
            closest = min(valid_durations, key=lambda x: abs(x - duration))
            logger.warning(f"⚠️ Veo3 duration {duration}s not supported，adjusted to {closest}s")
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

        logger.info(f"📤 Veo3 video generation: {prompt[:50]}... ({duration}s, {aspect_ratio})")

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
            return {"success": False, "error": f"Veo3 submit failed: {e}"}

        operation_name = result.get("name")
        if not operation_name:
            return {"success": False, "error": f"no operation name: {result}"}

        logger.info(f"⏳ task submitted，waitgenerate...")

        # poll
        video_url = await self._wait_for_completion(operation_name)
        if not video_url:
            return {"success": False, "error": "Veo3 generation failedortimeout"}

        # download
        await self._download_file(video_url, output)
        return {
            "success": True,
            "output": output,
            "video_url": video_url,
            "duration": duration
        }

    async def _wait_for_completion(self, operation_name: str, max_wait: int = 600) -> Optional[str]:
        """polltask status"""
        import time
        start_time = time.monotonic()

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Veo3 task timeout ({max_wait}s)")
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
                    # check if there are errors
                    if "error" in result:
                        error_msg = result["error"].get("message", "Unknown error")
                        logger.error(f"❌ Veo3 task fail: {error_msg}")
                        return None

                    # extractvideo URL
                    videos = result.get("response", {}).get("videos", [])
                    if videos:
                        video_url = videos[0].get("uri") or videos[0].get("gcsUri")
                        cost = result.get("priceCostUsd", 0)
                        logger.info(f"✅ Veo3 generatecompletion (takes time: {int(elapsed)}s, cost: ${cost})")
                        return video_url
                    else:
                        logger.error(f"❌ no video in response: {result}")
                        return None

                logger.info(f"   [{int(elapsed)}s] generating...")
                await asyncio.sleep(10)

            except Exception as e:
                logger.warning(f"⚠️ pollexception: {e}")
                await asyncio.sleep(10)

    async def _download_file(self, url: str, output_path: str):
        """downloadvideo file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=300.0) as dl_client:
            response = await dl_client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ saved to: {output_path}")

    def _encode_image(self, image_path: str) -> str:
        """encode image as base64"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _get_mime_type(self, image_path: str) -> str:
        """get image MIME type"""
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
        """generatemusic"""
        payload = {
            "prompt": prompt,
            "instrumental": instrumental,
            "model": Config.SUNO_MODEL,
            "customMode": True,
            "style": style,
            "callbackUrl": "https://example.com/callback"
        }

        # truncate too long prompt（avoid log too long），does not affect passing to API parameter
        display_prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
        logger.info(f"📤 createmusic generation task - description: {display_prompt}, style: {style}")

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
            logger.info(f"✅ task created: {task_id}")

            audio_url = await self._wait_for_completion(task_id)

            if audio_url and output:
                await self._download_file(audio_url, output)
                return {"success": True, "audio_url": audio_url, "output": output}

            return {"success": True, "audio_url": audio_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ music generationfailed: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 300) -> Optional[str]:
        """waittask complete"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ waitmusic generation...")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ task timeout ({max_wait}s)")
                return None

            try:
                response = await self.client.get(
                    f"{Config.SUNO_API_URL}/generate/record-info?taskId={task_id}",
                    headers={"Authorization": f"Bearer {Config.SUNO_API_KEY}"}
                )
                response.raise_for_status()
                result = response.json()

                if result.get("code") != 200:
                    logger.warning(f"⚠️ query failed: {result.get('msg')}")
                    await asyncio.sleep(5)
                    continue

                data = result.get("data", {})
                status = data.get("status")

                if status == "SUCCESS":
                    tracks = data.get("response", {}).get("sunoData", [])
                    if tracks:
                        audio_url = tracks[0].get("audioUrl")
                        logger.info(f"✅ music generationcompletion (takes time: {int(elapsed)}s)")
                        return audio_url

                elif status == "FAILED":
                    logger.error("❌ music generationfailed")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ query failed: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """download file"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ saved to: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Volcano Engine TTS (Deprecated) ==============


class TTSClient:
    """
    Volcano Engine TTS client

    .. deprecated::
        Volcano Engine TTS deprecated and no longer supported。please use Gemini TTS（need MIGOO_API_KEY）。
        this typekept only for backward compatibility，will be removed in future version。
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
            "TTSClient（Volcano Engine）deprecated, please use GeminiTTSClient",
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
        """synthesize voice"""
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
            logger.error(f"❌ TTSfailed: {e}")
            return {"success": False, "error": str(e)}


# ============== Gemini TTS（via Migoo LLM API）==============

class GeminiTTSClient:
    """Gemini TTS client（via Migoo LLM API）"""

    # Gemini TTS voice
    VOICE_TYPES = {
        # female voice
        "female_narrator": ("Kore", "cmn-CN"),      # standardfemale voice
        "female_gentle": ("Aoede", "cmn-CN"),        # clearfemale voice
        "female_soft": ("Zephyr", "cmn-CN"),         # soft female voice
        "female_bright": ("Leda", "cmn-CN"),         # brightfemale voice
        # male voice
        "male_narrator": ("Charon", "cmn-CN"),       # standardmale voice
        "male_warm": ("Orus", "cmn-CN"),             # steadymale voice
        "male_deep": ("Fenrir", "cmn-CN"),           # deep male voice
        "male_bright": ("Puck", "cmn-CN"),           # bright male voice
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
        """synthesize voice

        Args:
            text: text to read，support inline emotion taglike [brightly], [sigh], [pause]
            output: output file path
            voice: voice name or preset（female_narrator, male_narrator, etc）
            emotion: deprecated, please use prompt or inline mark
            speed: speech rate（Gemini TTS currently not supported）
            prompt: style instruction，control accent/emotion/tone/speech rate/character design
            language_code: language code（cmn-CN, en-US, ja-JP, etc）
        """
        from google.cloud import texttospeech
        from google.api_core import client_options

        if not Config.MIGOO_API_KEY:
            return {
                "success": False,
                "error": "MIGOO_API_KEY not configured",
                "hint": "please in config.json add MIGOO_API_KEY"
            }

        # Auto-add speed instruction for Chinese narration
        if language_code == "cmn-CN" and not prompt:
            prompt = "speech rate is fast，crisp and clear，natural fluent"
            logger.info(f"📝 Auto-add prompt for Chinese narration: {prompt}")

        # get voice config
        voice_name = voice
        lang_code = language_code
        if voice in self.VOICE_TYPES:
            voice_name, lang_code = self.VOICE_TYPES[voice]

        logger.info(f"📤 Gemini TTS synthesis: {text[:30]}... (voice: {voice_name})")

        try:
            # create client
            client = texttospeech.TextToSpeechClient(
                client_options=client_options.ClientOptions(
                    api_endpoint="https://inner-api.us.migoo.shopee.io/inbeeai/compass-api/v1",
                    api_key=Config.MIGOO_API_KEY,
                ),
                transport="rest",
            )

            # build input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            if prompt:
                synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

            # voice config
            voice_params = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                name=voice_name,
                model_name="gemini-2.5-flash-tts",
            )

            # audioconfig
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
            )

            # synthesize voice
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )

            # savefile
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, "wb") as f:
                f.write(response.audio_content)

            # use ffprobe to get precise duration
            duration = get_audio_duration(output)
            duration_ms = int(duration * 1000)
            logger.info(f"✅ Gemini TTS saved: {output} ({duration:.2f}s)")

            return {"success": True, "output": output, "duration": duration, "duration_ms": duration_ms}

        except Exception as e:
            logger.error(f"❌ Gemini TTSfailed: {e}")
            return {"success": False, "error": str(e)}


class ElevenLabsTTSClient:
    """ElevenLabs TTS client（via fal.ai API）

    three-step workflow：Design → Create → TTS
    Priority: ElevenLabs TTS > Gemini TTS(fallback)
    """

    # fal.ai API endpoint
    ENDPOINTS = {
        "design": "fal-ai/elevenlabs/text-to-voice/design/eleven-v3",
        "create": "fal-ai/elevenlabs/text-to-voice/create",
        "tts": "fal-ai/elevenlabs/tts/eleven-v3"
    }

    # built-in voice（can directly use，no need Design/Create）
    BUILTIN_VOICES = {
        "rachel": "warmfemale voice，emotionally rich",
        "adam": "deep male voice，professional and steady",
        "charlotte": "clearfemale voice，energetic",
        "callum": "youngmale voice，friendlynatural",
        "george": "maturemale voice，steady and powerful",
        "alice": "gentlefemale voice，softfriendly",
        "aria": "drama female voice, high expressiveness"
    }

    # voice_style to built-in voice and stability mapping
    VOICE_STYLE_MAP = {
        # female voice
        "female_narrator": {
            "builtin": None,  # need to create new voice
            "design_prompt": "Chinese Mandarin accent. Female, 30-35 years old. Medium-low pitch. Studio quality spoken performance. Character: Professional narrator, documentary style. Emotional arc: calm → informative → confident. Style: Clear and measured, with subtle warmth. Pace: Moderate, consistent delivery. Spoken, not sung.",
            "stability": 0.32
        },
        "female_gentle": {
            "builtin": "Alice",
            "design_prompt": "Chinese Mandarin accent. Female, 25-30 years old. Medium pitch, soft tone. Studio quality spoken performance. Character: Gentle storyteller, warm and caring. Emotional arc: soft → tender → reassuring. Style: Gentle and flowing, with natural pauses. Pace: Slow to moderate, unhurried. Spoken, not sung.",
            "stability": 0.28
        },
        "female_soft": {
            "builtin": None,
            "design_prompt": "Chinese Mandarin accent. Female, 20-25 years old. Soft, breathy quality. Studio quality spoken performance. Character: Soft-spoken companion, intimate and close. Emotional arc: quiet → intimate → peaceful. Style: Whispery and close, with gentle emphasis. Pace: Slow, deliberate. Spoken, not sung.",
            "stability": 0.25
        },
        "female_bright": {
            "builtin": "Charlotte",
            "design_prompt": "Chinese Mandarin accent. Female, 20-25 years old. Bright, energetic pitch. Studio quality spoken performance. Character: Energetic presenter, upbeat and engaging. Emotional arc: bright → excited → enthusiastic. Style: Bright and animated, with dynamic energy. Pace: Quick, rhythmic. Spoken, not sung.",
            "stability": 0.30
        },
        # male voice
        "male_narrator": {
            "builtin": "George",
            "design_prompt": "Chinese Mandarin accent. Male, 35-40 years old. Deep, resonant pitch. Studio quality spoken performance. Character: Professional narrator, authoritative and clear. Emotional arc: steady → authoritative → confident. Style: Deep and measured, with gravitas. Pace: Moderate, controlled. Spoken, not sung.",
            "stability": 0.32
        },
        "male_warm": {
            "builtin": "Adam",
            "design_prompt": "Chinese Mandarin accent. Male, 30-35 years old. Warm, rich timbre. Studio quality spoken performance. Character: Warm host, friendly and approachable. Emotional arc: warm → welcoming → sincere. Style: Warm and inviting, with natural warmth. Pace: Moderate, relaxed. Spoken, not sung.",
            "stability": 0.28
        },
        "male_deep": {
            "builtin": None,
            "design_prompt": "Chinese Mandarin accent. Male, 40-45 years old. Very deep, powerful voice. Studio quality spoken performance. Character: Deep narrator, commanding presence. Emotional arc: powerful → authoritative → commanding. Style: Deep and resonant, with weight. Pace: Slow, deliberate. Spoken, not sung.",
            "stability": 0.35
        },
        "male_bright": {
            "builtin": "Callum",
            "design_prompt": "Chinese Mandarin accent. Male, 25-30 years old. Bright, clear pitch. Studio quality spoken performance. Character: Energetic presenter, dynamic and engaging. Emotional arc: energetic → dynamic → animated. Style: Bright and punchy, with energy. Pace: Quick, rhythmic. Spoken, not sung.",
            "stability": 0.30
        }
    }

    # video type to stability mapping
    STABILITY_MAP = {
        "cinematic": 0.22,      # drama character，high expressiveness
        "vlog": 0.28,           # emotional narrative，balancestable
        "documentary": 0.35,    # professional narration，more stable
        "commercial": 0.30,     # commercial，stable but flexible
        "artistic": 0.20        # art/experimental，maximum expressiveness
    }

    # text enhancement tag
    ENHANCE_TAGS = {
        "emotion": ["[thoughtful]", "[curious]", "[excited]", "[calm]", "[reassuring]", "[hopeful]"],
        "rhythm": ["[short pause]", "[long pause]", "[pause]", "[slows down]", "[deliberate]", "[emphasized]"],
        "physio": ["[sighs]", "[exhales]", "[breathes]", "[clears throat]"]
    }

    def _pad_design_text(self, text: str, min_length: int = 100) -> str:
        """ensure design sample text meets minimum length requirement"""
        if len(text) >= min_length:
            return text[:1000]
        # supplemental filler text
        filler = "This is a sample text for voice design，please ignore the content itself，focus on voice tone and expression。voice should be gentle and emotional，suitable for storytelling and memories。"
        return f"{text} {filler}"[:1000]

    def _enhance_text(self, text: str, video_type: str = None) -> str:
        """text enhancement：insertemotion/rhythm/physiology tag

        rule：do not rewrite original wording，only change punctuation、insert tag
        """
        if not text:
            return text

        # based on video typetype selection enhancement frequency
        frequencies = {
            "cinematic": 0.6,
            "vlog": 0.4,
            "documentary": 0.3,
            "commercial": 0.5,
            "artistic": 0.7
        }
        freq = frequencies.get(video_type, 0.4)

        # split sentences（Chinese-English compatible）
        import re
        sentences = re.split(r'([。！？.!?])', text)

        enhanced = []
        tag_idx = 0

        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""

            if sentence.strip():
                # determine whether to add tags by frequency
                if (tag_idx % 3) < int(freq * 3):
                    # select tag type
                    tag_type = tag_idx % 3
                    if tag_type == 0:
                        tag = self.ENHANCE_TAGS["emotion"][tag_idx % len(self.ENHANCE_TAGS["emotion"])]
                    elif tag_type == 1:
                        tag = self.ENHANCE_TAGS["rhythm"][tag_idx % len(self.ENHANCE_TAGS["rhythm"])]
                    else:
                        tag = self.ENHANCE_TAGS["physio"][tag_idx % len(self.ENHANCE_TAGS["physio"])]

                    enhanced.append(f"{tag} {sentence}{punct}")
                else:
                    enhanced.append(f"{sentence}{punct}")

                tag_idx += 1

        # process remaining part
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            enhanced.append(sentences[-1])

        return " ".join(enhanced)

    async def _call_fal(self, endpoint: str, payload: dict) -> dict:
        """call fal.ai API"""
        import fal_client

        # set FAL_KEY
        if Config.FAL_API_KEY:
            os.environ["FAL_KEY"] = Config.FAL_API_KEY

        try:
            result = fal_client.subscribe(endpoint, payload, with_logs=False)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _download_audio(self, url: str, output: str) -> bool:
        """downloadaudio file"""
        import requests
        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            logger.error(f"❌ audio download failed: {e}")
            return False

    async def design_voice(self, design_prompt: str, sample_text: str = None) -> Dict[str, Any]:
        """Design endpoint：generate voice preview

        Args:
            design_prompt: voice design description（follow template format）
            sample_text: optional sample text（forpreview）

        Returns:
            {"success": True, "previews": [...], "selected_voice_id": "..."}
        """
        payload = {
            "prompt": design_prompt,
            "text": self._pad_design_text(sample_text or design_prompt),
            "auto_generate_text": False,
            "loudness": 0.5,
            "guidance_scale": 5,
            "output_format": "mp3_44100_128"
        }

        logger.info(f"📤 ElevenLabs Design: {design_prompt[:50]}...")
        result = await self._call_fal(self.ENDPOINTS["design"], payload)

        if not result.get("success"):
            return result

        previews = result["result"].get("previews", [])
        if not previews:
            return {"success": False, "error": "No voice previews generated"}

        selected_id = previews[0].get("generated_voice_id")
        preview_url = previews[0].get("audio", {}).get("url") if isinstance(previews[0].get("audio"), dict) else previews[0].get("audio")

        logger.info(f"✅ ElevenLabs Design completion，selected voice_id: {selected_id}")

        return {
            "success": True,
            "previews": previews,
            "selected_voice_id": selected_id,
            "preview_url": preview_url
        }

    async def create_voice(self, voice_name: str, voice_description: str,
                          generated_voice_id: str) -> Dict[str, Any]:
        """Create endpoint：create permanent voice_id

        Args:
            voice_name: unique voice name
            voice_description: voice description（requires ≥20 characters）
            generated_voice_id: Design returned preview ID

        Returns:
            {"success": True, "voice_id": "..."}
        """
        # ensure voice_description long enough
        if len(voice_description) < 20:
            voice_description = f"{voice_description}，high-quality professional recording-grade voice performance"

        payload = {
            "voice_name": voice_name,
            "voice_description": voice_description,
            "generated_voice_id": generated_voice_id,
            "labels": {"locale": "zh"}
        }

        logger.info(f"📤 ElevenLabs Create: {voice_name}")
        result = await self._call_fal(self.ENDPOINTS["create"], payload)

        if not result.get("success"):
            return result

        voice_id = result["result"].get("voice_id", generated_voice_id)
        logger.info(f"✅ ElevenLabs Create completion，voice_id: {voice_id}")

        return {
            "success": True,
            "voice_id": voice_id,
            "voice_name": voice_name
        }

    async def synthesize(
        self,
        text: str,
        output: str,
        voice_id: str = None,
        voice_style: str = None,
        stability: float = None,
        video_type: str = None,
        enhance_text: bool = True,
        voice_name: str = None,
        language: str = "zh"
    ) -> Dict[str, Any]:
        """TTS synthesize（completeworkflow）

        Args:
            text: text to read
            output: output file path
            voice_id: existing voice_id（skip Design/Create）
            voice_style: voice style（map to design_prompt or builtin voice）
            stability: stable param（0-1，lower is more dramatic）
            video_type: video type（used for auto adjustment stability）
            enhance_text: whether to enhance text（insert emotion tags）
            voice_name: new voice name（for Create）
            language: language code（ISO 639-1）

        Returns:
            {"success": True, "output": "...", "duration": ..., "voice_id": "..."}
        """
        # check FAL_API_KEY
        if not Config.FAL_API_KEY:
            return {
                "success": False,
                "error": "FAL_API_KEY not configured",
                "hint": "please in config.json add FAL_API_KEY",
                "fallback": True  # mark as degradable
            }

        # Step 1: confirm voice_id
        final_voice_id = voice_id

        if not final_voice_id and voice_style:
            style_config = self.VOICE_STYLE_MAP.get(voice_style)

            if style_config and style_config.get("builtin"):
                # usebuilt-in voice
                final_voice_id = style_config["builtin"]
                logger.info(f"📝 usebuilt-in voice: {final_voice_id}")
            elif style_config:
                # need to create new voice
                design_result = await self.design_voice(
                    design_prompt=style_config["design_prompt"],
                    sample_text=text[:50]
                )

                if not design_result.get("success"):
                    return {
                        "success": False,
                        "error": design_result.get("error"),
                        "fallback": True
                    }

                # Create voice
                import time
                vname = voice_name or f"{voice_style}_{int(time.time())}"
                create_result = await self.create_voice(
                    voice_name=vname,
                    voice_description=style_config["design_prompt"][:200],
                    generated_voice_id=design_result["selected_voice_id"]
                )

                if not create_result.get("success"):
                    return {
                        "success": False,
                        "error": create_result.get("error"),
                        "fallback": True
                    }

                final_voice_id = create_result["voice_id"]
                logger.info(f"📝 create new voice: {vname} → {final_voice_id}")
            else:
                # unknown voice_style，use default built-in voice
                final_voice_id = "alice"
                logger.info(f"📝 unknown voice_style，use default: alice")

        if not final_voice_id:
            final_voice_id = "rachel"  # defaultbuilt-in voice

        # Step 2: text enhancement（optional）
        final_text = text
        if enhance_text:
            final_text = self._enhance_text(text, video_type)
            if final_text != text:
                logger.info(f"📝 text enhanced")

        # Step 3: confirm stability
        if stability is None:
            if video_type and video_type in self.STABILITY_MAP:
                stability = self.STABILITY_MAP[video_type]
            elif voice_style and voice_style in self.VOICE_STYLE_MAP:
                stability = self.VOICE_STYLE_MAP[voice_style].get("stability", 0.28)
            else:
                stability = 0.28

        # Step 4: TTS synthesize
        logger.info(f"📤 ElevenLabs TTS synthesis: {text[:30]}... (voice: {final_voice_id}, stability: {stability})")

        payload = {
            "text": final_text,
            "voice": final_voice_id,
            "stability": stability,
            "language_code": language,
            "apply_text_normalization": "auto",
            "output_format": "mp3_44100_128"
        }

        result = await self._call_fal(self.ENDPOINTS["tts"], payload)

        if not result.get("success"):
            # try removing tag and retry
            if enhance_text and final_text != text:
                logger.warning(f"⚠️ TTS failed，remove tagretry")
                payload["text"] = text
                result = await self._call_fal(self.ENDPOINTS["tts"], payload)

            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error"),
                    "fallback": True
                }

        # download audio
        audio_data = result["result"].get("audio", {})
        audio_url = audio_data.get("url") if isinstance(audio_data, dict) else audio_data

        if not audio_url:
            return {"success": False, "error": "No audio URL in response", "fallback": True}

        if not await self._download_audio(audio_url, output):
            return {"success": False, "error": "Audio download failed", "fallback": True}

        # getduration
        duration = get_audio_duration(output)
        logger.info(f"✅ ElevenLabs TTS saved: {output} ({duration:.2f}s)")

        return {
            "success": True,
            "output": output,
            "duration": duration,
            "duration_ms": int(duration * 1000),
            "voice_id": final_voice_id,
            "stability": stability,
            "backend": "elevenlabs"
        }


def get_audio_duration(audio_path: str) -> float:
    """
    use ffprobe to get precise audio duration (seconds）

    Args:
        audio_path: audio filepath

    Returns:
        duration (seconds，float）
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
    use ffprobe to get precise video duration (seconds）

    Args:
        video_path: video filepath

    Returns:
        duration (seconds，float）
    """
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


# ============== Gemini image generation（via Yunwu API）==============

class ImageClient:
    """Gemini image generation client（via Yunwu API）"""

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
        """generate image，supportmulti reference image"""
        import httpx

        style_suffix = self.STYLE_PRESETS.get(style, style)
        full_prompt = f"{prompt}, {style_suffix}"

        # build parts array
        parts = []

        # add reference image（Gemini give more weight to the last reference image，so important characters placed later）
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

        # addtext prompt
        parts.append({"text": full_prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
                "responseMimeType": "text/plain",
            }
        }

        ref_info = f" (with {len(reference_images)} reference images)" if reference_images else ""
        logger.info(f"📤 image generation{ref_info}: {prompt[:30]}...")

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
                logger.info(f"✅ image saved: {output}")
                return {"success": True, "output": output}

            return {"success": True, "image_base64": image_data}

        except Exception as e:
            logger.error(f"❌ image generationfailed: {e}")
            return {"success": False, "error": str(e)}


class FalImageClient:
    """
    Gemini image generation client（via fal.ai API）

    .. deprecated::
        Fal Image deprecated and no longer supported。please use MigooImageClient（need MIGOO_API_KEY）。
    """

    def __init__(self):
        import warnings
        warnings.warn(
            "FalImageClient deprecated, please use MigooImageClient",
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
        """generate image，supportmulti reference image"""
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

        # image-to-image mode：use when has reference image edit endpoint
        is_edit_mode = reference_images and len(reference_images) > 0
        url = self.FAL_IMAGE_EDIT_URL if is_edit_mode else self.FAL_IMAGE_URL

        if is_edit_mode:
            # upload reference image to temp storageoruse base64
            image_urls = []
            for ref_path in reference_images:
                if os.path.exists(ref_path):
                    # convert to base64 data URI
                    with open(ref_path, 'rb') as f:
                        img_data = f.read()
                    ext = os.path.splitext(ref_path)[1].lower()
                    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
                    mime_type = mime_map.get(ext, 'image/jpeg')
                    data_uri = f"data:{mime_type};base64,{base64.b64encode(img_data).decode('utf-8')}"
                    image_urls.append(data_uri)

            payload["image_urls"] = image_urls
            logger.info(f"📤 image generation（fal edit，{len(image_urls)} reference image）: {prompt[:30]}...")
        else:
            logger.info(f"📤 image generation（fal t2i）: {prompt[:30]}...")

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

            # download image
            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as dl_client:
                    dl_resp = await dl_client.get(image_url)
                    dl_resp.raise_for_status()
                    with open(output, "wb") as f:
                        f.write(dl_resp.content)
                logger.info(f"✅ image saved: {output}")
                return {"success": True, "output": output, "url": image_url}

            return {"success": True, "url": image_url}

        except Exception as e:
            logger.error(f"❌ image generationfailed: {e}")
            return {"success": False, "error": str(e)}


class MigooImageClient:
    """Gemini image generation client（via Migoo LLM API）"""

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
        """generate image，supportmulti reference image"""
        import httpx

        style_suffix = self.STYLE_PRESETS.get(style, style)
        full_prompt = f"{prompt}, {style_suffix}"

        # build parts array
        parts = []

        # add reference image（image-to-image mode）
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

        # addtext prompt
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
        logger.info(f"📤 image generation（migoo{ref_info}）: {prompt[:30]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    Config.MIGOO_IMAGE_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {Config.MIGOO_API_KEY}",
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
                logger.info(f"✅ image saved: {output}")
                return {"success": True, "output": output}

            return {"success": True, "image_base64": image_data}

        except Exception as e:
            logger.error(f"❌ image generationfailed: {e}")
            return {"success": False, "error": str(e)}


# ============== character management（optional tool）==============

class PersonaManager:
    """
    character manager（optional tool）

    used to manage in projectcharacter reference image。
    only when videoinvolves characterused when，pure landscape/object videos do not need。

    usage：
        manager = PersonaManager(project_dir)
        manager.register("Xiaomei", "female", "path/to/reference.jpg", "long hair、round face、wearing glasses")
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
        """load character data from file"""
        if self._persona_file and self._persona_file.exists():
            try:
                with open(self._persona_file, "r", encoding="utf-8") as f:
                    self.personas = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ load personas.json failed: {e}")
                self.personas = {}

    def _save(self):
        """save character data to file"""
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
        register charactercharacter

        Args:
            name: character name
            gender: gender (male/female)
            reference_image: reference image path（can be None，Phase 2 supplement）
            features: appearance feature description

        Returns:
            persona_id
        """
        # generate uniqueID
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
            logger.info(f"✅ registered character: {name} (ID: {persona_id}, reference image: {reference_image})")
        else:
            logger.info(f"✅ registered character: {name} (ID: {persona_id}, no reference image)")

        return persona_id

    def update_reference_image(self, persona_id: str, reference_image: str) -> bool:
        """
        updatecharacter reference image（Phase 2 use）

        Args:
            persona_id: characterID
            reference_image: newreference image path

        Returns:
            success status
        """
        if persona_id not in self.personas:
            logger.warning(f"⚠️ character does not exist: {persona_id}")
            return False

        self.personas[persona_id]["reference_image"] = reference_image
        self._save()
        logger.info(f"✅ updated {persona_id} reference image: {reference_image}")
        return True

    def has_reference_image(self, persona_id: str) -> bool:
        """check if character has reference image"""
        persona = self.personas.get(persona_id)
        if persona:
            return bool(persona.get("reference_image"))
        return False

    def list_personas_without_reference(self) -> List[str]:
        """return all characters without reference imagesIDlist"""
        return [
            pid for pid, data in self.personas.items()
            if not data.get("reference_image")
        ]

    def get_reference(self, persona_id: str) -> Optional[str]:
        """getcharacter reference imagepath"""
        persona = self.personas.get(persona_id)
        if persona:
            return persona.get("reference_image")
        return None

    def get_features(self, persona_id: str) -> str:
        """
        getcharacter featuresdescription（for prompt）

        Returns:
            characteristic description string，like "young woman with long hair, round face, glasses"
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

        # feature
        features = persona.get("features", "")
        if features:
            parts.append(features)

        # name as reference identifier
        name = persona.get("name", "")
        if name:
            return f"{', '.join(parts)} (reference: {name})"

        return ", ".join(parts)

    def get_persona_prompt(self, persona_id: str) -> str:
        """
        get for Vidu/Gemini character prompt

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
        """list all characters"""
        return [
            {"id": pid, **pdata}
            for pid, pdata in self.personas.items()
        ]

    def export_for_storyboard(self) -> List[Dict[str, Any]]:
        """
        export as storyboard.json compatible characters format

        Returns:
            match storyboard.json elements.characters format list
        """
        characters = []
        for pid, pdata in self.personas.items():
            name = pdata.get("name", "")
            # generate name_en（pinyin/English）
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
        generate character_image_mapping（for storyboard.json）

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
        """whether hascharacter registration"""
        return len(self.personas) > 0

    def remove(self, persona_id: str) -> bool:
        """delete character"""
        if persona_id in self.personas:
            del self.personas[persona_id]
            self._save()
            return True
        return False

    def clear(self):
        """clear all characters"""
        self.personas = {}
        self._save()


# ============== multimodal image analysis（built-in Vision capability）==============

class VisionClient:
    """
    multimodal image analysis client

    for fallback for non-multimodal models，support Kimi K2.5、GPT-4o visual models etc。
    use Anthropic API compatibleformat。

    usage：
        client = VisionClient()
        result = await client.analyze_image("path/to/image.jpg", "describe this image")
        results = await client.analyze_batch(["img1.jpg", "img2.jpg"])
    """

    # supported image formats
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(timeout=60.0)

    async def analyze_image(
        self,
        image_path: str,
        prompt: str = "please describe this in detailimage content，including scene、subject、color、atmosphere etc。",
    ) -> Dict[str, Any]:
        """analyze single image"""
        if not os.path.exists(image_path):
            return {"success": False, "error": f"image does not exist: {image_path}"}

        # read and encode image
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

        # get config
        api_key = Config.get("VISION_API_KEY", "")
        base_url = Config.get("VISION_BASE_URL", "https://coding.dashscope.aliyuncs.com/apps/anthropic")
        model = Config.get("VISION_MODEL", "kimi-k2.5")

        if not api_key:
            return {"success": False, "error": "VISION_API_KEY not configured"}

        # build API request（Anthropic API compatibleformat）
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

            # extract response text
            content = result.get("content", [])
            description = None
            for item in content:
                if item.get("type") == "text":
                    description = item.get("text", "")
                    break

            if not description:
                description = "cannot parse response"

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
        prompt: str = "please describe this in detailimage content，including scene、subject、color、atmosphere etc。"
    ) -> List[Dict[str, Any]]:
        """batch analysismultiple images"""
        results = []
        for path in image_paths:
            result = await self.analyze_image(path, prompt)
            results.append(result)
        return results

    async def close(self):
        await self.client.aclose()


# ============== command line entry ==============

async def cmd_vision(args):
    """image analysis command"""
    api_key = Config.get("VISION_API_KEY", "")
    if not api_key:
        print(json.dumps({
            "success": False,
            "error": "VISION_API_KEY not configured",
            "hint": "please in config.json add VISION_API_KEY",
            "config_file": str(CONFIG_FILE)
        }, indent=2, ensure_ascii=False))
        return 1

    client = VisionClient()
    try:
        if args.batch:
            # batch analysisdirectory
            directory = Path(args.image)
            if not directory.is_dir():
                print(json.dumps({
                    "success": False,
                    "error": f"directory does not exist: {args.image}"
                }, indent=2, ensure_ascii=False))
                return 1

            image_files = []
            for ext in VisionClient.SUPPORTED_FORMATS:
                image_files.extend(directory.glob(f"*{ext}"))
                image_files.extend(directory.glob(f"*{ext.upper()}"))

            if not image_files:
                print(json.dumps({
                    "success": False,
                    "error": f"not found in directoryimage file: {args.image}"
                }, indent=2, ensure_ascii=False))
                return 1

            logger.info(f"found {len(image_files)} image，start analysis...")
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
            # single image analysis
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


# ============== command line entry ==============

async def cmd_video(args):
    """video generationcommand"""
    # param mutual exclusion check：must specify --prompt or (--storyboard + --scene)
    has_prompt = bool(args.prompt)
    has_scene = bool(getattr(args, 'scene', None) and getattr(args, 'storyboard', None))
    if not has_prompt and not has_scene:
        print(json.dumps({
            "success": False,
            "error": "must specify --prompt or --storyboard + --scene"
        }, indent=2, ensure_ascii=False))
        return 1

    provider = getattr(args, 'provider', None)
    backend = getattr(args, 'backend', 'kling')

    # Provider auto selection logic（likeif user not specified）
    if provider is None:
        if backend == 'seedance':
            # seedance: fal > piapi（as defined in SKILL.md）
            if Config.FAL_API_KEY:
                provider = 'fal'
            elif Config.SEEDANCE_API_KEY:
                provider = 'piapi'
            else:
                provider = 'fal'  # default，will report error and hint config
        elif backend == 'veo3':
            provider = 'migoo'  # veo3 only migoo provider
        elif Config.KLING_ACCESS_KEY and Config.KLING_SECRET_KEY:
            provider = 'official'  # priority use official API
        elif Config.FAL_API_KEY:
            provider = 'fal'       # then use fal
        else:
            provider = 'official'  # default，will report error and hint config

    logger.info(f"🔧 use provider: {provider}, backend: {backend}")

    # Priority: command line > storyboard.json > default value
    aspect_ratio = args.aspect_ratio
    if aspect_ratio is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect_ratio = get_aspect_from_storyboard(args.storyboard)
        if aspect_ratio:
            logger.info(f"📐 read from storyboard.json aspect ratio: {aspect_ratio}")
    if aspect_ratio is None:
        aspect_ratio = "9:16"  # final default value
        logger.info(f"📐 use default aspect ratio: {aspect_ratio}")

    # ==================== fal.ai provider ====================
    # fal support Kling and Seedance backends，need to based on backend parameter distinction
    if provider == 'fal':
        if not Config.FAL_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "FAL_API_KEY not configured",
                "hint": "please in config.json add FAL_API_KEY",
                "get_key": "access https://fal.ai get API key"
            }, indent=2, ensure_ascii=False))
            return 1

        # ===== Seedance backend (fal provider) =====
        if backend == 'seedance':
            client = FalSeedanceClient()
            try:
                duration = max(4, min(15, args.duration))
                if duration != args.duration:
                    logger.warning(f"⚠️ Seedance duration adjusted to {duration}s (range 4-15s)")
                image_list = getattr(args, 'image_list', None)
                audio_urls = getattr(args, 'audio_urls', None)
                video_urls = getattr(args, 'video_urls', None)
                scene_id = getattr(args, 'scene', None)
                storyboard_path = getattr(args, 'storyboard', None)

                # support --storyboard + --scene auto assemble
                if storyboard_path and scene_id:
                    storyboard_data = load_storyboard(storyboard_path)
                    if not storyboard_data:
                        print(json.dumps({"success": False, "error": f"cannot load storyboard: {storyboard_path}"}, indent=2, ensure_ascii=False))
                        return 1
                    target_scene = None
                    for sc in storyboard_data.get("scenes", []):
                        if sc.get("scene_id") == scene_id:
                            target_scene = sc
                            break
                    if not target_scene:
                        print(json.dumps({"success": False, "error": f"not found scene: {scene_id}"}, indent=2, ensure_ascii=False))
                        return 1
                    prompt, image_urls, duration = build_seedance_prompt(target_scene, storyboard_data, storyboard_path)
                    aspect_ratio = storyboard_data.get("aspect_ratio", aspect_ratio)
                    logger.info(f"🎬 Seedance auto assemble: scene={scene_id}, duration={duration}s, images={len(image_urls)}")

                    result = await client.submit_task(
                        prompt=prompt, duration=duration, aspect_ratio=aspect_ratio,
                        image_urls=image_urls if image_urls else None,
                        resolution=getattr(args, 'resolution', '720p'),
                        seed=getattr(args, 'seed', None),
                        model=getattr(args, 'model', 'fast'),
                        output=args.output
                    )
                else:
                    result = await client.submit_task(
                        prompt=args.prompt,
                        duration=duration,
                        aspect_ratio=aspect_ratio,
                        image_urls=image_list,
                        video_urls=video_urls,
                        audio_urls=audio_urls,
                        resolution=getattr(args, 'resolution', '720p'),
                        seed=getattr(args, 'seed', None),
                        model=getattr(args, 'model', 'fast'),
                        output=args.output
                    )

                if result.get("success"):
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    return 0
                else:
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    return 1
            finally:
                await client.close()

        # ===== Kling / Kling-Omni backend (fal provider) =====
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

    # ==================== kling provider (official API) ====================
    # BackendRouter: force switch by functional requirement
    # - image-list: kling-omni and seedance both support，do not force switch
    # - tail-image: only kling support，need force switch
    image_list = getattr(args, 'image_list', None)
    tail_image = getattr(args, 'tail_image', None)
    if tail_image and backend not in ['kling']:
        backend = 'kling'
        logger.info("🔀 detected --tail-image，auto switch to Kling backend")

    # ==================== official provider (official API) ====================
    # check corresponding backend's API key
    if backend == 'kling':
        if not Config.KLING_ACCESS_KEY or not Config.KLING_SECRET_KEY:
            print(json.dumps({
                "success": False,
                "error": "Kling API credentialnot configured",
                "hint": "please in config.json add KLING_ACCESS_KEY and KLING_SECRET_KEY",
                "get_key": "access https://klingai.kuaishou.com get API credential"
            }, indent=2, ensure_ascii=False))
            return 1

        client = KlingClient()
        try:
            # Kling parameterconversion：audio -> sound
            sound = "on" if args.audio else "off"
            # Kling durationrange：3-15s
            duration = max(3, min(15, args.duration))

            # process multi-shot params
            multi_shot = getattr(args, 'multi_shot', False)
            shot_type = getattr(args, 'shot_type', None)
            multi_prompt = None
            if getattr(args, 'multi_prompt', None):
                try:
                    multi_prompt = json.loads(args.multi_prompt)
                except json.JSONDecodeError:
                    print(json.dumps({
                        "success": False,
                        "error": "multi_prompt JSON parse failed"
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
                "error": "Kling API credentialnot configured",
                "hint": "please in config.json add KLING_ACCESS_KEY and KLING_SECRET_KEY",
                "get_key": "access https://klingai.kuaishou.com get API credential"
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
                        "error": "multi_prompt JSON parse failed"
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

    elif backend == 'seedance':
        # Provider select: fal > piapi
        provider = getattr(args, 'provider', None)
        use_fal = False

        if provider == 'fal':
            if not Config.FAL_API_KEY:
                print(json.dumps({
                    "success": False,
                    "error": "FAL_API_KEY not configured",
                    "hint": "use --provider fal need FAL_API_KEY"
                }, indent=2, ensure_ascii=False))
                return 1
            use_fal = True
        elif provider == 'piapi':
            if not Config.SEEDANCE_API_KEY:
                print(json.dumps({
                    "success": False,
                    "error": "SEEDANCE_API_KEY not configured",
                    "hint": "use --provider piapi need SEEDANCE_API_KEY"
                }, indent=2, ensure_ascii=False))
                return 1
            use_fal = False
        else:
            # auto select：fal > piapi
            if Config.FAL_API_KEY:
                use_fal = True
                logger.info("🔵 Seedance auto select provider: fal")
            elif Config.SEEDANCE_API_KEY:
                use_fal = False
                logger.info("🔵 Seedance auto select provider: piapi")
            else:
                print(json.dumps({
                    "success": False,
                    "error": "Seedance no available Provider",
                    "hint": "please configure FAL_API_KEY（recommend）or SEEDANCE_API_KEY",
                    "providers": {
                        "fal": {"key": "FAL_API_KEY", "url": "https://fal.ai", "priority": 1},
                        "piapi": {"key": "SEEDANCE_API_KEY", "url": "https://piapi.ai", "priority": 2}
                    }
                }, indent=2, ensure_ascii=False))
                return 1

        client = FalSeedanceClient() if use_fal else SeedanceClient()
        try:
            scene_id = getattr(args, 'scene', None)
            storyboard_path = getattr(args, 'storyboard', None)

            if storyboard_path and scene_id:
                storyboard_data = load_storyboard(storyboard_path)
                if not storyboard_data:
                    print(json.dumps({"success": False, "error": f"cannot load storyboard: {storyboard_path}"}, indent=2, ensure_ascii=False))
                    return 1

                target_scene = None
                for sc in storyboard_data.get("scenes", []):
                    if sc.get("scene_id") == scene_id:
                        target_scene = sc
                        break
                if not target_scene:
                    print(json.dumps({"success": False, "error": f"not found scene: {scene_id}", "available": [s.get("scene_id") for s in storyboard_data.get("scenes", [])]}, indent=2, ensure_ascii=False))
                    return 1

                prompt, image_urls, duration = build_seedance_prompt(target_scene, storyboard_data, storyboard_path)
                aspect_ratio = storyboard_data.get("aspect_ratio", aspect_ratio)
                logger.info(f"🎬 Seedance auto assemble: scene={scene_id}, duration={duration}s, images={len(image_urls)}")

                if use_fal:
                    result = await client.submit_task(
                        prompt=prompt, duration=duration, aspect_ratio=aspect_ratio,
                        image_urls=image_urls if image_urls else None,
                        resolution=getattr(args, 'resolution', '720p'),
                        seed=getattr(args, 'seed', None),
                        model=getattr(args, 'model', 'fast'),
                        output=args.output
                    )
                else:
                    result = await client.submit_task(
                        prompt=prompt, duration=duration, aspect_ratio=aspect_ratio,
                        image_urls=image_urls if image_urls else None,
                        output=args.output
                    )
            else:
                duration = max(4, min(15, args.duration))
                if duration != args.duration:
                    logger.warning(f"⚠️ Seedance 2 duration adjusted to {duration}s")
                image_list = getattr(args, 'image_list', None)
                audio_urls = getattr(args, 'audio_urls', None)
                video_urls = getattr(args, 'video_urls', None)

                if use_fal:
                    result = await client.submit_task(
                        prompt=args.prompt, duration=duration, aspect_ratio=aspect_ratio,
                        image_urls=image_list, video_urls=video_urls, audio_urls=audio_urls,
                        resolution=getattr(args, 'resolution', '720p'),
                        seed=getattr(args, 'seed', None),
                        model=getattr(args, 'model', 'fast'),
                        output=args.output
                    )
                else:
                    mode = getattr(args, 'mode', 'text_to_video')
                    if mode in ['std', 'pro']:
                        mode = 'omni_reference' if image_list else 'text_to_video'
                    result = await client.submit_task(
                        prompt=args.prompt, duration=duration, aspect_ratio=aspect_ratio,
                        image_urls=image_list, mode=mode,
                        audio_urls=audio_urls, video_urls=video_urls,
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

    elif backend == 'veo3':
        # Veo3 deprecated，but keep code backward compatible
        logger.warning("⚠️ Veo3 backend is deprecated，recommended Kling、Kling-Omni or Seedance")
        if not Config.MIGOO_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "MIGOO_API_KEY not configured",
                "hint": "please in config.json add MIGOO_API_KEY",
                "get_key": "Migoo LLM API key foraccess Veo3 video generation"
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
                print(f"error: {result.get('error')}")
                return 1
        finally:
            await client.close()

    # unknown backend
    print(json.dumps({
        "success": False,
        "error": f"unsupported backend: {backend}",
        "supported_backends": ["kling", "kling-omni", "seedance"]
    }, indent=2, ensure_ascii=False))
    return 1


async def cmd_music(args):
    """music generation command"""
    # Priority: command line > creative.json > report error
    prompt = args.prompt
    style = args.style

    # read from creative.json prompt and style
    if hasattr(args, 'creative') and args.creative:
        config = get_music_config_from_creative(args.creative)
        if config:
            if prompt is None:
                prompt = config.get("prompt")
                if prompt:
                    logger.info(f"🎵 read from creative.json music description: {prompt[:50]}...")
            if style is None:
                style = config.get("style")
                if style:
                    logger.info(f"🎵 read from creative.json music style: {style}")

    # prompt must provide
    if prompt is None:
        print(json.dumps({
            "success": False,
            "error": "must provide music description",
            "hint": "please pass --prompt or --creative parameter provides music description"
        }, indent=2, ensure_ascii=False))
        return 1

    # style must provide
    if style is None:
        print(json.dumps({
            "success": False,
            "error": "must provide music style",
            "hint": "please pass --style or --creative parameter provides music style"
        }, indent=2, ensure_ascii=False))
        return 1

    if not Config.SUNO_API_KEY:
        print(json.dumps({
            "success": False,
            "error": "SUNO_API_KEY not configured",
            "hint": "please set environment variable: export SUNO_API_KEY='your-api-key'",
            "get_key": "access https://sunoapi.org get API key"
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
    """TTS synthesiscommand - support ElevenLabs (priority) and Gemini (fallback)"""
    backend = getattr(args, 'backend', 'elevenlabs')

    # ElevenLabs TTS（priority）
    if backend == "elevenlabs":
        if not Config.FAL_API_KEY:
            logger.warning("⚠️ FAL_API_KEY not configured，degrade to Gemini TTS")
            backend = "gemini"
        else:
            logger.info("🔧 use ElevenLabs TTS (via fal)")
            client = ElevenLabsTTSClient()
            result = await client.synthesize(
                text=args.text,
                output=args.output,
                voice_id=getattr(args, 'voice_id', None),
                voice_style=args.voice,
                stability=getattr(args, 'stability', None),
                video_type=getattr(args, 'video_type', None),
                enhance_text=getattr(args, 'enhance_text', True),
                voice_name=getattr(args, 'voice_name', None)
            )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0

            # ElevenLabs failed，check if can degrade
            if result.get("fallback"):
                logger.warning(f"⚠️ ElevenLabs TTS failed: {result.get('error')}, degrade to Gemini")
                backend = "gemini"
            else:
                print(f"error: {result.get('error')}")
                return 1

    # Gemini TTS(fallback)
    if backend == "gemini":
        if not Config.MIGOO_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "MIGOO_API_KEY not configured",
                "hint": "please configure MIGOO_API_KEY to use Gemini TTS",
                "get_key": "access Migoo LLM PROXY get API key（contact dongming.shen）"
            }, indent=2, ensure_ascii=False))
            return 1

        logger.info("🔧 use Gemini TTS (Migoo LLM) - fallback mode")
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
            # marked as degradedresult
            if backend == "gemini" and getattr(args, 'backend', 'elevenlabs') == 'elevenlabs':
                result["backend"] = "gemini_fallback"
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        else:
            print(f"error: {result.get('error')}")
            return 1


async def cmd_image(args):
    """image generationcommand"""
    # Provider auto selection logic
    provider = getattr(args, 'provider', None)
    if provider is None:
        # Priority: migoo → yunwu
        if Config.MIGOO_API_KEY:
            provider = 'migoo'
        elif Config.GEMINI_API_KEY:  # GEMINI_API_KEY actually is YUNWU_API_KEY
            provider = 'yunwu'
        else:
            provider = 'migoo'  # default，will report error and hint config

    logger.info(f"🔧 use provider: {provider}")

    # Priority: command line > storyboard.json > default value
    aspect_ratio = args.aspect_ratio
    if aspect_ratio is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect_ratio = get_aspect_from_storyboard(args.storyboard)
        if aspect_ratio:
            logger.info(f"📐 read from storyboard.json aspect ratio: {aspect_ratio}")
    if aspect_ratio is None:
        aspect_ratio = "9:16"  # final default value
        logger.info(f"📐 use default aspect ratio: {aspect_ratio}")

    # migoo provider
    if provider == 'migoo':
        if not Config.MIGOO_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "MIGOO_API_KEY not configured",
                "hint": "please in config.json add MIGOO_API_KEY"
            }, indent=2, ensure_ascii=False))
            return 1

        client = MigooImageClient()
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
                "hint": "please set environment variable: export YUNWU_API_KEY='your-api-key'",
                "get_key": "access https://yunwu.ai register to get API key"
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


async def cmd_setup(args):
    """Interactive API provider setup and key"""

    # define all availablevideo generation provider and its required key
    VIDEO_PROVIDERS = {
        "1": {
            "name": "Seedance（ByteDance，recommend fiction film/short drama/MV）",
            "backend": "seedance",
            "provider": "fal > piapi",
            "keys": [
                {"key": "FAL_API_KEY", "label": "fal.ai API Key (preferred)", "url": "https://fal.ai"},
                {"key": "SEEDANCE_API_KEY", "label": "Seedance API Key (piapi fallback)", "url": "https://piapi.ai"}
            ]
        },
        "2": {
            "name": "Kling official API（Kuaishou，recommend realistic/commercial）",
            "backend": "kling",
            "provider": "official",
            "keys": [
                {"key": "KLING_ACCESS_KEY", "label": "Kling Access Key", "url": "https://klingai.kuaishou.com"},
                {"key": "KLING_SECRET_KEY", "label": "Kling Secret Key", "url": "https://klingai.kuaishou.com"}
            ]
        },
        "3": {
            "name": "Kling via fal.ai（bypass official concurrency limit）",
            "backend": "kling-omni",
            "provider": "fal",
            "keys": [
                {"key": "FAL_API_KEY", "label": "fal.ai API Key", "url": "https://fal.ai"}
            ]
        },
        # "4": Veo3 deprecated - removed from setup options
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

    # output as JSON，for convenience Claude parse
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

    # displaycurrentconfigured keys
    for key in ["SEEDANCE_API_KEY", "KLING_ACCESS_KEY", "KLING_SECRET_KEY", "FAL_API_KEY",
                "YUNWU_API_KEY", "SUNO_API_KEY", "VOLCENGINE_TTS_APP_ID",
                "VOLCENGINE_TTS_ACCESS_TOKEN", "MIGOO_API_KEY"]:
        val = config.get(key) or os.getenv(key, "")
        setup_info["current_config"][key] = f"{val[:4]}***" if val else "not set"

    # non-interactive mode：pass --provider to directly configure
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
        Config._cached_config = None  # clear cache
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
    """environment checkcommand"""
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
            "purpose": "Seedance video generation（piapi.ai proxy）",
            "get_key": "https://piapi.ai"
        },
        "MIGOO_API_KEY": {
            "value": Config.MIGOO_API_KEY,
            "purpose": "Gemini image + Gemini TTS（Migoo LLM PROXY）",
            "get_key": "https://inner-api.us.migoo.shopee.io/inbeeai"
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
            "purpose": "fal.ai Kling video generation proxy（bypass official concurrency limit）",
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
        masked = f"{info['value'][:4]}***" if is_set else "not set"
        results["api_keys"][name] = {
            "set": is_set,
            "masked_value": masked,
            "purpose": info["purpose"],
            "get_key_url": info["get_key"]
        }

    # checkwhether at least one existsvideo provider available
    has_video_provider = any([
        Config.SEEDANCE_API_KEY,
        Config.MIGOO_API_KEY,
        Config.KLING_ACCESS_KEY and Config.KLING_SECRET_KEY,
        Config.FAL_API_KEY,
    ])
    results["has_video_provider"] = has_video_provider
    if not has_video_provider:
        results["ready"] = False
        results["missing"].append("no video generation configured API key")
        results["hints"].append("please first run setup commandconfig API: python video_gen_tools.py setup")

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results["ready"] else 1


async def cmd_validate(args):
    """validation storyboard.json"""
    result = validate_storyboard(args.storyboard)

    # output result
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result["errors"]:
        logger.error(f"❌ validationfailed: {len(result['errors'])} errors")
    if result["warnings"]:
        logger.warning(f"⚠️ {len(result['warnings'])} warnings")
    if result["valid"]:
        logger.info("✅ validation passed")

    return 0 if result["valid"] else 1


def main():
    parser = argparse.ArgumentParser(
        description="Vico Tools - video creationAPIcommand line tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="available command")

    # setup subcommand（interactive config provider + API key）
    setup_parser = subparsers.add_parser("setup", help="Interactive API provider setup and key")
    setup_parser.add_argument("--provider", dest="provider_choice", choices=["1", "2", "3"],
                              help="select video provider: 1=Seedance, 2=Klingofficial, 3=Kling(fal)")
    setup_parser.add_argument("--set-key", nargs="+", metavar="KEY=VALUE",
                              help="set API key，format: KEY=VALUE(can be multiple)")

    # check subcommand
    subparsers.add_parser("check", help="check environment dependencies and config")

    # video subcommand
    video_parser = subparsers.add_parser("video", help="generatevideo")
    video_parser.add_argument("--image", "-i", help="inputimage pathorURL（image-to-video）")
    video_parser.add_argument("--prompt", "-p", default=None, help="videodescription（Seedance --scene can be omitted in mode）")
    video_parser.add_argument("--duration", "-d", type=int, default=5, help="duration(s)")
    video_parser.add_argument("--resolution", "-r", default="720p", help="resolution")
    video_parser.add_argument("--aspect-ratio", "-a", default=None, help="aspect ratio（like 16:9, 9:16）")
    video_parser.add_argument("--storyboard", "-s", help="storyboard.json path，auto read aspect_ratio")
    video_parser.add_argument("--audio", action="store_true", help="generate native audio")
    video_parser.add_argument("--output", "-o", help="output file path")
    video_parser.add_argument("--provider", choices=["official", "fal", "piapi", "migoo"], default=None,
                              help="API provider (default auto select; seedance: fal > piapi; veo3 only supports migoo)")
    video_parser.add_argument("--backend", "-b", choices=["kling", "kling-omni", "seedance"], default="kling",
                              help="video generation backend (default kling; kling-omni for reference image; seedance for intelligent shot cutting; veo3 for global fallback)")
    video_parser.add_argument("--mode", "-m", choices=["std", "pro", "text_to_video", "first_last_frames", "omni_reference"], default="std",
                              help="generation mode (Kling: std or pro; Seedance: text_to_video, first_last_frames, omni_reference)")
    video_parser.add_argument("--multi-shot", action="store_true",
                              help="enable Kling multi-shotmode")
    video_parser.add_argument("--shot-type", choices=["intelligence", "customize"],
                              help="multi-shot storyboard type (intelligence: AIauto, customize: custom)")
    video_parser.add_argument("--multi-prompt", type=str,
                              help="multi-shot prompt list (JSON format)")
    video_parser.add_argument("--tail-image", type=str,
                              help="last frameimage path（forfirst/last framecontrol）")
    video_parser.add_argument("--image-list", nargs="+",
                              help="Omni-Video multi reference imagepath list（kling-omni dedicated）；or Seedance first/last frame images for first/last frame mode")
    video_parser.add_argument("--scene", help="Scene ID（Seedance dedicated：coordinate with --storyboard auto assemble time segments prompt）")
    video_parser.add_argument("--audio-urls", nargs="+",
                              help="audioreference URL list（Seedance 2 dedicated）")
    video_parser.add_argument("--video-urls", nargs="+",
                              help="videoreference URL list（Seedance 2 dedicated）")
    video_parser.add_argument("--seed", type=int,
                              help="random seed(only Seedance fal provider supports)")
    video_parser.add_argument("--end-user-id",
                              help="end userID（falcompliance requirement）")
    video_parser.add_argument("--model", choices=["fast", "high_quality"], default="fast",
                              help="Seedance modelversion(only fal provider supports)")

    # music subcommand
    music_parser = subparsers.add_parser("music", help="generatemusic")
    music_parser.add_argument("--prompt", "-p", default=None, help="musicdescription（can from creative.json auto read）")
    music_parser.add_argument("--style", "-s", default=None, help="musicstyle（can from creative.json auto read）")
    music_parser.add_argument("--creative", "-c", help="creative.json path，auto read prompt and style")
    music_parser.add_argument("--no-instrumental", dest="instrumental", action="store_false", help="contains vocals（default pure music）")
    music_parser.set_defaults(instrumental=True)
    music_parser.add_argument("--output", "-o", help="output file path")

    # tts subcommand
    tts_parser = subparsers.add_parser("tts", help="generatevoice（ElevenLabs priority，Gemini fallback）")
    tts_parser.add_argument("--text", "-t", required=True, help="text to synthesize")
    tts_parser.add_argument("--output", "-o", required=True, help="output file path")
    tts_parser.add_argument("--backend", "-b", choices=["elevenlabs", "gemini"],
                           default="elevenlabs", help="TTS backend（default elevenlabs，gemini as fallback）")
    tts_parser.add_argument("--voice", "-v", default="female_narrator",
                           choices=["female_narrator", "female_gentle", "female_soft", "female_bright",
                                    "male_narrator", "male_warm", "male_deep", "male_bright"],
                           help="voice style（map to ElevenLabs built-in voiceorcreate new voice）")
    tts_parser.add_argument("--voice-id", help="existing ElevenLabs voice_id（skip Design/Create）")
    tts_parser.add_argument("--stability", type=float, help="stable param（0-1，drama character 0.20-0.25，emotional narrative 0.25-0.35）")
    tts_parser.add_argument("--video-type", choices=["cinematic", "vlog", "documentary", "commercial", "artistic"],
                           help="video type（used for auto adjustment stability and text enhancement)")
    tts_parser.add_argument("--enhance-text", action="store_true", default=True,
                           help="auto enhance text（insertemotion/rhythm tag）")
    tts_parser.add_argument("--no-enhance-text", dest="enhance_text", action="store_false",
                           help="not enhance text，read as-is")
    tts_parser.add_argument("--voice-name", help="new voice name（for Create）")
    tts_parser.add_argument("--emotion", "-e", choices=["neutral", "happy", "sad", "gentle", "serious"],
                           help="emotion（deprecated，recommended --prompt）")
    tts_parser.add_argument("--prompt", "-p", help="style instruction（Gemini TTS dedicated，ElevenLabs use text enhancement）")
    tts_parser.add_argument("--speed", type=float, default=1.0, help="speech rate(only Gemini TTS supports)")

    # image subcommand
    image_parser = subparsers.add_parser("image", help="generate image")
    image_parser.add_argument("--prompt", "-p", required=True, help="image description")
    image_parser.add_argument("--output", "-o", help="output file path")
    image_parser.add_argument("--style", "-s", default="cinematic",
                              help="style（free text，like cinematic, watercolor illustration, etc)")
    image_parser.add_argument("--aspect-ratio", "-a", default=None, help="aspect ratio")
    image_parser.add_argument("--storyboard", help="storyboard.json path，auto read aspect_ratio")
    image_parser.add_argument("--reference", "-r", nargs="+", help="reference image path（support multiple，important characterput later）")
    image_parser.add_argument("--provider", choices=["migoo", "yunwu"], default=None,
                              help="API provider (default auto select: migoo priority)")

    # vision subcommand（built-in multimodal analysis）
    vision_parser = subparsers.add_parser("vision", help="analyze image content")
    vision_parser.add_argument("image", help="image pathordirectory")
    vision_parser.add_argument("--batch", "-b", action="store_true", help="batch analyze images in directory")
    vision_parser.add_argument("--prompt", "-p", default="please describe this in detailimage content，including scene、subject、color、atmosphere etc。", help="analyze prompt")

    # validate subcommand
    validate_parser = subparsers.add_parser("validate", help="validation storyboard.json")
    validate_parser.add_argument("--storyboard", "-s", required=True, help="storyboard.json path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # run corresponding command
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