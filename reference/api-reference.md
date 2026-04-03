# API Tools Reference

## video_gen_tools.py - API Tools

```bash
# Environment check
python ~/.claude/skills/video-gen/video_gen_tools.py check

# Video generation (Kling backend, default)
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt <description> --duration 5 --output <output>
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <first-frame-image> --prompt <description> --output <output>

# Video generation (Vidu backend - fallback/rapid prototyping)
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <image> --prompt <description> --backend vidu --duration <seconds> --output <output>

# Kling first/last frame control
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <first-frame-image> --tail-image <last-frame-image> --prompt "action description" --backend kling --duration 5

# Kling multi-shot mode
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "story description" --backend kling --multi-shot --shot-type intelligence --duration 10
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "overall description" --backend kling --multi-shot --shot-type customize --multi-prompt '[{"index":1,"prompt":"shot 1 description","duration":"3"},{"index":2,"prompt":"shot 2 description","duration":"4"}]' --duration 7

# Video generation (Kling Omni backend - reference image mode)
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend kling-omni --prompt "character <<<image_1>>> in scene" --image-list <reference-image> --duration 5 --output <output>

# Kling Omni multi-reference + multi-shot
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend kling-omni --prompt "story" --image-list <ref-image-1> <ref-image-2> --multi-shot --shot-type customize --multi-prompt '[{"index":1,"prompt":"<<<image_1>>> shot 1","duration":"3"}]' --duration 7

# Auto backend selection (providing --image-list auto-uses kling-omni, providing --tail-image auto-uses kling)
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "<<<image_1>>> on the field" --image-list ref.jpg --output out.mp4

# Music generation
python ~/.claude/skills/video-gen/video_gen_tools.py music --prompt <description> --style <style> --output <output>

# TTS voice
python ~/.claude/skills/video-gen/video_gen_tools.py tts --text <text> --voice <voice-type> --output <output>

# Image generation
python ~/.claude/skills/video-gen/video_gen_tools.py image --prompt <description> --style <style> --output <output>

# Image analysis (built-in multimodal capability)
python ~/.claude/skills/video-gen/video_gen_tools.py vision <image-path> [--prompt "analysis prompt"]
python ~/.claude/skills/video-gen/video_gen_tools.py vision <directory-path> --batch [--prompt "analysis prompt"]
```

### Kling / Kling Omni Parameter Reference

| Parameter | Applicable Backend | Description |
|------|---------|------|
| `--backend kling` | kling | Kling v3 backend (first-frame/first-last frame control) |
| `--backend kling-omni` | kling-omni | Kling Omni backend (reference image mode) |
| `--image` | kling, vidu | First frame image path (image-to-video) |
| `--image-list` | kling-omni | Reference image path list (use `<<<image_1>>>` in prompt to reference) |
| `--tail-image` | kling | Last frame image path (first-last frame control) |
| `--multi-shot` | kling, kling-omni | Enable multi-shot mode |
| `--shot-type` | kling, kling-omni | `intelligence` (AI automatic) or `customize` (custom) |
| `--multi-prompt` | kling, kling-omni | Custom shot list (JSON format) |
| `--audio` | kling, kling-omni | Enable audio-video sync output |
| `--mode` | kling, kling-omni | `std` (standard) or `pro` (high quality) |

---

## video_gen_editor.py - Editing Tools

```bash
# Concatenate (auto-validate resolution + normalize)
python ~/.claude/skills/video-gen/video_gen_editor.py concat --inputs <video-list> --output <output>

# Audio mixing
python ~/.claude/skills/video-gen/video_gen_editor.py mix --video <video> --bgm <music> --output <output>

# Transition
python ~/.claude/skills/video-gen/video_gen_editor.py transition --inputs <video1> <video2> --type <type> --output <output>

# Color grading
python ~/.claude/skills/video-gen/video_gen_editor.py color --video <video> --preset <preset> --output <output>
```

**Transition types**: fade | dissolve | wipeleft | wiperight | wipeup | wipedown | slideleft | slideright | slideup | slidedown | circleopen | circleclose | pixelize | hblur

**Color presets**: warm | cool | vibrant | cinematic | desaturated | vintage

---

## Environment Variables

| Variable | Purpose | When Required |
|------|------|---------|
| COMPASS_API_KEY | Gemini image generation + Gemini TTS | When generating images/TTS (highest priority) |
| FAL_API_KEY | Gemini image generation + Kling-Omni video (fal.ai proxy) | When generating images/videos (backup) |
| YUNWU_API_KEY | Vidu/Kling/Kling-Omni video generation + image generation (yunwu proxy) | When generating videos/images (lowest priority backup) |
| KLING_ACCESS_KEY | Kling video generation Access Key | When using Kling/Kling Omni official API |
| KLING_SECRET_KEY | Kling video generation Secret Key | When using Kling/Kling Omni official API |
| SEEDANCE_API_KEY | Seedance video generation (piapi.ai proxy) | When using Seedance backend |
| SUNO_API_KEY | Suno music generation | When generating BGM |
| VOLCENGINE_TTS_APP_ID | Volcano Engine TTS | When generating narration |
| VOLCENGINE_TTS_ACCESS_TOKEN | Volcano Engine TTS | When generating narration |
| VISION_API_KEY | Built-in vision analysis fallback | When Read tool cannot recognize images |
| VISION_BASE_URL | Vision model API URL | When using custom vision model |
| VISION_MODEL | Vision model name | When using custom vision model |

**Provider Priority**:
- Image generation: compass → fal → yunwu
- Video generation: official → fal → yunwu

API keys can be configured via environment variables or `config.json`.