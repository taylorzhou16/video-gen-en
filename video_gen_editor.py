#!/usr/bin/env python3
"""
Vico Editor - FFmpeg video editing CLI tool

Usage:
  python video_gen_editor.py concat --inputs <video1> <video2> --output <output.mp4>
  python video_gen_editor.py subtitle --video <video> --srt <subtitle.srt> --output <output.mp4>
  python video_gen_editor.py mix --video <video> --bgm <music.mp3> --output <output.mp4>
  python video_gen_editor.py transition --inputs <video1> <video2> --type fade --output <output.mp4>
  python video_gen_editor.py color --video <video> --preset warm --output <output.mp4>
  python video_gen_editor.py speed --video <video> --rate 1.5 --output <output.mp4>
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT = 300  # 5 minutes


# ============== Utility functions ==============

async def run_ffmpeg(cmd: List[str], timeout: int = FFMPEG_TIMEOUT) -> Tuple[bool, str]:
    """Run FFmpeg command"""
    logger.info(f"Executing: {' '.join(cmd[:10])}...")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return False, f"FFmpeg timeout ({timeout}seconds)"

        if process.returncode == 0:
            return True, "success"
        else:
            error_msg = stderr.decode()[:500]
            logger.error(f"FFmpeg error: {error_msg}")
            return False, error_msg

    except Exception as e:
        return False, str(e)


def get_resolution_for_aspect(aspect: str) -> Tuple[int, int]:
    """Get resolution for specified aspect ratio"""
    if aspect == "16:9":
        return (1920, 1080)
    elif aspect == "1:1":
        return (1080, 1080)
    return (1080, 1920)  # default 9:16


def get_aspect_from_storyboard(storyboard_path: str) -> Optional[str]:
    """Read aspect_ratio from storyboard.json"""
    try:
        with open(storyboard_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("aspect_ratio")
    except Exception:
        return None


async def has_audio_track(video_path: str) -> bool:
    """Check if video has audio track"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        video_path
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        return len(stdout.strip()) > 0
    except Exception:
        return False


async def get_video_info(video_path: str) -> Dict[str, Any]:
    """Get video info"""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return json.loads(stdout.decode())
        return {}
    except Exception as e:
        logger.error(f"Get video infofailure: {e}")
        return {}


async def get_video_duration(video_path: str) -> float:
    """Get video duration (seconds)"""
    info = await get_video_info(video_path)
    if info:
        duration = info.get("format", {}).get("duration")
        if duration:
            return float(duration)
    return 0.0


