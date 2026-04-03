# Storyboard Design Complete Specifications

## Table of Contents

- Storyboard Structure (Scene / Shot)
- Character Registration and Reference Guidelines
- Storyboard Design Principles and Duration Limits
- shot_id Naming Rules
- T2V/I2V/Omni/Seedance Selection Rules
- First Frame Generation Strategy
- Dialogue Integration in video_prompt
- Storyboard JSON Format
- V3-Omni Two-stage Structure
- Multi-shot Mode (Kling / Kling Omni)
- **Seedance Smart Shot Cutting Mode**
- Review Check Mechanism
- Present to User for Confirmation

---

## Storyboard Structure

Uses **Scene-Shot two-layer structure**: `scenes[] → shots[]`

- **Scene**: Semantically+visually+spatially relatively stable narrative unit, duration typically 10-30 seconds
- **Shot**: Minimum video generation unit, duration 2-5 seconds

## Character Registration and Reference Guidelines

### Three-layer Naming System

| Level | Purpose | Naming Convention | Example |
|-------|---------|-------------------|---------|
| **Element ID** | Technical ID, used for JSON reference, character identifier in Prompt | `Element_` + English name/Pinyin | `Element_Chuyue`, `Element_Emma` |
| **Display Name** | Display name, used for user interaction, Chinese description | Chinese name | `Chuyue`, `Emma` |
| **Reference Tag** | Placeholder in Prompt (auto-mapped) | `<<<image_N>>>` | `<<<image_1>>>`, `<<<image_2>>>` |

### Usage in Workflow

**Phase 1: Character Identification**
- After user confirms character identities, generate `element_id` (auto: Element_ + Pinyin/English name)
- Write to `storyboard.json`'s `elements.characters`
- **Note**: Phase 1 only processes reference images uploaded by user, for those not uploaded leave `reference_images` empty, supplemented by Phase 2

**Phase 2: Character Reference Image Collection (Key)**
- Check characters with empty `reference_images`
- Ask user: AI generate / Upload reference image / Accept text-only (with warning)
- Update `personas.json` and `storyboard.json`'s `reference_images`

**Phase 3: Storyboard Design (LLM Auto-generation)**
- LLM generates storyboard based on `elements.characters`
- Auto-assign `character_image_mapping` (by characters array order: image_1, image_2...)
- **Select generation mode based on project type**:
  - Fiction film/Short drama, MV short film → **All shots mandatory storyboard image** → `reference2video` (Omni) or `img2video` (fallback)
  - Vlog/Documentary, Commercial (with real materials) → User material first frame → `img2video`
- When generating Prompt:
  - Image Prompt uses `<<<image_1>>>`, `<<<image_2>>>` to reference appearance
  - Video Prompt uses `Element_XXX` + `<<<image_N>>>` double reference

**Phase 4: Generation Execution**
- Read `character_image_mapping`, prepare image file list by `image_N` order
- Pass corresponding reference images when calling API

### Scene Fields

- `scene_id`: Scene number (e.g. "scene_1")
- `scene_name`: Scene name
- `duration`: Total scene duration = sum of all subordinate shot durations
- `narrative_goal`: Main narrative objective
- `spatial_setting`: Spatial setting
- `time_state`: Time state
- `visual_style`: Visual master style
- `shots[]`: Shot list

### Shot Fields

- `shot_id`: Shot number (format see naming rules below)
- `duration`: Duration (unit: seconds, range: 2-5 seconds)
- `shot_type`: Shot type, options: establishing (wide) / dialogue / action / closeup / insert
- `description`: Brief description
- `generation_mode`: Generation mode, options: text2video / img2video / omni-video
- `multi_shot`: Whether multi-shot mode, true / false (independent of shot_type)
- `generation_backend`: Backend selection, options: kling / kling-omni / vidu
- `video_prompt`: Video generation prompt
- `image_prompt`: Image generation prompt (used for img2video/omni-video)
- `frame_strategy`: First/last frame strategy, options: none / first_frame_only / first_and_last_frame
  - **Note**: Omni mode (`generation_mode: omni-video`) doesn't use this field, because Omni uses `reference_images` instead of first frame control
