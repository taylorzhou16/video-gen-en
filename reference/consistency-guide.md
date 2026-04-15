# Consistency Guide

This document defines the principles for cross-shot consistency review, for reference during Phase 3.5 automatic review of storyboard.json by the model.

---

## Review Principles Overview

| Principle | Detection Scope | Core Requirement |
|-----------|-----------------|------------------|
| **1. Time-Lighting Consistency** | All shots within the same scene | Lighting description must be semantically consistent with `time_state` |
| **2. Spatial Element Consistency** | All shots within the same scene | Key element descriptions must maintain style consistency (not just name matching) |
| **3. Character Costume/Makeup Consistency** | All shots within the same scene | Costume/hair/makeup must be locked, unless plot requires change |
| **4. image/video Description Matching** | Within the same shot | image_prompt and video_prompt descriptions of the same element must match |
| **5. Cross-scene Asset Continuity** | Multiple consecutive scenes | Key assets (character costume, scene layout) should maintain visual continuity |

---

## Principle 1: Time-Lighting Consistency

### Rule

All lighting descriptions in shots within the same scene must be semantically consistent with `time_state`.

**`time_state` defines the scene's time context and lighting baseline**, all `image_prompt` Lighting lines and `video_prompt` lighting descriptions should inherit `time_state`.

### Forbidden Word Reference Table

| time_state Value | Forbidden Lighting Descriptions |
|------------------|--------------------------------|
| "spring afternoon", "afternoon", "daytime" | "twilight", "evening", "sunset", "golden hour (specifically before sunset)", "night", "moonlight" |
| "twilight", "sunset", "sunset" | "morning", "early morning", "noon", "night" |
| "night", "night" | "daytime", "sunlight", "twilight" |

### Exception Cases

If the plot explicitly requires time progression (e.g., "from afternoon to twilight"), it needs to be explained in the scene's `narrative_goal` or the shot's `description`.

**Example**:
```
narrative_goal: "Show protagonist's time progression from afternoon reading to twilight finishing work"
→ shot_1: afternoon lighting ✓
→ shot_2: twilight lighting ✓ (has plot explanation)
```

### Detection Example

```
time_state: "Spring afternoon, soft sunlight"
shot_1 Lighting: "Warm afternoon sunlight, soft golden glow" → ✓ Consistent
shot_2 Lighting: "Twilight light, low angle backlight" → ❌ Conflict, should fix
shot_3 Lighting: "Dramatic sunset lighting" → ❌ Conflict, should fix
```

---

## Principle 2: Spatial Element Consistency

### Rule

All descriptions of key scene elements in shots within the same scene must maintain **style consistency**, not just matching names but with style drift.

**`spatial_setting` defines the scene's spatial layout and key element styles**, all shot's `image_prompt` Scene lines and `video_prompt` scene descriptions should inherit these elements.

### Style Lock Requirements

Not only should element names match, but style descriptions should also be consistent:

| spatial_setting Description | Shot Description | Judgment |
|-----------------------------|------------------|----------|
| "weeping willow (long drooping branches)" | "weeping willow branches drooping" | ✓ Name + style consistent |
| "weeping willow (long drooping branches)" | "weeping willow" | ⚠️ Name consistent but style needs completion |
| "weeping willow (long drooping branches)" | "old tree" / "dead tree" / "ancient willow" | ❌ Semantic drift |
| "stone path (grey-blue)" | "grey stone path" | ✓ Consistent |
| "stone path (grey-blue)" | "dirt path" / "grass" | ❌ Drift |

### Element Forbidden Drift Words

| Key Element | Forbidden Drift Words | Reason |
|-------------|----------------------|--------|
| Weeping willow | "dead", "old", "twisted", "thick", "ancient" | Will change tree's visual form |
| Stone path | "dirt", "mud", "grass", "sand" | Will change ground material |
| Waterside pavilion | "dilapidated", "ruined", "ruins" | Will change building state |
| Green-blue tones | "yellow", "red", "warm tones" | Will change overall color scheme |

### Detection Example

```
spatial_setting: "Under weeping willow, stone path, waterside pavilion"
shot_1 Scene: "Weeping willow branches drooping, grey stone path" → ✓ Consistent
shot_2 Scene: "Under old tree, sparse willow branches" → ❌ "old tree" drift, should be "weeping willow"
shot_3 Scene: "Dead willow tree, dirt path" → ❌ Multiple drifts
```

---

## Principle 3: Character Costume/Makeup Consistency

### Rule

The same character within the same scene (without explicit costume change) must have locked costume/hair/makeup.

**The character's `visual_description` or `locked_costume` defines the costume baseline**, all shot descriptions of that character's costume/hair must be consistent.

### Field Definition

```json
{
  "element_id": "Element_LinDaiyu",
  "locked_costume": "Light green wide-sleeve robe, beige cross-collar inner garment, dark green wide waistband",
  "locked_hairstyle": "Classical high bun, hanging rings on both sides",
  "locked_makeup": "Slender willow-leaf eyebrows, light pink lip color, fair base makeup",
  "costume_scope": "scene_1, scene_2"  // Scope (optional)
}
```

