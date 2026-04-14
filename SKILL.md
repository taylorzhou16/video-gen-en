---
name: video-gen-en
description: AI video editing tool. Analyze materials, generate creative ideas, design storyboards, execute editing. Supports Vidu/Kling/Kling Omni video generation, Suno music generation, TTS voiceover, FFmpeg editing. Triggers when users request to make videos, edit videos, generate videos, create short films, or provide material directories for producing works.
argument-hint: <material_directory_or_video_file>
---

# video-gen User Guide

**Role**: Director Agent — Understand creative intent, coordinate all resources, deliver video works.

**Language Requirement**: Respond in the same language the user uses.

---

## Recommended Configuration

**Recommended to use multimodal models** (such as Claude Opus/Sonnet/Kimi-K2.5) for the best experience.

Non-multimodal models will automatically call vision models for image analysis. Configure `VISION_BASE_URL`, `VISION_MODEL`, `VISION_API_KEY` in `config.json`.

### Provider Selection

**Different backends support different providers**:

| Backend | Supported Providers | Notes |
|---------|-------------------|-------|
| `seedance` | **fal > piapi** | fal preferred, piapi as fallback |
| `kling-omni` | official, fal | Switch when official API encounters limits |
| `kling` | official, fal | Switch when official API encounters limits |
| `veo3` | **compass only** | Veo3 has only one provider: compass |

When Kling official API encounters concurrency limits (429), you can use `--provider fal`:

```bash
# fal.ai proxy
python video_gen_tools.py video --provider fal --backend kling-omni --image-list ref.jpg ...
```

**Note**: Seedance auto-selects provider (fal preferred), Veo3 does not need `--provider` specified.

**Provider auto-selection priority**: Official API → fal

---

## Core Philosophy

- **Tool Files**: video_gen_tools.py (API calls) and video_gen_editor.py (FFmpeg editing) are command-line tools
- **Flexible Planning, Robust Execution**: Planning phase produces structured artifacts, execution phase is driven by storyboard plan
- **Graceful Degradation**: Actively seek user help when encountering problems, rather than stalling the process

### Backend Selection Overview

**Scenario-driven Selection**:

| Scenario | Real Person Materials | Preferred Backend | Fallback Backend | Reason |
|----------|----------------------|------------------|------------------|--------|
| **Fiction/Short Drama** | None (Anime) | **Seedance** | Kling-Omni | Smart shot switching + multiple reference images |
| **Fiction/Short Drama** | **Has Real Person** | **Kling-Omni** | — | Real person materials disable Seedance |
| **Commercial (no real materials)** | None | **Seedance** | Kling-Omni | Long shots + smart shot switching |
| **Commercial (with real materials)** | Has | Kling-3.0 | — | Precise first-frame control, real materials |
| **MV Short Film** | None (Anime) | **Seedance** | Kling-Omni | Long shots + music-driven |
| **MV Short Film** | **Has Real Person** | **Kling-Omni** | — | Real person materials disable Seedance |
| **Vlog/Realistic** | Has | Kling-3.0 | Veo3 | Precise first-frame control, not using Seedance |

**Veo3 as Global Fallback Video Generation Model**: Unless user explicitly requests Veo3, do not proactively call Veo3. Veo3 has fixed duration (4/6/8s), max resolution 720p, only use as final backup when all other backends fail.

**visual_style only affects how user photos are processed (if user photos exist)**:

| visual_style | User Photo Processing | Notes |
|--------------|----------------------|-------|
| `realistic` (photorealistic) | **Seedance requires conversion** | User's real photos need to generate three-view images first, then use as reference |
| `anime` (animation/2D) | Use directly | Can be used directly as reference image |
| `mixed` | Process by scene | Real-person scenes need conversion, anime scenes can use directly |

**Seedance User Real Photo Conversion Process**:
```
User provides real photo →
  ├── Call Gemini to generate three-view images (maintaining facial features, body shape, figure details) →
  │   - Front view
  │   - Side view
  │   - Full body proportion
  ├── Select best view as character reference image →
  └── Register to personas.json
```

**Key Rules**:
- **Seedance preferred for fictional content** (smart shot switching is core advantage)
- **Kling-Omni as fallback when Seedance fails**
- **Use Kling/Vidu when having real materials** (precise first-frame control)
- **Use the same model for the same project**, no mixing (except mixed mode)

Detailed backend comparison and degradation strategy: See [reference/backend-guide.md](reference/backend-guide.md)

---

## Quick Start Process

```
Provider Selection → Environment Check → Material Collection → Creative Confirmation → Storyboard Design → Execute Generation → Edit Output
    Interactive         5 seconds           Interactive         Interactive          Interactive        Automatic        Automatic
```

### Workflow Progress Checklist

```
Task Progress:
- [ ] Phase 0: Provider Configuration + Environment Check
- [ ] Phase 1: Material Collection (Scan + Visual Analysis + Character Recognition)
- [ ] Phase 2: Creative Confirmation (Question Card Interaction + Character Reference Image Collection)
- [ ] Phase 3: Storyboard Design (Generate storyboard.json + Auto Backend Selection + User Confirmation)
- [ ] Phase 4: Execute Generation (API Calls + Progress Tracking)
- [ ] Phase 5: Edit Output (Concatenation + Transitions + Color Grading + Music)
```

---