- `reference_images`: Reference image path list (required for omni-video, optional for img2video)
  - Omni mode: Contains storyboard image + character reference images
  - img2video mode: Optional, used as reference when Gemini generates storyboard image
- `dialogue`: Dialogue information (structured)
- `transition`: Transition effect
- `audio`: Audio configuration (enabled, no_bgm, dialogue)

---

## Storyboard Design Principles

1. **Duration Allocation**: Total duration = Target duration (±2 seconds)
2. **Rhythm Variation**: Avoid all shots having same duration
3. **Shot Type Variation**: Consecutive shots should have shot type differences
4. **Transition Selection**: Choose appropriate transitions based on emotion
5. **Single Action Principle**: Maximum 1 action per shot
6. **Spatial Invariance Principle**: No spatial environment changes within a shot
7. **Concrete Description Principle**: Replace abstract action descriptions with concrete actions

### Duration Limits

- Normal shots: 2-3 seconds
- Complex motion shots: ≤2 seconds
- Static emotional shots: ≤5 seconds

---

## shot_id Naming Rules

Format: `scene{scene_number}_shot{shot_number}`

| Type | Example | Description |
|------|---------|-------------|
| Single shot | `scene1_shot1`, `scene2_shot1` | Standard naming |
| Multi-shot mode | `scene1_shot2to4_multi` | Merged shots, range connected with `to`, with `_multi` suffix |

**Multi-shot Naming Convention**:
- Merge shot2, shot3, shot4 → `scene1_shot2to4_multi`
- Merge shot1 to shot5 → `scene1_shot1to5_multi`
- **Do not** use underscore connection: `scene1_shot2_shot3_shot4_multi` ❌

---

## T2V/I2V/Ref2V Selection Rules

**Core Principles**:
- **Fiction film doesn't use text2video**
- **Same project uses same model**

### Project Type Determination

| User Intent Keywords | Project Type |
|---------------------|--------------|
| "short drama", "story", "narrative" | Fiction film/Short drama |
| "vlog", "travel diary", "life record" | Vlog/Documentary |
| "commercial", "promotional video", "product showcase" | Commercial/Promotional |
| "MV", "music video" | MV short film |

### Auto-selection Decision Tree

**Fiction film/Short drama, MV short film**:
```
Fiction content → All shots mandatory storyboard image first
                 ├── Priority → Kling-3.0-Omni (reference2video)
                 │              └── image_list: [storyboard image, character reference image]
                 │
                 └── Fallback → Kling-3.0 or Vidu Q3 Pro (img2video)
                                └── --image: storyboard image first frame
```

**Vlog/Documentary, Commercial/Promotional (with real materials)**:
```
Real materials → Need first frame control
                └── Kling-3.0 or Vidu Q3 Pro (img2video)
                    └── --image: User material first frame
```

### Selection Rules Table

| Project Type | Material Situation | Generation Mode | Backend | Description |
|--------------|-------------------|-----------------|---------|-------------|
| Fiction film/Short drama | With/without character reference | `reference2video` | `kling-omni` | Mandatory storyboard image, Omni ensures consistency |
| MV short film | With/without character reference | `reference2video` | `kling-omni` | Mandatory storyboard image, music-driven |
| Vlog/Documentary | User's real materials | `img2video` | `kling` or `vidu` | User material first frame control |
| Commercial/Promotional | Has real materials | `img2video` | `kling` or `vidu` | Product/company material first frame |
| Commercial/Promotional | No real materials | `reference2video` | `kling-omni` | Pure fiction showcase |

### Model and Generation Path Support

| Model | reference2video | img2video | text2video |
|-------|-----------------|-----------|------------|
| **Kling-3.0-Omni** | ✅ Supported | ❌ Not supported | ✅ Supported |
| **Kling-3.0** | ❌ Not supported | ✅ Supported | ✅ Supported |
| **Vidu Q3 Pro** | ❌ Not supported | ✅ Supported | ✅ Supported |

