# Storyboard Design Complete Specification

## Table of Contents

- Storyboard Structure (Scene / Shot)
- Character Registration and Reference Specification
- Storyboard Design Principles and Duration Limits
- shot_id Naming Rules
- T2V/I2V/Omni/Seedance Selection Rules
- First and Last Frame Generation Strategy
- Dialogue Integration into video_prompt
- Storyboard JSON Format
- V3-Omni Two-Stage Structure
- Multi-Shot Mode (Kling / Kling Omni)
- **Seedance Smart Scene Switching Mode**
- Review Check Mechanism
- User Confirmation Display

---

## Storyboard Structure

Adopts **Scene-Shot two-layer structure**: `scenes[] → shots[]`

- **Scene**: A narrative unit with relatively stable semantics, visuals, and spatiotemporal context, typically lasting 10-30 seconds
- **Shot**: The minimum video generation unit, lasting 2-5 seconds

## Character Registration and Reference Specification

### Three-Layer Naming System

| Layer | Purpose | Naming Convention | Example |
|-------|---------|-------------------|---------|
| **Element ID** | Technical ID, used for JSON references and character identification in prompts | `Element_` + English name/Pinyin | `Element_Chuyue`, `Element_Xiaomei` |
| **Display Name** | Display name, used for user interaction | Character name | `Luna`, `May` |
| **Reference Tag** | Placeholder in prompts (auto-mapped) | `<<<image_N>>>` | `<<<image_1>>>`, `<<<image_2>>>` |

### Usage Flow in Workflow

**Phase 1: Character Identification**
- After user confirms character identity, generate `element_id` (auto: Element_ + Pinyin/English name)
- Write to `storyboard.json` in `elements.characters`
- **Note**: Phase 1 only processes user-uploaded reference images; reference images not uploaded remain empty, to be filled in Phase 2

**Phase 2: Character Reference Image Collection (Critical)**
- Check characters with empty `reference_images`
- Ask user: AI generate / Upload reference image / Accept text-only (with warning)
- Update `personas.json` and `storyboard.json` `reference_images`

**Phase 3: Storyboard Design (LLM Auto-Generation)**
- LLM generates storyboard based on `elements.characters`
- Auto-assign `character_image_mapping` (in characters array order: image_1, image_2...)
- **Select generation mode based on project type**:
  - Fiction/Short drama, MV short film → **All shots require storyboard frames** → `reference2video` (Omni) or `img2video` (fallback)
  - Vlog/Documentary, Advertisement (with real materials) → User material first frame → `img2video`
- When generating prompts:
  - Image Prompt uses `<<<image_1>>>`, `<<<image_2>>>` to reference appearance
  - Video Prompt uses `Element_XXX` + `<<<image_N>>>` dual reference

**Phase 4: Execute Generation**
- Read `character_image_mapping`, prepare image file list in `image_N` order
- Pass corresponding reference images when calling API

### Scene Fields

- `scene_id`: Scene number (e.g., "scene_1")
- `scene_name`: Scene name
- `duration`: Total scene duration = sum of all shot durations within
- `narrative_goal`: Main narrative objective
- `spatial_setting`: Spatial setting
- `time_state`: Time state
- `visual_style`: Visual master style
- `shots[]`: Shot list

### Shot Fields

- `shot_id`: Shot number (format see naming rules below)
- `duration`: Duration (unit: seconds, range: 2-5 seconds)
- `shot_type`: Shot type, options: establishing / dialogue / action / closeup / insert
- `description`: Brief description
- `generation_mode`: Generation mode, options: text2video / img2video / omni-video / seedance-video
- `multi_shot`: Whether multi-shot mode, true / false (independent of shot_type)
- `generation_backend`: Backend selection, options: kling / kling-omni / vidu / seedance
- `video_prompt`: Video generation prompt
- `image_prompt`: Image generation prompt (used for img2video/omni-video)
- `frame_path`: Storyboard frame output path (required for Kling-Omni shot-level), e.g., `generated/frames/{shot_id}_frame.png`
- `frame_strategy`: First/last frame strategy, options: none / first_frame_only / first_and_last_frame
  - **Note**: Omni mode (`generation_mode: omni-video`) does not use this field because Omni uses `reference_images` instead of first frame control