### Scope Explanation

- `costume_scope` specifies which scenes the character's costume remains consistent
- Empty means global consistency (all scenes)
- Multiple scenes separated by comma
- When costume change is needed, update lock fields at new scene start and set new scope

### Cross-scene Costume Change Rules

If the plot requires costume change (e.g., change to sleepwear after bathing), it needs to be updated in the scene's `narrative_goal` or the new scene's `locked_costume`.

**Without explicit costume change explanation, default inherit previous scene's costume**.

### Detection Example

```
Character: Lin Daiyu, locked_costume="light green silk skirt"
shot_1: "Light green robe" → ✓ Consistent
shot_2: "White silk skirt" → ❌ Color drift, should be "light green"
shot_3: "Plain Hanfu" → ❌ Description vague, should specify color
```

---

## Principle 4: image/video Description Matching

### Rule

Descriptions of the same element in the same shot's `image_prompt` and `video_prompt` must match.

**image_prompt determines the storyboard image's visual baseline**, **video_prompt determines the video's dynamic consistency**, both should match in descriptions of key elements (scene, character, props).

### Detection Focus

| Element Type | image_prompt Location | video_prompt Location | Detection Content |
|--------------|----------------------|----------------------|-------------------|
| Scene element | Scene line | Scene description | Element name + style |
| Lighting | Lighting line | Lighting description | Time + lighting feature |
| Character costume | Character line | Character reference | Costume color + style |

### Detection Example

```
shot_1:
  image_prompt: "Weeping willow branches drooping, spring sunlight"
  video_prompt: "Ancient tree swaying, twilight light" → ❌ Multiple mismatches
  
  Fix suggestion:
  video_prompt: "Weeping willow branches swaying, spring afternoon soft sunlight"
```

---

## Principle 5: Cross-scene Asset Continuity

### Rule

If multiple scenes belong to the same "narrative continuum", key assets should maintain visual consistency.

### Narrative Continuum Judgment

**Belongs to narrative continuum**:
- Multiple scenes with similar `spatial_setting` and close time
- Continuous narrative segments (e.g., different perspectives of the same event)

**Does not belong to narrative continuum**:
- Obvious scene switches between scenes (e.g., "indoors → outdoors", "day → night")
- Independent narratives of different events

### Continuity Requirements

| Asset Type | Continuum Requirement | Non-continuum |
|------------|----------------------|---------------|
| Character costume | Default locked (unless plot costume change) | Can be independently designed |
| Scene layout | Keep consistent (willow position, building orientation) | Can be redesigned |
| Time state | Logical progression (cannot jump too much) | Can be independently set |

### Detection Example

```
scene_1: time_state="2 PM", spatial_setting="Under weeping willow"
scene_2: time_state="4 PM", spatial_setting="Under weeping willow" → ✓ Continuum, assets consistent

scene_1: time_state="afternoon"
scene_2: time_state="night" → ⚠️ Need to check if plot has time jump explanation
```

---

## Review Output Format

After model reviews storyboard.json, output in the following format:

```
📋 Consistency Review Result

【Issues Found】

1. [scene_1/scene1_shot2] Time inconsistency:
   - time_state: "Spring afternoon, soft sunlight"
   - Lighting: "Twilight light" → Should be "Spring afternoon soft sunlight"

2. [scene_2/scene2_shot4] Spatial drift:
   - spatial_setting: "Under weeping willow"
   - Scene description: "Under old tree" → Should be "Under weeping willow"

3. [scene_2/scene2_shot3] Character costume drift:
   - Character Lin Daiyu locked_costume: "Light green silk skirt"
   - Description: "White long skirt" → Should be "Light green silk skirt"

【Fix Suggestions】

Fix scene_1/scene1_shot2 image_prompt Lighting line:
Original: "Twilight light, low angle backlight"
Fix to: "Spring afternoon soft sunlight, warm tones, dappled shadows"

Fix scene_2/scene2_shot4 image_prompt Scene line:
Original: "Under old tree, sparse willow branches"
Fix to: "Under weeping willow, long drooping branches, spring garden"

Fix scene_2/scene2_shot3 image_prompt character costume description:
Original: "White long skirt"
Fix to: "Light green silk skirt, matching locked_costume"

---

Found N consistency issues, auto-fixed.
```

---

## Review Execution Flow

**Trigger Time**: After Phase 3 storyboard design completion, automatically execute

**Flow Steps**:

1. Read `storyboard.json`
2. Iterate through all scenes and shots, check by above 5 principles
3. Find issue → Record issue + Generate fix suggestion
4. Auto apply fix suggestions (modify storyboard.json)
5. Save fixed storyboard.json
6. Output review result to notify user

**No User Confirmation Required**: When obvious inconsistency issues are found, fix directly, then notify user.