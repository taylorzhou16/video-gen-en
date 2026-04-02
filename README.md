# Video-Gen - AI Video Editing Skill

A Claude Code Skill that brings AI video editing capabilities into your conversations.

## Architecture

**Core Concept**: Claude itself is the Director Agent, no additional Agent code needed.

```
~/.claude/skills/video-gen/
├── SKILL.md                # Core workflow instructions (~290 lines)
├── reference/
│   ├── storyboard-spec.md  # Complete storyboard design specification
│   ├── backend-guide.md    # Backend selection and reference image strategy
│   ├── prompt-guide.md     # Prompt writing and consistency specifications
│   └── api-reference.md    # CLI parameters and environment variables
├── video_gen_tools.py           # API tools (video/music/TTS/image generation)
├── video_gen_editor.py          # FFmpeg editing tools
└── config.json             # API key configuration
```

**Responsibilities**:
- **Claude**: Intent recognition, creative generation, storyboard design, workflow planning
- **video_gen_tools.py**: Vidu/Kling/Suno/TTS/Gemini API calls
- **video_gen_editor.py**: FFmpeg video editing operations

## Features

- ✅ **Material Analysis** - Automatically recognize image/video content, scenes, emotions
- ✅ **Creative Generation** - Interactive question cards, customized video creative plans
- ✅ **Storyboard Design** - Generate storyboard scripts and video generation prompts
- ✅ **AI Video Generation**
  - **Kling v3**(default)：3-15s, precise first frame control, good visual quality
  - **Kling v3 Omni**：3-15s, multi-reference images, best character consistency
  - **Vidu Q3 Pro**（fallback）：image-to-video/text-to-video (5-10s)
- ✅ **AI Music Generation** - Suno V4.5 background music
- ✅ **TTS Voice Synthesis** - Volcengine TTS
- ✅ **AI Image Generation** - Gemini image generation
- ✅ **Video Editing** - Transitions, subtitles, color grading, speed change, audio mixing

## Usage Recommendations

### Recommended Models

**Recommend using multimodal models (e.g., Kimi K2.5) for best experience.**

Multimodal models have stronger understanding of materials，Can more accurately recognize scenes, characters, emotions and visual styles in images/videos。If your primary model is not multimodal, you can call `/vision` skill to supplement visual understanding.

### Guiding the Model

Current capabilities are still basic, **recommend guiding the model during use**. For example:
- Actively describe desired video style, pacing and mood
- Provide specific feedback on storyboard plans
- Give timely feedback during generation to help model adjust direction

### Project Positioning

This project aims to fully leverage Claude Code Agent's intelligent capabilities，Provide all tools and capabilities related to video generation，Explore practical effects of AI-assisted video creation。**This is an exploratory project, still continuously updating.** Welcome to try various creative ideas, your feedback will help us continuously improve.

**Flexible API Support**: The image and video generation APIs (Vidu, Gemini) can be replaced with your preferred channels.API calls in `video_gen_tools.py` are clearly encapsulated, easy to integrate other providers (OpenAI, Midjourney, Stability AI, etc.).

## Installation

```bash
# Copy entire directory to skills directory
mkdir -p ~/.claude/skills/video-gen
cp -r SKILL.md reference/ video_gen_tools.py video_gen_editor.py config.json.example README.md requirements.txt ~/.claude/skills/video-gen/

# Install dependencies
cd ~/.claude/skills/video-gen && pip install -r requirements.txt

# Configure API keys
cp config.json.example config.json
# Edit config.json to add your API keys
```

## Usage

```
/video-gen <material directory>
```

### Examples

```bash
# Complete creation workflow
/video-gen ~/Videos/travel materials/

# Continue previous project
/video-gen ~/video-gen-projects/trip_20260310/
```

## Tool Calls

### video_gen_tools.py