## Phase 0: Provider Configuration + Environment Check

### Step 1: Select Video Generation Provider

**Must complete API configuration before starting any work. Do not proceed to Phase 1 without an available API key.**

First run setup to view current configuration status:

```bash
python video_gen_tools.py setup
```

Output includes all available providers and their key configuration status. **If no video provider key is configured**, must guide user to select and configure:

**Present option card to user**:

> Please select video generation API (can change later):
>
> **1. Seedance (Recommended)** — From ByteDance, smart shot switching + multiple reference images, suitable for fiction/short drama/MV
>    - Requires: FAL_API_KEY (preferred) or SEEDANCE_API_KEY (piapi fallback)
>
> **2. Kling Official** — From Kuaishou, precise first-frame control, suitable for realistic/commercial videos
>    - Requires: Kling Access Key + Secret Key (from klingai.kuaishou.com)
>
> **3. Kling via fal.ai** — Bypass official concurrency limits
>    - Requires: fal.ai API Key (from fal.ai)
> **4. Veo3 via Compass** — Google Veo3, global fallback model (4/6/8s)
>    - Requires: Compass API Key (from compass.llm.shopee.io)
>    - Note: Only use when all other backends fail, or when user explicitly requests

After user selects, request corresponding API key, then save:

```bash
# Example: User selects Seedance
python video_gen_tools.py setup --set-key SEEDANCE_API_KEY=sk-xxx

# Example: User selects Kling Official
python video_gen_tools.py setup --set-key KLING_ACCESS_KEY=xxx KLING_SECRET_KEY=xxx

# Example: User selects fal
python video_gen_tools.py setup --set-key FAL_API_KEY=xxx

# Example: User selects Veo3
python video_gen_tools.py setup --set-key COMPASS_API_KEY=xxx
```

**Optional Services** (ask after saving key):
- Music generation (Suno): `SUNO_API_KEY`

User can skip optional services.

### Step 2: Environment Check

```bash
python video_gen_tools.py check
```

- Basic dependencies (FFmpeg/Python/httpx) not passing → Stop and inform installation method
- **At least one video provider's API key configured** → Continue
- **No video API key** → Return to Step 1, do not continue

---

## Phase 1: Material Collection

### Material Source Identification

- **Directory path** → Scan image/video files in directory
- **Video file** → Analyze that video directly
- **No materials** → Pure creative mode

### Visual Analysis Process (Three-level fallback)

**Step 1**: Use Read tool to read images. Record scene description, subject content, emotional tone, color style.

**Step 2**: Read fails → Call built-in VisionClient:

```python
from video_gen_tools import VisionClient
client = VisionClient()
results = await client.analyze_batch(image_paths, "Analyze these materials: scene, subject, color, atmosphere")
```

**Step 3**: VisionClient also fails → Actively ask user to describe each material's content.

### Character Recognition (Conditional)

**Triggers only when user provides character portrait images** (ask user if uncertain).

Execution steps:
1. Read image content, identify all characters
2. Ask user to confirm each character's identity
3. Register separately using PersonaManager:

```python
from video_gen_tools import PersonaManager
manager = PersonaManager(project_dir)

# Case A: User provided reference image
manager.register("Xiaomei", "female", "path/to/ref.jpg", "long hair, oval face")

# Case B: User did not provide reference image (Phase 2 will supplement)
manager.register("SunWukong", "male", None, "monkey face, golden headband, tiger skin skirt")
```

**Phase 1 Key Principles**:
- Only process reference images user **has uploaded**
- For characters without uploaded images, set reference_image to `None`, supplemented by Phase 2
- Do not ask about reference images not uploaded at this stage

### Phase 1 Output

Create project directory `~/video-gen-projects/{project_name}_{timestamp}/`, produce:
- `state.json` — Project status
- `analysis/analysis.json` — Material analysis results
- `personas.json` — Character registry (reference_image may be None)

**personas.json Structure**:
```json
{
  "personas": [
    {
      "name": "SunWukong",
      "gender": "male",
      "reference_image": null,  // null when not uploaded in Phase 1
      "features": "monkey face, golden fur, fiery eyes, wearing golden chainmail"
    },
    {
      "name": "Xiaomei",
      "gender": "female",
      "reference_image": "/path/to/ref.jpg",  // User uploaded reference image
      "features": "long hair, oval face"
    }
  ]
}
```

---

## Phase 2: Creative Confirmation

**Interact with user using question cards**, collect key information.

### Question Card Design

**Question 1: Video Style**
- Options: Cinematic | Vlog Style | Commercial | Documentary | Art/Experimental
- Note: Determines overall tone of color grading, transitions, music

**Question 2: Target Duration**
- Options: 15 seconds (short video) | 30 seconds (standard) | 60 seconds (long video) | Custom
- Note: Affects number of shots and pacing

**Question 3: Aspect Ratio**
- Options: 9:16 (Douyin/Xiaohongshu) | 16:9 (Bilibili/YouTube) | 1:1 (Instagram)
- Note: Choose based on publishing platform

**Question 4: Music Needs**
- Options: AI-generated BGM | No music needed | I already have music
- Note: Whether to use Suno for background music generation

**Question 5: Voiceover/Narration**

**First determine if video type is suitable for voiceover**:

