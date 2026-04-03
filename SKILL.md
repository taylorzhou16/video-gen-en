---
name: video-gen-en
description: AI video editing tool. Analyze materials, generate creative ideas, design storyboards, execute editing. Supports Vidu/Kling/Kling Omni video generation, Suno music generation, TTS voiceover, FFmpeg editing. Triggers when users request video creation, video editing, video generation, short film creation, or provide material directories for producing works.
argument-hint: <material_directory_or_video_file>
---

# video-gen User Guide

**Role**: Director Agent — Understand creative intent, coordinate all resources, deliver video works.

**Language Requirement**: Respond in the same language the user uses. If user writes in Chinese, respond in Chinese; if user writes in English, respond in English.

---

## Recommended Configuration

**Must use a multimodal model** (such as Claude Opus/Sonnet/Kimi-K2.5) for the best experience.

For non-multimodal models, a vision model will be automatically called for image analysis. Configure `VISION_BASE_URL`, `VISION_MODEL`, `VISION_API_KEY` in `config.json`.

### Provider Selection

**Different backends support different providers**:

| Backend | Supported Providers | Notes |
|------|----------------|------|
| `seedance` | **piapi only** | Seedance only has piapi provider, no yunwu/fal support |
| `kling-omni` | official, yunwu, fal | Switch when official API hits limits |
| `kling` | official, yunwu | Switch when official API hits limits |
| `vidu` | **yunwu only** | Vidu only has yunwu provider |

When Kling official API encounters rate limits (429), use `--provider yunwu` or `--provider fal`:

```bash
# yunwu proxy (supports Vidu/Kling/Kling-Omni)
python video_gen_tools.py video --provider yunwu --backend kling-omni --image-list ref.jpg ...

# fal.ai proxy (only supports kling-omni)
python video_gen_tools.py video --provider fal --backend kling-omni --image-list ref.jpg ...
```

**Note**: Seedance doesn't need `--provider` specified since it only has piapi provider.

**Provider auto-selection priority**: Official API → fal → yunwu

---

## Core Concepts

- **Tool Files**: video_gen_tools.py (API calls) and video_gen_editor.py (FFmpeg editing) are command-line tools
- **Flexible Planning, Robust Execution**: Planning phase produces structured artifacts, execution phase is driven by storyboard plan
- **Graceful Degradation**: Proactively seek user help when encountering problems, rather than getting stuck

### Backend Selection Overview

**Scenario-driven selection**:

| Scenario | Priority Backend | Fallback Backend | Reason |
|-----|---------|---------|------|
| **Fiction films/short dramas** | **Seedance** | Kling-Omni | Smart shot cutting + multi-reference, character consistency |
| **Commercials (no real materials)** | **Seedance** | Kling-Omni | Long shots + smart shot cutting |
| **Commercials (with real materials)** | Kling-3.0 / Vidu | — | Precise first frame control, real materials |
| **MV clips** | **Seedance** | Kling-Omni | Long shots + music-driven |
| **Vlog/documentary style** | Kling-3.0 | Vidu | Precise first frame control, no Seedance |

**visual_style only affects user photo processing (if user photos exist)**:

| visual_style | User Photo Processing | Notes |
|--------------|-------------|------|
| `realistic` | **Seedance needs conversion** | User photos need 3-view generation first, then as reference |
| `anime` | Direct use | Can be used as reference directly |
| `mixed` | Per-scene processing | Realistic scenes need conversion, anime scenes direct use |

**Seedance user photo conversion flow**:
```
User provides real photo →
  ├── Call Gemini to generate 3-view (preserve face, body, figure details) →
  │   - Front view
  │   - Side view
  │   - Full body proportion
  ├── Select best angle as character reference →
  └── Register to personas.json
```

**Key Rules**:
- **Seedance prioritized for fictional content** (smart shot cutting is core advantage)
- **Kling-Omni as fallback when Seedance fails**
- **Use Kling/Vidu for real materials** (precise first frame control)
- **Use same model for same project**, no mixing (except mixed mode)

Detailed backend comparison and reference image strategy: See [reference/backend-guide.md](reference/backend-guide.md)

---

## Quick Start Workflow

```
Environment Check → Material Collection → Creative Confirmation → Storyboard Design → Generation Execution → Editing Output
      5s               Interactive         Interactive           Interactive           Automatic            Automatic
```

### Workflow Progress Checklist