- `reference_images`: Reference image path list (required for omni-video, optional for img2video)
  - Omni mode: Contains storyboard frame + character reference images
  - img2video mode: Optional, used as reference when Gemini generates storyboard frames
- `dialogue`: Dialogue information (structured)
- `transition`: Transition effect
- `audio`: Audio configuration (enabled, no_bgm, dialogue)

---

## Storyboard Design Principles

1. **Duration Allocation**: Total duration = Target duration (±2 seconds)
2. **Rhythm Variation**: Avoid identical shot durations
3. **Shot Type Variation**: Consecutive shots should have shot type differences
4. **Transition Selection**: Choose appropriate transitions based on emotion
5. **Single Action Principle**: Maximum 1 action per shot
6. **Spatial Invariance Principle**: No spatial environment changes within a shot
7. **Specific Description Principle**: Avoid abstract action descriptions; use specific actions instead

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
- **Fiction projects do not use text2video**
- **Use the same model within one project**

### Project Type Determination

| User Intent Keywords | Project Type |
|---------------------|--------------|
| "short drama", "story", "narrative" | Fiction/Short drama |
| "vlog", "travel record", "life record" | Vlog/Documentary |
| "commercial", "promo video", "product showcase" | Advertisement/Promotional video |
| "MV", "music video" | MV short film |

### Automatic Selection Decision Tree

**Fiction/Short drama, MV short film**:
```
Fiction content → All shots require storyboard frames first
                   ├── Priority → Seedance (smart scene switching + multi-reference images)
                   │              └── image_urls: [storyboard frame, character reference images...]
                   │              └── Time segment prompt auto-triggers multi-shot
                   │
                   ├── Fallback 1 → Kling-3.0-Omni (reference2video)
                   │                └── image_list: [storyboard frame, character reference images]
                   │
                   └── Fallback 2 → Kling-3.0 or Vidu Q3 Pro (img2video)
                                    └── --image: Storyboard frame as first frame
```

**Vlog/Documentary, Advertisement/Promotional video (with real materials)**:
```
Real materials → First frame control needed
                  └── Kling-3.0 or Vidu Q3 Pro (img2video)
                      └── --image: User material first frame
```

### Selection Rule Table

| Project Type | Material Status | Generation Mode | Backend | Description |
|--------------|-----------------|-----------------|---------|-------------|
| Fiction/Short drama | With/Without character reference | `seedance-video` | `seedance` | **Priority**: Smart scene switching + multi-reference |
| Fiction/Short drama | Seedance unavailable | `omni-video` | `kling-omni` | Fallback: Mandatory storyboard frame, Omni ensures consistency |
| MV short film | With/Without character reference | `seedance-video` | `seedance` | **Priority**: Music-driven + smart scene switching |
| MV short film | Seedance unavailable | `omni-video` | `kling-omni` | Fallback: Mandatory storyboard frame |
| Vlog/Documentary | User real materials | `img2video` | `kling` or `vidu` | User material first frame control |
| Advertisement/Promotional video | Has real materials | `img2video` | `kling` or `vidu` | Product/Company material first frame |
| Advertisement/Promotional video | No real materials | `seedance-video` | `seedance` | **Priority**: Smart scene switching, long take |
| Advertisement/Promotional video | No real materials + Seedance unavailable | `omni-video` | `kling-omni` | Fallback: Pure fictional showcase |

### Model and Generation Path Support

| Model | seedance-video | reference2video | img2video | text2video |
|-------|----------------|-----------------|-----------|------------|
| **Seedance** | ✅ Supported | ✅ Supported (image_urls) | ❌ First frame control not supported | ✅ Supported |
| **Kling-3.0-Omni** | ❌ Not supported | ✅ Supported | ❌ Not supported | ✅ Supported |
| **Kling-3.0** | ❌ Not supported | ❌ Not supported | ✅ Supported | ✅ Supported |
| **Vidu Q3 Pro** | ❌ Not supported | ❌ Not supported | ✅ Supported | ✅ Supported |

