# Backend Selection and Reference Image Strategy

## Table of Contents

- Four Backend Capabilities Comparison
- Backend Selection Decision Tree
- Seedance Smart Shot Cutting Mode
- Auto-selection Logic
- Two Paths for Character Reference Images
- **Path A: Kling Omni (Recommended)**
- Path B: Kling + Gemini First Frame
- Gemini Prompt Notes

---

## Four Backend Capabilities Comparison

| Feature | Vidu | Kling | Kling Omni | **Seedance** |
|---------|------|-------|------------|--------------|
| **Backend Name** | `vidu` | `kling` | `kling-omni` | `seedance` |
| **Text-to-video** | 5-10s | 3-15s | 3-15s | **5/10/15s** |
| **Image-to-video** | Single image | First frame image (precise control) | Use image_list instead | Storyboard + reference images |
| **image_list Multiple Reference Images** | -- | -- | `<<<image_1>>>` reference | **`@image1` reference (up to 9 images)** |
| **Smart Shot Cutting** | -- | multi-shot parameter | multi-shot parameter | **Time-segmented prompt auto triggers** |
| **First/Last Frame Control** | -- | `--image` + `--tail-image` | -- | -- (Storyboard as reference) |
| **Audio-Video Together** | -- | `--audio` | `--audio` | **✓ Default audio generation** |
| **Max Resolution** | 1080p | 1080p | 1080p | **720p** ⚠️ |
| **Best Scenario** | Simple fast, fallback | First frame precise control, scene consistency | Character consistency, multi-character | **Fiction/shorts, smart shot cutting** |

**Key Differences**:
- Kling `--image` is **first frame image** (video starts from this image)
- Kling Omni `--image-list` is **reference image** (character stays consistent)
- **Seedance time segments = auto multi-shot**: No extra parameters needed, time-segmented prompt auto triggers smart shot cutting
- **Seedance storyboard image is reference**: Not first frame precise control, but visual style reference

---

## Backend Selection Decision Tree

**Scenario-driven Selection**:

| Scenario | Priority Backend | Fallback Backend | Reason |
|----------|------------------|------------------|--------|
| **Fiction/Shorts** | **Seedance** | Kling-Omni | Smart shot cutting + multi-reference, character consistency |
| **Commercial (No real materials)** | **Seedance** | Kling-Omni | Long shots + smart shot cutting |
| **Commercial (With real materials)** | Kling-3.0 / Vidu | — | First frame precise control, real materials |
| **MV Shorts** | **Seedance** | Kling-Omni | Long shots + music-driven |
| **Vlog/Documentary** | Kling-3.0 | Vidu | First frame precise control, not Seedance |

**First Frame Control Comparison**:

| Backend | First Frame Control | Description |
|---------|---------------------|-------------|
| **Kling-3.0** | ✅ `--image` | Video starts from this image |
| **Vidu** | ✅ `--image` | First frame precise control |
| **Seedance** | ❌ Reference image | Storyboard is visual style reference, not first frame |
| **Kling-Omni** | ❌ Reference image | Only reference2video, no img2video |

**Core Principles**:
1. **Need smart shot cutting → Seedance** (Time segments auto trigger multi-shot)
2. **Need first frame control → Kling/Vidu** (Only these two support it)
3. **Seedance fails → Degrade to Kling-Omni** (Lose smart shot cutting, keep character consistency)

### Scenario Quick Reference

| Scenario | Backend | Key Parameters |
|----------|---------|----------------|
| **Fiction/Shorts** | **Seedance** | `--backend seedance --image-list frame.png ref.jpg` |
| **Commercial (No real materials)** | **Seedance** | Time-segmented prompt + storyboard image |
| **Commercial (With real materials)** | Kling-3.0 | `--image first_frame.png` |
| **MV Shorts** | **Seedance** | Time-segmented prompt + storyboard image |
| **Vlog/Documentary** | Kling-3.0 | `--image first_frame.png` |
| Need first/last frame animation | Kling | `--image first.png --tail-image last.png` |
| Simple non-character scene / Fast prototype | Kling (default) or vidu | No special parameters needed |

---

## Seedance Smart Shot Cutting Mode

**Core Feature**: Time-segmented prompt auto triggers multi-shot smart shot cutting, no extra parameters needed.