```bash
# Video generation (Kling backend, default)
python video_gen_tools.py video --prompt "<description>" --duration 5 --output video.mp4
python video_gen_tools.py video --image <first frame image> --prompt "<description>" --output video.mp4

# Video generation (Kling Omni backend - reference image mode)
python video_gen_tools.py video --backend kling-omni --prompt "<<<image_1>>> in the scene" --image-list <reference_images> --output video.mp4

# Video generation (Vidu backend - fallback/rapid prototyping）
python video_gen_tools.py video --backend vidu --image <image> --prompt "<description>" --duration 5 --output video.mp4

# Kling multi-shot mode
python video_gen_tools.py video --prompt "<story description>" --multi-shot --shot-type intelligence --duration 10
python video_gen_tools.py video --prompt "<overall description>" --multi-shot --shot-type customize --multi-prompt '[{"index":1,"prompt":"shot 1","duration":"3"}]' --duration 5

# Kling first/last frame control
python video_gen_tools.py video --image <first frame image> --tail-image <last frame image> --prompt "<action description>" --duration 5

# Music generation
python video_gen_tools.py music --prompt "<description>" --style "Lo-fi" --output music.mp3

# TTS
python video_gen_tools.py tts --text "<text>" --voice female_narrator --output audio.mp3

# Image generation
python video_gen_tools.py image --prompt "<description>" --style cinematic --output image.png
```

### Video Generation Backend Comparison

| Backend | Model | Duration | Features |
|------|------|------|------|
| **Kling Omni** | kling-3.0-omni | 3-15s | multi-reference images(reference2video)、best character consistency、audio-video sync output |
| **Kling** | kling-3.0 | 3-15s | precise first frame control(img2video)、good visual quality |
| **Vidu**（fallback） | vidu-q3-pro | 5-10s | stable, fast, first frame control |

**Key Differences**:
- **Kling Omni** supports `reference2video`（multi-reference images），but **does not support `img2video`（first frame control）**
- **Kling / Vidu** supports `img2video`（first frame control），but does notsupportsmulti-reference images

**Selection Recommendations**:
- Fiction films/short dramas, MV → **Kling Omni** (character consistency)
- Vlog/documentary style, commercials (with real materials) → **Kling or Vidu** (first frame control)

### video_gen_editor.py

```bash
# Concatenate
python video_gen_editor.py concat --inputs v1.mp4 v2.mp4 --output out.mp4

# Subtitle
python video_gen_editor.py subtitle --video video.mp4 --srt subs.srt --output out.mp4

# Audio mixing
python video_gen_editor.py mix --video video.mp4 --bgm music.mp3 --output out.mp4

# Transition
python video_gen_editor.py transition --inputs v1.mp4 v2.mp4 --type fade --output out.mp4

# Color grading
python video_gen_editor.py color --video video.mp4 --preset warm --output out.mp4

# Speed change
python video_gen_editor.py speed --video video.mp4 --rate 1.5 --output out.mp4
```

## Environment Variables

```bash
# Yunwu API - for Vidu video generation + Gemini Image generation
export YUNWU_API_KEY="your-api-key"

# Kling API - for Kling video generation
export KLING_ACCESS_KEY="your-access-key"
export KLING_SECRET_KEY="your-secret-key"

# Suno Music generation
export SUNO_API_KEY="your-api-key"

# Volcengine TTS
export VOLCENGINE_TTS_APP_ID="your-app-id"
export VOLCENGINE_TTS_ACCESS_TOKEN="your-token"
```

**Note**:
- Gemini image generation uses Yunwu API
- Kling/Kling-Omni video generation can use Yunwu API via `--provider yunwu` (as fallback for official API)
- Uses the same YUNWU_API_KEY

## Workflow

```
Material Analysis → Creative Generation → Storyboard Design → Content Generation → Editing Output
```

## Output Directory Structure

```
~/video-gen-projects/{project_name}_{timestamp}/
├── state.json              # Project state
├── materials/              # Original materials
├── analysis/               # Analysis results
├── creative/               # Creative plan
├── storyboard/             # Storyboard script
├── generated/              # Generated content
│   ├── videos/
│   └── music/
└── output/                 # Final video
```

## Dependencies

