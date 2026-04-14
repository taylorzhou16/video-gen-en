#!/usr/bin/env python3
"""
Vico Editor - FFmpeg Video Editing CLI Tool

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT = 300  # 5 minutes


# ============== Utility Functions ==============

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
            return False, f"FFmpeg timeout ({timeout}s)"

        if process.returncode == 0:
            return True, "Success"
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
    return (1080, 1920)  # Default 9:16


def get_aspect_from_storyboard(storyboard_path: str) -> Optional[str]:
    """Read aspect_ratio from storyboard.json"""
    try:
        with open(storyboard_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("aspect_ratio")
    except Exception:
        return None


async def has_audio_track(video_path: str) -> bool:
    """Check if video has an audio track"""
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
    """Get video information"""
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
        logger.error(f"Failed to get video info: {e}")
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
    """Get detailed video specifications"""
    info = await get_video_info(video_path)
    if not info:
        return {"path": video_path, "error": "Unable to get video info"}

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
            "issues": List[str],  # Issue descriptions
            "specs": List[dict],  # Each video's parameters
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
            issues.append(f"Video parameter error: {specs['path']} - {specs['error']}")
            continue

        resolutions.add((specs.get("width", 0), specs.get("height", 0)))
        codecs.add(specs.get("codec", "unknown"))
        fps_values.add(specs.get("fps", 0))

    # Check consistency
    if len(resolutions) > 1:
        res_str = ", ".join([f"{w}x{h}" for w, h in resolutions])
        issues.append(f"Inconsistent resolutions: {res_str}")

    if len(codecs) > 1:
        issues.append(f"Inconsistent codecs: {', '.join(codecs)}")

    if len(fps_values) > 1:
        # Allow slight frame rate differences (e.g., 23.976 vs 24)
        fps_range = max(fps_values) - min(fps_values)
        if fps_range > 1:
            issues.append(f"Large frame rate differences: {', '.join(map(str, fps_values))}")

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
    - Resolution: 9:16 -> 1080x1920, 16:9 -> 1920x1080, 1:1 -> 1080x1080
    - Codec: H.264
    - Frame rate: 24fps
    - Pixel format: yuv420p
    - Audio: Unified 48kHz stereo, silent track added for clips without audio

    Returns:
        List of normalized video paths
    """
    w, h = get_resolution_for_aspect(aspect)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    normalized_paths = []
    vf_filter = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"

    for i, video_path in enumerate(video_paths):
        output_file = output_path / f"normalized_{i:03d}.mp4"

        # Check if has audio track
        has_audio = await has_audio_track(video_path)

        if has_audio:
            # Has audio: normalize normally
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
            logger.info(f"Video has no audio track, adding silent track: {video_path}")
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
            logger.info(f"Video normalization complete: {output_file}")
        else:
            logger.warning(f"Video normalization failed, using original file: {video_path}")
            normalized_paths.append(video_path)

    return normalized_paths


# ============== Concatenate Videos ==============