**Key Points**:
- **Seedance does not support precise first frame control**; storyboard frames serve as reference, not first frame
- **Kling-3.0-Omni does not support img2video (first frame control)**; cannot use Omni when first frame control is needed
- **Seedance time segmentation = automatic multi-shot**; no additional parameters needed

---

## First and Last Frame Generation Strategy

| frame_strategy | Description | Execution Method |
|---|-------------|------------------|
| `none` | No first/last frame needed | Call text-to-video API directly |
| `first_frame_only` | First frame only | Generate first frame → image2video API |
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

## Dialogue Integration into video_prompt

When a shot contains dialogue, **it must be fully described in video_prompt**: character (including appearance), dialogue content (in quotes), expression/emotion, voice quality and speaking speed.

```json
{
  "shot_id": "scene1_shot5",
  "video_prompt": "Xiaomei (25-year-old Asian woman, long straight black hair) looks up at the server, smiling gently and says: 'It's really quiet here, I like it.' Voice is crisp and pleasant, speaking speed is moderate to slow. Maintain vertical 9:16 composition.",
  "dialogue": {
    "speaker": "Xiaomei",
    "content": "It's really quiet here, I like it.",
    "emotion": "Gentle, happy",
    "voice_type": "Crisp female voice"
  },
  "audio": {
    "enabled": true,
    "dialogue": {
      "speaker": "Xiaomei",
      "text": "It's really quiet here, I like it.",
      "emotion": "Gentle, happy"
    },
    "no_bgm": true
  }
}
```

---

## Narration Segmentation Planning (narration_segments)

**Trigger Condition**: After Phase 2 confirms "AI-generated narration" is needed, Phase 3 must plan narration segments when generating storyboard.

### Global Configuration (Root Level)

```json
{
  "narration_config": {
    "enabled": true,
    "voice_style": "Gentle female voice, moderate to slow speaking speed, full of emotion"
  },
  "narration_segments": [
    {
      "segment_id": "narr_1",
      "time_range": "0-3s",
      "target_shot": "scene1_shot1",
      "text": "It was a peaceful afternoon, sunlight streaming through the floor-to-ceiling windows into the cafe..."
    },
    {
      "segment_id": "narr_2",
      "time_range": "8-11s",
      "target_shot": "scene1_shot3",
      "text": "She sat by the window, gazing at the scenery outside, her thoughts drifting far away..."
    }
  ]
}
```

### Field Description

| Field | Type | Description |
|-------|------|-------------|
| `narration_config.enabled` | boolean | Whether narration is enabled |
| `narration_config.voice_style` | string | Globally unified narration style (consistent within one video) |
| `narration_segments` | array | Narration segment list |
| `segment_id` | string | Segment number (format: `narr_1`, `narr_2`...) |
| `time_range` | string | Timeline position (format: `0-3s`, `8-11s`, calculated from video start) |
| `target_shot` | string | Corresponding shot ID |
| `text` | string | Narration text for this segment |

### Planning Principles

1. **Timeline Continuity**: `time_range` is calculated from video start point (0 seconds), not shot internal time
2. **Segment Length**: Each narration segment should be speakable within 2-5 seconds (approximately 30-50 characters)
3. **Avoid Conflicts**: Narration time range should not overlap with character dialogue (sync sound)
4. **Shot Correspondence**: Each segment must correspond to a target_shot
5. **Voice Style Unity**: Use the same narration style within one video

### Narration Text Segmentation Tips

**Don't do this** (one big chunk):
```json
{
  "text": "It was a peaceful afternoon, sunlight streaming through the floor-to-ceiling windows into the cafe, she sat by the window, gazing at the scenery outside, her thoughts drifting far away, recalling that special summer."
}
```

**Do this** (segment by shot):
```json
{
  "narration_segments": [
    {"segment_id": "narr_1", "time_range": "0-3s", "target_shot": "scene1_shot1", "text": "It was a peaceful afternoon, sunlight streaming through the floor-to-ceiling windows into the cafe..."},
    {"segment_id": "narr_2", "time_range": "8-11s", "target_shot": "scene1_shot3", "text": "She sat by the window, gazing at the scenery outside..."},
    {"segment_id": "narr_3", "time_range": "15-18s", "target_shot": "scene2_shot1", "text": "Her thoughts drifted far away, recalling that special summer..."}
  ]
}
```