- FFmpeg 6.0+ (video processing)
- Python 3.9+ (tool execution)
- httpx (HTTP client)

## Changelog

### v1.4.6 (2026-04-02)
🔧 **API Field Name Fixes**

#### Bug Fixes
- 🐛 **FalKlingClient field name corrections** — Use correct fal.ai official field names
  - `image_url` → `start_image_url` (first frame control)
  - `tail_image_url` → `end_image_url` (last frame control)
- 🐛 **YunwuKlingOmniClient parameter corrections**
  - `audio` boolean → `sound: "on"/"off"` string
  - `_file_to_base64()` returns plain base64 instead of data URI format

#### Tested
- ✅ Text-to-video (prompt only)
- ✅ Image-to-video (start_image_url, character preserved correctly)
- ✅ Multi-reference video (image_urls + @Image1/@Image2, with audio)

### v1.4.5 (2026-04-02)
🔧 **API Field Name Fixes (Initial)**

- Same fixes as v1.4.6, initial release

### v1.4.4 (2026-04-02)
📚 **Yunwu Provider Documentation Enhancement**

#### Documentation Updates
- 📝 `api-reference.md` — YUNWU_API_KEY scope expanded to support Kling/Kling-Omni
- 📝 `backend-guide.md` — Added Provider Selection Priority section
- 📝 `README.md` — Added Kling can use Yunwu as official API fallback
- 📝 `SKILL.md` — Added Provider Selection section, explaining how to bypass rate limits

### v1.4.3 (2026-04-02)
🔌 **Yunwu Kling Provider supports**

#### New Features
- YunwuKlingClient — Added yunwu kling-v3 client，supports text2video、img2video、multi_shot、first/last frame control, audio
- YunwuKlingOmniClient — Added yunwu kling-v3-omni client，supports omni-video、image_list multi-reference images、multi_shot、audio
- --provider parameter — Added provider selection（official/yunwu/fal），supports switching different providers for same backend
- Provider auto-selection — Auto-select by priority when unspecified：official > yunwu > fal

#### Architecture Optimization
- 🔄 **Backend/Provider separation** — backend selection (vidu/kling/kling-omni), provider selection (official/yunwu/fal)
- 📝 **Function support matrix** — Clarified each provider's function support (multi_shot, first/last frame, audio, etc.)

#### API Differences Handling
- 🔧 **Yunwu kling-v3 uses `model` parameter**（Official API uses `model_name`）
- 🔧 **Yunwu kling-v3-omni uses `model_name` parameter**（Same as official API）
- 🔧 **Video URL parsing path** — `data.task_result.videos[0].url`（not `task_info`）

#### File Changes
- 📝 `video_gen_tools.py` — Added YunwuKlingClient, YunwuKlingOmniClient, modified cmd_video function

### v1.4.2 (2026-04-01)
Audio Mixing Fix and Standardization

#### Bug Fixes
- FFmpeg amix normalize=0 — Disable auto-normalization, preserve original volume ratios, fix narration being suppressed

#### New Features
- Audio mixing rules documentation — Added audio mixing rules section to SKILL.md Phase 5
  - Volume recommendations: video ambient 0.8, narration 1.5-2.0, BGM 0.1-0.15
  - Video type adaptation: MV → 0.5-0.7, Vlog → 0.1-0.15, Cinematic → 0.2-0.3

#### File Changes
- 📝 `video_gen_editor.py` — Added normalize=0 to mix_audio() function (line 470)
- 📝 `SKILL.md` — Phase 5 added audio mixing rules section

### v1.4.1 (2026-03-31)
Narration Segment Planning Feature

#### New Features
- ✨ **Phase 2 narration requirement judgment** — Recommend whether narration is needed based on video type（documentary/Vlog usually needs, cinematic/fiction usually doesn't）
- ✨ **Phase 3 synchronous narration design** — Plan `narration_segments` synchronously when generating storyboard, segment by shot timing
- ✨ **Phase 4 narration generation** — Added TTS narration generation step after video/music generation (Volcengine)
- ✨ **Phase 5 narration insertion** — Place narration audio at correct position based on `overall_time_range`

