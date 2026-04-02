# Backend Selection and Reference Image Strategy

## Table of Contents

- Three Backend Capabilities Comparison
- Backend Selection Decision Tree
- Auto-selection Logic
- Two Paths for Character Reference Images
- **Path A: Kling Omni (Recommended)**
- Path B: Kling + Gemini First Frame
- Gemini Prompt Notes

---

## Three Backend Capabilities Comparison

| Feature | Vidu | Kling | Kling Omni |
|---------|------|-------|------------|
| **Backend Name** | `vidu` | `kling` | `kling-omni` |
| **Text-to-video** | 5-10s | 3-15s | 3-15s |
| **Image-to-video** | Single image | First frame image (precise control) | Use image_list instead |
| **image_list Multiple Reference Images** | -- | -- | `<<<image_1>>>` reference |
| **multi_shot Multi-shot** | -- | intelligence / customize | intelligence / customize |
| **First/Last Frame Control** | -- | `--image` + `--tail-image` | -- |
| **Audio-Video Together** | -- | `--audio` | `--audio` |
| **Best Scenario** | Simple fast, fallback | First frame precise control, scene consistency | Character consistency, multi-character |

**Key Difference**:
- Kling `--image` is **first frame image** (video starts from this image)
- Kling Omni `--image-list` is **reference image** (character stays consistent)

---

## Backend Selection Decision Tree

**Core Trade-off: Character Consistency vs Scene Precision vs Both**

```
Does shot contain characters?
├── Yes → Have registered character reference images?
│        ├── Yes → Need scene precise control?
│        │        ├── Yes → Need character consistency?
│        │        │        ├── Both → Omni + storyboard image reference + character reference image (Path A best practice)
│        │        │        └── First frame certainty priority → Kling + Gemini first frame (Path B)
│        │        └── No → Omni --image-list (Path A basic usage)
│        └── No → Need precise control of first frame visuals?
│                 ├── Yes → Kling + image (Gemini generates first frame)
│                 └── No → Kling text2video
└── No → Need multi_shot?
         ├── Yes → Kling
         └── No → Kling (default)
```

### Scenario Quick Reference

| Scenario | Backend | Key Parameters |
|----------|---------|----------------|
| **Narrative video, scene+character both needed** | **Omni** | `--image-list frame.png ref.jpg` |
| Fast prototype, character consistency priority | Omni | `--image-list ref.jpg` |
| Scene precision priority, character can vary | Kling | `--image first_frame.png` |
| Need first/last frame animation | Kling | `--image first.png --tail-image last.png` |
| Multi-shot narrative + character consistency | Omni | `--image-list ref.jpg --multi-shot` |
| Simple non-character scene / Fast prototype | Kling (default) or vidu | No special parameters needed |

---

## Auto-selection Logic

Default uses **kling** when `--backend` not specified. Special parameters force backend switch:
- Provide `--image-list` → Auto switch to kling-omni (only one that supports)
- Provide `--tail-image` → Keep kling (only one that supports)
- Need fast fallback → Manually specify `--backend vidu`

### Provider Selection Priority

When `--provider` is not specified, auto-selection follows this priority:

| Condition | Provider | Description |
|-----------|----------|-------------|
| Has KLING_ACCESS_KEY + KLING_SECRET_KEY | `official` | Kling official API |
| Has YUNWU_API_KEY | `yunwu` | yunwu.ai proxy |
| Has FAL_API_KEY | `fal` | fal.ai proxy |

**Manually specify provider**:

```bash
# Use yunwu proxy (bypass official API rate limits)
python video_gen_tools.py video --provider yunwu --backend kling-omni --image-list ref.jpg ...

# Use fal.ai proxy
python video_gen_tools.py video --provider fal --backend kling-omni --image-list ref.jpg ...
```

**yunwu vs fal comparison**:

| Provider | Supported Backends | Advantage | Use Case |
|----------|-------------------|-----------|----------|
| `yunwu` | vidu, kling, kling-omni | Full range support, stable in China | First choice fallback when official API unavailable |
| `fal` | kling-omni | Stable international access | Alternative when only kling-omni needed |

---

## Two Paths for Character Reference Images

**Only consider when character reference images are registered**

| | **Path A: Kling Omni (Recommended)** | Path B: Kling + Gemini |
|---|---|---|
| **Process** | **Storyboard image + Character reference image → `image_list`** | Storyboard image → `--image` → Kling img2video |
| **Advantage** | **Both: Scene controllable + Character consistent** | Scene precisely controllable |
| **Consistency** | **Good (reference image in image_list)** | Moderate |
| **Scene Control** | **Strong (Storyboard image provides overall visual)** | Strong (Storyboard image as first frame) |
| **Applicable** | **Narrative video (Recommended)** | First frame precision priority, can accept character variance |