async def get_video_specs(video_path: str) -> Dict[str, Any]:
    """Get video detailed parameters"""
    info = await get_video_info(video_path)
    if not info:
        return {"path": video_path, "error": "Cannot get video info"}

    specs = {"path": video_path}

    # Get video parameters from streams
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            specs["width"] = stream.get("width", 0)
            specs["height"] = stream.get("height", 0)
            specs["codec"] = stream.get("codec_name", "unknown")
            specs["pix_fmt"] = stream.get("pix_fmt", "unknown")
            # Frame rate may be "24/1" or "23.976" format
            fps_str = stream.get("r_frame_rate", "0/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                specs["fps"] = round(int(num) / int(den), 3) if int(den) != 0 else 0
            else:
                specs["fps"] = float(fps_str)
            break

    # Duration
    specs["duration"] = float(info.get("format", {}).get("duration", 0))

    return specs


async def validate_videos(video_paths: List[str]) -> Dict[str, Any]:
    """
    Validate if all video parameters are consistent

    Returns:
        {
            "consistent": bool,
            "issues": List[str],  # Issue description
            "specs": List[dict],  # Parameters for each video
        }
    """
    specs_list = []
    for path in video_paths:
        specs = await get_video_specs(path)
        specs_list.append(specs)

    # Extract key parameters
    resolutions = set()
    codecs = set()
    fps_values = set()
    issues = []

    for specs in specs_list:
        if "error" in specs:
            issues.append(f"videoparametererror: {specs['path']} - {specs['error']}")
            continue

        resolutions.add((specs.get("width", 0), specs.get("height", 0)))
        codecs.add(specs.get("codec", "unknown"))
        fps_values.add(specs.get("fps", 0))

    # Check consistency
    if len(resolutions) > 1:
        res_str = ", ".join([f"{w}x{h}" for w, h in resolutions])
        issues.append(f"Resolution inconsistent: {res_str}")

    if len(codecs) > 1:
        issues.append(f"Codec inconsistent: {', '.join(codecs)}")

    if len(fps_values) > 1:
        # Allow minor frame rate differences（e.g., 23.976 vs 24）
        fps_range = max(fps_values) - min(fps_values)
        if fps_range > 1:
            issues.append(f"Frame rate difference too large: {', '.join(map(str, fps_values))}")

    return {
        "consistent": len(issues) == 0,
        "issues": issues,
        "specs": specs_list
    }


async def normalize_videos(
    video_paths: List[str],
    output_dir: str,
    aspect: str = "9:16"
) -> List[str]:
    """
    Normalize all videos to unified parameters

    Unified parameters:
    - Resolution：9:16 → 1080x1920, 16:9 → 1920x1080, 1:1 → 1080x1080
    - encode：H.264
    - Frame rate: 24fps
    - Pixel format: yuv420p
    - Audio: unified 48kHz stereo, silent track added for videos without audio

    Returns:
        Normalized video path list
    """
    w, h = get_resolution_for_aspect(aspect)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    normalized_paths = []
    vf_filter = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"

    for i, video_path in enumerate(video_paths):
        output_file = output_path / f"normalized_{i:03d}.mp4"

        # Check if audio track exists
        has_audio = await has_audio_track(video_path)

        if has_audio:
            # Has audio: normal normalization
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", vf_filter,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-r", "24",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-ar", "48000",
                str(output_file)
            ]
        else:
            # No audio: add silent track
            logger.info(f"🔇 Video has no audio track, adding silent track: {video_path}")
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                "-vf", vf_filter,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-r", "24",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                str(output_file)
            ]

        success, msg = await run_ffmpeg(cmd)

        if success:
            normalized_paths.append(str(output_file))
            logger.info(f"✅ Video normalization complete: {output_file}")
        else:
            logger.warning(f"⚠️ Video normalization failed, using original file: {video_path}")
            normalized_paths.append(video_path)

    return normalized_paths


# ============== Concatenate videos ==============

