# Premium Quality Upgrade — Design Spec

**Date:** 2026-06-24
**Status:** Approved
**Goal:** Upgrade the Luminous Will video pipeline to match premium dark motivation YouTube channels (Motiversity, Mulligan Brothers tier). Every output should look naturally cinematic, not like stock footage with filters.

---

## 1. Config & Font Setup

### New environment variables (`.env`)
```
STORYBLOCKS_API_KEY=your_key
STORYBLOCKS_API_SECRET=your_secret
EPIDEMIC_SOUND_API_KEY=           # future slot, empty by default
```

### New config entries (`config.py`)
- `STORYBLOCKS_API_KEY`, `STORYBLOCKS_API_SECRET` loaded from `.env`
- `EPIDEMIC_SOUND_API_KEY` loaded from `.env` (empty = disabled)
- `CAPTION_FONT_FILE` pointing to `assets/fonts/Montserrat-Bold.ttf`
- `ken_burns_enabled: True` global toggle in each format profile
- `crossfade_duration: 1.0` in each format profile
- `voiceover_boost_db: 1.5` and `music_level_db: -9` in each format profile

### Font setup
- Download Montserrat-Bold.ttf from Google Fonts into `assets/fonts/`
- `captions.py` loads from `config.CAPTION_FONT_FILE`
- Fallback to Arial if font file missing

---

## 2. Caption Animations — Word-by-Word Reveal

