# API Tool Reference

## video_gen_tools.py - API Tools

```bash
# Environment check
python ~/.claude/skills/video-gen/video_gen_tools.py check

# Video generation (Kling backend, default)
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt <description> --duration 5 --output <output>
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <first_frame_image> --prompt <description> --output <output>

# Video generation (Vidu backend - fallback/fast prototype)
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <image> --prompt <description> --backend vidu --duration <seconds> --output <output>

# Kling first/last frame control
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <first_frame_image> --tail-image <last_frame_image> --prompt "Action description" --backend kling --duration 5

# Kling multi-shot mode
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "Story description" --backend kling --multi-shot --shot-type intelligence --duration 10
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "Overall description" --backend kling --multi-shot --shot-type customize --multi-prompt '[{"index":1,"prompt":"Shot 1 description","duration":"3"},{"index":2,"prompt":"Shot 2 description","duration":"4"}]' --duration 7

# Video generation (Kling Omni backend - reference image mode)
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend kling-omni --prompt "Character <<<image_1>>> in scene" --image-list <reference_image> --duration 5 --output <output>

# Kling Omni multiple reference images + multi-shot
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend kling-omni --prompt "Story" --image-list <reference1> <reference2> --multi-shot --shot-type customize --multi-prompt '[{"index":1,"prompt":"<<<image_1>>> Shot 1","duration":"3"}]' --duration 7

# Auto backend selection (provide --image-list auto uses kling-omni, provide --tail-image auto uses kling)
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "<<<image_1>>> at racetrack" --image-list ref.jpg --output out.mp4

# Music generation
python ~/.claude/skills/video-gen/video_gen_tools.py music --prompt <description> --style <style> --output <output>

# TTS voice
python ~/.claude/skills/video-gen/video_gen_tools.py tts --text <text> --voice <voice> --output <output>

# Image generation
python ~/.claude/skills/video-gen/video_gen_tools.py image --prompt <description> --style <style> --output <output>

# Image analysis (built-in multimodal capability)
python ~/.claude/skills/video-gen/video_gen_tools.py vision <image_path> [--prompt "Analysis prompt"]
python ~/.claude/skills/video-gen/video_gen_tools.py vision <directory_path> --batch [--prompt "Analysis prompt"]
```

### Kling / Kling Omni Parameter Description

| Parameter | Applicable Backend | Description |
|-----------|--------------------|-------------|
| `--backend kling` | kling | Kling v3 backend (first frame/first-last frame control) |
| `--backend kling-omni` | kling-omni | Kling Omni backend (reference image mode) |
| `--image` | kling, vidu | First frame image path (image-to-video) |
| `--image-list` | kling-omni | Reference image path list (use `<<<image_1>>>` reference in prompt) |
| `--tail-image` | kling | Last frame image path (first-last frame control) |
| `--multi-shot` | kling, kling-omni | Enable multi-shot mode |
| `--shot-type` | kling, kling-omni | `intelligence` (AI auto) or `customize` (custom) |
| `--multi-prompt` | kling, kling-omni | Custom storyboard list (JSON format) |
| `--audio` | kling, kling-omni | Enable audio-video together |
| `--mode` | kling, kling-omni | `std` (standard) or `pro` (high quality) |

---

## video_gen_editor.py - Editing Tools

```bash
# Concatenation (auto validates resolution + normalization)
python ~/.claude/skills/video-gen/video_gen_editor.py concat --inputs <video_list> --output <output>

# Audio mixing
python ~/.claude/skills/video-gen/video_gen_editor.py mix --video <video> --bgm <music> --output <output>

# Transition
python ~/.claude/skills/video-gen/video_gen_editor.py transition --inputs <video1> <video2> --type <type> --output <output>

# Color grading
python ~/.claude/skills/video-gen/video_gen_editor.py color --video <video> --preset <preset> --output <output>
```

**Transition Types**: fade | dissolve | wipeleft | wiperight | wipeup | wipedown | slideleft | slideright | slideup | slidedown | circleopen | circleclose | pixelize | hblur

**Color Grading Presets**: warm | cool | vibrant | cinematic | desaturated | vintage

---

## Environment Variables

| Variable | Purpose | When Needed |
|----------|---------|-------------|
| YUNWU_API_KEY | Vidu/Kling/Kling-Omni video generation + Gemini image generation | When generating video/image (can be used as fallback for Kling official API) |
| KLING_ACCESS_KEY | Kling video generation Access Key | When using Kling/Kling Omni |
| KLING_SECRET_KEY | Kling video generation Secret Key | When using Kling/Kling Omni |
| SUNO_API_KEY | Suno music generation | When generating BGM |
| VOLCENGINE_TTS_APP_ID | Volcano Engine TTS | When generating narration |
| VOLCENGINE_TTS_ACCESS_TOKEN | Volcano Engine TTS | When generating narration |
| VISION_API_KEY | Built-in vision analysis fallback | When Read tool cannot recognize image |
| VISION_BASE_URL | Vision model API address | When customizing vision model |
| VISION_MODEL | Vision model name | When customizing vision model |

API key can be configured via environment variables or `config.json`.