#### Documentation Updates
- 📝 `storyboard-spec.md` — Added `narration_config` and `narration_segments` field specifications
- 📝 `prompt-guide.md` — Added TTS narration generation process and parameter descriptions

### v1.4.0 (2026-03-30)
Video Generation Best Practices Refactoring

#### Core Architecture Changes
- Project type-driven decisions — Automatically determine project type based on user intent（fiction films/short dramas, Vlog/documentary, commercials/promos, MV shorts），No manual selection needed
- Disable text2video for fiction films — All fictional content must first generate storyboard images, then use reference2video or img2video
- Unified model within same project — Do not mix models within project, use one consistently after selection

#### Models and Generation Paths
- Updated model names — Kling-3.0-Omni, Kling-3.0, Vidu Q3 Pro
- Clarified model capability boundaries — Kling-3.0-Omni supports reference2video but **does not support img2video（first frame control）**
- Decision matrix optimization — Fiction films prefer Omni (character consistency), Vlog/commercials use Kling/Vidu (first frame control)

#### Bug Fixes
- 🐛 **Omni reference format fix** — `image_1` → `<<<image_1>>>`，Compliant with official documentation

#### Documentation Updates
- 📝 `SKILL.md` — Backend selection overview, Phase 3 decision tree rewritten
- 📝 `storyboard-spec.md` — Reference Tag format, T2V/I2V/Ref2V selection rules rewritten
- 📝 `prompt-guide.md` — Omni mode reference format fixed

### v1.3.10 (2026-03-23)
🎵 **Music Generation Parameter Standardization**

#### Fix
- 🐛 **music command style parameter must be provided** — Removed Lo-fi Chill default value to avoid style mismatch
  - Must read from creative.json via `--creative`
  - Or manually pass `--prompt` and `--style` parameters

### v1.3.9 (2026-03-23)
🎬 **Audio-Video Sync Fix**

#### Fix
- 🐛 **Video concatenation audio-video sync issue** — Silent clips caused audio desync in subsequent videos
  - Added `has_audio_track()` to detect if video has audio track
  - `normalize_videos()` Automatically add silent track to clips without audio
  - `concat_videos()` Changed to concat filter to ensure audio-video sync

#### Improvements
- 🔄 `music` Command `--prompt` Changed to optional, can read from creative.json
- 📝 SKILL.md: Phase 5 Added audio protection instructions

### v1.3.8 (2026-03-23)
🔧 **Parameter Passing Standardization**

#### Fix
- 🐛 **Hardcoded default value issue** — CLI parameters should preferentially read from storyboard.json
  - `video_gen_editor.py`: Added `--storyboard` parameter to concat/image commands
  - `video_gen_tools.py`: Added `--storyboard` to video/image, `--creative` to music
  - Unified KlingClient/KlingOmniClient default aspect_ratio to `"9:16"`

#### Improvements
- 🔄 Suno logs show both prompt and style to avoid misleading users

### v1.3.7 (2026-03-20)
🔧 **Execution Phase Fix & Image Size Optimization**

#### Fix
- 🐛 **Phase 4 aspect_ratio passing** — Execution phase must read aspect ratio from storyboard.json and pass to CLI
- 🐛 Fixed generation failure caused by inconsistent image sizes

#### New Features
- ✨ **Image size automatic validation and adjustment** — Added `validate_and_resize_image()` function
  - Min dimension < 720px auto upscale to 1280px
  - Max dimension > 2048px auto downscale to 2048px
  - Auto-process before Kling/KlingOmni calls

### v1.3.6 (2026-03-20)
📝 **Documentation Fix**

#### Fix
- 🐛 Fixed conflicts and ambiguous descriptions in storyboard-spec.md
- 📝 Clarified three-layer structure field definitions and usage scenarios

### v1.3.5 (2026-03-19)
🎬 **Character Consistency Workflow Enhancement**