| Video Style | Voiceover Need | Note |
|------------|----------------|------|
| Cinematic/Fiction | Usually not needed | Character dialogue is primary, voiceover breaks immersion |
| Documentary | Usually needed | Scene explanation, background introduction |
| Vlog Style | Possibly needed | Travel commentary, mood recording |
| Commercial | Possibly needed | Product introduction, brand story |
| Art/Experimental | Case by case | Concept expression may need voiceover |

**When uncertain, ask user**:

> Does this video need voiceover/narration?
> - **No voiceover needed** (character dialogue is primary, or pure visual expression)
> - **Need AI-generated voiceover** (I will design script based on storyboard)
> - **I already have voiceover script** (User provides complete script)

**Distinguish two audio generation methods**:

**A. Character Dialogue (Sync Sound)**
- Generated directly by video generation model
- Need to explicitly describe in shot's video_prompt: character, dialogue, emotion, speech rate, voice quality
- Set `audio: true` during video generation

**B. Voiceover/Narration (Post-production)**
- Generated by TTS in post-production, mixed in during editing phase
- Used for scene explanation, background introduction, emotional enhancement
- Phase 3 will design voiceover script and timing based on storyboard

**Important Principle**: For shots that can capture sync sound, never use post-production TTS dubbing!

### Question 6: Character Art Style Selection

**Trigger Condition**: Fiction/short drama, MV short film type projects (Vlog/realistic defaults to realistic style).

> **Please select character art style**
> - **A. Photorealistic Style** — AI-generated character reference images adopt real actor style
> - **B. Anime/2D Style** — AI-generated character reference images adopt anime style
> - **C. Mixed Style** — Process by scene, real-person scenes and anime scenes have different styles

**After selection, write to `creative.json`**:
```json
{
  "visual_style": "realistic"  // realistic / anime / mixed
}
```

**Explanation**:

| visual_style | AI Reference Image Style | User Real Photo Processing (if any) |
|--------------|-------------------------|-----------------------------------|
| `realistic` | Real actor style | Seedance needs to generate three-view conversion first, Kling-Omni can use directly |
| `anime` | Anime/2D style | Can use directly as reference image |
| `mixed` | Decide by scene | Real-person scene photos need conversion, anime scenes can use directly |

**Key Understanding**:
- **Pure creative mode (no user photos)**: visual_style only determines AI-generated reference image style, **does not affect backend selection**
- **User photo mode**: visual_style determines how user photos are processed (whether three-view conversion is needed)
- **Backend selection basis**: Project requirements (smart shot switching vs character consistency vs first-frame control), not visual_style

### Question 7: Character Reference Image Collection

**Trigger Condition**: Check personas.json, triggers when character with null/empty `reference_image` exists.

**Check Logic**:
```python
manager = PersonaManager(project_dir)
for persona_id in manager.list_personas_without_reference():
    # Ask user about this character's reference image source
    ask_user_for_reference(persona_id)
```

**Ask Content** (for each character without reference image):

> **Character "{name}" needs a reference image**
>
> Please select reference image source:
> - **A. AI-generated character image** (Recommended, automatically generate standard reference image)
> - **B. Upload reference image** (User provides character photo)
> - **C. Accept text-only generation** (Character appearance may be inconsistent across different shots)

**Post-selection Processing**:

**A. AI Generation** (determine style based on visual_style):
```python
# Read visual_style
visual_style = creative.get("visual_style", "realistic")

# Generate reference image with corresponding style based on art style
if visual_style == "anime":
    style_suffix = "anime style, 2D animation, vibrant colors"
else:  # realistic
    style_suffix = "photorealistic, cinematic, realistic"

python video_gen_tools.py image \
  --prompt "{character appearance description}, {style_suffix}, front half-body shot, solid background, high-quality portrait" \
  --output materials/personas/{name}_ref.png

# Update personas.json
manager.update_reference_image(persona_id, "materials/personas/{name}_ref.png")
```

**B. Upload Reference Image**:
- Ask user to upload image
- Save to `materials/personas/{name}_ref.{ext}`
- Update personas.json

**C. Text Only**:
- Record warning to `creative/decision_log`
- Subsequent Phase 3 will **force storyboard image generation**, then use img2video or reference2video

**Key Rules**:
- **Must generate reference image**: When character needs to appear in **multiple shots**
- **Can use text2video**: Single scene appearance, pure scenery, user explicitly accepts appearance variation
- **When AI generates reference images must follow visual_style**: anime style or realistic style

---

### Phase 2 End Checkpoint: Real Person Material Detection

**Timing**: After all creative questions (Questions 1-7) are completed, before Phase 2 output

**Detection Logic**:

**Core Rules (No need to check image content)**:

| visual_style | Has Character Reference Image | Seedance |
|--------------|------------------------------|----------|
| **realistic** | Yes (any source: user uploaded or AI generated) | **Disabled** |
| realistic | No | Available |
| **anime** | Yes | Available |
| anime | No | Available |

**Reasoning Chain**:
```
visual_style = realistic?
    ↓ Yes
Has character reference image (user uploaded or Phase 2 AI generated)?
    ↓ Yes
→ Disable Seedance, use Kling-Omni
```

**Key Understanding**:
- **Adopt conservative strategy**: visual_style = realistic + has character reference image → Disable Seedance
- **Avoid moderation uncertainty**: Seedance moderation behavior is unstable (actual tests show real photos may pass, but for safety uniformly disable)
- No need to check image content afterward, only need prior reasoning of visual_style + whether character reference image exists