async def concat_videos(
    inputs: List[str],
    output: str,
    aspect: str = "9:16"
) -> Dict[str, Any]:
    """
    Concatenate multiple videos (using concat filter, ensures A/V sync)

    Args:
        inputs: List of input video paths (all clips must have audio tracks, guaranteed by normalize_videos)
        output: Output video path
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

    # Use concat filter (all clips must have audio tracks)
    n = len(inputs)
    filter_str = f"concat=n={n}:v=1:a=1[outv][outa]"

    # Build input arguments
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
        logger.info(f"Video concatenation complete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Add Subtitles ==============

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
        video: Input video
        srt: SRT subtitle file
        output: Output video
        font_size: Font size
        font_color: Font color
        position: Position (bottom/top/center)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video not found: {video}"}
    if not os.path.exists(srt):
        return {"success": False, "error": f"Subtitle file not found: {srt}"}

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
        logger.info(f"Subtitle addition complete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Audio Mixing ==============

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
        video: Input video
        output: Output video
        bgm: Background music (optional)
        tts: Narration audio (optional)
        video_volume: Original video volume (0-1)
        bgm_volume: BGM volume (0-1)
        tts_volume: TTS volume (0-1)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video not found: {video}"}

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
    # normalize=0: disable FFmpeg auto-normalization, preserve original volume ratio
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
        logger.info(f"Audio mixing complete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Transition Effects ==============

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
    Add transition effect

    Args:
        inputs: Input video list (two videos)
        output: Output video
        transition_type: Transition type
        duration: Transition duration (seconds)
    """
    if len(inputs) != 2:
        return {"success": False, "error": "Two input videos required"}

    video1, video2 = inputs

    if not os.path.exists(video1):
        return {"success": False, "error": f"Video not found: {video1}"}
    if not os.path.exists(video2):
        return {"success": False, "error": f"Video not found: {video2}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # Validate transition type
    if transition_type not in TRANSITION_TYPES:
        transition_type = "fade"

    # Get duration of first video
    duration1 = await get_video_duration(video1)
    if duration1 <= 0:
        return {"success": False, "error": "Unable to get video duration"}

    # Calculate transition offset
    offset = duration1 - duration

    # Use xfade filter
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
        logger.info(f"Transition addition complete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Color Grading ==============

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
    Apply color grading to video

    Args:
        video: Input video
        output: Output video
        preset: Color grading preset (warm/cool/vibrant/cinematic/desaturated/vintage)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video not found: {video}"}

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
        logger.info(f"Color grading complete ({preset}): {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Speed Change ==============

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
    Change video speed

    Args:
        video: Input video
        output: Output video
        rate: Speed multiplier (0.5=slow motion, 2.0=fast forward)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video not found: {video}"}
    if rate <= 0:
        return {"success": False, "error": f"Rate must be greater than 0: {rate}"}

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
        logger.info(f"Speed change complete ({rate}x): {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Trim Video ==============

async def trim_video(
    video: str,
    output: str,
    start: float = 0,
    duration: float = None
) -> Dict[str, Any]:
    """
    Trim video

    Args:
        video: Input video
        output: Output video
        start: Start time (seconds)
        duration: Duration (seconds), None means to end
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video not found: {video}"}

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
        logger.info(f"Trim complete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Image to Video ==============

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
        image: Input image
        output: Output video
        duration: Duration (seconds)
        aspect: Aspect ratio
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
        logger.info(f"Image to video complete: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== Narration Synthesis ==============

async def add_narration(
    video: str,
    output: str,
    storyboard: str = None,
    narration_dir: str = None,
    narration_volume: float = 1.0,
    video_volume: float = 1.0
) -> Dict[str, Any]:
    """
    Synthesize narration audio into video at specified time points

    Args:
        video: Input video
        output: Output video
        storyboard: storyboard.json path (contains narration_segments)
        narration_dir: Narration audio directory
        narration_volume: Narration volume
        video_volume: Original video volume
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"Video not found: {video}"}

    # Read storyboard.json to get narration time points
    narration_segments = []
    if storyboard and os.path.exists(storyboard):
        with open(storyboard, 'r', encoding='utf-8') as f:
            data = json.load(f)
            narration_segments = data.get("narration_segments", [])

    if not narration_segments:
        logger.warning("No narration_segments found, copying video directly")
        import shutil
        shutil.copy(video, output)
        return {"success": True, "output": output, "warning": "No narration segments"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # Build filter_complex
    # Inputs: [0] video, [1-N] narration audio
    inputs = ["-i", video]
    filter_parts = []

    # Build audio mix
    audio_mix_parts = [f"[0:a]volume={video_volume}[video]"]

    audio_counter = 0  # Actual added audio count
    for i, seg in enumerate(narration_segments):
        audio_file = None
        if narration_dir:
            # Try multiple naming formats
            seg_id = seg.get("segment_id", str(i+1))
            possible_paths = [
                os.path.join(narration_dir, f"narr_{seg_id}.mp3"),
                os.path.join(narration_dir, f"narration_{seg_id}.mp3"),
                os.path.join(narration_dir, f"{seg_id}.mp3"),
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    audio_file = p
                    break

        if not audio_file:
            logger.warning(f"Narration audio not found: segment {seg_id}")
            continue

        inputs.extend(["-i", audio_file])
        audio_counter += 1

        # Get time range
        time_range = seg.get("overall_time_range", "0-5")
        if isinstance(time_range, str) and "-" in time_range:
            start, end = time_range.split("-")
            start = float(start)
        else:
            start = 0

        # Delay audio to correct time point
        # audio_idx: video is input 0, first narration is input 1, second is input 2...
        audio_idx = audio_counter
        filter_parts.append(f"[{audio_idx}:a]adelay={int(start*1000)}|{int(start*1000)},volume={narration_volume}[narr{audio_counter}]")
        audio_mix_parts.append(f"[narr{audio_counter}]")

    # Mix all audio
    if len(audio_mix_parts) > 1:
        # Has narration audio
        filter_parts.append(f"{''.join(audio_mix_parts)}amix=inputs={len(audio_mix_parts)}:duration=first[aout]")
        filter_complex = ";".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            output
        ]
    else:
        # No narration audio, copy directly
        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-c", "copy",
            output
        ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"Narration synthesis complete: {output}")
        return {"success": True, "output": output, "segments": len(narration_segments)}
    else:
        return {"success": False, "error": msg}


def get_audio_duration_sync(audio_path: str) -> float:
    """
    Get precise audio duration (seconds) using ffprobe
    Synchronous version, for use in async functions
    """
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def calculate_shot_times(storyboard: dict) -> dict:
    """
    Calculate start time for each shot

    Returns:
        {shot_id: start_time_in_seconds}
    """
    shot_times = {}
    current_time = 0

    for scene in storyboard.get("scenes", []):
        for shot in scene.get("shots", []):
            shot_id = shot["shot_id"]
            shot_times[shot_id] = current_time
            current_time += shot["duration"]

    return shot_times


def calculate_narration_times(
    segments_info: list,
    video_duration: float,
    gap: float = 0.5
) -> tuple:
    """
    Calculate non-overlapping narration time points

    Args:
        segments_info: List containing info for each narration segment
        video_duration: Total video duration
        gap: Gap between segments (seconds)

    Returns:
        (time_points, warnings)
        - time_points: [{"start_time": x, "end_time": y, "skipped": bool}, ...]
        - warnings: List of warning messages
    """
    time_points = []
    warnings = []
    current_time = 0  # End time of previous narration segment

    # Calculate total narration duration
    total_narration = sum(seg["duration"] for seg in segments_info)
    total_gap = gap * (len(segments_info) - 1) if len(segments_info) > 1 else 0
    required_duration = total_narration + total_gap

    if required_duration > video_duration:
        warnings.append(
            f"Total narration duration ({total_narration:.1f}s) + gaps ({total_gap:.1f}s) = {required_duration:.1f}s, "
            f"exceeds video duration ({video_duration:.1f}s), will compress gaps and may skip some segments"
        )

    for i, seg in enumerate(segments_info):
        duration = seg["duration"]
        shot_start = seg.get("shot_start", 0)
        seg_id = seg.get("segment_id", f"segment_{i+1}")

        # Check if remaining space is sufficient
        min_start = max(current_time, shot_start)
        min_end = min_start + duration

        if min_end > video_duration:
            # Insufficient space, skip this segment
            warnings.append(f"{seg_id}: Insufficient space, skipped (needs {duration:.1f}s, remaining {video_duration - current_time:.1f}s)")
            time_points.append({"start_time": 0, "end_time": 0, "skipped": True})
            continue

        # Calculate remaining available time and remaining segment count
        remaining_segments = len([s for s in segments_info[i:] if s.get("duration", 0) > 0])
        remaining_narration = sum(s["duration"] for s in segments_info[i:])
        remaining_gap = gap * (remaining_segments - 1) if remaining_segments > 1 else 0
        remaining_required = remaining_narration + remaining_gap
        remaining_available = video_duration - current_time

        # If remaining space is tight, dynamically adjust gap
        effective_gap = gap
        if remaining_required > remaining_available and remaining_segments > 1:
            # Calculate minimum gap needed
            needed_gap = (remaining_available - remaining_narration) / (remaining_segments - 1)
            effective_gap = max(0, needed_gap)  # Can compress to 0

        # Start time
        start_time = max(current_time + effective_gap, shot_start)
        end_time = start_time + duration

        # Final check
        if end_time > video_duration:
            end_time = video_duration
            warnings.append(f"{seg_id}: Truncated to video end")

        time_points.append({"start_time": start_time, "end_time": end_time, "skipped": False})
        current_time = end_time  # Update to current segment's end time

    return time_points, warnings


async def smart_narration_mix(
    video_path: str,
    narration_dir: str,
    storyboard_path: str,
    output: str,
    bgm_path: str = None,
    bgm_volume: float = 0.15,
    narration_volume: float = 1.5,
    gap: float = 0.5
) -> Dict[str, Any]:
    """
    Smart narration synthesis:
    1. Read all narration audio files and their precise durations (ffprobe)
    2. Locate shot start times based on target_shot
    3. Calculate non-overlapping time points, reserve gaps
    4. Synthesize final audio

    Args:
        video_path: Video file path
        narration_dir: Narration audio directory
        storyboard_path: storyboard.json path
        output: Output video path
        bgm_path: Background music path (optional)
        bgm_volume: BGM volume (default 0.15)
        narration_volume: Narration volume (default 1.5)
        gap: Gap between segments (seconds, default 0.5)

    Returns:
        {"success": True, "output": output, "segments_info": [...]}
    """
    if not os.path.exists(video_path):
        return {"success": False, "error": f"Video not found: {video_path}"}

    if not os.path.exists(storyboard_path):
        return {"success": False, "error": f"storyboard.json not found: {storyboard_path}"}

    # Read storyboard
    with open(storyboard_path, 'r', encoding='utf-8') as f:
        storyboard = json.load(f)

    segments = storyboard.get("narration_segments", [])
    if not segments:
        logger.info("No narration segments, copying video directly")
        import shutil
        shutil.copy(video_path, output)
        return {"success": True, "output": output, "skipped": True}

    # Get video duration
    video_duration = await get_video_duration(video_path)

    # Get start time for each shot
    shot_times = calculate_shot_times(storyboard)

    # Collect precise duration for each narration segment
    segments_info = []
    for seg in segments:
        seg_id = seg.get("segment_id", "")

        # Find audio file
        audio_file = None
        possible_paths = [
            os.path.join(narration_dir, f"{seg_id}.mp3"),
            os.path.join(narration_dir, f"narr_{seg_id}.mp3"),
            os.path.join(narration_dir, f"narration_{seg_id}.mp3"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                audio_file = p
                break

        if not audio_file:
            logger.warning(f"Narration audio not found: {seg_id}")
            continue

        # Get precise duration
        duration = get_audio_duration_sync(audio_file)

        # Get corresponding shot start time
        target_shot = seg.get("target_shot", "")
        shot_start = shot_times.get(target_shot, 0)

        segments_info.append({
            "segment_id": seg_id,
            "audio_path": audio_file,
            "duration": duration,
            "shot_start": shot_start,
            "target_shot": target_shot,
            "text": seg.get("text", "")[:30] + "..."
        })

    if not segments_info:
        logger.warning("No valid narration audio")
        import shutil
        shutil.copy(video_path, output)
        return {"success": True, "output": output, "warning": "No valid narration"}

    # Calculate non-overlapping time points
    time_points, warnings = calculate_narration_times(segments_info, video_duration, gap)

    # Print warnings
    for w in warnings:
        logger.warning(w)

    # Update segments_info, filter out skipped segments
    active_segments = []
    for i, tp in enumerate(time_points):
        segments_info[i]["start_time"] = tp["start_time"]
        segments_info[i]["end_time"] = tp["end_time"]
        segments_info[i]["skipped"] = tp.get("skipped", False)

        if tp.get("skipped"):
            logger.warning(f"  Skipped: {segments_info[i]['segment_id']}")
        else:
            logger.info(f"  {segments_info[i]['segment_id']}: {tp['start_time']:.1f}s - {tp['end_time']:.1f}s ({segments_info[i]['duration']:.1f}s)")
            active_segments.append(segments_info[i])

    # Build FFmpeg command
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # If no active segments, copy video directly
    if not active_segments:
        logger.warning("No available narration segments, copying video directly")
        import shutil
        shutil.copy(video_path, output)
        return {
            "success": True,
            "output": output,
            "warning": "All narration segments skipped",
            "segments_info": segments_info
        }

    cmd = ["ffmpeg", "-y"]
    filter_parts = []
    input_idx = 1

    # Add video input
    cmd.extend(["-i", video_path])

    # Add narration inputs and build filter (only active_segments)
    mix_inputs = ["[0:a]"]

    for seg in active_segments:
        cmd.extend(["-i", seg["audio_path"]])
        delay_ms = int(seg["start_time"] * 1000)
        filter_parts.append(
            f"[{input_idx}:a]adelay={delay_ms}|{delay_ms},volume={narration_volume}[n{input_idx}]"
        )
        mix_inputs.append(f"[n{input_idx}]")
        input_idx += 1

    # Add BGM (if available)
    if bgm_path and os.path.exists(bgm_path):
        cmd.extend(["-i", bgm_path])
        filter_parts.append(f"[{input_idx}:a]volume={bgm_volume}[bgm]")
        mix_inputs.append("[bgm]")

    # amix mixing - note: inputs are concatenated directly without commas
    filter_parts.append(
        f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:normalize=0[aout]"
    )

    cmd.extend([
        "-filter_complex", ";".join(filter_parts),
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output
    ])

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"Smart narration synthesis complete: {output}")
        return {
            "success": True,
            "output": output,
            "segments_count": len(active_segments),
            "total_segments": len(segments_info),
            "segments_info": segments_info,
            "warnings": warnings if warnings else None
        }
    else:
        return {"success": False, "error": msg}


# ============== CLI Entry Point ==============

async def cmd_concat(args):
    """Concatenate command"""
    # Priority: CLI args > storyboard.json > default value
    aspect = args.aspect
    if aspect is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect = get_aspect_from_storyboard(args.storyboard)
        if aspect:
            logger.info(f"Read aspect ratio from storyboard.json: {aspect}")
    if aspect is None:
        aspect = "9:16"  # Final default value
        logger.info(f"Using default aspect ratio: {aspect}")

    inputs = args.inputs
    output_dir = Path(args.output).parent

    # First validate video parameters
    logger.info("Validating video parameters...")
    validation = await validate_videos(inputs)

    if not validation["consistent"]:
        logger.warning(f"Inconsistent video parameters: {validation['issues']}")
        logger.info("Auto-normalizing videos...")

        # Create temp directory for normalized videos
        normalize_dir = output_dir / "normalized_temp"
        inputs = await normalize_videos(inputs, str(normalize_dir), aspect)

        # Mark temp files for cleanup
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
    """Audio mix command"""
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
    """Color grading command"""
    result = await color_grade(
        video=args.video,
        output=args.output,
        preset=args.preset
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_speed(args):
    """Speed change command"""
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
    """Image to video command"""
    # Priority: CLI args > storyboard.json > default value
    aspect = args.aspect
    if aspect is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect = get_aspect_from_storyboard(args.storyboard)
        if aspect:
            logger.info(f"Read aspect ratio from storyboard.json: {aspect}")
    if aspect is None:
        aspect = "9:16"  # Final default value
        logger.info(f"Using default aspect ratio: {aspect}")

    result = await image_to_video(
        image=args.image,
        output=args.output,
        duration=args.duration,
        aspect=aspect,
        zoom=args.zoom
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_narration(args):
    """Narration synthesis command"""
    result = await add_narration(
        video=args.video,
        output=args.output,
        storyboard=args.storyboard,
        narration_dir=args.narration_dir,
        narration_volume=args.narration_volume,
        video_volume=args.video_volume
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_smart_narration(args):
    """Smart narration synthesis command"""
    result = await smart_narration_mix(
        video_path=args.video,
        narration_dir=args.narration_dir,
        storyboard_path=args.storyboard,
        output=args.output,
        bgm_path=args.bgm,
        bgm_volume=args.bgm_volume,
        narration_volume=args.narration_volume,
        gap=args.gap
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


def main():
    parser = argparse.ArgumentParser(
        description="Vico Editor - FFmpeg Video Editing CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # concat subcommand
    concat_parser = subparsers.add_parser("concat", help="Concatenate videos")
    concat_parser.add_argument("--inputs", "-i", nargs="+", required=True, help="Input video list")
    concat_parser.add_argument("--output", "-o", required=True, help="Output video path")
    concat_parser.add_argument("--aspect", "-a", default=None, help="Aspect ratio (e.g., 16:9, 9:16)")
    concat_parser.add_argument("--storyboard", "-s", help="storyboard.json path, auto-read aspect_ratio")

    # subtitle subcommand
    subtitle_parser = subparsers.add_parser("subtitle", help="Add subtitles")
    subtitle_parser.add_argument("--video", "-v", required=True, help="Input video")
    subtitle_parser.add_argument("--srt", "-s", required=True, help="SRT subtitle file")
    subtitle_parser.add_argument("--output", "-o", required=True, help="Output video path")
    subtitle_parser.add_argument("--font-size", type=int, default=40, help="Font size")
    subtitle_parser.add_argument("--font-color", default="white", help="Font color")
    subtitle_parser.add_argument("--position", default="bottom", choices=["bottom", "top", "center"], help="Subtitle position")

    # mix subcommand
    mix_parser = subparsers.add_parser("mix", help="Audio mixing")
    mix_parser.add_argument("--video", "-v", required=True, help="Input video")
    mix_parser.add_argument("--bgm", "-b", help="Background music")
    mix_parser.add_argument("--tts", "-t", help="Narration audio")
    mix_parser.add_argument("--output", "-o", required=True, help="Output video path")
    mix_parser.add_argument("--video-volume", type=float, default=0.3, help="Original video volume")
    mix_parser.add_argument("--bgm-volume", type=float, default=0.6, help="BGM volume")
    mix_parser.add_argument("--tts-volume", type=float, default=1.0, help="TTS volume")

    # transition subcommand
    transition_parser = subparsers.add_parser("transition", help="Add transition")
    transition_parser.add_argument("--inputs", "-i", nargs="+", required=True, help="Input video list")
    transition_parser.add_argument("--output", "-o", required=True, help="Output video path")
    transition_parser.add_argument("--type", "-t", default="fade", choices=TRANSITION_TYPES, help="Transition type")
    transition_parser.add_argument("--duration", "-d", type=float, default=0.5, help="Transition duration (seconds)")

    # color subcommand
    color_parser = subparsers.add_parser("color", help="Video color grading")
    color_parser.add_argument("--video", "-v", required=True, help="Input video")
    color_parser.add_argument("--output", "-o", required=True, help="Output video path")
    color_parser.add_argument("--preset", "-p", default="warm", choices=list(COLOR_PRESETS.keys()), help="Color preset")

    # speed subcommand
    speed_parser = subparsers.add_parser("speed", help="Video speed change")
    speed_parser.add_argument("--video", "-v", required=True, help="Input video")
    speed_parser.add_argument("--output", "-o", required=True, help="Output video path")
    speed_parser.add_argument("--rate", "-r", type=float, default=1.0, help="Speed rate")

    # trim subcommand
    trim_parser = subparsers.add_parser("trim", help="Trim video")
    trim_parser.add_argument("--video", "-v", required=True, help="Input video")
    trim_parser.add_argument("--output", "-o", required=True, help="Output video path")
    trim_parser.add_argument("--start", "-s", type=float, default=0, help="Start time (seconds)")
    trim_parser.add_argument("--duration", "-d", type=float, help="Duration (seconds)")

    # image subcommand
    image_parser = subparsers.add_parser("image", help="Generate video from image")
    image_parser.add_argument("--image", "-i", required=True, help="Input image")
    image_parser.add_argument("--output", "-o", required=True, help="Output video path")
    image_parser.add_argument("--duration", "-d", type=float, default=5.0, help="Duration (seconds)")
    image_parser.add_argument("--aspect", "-a", default=None, help="Aspect ratio")
    image_parser.add_argument("--storyboard", "-s", help="storyboard.json path, auto-read aspect_ratio")
    image_parser.add_argument("--zoom", action="store_true", help="Add Ken Burns zoom effect")

    # narration subcommand
    narration_parser = subparsers.add_parser("narration", help="Narration synthesis")
    narration_parser.add_argument("--video", "-v", required=True, help="Input video")
    narration_parser.add_argument("--output", "-o", required=True, help="Output video path")
    narration_parser.add_argument("--storyboard", "-s", help="storyboard.json path (contains narration_segments)")
    narration_parser.add_argument("--narration-dir", "-n", help="Narration audio directory")
    narration_parser.add_argument("--narration-volume", type=float, default=1.0, help="Narration volume")
    narration_parser.add_argument("--video-volume", type=float, default=1.0, help="Original video volume")

    # smart-narration subcommand (smart narration synthesis)
    smart_narration_parser = subparsers.add_parser("smart-narration", help="Smart narration synthesis (auto-calculate time points, avoid overlap)")
    smart_narration_parser.add_argument("--video", "-v", required=True, help="Input video")
    smart_narration_parser.add_argument("--output", "-o", required=True, help="Output video path")
    smart_narration_parser.add_argument("--storyboard", "-s", required=True, help="storyboard.json path")
    smart_narration_parser.add_argument("--narration-dir", "-n", required=True, help="Narration audio directory")
    smart_narration_parser.add_argument("--bgm", "-b", help="Background music path (optional)")
    smart_narration_parser.add_argument("--bgm-volume", type=float, default=0.15, help="BGM volume (default 0.15)")
    smart_narration_parser.add_argument("--narration-volume", type=float, default=1.5, help="Narration volume (default 1.5)")
    smart_narration_parser.add_argument("--gap", type=float, default=0.5, help="Narration gap in seconds (default 0.5)")

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
        "narration": cmd_narration,
        "smart-narration": cmd_smart_narration,
    }

    return asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    sys.exit(main())