**Selection Advice**:
- **Narrative video, both needed → Path A: Kling Omni (Recommended)**
- First frame precision priority, can accept character variance → Path B: Kling + Gemini

---

## Path A: Kling Omni (Recommended)

**Best Practice: Storyboard Image + Character Reference Image Double Reference**

```
Stage 1: Image Prompt → Gemini generates storyboard image (controls scene/style/lighting/atmosphere/color/makeup/costume)
         ↓
Stage 2: Storyboard image + Character reference image → Pass as image_list to Omni → Video
```

**Key Understanding**:
- **Storyboard image** passed via `image_list`, controls overall visual (scene, style, lighting, atmosphere, color, makeup/costume)
- **Character reference image** also passed to `image_list`, ensures character appearance/body consistency
- Omni will synthesize reference from multiple images: storyboard image provides overall visual, character reference image provides character features

### Fast Prototype (No requirements for scene, character makeup consistency)

Only pass character reference image, don't generate storyboard image:

```bash
python video_gen_tools.py video \
  --backend kling-omni \
  --prompt "Character <<<image_1>>> sits by coffee shop window, smiling at the window" \
  --image-list /path/to/person_ref.jpg \
  --audio --output output.mp4
```

### Best Practice (Storyboard Image + Character Reference)

**Step 1**: Generate storyboard image

```bash
python video_gen_tools.py image \
  --prompt "Cinematic realistic start frame.\nReferencing the facial features...\nScene: Men's restroom doorway...\nLighting: Cold white fluorescent..." \
  --reference /path/to/person_ref.jpg \
  --output generated/frames/{shot_id}_frame.png
```

**Step 2**: Pass storyboard image + character reference image together to Omni

```bash
python video_gen_tools.py video \
  --backend kling-omni \
  --prompt "Referencing the composition, characters interact in the scene..." \
  --image-list generated/frames/{shot_id}_frame.png /path/to/person_ref.jpg \
  --audio --output output.mp4
```

**Note**: Image order in `image_list` is important, Omni will synthesize reference from all images. Usually storyboard image first provides overall visual, character reference image later ensures character features.

### Omni Multiple Reference Images + multi_shot

```bash
python video_gen_tools.py video --backend kling-omni \
  --prompt "Story" \
  --image-list frame.png ref1.jpg ref2.jpg \
  --multi-shot --shot-type customize \
  --multi-prompt '[{"index":1,"prompt":"Shot 1","duration":"3"},{"index":2,"prompt":"Shot 2","duration":"4"}]' \
  --duration 7
```

### Omni Mode Storyboard Annotation

```json
{
  "shot_id": "scene1_shot2",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "Xiaomei and Xiaoming converse in coffee shop...",
  "reference_images": [
    "generated/frames/scene1_shot2_frame.png",
    "/path/to/xiaomei_ref.jpg",
    "/path/to/xiaoming_ref.jpg"
  ],
  "frame_strategy": "frame_as_reference"
}
```

---

## Path B: Kling + Gemini First Frame

**Reminder**: Character reference image is **appearance reference image**, only takes facial/body features, **cannot directly use as img2video first frame**. Scene, clothing, posture in character reference image are interference.

```
Character reference image → Gemini generates storyboard image (specifies scene/clothing/posture) → img2video (Kling standard)
```

**Note**: This path uses standard Kling img2video (`--image` first frame), **doesn't use** Omni. First frame scene control is good, but character consistency is worse than Path A.

### Single Character Shot

**Step 1**: Gemini generates storyboard image based on reference image

```bash
python video_gen_tools.py image \
  --prompt "Xiaomei (25-year-old Asian female, long straight black hair, oval face) sits by coffee shop window, looking up smiling, afternoon sunlight, cinematic, 9:16 vertical composition" \
  --reference <reference_image_path> \
  --output generated/storyboard/scene1_shot2_frame.png
```

**Step 2**: Storyboard image as img2video

```bash
python video_gen_tools.py video \
  --image generated/storyboard/scene1_shot2_frame.png \
  --prompt "Xiaomei looks up at server, smiling gently and says: 'It's really quiet here, I like it.'" \
  --backend kling --audio \
  --output generated/videos/scene1_shot2.mp4
```

### Two/Multiple Character Shot

**Step 1**: Gemini multiple reference images merged into one storyboard image (**Reference image order is important, main character later**)

```bash
python video_gen_tools.py image \
  --prompt "Xiaomei and Xiaoming walk side by side on street, warm golden light, 9:16 vertical composition" \
  --reference <secondary_character_ref> <main_character_ref> \
  --output generated/storyboard/scene2_shot1_frame.png
```

**Step 2**: Composite image as img2video

### Kling Path Storyboard Annotation