**Key**: Kling-3.0-Omni doesn't support img2video (first frame control), need first frame control then can't use Omni.

---

## First Frame Generation Strategy

| frame_strategy | Description | Execution Method |
|-----------------|-------------|------------------|
| `none` | No first/last frame needed | Directly call text-to-video API |
| `first_frame_only` | First frame only | Generate first frame image → img2video API |
| `first_and_last_frame` | First and last frame | Generate first and last frame → Kling API (`image_tail` parameter) |

First/last frame field extension (when `first_and_last_frame`):

```json
{
  "frame_strategy": "first_and_last_frame",
  "image_prompt": "First frame description",
  "last_frame_prompt": "Last frame description"
}
```

---

## Dialogue Integration in video_prompt

When shot contains dialogue, **must fully describe in video_prompt**: character (including appearance), dialogue content (in quotes), expression/emotion, voice quality and speaking rate.

```json
{
  "shot_id": "scene1_shot5",
  "video_prompt": "Emma (a 25-year-old Asian woman with long black hair) looks up at the server, smiling gently and says, 'It's really quiet here, I like it.' Clear, pleasant voice, moderate pace. Keep 9:16 vertical composition.",
  "dialogue": {
    "speaker": "Emma",
    "content": "It's really quiet here, I like it.",
    "emotion": "gentle, pleasant",
    "voice_type": "clear female voice"
  },
  "audio": {
    "enabled": true,
    "dialogue": {
      "speaker": "Emma",
      "text": "It's really quiet here, I like it.",
      "emotion": "gentle, pleasant"
    },
    "no_bgm": true
  }
}
```

---

## Narration Segmentation Planning (narration_segments)

**Trigger Condition**: After Phase 2 confirms need for "AI-generated narration", Phase 3 must plan narration segments when generating storyboard.

### Global Configuration (Root Level)

```json
{
  "narration_config": {
    "enabled": true,
    "voice_style": "Gentle female voice, moderate pace, full emotion"
  },
  "narration_segments": [
    {
      "segment_id": "narr_1",
      "time_range": "0-3s",
      "target_shot": "scene1_shot1",
      "text": "This is a peaceful afternoon, sunlight streams through the floor-to-ceiling windows into the coffee shop..."
    },
    {
      "segment_id": "narr_2",
      "time_range": "8-11s",
      "target_shot": "scene1_shot3",
      "text": "She sits by the window, gazing at the scenery outside, thoughts drifting away..."
    }
  ]
}
```

### Field Description

| Field | Type | Description |
|-------|------|-------------|
| `narration_config.enabled` | boolean | Whether to enable narration |
| `narration_config.voice_style` | string | Globally unified narration style (unified within one video) |
| `narration_segments` | array | Narration segment list |
| `segment_id` | string | Segment number (format: `narr_1`, `narr_2`...) |
| `time_range` | string | Overall timeline position (format: `0-3s`, `8-11s`, calculated from video start point) |
| `target_shot` | string | Corresponding shot ID |
| `text` | string | Narration copy for this segment |

### Planning Principles

1. **Timeline Continuity**: `time_range` calculated from video start point (0 seconds), not shot internal time
2. **Segment Length**: Each narration segment should be speakable in 2-5 seconds (about 30-50 characters)
3. **Avoid Conflict**: Narration time range shouldn't overlap with character dialogue (sync sound)
4. **Shot Correspondence**: Each segment must correspond to a target_shot
5. **voice_style Unified**: Use same narration style within one video

### Narration Copy Segmentation Tips

**Don't do this** (one big chunk):
```json
{
  "text": "This is a peaceful afternoon, sunlight streams through the floor-to-ceiling windows into the coffee shop, she sits by the window, gazing at the scenery outside, thoughts drifting away, recalling that special summer."
}
```