#### New Features
- ✨ **Phase 1 character registration enhancement**
  - Added `personas.json` structure, supports `reference_image` as null
  - Only process uploaded reference images, pending ones wait for Phase 2

- ✨ **Phase 2 character reference image collection**
  - Added question 6: character reference image source selection
  - Supports three methods: AI generation / User upload / Pure text generation
  - Auto-call `video_gen_tools.py image` to generate standard character reference images

- ✨ **Phase 3 auto backend selection**
  - With reference images + multi-shot characters → `kling-omni` (best character consistency)
  - With reference images + single-shot character → `kling` (precise first frame control)
  - No reference images + characters → `kling` text2video (user warned)
  - Pure scenes without characters → `kling` text2video

#### PersonaManager Enhancement
- ✨ `list_personas_without_reference()` — List characters without reference images
- ✨ `update_reference_image()` — Update character reference image path
- ✨ `export_for_storyboard()` — Export as storyboard compatible format
- ✨ `get_character_image_mapping()` — Generate character_image_mapping

#### SKILL.md Workflow Optimization
- 📝 Added 'must read before storyboard generation' step
- 📝 Added 'Step 1: Sync character info to storyboard'
- 📝 Enhanced output file descriptions and JSON structure examples

### v1.3.4 (2026-03-19)
🎬 **Kling V3-Omni Two-Stage Workflow Standardization**

#### Documentation Updates
- ✨ **Added V3-Omni three-layer structure specification** — storyboard + frame_generation + video_generation
  - `storyboard-spec.md`：Added three-layer schema definitions（storyboard/frame/video）
  - `prompt-guide.md`：Added Image Prompt and Video Prompt writing specifications
  - `backend-guide.md`：Added Path C (V3-Omni recommended path), updated decision tree and path comparison

- 📝 **Image Prompt Specification**
  - Structure: Cinematic realistic start frame → Character refs → Scene → Lighting → Camera → Style
  - Must include character references（image_1, image_2...）、Aspect ratio, scene, lighting, camera parameters

- 📝 **Video Prompt Specification**
  - Structure: Referencing frame composition → Motion segments → Dialogue exchange → Camera → Sound
  - Time segment format（"0-2s", "2-5s"）、Dialogue sync markers, sound design descriptions

#### Architecture Adjustment
- 🗑️ Removed incorrectly created vico-templates Python code（Should be documentation specs not code templates）

### v1.3.3 (2026-03-18)
📐 **SKILL.md Architecture Refactoring & Default Backend Switch**

