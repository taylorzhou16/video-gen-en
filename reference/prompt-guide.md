# Prompt Writing and Consistency Guidelines

## Table of Contents

1. [Basic Concepts](#basic-concepts) — Character registration naming standards, data sources, reference methods
2. [Image Generation Prompt] — Storyboard frames (Gemini)
3. [Kling/Vidu Video Generation Prompt] — General structure (Kling-v3/Vidu)
4. [Kling-Omni Two-Stage Workflow Prompt] — Storyboard frame + Video generation Prompt (Kling-v3-Omni)
5. [Consistency Guidelines](#consistency-guidelines) — Character and prop consistency across shots
6. [Aspect Ratio Constraints](#aspect-ratio-constraints) — Aspect ratio requirements
7. [Dialogue and Audio](#dialogue-and-audio) — Sync sound, TTS, BGM constraints
8. [Appendix: Quick Templates](#appendix-quick-templates) — Common templates summary

---

## Basic Concepts

### Character Registration Naming Standards

| Level | Purpose | Naming Convention | Example |
|------|---------|------------------|---------|
| **Element ID** | Technical ID, character identifier in JSON/Prompt | `Element_` + English name/Pinyin | `Element_Chuyue` |
| **Display Name** | Display name for user interaction, Chinese description | Character name | `Chuyue` |
| **Reference Tag** | Image placeholder in Prompt | `<<<image_N>>>` | `<<<image_1>>>`, `<<<image_2>>>` |

### Single Data Source

Character information is stored uniformly in `storyboard.json`:

```json
{
  "elements": {
    "characters": [
      {
        "element_id": "Element_Chuyue",
        "name": "Chuyue",
        "reference_images": ["/path/to/ref.jpg"],
        "visual_description": "25-year-old Asian woman, long black straight hair..."
      }
    ]
  },
  "character_image_mapping": {
    "Element_Chuyue": "image_1"
  }
}
```

### Reference Methods in Prompts

| Reference Type | Syntax | Purpose |
|---------|------|------|
| Appearance Reference | `<<<image_1>>>` / `<<<image_2>>>` | Ensure consistent character appearance |
| Storyboard Frame Reference | `Shot_XXX_frame` | Ensure scene layout and character positioning |
| Character Identifier | `Element_Chuyue` | Character identifier in motion sequence |

---

## Image Generation Prompt

Used for Gemini to generate storyboard frames.

### Five Key Elements Structure

1. **Scene**: Time, location, environment
2. **Subject**: Character appearance, clothing, pose
3. **Lighting**: Light direction, color temperature, atmosphere
4. **Style**: cinematic / realistic / anime
5. **Aspect Ratio**: Portrait 9:16 / Landscape 16:9 / Square 1:1

### Force Style Keywords Based on visual_style (Important)

**Must force style keywords at the beginning of image_prompt to avoid Gemini generating wrong style!**

Read the `visual_style` field from `creative.json`:

| visual_style | Forced Opening Syntax | Style Line Syntax |
|--------------|----------------------|-------------------|
| `realistic` (Photorealistic) | `**PHOTOREALISTIC real human start frame. NOT ANIME, NOT CARTOON, NOT ILLUSTRATION.**` | `Style: PHOTOREALISTIC, real human actress, actual skin texture, cinematic film grain, shallow depth of field` |
| `anime` (Animation) | `Anime style 2D animation start frame.` | `Style: Anime style, 2D animation, cel shading, vibrant colors` |
| `mixed` (Mixed) | Differentiate by scene, use realistic syntax for live-action scenes, anime syntax for animated scenes | Same as above |

**Wrong Example (will cause anime style)**:
```
Wrong: Cinematic realistic start frame.
Wrong: Style: cinematic realistic  <- Gemini may interpret as "cinematic anime"
```

**Correct Example (Photorealistic)**:
```
Correct: PHOTOREALISTIC real human start frame. NOT ANIME, NOT CARTOON.
Correct: Style: PHOTOREALISTIC, real human actress, actual skin texture, cinematic film grain
```

### Basic Template (visual_style = realistic)

```
PHOTOREALISTIC real human start frame. NOT ANIME, NOT CARTOON, NOT ILLUSTRATION.

Scene: {specific scene description}
Location details: {environment details}

{detailed character appearance description}, {pose}, {expression}, {position}

Shot scale: {wide/medium/close-up}
Camera angle: {eye-level/high/low}
Lighting: {lighting description}
Color grade: {color tone}
Aspect ratio: {aspect ratio}

Style: PHOTOREALISTIC, real human actress, actual skin texture, cinematic film grain, shallow depth of field
```

### Basic Template (visual_style = anime)

```
Anime style 2D animation start frame.

Scene: {specific scene description}
Location details: {environment details}

{detailed character appearance description}, {pose}, {expression}, {position}

Shot scale: {wide/medium/close-up}
Camera angle: {eye-level/high/low}
Lighting: {lighting description}
Color grade: {color tone}
Aspect ratio: {aspect ratio}

Style: Anime style, 2D animation, cel shading, vibrant colors
```

### Complete Example (realistic)

```
PHOTOREALISTIC real human start frame. NOT ANIME, NOT CARTOON, NOT ILLUSTRATION.

Scene: A wide three-person shot inside the men's restroom at the doorway
Location details: white tiles, sink and mirror visible, door frame as divider

A 25-year-old Asian woman with long black hair, wearing light grey blazer,
stands in doorway, hands raised in flustered waving gesture, forced apologetic smile

Shot scale: Wide/Full shot
Camera angle: Eye-level, frontal
Lighting: Cold white fluorescent overhead lighting
Color grade: Cool blue-white

Style: PHOTOREALISTIC, real human actress, actual skin texture, cinematic film grain, shallow depth of field, 16:9 aspect ratio
```

---

## Kling/Vidu Video Generation Prompt

Used for Kling-v3/Vidu video generation.

### Structure Elements (in order)

1. **Overall Action Summary** — Briefly describe the overall shot action
2. **Segmented Actions** — Timeline: 0-2s, 2-5s...
3. **Camera Movement** — Push/Pull/Pan/Tilt/Track/Crane
4. **Motion Rhythm** — Slow/Steady/Fast/Urgent
5. **Frame Stability** — Keep stable / Slight shake
6. **Dialogue Information** — Character, content, emotion, speech rate
7. **Aspect Ratio Protection** — "Maintain XX aspect ratio composition"
8. **BGM Constraint** — Based on audio.no_bgm setting

### Basic Template

```
Overall: {overall shot action description}

Segmented actions ({duration}s):
{time_range_1}: {action description}
{time_range_2}: {action description + dialogue sync}
...

Camera movement: {camera movement description}
Rhythm: {motion rhythm}
Frame stability: {keep stable/slight shake}
{dialogue information}
Maintain {ratio} composition, do not break aspect ratio
{BGM constraint}
```

### Complete Example (5-second shot)

```
Overall: The heroine looks up from contemplation toward the window, lips gradually curving into a gentle smile.

Segmented actions (5s):
0-2s: Heroine in profile facing camera, gazing out the window, expression calm
2-4s: Heroine's lips slightly curve upward, eyes become softer
4-5s: Heroine fully turns around, facing camera with a natural smile

Camera movement: Camera slowly pushes in, remains stable
Rhythm: Slow and steady
Frame stability: Keep stable
Dialogue: Heroine says gently: "This is my favorite place." Voice clear, moderate to slow pace.
Maintain vertical 9:16 composition, character always in center of frame, do not break aspect ratio
No background music. Natural ambient sound only.
```

---

## V3-Omni Two-Stage Workflow

For Kling V3-Omni **storyboard frame + video** two-stage generation.

### Workflow Overview

```
Stage 1: Image Prompt → Gemini generates storyboard frame (controls scene/style)
         ↓
Stage 2: Storyboard frame + Character reference image → Omni video generation (maintains character consistency)
```

### Stage 1: Image Prompt (Storyboard Frame)

**Key**: Must include character references (image_N), use `Element_XXX` identifier

```
Cinematic realistic start frame.

Referencing the facial features, face shape, skin tone, and clothing details of:
- image_1: Element_Chuyue, young Asian woman, long black hair, delicate features, wearing light grey blazer
- image_2: Element_Jiazhi, mature man, short hair, deep eyes, wearing black shirt

Scene: {scene description}
Location details: {environment details}

Element_Chuyue: {pose}, {expression}, {position}
Element_Jiazhi: {pose}, {expression}, {position}

Shot scale: {wide/medium/close-up}
Camera angle: {eye-level/high/low}
Lighting: {lighting description}
Color grade: {color tone}
Aspect ratio: {aspect ratio}

Style: Cinematic realistic, film grain
```

### Stage 2: Video Prompt (Omni Video)

**Key**: Dual reference (Element_XXX + image_N), reference storyboard frame to control layout

```
Referencing the {frame_name} composition for scene layout and character positioning.

Element_{Name}'s appearance from {image_N} (facial features, hairstyle, outfit),
positioned as shown in {frame_name}.

Overall: {overall action description}

Motion sequence ({duration}s):
{time_range_1}: Element_{Name} {action}{, with lip-synced dialogue}
{time_range_2}: {action}

Dialogue exchange:
- Element_{Name} ({emotion}): "{line}"

Camera movement: {static/pan/tracking/etc.}
Sound effects: {ambient sound description}

Style: Cinematic realistic style. No music, no subtitles.
```

### Two-Stage Key Points

| Stage | Key Requirements |
|------|-----------------|
| **Image** | Must include character references (image_1, image_2), use Element_XXX identifier |
| **Image** | Must include aspect ratio (16:9 / 9:16) |
| **Image** | Scene, lighting, camera parameters should be detailed |
| **Video** | Must reference storyboard frame (Referencing XXX_frame composition) |
| **Video** | Prefer dual reference: Element_XXX (character) + image_N (appearance) |
| **Video** | Actions must be segmented (0-2s, 2-5s...) |
| **Video** | Dialogue must include emotion and lip-sync annotation |

---

## Consistency Guidelines

### Character Consistency

**Every shot containing characters must include in prompt**:

1. **Character Identity Identifier** — `Element_Chuyue`
2. **Appearance Features** — Gender, age, hairstyle, facial features, body type, distinctive features
3. **Clothing Description** — Style, color, material, accessories

**Omni Mode Special Requirements**:
- Image Prompt uses `<<<image_1>>>`, `<<<image_2>>>` to reference appearance
- Video Prompt uses `Element_XXX` + `<<<image_N>>>` dual reference

### Prop Consistency

For important props that appear repeatedly across shots:

1. **Build Material List** — `props` field in storyboard
2. **Complete Description per Shot** — Include prop features in prompt
3. **Key Prop Types** — Brand logos, product appearance, plot-critical items

---

## Aspect Ratio Constraints

### Text-to-Image Prompt

| Aspect Ratio | Required Text |
|------|---------------|
| 9:16 | "Portrait composition, 9:16 aspect ratio, character/subject in center of frame" |
| 16:9 | "Landscape composition, 16:9 aspect ratio" |
| 1:1 | "Square composition, 1:1 aspect ratio, subject centered" |

### Image-to-Video / Text-to-Video

- All video_prompt must ensure camera movement doesn't break the original aspect ratio
- 9:16 portrait: Avoid camera movement descriptions that would make the frame landscape
- **All video generation modes must pass aspect ratio via CLI `--aspect-ratio` parameter**
- Parameter value is read from `aspect_ratio` field in `storyboard.json`

---

## Dialogue and Audio

### Sync Sound vs TTS

| Type | Generation Method | Use Case |
|------|------------------|----------|
| Sync Sound | Video generation model (`audio.enabled: true`) | Character dialogue, character monologue |
| TTS Narration | TTS post-production dubbing | Opening/closing narration, scene description |

**Core Principle**: For shots where sync sound can be captured, do not use TTS!

### TTS Narration Generation Workflow

**Trigger Condition**: `storyboard.json` contains `narration_segments` field.

**Data Sources**:
- `narration_config.voice_style` → Maps to TTS voice and emotion parameters
- `narration_segments[].text` → TTS --text parameter
- `narration_segments[].segment_id` → Output file naming

**CLI Call Example**:

```bash
# Generate each narration segment separately
python video_gen_tools.py tts \
  --text "This is a peaceful afternoon, sunlight streaming through the floor-to-ceiling windows into the cafe..." \
  --voice female_narrator \
  --emotion gentle \
  --output generated/narration/narr_1.mp3
```

**voice Parameters (Volcano Engine TTS Voices)**:

| Parameter Value | Voice Description | Volcano Engine ID |
|-------|----------------|-------------------|
| `female_narrator` | Female narration, professional and steady | BV700_streaming |
| `female_gentle` | Female gentle, soft and friendly | BV034_streaming |
| `male_narrator` | Male narration, professional and steady | BV701_streaming |
| `male_warm` | Male warm, magnetic and friendly | BV033_streaming |

**emotion Parameters (Optional)**:

| Parameter Value | Emotion Style |
|-------|-------------|
| `neutral` | Neutral (default) |
| `happy` | Happy |
| `sad` | Sad |
| `gentle` | Gentle |
| `serious` | Serious |

**narration_config.voice_style Mapping Rules**:

The voice_style specified by user in Phase 2 (e.g., "gentle female voice") is mapped to specific TTS parameters in Phase 3:
- "gentle female voice" → `voice: female_gentle, emotion: gentle`
- "professional female narrator" → `voice: female_narrator, emotion: neutral`
- "magnetic male voice" → `voice: male_warm, emotion: neutral`
- "serious male voice" → `voice: male_narrator, emotion: serious`

**Important**: Use the same voice + emotion parameters within one video to ensure consistent narration style.

### BGM Constraints

**Mapping between `audio` field in storyboard.json and API parameters**:

| Storyboard Field | API Parameter | Description |
|----------------|---------------|-------------|
| `audio.no_bgm = true` | Add `"No background music. Natural ambient sound only."` at end of prompt | BGM added in post-production |
| `audio.no_bgm = false` | No additional constraint | Video model decides whether to generate BGM |
| `audio.enabled = true` | `sound: "on"` | Generate ambient sound/dialogue |
| `audio.enabled = false` | `sound: "off"` | Silent output |

**Note**: Do not write Sound effects separately; let the model automatically generate ambient sound based on visual content (e.g., racing car engine sounds, keyboard sounds, wind sounds, etc.).

### Integrating Dialogue into Prompt

When a shot contains dialogue, it must be fully described in the video_prompt: character (including appearance), dialogue content (in quotes), expression/emotion, voice quality and speech rate.

```
The heroine (25-year-old Asian woman, long black straight hair) looks up at the server,
smiling gently and says: "It's really quiet here, I like it."
Voice clear and pleasant, moderate to slow pace.
```

---

## Appendix: Quick Templates

### Image Prompt Template (Omni Storyboard Frame, realistic)

```
PHOTOREALISTIC real human start frame. NOT ANIME, NOT CARTOON, NOT ILLUSTRATION.

Referencing the facial features, face shape, skin tone, and clothing details of:
- image_1: Element_{Name}, {detailed appearance description}

Scene: {scene description}
Location details: {environment details}

Element_{Name}: {pose}, {expression}, {position}

Shot scale: {wide/medium/close-up}
Camera angle: {eye-level/high/low}
Lighting: {lighting description}
Color grade: {color tone}
Aspect ratio: {aspect ratio}

Style: PHOTOREALISTIC, real human actress, actual skin texture, cinematic film grain, shallow depth of field
```

### Video Prompt Template (Omni Video)

```
Referencing the {frame_name} composition for scene layout and character positioning.

Element_{Name}'s appearance from {image_N} ({appearance reference}),
positioned as shown in {frame_name}.

Overall: {overall action description}

Motion sequence ({duration}s):
{time_range}: Element_{Name} {action}{, with lip-synced dialogue}

Dialogue exchange:
- Element_{Name} ({emotion}): "{line}"

Camera movement: {static/pan/tracking/etc.}
Sound effects: {sound design}

Style: Cinematic realistic style. No music, no subtitles.
```

### Video Prompt Template (Standard Kling, without Omni)

```
Overall: {overall shot action description}

Segmented actions ({duration}s):
{time_range_1}: {action description}
{time_range_2}: {action description + dialogue sync}

Camera movement: {camera movement description}
Rhythm: {motion rhythm}
Frame stability: {keep stable/slight shake}
{dialogue information}
Maintain {ratio} composition, do not break aspect ratio
{BGM constraint}
``````

---

## Three-View Character Reference Prompt (Fiction/Short Drama Only)

**Trigger Condition**: Only for fiction/short drama projects. Other types keep single reference image.

**Core Concept**: Three-view is the character reference image itself, containing front view + three-quarter side view + rear three-quarter view in one sheet. This is passed directly during storyboard design and video generation.

### Structural Elements (in order)

1. **Subject Definition** — Three-view full-body character reference sheet
2. **Style Anchor** — Film style reference (realistic/anime)
3. **Composition Layout** — Three figures side by side (front/three-quarter/rear three-quarter)
4. **Character Details** — Body, face, hair, costume (layered description)
5. **Lighting Design** — Key light, rim light, shadows
6. **Color Scheme** — Color quantification
7. **Render Precision** — Micro textures
8. **Mood Closing** — Metaphorical expression

### Realistic Template (visual_style = realistic)

```
A three-view full-body character reference sheet of {character description},
PHOTOREALISTIC real human style. NOT ANIME, NOT CARTOON, NOT ILLUSTRATION.
Inspired by cinematic realism with classical portrait aesthetic.

The sheet presents three medium-to-wide shots arranged side by side on a clean neutral backdrop:
front view, three-quarter view, and rear three-quarter view — each capturing the complete figure
from head to toe, ensuring no part of the silhouette is cropped.

{body description}, {posture description}
{face details}
{hair description}
{costume layered description}

Lighting: {lighting description}
Color grading: {color description}
Fine photorealistic rendering: {material details}
Mood: {mood keywords}

Style: PHOTOREALISTIC, real human actress/actor, actual skin texture, cinematic film grain,
shallow depth of field, clean neutral backdrop, 16:9 aspect ratio for three-view layout
```

**Complete Example (Realistic)**:

```
A three-view full-body character reference sheet of a young woman named Alice,
PHOTOREALISTIC real human style. NOT ANIME, NOT CARTOON, NOT ILLUSTRATION.
Inspired by cinematic realism with classical portrait aesthetic.

The sheet presents three medium-to-wide shots arranged side by side on a clean neutral backdrop:
front view, three-quarter view, and rear three-quarter view — each capturing the complete figure
from head to toe, ensuring no part of the silhouette is cropped.

The character is a young woman, late teens, slender and ethereal in physique — waist narrow,
posture elegant with shoulders slightly inward. Face: porcelain-pale skin with soft undertone;
softly arched brows; large, liquid eyes; delicately sculpted nose; faintly compressed lips.
Her jet-black hair is styled in an elegant updo secured with a jade hairpin,
with two loose tendrils framing her temples.

Costume: a layered traditional ensemble — fitted inner robe in soft pink with embroidered cuffs,
beneath a flowing outer robe in pale green with ribbon ties at waist and draped sleeves.
Fabric rendered as weightless silk with subtle sheen.

Lighting: soft diffused overcast natural light from high-left key, thin cool rim light outlining silhouette
Color grading: pale green and pink dominate 80% of palette, warm ivory for skin
Fine photorealistic rendering: individual silk thread texture, hair-strand detail, subtle skin pore depth
Mood: poetic vulnerability, classical feminine elegance

Style: PHOTOREALISTIC, real human actress, actual skin texture, cinematic film grain,
shallow depth of field, clean neutral backdrop, 16:9 aspect ratio for three-view layout
```

### Anime Style Template (visual_style = anime)

```
A three-view full-body character reference sheet of {character description},
Anime style 2D animation character design sheet.

Three poses arranged side by side on a clean backdrop:
front view, three-quarter view, and rear three-quarter view — full body from head to toe.

{body description}
{face features (anime style)}
{hair description}
{costume description}

Style: Anime style, 2D animation, cel shading, vibrant colors, clean lines,
character design sheet format, white/neutral backdrop
```

**Complete Example (Anime)**:

```
A three-view full-body character reference sheet of a young girl named Sakura,
Anime style 2D animation character design sheet.

Three poses arranged side by side on a clean backdrop:
front view, three-quarter view, and rear three-quarter view — full body from head to toe.

The character is a teenage girl, petite and energetic in physique — lively posture,
bright expressive eyes with characteristic anime sparkle, small nose, cheerful smile.
Pink hair styled in twin braids with ribbon hair accessories, bangs framing forehead.

Costume: school uniform — white blouse with sailor collar, navy blue skirt with pleats,
white knee-high socks, brown loafers. Clean crisp fabric lines.

Style: Anime style, 2D animation, cel shading, vibrant colors, clean lines,
character design sheet format, white backdrop, consistent proportions across all three views
```

### Based on User Photo

When user provides a photo as reference, use `--reference` parameter. Prompt must emphasize preserving original appearance:

```
A three-view full-body character reference sheet preserving the exact facial features,
body proportions, and skin tone from the reference photo.

PHOTOREALISTIC real human style. NOT ANIME, NOT CARTOON, NOT ILLUSTRATION.

The sheet presents three medium-to-wide shots arranged side by side on a clean neutral backdrop:
front view, three-quarter view, and rear three-quarter view — each capturing the complete figure
from head to toe.

IMPORTANT: Preserve exact facial identity from reference — same face shape, same eye shape,
same nose, same lip shape, same skin tone, same body proportions. Only adjust posture and
add simple costume/attire suitable for the character concept.

Lighting: soft diffused studio lighting, clean neutral backdrop
Style: PHOTOREALISTIC, real human, identity-preserving, 16:9 aspect ratio
```
