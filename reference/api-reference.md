# API Tools Reference

## video_gen_tools.py - API Tools

```bash
# Environment check
python ~/.claude/skills/video-gen/video_gen_tools.py check

# Storyboard validation (must pass before Phase 4 execution)
python ~/.claude/skills/video-gen/video_gen_tools.py validate --storyboard storyboard/storyboard.json

# Video generation (Kling backend, default)
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt <description> --duration 5 --output <output>
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <first_frame_image> --prompt <description> --output <output>

# Kling first/last frame control
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <first_frame_image> --tail-image <last_frame_image> --prompt "action description" --backend kling --duration 5

# Kling multi-shot mode
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "story description" --backend kling --multi-shot --shot-type intelligence --duration 10
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "overall description" --backend kling --multi-shot --shot-type customize --multi-prompt '[{"index":1,"prompt":"shot 1 description","duration":"3"},{"index":2,"prompt":"shot 2 description","duration":"4"}]' --duration 7

# Video generation (Kling Omni backend - reference image mode)
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend kling-omni --prompt "character <<<image_1>>> in scene" --image-list <reference_image> --duration 5 --output <output>

# Kling Omni multi-reference + multi-shot
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend kling-omni --prompt "story" --image-list <ref1> <ref2> --multi-shot --shot-type customize --multi-prompt '[{"index":1,"prompt":"<<<image_1>>> shot 1","duration":"3"}]' --duration 7

# Auto backend selection (providing --image-list auto-uses kling-omni, providing --tail-image auto-uses kling)
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "<<<image_1>>> on the field" --image-list ref.jpg --output out.mp4

# Seedance 2 auto-assembly mode (recommended: automatically calculate time segments, assemble prompts, and arrange image_urls from storyboard)
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend seedance --storyboard storyboard/storyboard.json --scene scene_1 --output generated/videos/scene_1.mp4

# Seedance 2 manual mode (fallback)
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend seedance --prompt "time-segmented prompt..." --image-list frame.png ref.jpg --duration 8 --output out.mp4

# Seedance 2 first/last frame control mode
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend seedance --mode first_last_frames --image-list <first_frame> <last_frame> --prompt "action description" --duration 5 --output out.mp4

# Veo3 text-to-video (Google Veo3, only supports 4/6/8s)
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend veo3 --prompt "description..." --duration 8 --output out.mp4

# Veo3 image-to-video (first frame control)
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend veo3 --image first_frame.png --prompt "description..." --duration 8 --output out.mp4

# Music generation
python ~/.claude/skills/video-gen/video_gen_tools.py music --prompt <description> --style <style> --output <output>

# TTS voice
python ~/.claude/skills/video-gen/video_gen_tools.py tts --text <text> --voice <voice> --output <output>

# Image generation
python ~/.claude/skills/video-gen/video_gen_tools.py image --prompt <description> --style <style> --output <output>

# Image analysis (built-in multimodal capability)
python ~/.claude/skills/video-gen/video_gen_tools.py vision <image_path> [--prompt "analysis prompt"]
python ~/.claude/skills/video-gen/video_gen_tools.py vision <directory_path> --batch [--prompt "analysis prompt"]
```

### Kling / Kling Omni Parameters

| Parameter | Applicable Backends | Description |
|------|---------|------|
| `--backend kling` | kling | Kling v3 backend (first frame/first-last frame control) |
| `--backend kling-omni` | kling-omni | Kling Omni backend (reference image mode) |
| `--image` | kling, vidu | First frame image path (image-to-video) |
| `--image-list` | kling-omni | Reference image path list (use `<<<image_1>>>` in prompt to reference) |
| `--tail-image` | kling | Last frame image path (first-last frame control) |
| `--multi-shot` | kling, kling-omni | Enable multi-shot mode |
| `--shot-type` | kling, kling-omni | `intelligence` (AI auto) or `customize` (custom) |
| `--multi-prompt` | kling, kling-omni | Custom shot list (JSON format) |
| `--audio` | kling, kling-omni | Enable audio generation with video |
| `--mode` | kling, kling-omni | `std` (standard) or `pro` (high quality) |

### Seedance 2 Parameters