### Association with creative.json

After Phase 2 confirms narration requirement, `creative.json` records:
```json
{
  "narration": {
    "type": "ai_generated",
    "voice_style": "Gentle female voice",
    "full_text": "Complete narration text provided by user (if multiple segments)"
  }
}
```

When Phase 3 generates storyboard:
- Read `creative.narration.type`
- If `ai_generated`, plan `narration_segments`
- Segment `creative.narration.full_text` by shot timing
- Write `creative.narration.voice_style` to `narration_config.voice_style`

### audio Field Description

`audio` field uses object format, containing the following sub-fields:

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether to generate audio (including ambient sound + dialogue), default true |
| `dialogue` | object/null | Dialogue information, null means no dialogue |
| `dialogue.speaker` | string | Speaking character |
| `dialogue.text` | string | Dialogue content |
| `dialogue.emotion` | string | Emotion/tone |
| `no_bgm` | boolean | Whether to explicitly state "No background music" in prompt |

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
- `"ai_generated"` → All shots `audio.no_bgm = true` (BGM synthesized by Suno in post-production)
- `"user_provided"` → All shots `audio.no_bgm = true` (BGM provided by user)
- `"none"` → All shots `audio.no_bgm = false` (Video model decides freely)

`dialogue` field usage: TTS generation, subtitle extraction, quick user review.