**Do this instead** (segment by shot):
```json
{
  "narration_segments": [
    {"segment_id": "narr_1", "time_range": "0-3s", "target_shot": "scene1_shot1", "text": "This is a peaceful afternoon, sunlight streams through the floor-to-ceiling windows into the coffee shop..."},
    {"segment_id": "narr_2", "time_range": "8-11s", "target_shot": "scene1_shot3", "text": "She sits by the window, gazing at the scenery outside..."},
    {"segment_id": "narr_3", "time_range": "15-18s", "target_shot": "scene2_shot1", "text": "Thoughts drifting away, recalling that special summer..."}
  ]
}
```

### Relationship with creative.json

After Phase 2 confirms narration requirement, `creative.json` records:
```json
{
  "narration": {
    "type": "ai_generated",
    "voice_style": "Gentle female voice",
    "full_text": "Full narration copy provided by user (if multiple segments)"
  }
}
```

When Phase 3 generates storyboard:
- Read `creative.narration.type`
- If `ai_generated`, then plan `narration_segments`
- Segment `creative.narration.full_text` by shot time points
- Write `creative.narration.voice_style` to `narration_config.voice_style`

### audio Field Description

`audio` field uses object format, containing following sub-fields:

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether to generate audio (including ambient sound + dialogue), default true |
| `dialogue` | object/null | Dialogue information, null means no dialogue |
| `dialogue.speaker` | string | Speaking character |
| `dialogue.text` | string | Dialogue content |
| `dialogue.emotion` | string | Emotion/tone |
| `no_bgm` | boolean | Whether to explicitly add "No background music" in prompt |

### BGM Decision Logic

Define `bgm` field in creative.json:

```json
{
  "bgm": {
    "type": "ai_generated",
    "style": "Epic, racing theme"
  }
}
```

`bgm.type` values:
- `"ai_generated"` → All shots `audio.no_bgm = true` (BGM by Suno post-production mix)
- `"user_provided"` → All shots `audio.no_bgm = true` (BGM provided by user)
- `"none"` → All shots `audio.no_bgm = false` (video model decides freely)

`dialogue` field usage: TTS generation, subtitle extraction, user quick view.

**TTS Narration only for**: Opening/closingnarration, scene description without character speaking, emotional narration. **Don't use TTS for shots that can capture sync sound!**

---

## Storyboard JSON Format

```json
{
  "project_name": "Project Name",
  "target_duration": 60,
  "aspect_ratio": "9:16",
  "elements": {
    "characters": [
      {
        "element_id": "Element_Chuyue",
        "name": "Chuyue",
        "name_en": "Chuyue",
        "reference_images": ["/path/to/ref.jpg"],
        "visual_description": "25-year-old Asian female, long straight black hair to waist, oval face..."
      },
      {
        "element_id": "Element_Jiazhi",
        "name": "Jiazhi",
        "name_en": "Jiazhi",
        "reference_images": ["/path/to/ref2.jpg"],
        "visual_description": "Mature male, short hair, deep eyes..."
      }
    ]
  },
  "character_image_mapping": {
    "Element_Chuyue": "image_1",
    "Element_Jiazhi": "image_2"
  },
  "scenes": [
    {
      "scene_id": "scene_1",
      "scene_name": "Opening - Coffee Shop Encounter",
      "duration": 18,
      "narrative_goal": "Show female protagonist's daily life in coffee shop",
      "spatial_setting": "Cozy city coffee shop",
      "time_state": "3 PM",
      "visual_style": "Warm tones, cinematic",
      "shots": [
        {
          "shot_id": "scene1_shot1",
          "duration": 3,
          "shot_type": "establishing",
          "description": "Coffee shop wide shot",
          "generation_mode": "text2video",
          "generation_backend": "kling",
          "video_prompt": "Interior of a cozy city coffee shop, afternoon sunlight streaming through floor-to-ceiling windows, camera slowly pushing in. Keep 9:16 vertical composition. No background music. Natural ambient sound only.",
          "frame_strategy": "none",
          "multi_shot": false,
          "dialogue": null,
          "transition": "fade_in",
          "audio": {
            "enabled": true,
            "dialogue": null,
            "no_bgm": true
          }
        }
      ]
    }
  ],
  "props": [],
  "decision_log": {}
}
```

