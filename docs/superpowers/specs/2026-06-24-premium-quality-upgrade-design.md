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

## 10. Script Generation Overhaul — Gemini for Both Formats

### Goal
Both short-form and long-form use Gemini for script generation. Scripts are fresh, trending, deeply personal, with viral hooks. Simple language everyone understands.

### Delete
- All 5 hardcoded template scripts
- `get_template_script()` function
- `HOOK_TEMPLATES` list
- `_chain_template_scripts()` fallback
- Keep a minimal emergency fallback (10 pre-written hooks + simple segments) only for when Gemini API is completely down

### Topic Discovery
Gemini generates 10 fresh topic ideas per batch based on:
- Dark motivation / stoic philosophy / psychology of power niche
- What's trending in self-improvement content
- Emotional triggers: loneliness, betrayal, self-doubt, being underestimated, silent strength
- Filter against `generated_history.json` to avoid exact repeats

### Generated History — Fresh Angles, Not Banned Topics
`generated_history.json` stores every generated video's topic + hook + angle summary:
```json
[
  {"topic": "Power of Silence", "hook": "The most powerful people never raise their voice", "angle": "psychological authority through silence", "date": "2026-04-27"},
  {"topic": "High value solitude", "hook": "If you're always alone, this message is for you", "angle": "loneliness as sign of outgrowing environment", "date": "2026-04-27"}
]
```

Gemini's prompt includes this history with the instruction:
> "You MAY revisit these topics but you MUST take a completely different angle and a different hook. Never repeat the same opening or narrative structure."

**Pre-seeded with existing 17 videos:**
1. Being average is not a choice
2. Cheap Dopamine
3. Comfort is a threat
4. Debt of discipline
5. Emotional Detachment
6. Execution matters the most
7. Focus on the present
8. High value solitude
9. How to achieve flow state
10. Human Loyalty
11. Master your emotions
12. Power of Silence
13. Procrastination
14. Stop waiting too long
15. The quiet leader vs the loud victim
16. Validation
17. Why real life feels boring now

### Script Generation Prompt Rules
- **Simple language** — max 8th grade reading level, no fancy words, no jargon
- **Personal hooks** — use "you" constantly, make the viewer feel directly spoken to
- **Emotional triggers** — loneliness, betrayal, self-doubt, being underestimated, silent strength
- **Short punchy sentences** — max 15 words per segment
- **Brand voice** — stoic, commanding, no fluff, no cliches ("grind", "hustle", "manifest"), dark intense energy

### Hook Formula Patterns (embedded in Gemini prompt)
```
"If you [common painful experience], this is for you."
"Nobody tells you this about [relatable topic]."
"The reason you [common struggle] isn't what you think."
"Stop [common mistake]. Here's why it's destroying you."
"They don't want you to know this about [topic]."
```

### Short-form Script Structure (Gemini-generated)
- 25 segments, 60-90 seconds
- One strong hook → build tension → deliver truth → close with impact
- Each segment: `text`, `visual_keywords`, `visual_keywords_alt`, `mood`, `emphasis_word`, `motion_style`, `transition`

### Long-form Script Structure (Gemini-generated, unchanged)
- 50 segments, 8-12 minutes
- Narrative arc: hook → setup → escalation → climax → resolution → callback
- Same fields as short-form plus `chapter` markers