### How it works
- `captions.py` already stores individual word timing in each caption event (`"words": [...]` with `start`/`end` per word)
- `render_caption_frame` receives a new parameter: `current_time`
- At render time, each word in the chunk is checked against `current_time`:
  - **Before word's start time** — invisible (not drawn)
  - **During word's start to start+0.08s** — scale-in from 90% to 100% with slight opacity ramp
  - **After settled** — fully visible, normal size
  - **Highlight word** — amber color (#E8A817) as before, same animation

### Font change
- Montserrat Bold replaces Arial Bold throughout
- Same stroke width, same positioning, same highlight color

### Assembler integration
- `burn_captions` in `video_assembler.py` passes `t` (current playback time) through to the renderer
- Cache invalidation updated to account for time-dependent rendering

---

## 3. Ken Burns Effect — Selective, Not Blanket

### Per-segment motion style
Each script segment gets a `motion_style` field:
- `"static"` — no effect, clip plays as-is (most clips)
- `"ken_burns_zoom"` — slow zoom in, for still subjects (chess, silhouette, portrait)
- `"ken_burns_pan"` — slow horizontal pan, for wide shots (landscape, cityscape, mountain)
- `"slow_zoom_out"` — slow pull-back, for establishing shots

### How the style is chosen
- **Long-form (Gemini):** Gemini picks `motion_style` per segment in the script generation prompt
- **Short-form (templates):** Heuristic based on visual keywords:
  - Keywords contain landscape/cityscape/mountain/ocean/highway → `"ken_burns_pan"`
  - Keywords contain chess/silhouette/portrait/statue/room → `"ken_burns_zoom"`
  - Keywords contain running/boxing/training/walking/driving → `"static"` (already has motion)
  - Default → `"static"`

### Implementation in `video_assembler.py`
- Applied during `create_base_video` before color grading
- Zoom: 1.0x to 1.12x over clip duration (subtle, not distracting)
- Pan: 5% horizontal drift over clip duration
- Zoom out: 1.12x to 1.0x over clip duration

---

## 4. Premium Stock Footage — Storyblocks Integration

### Fallback chain in `visuals.py`
1. **Storyblocks** (if `STORYBLOCKS_API_KEY` set) — search API, download 4K/HD clips
2. **Pexels** (existing, unchanged)
3. **Pixabay** (existing, unchanged)

### Storyblocks API integration
- REST API: search endpoint with keyword query
- Filters: resolution (prefer 4K, accept 1080p+), orientation (portrait/landscape per format), duration
- Same `_score_video_relevance` scoring adapted for Storyblocks metadata
- Track used IDs to prevent reuse within the same video
- Downloads via CDN endpoint

### Scoring improvements (all sources)
- **+1 score** for 4K resolution
- **+1 score** for matching orientation (portrait for shorts, landscape for long-form)
- **+1 score** for clip duration > segment duration (avoids looping)
- **Reject** clips under 720p resolution
- **Prefer** 1080p+, accept 720p as fallback
- Looping only as absolute last resort

### No changes to existing Pexels/Pixabay code
Storyblocks layer sits on top. When no API key is set, the pipeline behaves exactly as before.

---

## 5. Premium Music — Storyblocks + Future Epidemic Sound

### Fallback chain in `music.py`
1. **Storyblocks Music** (if API key set) — search by mood, download full-quality track
2. **Local library** (existing, unchanged) — mood subfolders + tagged files
3. **Freesound** (existing, unchanged) — last resort

### Storyblocks Music API
- Search with mood/genre filters mapped from the 4 mood categories:
  - `dark` → "dark ambient cinematic suspense"
  - `intense` → "intense epic cinematic trailer"
  - `reflective` → "reflective cinematic piano"
  - `powerful` → "powerful epic triumphant orchestra"
- Filter: instrumental only, duration 2-5 minutes
- Download full-quality track (not preview)

### Epidemic Sound (future slot)
- `EPIDEMIC_SOUND_API_KEY` in config, empty by default
- Placeholder function `_epidemic_sound_search()` that returns `None`
- When active, sits above Storyblocks in the chain

---

## 6. Audio Mixing — dB-Based, No Ducking

### Levels (match user's CapCut workflow)
| Track | Level |
|---|---|
| Voiceover | +1.5 dB boost |
| Background music | -9 dB constant |

### Implementation in `video_assembler.py`
- Replace percentage-based volume (`music.with_volume_scaled(0.32)`) with dB-based gain
- Convert: `linear_gain = 10^(dB/20)` — so -9dB ~ 0.35x, +1.5dB ~ 1.19x
- **Same level throughout** — no ducking, no dynamic volume changes
- Remove ducking system entirely (delete `music_mode: "ducking"` and related code)
- Both formats use identical mixing: flat music at -9dB
- Keep music fade-in (2s) and fade-out (3s)

### Config entries per format profile
- `voiceover_boost_db: 1.5`
- `music_level_db: -9`

---

## 7. Voiceover Validation & Cleanup

### Pre-send: Clean script text
Before sending to ElevenLabs (zero cost):
- Replace `...` with `.`
- Replace `--` and `—` with `,`
- Strip double spaces, unusual characters
- Normalize quotes/apostrophes to standard ASCII

### Post-download: Validate
| Check | Threshold | Action |
|---|---|---|
| File corrupt/truncated | Size < 10KB or duration 0s | Retry once |
| Duration way off | >30% shorter than expected | Retry once |
| Volume spike (glitch) | >3x surrounding RMS in any 0.1s window | Retry once |
| Long pauses | >1.5s silence between sentences | Auto-trim to 0.8s |
| Edge glitch | Spike in first/last 0.5s | Trim it off (no retry) |

### Post-trim: Recalculate timestamps
- If any pauses are trimmed, rebuild the word timestamp array
- Every word after the trim point shifts earlier by the trimmed amount
- Ensures captions stay perfectly synced

### Retry policy
- Max 1 retry per generation
- Only retry for actual corruption (unloadable, 0 duration, <10KB)
- Trimmable issues (pauses, edge glitches) are fixed, not retried
- If retry also fails, continue with best attempt + log warning

---

## 8. Smooth Transitions — Context-Aware Mix

### Transition types
| Transition | When | Why |
|---|---|---|
| **Crossfade (1.0s)** | Mood/scene change, reflective moments, slow visuals | Smooth emotional flow |
| **Hard cut (0s)** | Same energy continues, action footage, intense moments | Keeps momentum, punchy |

### How the transition is chosen per segment
- **Long-form (Gemini):** Gemini assigns `transition: "crossfade"` or `"cut"` per segment
- **Short-form (templates):** Heuristic:
  - Mood changes between consecutive segments → crossfade
  - Same mood continues → hard cut
  - First segment → crossfade (clean open)
  - Last segment before outro → crossfade (clean close)

### Config
- `crossfade_duration: 1.0` in format profile (used when crossfade is selected)
- Hard cuts are 0s by definition

---

## 9. Adaptive Color Grading — Premium Cinematic Look

### Goal
Every clip looks like it was naturally shot on a cinema camera in dark, moody conditions. Not like stock footage with a filter. Natural, premium, sophisticated.

### Upgrade from mechanical to cinematic grading

| Current (mechanical) | Premium (natural) |
|---|---|
| Linear brightness multiply | **S-curve contrast** — cinematic film-look, smooth rolloff in shadows and highlights |
| Flat desaturation | **Selective saturation** — mute greens/reds (distracting), preserve blues/golds (brand colors) |
| Linear contrast boost | **Lift-Gamma-Gain** model — industry standard, controls shadows/mids/highlights independently |
| Hard black crush | **Smooth shadow rolloff** — blacks are deep but retain detail, not clipped |
| Same grade for every clip | **Adaptive intensity** — reads each clip's brightness, adjusts grade strength |

### Adaptive intensity
Sample the first frame of each clip to measure average brightness:
- **Already dark** (avg brightness <30%) → light touch: 80% grade intensity, skip aggressive darkening
- **Medium** (30-60%) → full standard grade
- **Bright** (>60%) → aggressive grade: extra darkening, stronger desaturation

### Brand constants (always applied regardless of adaptive level)
- Split toning: cool blue shadows + warm amber highlights
- Subtle vignette
- Selective saturation: preserve blues and golds, mute greens and reds
- All output matches the Luminous Will dark premium aesthetic

---

## Files Modified

| File | Changes |
|---|---|
| `config.py` | New API keys, font config, dB mixing values, Ken Burns toggle, crossfade duration |
| `captions.py` | Montserrat font, word-by-word reveal animation, time-aware rendering |
| `video_assembler.py` | Ken Burns per clip, context-aware transitions, dB-based audio mixing, remove ducking |
| `visuals.py` | Storyblocks search+download layer, scoring improvements (resolution, orientation, duration) |
| `music.py` | Storyblocks music search layer, Epidemic Sound placeholder |
| `voiceover.py` | Script text cleaning, post-download validation, pause trimming, timestamp recalculation |
| `color_grading.py` | S-curve contrast, lift-gamma-gain, selective saturation, adaptive intensity |
| `script_generator.py` | Add `motion_style` and `transition` fields to Gemini prompt + template heuristics |

## New Files

| File | Purpose |
|---|---|
| `assets/fonts/Montserrat-Bold.ttf` | Custom caption font (Google Fonts, free) |

## No Changes To

| File | Reason |
|---|---|
| `main.py` | Pipeline flow unchanged, just better quality at each step |
| `brand_reference.py` | Brand rules unchanged |
| `queue_manager.py` | Scheduling unchanged |
| `scheduler.py` | Scheduling unchanged |
| `publisher.py` | Publishing unchanged |
| Platform adapters | Upload logic unchanged |