**TTS narration is only for**: Opening/closing narration, scene descriptions that don't require character on-screen, emotional enhancement narration. **Do not use TTS for shots that can capture sync sound!**

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
        "visual_description": "25-year-old Asian woman, long straight black hair to waist, oval face..."
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
      "scene_name": "Opening - Cafe Encounter",
      "duration": 18,
      "narrative_goal": "Show female lead's daily life at the cafe",
      "spatial_setting": "Cozy urban cafe",
      "time_state": "3 PM",
      "visual_style": "Warm tones, cinematic feel",
      "shots": [
        {
          "shot_id": "scene1_shot1",
          "duration": 3,
          "shot_type": "establishing",
          "description": "Cafe panoramic view",
          "generation_mode": "text2video",
          "generation_backend": "kling",
          "video_prompt": "Cozy urban cafe interior panoramic view, afternoon sunlight streaming through floor-to-ceiling windows, camera slowly pushes in. Maintain vertical 9:16 composition. No background music. Natural ambient sound only.",
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

**elements.characters**: Character registry, written after Phase 1 identification
- `element_id`: Technical ID, format `Element_` + English name/Pinyin
- `name`: Chinese display name
- `name_en`: English name
- `reference_images`: Reference image path list
- `visual_description`: Visual feature description

**character_image_mapping**: Auto-generated mapping table (Phase 3), **Storyboard global field**
- Key: `element_id` (e.g., `Element_Chuyue`)
- Value: `image_N` tag (e.g., `image_1`)
- Mapping rule: Assign image_1, image_2... in characters array order
- Note: This field is at storyboard root level, not repeated inside shots

### Kling Omni Mode Example

```json
{
  "shot_id": "scene2_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "Xiaomei (<<<image_1>>>) wearing headphones, fully focused at the racing simulator. Vertical 9:16 composition.",
  "reference_images": ["materials/personas/xiaomei_ref.jpg"],
  "frame_strategy": "none",
  "image_prompt": "Cinematic realistic start frame... (optional, for storyboard frame generation)",
  "multi_shot": false,
  "audio": {
    "enabled": true,
    "dialogue": null,
    "no_bgm": true
  }
}
```

**Note**: Omni mode uses `reference_images` as reference images, does not use `frame_strategy` first frame control. `frame_strategy` should be set to `none`. If storyboard frame generation is needed, use `image_prompt` to record storyboard frame prompt separately.

---

## V3-Omni Two-Stage Structure (Recommended)

For Kling V3-Omni's **storyboard frame + video** two-stage generation workflow, a layered data structure is recommended.

### Relationship with Standard Structure

**V3-Omni three-layer structure is an extension of the standard Shot structure**, not a replacement:
- Standard structure fields (`shot_id`, `duration`, `generation_mode`, `generation_backend`, etc.) are retained
- Three-layer structure expands `image_prompt` and `video_prompt` into more detailed structured fields
- `character_image_mapping` is always at **Storyboard global level**, not repeated inside shots

### Field Mapping Table

| Standard Structure Field | V3-Omni Structure Equivalent | Description |
|-------------------------|------------------------------|-------------|
| `image_prompt` | `frame_generation.prompt` | Storyboard frame generation prompt |
| `video_prompt` | `video_generation.prompt` | Video generation prompt |
| `reference_images` | Auto-added after `frame_generation` generates | Storyboard frame output + character reference images |
| `frame_strategy` | Always `"none"` | Omni does not use first frame control |

### Design Philosophy

**Storyboard Frame**: Not just first frame control, but also controls overall visual (scene, style, lighting, atmosphere, color, makeup/styling)

**Video Generation**: References storyboard frame composition, overlays action and character references

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
    "chinese_description": "Continuous action and dialogue (approx 7s) wide shot. Chuyue frantically backs out the door...",
    "shot_scale": "Wide shot",
    "location": "Men's restroom entrance transition area",
    "dialogue_segments": [
      {"time": "0-2s", "speaker": "Chuyue", "line": "Okay, I admit...", "emotion": "Awkward apologetic smile"},
      {"time": "2-4s", "speaker": "Tianyu", "line": "Then don't look like you've seen a ghost.", "emotion": "flat"}
    ],
    "transition": "cut"
  },

  "frame_generation": {
    "output_key": "scene1_shot1_frame",
    "prompt": "Cinematic realistic start frame...",
    "character_refs": ["Element_Chuyue", "Element_Jiazhi", "Element_Tianyu"],
    "scene": "Men's restroom entrance, white tiles...",
    "lighting": "Cool white fluorescent light",
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

**Note**: `character_image_mapping` is always at **Storyboard global level**, not repeated inside shots. V3-Omni structure uses `frame_generation.character_refs` to reference characters.

**storyboard layer** (Chinese, for human review)
- `chinese_description`: Plot description
- `shot_scale`: Shot scale (wide/medium/close-up, etc.)
- `location`: Scene location
- `dialogue_segments`: Dialogue timeline
- `transition`: Transition effect

**frame_generation layer** (generate storyboard frame)
- `output_key`: Output filename
- `prompt`: Complete Image Prompt
- `character_refs`: Referenced character elements
- `scene`: Scene description
- `lighting`: Lighting description
- `camera`: Camera parameters (shot_scale, angle, lens)
- `style`: Visual style

**video_generation layer** (generate video)
- `frame_reference`: Referenced storyboard frame output_key
- `prompt`: Complete Video Prompt
- `motion_overall`: Overall action description
- `motion_segments`: Segmented actions (with timeline)
- `camera_movement`: Camera movement
- `sound_effects`: Sound design

---

## Multi-Shot Mode (Kling / Kling Omni)

Both Kling and Kling Omni support multi-shot continuous recording.

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

- **intelligence**: AI auto storyboarding, suitable for simple narratives
- **customize** (recommended): Precise control of each shot's content and duration

### Multi-Shot Rules

- Total duration 3-15s, each shot at least 1s
- All shot durations sum = total video duration

| Scenario | Recommended Mode |
|----------|-----------------|
| Narrative video (story, advertisement) | multi_shot + customize |
| Simple narrative | multi_shot + intelligence |
| Material montage (vlog, showcase) | Single shot generation one by one |
| Simple short video (<10s) | Single shot text2video |

---

## Review Check Mechanism

After generating storyboard, must check the following items:

**1. Structural Completeness**
- Total duration matches target duration (±2 seconds)
- Scene duration = sum of subordinate shot durations

**2. Storyboard Rules**
- Each shot duration 2-5 seconds
- No multi-action shots, no in-shot spatial changes

**3. Prompt Standards**
- All video_prompt contains aspect ratio information
- Dialogue integrated into video_prompt
- No abstract action descriptions

**4. Technical Selection**
- T2V/I2V selection is reasonable
- Backend selection matches requirements
- First/last frame strategy is correct

---

## User Confirmation Display (Mandatory Step)

**Must wait for explicit user confirmation before entering Phase 4!**

When confirming, display for each shot: scene information, generation mode, backend, video_prompt, image_prompt (if any), dialogue, transition, duration.

User can choose: Confirm and execute / Modify storyboard / Adjust duration / Change transition / Cancel.

---

## fallback_plan Field (Fallback Plan)

In Phase 3 storyboard generation, it's recommended to reserve a fallback plan for each shot to avoid ad-hoc `image_prompt` writing.

### Field Structure

```json
{
  "shot_id": "scene1_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "...",
  "reference_images": ["materials/personas/xiaomei_ref.jpg"],
  "frame_strategy": "none",

  "fallback_plan": {
    "mode": "img2video",
    "backend": "kling",
    "image_prompt": "Cinematic realistic start frame.\nScene: ...\nLighting: ...\nCharacter: Referencing <<<image_1>>> appearance...\nStyle: ...",
    "frame_strategy": "first_frame_only",
    "frame_output": "generated/frames/{shot_id}_frame.png",
    "reason": "Fallback when Omni API is unavailable"
  }
}
```

### Field Description

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | Fallback generation mode: `img2video` or `text2video` |
| `backend` | string | Fallback backend: `kling` or `vidu` |
| `image_prompt` | string | Complete prompt for generating storyboard frame (required for fallback) |
| `frame_strategy` | string | Fallback first frame strategy: `first_frame_only` |
| `frame_output` | string | Storyboard frame output path template |
| `reason` | string | Fallback reason description |

### Fallback Processing Flow

When fallback is needed:

1. Read shot's `fallback_plan` field
2. Copy the following fields from `fallback_plan` to shot main fields:
   - `generation_mode` ← `fallback_plan.mode`
   - `generation_backend` ← `fallback_plan.backend`
   - `frame_strategy` ← `fallback_plan.frame_strategy`
   - `image_prompt` ← `fallback_plan.image_prompt`
3. Clear or adjust `reference_images` (img2video doesn't need character reference images)
4. Execute fallback generation flow

### Example: Shot After Fallback

```json
// Before fallback
{
  "shot_id": "scene1_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "Xiaomei (<<<image_1>>>) by the cafe window...",
  "reference_images": ["materials/personas/xiaomei_ref.jpg"],
  "frame_strategy": "none",
  "fallback_plan": {
    "mode": "img2video",
    "backend": "kling",
    "image_prompt": "Cinematic start frame. 25-year-old Asian woman...",
    "frame_strategy": "first_frame_only"
  }
}

// After fallback (fallback_plan fields copied)
{
  "shot_id": "scene1_shot1",
  "generation_mode": "img2video",
  "generation_backend": "kling",
  "video_prompt": "Xiaomei by the cafe window...",  // <<<image_1>>> reference removed
  "reference_images": [],
  "frame_strategy": "first_frame_only",
  "image_prompt": "Cinematic start frame. 25-year-old Asian woman...",
  "frame_path": "generated/frames/scene1_shot1_frame.png",
  "fallback_plan": { ... }  // Keep original plan, can fallback again
}
```

### Scenarios Not Requiring fallback_plan

- Pure `text2video` shots (no reference images needed, fallback is meaningless)
- User explicitly states no fallback accepted
- Simple prototypes, no need to guarantee character consistency

---

## Seedance Smart Scene Switching Mode

**Core Feature**: Time segment prompt auto-triggers multi-shot, execution phase merges multiple shots in same scene into one API call.

**✅ Duration Support: Any integer 4-15s**

In **Phase 3 storyboard design phase**, when selecting Seedance backend, scene total duration can be **any integer between 4 and 15 seconds** (e.g., 6s, 8s, 12s, etc., no longer limited to 5/10/15).

### Design Phase Duration Planning (Phase 3)

**Seedance Backend Duration Design Rules**:

| Scene Total Duration | ✅ Supported |
|---------------------|--------------|
| Any integer 4-15s | ✓ |

**Design Flow**:
```
Select Seedance → Determine scene total duration (any integer within 4-15s range) → Allocate shot durations
```

**Examples**:
- Target 15s scene → shots: 3s + 3s + 4s + 5s = 15s ✓
- Target 10s scene → shots: 3s + 3s + 4s = 10s ✓
- Target 8s scene → shots: 3s + 5s = 8s ✓ (newly supported!)
- Target 18s scene → ✗ Exceeds range, needs splitting into two scenes

### Design Principles

**Shot Structure Remains Unchanged**: Seedance only merges in execution phase, doesn't change storyboard's `scenes → shots` structure.

| Model | Execution Method |
|-------|-----------------|
| Kling/Vidu/Omni | Each shot calls API separately |
| **Seedance** | Multiple shots in same scene merged into one API call (time segment prompt) |

### Scene → Video Segment Division Rules

| Scene Duration | Shot Count | Video Segment Planning |
|---------------|------------|------------------------|
| ≤15s | Any number (e.g., 3-5 shots) | **Single video segment**, time segments cover all shots |
| 16-30s | Many (e.g., 6-10 shots) | **2-3 video segments**, segmented coverage (e.g., 15s + 15s) |
| >30s | Very many (e.g., >10 shots) | **3+ video segments**, segmented coverage |
| Scene switch | - | **Independent video segments each**, no cross-Scene merge |

### Execution Phase Processing Flow

**Example**: Scene 1 contains 4 shots (total duration 15s)

```json
{
  "scene_id": "scene_1",
  "shots": [
    {"shot_id": "scene1_shot1", "duration": 3, "description": "Pick apple"},
    {"shot_id": "scene1_shot2", "duration": 3, "description": "Put into shaker cup"},
    {"shot_id": "scene1_shot3", "duration": 4, "description": "Finished product close-up"},
    {"shot_id": "scene1_shot4", "duration": 5, "description": "Raise cup to display"}
  ]
}
```

**Seedance Execution Logic**:

1. Identify `generation_backend = "seedance"`
2. Merge scene_1's 4 shots (total 15s) into one API call
3. Generate storyboard frame (one per video segment)
4. Generate time segment prompt:
   ```
   0-3s: Pick apple...;
   3-6s: Put into shaker cup...;
   6-10s: Finished product close-up...;
   10-15s: Raise cup to display...;
   ```
5. Call Seedance API

### Time Segment Prompt Format

```
Referencing the {segment_id}_frame composition for scene layout and character positioning.

@image1 (character reference image), [perspective setting] [subject/style];

Overall: [Overall camera action overview]

Segmented actions ({duration}s):
0-Xs: [scene] + [action] + [camera movement] + [rhythm] + [sound effect/dialogue];
X-Xs: [cut] + [scene] + [action] + [camera movement] + [rhythm] + [sound effect/dialogue];
...

Maintain {ratio} composition, do not break frame ratio
{BGM constraint}
```

### image_urls Order Convention

| index | Purpose | Reference Method |
|-------|---------|------------------|
| `image_urls[0]` | Storyboard frame | `Referencing the {segment_id}_frame composition...` |
| `image_urls[1]` | Character reference image 1 | `@image1` |
| `image_urls[2]` | Character reference image 2 | `@image2` |

### Seedance Storyboard Annotation Example

```json
{
  "shot_id": "scene1_shot1",
  "duration": 3,
  "generation_mode": "seedance-video",
  "generation_backend": "seedance",
  "video_prompt": "Your hand picks a dew-covered Aksu red apple, fixed camera, steady rhythm, crisp apple collision sound",
  "reference_images": [
    "generated/frames/scene1_frame.png",
    "materials/personas/xiaomei_ref.jpg"
  ],
  "frame_strategy": "none",
  "seedance_merge_info": {
    "merged_shots": ["scene1_shot1", "scene1_shot2", "scene1_shot3", "scene1_shot4"],
    "total_duration": 15,
    "segment_index": 0
  }
}
```

### Limitations and Notes

| Limitation | Description |
|------------|-------------|
| Duration range 4-15s | Any integer, no longer limited to 5/10/15 |
| Maximum 720p | Use Kling/Vidu for 1080p |
| No precise first frame control | Storyboard frame is reference, not first frame |
| Image reference syntax | Use `@imageN` (not `<<<image_N>>>`) |