### Field Description

**elements.characters**: Character registration table, written after Phase 1 identification
- `element_id`: Technical ID, format `Element_` + English name/Pinyin
- `name`: Chinese display name
- `name_en`: English name
- `reference_images`: Reference image path list
- `visual_description`: Visual feature description

**character_image_mapping**: Auto-generated mapping table (Phase 3), **Storyboard global field**
- Key: `element_id` (e.g. `Element_Chuyue`)
- Value: `image_N` tag (e.g. `image_1`)
- Mapping rule: Assign image_1, image_2... by characters array order
- Note: This field at storyboard root level, not repeated inside shot

### Kling Omni Mode Example

```json
{
  "shot_id": "scene2_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "Emma (<<<image_1>>>), wearing headphones, fully focused at racing simulator. 9:16 vertical composition.",
  "reference_images": ["materials/personas/emma_ref.jpg"],
  "frame_strategy": "none",
  "image_prompt": "Cinematic realistic start frame... (optional, for storyboard image generation)",
  "multi_shot": false,
  "audio": {
    "enabled": true,
    "dialogue": null,
    "no_bgm": true
  }
}
```

**Note**: Omni mode uses `reference_images` as reference, doesn't use `frame_strategy` first frame control. `frame_strategy` should be set to `none`. If need to generate storyboard image, use `image_prompt` to separately record storyboard image prompt.

---

## V3-Omni Two-stage Structure (Recommended)

For Kling V3-Omni's **storyboard image + video** two-stage generation process, recommend adopting layered data structure.

### Relationship with Standard Structure

**V3-Omni three-layer structure is an extension of standard Shot structure**, not a replacement:
- Standard structure fields (`shot_id`, `duration`, `generation_mode`, `generation_backend` etc.) still retained
- Three-layer structure expands `image_prompt` and `video_prompt` into more detailed structured fields
- `character_image_mapping` always at **Storyboard global level**, not repeated inside shot

### Field Mapping Table

| Standard Structure Field | V3-Omni Structure Corresponding | Description |
|-------------------------|--------------------------------|-------------|
| `image_prompt` | `frame_generation.prompt` | Storyboard image generation prompt |
| `video_prompt` | `video_generation.prompt` | Video generation prompt |
| `reference_images` | Auto-added after `frame_generation` generation | Storyboard image output + character reference images |
| `frame_strategy` | Always `"none"` | Omni doesn't use first frame control |

### Design Philosophy

**Storyboard Frame**: Not just first frame control, also controls overall visual (scene, style, lighting, atmosphere, color, makeup/costume)

**Video Generation**: References storyboard frame composition,overlaying action and character reference

### Schema Structure

```json
{
  "shot_id": "scene1_shot1",
  "duration": 7,
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "multi_shot": false,
  "reference_images": [],

  "storyboard": {
    "chinese_description": "Continuous action and dialogue (about 7s) wide shot. Chuyue fumbles backward to outside...",
    "shot_scale": "Wide shot",
    "location": "Men's restroom doorway transition area",
    "dialogue_segments": [
      {"time": "0-2s", "speaker": "Chuyue", "line": "Okay, I admit...", "emotion": "Embarrassed apologetic smile"},
      {"time": "2-4s", "speaker": "Tianyu", "line": "Then don't look like you saw a ghost.", "emotion": "flat"}
    ],
    "transition": "cut"
  },

  "frame_generation": {
    "output_key": "scene1_shot1_frame",
    "prompt": "Cinematic realistic start frame...",
    "character_refs": ["Element_Chuyue", "Element_Jiazhi", "Element_Tianyu"],
    "scene": "Men's restroom doorway, white tiles...",
    "lighting": "Cold white fluorescent light",
    "camera": {"shot_scale": "wide", "angle": "eye-level"},
    "style": "cinematic realistic, cool blue-white"
  },

  "video_generation": {
    "backend": "kling_v3_omni",
    "frame_reference": "scene1_shot1_frame",
    "prompt": "Referencing scene1_shot1_frame composition...",
    "motion_overall": "Chuyue fumbles backward...",
    "motion_segments": [
      {"time": "0-2s", "action": "steps back past threshold...", "character": "Element_Chuyue"},
      {"time": "2-5s", "action": "three-way dialogue exchange", "lip_sync": true}
    ],
    "camera_movement": "static wide shot",
    "sound_effects": "shuffling footsteps on tile"
  }
}
```