```json
{
  "shot_id": "scene1_shot2",
  "generation_mode": "img2video",
  "generation_backend": "kling",
  "frame_strategy": "first_frame_only",
  "image_prompt": "Xiaomei sits by coffee shop window, looking up smiling, 9:16 vertical composition",
  "video_prompt": "Xiaomei looks up at server, smiling gently...",
  "reference_personas": ["Xiaomei"]
}
```

---

## Gemini Prompt Notes

Must include:
- Character identity + appearance features (corresponding to reference image)
- Scene description (current storyboard's scene, not reference image scene)
- Clothing description (may differ from reference image)
- Lighting atmosphere
- **Aspect ratio** (9:16 vertical composition)

**Example**:
```
Reference for Xiaomei: MUST preserve exact appearance - 25-year-old Asian female, long straight black hair, oval face
Xiaomei sits by cozy coffee shop window, wearing beige knit sweater, afternoon sunlight streaming through windows,
cinematic tones, shallow depth of field background blur, vertical composition, 9:16 aspect ratio, character centered in frame
```

---

## Degradation Strategy When API Limited

When Kling API encounters 429 (concurrency limit), 402 (insufficient balance), or other unrecoverable errors, need to degrade to Path B.

### Degradation Prerequisites

**Must meet following conditions to degrade**:
1. User explicitly agrees to degrade
2. Degraded backend still available (e.g. Kling official API available but Omni unavailable)
3. Degraded mode can meet basic needs (scene controllable)

### Degradation Path

| Original Mode | Degraded Mode | Backend Change | Capability Change |
|---------------|---------------|----------------|-------------------|
| `omni-video` (kling-omni) | `img2video` (kling) | Omni → Kling | Lose multi-reference ability, character consistency reduced |
| `omni-video` (kling-omni) | `text2video` (kling) | Omni → Kling | Lose character consistency, pure text generation |
| `img2video` (kling) | `text2video` (kling) | No change | Lose first frame control |

**Forbidden Degradation**:
- ❌ `omni-video` → Vidu text2video (Vidu doesn't support image_list)
- ❌ `img2video` → Vidu text2video (Vidu img2video is single image reference, not first frame control)

### Path A → Path B Degradation Flow

When omni-video cannot execute, degrade to Path B (Storyboard image + Kling img2video):

**Step 1: Ask User**
```
Kling Omni API currently unavailable (Reason: 429 concurrency limit / 402 insufficient balance).

Options:
A. Wait and retry (may take longer)
B. Degrade to Path B: First generate storyboard image, then use Kling img2video (character consistency will reduce)
C. Cancel this generation

Please choose:
```

**Step 2: After user chooses B, modify storyboard.json**

Need to modify each shot's fields:

```json
// Original (Path A)
{
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "reference_images": ["Character reference image", "Storyboard image"],
  "frame_strategy": "none"
}

// Degraded (Path B)
{
  "generation_mode": "img2video",
  "generation_backend": "kling",
  "reference_images": [],
  "frame_strategy": "first_frame_only",
  "frame_path": "generated/frames/{shot_id}_frame.png",
  "image_prompt": "..." // Must add, used to generate storyboard image
}
```

**Step 3: Execute Path B**

1. First generate all storyboard images (using Gemini + character reference images)
2. Use storyboard images as first frame to call Kling img2video

### storyboard.json Degradation Modification Details

| Field | Path A (omni-video) | Path B (img2video) |
|-------|---------------------|--------------------|
| `generation_mode` | `omni-video` | `img2video` |
| `generation_backend` | `kling-omni` | `kling` |
| `reference_images` | `[Character ref, Storyboard]` | `[]` (Storyboard passed separately) |
| `frame_strategy` | `none` | `first_frame_only` |
| `frame_path` | None | `generated/frames/{shot_id}_frame.png` |
| `image_prompt` | Optional | **Required** |

**Unchanged Fields**:
- `shot_id`, `duration`, `shot_type`, `description`
- `video_prompt` (may needfine-tuning: remove `<<<image_N>>>` reference)
- `dialogue`, `transition`, `audio`
- `characters` (characters in shot)

### Pre-reserved fallback_plan (Recommended)

When generating storyboard in Phase 3, pre-write degradation plan, avoidtemporary writing `image_prompt`:

```json
{
  "shot_id": "scene1_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "...",
  "reference_images": ["..."],

  "fallback_plan": {
    "mode": "img2video",
    "backend": "kling",
    "image_prompt": "Cinematic realistic start frame.\nScene: ...\nLighting: ...\nStyle: ...",
    "frame_strategy": "first_frame_only",
    "reason": "Fallback when Omni API unavailable"
  }
}
```

When degrading, just switch fields, directly use `fallback_plan.image_prompt`.