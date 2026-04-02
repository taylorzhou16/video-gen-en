# Prompt Writing and Consistency Specifications

## Table of Contents

1. [Basic Concepts](#basic-concepts) — Character registration naming standards, data sources, reference methods
2. [Image Generation Prompt](#image-generation-prompt) — Storyboard image (Gemini)
3. [Kling/Vidu Video Generation Prompt](#klingvidu-video-generation-prompt) — General structure (Kling-v3/Vidu)
4. [Kling-Omni Two-stage Process Prompt](#kling-omni-two-stage-process-prompt) — Storyboard image + Video generation Prompt (Kling-v3-Omni)
5. [Consistency Standards](#consistency-standards) — Character, prop cross-shot consistency
6. [Aspect Ratio Constraints](#aspect-ratio-constraints) — Frame aspect ratio mandatory requirements
7. [Dialogue and Audio](#dialogue-and-audio) — Sync sound, TTS, BGM constraints
8. [Appendix: Quick Templates](#appendix-quick-templates) — Common template summary

---

## Basic Concepts

### Character Registration Naming Standards

| Level | Purpose | Naming Convention | Example |
|-------|---------|-------------------|---------|
| **Element ID** | Technical ID, character identifier in JSON/Prompt | `Element_` + English name/Pinyin | `Element_Chuyue` |
| **Display Name** | Display name, for user interaction, Chinese description | Chinese name | `Chuyue` |
| **Reference Tag** | Image placeholder in Prompt | `<<<image_N>>>` | `<<<image_1>>>`, `<<<image_2>>>` |

### Single Data Source

Character information unified storage in `storyboard.json`:

```json
{
  "elements": {
    "characters": [
      {
        "element_id": "Element_Chuyue",
        "name": "Chuyue",
        "reference_images": ["/path/to/ref.jpg"],
        "visual_description": "25-year-old Asian female, long straight black hair..."
      }
    ]
  },
  "character_image_mapping": {
    "Element_Chuyue": "image_1"
  }
}
```

### Reference Methods in Prompt

| Reference Type | Writing | Purpose |
|----------------|---------|---------|
| Appearance reference | `<<<image_1>>>` / `<<<image_2>>>` | Ensures character appearance stable |
| Storyboard image reference | `Shot_XXX_frame` | Ensures scene layout, character position |
| Character identifier | `Element_Chuyue` | Character identifier in Motion sequence |

---

## Image Generation Prompt

Used for Gemini to generate storyboard images (Storyboard Frame).

### Five-element Structure

1. **Scene**: Time, location, environment
2. **Subject**: Character appearance, clothing, posture
3. **Lighting**: Light direction, color temperature, atmosphere
4. **Style**: cinematic / realistic / anime
5. **Ratio**: Vertical 9:16 / Horizontal 16:9 / Square 1:1

### Basic Template

```
Cinematic realistic start frame.

Scene: {Specific scene description}
Location details: {Environment details}

{Character appearance detailed description}, {posture}, {expression}, {position}

Shot scale: {wide/medium/close-up}
Camera angle: {eye-level/high/low}
Lighting: {Lighting description}
Color grade: {Color tone}
Aspect ratio: {Aspect ratio}

Style: {cinematic realistic/film grain/etc.}
```

### Complete Example

```
Cinematic realistic start frame.

Scene: A wide three-person shot inside the men's restroom at the doorway
Location details: white tiles, sink and mirror visible, door frame as divider

A 25-year-old Asian woman with long black hair, wearing light grey blazer,
stands in doorway, hands raised in flustered waving gesture, forced apologetic smile

Shot scale: Wide/Full shot
Camera angle: Eye-level, frontal
Lighting: Cold white fluorescent overhead lighting
Color grade: Cool blue-white

Style: Cinematic realistic, film grain, shallow depth of field, 16:9 aspect ratio
```

---

## Kling/Vidu Video Generation Prompt

Used for Kling-v3/Vidu video generation.

### Structure Elements (in order)

1. **Overall Action Summary** — Briefly describe overall shot action
2. **Segmented Actions** — By timeline: 0-2s, 2-5s...
3. **Camera Movement** — Push/pull/pan/tilt/track/crane
4. **Motion Rhythm** — Slow/steady/fast/urgent
5. **Frame Stability** — Keep stable/Slight shake
6. **Dialogue Information** — Character, content, emotion, speaking rate
7. **Aspect Ratio Protection** — "Keep XX aspect ratio composition"
8. **BGM Constraint** — Based on audio.no_bgm decision

### Basic Template

```
Overall: {Shot overall action description}

Segmented actions ({duration}s):
{time_range_1}: {Action description}
{time_range_2}: {Action description + dialogue sync}
...

Camera movement: {Camera movement description}
Rhythm: {Motion rhythm}
Frame stability: {Keep stable/Slight shake}
{Dialogue information}
Keep {aspect ratio} composition, maintain aspect ratio
{BGM constraint}
```

### Complete Example (5-second shot)

```
Overall: Female protagonist looks up from contemplation toward the window,corner of mouth gradually rising, revealing gentle smile.

Segmented actions (5 seconds):
0-2s: Female protagonist profile to camera, gazing out window, expression calm
2-4s: Female protagonistcorner of mouthslightly raised, gaze becomes soft
4-5s: Female protagonist fully turns around, facing camera with natural smile

Camera movement: Camera slowly pushes in, keep stable
Rhythm: Slow and smooth
Frame stability: Keep stable
Dialogue: Female protagonist says gently, "This is my favorite place." Clear voice, moderate pace.
Keep 9:16 vertical composition, character always centered in frame, maintain aspect ratio
No background music. Natural ambient sound only.
```

---

## V3-Omni Two-stage Process

For Kling V3-Omni's **storyboard image + video** two-stage generation.

### Process Overview

```
Stage 1: Image Prompt → Gemini generates storyboard image (controls scene/style)
         ↓
Stage 2: Storyboard image + Character reference image → Omni video generation (maintains character consistency)
```

### Stage 1: Image Prompt (Storyboard Image)

**Key**: Must include character reference (image_N), use `Element_XXX` identifier

```
Cinematic realistic start frame.

Referencing the facial features, face shape, skin tone, and clothing details of:
- image_1: Element_Chuyue, young Asian woman, long black hair, delicate features, wearing light grey blazer
- image_2: Element_Jiazhi, mature man, short hair, deep eyes, wearing black shirt

Scene: {Scene description}
Location details: {Environment details}

Element_Chuyue: {Posture}, {expression}, {position}
Element_Jiazhi: {Posture}, {expression}, {position}

Shot scale: {wide/medium/close-up}
Camera angle: {eye-level/high/low}
Lighting: {Lighting description}
Color grade: {Color tone}
Aspect ratio: {Aspect ratio}

Style: Cinematic realistic, film grain
```

### Stage 2: Video Prompt (Omni Video)

**Key**: Double reference (Element_XXX + image_N), reference storyboard image to control layout

```
Referencing the {frame_name} composition for scene layout and character positioning.

Element_{Name}'s appearance from {image_N} (facial features, hairstyle, outfit),
positioned as shown in {frame_name}.

Overall: {Overall action description}

Motion sequence ({duration}s):
{time_range_1}: Element_{Name} {action}{, with lip-synced dialogue}
{time_range_2}: {action}

Dialogue exchange:
- Element_{Name} ({emotion}): "{line}"

Camera movement: {static/pan/tracking/etc.}
Sound effects: {Ambient sound description}

Style: Cinematic realistic style. No music, no subtitles.
```

### Two-stage Key Points

| Stage | Key Requirements |
|-------|------------------|
| **Image** | Must include character reference (image_1, image_2), use Element_XXX identifier |
| **Image** | Must include aspect ratio (16:9 / 9:16) |
| **Image** | Scene, lighting, camera parameters need detail |
| **Video** | Must reference storyboard image (Referencing XXX_frame composition) |
| **Video** | Try to use double reference: Element_XXX (character) + image_N (appearance) |
| **Video** | Actions must be segmented description (0-2s, 2-5s...) |
| **Video** | Dialogue mustmarked with emotion and lip-sync |

---

## Consistency Standards

### Character Consistency

**Every shot containing characters, prompt must include**:

1. **Character Identity Identifier** — `Element_Chuyue`
2. **Appearance Features** — Gender, age, hairstyle, facial features, body type, signature features
3. **Clothing Description** — Style, color, material, accessories

**Omni Mode Special Requirements**:
- Image Prompt uses `<<<image_1>>>`, `<<<image_2>>>` to reference appearance
- Video Prompt uses `Element_XXX` + `<<<image_N>>>` double reference

### Prop Consistency

Cross-shot recurring important props:

1. **Establish Material List** — storyboard's `props` field
2. **Complete Description Per Shot** — prompt includes prop features
3. **Key Prop Types** — Brand Logo, product appearance, plot key items

---

## Aspect Ratio Constraints

### Text-to-image Prompt

| Ratio | Required Text |
|-------|---------------|
| 9:16 | "Vertical composition, 9:16 aspect ratio, character/subject centered in frame" |
| 16:9 | "Horizontal composition, 16:9 aspect ratio" |
| 1:1 | "Square composition, 1:1 aspect ratio, subject centered" |

### Image-to-video / Text-to-video

- All video_prompt must ensure camera movement doesn'tbreak original aspect ratio
- 9:16 vertical: Avoid camera movement descriptions that would make frame horizontal
- **All video generation modes must pass aspect ratio via CLI `--aspect-ratio` parameter**
- Parameter value read from `storyboard.json`'s `aspect_ratio` field

---

## Dialogue and Audio

### Sync Sound vs TTS

| Type | Generation Method | Applicable Scenario |
|------|-------------------|---------------------|
| Sync sound | Video generation model (`audio.enabled: true`) | Character dialogue, character monologue |
| TTS Narration | TTS post-production dubbing | Opening/closing narration, scene description |

**Core Principle**: For shots that can capture sync sound, don't use TTS!

### TTS Narration Generation Process

**Trigger Condition**: `storyboard.json` has `narration_segments` field.

**Data Sources**:
- `narration_config.voice_style` → Maps to TTS voice and emotion parameters
- `narration_segments[].text` → TTS --text parameter
- `narration_segments[].segment_id` → Output file naming

**CLI Call Example**:

```bash
# Generate each narration segment separately
python video_gen_tools.py tts \
  --text "This is a peaceful afternoon, sunlight streams through floor-to-ceiling windows into the coffee shop..." \
  --voice female_narrator \
  --emotion gentle \
  --output generated/narration/narr_1.mp3
```

**voice Parameter (Volcano Engine TTS Voices)**:

| Parameter Value | Voice Description | Volcano Engine ID |
|-----------------|-------------------|-------------------|
| `female_narrator` | Female narrator, professional and steady | BV700_streaming |
| `female_gentle` | Female voice gentle, soft and friendly | BV034_streaming |
| `male_narrator` | Male narrator, professional and steady | BV701_streaming |
| `male_warm` | Male voice warm, magnetic and friendly | BV033_streaming |

**emotion Parameter (Optional)**:

| Parameter Value | Emotion Style |
|-----------------|---------------|
| `neutral` | Neutral (default) |
| `happy` | Happy |
| `sad` | Sad |
| `gentle` | Gentle |
| `serious` | Serious |

**narration_config.voice_style Mapping Rules**:

User-specified voice_style in Phase 2 (e.g. "Gentle female voice") maps to specific TTS parameters in Phase 3:
- "Gentle female voice" → `voice: female_gentle, emotion: gentle`
- "Professional female narrator" → `voice: female_narrator, emotion: neutral`
- "Magnetic male voice" → `voice: male_warm, emotion: neutral`
- "Serious male voice" → `voice: male_narrator, emotion: serious`

**Important**: Use same voice + emotion parameters within one video to ensure unified narration style.

### BGM Constraint

**Mapping between `audio` field in storyboard.json and API parameters**:

| Storyboard Field | API Parameter | Description |
|------------------|---------------|-------------|
| `audio.no_bgm = true` | Add `"No background music. Natural ambient sound only."` at prompt end | BGM by post-production mix |
| `audio.no_bgm = false` | No additional constraint | Video modelfreely decides whether to generate BGM |
| `audio.enabled = true` | `sound: "on"` | Generate ambient sound/dialogue |
| `audio.enabled = false` | `sound: "off"` | Silent output |

**Note**: Don't separately write Sound effects, let model automatically generate ambient sound based on visual content (e.g. car engine sound, keyboard typing, wind sound etc.).

### Dialogue Integration in Prompt

When shot contains dialogue, must fully describe in video_prompt: character (including appearance), dialogue content (in quotes), expression/emotion, voice quality and speaking rate.

```
Female protagonist (25-year-old Asian female, long straight black hair) looks up at server,
smiling gently and says, "It's really quiet here, I like it."
Clear pleasant voice, moderate pace.
```

---

## Appendix: Quick Templates

### Image Prompt Template (Omni Storyboard Image)

```
Cinematic realistic start frame.

Referencing the facial features, face shape, skin tone, and clothing details of:
- image_1: Element_{Name}, {Appearance detailed description}

Scene: {Scene description}
Location details: {Environment details}

Element_{Name}: {Posture}, {expression}, {position}

Shot scale: {wide/medium/close-up}
Camera angle: {eye-level/high/low}
Lighting: {Lighting description}
Color grade: {Color tone}
Aspect ratio: {Aspect ratio}

Style: Cinematic realistic, film grain, shallow depth of field
```

### Video Prompt Template (Omni Video)

```
Referencing the {frame_name} composition for scene layout and character positioning.

Element_{Name}'s appearance from {image_N} ({Appearance reference}),
positioned as shown in {frame_name}.

Overall: {Overall action description}

Motion sequence ({duration}s):
{time_range}: Element_{Name} {action}{, with lip-synced dialogue}

Dialogue exchange:
- Element_{Name} ({emotion}): "{line}"

Camera movement: {static/pan/tracking/etc.}
Sound effects: {Sound design}

Style: Cinematic realistic style. No music, no subtitles.
```

### Video Prompt Template (Standard Kling, No Omni)

```
Overall: {Shot overall action description}

Segmented actions ({duration}s):
{time_range_1}: {Action description}
{time_range_2}: {Action description + dialogue sync}

Camera movement: {Camera movement description}
Rhythm: {Motion rhythm}
Frame stability: {Keep stable/Slight shake}
{Dialogue information}
Keep {aspect ratio} composition, maintain aspect ratio
{BGM constraint}
```