### Field Description

**Note**: `character_image_mapping` always at **Storyboard global level**, not repeated inside shot. V3-Omni structure uses `frame_generation.character_refs` to reference characters.

**storyboard layer** (Chinese, for human reading)
- `chinese_description`: Plot description
- `shot_scale`: Shot scale (wide/medium/close-up etc.)
- `location`: Scene location
- `dialogue_segments`: Dialogue timeline
- `transition`: Transition effect

**frame_generation layer** (generate storyboard image)
- `output_key`: Output file name
- `prompt`: Complete Image Prompt
- `character_refs`: Referenced character elements
- `scene`: Scene description
- `lighting`: Lighting description
- `camera`: Camera parameters (shot_scale, angle, lens)
- `style`: Visual style

**video_generation layer** (generate video)
- `frame_reference`: Referenced storyboard image output_key
- `prompt`: Complete Video Prompt
- `motion_overall`: Overall action description
- `motion_segments`: Segmented actions (with timeline)
- `camera_movement`: Camera movement
- `sound_effects`: Sound design

---

## Multi-shot Mode (Kling / Kling Omni)

Both Kling and Kling Omni support multi-shot single-take.

### Configuration Fields

```json
{
  "shot_id": "scene1_shot2to4_multi",
  "duration": 10,
  "multi_shot": true,
  "multi_shot_config": {
    "mode": "customize",
    "shots": [
      {"shot_id": "scene1_shot2", "duration": 3, "prompt": "Shot 1 description"},
      {"shot_id": "scene1_shot3", "duration": 4, "prompt": "Shot 2 description"},
      {"shot_id": "scene1_shot4", "duration": 3, "prompt": "Shot 3 description"}
    ]
  }
}
```

### Two Modes

- **intelligence**: AI auto storyboard, suitable for simple narrative
- **customize** (Recommended): Precise control of each shot's content and duration

### Multi-shot Rules

- Total duration 3-15s, each shot at least 1s
- All shot durations sum = Video total duration

| Scenario | Recommended Mode |
|----------|------------------|
| Narrative video (story, commercial) | multi_shot + customize |
| Simple narrative | multi_shot + intelligence |
| Material mashup (vlog, showcase) | Single shot generate one by one |
| Simple short video (<10s) | Single shot text2video |

---

## Seedance Smart Shot Cutting Mode

**Core Feature**: Time-segmented prompt auto triggers multi-shot, execution phase merges multiple shots in same scene into one API call.

**⚠️ Key Limit: Duration can only be 5/10/15s (enum values)**

In **Phase 3 Storyboard Design Phase**, when choosing Seedance backend, must ensure each scene's total duration is **5, 10 or 15 seconds** (only these three values, not other durations like 8s, 12s).

### Duration Planning in Design Phase (Phase 3)

**Seedance Backend Duration Design Rules**:

| Scene Total Duration | ✅ Allowed | ❌ Not Allowed |
|---------------------|------------|----------------|
| 5s | ✓ | - |
| 10s | ✓ | - |
| 15s | ✓ | - |
| 8s, 12s, 18s etc. | - | ✗ (API doesn't support) |

**Design Flow**:
```
Choose Seedance → Determine scene total duration (must be 5/10/15) → Allocate shot durations
```

**Example**:
- Target 15s scene → shots: 3s + 3s + 4s + 5s = 15s ✓
- Target 10s scene → shots: 3s + 3s + 4s = 10s ✓
- Target 18s scene → ✗ Not allowed, need to split into 15s + 3s (second segment needs separate processing)

### Design Principles

**Shot Structure Remains Unchanged**: Seedance only merges in execution phase, doesn't change storyboard's `scenes → shots` structure.

| Model | Execution Method |
|-------|-----------------|
| Kling/Vidu/Omni | Each shot calls API separately |
| **Seedance** | Multiple shots in same scene merged into one API call (time-segmented prompt) |

### Scene → Video Segment Division Rules

| Scene Duration | Shot Count | Video Segment Planning |
|---------------|------------|----------------------|
| ≤15s | Any number (e.g. 3-5 shots) | **Single video segment**, time segments cover all shots |
| 16-30s | Many (e.g. 6-10 shots) | **2-3 video segments**, segmented coverage (e.g. 15s + 15s) |
| >30s | Very many (e.g. >10 shots) | **3+ video segments**, segmented coverage |
| Scene switch | - | **Independent video segments each**, no cross-Scene merging |

### Execution Phase Processing Flow

**Example**: Scene 1 contains 4 shots (total 15s)

```json
{
  "scene_id": "scene_1",
  "shots": [
    {"shot_id": "scene1_shot1", "duration": 3, "description": "Pick apple"},
    {"shot_id": "scene1_shot2", "duration": 3, "description": "Put in shaker"},
    {"shot_id": "scene1_shot3", "duration": 4, "description": "Product closeup"},
    {"shot_id": "scene1_shot4", "duration": 5, "description": "Raise cup display"}
  ]
}
```

**Seedance Execution Logic**:

1. Identify `generation_backend = "seedance"`
2. Merge scene_1's 4 shots (total 15s) into one API call
3. Generate storyboard image (one per video segment)
4. Generate time-segmented prompt:
   ```
   0-3s: Pick apple...;
   3-6s: Put in shaker...;
   6-10s: Product closeup...;
   10-15s: Raise cup display...;
   ```
5. Call Seedance API

### Time-segmented Prompt Format

```
Referencing the {segment_id}_frame composition for scene layout and character positioning.

@image1 (character reference), [viewpoint setting] [theme/style];

Overall: [Shot overall action summary]

Segmented actions ({duration}s):
0-Xs: [Scene] + [Action] + [Camera] + [Rhythm] + [Sound/Dialogue];
X-Xs: [Cut] + [Scene] + [Action] + [Camera] + [Rhythm] + [Sound/Dialogue];
...

Maintain {aspect_ratio} composition, don't break aspect ratio
{BGM constraint}
```

### image_urls Order Convention

| index | Usage | Reference Method |
|-------|-------|-----------------|
| `image_urls[0]` | Storyboard image | `Referencing the {segment_id}_frame composition...` |
| `image_urls[1]` | Character reference 1 | `@image1` |
| `image_urls[2]` | Character reference 2 | `@image2` |

### Seedance Storyboard Annotation Example

```json
{
  "shot_id": "scene1_shot1",
  "duration": 3,
  "generation_mode": "seedance-video",
  "generation_backend": "seedance",
  "video_prompt": "Your hand picks a dewy Aksu red apple, fixed shot, steady rhythm, crisp apple collision sound",
  "reference_images": [
    "generated/frames/scene1_frame.png",
    "materials/personas/emma_ref.jpg"
  ],
}
```

### Limitations and Notes

| Limitation | Description |
|------------|-------------|
| Duration only supports 5/10/15s | Only these three enum values, no other durations |
| Max 720p | Use Kling/Vidu when 1080p needed |
| No first frame precise control | Storyboard image is reference, not first frame |
| No reference audio | Cannot use audio_urls parameter |
| Image reference syntax | Use `@imageN` (not `<<<image_N>>>`) |

---

## Review Check Mechanism

After generating storyboard, must check following items:

**1. Structural Completeness**
- Total duration matches target duration (±2 seconds)
- Scene duration = Sum of subordinate shot durations

**2. Storyboard Rules**
- Each shot duration 2-5 seconds
- No multi-action shots, no spatial changes within shots

**3. Prompt Standards**
- All video_prompts include aspect ratio information
- Dialogue integrated into video_prompt
- No abstract action descriptions

**4. Technical Selection**
- T2V/I2V selection reasonable
- Backend selection matches requirements
- First/last frame strategy correct

---

## Present to User for Confirmation (Mandatory Step)

**Must have explicit user confirmation before entering Phase 4!**

When confirming, display for each shot: scene information, generation mode, backend, video_prompt, image_prompt (if any), dialogue, transition, duration.

User can choose: Confirm and Execute / Modify Storyboard / Adjust Duration / Change Transition / Cancel.

---

## fallback_plan Field (Degradation Plan)

When generating storyboard in Phase 3, recommend reserving degradation plan for each shot, avoidtemporary writing `image_prompt`.

### Field Structure

```json
{
  "shot_id": "scene1_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "...",
  "reference_images": ["materials/personas/emma_ref.jpg"],
  "frame_strategy": "none",

  "fallback_plan": {
    "mode": "img2video",
    "backend": "kling",
    "image_prompt": "Cinematic realistic start frame.\nScene: ...\nLighting: ...\nCharacter: Referencing <<<image_1>>> appearance...\nStyle: ...",
    "frame_strategy": "first_frame_only",
    "frame_output": "generated/frames/{shot_id}_frame.png",
    "reason": "Fallback when Omni API unavailable"
  }
}
```

### Field Description

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | Degraded generation mode: `img2video` or `text2video` |
| `backend` | string | Degraded backend: `kling` or `vidu` |
| `image_prompt` | string | Complete prompt for generating storyboard image (required when degrading) |
| `frame_strategy` | string | Degraded first frame strategy: `first_frame_only` |
| `frame_output` | string | Storyboard image output path template |
| `reason` | string | Degradation reason description |

### Degradation Processing Flow

When degradation needed:

1. Read shot's `fallback_plan` field
2. Copy following fields from `fallback_plan` to shot main fields:
   - `generation_mode` ← `fallback_plan.mode`
   - `generation_backend` ← `fallback_plan.backend`
   - `frame_strategy` ← `fallback_plan.frame_strategy`
   - `image_prompt` ← `fallback_plan.image_prompt`
3. Clear or adjust `reference_images` (img2video doesn't need character reference images)
4. Execute degraded generation flow

### Example: Degraded Shot

```json
// Before degradation
{
  "shot_id": "scene1_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "Emma (<<<image_1>>>), by coffee shop window...",
  "reference_images": ["materials/personas/emma_ref.jpg"],
  "frame_strategy": "none",
  "fallback_plan": {
    "mode": "img2video",
    "backend": "kling",
    "image_prompt": "Cinematic start frame. 25-year-old Asian female...",
    "frame_strategy": "first_frame_only"
  }
}

// After degradation (fallback_plan fields copied)
{
  "shot_id": "scene1_shot1",
  "generation_mode": "img2video",
  "generation_backend": "kling",
  "video_prompt": "Emma, by coffee shop window...",  // Remove <<<image_1>>> reference
  "reference_images": [],
  "frame_strategy": "first_frame_only",
  "image_prompt": "Cinematic start frame. 25-year-old Asian female...",
  "frame_path": "generated/frames/scene1_shot1_frame.png",
  "fallback_plan": { ... }  // Keep original plan, can degrade again
}
```

### Scenarios Without fallback_plan

- Pure `text2video` shots (no reference images needed, degradation meaningless)
- User explicitly states no degradation accepted
- Simple prototype, no character consistency guarantee needed