**Write detection result to creative.json**:

```json
{
  "visual_style": "realistic",
  "backend_selection": {
    "seedance_disabled": true,
    "preferred_backend": "kling-omni",
    "reason": "Real person reference images trigger Seedance content_policy_violation"
  }
}
```

**Inform user**:
> ⚠️ Detected real person style materials. Seedance backend will trigger content policy restrictions.
> Recorded: Cannot use Seedance path going forward, Phase 3 will use Kling-Omni (need shot-level storyboard design).

**Phase 3 reads this field**: If `backend_selection.seedance_disabled = true`, automatically design storyboard according to Kling-Omni shot-level.

---

### Phase 2 Output

- `creative/creative.json` — Creative plan (including visual_style art style decision)
- Updated `personas.json` — Supplement reference_images (if any)
- `creative/decision_log.json` — Record reference image related decisions

**creative.json Structure**:

```json
{
  "title": "Project Title",
  "style": "cinematic",
  "duration": 30,
  "aspect_ratio": "16:9",
  "visual_style": "anime",  // realistic / anime / mixed — art style decision
  "backend_selection": {
    "seedance_disabled": false,
    "preferred_backend": "seedance",
    "reason": "Anime style, no real person material restrictions"
  },
  "music": {
    "enabled": true,
    "source": "ai_generated",
    "prompt": "Music description",
    "style": "Music style"
  },
  "narration": {
    "type": "ai_generated",
    "voice_style": "Gentle female voice, moderate pace",
    "user_text": null
  }
}
```

**backend_selection when visual_style = realistic**:

```json
{
  "visual_style": "realistic",
  "backend_selection": {
    "seedance_disabled": true,
    "preferred_backend": "kling-omni",
    "reason": "Real person reference images trigger Seedance content_policy_violation"
  }
}
```

**visual_style Field Explanation**:

| Value | Explanation | User Photo Processing |
|-------|-------------|----------------------|
| `realistic` | Photorealistic style | Seedance needs three-view conversion first, Kling-Omni can use directly |
| `anime` | Anime/2D style | Can use directly as reference image |
| `mixed` | Mixed style | Real-person scene photos need conversion, anime scenes can use directly |

| type | Explanation | Phase 3 Processing |
|------|-------------|-------------------|
| `none` | No voiceover needed | Do not plan narration_segments |
| `ai_generated` | AI designs script | Automatically write voiceover based on storyboard, segment by shot |
| `user_provided` | User already has script | Segment user_text by shot timing |

---

## Phase 3: Storyboard Design

Generate storyboard script based on materials and creative plan.

### Mandatory Reading Before Storyboard Generation

**Before generating storyboard script, must read the following three documents**:

```
Read: reference/storyboard-spec.md   # T2V/I2V decision tree, storyboard specs, JSON format
Read: reference/prompt-guide.md       # Prompt writing standards, consistency requirements
Read: reference/backend-guide.md      # Backend selection decision tree, reference image strategy
```

### Step 1: Sync Character Info to Storyboard

**Sync from personas.json to storyboard.json**:

```python
from video_gen_tools import PersonaManager

manager = PersonaManager(project_dir)

# Generate storyboard.json's elements.characters
characters = manager.export_for_storyboard()

# Generate character_image_mapping
image_mapping = manager.get_character_image_mapping()

# Write to storyboard.json
storyboard["elements"] = {"characters": characters}
storyboard["character_image_mapping"] = image_mapping
```

**After sync, storyboard.json Structure**:
```json
{
  "elements": {
    "characters": [
      {
        "element_id": "Element_SunWukong",
        "name": "SunWukong",
        "name_en": "SunWukong",
        "reference_images": ["materials/personas/sunwukong_ref.png"],
        "visual_description": "Monkey face, golden fur..."
      }
    ]
  },
  "character_image_mapping": {
    "Element_SunWukong": "image_1"
  }
}
```

### Step 2: Auto Backend Selection Logic

**Read Phase 2 Real Person Detection Result**:

First read `creative.json`'s `backend_selection` field:
- If `seedance_disabled = true` → Force use Kling-Omni, skip scene analysis
- If no such field → Select backend by scene requirements

---

**Scenario-driven Selection**:

| Scenario | Real Person Materials | Preferred Backend | Fallback Backend | Reason |
|----------|----------------------|------------------|------------------|--------|
| **Fiction/Short Drama** | None (Anime) | **Seedance** | Kling-Omni | Smart shot switching + multiple reference images |
| **Fiction/Short Drama** | **Has Real Person** | **Kling-Omni** | — | Real person materials disable Seedance |
| **Commercial (no real materials)** | None | **Seedance** | Kling-Omni | Long shots + smart shot switching |
| **Commercial (with real materials)** | Has | Kling-3.0 | — | Precise first-frame control, real materials |
| **MV Short Film** | None (Anime) | **Seedance** | Kling-Omni | Long shots + music-driven |
| **MV Short Film** | **Has Real Person** | **Kling-Omni** | — | Real person materials disable Seedance |
| **Vlog/Realistic** | Has | Kling-3.0 | Veo3 | Precise first-frame control, not using Seedance |

**First-frame Control Capability Comparison**:

| Backend | First-frame Control | Note |
|---------|-------------------|------|
| **Kling-3.0** | ✅ `--image` | Video starts from this image |
| **Veo3** | ✅ `--image` | Precise first-frame control |
| **Seedance** | ❌ Reference image | Storyboard image is visual style reference, not first frame |
| **Kling-Omni** | ❌ Reference image | Only reference2video, no img2video |

**visual_style only applies when "has user real photos + using Seedance"**:
- `realistic` → User photos need three-view conversion first
- `anime` → User photos can be used directly
- Pure creative mode: visual_style only affects AI reference image style

**Core Principles** (priority from high to low):
1. **Real Person Material Detection → Disable Seedance** (top-level filter)
2. **Use the same model for the same project**
3. **Fiction does not use text2video**
4. **When needing first-frame control, only use Kling or Vidu**
5. **Seedance/Omni storyboard images are references, not precise first-frame control**

**Execution Method Difference (Key)**:

| Backend | Storyboard Image Level | Execution Method | Output |
|---------|------------------------|------------------|--------|
| **Seedance** | scene-level | Single API call | 1 video |
| **Kling-Omni** | **shot-level** | **Call per shot** | N video clips |

**Kling-Omni Must Execute by shot-level**:
1. Generate storyboard image for each shot: `generated/frames/{shot_id}_frame.png`
2. Call API per shot: `--image-list {shot_frame} {character_ref_image}`
3. Output N video clips (to be concatenated later)

### Step 3: Generate Storyboard

**Core Structure**: Storyboard uses `scenes[] → shots[]` two-layer structure.

**Key Design Principles**:

1. **Duration Design (based on backend limits)**:
   | Backend | Scene Total Duration Limit | Design Strategy |
   |---------|---------------------------|----------------|
   | **Seedance** | **4-15s** (any integer) | Scene total duration ≤15s is fine |
   | Kling-Omni | 3-15s (continuous range) | Scene total duration ≤15s is fine |
   | Kling-3.0 | 3-15s (continuous range) | Each individual shot ≤15s |
   | Vidu | 5-10s | Each shot 5-10s |

2. Total duration = Target duration (±2 seconds), single shot 2-5 seconds
3. At most 1 action per shot, no spatial changes
4. All video_prompt must include aspect ratio info
5. Dialogue must be integrated into video_prompt (character + content + emotion + voice)
6. Set `generation_mode` and `reference_images` based on Step 2's auto-selection result

**Complete Storyboard Specification**: See [reference/storyboard-spec.md](reference/storyboard-spec.md)
**Prompt Writing and Consistency Standards**: See [reference/prompt-guide.md](reference/prompt-guide.md)

**Process Voiceover Segmentation While Generating Storyboard**:

If `creative.narration.type` is not `none`, plan voiceover segmentation while generating storyboard:

1. **Read narration info**:
   - `voice_style` → Write to `narration_config.voice_style`
   - `user_text` (if any) → Segment by shot timing

2. **Design voiceover script based on shot content**:
   - Each voiceover segment corresponds to one shot or a group of consecutive shots
   - Each segment should be 2-5 seconds in length when spoken (about 30-50 characters)

3. **Plan timing and write to storyboard.json**:

```json
{
  "narration_config": {
    "voice_style": "Gentle female voice"
  },
  "narration_segments": [
    {"segment_id": "narr_1", "overall_time_range": "0-3s", "text": "This is a peaceful afternoon..."},
    {"segment_id": "narr_2", "overall_time_range": "8-11s", "text": "She sits by the window..."}
  ]
}
```

**Voiceover Segmentation Specification**: See [reference/storyboard-spec.md](reference/storyboard-spec.md) → "Voiceover Segmentation Planning"

### Step 4: Present to User for Confirmation (Mandatory Step)

**Must get user's explicit confirmation before entering Phase 4!**

Present each shot's:
- Scene information
- Generation mode (text2video/img2video/omni-video)
- Backend selection
- video_prompt
- image_prompt (if any)
- reference_images (if any)
- Dialogue
- Transition
- Duration

**If voiceover exists, additionally present**:
- narration_segments segment list
- Each segment's timing, script

Provide options: Confirm and Execute / Modify Storyboard / Adjust Voiceover / Adjust Duration / Change Transition / Cancel

### Phase 3 Output

- `storyboard/storyboard.json` — Storyboard script (including generation_mode, reference_images, backend selection, narration_segments)

---

## Phase 4: Execute Generation

Execute video generation based on storyboard.json.

### Phase 4 Pre-execution Check

**0. Storyboard Validation (Must Pass)**

```bash
python video_gen_tools.py validate --storyboard storyboard/storyboard.json
```

Validation content: Whether Seedance duration is within 4-15s range, whether backend-mode matches, whether reference images exist, aspect_ratio format, whether API key is available.
- Has ERROR → Must fix before continuing
- Only WARNING → Can continue, but needs attention

**1. Reference Image Size Check**
- Read `reference_images` for each shot from storyboard.json
- Detect all reference image sizes
- Minimum edge < 720px → Auto upscale to 1280px
- Maximum edge > 2048px → Auto downscale to 2048px
- Auto-generate adjusted images (add `_resized` suffix)

**2. Parameter Validation**
- **Read `aspect_ratio` field from storyboard.json, pass to CLI's `--aspect-ratio` parameter**
- Set API parameters based on storyboard's `audio` configuration (see prompt-guide.md for details)