| Parameter | Description |
|------|------|
| `--backend seedance` | Use Seedance 2 backend |
| `--provider` | Provider selection: `fal` (recommended) / `piapi` (fallback), default auto-select (fal > piapi) |
| `--storyboard` + `--scene` | Auto-assembly mode: read scene from storyboard, automatically calculate time segments, assemble prompts, arrange image_urls, align duration |
| `--prompt` | Manual mode: directly specify time-segmented prompt (for fallback), reference format: `@Image1` / `@Video1` / `@Audio1` |
| `--image-list` | Manual mode: image list (storyboard images first, character reference images after), max 9 images (fal) |
| `--duration` | Duration: **4-15s (any integer)** or `auto` (fal only) |
| `--resolution` | Resolution: **480p** (fast) / **720p** (balanced), fal provider only |
| `--seed` | Random seed: for reproducing results, fal provider only |
| `--end-user-id` | End user ID: fal compliance requirement |
| `--model` | Model version: `fast` (quick, ~60s) / `high_quality` (high quality), fal provider only |
| `--generate-audio` | Whether to generate audio: default true, fal provider only |
| `--audio-urls` | Audio reference URL list (optional) |
| `--video-urls` | Video reference URL list (optional) |
| `--aspect-ratio` | Aspect ratio: **16:9/9:16/4:3/3:4/21:9/auto** |

**fal vs piapi Comparison**:

| Feature | fal provider | piapi provider |
|------|-------------|----------------|
| API Key | FAL_API_KEY | SEEDANCE_API_KEY |
| Generation speed | ~60s | ~120s |
| resolution | Supported 480p/720p | Not supported |
| seed | Supported | Not supported |
| Model version | fast/high_quality | seedance-2-fast/seedance-2 |
| Image count | Max 9 images | Max 12 images |
| Reference format | @Image1 | @image1 |

**CLI Examples**:

```bash
# fal Seedance (auto-selected when FAL_API_KEY exists)
python video_gen_tools.py video --backend seedance --prompt "..." --duration 10 --output out.mp4

# Specify resolution and seed
python video_gen_tools.py video --backend seedance --prompt "..." \
  --resolution 480p --seed 12345 --output out.mp4

# reference-to-video (use @Image1 reference)
python video_gen_tools.py video --backend seedance \
  --prompt "@Image1 character in scene..." \
  --image-list ref.jpg --duration 8 --output out.mp4

# High quality version
python video_gen_tools.py video --backend seedance --model high_quality \
  --prompt "..." --image-list ref.jpg --output out.mp4

# Specify piapi provider
python video_gen_tools.py video --backend seedance --provider piapi \
  --prompt "..." --output out.mp4
```

### Veo3 Parameters

| Parameter | Description |
|------|------|
| `--backend veo3` | Use Veo3 backend (requires COMPASS_API_KEY) |
| `--prompt` | Video description |
| `--image` | Optional: first frame image path (image-to-video mode) |
| `--duration` | Duration: only supports 4/6/8 seconds (auto-aligns to nearest value) |
| `--aspect-ratio` | Aspect ratio |
| `--output` | Output file path |

**Note**: Veo3 generates audio by default, no need for `--audio` parameter. Does not support `--image-list`, `--multi-shot`, `--tail-image`.

### validate Parameters

| Parameter | Description |
|------|------|
| `--storyboard` | storyboard.json path (required) |

**Validation Content**:
- Schema: existence of `scenes[]`, `aspect_ratio`
- Seedance: total scene duration within **4-15s range**
- Veo3: single shot duration must be 4/6/8
- Kling/Vidu: single shot duration range
- Backend-mode consistency
- Reference image file existence
- API key availability

**Output Format**: `{"valid": bool, "errors": [...], "warnings": [...]}`

---

## video_gen_editor.py - Editing Tools

```bash
# Concatenate (auto-validate resolution + normalize)
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
|------|------|---------|
| COMPASS_API_KEY | Gemini image generation + Gemini TTS + **Veo3 video** | When generating images/TTS/Veo3 videos |
| FAL_API_KEY | Gemini image generation + Kling-Omni video (fal.ai proxy) | When generating images/videos (backup) |
| YUNWU_API_KEY | Gemini image generation (yunwu proxy) | When generating images (lowest priority backup) |
| KLING_ACCESS_KEY | Kling video generation Access Key | When using Kling/Kling Omni official API |
| KLING_SECRET_KEY | Kling video generation Secret Key | When using Kling/Kling Omni official API |
| SEEDANCE_API_KEY | Seedance video generation (piapi.ai proxy) | When using Seedance backend |
| SUNO_API_KEY | Suno music generation | When generating BGM |
| VISION_API_KEY | Built-in vision analysis fallback | When Read tool cannot recognize images |
| VISION_BASE_URL | Vision model API URL | When using custom vision model |
| VISION_MODEL | Vision model name | When using custom vision model |

**Provider Priority**:
- Image generation: compass -> fal -> yunwu
- Video generation: official -> fal

API keys can be configured via environment variables or `config.json`.