```
Task Progress:
- [ ] Phase 0: Environment Check (python video_gen_tools.py check)
- [ ] Phase 1: Material Collection (scan + visual analysis + character identification)
- [ ] Phase 2: Creative Confirmation (question card interaction + character reference collection)
- [ ] Phase 3: Storyboard Design (generate storyboard.json + auto backend selection + user confirmation)
- [ ] Phase 4: Generation Execution (API calls + progress tracking)
- [ ] Phase 5: Editing Output (concatenation + transitions + color grading + music)
```

---

## Phase 0: Environment Check

```bash
python ~/.claude/skills/video-gen/video_gen_tools.py check
```

- Basic dependencies (FFmpeg/Python/httpx) fail → Stop and provide installation instructions
- API key not configured → Record status, ask later as needed

---

## Phase 1: Material Collection

### Material Source Identification

- **Directory path** → Scan images/videos in directory
- **Video file** → Analyze that video directly
- **No materials** → Pure creative mode

### Visual Analysis Process (3-level fallback)

**Step 1**: Use Read tool to read images. Record scene description, subject content, emotional tone, color style.

**Step 2**: Read fails → Call built-in VisionClient:

```python
from video_gen_tools import VisionClient
client = VisionClient()
results = await client.analyze_batch(image_paths, "Analyze these materials: scene, subject, color, atmosphere")
```

**Step 3**: VisionClient also fails → Proactively ask user to describe each material's content.

### Character Identification (Conditional)

**Triggered only when user provides character portrait images** (ask user if unsure).

Execution steps:
1. Read image content, identify all characters
2. Ask user to confirm each character's identity
3. Register each using PersonaManager:

```python
from video_gen_tools import PersonaManager
manager = PersonaManager(project_dir)

# Case A: User provided reference image
manager.register("Emma", "female", "path/to/ref.jpg", "long hair, oval face")

# Case B: User did not provide reference image (Phase 2 will supplement)
manager.register("Marcus", "male", None, "short brown hair, athletic build, casual clothes")
```

**Phase 1 Key Principles**:
- Only process reference images **already uploaded** by user
- For characters without uploads, set reference_image to `None`, supplemented in Phase 2
- Do not ask about reference images not uploaded at this stage

### Phase 1 Outputs

Create project directory `~/video-gen-projects/{project_name}_{timestamp}/`, outputs:
- `state.json` — Project status
- `analysis/analysis.json` — Material analysis results
- `personas.json` — Character registry (reference_image may be None)

**personas.json Structure**:
```json
{
  "personas": [
    {
      "name": "Marcus",
      "gender": "male",
      "reference_image": null,
      "features": "monkey face, golden fur, fiery eyes, wearing golden armor"
    },
    {
      "name": "Emma",
      "gender": "female",
      "reference_image": "/path/to/ref.jpg",
      "features": "long hair, oval face"
    }
  ]
}
```

---

## Phase 2: Creative Confirmation

**Use question cards to interact with user**, collecting key information.

### Question Card Design

**Question 1: Video Style**
- Options: Cinematic | Vlog style | Commercial | Documentary | Art/Experimental
- Note: Determines overall tone of color grading, transitions, music

**Question 2: Target Duration**
- Options: 15s (short video) | 30s (standard) | 60s (long video) | Custom
- Note: Affects number of shots and pacing

**Question 3: Aspect Ratio**
1. 9:16 Vertical
   Portrait for TikTok/Instagram Stories/YouTube Shorts
2. 16:9 Horizontal (Recommended)
   Landscape for YouTube/broad viewing
3. 1:1 Square
   Square for Instagram feed/Facebook
4. Type something else
- Note: Choose based on publishing platform

**Question 4: Music Needs**
- Options: AI-generated BGM | No music needed | I already have music
- Note: Whether Suno needs to generate background music

**Question 5: Narration/Voiceover**

**First determine if video type is suitable for narration**:

| Video Style | Narration Need | Note |
|-------------|----------------|------|
| Cinematic/Fiction | Usually not needed | Dialogue is main, narration breaks immersion |
| Documentary | Usually needed | Scene explanation, background intro |
| Vlog style | Possibly needed | Travel commentary, mood recording |
| Commercial | Possibly needed | Product intro, brand story |
| Art/Experimental | Case-dependent | Concept expression may need narration |

**When uncertain, ask user**:

> Does this video need narration/voiceover?
> - **No narration** (Dialogue is main, or pure visual expression)
> - **Need AI-generated narration** (I will design copy based on storyboard)
> - **I already have narration copy** (User provides complete copy)

**Distinguish two audio generation methods**:

**A. Character Dialogue (Sync Sound)**
- Generated directly by video generation model
- Need to explicitly describe in shot's video_prompt: character, dialogue, emotion, speed, voice quality
- Set `audio: true` during video generation

**B. Narration/Voiceover (Post-production Dubbing)**
- Generated by TTS in post-production, mixed in during editing phase
- Used for scene explanation, background intro, emotional enhancement
- Phase 3 will design narration copy and timing based on storyboard

**Important Principle**: For shots that can capture sync sound, do not use post-production TTS dubbing!

### Question 6: Character Reference Image Collection

**Trigger Condition**: Check personas.json, trigger when characters have `reference_image` as null/empty.

**Check Logic**:
```python
manager = PersonaManager(project_dir)
for persona_id in manager.list_personas_without_reference():
    # Ask user for this character's reference image source
    ask_user_for_reference(persona_id)
```

**Question Content** (for each character without reference):

> **Character '{name}' needs reference image**
>
> Please select reference image source:
> - **A. AI-generate character image** (Recommended, automatically generates standard reference)
> - **B. Upload reference image** (User provides character photo)
> - **C. Accept pure text generation** (Character appearance may vary across shots)

**Post-selection Processing**:

**A. AI Generation**:
```python
# Generate character reference image
python video_gen_tools.py image \
  --prompt "{character appearance description}, front half-body shot, solid background, HD portrait" \
  --output materials/personas/{name}_ref.png

# Update personas.json
manager.update_reference_image(persona_id, "materials/personas/{name}_ref.png")
```

**B. Upload Reference Image**:
- Ask user to upload image
- Save to `materials/personas/{name}_ref.{ext}`
- Update personas.json

**C. Pure Text**:
- Record warning to `creative/decision_log`
- Phase 3 will **force generate storyboard frame**, then use img2video or reference2video

**Key Rules**:
- **Must generate reference image**: When character appears in **multiple shots**
- **Can use text2video**: Single scene appearance, pure scenery, user explicitly accepts appearance variation

### Phase 2 Outputs

- `creative/creative.json` — Creative plan
- Updated `personas.json` — Supplemented reference_images (if any)
- `creative/decision_log.json` — Records reference image related decisions

**creative.json narration field structure**:

```json
{
  "narration": {
    "type": "ai_generated",
    "voice_style": "Gentle female voice, moderate speed",
    "user_text": "User-provided complete narration copy"
  }
}
```

| type | Note | Phase 3 Processing |
|------|------|-------------------|
| `none` | No narration needed | Do not plan narration_segments |
| `ai_generated` | AI designs copy | Auto-write narration based on storyboard, segment by shot |
| `user_provided` | User has copy | Segment user_text by shot timing |

---

## Phase 3: Storyboard Design

Generate storyboard script based on materials and creative plan.

### Must Read Before Generating Storyboard

**Before generating storyboard script, must read these three documents**:

```
Read: reference/storyboard-spec.md   # T2V/I2V decision tree, storyboard spec, JSON format
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

**Synced storyboard.json structure**:
```json
{
  "elements": {
    "characters": [
      {
        "element_id": "Element_Marcus",
        "name": "Marcus",
        "name_en": "Marcus",
        "reference_images": ["materials/personas/Marcus_ref.png"],
        "visual_description": "monkey face, golden fur..."
      }
    ]
  },
  "character_image_mapping": {
    "Element_Marcus": "image_1"
  }
}
```

### Step 2: Auto Backend Selection Logic

**Automatically select backend based on project type** (no manual decision needed):

#### Project Type Judgment (Phase 1 auto identification)

| User Intent Keywords | Project Type |
|---------------------|--------------|
| "short drama", "plot", "story" | Fiction film/short drama |
| "vlog", "travel record", "life record" | Vlog/documentary style |
| "commercial", "promo video", "product showcase" | Commercial/promo video |
| "MV", "music video" | MV clip |

#### Decision Tree

**Fiction films/short dramas, MV clips**:
```
Fiction content → All shots must first generate storyboard frame
           ├── Priority → Kling-3.0-Omni (reference2video)
           │             └── image_list: [storyboard frame, character reference]
           │
           └── Fallback → Kling-3.0 or Vidu Q3 Pro (img2video)
                         └── --image: storyboard frame as first frame