async def concat_videos(
    inputs: List[str],
    output: str,
    aspect: str = "9:16"
) -> Dict[str, Any]:
    """
    Concatenate multiple videos (using concat filter, ensures audio-video sync)

    Args:
        inputs: Input video path list (all clips must have audio track, ensured by normalize_videos)
        output: outputvideopath
        aspect: Target aspect ratio
    """
    if not inputs:
        return {"success": False, "error": "No input videos"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # If only one video, copy directly
    if len(inputs) == 1:
        import shutil
        shutil.copy(inputs[0], output)
        return {"success": True, "output": output}

    # Using concat filter (all clips must have audio track)
    n = len(inputs)
    filter_str = f"concat=n={n}:v=1:a=1[outv][outa]"

    # Build input parameters
    input_args = []
    for inp in inputs:
        input_args.extend(["-i", inp])

    cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_str,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        output
    ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ Video concatenation complete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Add subtitles ==============

# ASS color format: &HBBGGRR& (note: BGR order)
ASS_COLORS = {
    "white": "&HFFFFFF&",
    "black": "&H000000&",
    "red": "&H0000FF&",
    "green": "&H00FF00&",
    "blue": "&HFF0000&",
    "yellow": "&H00FFFF&",
    "cyan": "&HFFFF00&",
    "magenta": "&HFF00FF&",
}


async def add_subtitles(
    video: str,
    srt: str,
    output: str,
    font_size: int = 40,
    font_color: str = "white",
    position: str = "bottom"
) -> Dict[str, Any]:
    """
    Add subtitles to video

    Args:
        video: inputvideo
        srt: SRT subtitle file
        output: outputvideo
        font_size: Font size
        font_color: Font color
        position: Position (bottom/top/center)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video does not exist: {video}"}
    if not os.path.exists(srt):
        return {"success": False, "error": f"Subtitle file does not exist: {srt}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    ass_color = ASS_COLORS.get(font_color, font_color)

    subtitle_filter = f"subtitles='{os.path.abspath(srt)}':force_style='FontSize={font_size},PrimaryColour={ass_color},OutlineColour=&H000000&,Outline=2'"

    cmd = [
        "ffmpeg", "-y",
        "-i", video,
        "-vf", subtitle_filter,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output
    ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ Subtitle addition complete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Audio mixing ==============

async def mix_audio(
    video: str,
    output: str,
    bgm: str = None,
    tts: str = None,
    video_volume: float = 0.3,
    bgm_volume: float = 0.6,
    tts_volume: float = 1.0
) -> Dict[str, Any]:
    """
    Mix audio

    Args:
        video: inputvideo
        output: outputvideo
        bgm: Background music (optional)
        tts: Narration audio (optional)
        video_volume: Original video volume (0-1)
        bgm_volume: BGM volume (0-1)
        tts_volume: TTS volume (0-1)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video does not exist: {video}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # Build audio mixing filter
    audio_inputs = []
    filter_parts = []

    # Original video audio
    audio_inputs.extend(["-i", video])
    filter_parts.append(f"[0:a]volume={video_volume}[a0]")

    input_idx = 1

    # BGM
    if bgm and os.path.exists(bgm):
        audio_inputs.extend(["-i", bgm])
        # Loop BGM to match video duration
        video_duration = await get_video_duration(video)
        filter_parts.append(f"[{input_idx}:a]volume={bgm_volume},aloop=loop=-1:size=2e+09,atrim=duration={video_duration}[a{input_idx}]")
        input_idx += 1

    # TTS
    if tts and os.path.exists(tts):
        audio_inputs.extend(["-i", tts])
        filter_parts.append(f"[{input_idx}:a]volume={tts_volume}[a{input_idx}]")
        input_idx += 1

    # Mix all audio
    mix_inputs = "".join([f"[a{i}]" for i in range(input_idx)])
    # normalize=0: Disable FFmpeg auto-normalization, preserve original volume ratios
    filter_parts.append(f"{mix_inputs}amix=inputs={input_idx}:duration=first:dropout_transition=2:normalize=0[aout]")

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
    ] + audio_inputs + [
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output
    ]

    success, msg = await run_ffmpeg(cmd, timeout=600)

    if success:
        logger.info(f"✅ Audio mixingcomplete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Transition effects ==============

# Supported transition types
TRANSITION_TYPES = [
    "fade", "dissolve", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "circleopen", "circleclose", "diagtl", "diagtr", "diagbl", "diagbr",
    "pixelize", "hblur", "wipel"
]


async def add_transition(
    inputs: List[str],
    output: str,
    transition_type: str = "fade",
    duration: float = 0.5
) -> Dict[str, Any]:
    """
    Add transition effects

    Args:
        inputs: Input video list (two)
        output: outputvideo
        transition_type: Transition type
        duration: transition duration (seconds)
    """
    if len(inputs) != 2:
        return {"success": False, "error": "Need two input videos"}

    video1, video2 = inputs

    if not os.path.exists(video1):
        return {"success": False, "error": f"Video does not exist: {video1}"}
    if not os.path.exists(video2):
        return {"success": False, "error": f"Video does not exist: {video2}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # validateTransition type
    if transition_type not in TRANSITION_TYPES:
        transition_type = "fade"

    # Get first video duration
    duration1 = await get_video_duration(video1)
    if duration1 <= 0:
        return {"success": False, "error": "Cannot get video duration"}

    # Calculate transition offset
    offset = duration1 - duration

    # Using xfade filter
    filter_complex = f"[0:v][1:v]xfade=transition={transition_type}:duration={duration}:offset={offset}[outv];[0:a][1:a]acrossfade=d={duration}[outa]"

    cmd = [
        "ffmpeg", "-y",
        "-i", video1,
        "-i", video2,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output
    ]

    success, msg = await run_ffmpeg(cmd, timeout=600)

    if success:
        logger.info(f"✅ Transition addition complete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Color grading ==============

COLOR_PRESETS = {
    "warm": "colorbalance=rs=0.1:gs=0:bs=-0.1,eq=contrast=1.1:saturation=1.2",
    "cool": "colorbalance=rs=-0.1:gs=0:bs=0.1,eq=contrast=1.05:saturation=1.1",
    "vibrant": "eq=contrast=1.2:saturation=1.4",
    "cinematic": "curves=preset=vintage,eq=contrast=1.2:saturation=0.9",
    "desaturated": "eq=saturation=0.7",
    "vintage": "curves=preset=vintage,eq=contrast=1.1:saturation=0.8",
}


async def color_grade(
    video: str,
    output: str,
    preset: str = "warm"
) -> Dict[str, Any]:
    """
    videoColor grading

    Args:
        video: inputvideo
        output: outputvideo
        preset: Color grading preset (warm/cool/vibrant/cinematic/desaturated/vintage)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video does not exist: {video}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    filter_str = COLOR_PRESETS.get(preset, COLOR_PRESETS["warm"])

    cmd = [
        "ffmpeg", "-y",
        "-i", video,
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output
    ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ Color gradingcomplete ({preset}): {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Speed change ==============

def _build_atempo_chain(rate: float) -> str:
    """Build chained atempo filters for rates outside 0.5-2.0 range."""
    filters = []
    remaining = rate
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.4f}")
    return ",".join(filters)


async def change_speed(
    video: str,
    output: str,
    rate: float = 1.0
) -> Dict[str, Any]:
    """
    videoSpeed change

    Args:
        video: inputvideo
        output: outputvideo
        rate: Speed multiplier (0.5=slow motion, 2.0=fast forward)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video does not exist: {video}"}
    if rate <= 0:
        return {"success": False, "error": f"Multiplier must be greater than 0: {rate}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    video_filter = f"setpts={1/rate}*PTS"
    audio_filter = _build_atempo_chain(rate)

    cmd = [
        "ffmpeg", "-y",
        "-i", video,
        "-filter:v", video_filter,
        "-filter:a", audio_filter,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output
    ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ Speed changecomplete ({rate}x): {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Trim video ==============

async def trim_video(
    video: str,
    output: str,
    start: float = 0,
    duration: float = None
) -> Dict[str, Any]:
    """
    Trim video

    Args:
        video: inputvideo
        output: outputvideo
        start: Start time (seconds)
        duration: Duration (seconds), None means until end
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video does not exist: {video}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", video,
    ]

    if duration:
        cmd.extend(["-t", str(duration)])

    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output
    ])

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ Trimming complete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Image generationvideo ==============

async def image_to_video(
    image: str,
    output: str,
    duration: float = 5.0,
    aspect: str = "9:16",
    zoom: bool = True
) -> Dict[str, Any]:
    """
    Generate video from image (Ken Burns effect)

    Args:
        image: inputimage
        output: outputvideo
        duration: Duration（seconds）
        aspect: aspect ratio
        zoom: Whether to add slow zoom effect
    """
    if not os.path.exists(image):
        return {"success": False, "error": f"Image not found: {image}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    w, h = get_resolution_for_aspect(aspect)

    if zoom:
        # Ken Burns effect: slow zoom
        fps = 25
        total_frames = int(duration * fps)
        filter_str = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,zoompan=z='min(zoom+0.001,1.2)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"
    else:
        filter_str = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image,
        "-t", str(duration),
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        output
    ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ Image generationvideocomplete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Command Line Entry ==============

async def cmd_concat(args):
    """Concatenate command"""
    # Priority: CLI > storyboard.json > default value
    aspect = args.aspect
    if aspect is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect = get_aspect_from_storyboard(args.storyboard)
        if aspect:
            logger.info(f"📐 Read aspect ratio from storyboard.json: {aspect}")
    if aspect is None:
        aspect = "9:16"  # final default value
        logger.info(f"📐 Usingdefaultaspect ratio: {aspect}")

    inputs = args.inputs
    output_dir = Path(args.output).parent

    # First validate video parameters
    logger.info("🔍 Validating video parameters...")
    validation = await validate_videos(inputs)

    if not validation["consistent"]:
        logger.warning(f"⚠️ Video parameters inconsistent: {validation['issues']}")
        logger.info("🔧 Auto-normalizing videos...")

        # Create temp directory for normalized videos
        normalize_dir = output_dir / "normalized_temp"
        inputs = await normalize_videos(inputs, str(normalize_dir), aspect)

        # Cleanup temp file markers
        args._normalized_dir = normalize_dir

    # Then concatenate
    result = await concat_videos(
        inputs=inputs,
        output=args.output,
        aspect=aspect
    )

    # Cleanup temp normalized files
    if hasattr(args, '_normalized_dir') and args._normalized_dir.exists():
        import shutil
        shutil.rmtree(args._normalized_dir)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_subtitle(args):
    """Subtitle command"""
    result = await add_subtitles(
        video=args.video,
        srt=args.srt,
        output=args.output,
        font_size=args.font_size,
        font_color=args.font_color,
        position=args.position
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_mix(args):
    """Audio mixingcommand"""
    result = await mix_audio(
        video=args.video,
        output=args.output,
        bgm=args.bgm,
        tts=args.tts,
        video_volume=args.video_volume,
        bgm_volume=args.bgm_volume,
        tts_volume=args.tts_volume
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_transition(args):
    """Transition command"""
    result = await add_transition(
        inputs=args.inputs,
        output=args.output,
        transition_type=args.type,
        duration=args.duration
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_color(args):
    """Color gradingcommand"""
    result = await color_grade(
        video=args.video,
        output=args.output,
        preset=args.preset
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_speed(args):
    """Speed changecommand"""
    result = await change_speed(
        video=args.video,
        output=args.output,
        rate=args.rate
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_trim(args):
    """Trim command"""
    result = await trim_video(
        video=args.video,
        output=args.output,
        start=args.start,
        duration=args.duration
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_image(args):
    """Image generationvideocommand"""
    # Priority: CLI > storyboard.json > default value
    aspect = args.aspect
    if aspect is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect = get_aspect_from_storyboard(args.storyboard)
        if aspect:
            logger.info(f"📐 Read aspect ratio from storyboard.json: {aspect}")
    if aspect is None:
        aspect = "9:16"  # final default value
        logger.info(f"📐 Usingdefaultaspect ratio: {aspect}")

    result = await image_to_video(
        image=args.image,
        output=args.output,
        duration=args.duration,
        aspect=aspect,
        zoom=args.zoom
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


def main():
    parser = argparse.ArgumentParser(
        description="Vico Editor - FFmpeg video editing CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # concat sub-command
    concat_parser = subparsers.add_parser("concat", help="Concatenate videos")
    concat_parser.add_argument("--inputs", "-i", nargs="+", required=True, help="inputvideolist")
    concat_parser.add_argument("--output", "-o", required=True, help="outputvideopath")
    concat_parser.add_argument("--aspect", "-a", default=None, help="aspect ratio (e.g., 16:9, 9:16)")
    concat_parser.add_argument("--storyboard", "-s", help="storyboard.json path, auto-read aspect_ratio")

    # subtitle sub-command
    subtitle_parser = subparsers.add_parser("subtitle", help="Add subtitles")
    subtitle_parser.add_argument("--video", "-v", required=True, help="inputvideo")
    subtitle_parser.add_argument("--srt", "-s", required=True, help="SRT subtitle file")
    subtitle_parser.add_argument("--output", "-o", required=True, help="outputvideopath")
    subtitle_parser.add_argument("--font-size", type=int, default=40, help="Font size")
    subtitle_parser.add_argument("--font-color", default="white", help="Font color")
    subtitle_parser.add_argument("--position", default="bottom", choices=["bottom", "top", "center"], help="Subtitle position")

    # mix sub-command
    mix_parser = subparsers.add_parser("mix", help="Audio mixing")
    mix_parser.add_argument("--video", "-v", required=True, help="inputvideo")
    mix_parser.add_argument("--bgm", "-b", help="Background music")
    mix_parser.add_argument("--tts", "-t", help="Narration audio")
    mix_parser.add_argument("--output", "-o", required=True, help="outputvideopath")
    mix_parser.add_argument("--video-volume", type=float, default=0.3, help="Original video volume")
    mix_parser.add_argument("--bgm-volume", type=float, default=0.6, help="BGM volume")
    mix_parser.add_argument("--tts-volume", type=float, default=1.0, help="TTS volume")

    # transition sub-command
    transition_parser = subparsers.add_parser("transition", help="Add transition")
    transition_parser.add_argument("--inputs", "-i", nargs="+", required=True, help="inputvideolist")
    transition_parser.add_argument("--output", "-o", required=True, help="outputvideopath")
    transition_parser.add_argument("--type", "-t", default="fade", choices=TRANSITION_TYPES, help="Transition type")
    transition_parser.add_argument("--duration", "-d", type=float, default=0.5, help="transition duration (seconds)")

    # color sub-command
    color_parser = subparsers.add_parser("color", help="videoColor grading")
    color_parser.add_argument("--video", "-v", required=True, help="inputvideo")
    color_parser.add_argument("--output", "-o", required=True, help="outputvideopath")
    color_parser.add_argument("--preset", "-p", default="warm", choices=list(COLOR_PRESETS.keys()), help="Color grading preset")

    # speed sub-command
    speed_parser = subparsers.add_parser("speed", help="videoSpeed change")
    speed_parser.add_argument("--video", "-v", required=True, help="inputvideo")
    speed_parser.add_argument("--output", "-o", required=True, help="outputvideopath")
    speed_parser.add_argument("--rate", "-r", type=float, default=1.0, help="Speed multiplier")

    # trim sub-command
    trim_parser = subparsers.add_parser("trim", help="Trim video")
    trim_parser.add_argument("--video", "-v", required=True, help="inputvideo")
    trim_parser.add_argument("--output", "-o", required=True, help="outputvideopath")
    trim_parser.add_argument("--start", "-s", type=float, default=0, help="Start time(seconds)")
    trim_parser.add_argument("--duration", "-d", type=float, help="Duration(seconds)")

    # image sub-command
    image_parser = subparsers.add_parser("image", help="Image generationvideo")
    image_parser.add_argument("--image", "-i", required=True, help="inputimage")
    image_parser.add_argument("--output", "-o", required=True, help="outputvideopath")
    image_parser.add_argument("--duration", "-d", type=float, default=5.0, help="Duration(seconds)")
    image_parser.add_argument("--aspect", "-a", default=None, help="aspect ratio")
    image_parser.add_argument("--storyboard", "-s", help="storyboard.json path, auto-read aspect_ratio")
    image_parser.add_argument("--zoom", action="store_true", help="Add Ken Burns zoom effect")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run corresponding command
    commands = {
        "concat": cmd_concat,
        "subtitle": cmd_subtitle,
        "mix": cmd_mix,
        "transition": cmd_transition,
        "color": cmd_color,
        "speed": cmd_speed,
        "trim": cmd_trim,
        "image": cmd_image,
    }

    return asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    sys.exit(main())