### API Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `model` | `"seedance"` | Fixed value |
| `task_type` | `"seedance-2-fast-preview"` / `"seedance-2-preview"` | Fast / High quality |
| `prompt` | Text description | Supports `@imageN` image reference, supports time segments |
| `duration` | 5 / 10 / 15 | Seconds (only these three enum values) |
| `aspect_ratio` | 16:9/9:16/4:3/3:4 | Four ratios |
| `image_urls` | Array | Up to 9 reference images |

### Output Specifications

| Spec | Value |
|------|-------|
| Duration | 5/10/15s (only three enum values) |
| Resolution | 480p / 720p (max 720p) ⚠️ |
| Audio | Auto generated (AAC stereo) |

### Time-segmented Prompt Syntax

**Format**:
```
Referencing the {segment_id}_frame composition for scene layout and character positioning.

@image1 (character reference image), [viewpoint setting] [theme/style];

Overall: [Shot overall action summary]

Segmented actions ({duration}s):
0-Xs: [Scene] + [Action] + [Camera] + [Rhythm] + [Sound/Dialogue];
X-Xs: [Cut] + [Scene] + [Action] + [Camera] + [Rhythm] + [Sound/Dialogue];
...

Maintain {aspect_ratio} composition, don't break aspect ratio
{BGM constraint}
```

**Example**:
```
Referencing the scene_1_seg_1_frame composition for scene layout and character positioning.

@image1, first-person view fruit tea commercial; Element_Chuyue as female character;

Overall: First-person view showing fruit tea making process, from picking apples to final product, natural smooth.

Segmented actions (10s):
0-2s: Your hand picks a dewy Aksu red apple, fixed shot, steady rhythm, crisp apple collision sound;
2-4s: Quick cut, your hand puts apple chunks into shaker, adds ice and tea base, shakes hard, shot lightly follows, brisk rhythm, ice collision sound hits beat;
4-6s: First-person product closeup, layered fruit tea pours into transparent cup, your hand gently squeezes milk cap, shot slowly pushes, steady rhythm, liquid flowing sound;
6-8s: Shot pushes in, cup gets pink label, shows layered texture, soothing rhythm, soft background sound;
8-10s: First-person holding cup, @image2, fruit tea raised to camera, fixed shot, steady rhythm, cup label clearly visible, background sound: 'Have a sip of freshness';

Maintain horizontal 16:9 composition, don't break aspect ratio
Background sound: 'Fresh cut and shaken', 'Have a sip of freshness', female voice tone.
```

### image_urls Order Convention

| index | Usage | Reference Method |
|-------|-------|------------------|
| `image_urls[0]` | Storyboard image | `Referencing the {segment_id}_frame composition...` |
| `image_urls[1]` | Character reference 1 | `@image1` |
| `image_urls[2]` | Character reference 2 | `@image2` |
| ... | ... | ... |
| `image_urls[9]` | Character reference 9 (max) | `@image9` |

**Key Points**:
1. **Storyboard is reference, not first frame precise control** — Provides overall visual style reference
2. **Character reference uses `<<<image_N>>>` syntax** — Unified with Kling-Omni syntax
3. **Time segments auto trigger smart shot cutting** — No `--multi-shot` parameter needed
4. **Max 720p** — Need 1080p use Kling or Vidu

### CLI Usage Example

```bash
# Text-to-Video (pure text generation)
python video_gen_tools.py video \
  --backend seedance \
  --prompt "Time-segmented description..." \
  --duration 10 \
  --aspect-ratio 16:9 \
  --output output.mp4

# Image-to-Video (Storyboard + character reference)
python video_gen_tools.py video \
  --backend seedance \
  --prompt "Referencing the composition... @image1..." \
  --image-list generated/frames/scene1_frame.png materials/personas/xiaomei_ref.jpg \
  --duration 10 \
  --output output.mp4
```

### Recommended Scenarios

| Scenario | Priority Backend | Fallback Backend | Reason |
|----------|------------------|------------------|--------|
| **Fiction/Shorts** | **Seedance** | Kling-Omni | Smart shot cutting + multi-reference, character consistency |
| **Commercial (No real materials)** | **Seedance** | Kling-Omni | Long shots + smart shot cutting |
| **Commercial (With real materials)** | Kling-3.0 / Vidu | — | First frame precise control, real materials |
| **MV Shorts** | **Seedance** | Kling-Omni | Long shots + music-driven |
| **Vlog/Documentary** | Kling-3.0 | Vidu | First frame precise control, not Seedance |
| **Ultra short shots (< 5s)** | Kling / Vidu | — | Seedance min 5s |

---