```

**Vlog/documentary style, commercials/promos (with real materials)**:
```
Real materials → Need first frame control
           └── Kling-3.0 or Vidu Q3 Pro (img2video)
               └── --image: User material first frame
```

#### Selection Rules Table

| Project Type | Material Situation | Generation Mode | Backend |
|--------------|-------------------|-----------------|---------|
| Fiction/short drama | With/without character ref | **reference2video** | kling-omni |
| MV clip | With/without character ref | **reference2video** | kling-omni |
| Vlog/documentary | User real materials | **img2video** | kling or vidu |
| Commercial/promo | Has real materials | **img2video** | kling or vidu |
| Commercial/promo | No real materials | **reference2video** | kling-omni |

**Core Principles**:
1. **Use same model for same project**, do not mix
2. **Fiction films do not use text2video**
3. **Omni does not support first frame control**, use Kling-3.0 or Vidu when needed

### Step 3: Generate Storyboard

**Core Structure**: Storyboard uses `scenes[] → shots[]` two-level structure.

**Key Design Principles**:
1. Total duration = Target duration (±2s), single shot 2-5 seconds
2. Max 1 action per shot, no spatial changes
3. All video_prompt must include aspect ratio info
4. Dialogue must be integrated into video_prompt (character + content + emotion + voice)
5. Set `generation_mode` and `reference_images` based on Step 2's auto selection result

**Full storyboard spec**: See [reference/storyboard-spec.md](reference/storyboard-spec.md)
**Prompt writing and consistency spec**: See [reference/prompt-guide.md](reference/prompt-guide.md)

**Process narration while generating storyboard**:

If `creative.narration.type` is not `none`, plan narration segments while generating storyboard:

1. **Read narration info**:
   - `voice_style` → Write to `narration_config.voice_style`
   - `user_text` (if any) → Segment by shot timing

2. **Design narration copy based on shot content**:
   - Each narration segment corresponds to one shot or consecutive shots
   - Each segment should be 2-5 seconds speakable length (about 30-50 words)

3. **Plan timing and write to storyboard.json**:

```json
{
  "narration_config": {
    "voice_style": "Gentle female voice"
  },
  "narration_segments": [
    {"segment_id": "narr_1", "overall_time_range": "0-3s", "text": "This is a quiet afternoon..."},
    {"segment_id": "narr_2", "overall_time_range": "8-11s", "text": "She sits by the window..."}
  ]
}
```

**Narration segment spec**: See [reference/storyboard-spec.md](reference/storyboard-spec.md) → "Narration Segment Planning"

### Step 4: Show to User for Confirmation (Required Step)

**Must have user's explicit confirmation before entering Phase 4!**

Show for each shot:
- Scene info
- Generation mode (text2video/img2video/omni-video)
- Backend selection
- video_prompt
- image_prompt (if any)
- reference_images (if any)
- Dialogue
- Transition
- Duration

**If has narration, additionally show**:
- narration_segments segment list
- Each segment's timing, copy

Provide options: Confirm and execute / Modify storyboard / Adjust narration / Adjust duration / Change transition / Cancel

### Phase 3 Outputs

- `storyboard/storyboard.json` — Storyboard script (includes generation_mode, reference_images, backend selection, narration_segments)

---

## Phase 4: Generation Execution

Execute video generation based on storyboard.json.

### Pre-execution Check

**1. Reference Image Size Check**
- Read each shot's `reference_images` from storyboard.json
- Check all reference image sizes
- Min dimension < 720px → Auto upscale to 1280px
- Max dimension > 2048px → Auto downscale to 2048px
- Auto generate adjusted images (add `_resized` suffix)

**2. Parameter Validation**
- **Read `aspect_ratio` field from storyboard.json, pass to CLI's `--aspect-ratio` parameter**
- Set API parameters based on storyboard's `audio` config (see prompt-guide.md)

### Execution Rules

1. **First API call executes alone**, confirm success before concurrent
2. **Max 3 concurrent** API generation calls
3. **Real-time update state.json** recording progress
4. **Retry on failure** max 2 times, then ask user

### API Error Handling and Degradation

When API call fails, handle by error type:

| Error Type | Handling |
|------------|----------|
| **429 Concurrent limit** | Ask user: wait retry or degrade to Path B |
| **402 Insufficient balance** | Notify user to recharge, or degrade to other available backend |
| **Network timeout** | Retry 2 times, ask after failure |
| **Other error** | Record error details, ask user |

**Degradation Decision Flow**:

```
API Fail → Determine error type →
  ├── 429/402 (resource limit) → Ask user to degrade
  │     ├── User chooses wait → Wait 60s then retry
  │     ├── User chooses degrade → Execute degradation flow (see below)
  │     └── User chooses cancel → Stop generation
  └── Other error → Retry 2 times → Ask user after failure