#### Architecture Refactoring（Anthropic Skill specification optimization）
- ✨ **Progressive disclosure architecture** — SKILL.md compressed from 1401 lines to ~290 lines(-80%），Compliant with Anthropic recommended's 500 line limit
- ✨ **Split into 4 sub-files** — Storyboard spec, prompt guide, backend selection, API reference, load on demand
- ✨ **Optimized description** — Added Kling Omni keywords and trigger condition descriptions
- ✨ **Added workflow checklist** — Anthropic recommended checklist pattern
- ✨ **Added config.json.example** — Safe configuration template（without real keys）
- 🔄 Streamlined redundant content: removed repeated explanations, legacy formats, long JSON examples

#### Default Backend Switch
- 🔄 **Default backend changed from Vidu to Kling** — CLI `--backend` default value `vidu` → `kling`
- ✨ **Enhanced auto-selection logic** — Force backend switch based on functional requirements（`--image-list` → omni，`--tail-image` → kling），No longer limited to default backend triggering

### v1.3.2 (2026-03-18)
🎬 **Kling Omni Backend Integration**

#### New Features
- ✨ **Kling Omni API supports**
  - Added `--backend kling-omni` backend option
  - `--image-list` multi-reference images mode, use `<<<image_1>>>` reference in prompt
  - Supports multi-reference images + multi_shot combination
- ✨ **Auto backend selection**
  - Providing `--image-list` auto uses kling-omni
  - Providing `--tail-image` auto uses kling
- ✨ **Three-backend selection strategy** — Core trade-off: character consistency vs scene precision
- ✨ **Two character reference image paths** — Omni path（recommended）vs Kling+Gemini first frame path

#### CLI Updates
- 🔧 Added `--image-list` parameter（Kling Omni multi-reference images）
- 🔧 Added `--backend kling-omni` option

### v1.3.1 (2026-03-17)
📋 **Storyboard Structure Optimization & Workflow Enhancement**

#### Storyboard Structure Upgrade
- ✨ **Scene-Shot two-layer structure**
  - Changed from single `shots` array to `scenes` -> `shots` two-layer structure
  - Added scene fields：`scene_id`、`scene_name`、`narrative_goal`、`spatial_setting`、`time_state`、`visual_style`
  - Scene duration auto-calculation（sum of subordinate shot durations）

- ✨ **shot_id naming standardization**
  - New format: `scene{scene_num}_shot{shot_num}`
  - Single shot example：`scene1_shot1`、`scene1_shot2`
  - Multi-shot mode: `scene1_shot2to4_multi` (with `_multi` suffix)

#### Field Optimization
- 🔄 `vidu_prompt` → `video_prompt`（Generic name）
- ✨ Added fields：
  - `multi_shot`：Whether multi-shot mode
  - `generation_backend`：Backend selection（kling/vidu）
  - `frame_strategy`：First/last frame strategy（none/first_frame_only/first_and_last_frame）
  - `multi_shot_config`：Kling multi-shot configuration
  - `reference_personas`：Referenced character reference images

#### Workflow Enhancement
- 📝 **T2V/I2V selection rules**：Decision tree + rule table
- First/last frame generation strategy: supports `image_tail` parameter
- 📝 **Dialogue integration rules**：Directly include dialogue info in video_prompt
- 📝 **Review check mechanism**：Automated check items（Structure integrity, shot rules, prompt specs, technical selection）

#### Character Reference Image Workflow
- 📝 Enhanced character reference image usage workflow：
  - Core principle: reference images cannot directly be first frames
  - Complete workflow：`Character reference images → Gemini generate storyboard images → img2video`
  - Single/dual shot processing solutions
  - Storyboard JSON annotation `reference_personas` and `notes`

#### CLI Updates
- 🔧 Added `--multi-shot` parameter to enable multi-shot mode
- 🔧 Added `--shot-type` parameter to select shot type（intelligence/customize）
- 🔧 Added `--multi-prompt` parameter for custom shot list（JSON format）
- 🔧 Added `--tail-image` parameter for first/last frame control

### v1.3.0 (2026-03-16)
🎬 **Kling Video Generation API Integration**

#### New Features
- ✨ **Kling API supports**
  - Added KlingClient class, supports Kling v3 model
  - JWT Token authentication（iss, iat, exp, nbf）
  - text-to-video (text2video) andimage-to-video (image2video)
  - Supports 3-15s duration range
  - Supports std/pro generation modes
  - supportsaudio-video sync output (sound: on/off)

- ✨ **Multi-shot mode**
  - Supports generating video with multiple shots in one request
  - intelligence mode（AI auto storyboard）
  - customize mode（custom storyboard）

#### CLI Updates
- 🔧 Added `--backend` parameter for video generation backend（vidu/kling）
- 🔧 Added `--mode` parameter for generation mode（std/pro）

#### Documentation Updates
- 📝 Added Kling usage instructions and multi-shot storyboard design docs to SKILL.md
- 📝 README Updated feature list, tool call examples, environment variable config

### v1.2.0 (2026-03-16)
🎯 **Storyboard Workflow Standardization & User Experience Optimization**

#### Workflow Standards
- ✅ **Video aspect ratio full workflow constraints**
  - Both text-to-image and image-to-video prompts must include aspect ratio info
  - 9:16/16:9/1:1 Different ratios have clear description standards
  - Auto check aspect ratio consistency before generation

- ✅ **Strict execution of storyboard planned generation mode**
  - `generation_mode` must be explicitly specified in storyboard，Must not change during execution phase
  - img2video/text2video/existing have strict execution rules
  - Stop execution and report error when rules violated

- ✅ **Clear distinction of dialogue generation methods**
  - sync sound（video model generated）vs Clear distinction between post-production TTS narration
  - Sync sound explicitly described in vidu_prompt: character, dialogue, emotion, speech rate, voice quality
  - TTS only for scene narration, background intro, not character dialogue

- ✅ **Prompt Detail Level and Language Standards**
  - Video generation prompts must be written in Chinese
  - Must include camera movement, motion rhythm, stability, aspect ratio protection, dialogue info
  - Image generation prompts must include 5 elements: scene, subject, lighting, style, aspect ratio

- ✅ **Material Consistency Enforcement**
  - Cross-shot characters must have detailed identity and appearance descriptions in prompt
  - Establish material list for key props，Each shot includes complete description for consistency
  - Provided character/prop description prompt templates and examples

- ✅ **Force User Storyboard Confirmation**
  - Storyboard must get explicit user confirmation before execution
  - Detailed display of each shot's generation mode, prompt, duration, transition, etc.
  - state.json added `storyboard_confirmed` and `confirmation_details` fields

#### Documentation Optimization
- 📝 README Added 'Usage Recommendations' section，Explains recommended models, guiding techniques, project positioning

### v1.1.0 (2026-03-12)
🔧 **Stability Enhancement & Character Management**

#### New Features
- ✨ **Video Parameter Auto Validation and Normalization**
  - Auto detect all video resolution, codec, frame rate before concatenation
  - Auto normalize to unified format when parameters inconsistent（1080x1920 / H.264 / 24fps）
  - Fixed frame freeze caused by inconsistent video resolution from different APIs

- ✨ **Character Role Manager (PersonaManager)**
  - Manage project character reference images, maintain cross-scene consistency
  - Auto generate Vidu/Gemini compatible prompts
  - Supports different strategies for single/dual shots

#### Documentation Optimization
- 📝 SKILL.md Added conditional workflows：
  - Character identification workflow（Only triggered when material is portrait image）
  - Character reference image strategy（Single/dual shot processing solutions）
  - Video parameter validation workflow (must execute before concatenation)
- 📝 Added key experience summary：Gemini multi-reference notes, video generation parameter differences

#### Fix
- 🐛 Fix text2video (720x1280) and image2video (716x1284) Resolution inconsistency caused concatenation issue

### v1.0.0 (2026-03-10)
🎉 **Complete Initial Release**

#### Core Features
- ✨ **AI Director Workflow**: Complete video creation workflow - Material analysis → Creative confirmation → Storyboard design → Generation → Editing output
- ✨ **Multimodal AI Generation**：
  - Vidu Q3 Pro image-to-video/text-to-video（720p/1080p，up to 10s）
  - Suno V3.5/V4.5 Music generation（Supports custom style, duration, instrumental）
  - Volcengine TTS voice synthesis（various voices, emotions, speech rates）
  - Gemini Image generation（various styles, aspect ratios）
- ✨ **Professional Editing Tools**：
  - Video concatenation (Auto adjust resolution to 9:16/16:9/1:1)
  - Transition effects (16 types: fade, dissolve, wipe, slide, etc.)
  - Audio mixing（Auto loop BGM to match video duration, volume adjustment）
  - Color grading presets (warm, cool, vibrant, cinematic, vintage, etc.)
  - Speed change、Subtitlesupports
- ✨ **Auto Project Management**：
  - Auto create project directory structure
  - State tracking and resume from breakpoint
  - All intermediate artifacts auto saved
- ✨ **Interactive Creation**：
  - Auto material recognition and analysis
  - Question card style creative confirmation
  - Storyboard preview and adjustment

#### Technical Implementation
- ✨ Async API calls via httpx, supports concurrent generation
- ✨ FFmpeg underlying video processing, excellent performance
- ✨ Auto environment check and dependency management
- ✨ Comprehensive error handling and retry mechanism
- 🐛 Fixed Suno API callbackUrl missing, full functionality available

## 📄 License

MIT