## Auto-selection Logic

Default uses **kling** when `--backend` not specified. Special parameters force backend switch:
- Provide `--image-list` → No forced switch (both kling-omni and seedance support)
- Provide `--tail-image` → Keep kling (only one that supports)
- Need fast fallback → Manually specify `--backend vidu`

### Provider Selection Priority

When `--provider` is not specified, auto-selection follows this priority:

| Condition | Provider | Description |
|-----------|----------|-------------|
| Has KLING_ACCESS_KEY + KLING_SECRET_KEY | `official` | Kling official API |
| Has FAL_API_KEY | `fal` | fal.ai proxy |
| Has YUNWU_API_KEY | `yunwu` | yunwu.ai proxy |

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
  "video_prompt": "Emma and Alex converse in coffee shop...",
  "reference_images": [
    "generated/frames/scene1_shot2_frame.png",
    "/path/to/emma_ref.jpg",
    "/path/to/alex_ref.jpg"
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
  --prompt "Emma (25-year-old Asian female, long straight black hair, oval face) sits by coffee shop window, looking up smiling, afternoon sunlight, cinematic, 9:16 vertical composition" \
  --reference <reference_image_path> \
  --output generated/storyboard/scene1_shot2_frame.png
```

**Step 2**: Storyboard image as img2video

```bash
python video_gen_tools.py video \
  --image generated/storyboard/scene1_shot2_frame.png \
  --prompt "Emma looks up at server, smiling gently and says: 'It's really quiet here, I like it.'" \
  --backend kling --audio \
  --output generated/videos/scene1_shot2.mp4
```

### Two/Multiple Character Shot

**Step 1**: Gemini multiple reference images merged into one storyboard image (**Reference image order is important, main character later**)

```bash
python video_gen_tools.py image \
  --prompt "Emma and Alex walk side by side on street, warm golden light, 9:16 vertical composition" \
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
  "image_prompt": "Emma sits by coffee shop window, looking up smiling, 9:16 vertical composition",
  "video_prompt": "Emma looks up at server, smiling gently...",
  "reference_personas": ["Emma"]
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
Reference for Emma: MUST preserve exact appearance - 25-year-old Asian female, long straight black hair, oval face
Emma sits by cozy coffee shop window, wearing beige knit sweater, afternoon sunlight streaming through windows,
cinematic tones, shallow depth of field background blur, vertical composition, 9:16 aspect ratio, character centered in frame
```

---

## Degradation Strategy When API Limited

When API encounters 429 (concurrency limit), 402 (insufficient balance), timeout, or other unrecoverable errors, need to degrade.

### Degradation Prerequisites

**Must meet following conditions to degrade**:
1. Already retried once and still fails (Seedance timeout needs to wait 10 minutes)
2. User explicitly agrees to degrade
3. Degraded backend still available

### Degradation Path

| Original Mode | Degraded Mode | Backend Change | Capability Change |
|---------------|---------------|----------------|-------------------|
| `seedance-video` | `omni-video` (kling-omni) | Seedance → Kling-Omni | Lose smart shot cutting, need manual multi-shot |
| `omni-video` (kling-omni) | `img2video` (kling) | Omni → Kling | Lose multi-reference ability, character consistency reduced |
| `img2video` (kling) | `text2video` (kling) | No change | Lose first frame control |

**Forbidden Degradation**:
- ❌ `seedance-video` → Vidu text2video (Vidu doesn't support image_list)
- ❌ `omni-video` → Vidu text2video (Vidu doesn't support image_list)

### Seedance → Kling-Omni Degradation Flow

When Seedance times out or fails, degrade to Kling-Omni:

**Step 1: Ask User**
```
Seedance generation failed (already retried once).

Options:
A. Degrade to Kling-Omni (lose smart shot cutting, need manual multi-shot)
B. Modify prompt and retry Seedance
C. Cancel this generation

Please choose:
```

**Step 2: After user chooses A, modify storyboard.json**

```json
// Original (Seedance)
{
  "generation_mode": "seedance-video",
  "generation_backend": "seedance",
  "reference_images": ["Storyboard image", "Character reference 1", "Character reference 2"]
}

// Degraded (Kling-Omni)
{
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "reference_images": ["Character reference 1", "Character reference 2"]
}
```

**Step 3: Execute Kling-Omni**

- Provider auto-selects by priority: official → fal → yunwu
- Each shot calls API separately (no merging)
- Keep character reference images, maintain character consistency

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