### Hook Validation
- After generation, check that the first segment uses a strong personal hook pattern
- If too generic (doesn't contain "you" or a direct emotional trigger), regenerate just the hook (cheap — one sentence)

---

## 11. 4K Output Option

### Resolution settings per format profile
| Format | Default | 4K mode |
|---|---|---|
| Short (9:16) | 1080x1920 | 2160x3840 |
| Long (16:9) | 1920x1080 | 3840x2160 |

### Implementation
- New CLI flag: `python main.py --format short --quality 4k`
- Default stays 1080p (faster renders for daily use)
- 4K for maximum quality (special videos, YouTube long-form)
- Bitrate scales: 15000k → 30000k for 4K
- Ken Burns and captions render at target resolution
- Config: `quality` field in format profile (`"1080p"` or `"4k"`)

---

## 12. Premium Thumbnails

### Frame selection — pick the most visually striking frame
- Sample 20-30 frames evenly across the video (after color grading)
- Score each frame on:
  - **Visual contrast** — high contrast = eye-catching
  - **Subject presence** — frames with a clear subject (silhouette, figure, animal) beat empty landscapes
  - **Color interest** — frames with amber/blue split toning popping
  - **Sharpness** — reject blurry frames
- Pick the top-scoring frame as the base

### Text — bold, minimal, emotional
- Gemini generates a **2-3 word punch line** from the topic (not the full title):
  - "Power of Silence" → **"STAY SILENT"**
  - "Comfort is a threat" → **"COMFORT KILLS"**
  - "Being average is not a choice" → **"NEVER AVERAGE"**
- All caps, Montserrat Bold, massive font size
- White text with heavy black stroke + subtle amber outer glow
- Positioned to complement the frame, not cover the subject

### Visual treatment
- Dark vignette intensified (heavier than video — thumbnails need more punch at small size)
- Slight warm color boost on the subject area (draws the eye)
- Bottom gradient for text readability if text is at bottom

### Goal
Looks like a designer made it in Photoshop — not auto-generated. Should compete with Motiversity thumbnails at a glance.

---

## 13. Social Media Captions — Viral-Optimized Per Platform

### Caption style per platform
| Platform | Style | Length | Hashtags |
|---|---|---|---|
| **TikTok** | One punchy line + hashtags | 1-2 sentences max | 5-7 trending + niche |
| **Instagram Reels** | Hook line + CTA + hashtags | 2-3 sentences | 10-15 mixed (broad + niche) |
| **Facebook** | Slightly longer, emotional pull | 2-3 sentences | 3-5 only |
| **YouTube Shorts** | Title is the hook, description has keywords | Title: 5-8 words | Tags in description |
| **YouTube Long** | SEO description + chapters + keywords | Full description | Tags field |

### Caption rules (in Gemini prompt)
- First line is the hook — must make someone stop scrolling
- Use "you" and "your" — make it personal
- No generic motivational fluff ("keep grinding!")
- Include a natural CTA ("Save this", "Send to someone who needs this", "Follow for more")
- Hashtags: mix of broad viral (`#motivation #mindset #psychology`) and niche (`#darkmotivation #stoicmindset #sigmamindset #mentaltoughness`)

### Example output for "Power of Silence"

**TikTok:**
> Your silence terrifies them. That's the point.
> #darkmotivation #silence #psychology #mindset #mentalstrength #stoic #sigma

**Instagram:**
> They want you to react. They need you to react. But the moment you stay silent, you take back all the power. Save this for when you need it.
> #darkmotivation #silenceispower #stoicmindset #psychology #mentaltoughness #sigmamindset #motivation #selfimprovement #mindset #darkpsychology #powerofsilence #discipline #mentalhealth #growthmindset #strongmind

**YouTube title:**
> Your Silence Terrifies Them — The Psychology of Power

---

## 14. Review Dashboard Upgrade

### Current problems
- No video player — can't watch before approving
- No thumbnail preview
- No caption/metadata preview — approving blind
- Tiny cards, hard to evaluate quality

### Upgraded review card layout
```
┌──────────────────────────────────────────────────────┐
│  ┌─────────┐  Topic: "Power of Silence"              │
│  │         │  Format: 9:16 Short · 72s               │
│  │  VIDEO  │  Created: 24 Jun, 3:00 AM               │
│  │ PLAYER  │  Platforms: TikTok, Instagram, Facebook  │
│  │         │  Status: ● Pending Review                │
│  └─────────┘                                          │
│                                                        │
│  ┌──────────┐  Captions:                              │
│  │THUMBNAIL │  [TikTok] [Instagram] [YouTube]         │
│  │ PREVIEW  │  ─────────────────────────────          │
│  └──────────┘  Your silence terrifies them.           │
│                That's the point.                       │
│                #darkmotivation #silence ...            │
│                                          [Edit]        │
│                                                        │
│  [▶ View Script]                                       │
│                                                        │
│  [  ✓ APPROVE  ]              [  ✗ REJECT  ]          │
└──────────────────────────────────────────────────────┘
```

### Features
- **Embedded video player** — watch the full video in-card before approving
- **Thumbnail preview** — see the generated thumbnail alongside the video
- **Platform caption tabs** — TikTok / Instagram / YouTube captions shown in tabs
- **Inline edit** — edit captions, title, hashtags before approving
- **Script preview** — expandable section showing full script text
- **Large clear actions** — prominent Approve / Reject buttons with confirmation
- **Metadata at a glance** — topic, format, duration, date, target platforms

### Styling
- Black background (#000), dark borders (#1a1a1a) — matches brand
- Amber accent (#E8A817) for interactive elements
- Inter font (already loaded)
- Generous spacing, rounded corners
- Responsive — works on phone for reviewing on the go

---

## 15. Automated Generation — GitHub Actions Cron

### The problem
The scheduler (`scheduler.py`) needs a Python process running 24/7 on your machine. If your laptop sleeps, generation stops. Nothing is truly automated.

### Solution: GitHub Actions cron (free)
A `.github/workflows/generate.yml` file in the `Luminous-Will-automation` repo that triggers video generation on a schedule by calling the HF Spaces API.

### Schedule
| Time (UTC) | Action |
|---|---|
| Daily 3:00 AM | Trigger short-form generation |
| Monday 2:00 AM | Trigger long-form generation |
| Thursday 2:00 AM | Trigger long-form generation |

### Workflow steps
1. **Wake HF Space** — send health check request (free tier sleeps after 15 min inactivity)
2. **Wait 30-60s** — for Space to boot up
3. **Call generation API** — HTTP POST to HF Spaces Gradio endpoint with format + topic params
4. **Wait for completion** — poll until generation finishes
5. **Verify queued** — confirm video was added to review queue

### HF Spaces sleep handling
- Free tier puts the Space to sleep after 15 min of no requests
- Workflow first hits the Space URL to wake it, waits for 200 response
- Then triggers generation — Space stays awake during the pipeline run (~5-10 min)

### What this gives you
Your daily workflow becomes:
1. Wake up
2. Open dashboard on your phone
3. Video is already there (generated at 3 AM)
4. Watch, review captions, approve or reject
5. Done — total time: 2-3 minutes

### No server, no cost
- GitHub Actions free tier: 2000 minutes/month
- Each trigger: ~1 min of Actions time (just sends HTTP requests)
- Actual video generation runs on HF Spaces (free)

---

## Files Modified

| File | Changes |
|---|---|
| `config.py` | New API keys, font config, dB mixing values, Ken Burns toggle, crossfade duration, 4K quality option |
| `captions.py` | Montserrat font, word-by-word reveal animation, time-aware rendering |
| `video_assembler.py` | Ken Burns per clip, context-aware transitions, dB-based audio mixing, remove ducking, 4K resolution support |
| `visuals.py` | Storyblocks search+download layer, scoring improvements (resolution, orientation, duration) |
| `music.py` | Storyblocks music search layer, Epidemic Sound placeholder |
| `voiceover.py` | Script text cleaning, post-download validation, pause trimming, timestamp recalculation |
| `color_grading.py` | S-curve contrast, lift-gamma-gain, selective saturation, adaptive intensity |
| `script_generator.py` | Full rewrite: Gemini for both formats, topic discovery, history tracking, hook validation |
| `thumbnail.py` | Premium frame selection, Gemini punch line, styled text overlay, enhanced vignette |
| `metadata_generator.py` | Viral-optimized captions per platform, hashtag strategy, natural CTAs |
| `main.py` | Add `--quality 4k` CLI flag, pass quality setting through pipeline |

## New Files

| File | Purpose |
|---|---|
| `assets/fonts/Montserrat-Bold.ttf` | Custom caption font + thumbnail font (Google Fonts, free) |
| `generated_history.json` | Tracks all generated video topics + hooks + angles (pre-seeded with 17 existing videos) |
| `.github/workflows/generate.yml` | GitHub Actions cron — triggers daily short + Mon/Thu long generation |

## Modified (Web App — `luminous-will-web`)

| File | Changes |
|---|---|
| `app/dashboard/page.tsx` | Full rewrite: video player, thumbnail preview, caption tabs, inline edit, script preview |
| `app/api/queue/route.ts` | Return video URL + thumbnail URL + caption data for dashboard |
| `app/api/queue/[id]/approve/route.ts` | Accept edited captions on approve |

## No Changes To

| File | Reason |
|---|---|
| `brand_reference.py` | Brand rules unchanged |
| `queue_manager.py` | Queue data structure unchanged (already stores metadata) |
| `publisher.py` | Publishing unchanged |
| Platform adapters | Upload logic unchanged |