---

### Phase 4 Startup Check: Storyboard Path Consistency

**Timing**: Before starting the first video generation task each time

**Detection Logic**: Check if storyboard is written according to currently selected model path

| Backend | Required Conditions | Error Message |
|---------|--------------------|---------------|
| **Seedance** | scene-level storyboard image (scene_1_frame.png), no shot-level storyboard | No special requirements |
| **Kling-Omni** | **Each shot has image_prompt and frame_path** | Missing shot-level storyboard structure |
| **Kling img2video** | Each shot has frame_path, frame_strategy = first_frame_only | Missing first-frame image |
| **Veo3** | No special storyboard requirements | None |

**Kling-Omni Path Consistency Check**:

```python
# Check if each shot has shot-level storyboard structure
for shot in shots:
    if backend == "kling-omni":
        # Must have image_prompt (for generating storyboard image)
        if not shot.get("image_prompt"):
            errors.append(f"[{shot_id}] Kling-Omni must have image_prompt")
        
        # Must have frame_path (storyboard image output path)
        if not shot.get("frame_path"):
            errors.append(f"[{shot_id}] Kling-Omni must have frame_path")
        
        # Check if mistakenly using Seedance scene storyboard image
        ref_images = shot.get("reference_images", [])
        if ref_images and "_frame" in ref_images[0]:
            if "shot_" not in ref_images[0]:
                warnings.append(f"[{shot_id}] May be using Seedance scene storyboard, need shot-level")
```

**Check fails → Return to Phase 3 rewrite storyboard**:

```
Check storyboard → backend = kling-omni but no shot-level storyboard structure?
  ↓ Yes (has ERROR)
Inform user → Return to Phase 3:
  ⚠️ Storyboard structure inconsistent with Kling-Omni path.
  Missing shot-level storyboard images (image_prompt, frame_path).
  Need to return to Phase 3 to rewrite storyboard by shot-level.
  ↓
Return to Phase 3 → Rewrite storyboard:
  1. Design image_prompt for each shot
  2. Specify frame_path for each shot
  3. Generate shot-level storyboard images
  ↓
Recheck storyboard → Pass → Start video generation
```

**Important**: This check executes after validate_storyboard, validate passing doesn't mean path structure is correct.

---

### Execution Rules

1. **First API call executes separately**, confirm success before parallelizing
2. **No more than 3 concurrent** API generation calls
3. **Real-time update state.json** to record progress
4. **Retry on failure** up to 2 times, then ask user

### API Error Handling and Degradation

When API call fails, handle by error type:

| Error Type | Handling Method |
|-----------|----------------|
| **429 Concurrency Limit** | Ask user: Wait and retry or downgrade to Path B |
| **402 Insufficient Balance** | Inform user to top up, or downgrade to other available backend |
| **Network Timeout** | Retry 2 times, ask user after failure |
| **Other Errors** | Record error details, ask user |

**Degradation Decision Flow**:

```
API Failure → Determine error type →
  ├── 429/402 (Resource limit) → Ask user about downgrade
  │     ├── User chooses wait → Wait 60s then retry
  │     ├── User chooses downgrade → Execute degradation process (see below)
  │     └── User chooses cancel → Stop generation
  └── Other errors → Retry 2 times → Ask user after failure
```

**Degradation Execution Flow** (Seedance → Omni or Path A → Path B):

**Seedance Failure Handling** (Must retry first):
1. **First failure** → Retry once (same parameters, wait 30s)
2. **Retry still fails** → Inform user and ask about downgrade options:
   ```
   Seedance generation failed (retried 1 time).
   
   Available options:
   A. Downgrade to Kling-Omni (lose smart shot switching, need manual multi-shot)
   B. Modify prompt and retry Seedance
   C. Cancel this generation
   
   Please select:
   ```
3. User selects A → Execute degradation process