```

**Degradation Execution Flow** (Path A → Path B):

1. Notify user of degradation consequence (character consistency will decrease)
2. Modify storyboard.json's generation mode field
3. First generate all storyboard frames (using Gemini)
4. Use storyboard frames as first frame to call Kling img2video

**Degradation detailed spec**: See [reference/backend-guide.md](reference/backend-guide.md) → "Degradation Strategy on API Limits"

### Generation Mode Strict Execution

**Must strictly execute according to storyboard.json, no unauthorized changes**:

| generation_mode | CLI Parameters |
|-----------------|----------------|
| `omni-video` | `--backend kling-omni --aspect-ratio {aspect_ratio} --image-list {ref1} {ref2} ...` |
| `img2video` | `--aspect-ratio {aspect_ratio} --image {frame_path}` |
| `text2video` | `--aspect-ratio {aspect_ratio}` |

**Important**: `{aspect_ratio}` read from `storyboard.json`'s `aspect_ratio` field.

**Example (Omni mode)**:
```bash
# Read aspect_ratio from storyboard.json (e.g. "16:9")
python video_gen_tools.py video \
  --backend kling-omni \
  --aspect-ratio {aspect_ratio} \
  --prompt "Marcus walking confidently..." \
  --image-list materials/personas/marcus_ref.png \
  --audio \
  --output generated/videos/scene1_shot1.mp4
```

### API Key Management

Check and request API key on first call, set via `export` after user provides.

**Tool call detailed parameters**: See [reference/api-reference.md](reference/api-reference.md)

### Music Generation

Calling `video_gen_tools.py music` must pass `--creative` parameter.

Reason: Read `prompt` (music description) and `style` (music style) from `creative.json`'s `music` field, avoid using default style.

### Narration Generation (Conditional Trigger)

**Trigger Condition**: Read `storyboard.json`'s `narration_segments`, trigger if exists.

**Generation Flow**:

1. **Read narration_config and narration_segments**
2. **Call TTS for each segment**:

```bash
# Generate each narration segment separately
python video_gen_tools.py tts \
  --text "This is a quiet afternoon..." \
  --voice-style "Gentle female voice, moderate speed" \
  --output generated/narration/narr_1.mp3

python video_gen_tools.py tts \
  --text "She sits by the window..." \
  --voice-style "Gentle female voice, moderate speed" \
  --output generated/narration/narr_2.mp3