**Seedance → Omni**:
1. Inform user of degradation consequences (lose smart shot switching, need to re-execute by shot-level)
2. **Go through complete Kling-Omni flow** (don't do complex field migration):
   - Preserve storyboard's creative design (style, duration, characters, etc.)
   - Re-plan storyboard by Omni shot-level standards: design `image_prompt`, `frame_path` for each shot
   - First generate storyboard image for each shot (Gemini image generation)
   - Then call Kling-Omni API per shot
3. See [reference/backend-guide.md](reference/backend-guide.md) → "Seedance → Kling-Omni Degradation Process"

**Omni → Kling img2video**:
1. Inform user of degradation consequences (character consistency will decrease)
2. Modify storyboard.json's generation mode fields
3. Generate all storyboard images first (using Gemini)
4. Use storyboard images as first frame to call Kling img2video

**Detailed Degradation Specification**: See [reference/backend-guide.md](reference/backend-guide.md) → "Degradation Strategy When API Limited"

### Generation Mode Enforcement

**Must strictly execute according to storyboard.json, do not change without authorization**:

| generation_mode | CLI Parameters |
|----------------|----------------|
| `seedance-video` | `--backend seedance --aspect-ratio {aspect_ratio} --image-list {frame} {ref1} {ref2} ...` |
| `omni-video` | `--backend kling-omni --aspect-ratio {aspect_ratio} --image-list {frame} {ref1} {ref2} ...` |
| `img2video` | `--aspect-ratio {aspect_ratio} --image {frame_path}` |
| `text2video` | `--aspect-ratio {aspect_ratio}` |

**Important**: `{aspect_ratio}` is read from `storyboard.json`'s `aspect_ratio` field.

**Example (Seedance Mode)**:
```bash
# Seedance smart shot switching: storyboard image + character reference images
python video_gen_tools.py video \
  --backend seedance \
  --aspect-ratio 16:9 \
  --prompt "Referencing the scene1_frame composition... @image1..." \
  --image-list generated/frames/scene1_frame.png materials/personas/xiaomei_ref.jpg \
  --duration 10 \
  --output generated/videos/scene1.mp4
```

**Example (Omni Mode)**:
```bash
# Omni best practice: storyboard image + character reference images
python video_gen_tools.py video \
  --backend kling-omni \
  --aspect-ratio {aspect_ratio} \
  --prompt "Referencing scene1_shot1_frame composition. SunWukong wields golden staff, <<<image_1>>>..." \
  --image-list generated/frames/scene1_shot1_frame.png materials/personas/sunwukong_ref.png \
  --audio \
  --output generated/videos/scene1_shot1.mp4
```

### Seedance Execution Logic (Auto Assembly Mode)

**When `generation_backend = "seedance"`, use `--scene` parameter to auto-assemble time-segment prompts**.

Tool will automatically: time segment calculation, prompt format assembly, image_urls arrangement, duration validation (4-15s range).

#### Execution Steps

**Step 1: Generate Storyboard Image**
- Generate one storyboard image per Seedance scene
- Use Gemini + character reference images
- Save to `generated/frames/{scene_id}_frame.png`

**Step 2: Call Auto Assembly**

```bash
python video_gen_tools.py video \
  --backend seedance \
  --storyboard storyboard/storyboard.json \
  --scene scene_1 \
  --output generated/videos/scene_1.mp4
```

Tool internally:
1. Reads scene's shots, calculates time offsets, assembles time-segment prompts
2. Parses character reference image order from `character_image_mapping`
3. Assembles `image_urls` (storyboard image first, character reference images after)
4. Total duration can be any integer within 4-15s range

**Key**: Ensure storyboard image path is filled in shot's `reference_images`, and `video_prompt` contains camera movement + rhythm description.

#### Manual Mode (Fallback)

When auto assembly doesn't meet requirements, can still manually specify prompt:

```bash
python video_gen_tools.py video \
  --backend seedance \
  --prompt "Manually written time-segment prompt..." \
  --image-list frame.png ref.jpg \
  --duration 10 \
  --output output.mp4
```

### API Key Management

Check and request API key on first call, user provides then set via `export`.

**Detailed Tool Call Parameters**: See [reference/api-reference.md](reference/api-reference.md)

### Music Generation

Calling `video_gen_tools.py music` must pass `--creative` parameter.

Reason: Read `prompt` (music description) and `style` (music style) from `creative.json`'s `music` field, avoid using default style.

### Voiceover Generation (Conditional Trigger)

**Trigger Condition**: Read `storyboard.json`'s `narration_segments`, if exists then trigger.

**Generation Flow**:

1. **Read narration_config and narration_segments**
2. **Call TTS for each segment**:

```bash
# Generate each voiceover segment separately
python video_gen_tools.py tts \
  --text "This is a peaceful afternoon..." \
  --voice-style "Gentle female voice, moderate pace" \
  --output generated/narration/narr_1.mp3

python video_gen_tools.py tts \
  --text "She sits by the window..." \
  --voice-style "Gentle female voice, moderate pace" \
  --output generated/narration/narr_2.mp3
```

3. **Output File Naming**: Named by `segment_id` (`narr_1.mp3`, `narr_2.mp3`...)

**Execution Order**:
```
Video segment generation → Music generation → Voiceover generation (if any) → Enter Phase 5 Editing
```

### Phase 4 Output

- `generated/videos/*.mp4` — Generated video segments
- `generated/music/*.mp3` — Generated background music (if any)
- `generated/narration/*.mp3` — Generated voiceover audio (if any)
- Updated `state.json` — Record generation progress

---

## Phase 5: Edit Output

### Video Concatenation

Calling `video_gen_editor.py concat` must pass `--storyboard` parameter.

Reason: Read `aspect_ratio` from `storyboard.json`, ensure output video has correct aspect ratio.

### Audio Protection

Video segments may contain sync sound, sound effects, cannot be lost during concatenation. Silent segments will auto-add silent track, ensure audio-video sync.

### Video Parameter Validation

Before concatenation, auto-check resolution/encoding/framerate, auto-normalize if inconsistent (1080x1920 / H.264 / 24fps).

```bash
python video_gen_editor.py concat --inputs video1.mp4 video2.mp4 --output final.mp4
```

### Synthesis Flow

1. **Concatenate** → Connect by storyboard order (auto normalize)
2. **Insert Voiceover** → Place voiceover audio at correct position according to `narration_segments`'s `overall_time_range` (if any)
3. **Transitions** → Add transition effects between shots
4. **Color Grading** → Apply overall color grading style
5. **Music** → Mix background music
6. **Output** → Generate final video

### Audio Mixing Rules

**Core Principle**: FFmpeg `amix` filter **must use `normalize=0`**, prevent auto-normalization from lowering volume.

**Recommended Volume Values** (adjust flexibly based on video type):

| Audio Type | Recommended Volume | Note |
|-----------|-------------------|------|
| Video ambient/sync sound | 0.8 | Preserve original audio atmosphere |
| Voiceover/Narration | 1.5-2.0 | Ensure voice clarity |
| Background Music (BGM) | 0.1-0.15 | Background supporting role |

**Video Type Adaptation**:

| Video Type | BGM Volume | Reason |
|-----------|----------|--------|
| Vlog/Documentary | 0.1-0.15 | Voiceover is primary |
| Cinematic/Fiction | 0.2-0.3 | Music enhances emotion |
| Music MV | 0.5-0.7 | Music is core element |
| Commercial | 0.15-0.25 | Balance product intro and music |

**FFmpeg amix Syntax**:
```bash
# Key: normalize=0 preserves original volume ratio
"[track1][track2]amix=inputs=2:duration=first:normalize=0[out]"
```

**Implementation Note**: `video_gen_editor.py`'s `mix_audio()` function has hardcoded `normalize=0` (around line 470).

### Voiceover Insertion (Conditional Trigger)

**Trigger Condition**: Read `storyboard.json`'s `narration_segments`, if exists then trigger.

**Insertion Method**: Use FFmpeg to insert voiceover audio at specified time points.

```bash
# Insert voiceover by overall_time_range
python video_gen_editor.py narration \
  --video concat_output.mp4 \
  --storyboard storyboard/storyboard.json \
  --narration-dir generated/narration \
  --output with_narration.mp4
```

**Timing Calculation**:
- `overall_time_range` format: `"0-3s"` means starts at 0 seconds, ends at 3 seconds
- Voiceover audio is inserted at the start time of `overall_time_range`
- Multiple voiceover segments are overlaid in chronological order

### Phase 5 Output

- `output/final.mp4` — Final video

---

## Tool Command Reference

```bash
# Environment check
python video_gen_tools.py check

# Storyboard validation (Must pass before Phase 4 execution)
python video_gen_tools.py validate --storyboard storyboard/storyboard.json

# Video generation (Must read aspect_ratio from storyboard.json)
python video_gen_tools.py video --prompt <description> --aspect-ratio {aspect_ratio} --output <output>

# Seedance auto assembly mode (Recommended: tool auto-calculates time segments, assembles prompt, arranges image_urls)
python video_gen_tools.py video \
  --backend seedance \
  --storyboard storyboard/storyboard.json \
  --scene scene_1 \
  --output generated/videos/scene_1.mp4

# Seedance manual mode (Fallback)
python video_gen_tools.py video \
  --backend seedance \
  --prompt "Manually written time-segment prompt..." \
  --image-list frame.png ref.jpg \
  --duration 10 \
  --output output.mp4

# Veo3 text-to-video (Global fallback, only supports 4/6/8s)
python video_gen_tools.py video \
  --backend veo3 \
  --prompt <description> \
  --duration 8 \
  --output generated/videos/shot.mp4

# Veo3 image-to-video (First-frame control)
python video_gen_tools.py video \
  --backend veo3 \
  --image <first-frame-image> \
  --prompt <description> \
  --duration 8 \
  --output generated/videos/shot.mp4

# Music (Must pass --creative, reads prompt and style from creative.json)
python video_gen_tools.py music --creative creative/creative.json --output <output>

# Voiceover (Call by narration_segments)
python video_gen_tools.py tts --text <segment-script> --voice female_narrator --emotion gentle --output generated/narration/narr_1.mp3

# Image generation
python video_gen_tools.py image --prompt <description> --aspect-ratio {aspect_ratio} --output <output>

# Editing (concat must pass --storyboard, reads aspect_ratio from storyboard.json)
python video_gen_editor.py concat --inputs <video-list> --output <output> --storyboard storyboard/storyboard.json

# Voiceover insertion (Insert by overall_time_range)
python video_gen_editor.py narration --video <video> --storyboard storyboard/storyboard.json --narration-dir generated/narration --output <output>

# Other editing commands
python video_gen_editor.py mix --video <video> --bgm <music> --output <output>
python video_gen_editor.py transition --inputs <v1> <v2> --type <type> --output <output>
python video_gen_editor.py color --video <video> --preset <preset> --output <output>
```

---

## File Structure

```
~/video-gen-projects/{project_name}_{timestamp}/
├── state.json           # Project status
├── materials/           # Original materials
│   └── personas/        # Character reference images (Phase 2 generated)
├── analysis/
│   └── analysis.json    # Material analysis
├── creative/
│   ├── creative.json    # Creative plan
│   └── decision_log.json # Decision records
├── storyboard/
│   └── storyboard.json  # Storyboard script (contains narration_segments)
├── generated/
│   ├── videos/          # Generated videos
│   ├── music/           # Generated music
│   ├── narration/       # Generated voiceover audio
│   └── image/           # Generated images
└── output/
    └── final.mp4        # Final video
```

---

## Error Handling

| Issue | Handling Method |
|-------|-----------------|
| Visual analysis failure | VisionClient fallback → Ask user |
| API key not configured | Ask on first call |
| API call failure | Retry 2 times → Ask user |
| Video generation failure | Try other modes or use original materials |
| Music generation failure | Generate silent video and inform |

---

## Dependencies

- FFmpeg 6.0+
- Python 3.9+
- httpx