```

3. **Output file naming**: Name by `segment_id` (`narr_1.mp3`, `narr_2.mp3`...)

**Execution Order**:
```
Video clip generation → Music generation → Narration generation (if any) → Enter Phase 5 Editing
```

### Phase 4 Outputs

- `generated/videos/*.mp4` — Generated video clips
- `generated/music/*.mp3` — Generated background music (if any)
- `generated/narration/*.mp3` — Generated narration audio (if any)
- Updated `state.json` — Recording generation progress

---

## Phase 5: Editing Output

### Video Concatenation

Calling `video_gen_editor.py concat` must pass `--storyboard` parameter.

Reason: Read `aspect_ratio` from `storyboard.json` to ensure correct output video ratio.

### Audio Preservation

Video clips may contain sync sound, effects, must not lose during concatenation. Silent clips will auto-add silent track to ensure audio-visual sync.

### Video Parameter Validation

Auto check resolution/encoding/framerate before concatenation, normalize if inconsistent (1080x1920 / H.264 / 24fps).

```bash
python ~/.claude/skills/video-gen/video_gen_editor.py concat --inputs video1.mp4 video2.mp4 --output final.mp4
```

### Synthesis Flow

1. **Concatenate** → Connect by storyboard order (auto normalize)
2. **Insert narration** → Position narration audio at correct position based on `narration_segments`' `overall_time_range` (if any)
3. **Transition** → Add transition effects between shots
4. **Color grading** → Apply overall color grading style
5. **Music** → Mix background music
6. **Output** → Generate final video

### Audio Mixing Rules

**Core Principle**: FFmpeg `amix` filter **must use `normalize=0`**, prevent auto-normalization from lowering volume.

**Recommended Volume Values** (adjust flexibly by video type):

| Audio Type | Recommended Volume | Note |
|------------|-------------------|------|
| Video ambient/sync sound | 0.8 | Preserve original audio atmosphere |
| Narration/voiceover | 1.5-2.0 | Ensure voice clarity |
| Background music (BGM) | 0.1-0.15 | Background supporting role |

**Video Type Adaptation**:

| Video Type | BGM Volume | Reason |
|------------|------------|--------|
| Vlog/Documentary | 0.1-0.15 | Narration is main |
| Cinematic/Fiction | 0.2-0.3 | Music enhances emotion |
| Music MV | 0.5-0.7 | Music is core element |
| Commercial | 0.15-0.25 | Balance product intro with music |

**FFmpeg amix syntax**:
```bash
# Key: normalize=0 preserves original volume ratio
"[track1][track2]amix=inputs=2:duration=first:normalize=0[out]"
```

**Implementation Note**: `video_gen_editor.py`'s `mix_audio()` function has hardcoded `normalize=0` (around line 470).

### Narration Insertion (Conditional Trigger)

**Trigger Condition**: Read `storyboard.json`'s `narration_segments`, trigger if exists.

**Insertion Method**: Use FFmpeg to insert narration audio at specified time points.

```bash
# Insert narration by overall_time_range
python video_gen_editor.py narration \
  --video concat_output.mp4 \
  --storyboard storyboard/storyboard.json \
  --narration-dir generated/narration \
  --output with_narration.mp4
```

**Timing Calculation**:
- `overall_time_range` format: `"0-3s"` means starts at 0 seconds, continues to 3 seconds
- Narration audio inserts at `overall_time_range`'s start time
- Multiple narration segments stack in time order

### Phase 5 Outputs

- `output/final.mp4` — Final video

---

## Tool Call Quick Reference

```bash
# Environment check
python ~/.claude/skills/video-gen/video_gen_tools.py check

# Video generation (must read aspect_ratio from storyboard.json)
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt <description> --aspect-ratio {aspect_ratio} --output <output>

# Music (must pass --creative, read prompt and style from creative.json)
python ~/.claude/skills/video-gen/video_gen_tools.py music --creative creative/creative.json --output <output>

# Narration (call by narration_segments)
python ~/.claude/skills/video-gen/video_gen_tools.py tts --text <segment copy> --voice female_narrator --emotion gentle --output generated/narration/narr_1.mp3

# Image generation
python ~/.claude/skills/video-gen/video_gen_tools.py image --prompt <description> --aspect-ratio {aspect_ratio} --output <output>

# Editing (concat must pass --storyboard, read aspect_ratio from storyboard.json)
python ~/.claude/skills/video-gen/video_gen_editor.py concat --inputs <video list> --output <output> --storyboard storyboard/storyboard.json

# Narration insertion (insert by overall_time_range)
python ~/.claude/skills/video-gen/video_gen_editor.py narration --video <video> --storyboard storyboard/storyboard.json --narration-dir generated/narration --output <output>

# Other editing commands
python ~/.claude/skills/video-gen/video_gen_editor.py mix --video <video> --bgm <music> --output <output>
python ~/.claude/skills/video-gen/video_gen_editor.py transition --inputs <v1> <v2> --type <type> --output <output>
python ~/.claude/skills/video-gen/video_gen_editor.py color --video <video> --preset <preset> --output <output>
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
│   └── storyboard.json  # Storyboard script (includes narration_segments)
├── generated/
│   ├── videos/          # Generated videos
│   ├── music/           # Generated music
│   ├── narration/       # Generated narration audio
│   └── image/           # Generated images
└── output/
    └── final.mp4        # Final video
```

---

## Error Handling

| Issue | Handling |
|-------|----------|
| Visual analysis fail | VisionClient fallback → Ask user |
| API key not configured | Ask on first call |
| API call fail | Retry 2 times → Ask user |
| Video generation fail | Try other modes or use original materials |
| Music generation fail | Generate silent video and notify |

---

## Dependencies

- FFmpeg 6.0+
- Python 3.9+
- httpx