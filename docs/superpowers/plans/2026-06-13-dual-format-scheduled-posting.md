# Dual-Format Pipeline + Scheduled Posting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 16:9 YouTube long-form video generation (8-12 min, Gemini scripts) alongside existing 9:16 shorts, plus a scheduled posting system with review queue and publishing to YouTube, TikTok, Instagram, and Facebook.

**Architecture:** Format-aware config system branches the existing pipeline on a `VideoFormat` enum. Each format has its own resolution, bitrate, caption config, Pexels orientation, and script generation strategy. The scheduler generates videos on cron, queues them in JSON, and a web dashboard provides review/approve/reject before the publisher dispatches to platform-specific adapters via OAuth2.

**Tech Stack:** Python 3.11+, MoviePy 2.x, google-generativeai (Gemini 2.5 Flash), google-api-python-client (YouTube Data API v3), google-auth-oauthlib, requests-oauthlib, Pillow, schedule, Next.js 15, React 19, Tailwind CSS 4, @gradio/client, date-fns.

**Repos:**
- `C:\Users\User\LuminousWill` — local Python pipeline (primary)
- `C:\Users\User\luminous-will-api` — HF Spaces Gradio backend
- `C:\Users\User\luminous-will-web` — Next.js frontend

---

## Phase 1: Dual-Format Pipeline (Tasks 1-8)

### File Structure — Phase 1

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `config.py` | VideoFormat enum, format profiles, Gemini API key |
| Modify | `script_generator.py` | New `generate_long_script()` with Gemini |
| Modify | `video_assembler.py` | `fit_to_horizontal()`, crossfades, dynamic ducking, format branching |
| Modify | `visuals.py` | Landscape search, longer clips, enhanced dedup |
| Modify | `voiceover.py` | Speech rate config per format |
| Modify | `captions.py` | Format-aware caption rendering (font size, position, stroke) |
| Modify | `brand_reference.py` | Add HORIZONTAL_LONG specs |
| Modify | `main.py` | `--format` CLI flag |
| Modify | `requirements.txt` | Add google-generativeai |
| Modify | `luminous-will-api/app.py` | Format dropdown in Gradio UI |
| Modify | `luminous-will-api/config.py` | Same format system |
| Modify | `luminous-will-web/app/page.tsx` | Format selector, aspect-ratio-aware player |

---

### Task 1: Format System in Config

**Files:**
- Modify: `C:\Users\User\LuminousWill\config.py`

- [ ] **Step 1: Add VideoFormat enum and format profiles to config.py**

Add the enum and two format profile dictionaries after the existing imports. Keep all existing constants untouched — they become the defaults for `VERTICAL_SHORT`.

```python
# Add after line 2 (from dotenv import load_dotenv):
from enum import Enum

# Add after line 9 (load_dotenv...):

# --- Video Format System ---
# Each format has its own resolution, bitrate, caption style, and search orientation
class VideoFormat(Enum):
    VERTICAL_SHORT = "short"    # 9:16, 60-90s, template scripts
    HORIZONTAL_LONG = "long"    # 16:9, 8-12 min, Gemini scripts

# --- Format Profiles ---
# Each profile contains ALL format-specific settings
FORMAT_PROFILES = {
    VideoFormat.VERTICAL_SHORT: {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "bitrate": "12000k",
        "pexels_orientation": "portrait",
        "duration_range": (60, 90),
        "caption_font_size": 65,
        "caption_position_y": 0.83,
        "caption_stroke_width": 2,
        "brightness_factor": 0.55,
        "saturation_factor": 0.45,
        "music_volume": 0.32,
        "music_mode": "flat",
        "transition_type": "cut",
        "transition_duration": 0.0,
        "clip_duration_range": (2.5, 10),
        "voice_stability": 0.62,
        "script_source": "template",
    },
    VideoFormat.HORIZONTAL_LONG: {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "bitrate": "15000k",
        "pexels_orientation": "landscape",
        "duration_range": (480, 720),
        "caption_font_size": 48,
        "caption_position_y": 0.88,
        "caption_stroke_width": 3,
        "brightness_factor": 0.60,
        "saturation_factor": 0.45,
        "music_volume": 0.25,
        "music_mode": "ducking",
        "music_volume_high": 0.45,
        "music_duck_ramp": 0.3,
        "transition_type": "crossfade",
        "transition_duration": 0.5,
        "clip_duration_range": (8, 15),
        "voice_stability": 0.55,
        "script_source": "gemini",
    },
}


def get_format_profile(fmt: VideoFormat) -> dict:
    # Returns the full settings profile for a given format
    return FORMAT_PROFILES[fmt]
```

- [ ] **Step 2: Add Gemini API key to config.py**

Add after the FREESOUND_API_KEY line:

```python
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
```

- [ ] **Step 3: Add GEMINI_API_KEY to .env file**

```
GEMINI_API_KEY=your_gemini_api_key_here
```

- [ ] **Step 4: Add google-generativeai to requirements.txt**

Add to the end of requirements.txt:

```
# --- AI Script Generation (Gemini) ---
google-generativeai>=0.8.0  # Gemini API for long-form script generation
```

- [ ] **Step 5: Verify config loads without errors**

Run: `cd C:\Users\User\LuminousWill && python -c "import config; print(config.VideoFormat.HORIZONTAL_LONG); print(config.get_format_profile(config.VideoFormat.VERTICAL_SHORT)['width'])"`

Expected: prints `VideoFormat.HORIZONTAL_LONG` and `1080`

- [ ] **Step 6: Commit**

```bash
git add config.py requirements.txt .env
git commit -m "feat: add VideoFormat enum and dual format profiles"
```

---

### Task 2: Gemini Long-Form Script Generator

**Files:**
- Modify: `C:\Users\User\LuminousWill\script_generator.py`

- [ ] **Step 1: Add Gemini import and generate_long_script() function**

Add after the existing imports at the top of `script_generator.py`:

```python
import json
import google.generativeai as genai
```

Add the following function after the existing `generate_script()` function (after line 60):

```python
def generate_long_script(topic=None):
    """
    # Generates an 8-12 minute script using Gemini AI
    # Returns 40-60 segments with narrative arc structure:
    #   hook -> setup -> escalation -> climax -> resolution -> callback
    # Each segment includes visual keywords and chapter markers
    """

    if topic is None:
        topic = random.choice(config.TRENDING_TOPICS)

    print(f"[SCRIPT] Generating long-form script for: {topic}")

    if not config.GEMINI_API_KEY:
        print("[SCRIPT] WARNING: No Gemini API key, falling back to chained templates")
        return _chain_template_scripts(topic), topic

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""You are a scriptwriter for the YouTube channel "Luminous Will" — dark motivation, stoic philosophy, psychology of power.

VOICE RULES:
- Stoic, commanding, no-nonsense. Short punchy sentences even in long form.
- No fluff, no clichés ("grind", "hustle", "manifest"), no questions to the audience.
- Speak in universal truths. Never say "I" or "we". Use "you" and "they".
- Dark, intense energy. The tone of someone who has seen the worst and emerged stronger.

STRUCTURE for an 8-12 minute script on "{topic}":
1. HOOK (first 30 seconds) — One shocking statement that stops the scroll
2. SETUP (1-2 min) — Frame the problem, make it personal
3. ESCALATION (3-4 min) — Go deeper, reveal uncomfortable truths, build intensity
4. CLIMAX (2-3 min) — The turning point, the harsh lesson, the wake-up call
5. RESOLUTION (1-2 min) — The path forward, actionable transformation
6. CALLBACK (30 seconds) — Circle back to the opening hook with new meaning

Generate exactly 50 segments. Each segment is ONE sentence (max 20 words).

CHAPTER MARKERS: Insert a chapter title every 6-8 segments (for YouTube chapters). Set chapter to null for non-chapter segments.

OUTPUT FORMAT — respond with ONLY a JSON array, no markdown, no explanation:
[
  {{
    "text": "The sentence spoken in the voiceover.",
    "visual_keywords": "5-6 keywords for stock footage search (landscape orientation, dark cinematic)",
    "mood": "dark|intense|reflective|powerful",
    "emphasis_words": ["one", "key", "word"],
    "chapter": "Chapter Title Here or null"
  }},
  ...
]

VISUAL KEYWORD RULES:
- Always include "dark" or "cinematic" in keywords
- Use landscape-oriented subjects: cityscapes, mountains, oceans, highways, architecture, storms
- Vary the subjects — no two consecutive segments should have the same visual theme
- Preferred subjects: dark cityscape night, storm clouds dramatic, mountain peak dark, ocean waves cinematic, businessman walking dark, wolf forest night, lion savanna dark, chess board dark, gym training dark, running athlete silhouette

Generate the script now. 50 segments, JSON array only."""

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

        segments = json.loads(raw_text)

        # Validate and normalize segment structure
        validated = []
        for seg in segments:
            validated.append({
                "text": str(seg.get("text", "")),
                "visual_keywords": str(seg.get("visual_keywords", "dark cinematic landscape")),
                "emphasis_word": seg.get("emphasis_words", [""])[0] if seg.get("emphasis_words") else "",
                "mood": str(seg.get("mood", "dark")),
                "chapter": seg.get("chapter"),
            })

        if len(validated) < 30:
            print(f"[SCRIPT] WARNING: Only {len(validated)} segments generated, expected 40-60")

        print(f"[SCRIPT] Generated {len(validated)} segments via Gemini")

        # Count chapters
        chapters = [s for s in validated if s.get("chapter")]
        print(f"[SCRIPT] Chapters: {len(chapters)}")

        return validated, topic

    except json.JSONDecodeError as e:
        print(f"[SCRIPT] JSON parse error from Gemini: {e}")
        print(f"[SCRIPT] Raw response (first 500 chars): {raw_text[:500]}")
        print("[SCRIPT] Falling back to chained templates")
        return _chain_template_scripts(topic), topic

    except Exception as e:
        print(f"[SCRIPT] Gemini API error: {e}")
        print("[SCRIPT] Falling back to chained templates")
        return _chain_template_scripts(topic), topic


def _chain_template_scripts(topic):
    """
    # Fallback: chains 4-6 template scripts together for long-form
    # Used when Gemini API is unavailable
    """
    all_topics = list(get_template_script.__code__.co_consts)
    available_scripts = []
    for t in config.TRENDING_TOPICS:
        script = get_template_script(t)
        # Only include if it's not the fallback (silence and power)
        if len(script) > 0:
            available_scripts.append(script)

    # Shuffle and take enough to fill 8-12 minutes (~50 segments)
    random.shuffle(available_scripts)
    chained = []
    for script in available_scripts:
        chained.extend(script)
        if len(chained) >= 45:
            break

    return chained


def extract_chapters(script_segments, caption_events):
    """
    # Extracts YouTube chapter markers from long-form script segments
    # Returns list of {time: "M:SS", title: str} for video description
    """
    chapters = []
    word_index = 0

    for seg in script_segments:
        if seg.get("chapter"):
            # Find the timestamp for this segment
            seg_words = seg["text"].split()
            if word_index < len(caption_events):
                start_time = caption_events[word_index]["start"] if caption_events else 0
            else:
                start_time = 0

            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            chapters.append({
                "time": f"{minutes}:{seconds:02d}",
                "title": seg["chapter"],
                "seconds": start_time,
            })

        word_index += 1

    # Ensure first chapter starts at 0:00
    if chapters and chapters[0]["seconds"] > 0:
        chapters.insert(0, {"time": "0:00", "title": "Introduction", "seconds": 0})

    return chapters
```

- [ ] **Step 2: Update generate_script() to accept format parameter**

Replace the existing `generate_script()` function (lines 36-60):

```python
def generate_script(topic=None, custom_hook=None, video_format=None):
    """
    # Generates a video script based on the format:
    #   - VERTICAL_SHORT: template-based (existing behavior)
    #   - HORIZONTAL_LONG: Gemini AI-generated (8-12 min)
    #
    # Returns (segments_list, topic_string)
    """

    # Import here to avoid circular import
    from config import VideoFormat

    if video_format == VideoFormat.HORIZONTAL_LONG:
        return generate_long_script(topic)

    # --- Default: short-form template script ---
    if topic is None:
        topic = random.choice(config.TRENDING_TOPICS)

    print(f"[SCRIPT] Generating script for: {topic}")
    script = get_template_script(topic)
    return script, topic
```

- [ ] **Step 3: Verify the script generator loads**

Run: `cd C:\Users\User\LuminousWill && python -c "from script_generator import generate_script; s, t = generate_script('The art of not reacting'); print(f'{len(s)} segments for: {t}')"`

Expected: `27 segments for: The art of not reacting`

- [ ] **Step 4: Commit**

```bash
git add script_generator.py
git commit -m "feat: add Gemini long-form script generator with narrative arc"
```

---

### Task 3: Video Assembler — Format-Aware Assembly

**Files:**
- Modify: `C:\Users\User\LuminousWill\video_assembler.py`

- [ ] **Step 1: Add fit_to_horizontal() function**

Add after the existing `fit_to_vertical()` function (after line 410):

```python
def fit_to_horizontal(clip, profile):
    """
    # Resizes and crops a clip to 1920x1080 (16:9 landscape)
    # Landscape footage fills perfectly; portrait is center-cropped
    """

    target_w = profile["width"]    # 1920
    target_h = profile["height"]   # 1080
    target_ratio = target_w / target_h  # 1.7778

    clip_w, clip_h = clip.size
    clip_ratio = clip_w / clip_h

    if clip_ratio > target_ratio:
        # Clip is wider than needed -> crop sides
        new_h = target_h
        new_w = int(clip_w * (target_h / clip_h))
        clip = clip.resized(height=new_h)
        x_center = new_w // 2
        x1 = x_center - target_w // 2
        clip = clip.cropped(x1=x1, y1=0, x2=x1 + target_w, y2=target_h)
    else:
        # Clip is taller or matches -> crop top/bottom
        new_w = target_w
        new_h = int(clip_h * (target_w / clip_w))
        clip = clip.resized(width=new_w)
        y_center = new_h // 2
        y1 = y_center - target_h // 2
        y1 = max(0, y1)
        clip = clip.cropped(x1=0, y1=y1, x2=target_w, y2=y1 + target_h)

    return clip


def fit_clip(clip, profile):
    """
    # Routes to the correct fit function based on format profile
    """
    if profile["width"] > profile["height"]:
        return fit_to_horizontal(clip, profile)
    else:
        return fit_to_vertical(clip)
```

- [ ] **Step 2: Update assemble_video() to accept format parameter**

Replace the `assemble_video()` function signature and body. The key changes are: accept `video_format` parameter, use `profile` dict for all format-specific values, route to correct fit function, apply crossfades for long-form, use dynamic ducking for long-form.

Replace lines 27-124 (the entire `assemble_video` function):

```python
def assemble_video(
    clip_paths,
    voiceover_path,
    caption_events,
    script_segments,
    music_path,
    output_path,
    video_format=None,
):
    """
    # Main assembly function - builds the complete video
    # Format-aware: uses profile settings for resolution, bitrate,
    # transitions, and music mixing mode.
    """

    from config import VideoFormat, get_format_profile

    if video_format is None:
        video_format = VideoFormat.VERTICAL_SHORT

    profile = get_format_profile(video_format)
    print(f"[ASSEMBLER] Format: {video_format.value} ({profile['width']}x{profile['height']})")
    print("[ASSEMBLER] Starting video assembly...")

    # --- Step 1: Load voiceover and get total duration ---
    voiceover = AudioFileClip(voiceover_path)
    total_duration = voiceover.duration
    print(f"[ASSEMBLER] Voiceover duration: {total_duration:.1f}s")

    # --- Step 2: Build the visual timeline ---
    visual_timeline = build_visual_timeline(
        clip_paths, script_segments, caption_events, total_duration
    )

    # --- Step 3: Create base video ---
    base_video = create_base_video(visual_timeline, total_duration, profile)
    print(f"[ASSEMBLER] Base video created: {base_video.duration:.1f}s")

    # --- Step 4: Burn captions on-the-fly ---
    print(f"[ASSEMBLER] {len(caption_events)} captions will be burned on-the-fly")
    _caption_render_cache = {}
    frame_w = profile["width"]
    frame_h = profile["height"]

    def burn_captions(get_frame, t):
        frame = get_frame(t)
        for i, event in enumerate(caption_events):
            if event["start"] <= t < event["end"]:
                if i not in _caption_render_cache:
                    _caption_render_cache.clear()
                    rgba = render_caption_frame(
                        event["text"],
                        event.get("highlight_word"),
                        frame_w,
                        frame_h,
                        font_size=profile["caption_font_size"],
                        position_y=profile["caption_position_y"],
                        stroke_width=profile["caption_stroke_width"],
                    )
                    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
                    rgb = rgba[:, :, :3].astype(np.float32)
                    _caption_render_cache[i] = (alpha, rgb)
                a, rgb = _caption_render_cache[i]
                result = frame.astype(np.float32)
                result = result * (1.0 - a) + rgb * a
                return result.astype(np.uint8)
        return frame

    composited = base_video.transform(burn_captions)
    composited = composited.with_duration(total_duration)

    # --- Step 5: Add logo outro ---
    logo_clip = create_logo_outro(profile)
    if logo_clip:
        final_video = concatenate_videoclips([composited, logo_clip], method="chain")
    else:
        final_video = composited

    # --- Step 6: Mix audio ---
    final_audio = mix_audio(voiceover, music_path, total_duration, profile)
    final_video = final_video.with_audio(final_audio)

    # --- Step 7: Export ---
    print(f"[ASSEMBLER] Exporting final video to: {output_path}")
    final_video.write_videofile(
        output_path,
        fps=profile["fps"],
        codec="libx264",
        audio_codec="aac",
        bitrate=profile["bitrate"],
        preset="slow",
        threads=4,
    )

    # --- Cleanup ---
    voiceover.close()
    base_video.close()
    final_video.close()

    print(f"[ASSEMBLER] Video exported successfully: {output_path}")
    return output_path
```

- [ ] **Step 3: Update create_base_video() to use profile**

Replace the `create_base_video` function (lines 281-373):

```python
def create_base_video(visual_timeline, total_duration, profile):
    """
    # Creates the base video processing clips one at a time.
    # Uses profile for resolution, bitrate, color grading, and transitions.
    """
    import subprocess, tempfile
    from color_grading import create_grader

    temp_clip_dir = os.path.join(config.TEMP_DIR, "_graded_clips")
    os.makedirs(temp_clip_dir, exist_ok=True)

    grader = create_grader(profile)
    frame_w = profile["width"]
    frame_h = profile["height"]
    bitrate = profile["bitrate"]
    transition_type = profile["transition_type"]
    transition_dur = profile["transition_duration"]

    graded_paths = []
    actual_duration = 0.0

    for idx, entry in enumerate(visual_timeline):
        needed = entry["duration"]
        if needed <= 0:
            continue

        graded_path = os.path.join(temp_clip_dir, f"graded_{idx:03d}.mp4")
        try:
            clip = VideoFileClip(entry["path"])
            clip = fit_clip(clip, profile)

            if clip.duration >= needed:
                clip = clip.subclipped(0, needed)
            else:
                loops_needed = int(needed / clip.duration) + 1
                clip = concatenate_videoclips([clip] * loops_needed, method="chain")
                clip = clip.subclipped(0, needed)

            clip = clip.image_transform(grader)

            # Add crossfade for long-form (except first clip)
            if transition_type == "crossfade" and idx > 0 and transition_dur > 0:
                clip = clip.with_effects([vfx.CrossFadeIn(transition_dur)])

            clip.write_videofile(
                graded_path, fps=profile["fps"], codec="libx264",
                bitrate=bitrate, preset="fast", threads=2,
                audio=False, logger=None,
            )
            clip.close()
            del clip
            actual_duration += needed
            graded_paths.append(graded_path)
            print(f"[ASSEMBLER] Graded clip {idx+1}/{len(visual_timeline)}")

        except Exception as e:
            print(f"[ASSEMBLER] Error on clip {idx}: {e}")
            black = np.zeros((frame_h, frame_w, 3), dtype=np.uint8)
            blk = ImageClip(black).with_duration(needed)
            blk.write_videofile(
                graded_path, fps=profile["fps"], codec="libx264",
                audio=False, logger=None,
            )
            blk.close()
            actual_duration += needed
            graded_paths.append(graded_path)

    # --- Extend if too short ---
    if actual_duration < total_duration and graded_paths:
        gap = total_duration - actual_duration
        print(f"[ASSEMBLER] Extending last clip by {gap:.1f}s to fill duration")
        last_path = visual_timeline[-1]["path"]
        filler_path = os.path.join(temp_clip_dir, "graded_filler.mp4")
        clip = VideoFileClip(last_path)
        clip = fit_clip(clip, profile)
        if clip.duration < gap:
            clip = concatenate_videoclips([clip] * (int(gap / clip.duration) + 1), method="chain")
        clip = clip.subclipped(0, gap)
        clip = clip.image_transform(grader)
        clip.write_videofile(
            filler_path, fps=profile["fps"], codec="libx264",
            bitrate=bitrate, preset="fast", threads=2,
            audio=False, logger=None,
        )
        clip.close()
        graded_paths.append(filler_path)

    # --- Concatenate via ffmpeg ---
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    concat_list = os.path.join(temp_clip_dir, "concat_list.txt")
    with open(concat_list, "w") as f:
        for p in graded_paths:
            f.write(f"file '{p.replace(os.sep, '/')}'\n")

    base_path = os.path.join(temp_clip_dir, "base_video.mp4")
    subprocess.run([
        ffmpeg_exe, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list, "-c", "copy", base_path,
    ], capture_output=True)

    return VideoFileClip(base_path)
```

- [ ] **Step 4: Update mix_audio() for dynamic ducking**

Replace the `mix_audio` function (lines 488-543):

```python
def mix_audio(voiceover, music_path, voiceover_duration, profile):
    """
    # Mixes voiceover with background music.
    # Two modes based on profile:
    #   - "flat": constant music volume (for short-form)
    #   - "ducking": dynamic volume — dips during voice, rises in pauses (for long-form)
    """

    total_duration = voiceover_duration + config.LOGO_DURATION
    audio_layers = [voiceover]

    if music_path and os.path.exists(music_path):
        try:
            music = AudioFileClip(music_path)

            if music.duration < total_duration:
                loops = int(total_duration / music.duration) + 1
                music = music.looped(n=loops)

            music = music.subclipped(0, total_duration)

            music_mode = profile.get("music_mode", "flat")
            base_vol = profile.get("music_volume", 0.32)

            if music_mode == "ducking":
                # Dynamic ducking: analyze voiceover amplitude per-frame
                high_vol = profile.get("music_volume_high", 0.45)
                ramp = profile.get("music_duck_ramp", 0.3)

                # Sample voiceover RMS in 0.5s windows to detect speech vs silence
                vo_audio = voiceover.to_soundarray(fps=22050)
                window_samples = int(22050 * 0.5)
                rms_values = []
                for start in range(0, len(vo_audio), window_samples):
                    chunk = vo_audio[start:start + window_samples]
                    rms = np.sqrt(np.mean(chunk ** 2)) if len(chunk) > 0 else 0
                    rms_values.append(rms)

                # Threshold: below this RMS = silence/pause
                threshold = np.percentile(rms_values, 25) if rms_values else 0.01

                def duck_volume(get_frame, t):
                    # Find which 0.5s window we're in
                    window_idx = min(int(t / 0.5), len(rms_values) - 1)
                    if window_idx < 0:
                        window_idx = 0
                    rms = rms_values[window_idx] if window_idx < len(rms_values) else 0

                    if rms > threshold:
                        # Voice is speaking — duck music
                        vol = base_vol
                    else:
                        # Silence/pause — raise music
                        vol = high_vol

                    frame = get_frame(t)
                    return (frame * vol).astype(frame.dtype)

                music = music.transform(duck_volume, keep_duration=True)
                print(f"[ASSEMBLER] Dynamic music ducking: {base_vol*100:.0f}% (voice) / {high_vol*100:.0f}% (pauses)")
            else:
                music = music.with_volume_scaled(base_vol)
                print(f"[ASSEMBLER] Flat music at {base_vol*100:.0f}% volume")

            music = music.with_effects([afx.AudioFadeIn(2.0), afx.AudioFadeOut(3.0)])
            audio_layers.append(music)

        except Exception as e:
            print(f"[ASSEMBLER] Could not load music: {e}")

    if len(audio_layers) > 1:
        return CompositeAudioClip(audio_layers)
    else:
        return voiceover
```

- [ ] **Step 5: Update create_logo_outro() to use profile dimensions**

Replace the `create_logo_outro` function (lines 442-485):

```python
def create_logo_outro(profile=None):
    """
    # Creates the logo outro clip sized to match the current format
    """

    if not os.path.exists(config.LOGO_PATH):
        print("[ASSEMBLER] WARNING: Logo not found, skipping outro")
        return None

    if profile is None:
        frame_w = config.VIDEO_WIDTH
        frame_h = config.VIDEO_HEIGHT
    else:
        frame_w = profile["width"]
        frame_h = profile["height"]

    logo_img = Image.open(config.LOGO_PATH).convert("RGBA")

    img_ratio = logo_img.width / logo_img.height
    target_ratio = frame_w / frame_h

    if img_ratio > target_ratio:
        new_w = frame_w
        new_h = int(new_w / img_ratio)
    else:
        new_h = frame_h
        new_w = int(new_h * img_ratio)

    logo_img = logo_img.resize((new_w, new_h), Image.LANCZOS)

    bg = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 255))
    x = (frame_w - new_w) // 2
    y = (frame_h - new_h) // 2
    bg.paste(logo_img, (x, y), logo_img)

    logo_array = np.array(bg.convert("RGB"))
    logo_clip = ImageClip(logo_array).with_duration(config.LOGO_DURATION)
    logo_clip = logo_clip.with_effects([vfx.CrossFadeIn(1.0)])

    return logo_clip
```

- [ ] **Step 6: Commit**

```bash
git add video_assembler.py
git commit -m "feat: format-aware video assembler with crossfades and dynamic ducking"
```

---

### Task 4: Color Grading — Format-Aware Grader

**Files:**
- Modify: `C:\Users\User\LuminousWill\color_grading.py`

- [ ] **Step 1: Add create_grader() factory function**

Add at the end of `color_grading.py` (after line 93):

```python
def create_grader(profile):
    """
    # Returns a grading function calibrated to the format profile's
    # brightness and saturation settings
    """
    brightness = profile.get("brightness_factor", config.BRIGHTNESS_FACTOR)
    saturation = profile.get("saturation_factor", config.SATURATION_FACTOR)

    def grade_frame(frame):
        img = frame.astype(np.float32) / 255.0

        img *= brightness

        lum = np.float32(0.299) * img[:,:,0] + np.float32(0.587) * img[:,:,1] + np.float32(0.114) * img[:,:,2]
        for c in range(3):
            img[:,:,c] = lum + np.float32(saturation) * (img[:,:,c] - lum)
        del lum

        midpoint = np.float32(0.25)
        img = midpoint + np.float32(config.CONTRAST_FACTOR) * (img - midpoint)

        mask = img < 0.08
        img[mask] *= np.float32(0.3)

        avg = img.mean(axis=-1)
        shadow_px = avg < 0.25
        img[:,:,2][shadow_px] += np.float32(0.04)
        hi_px = avg > 0.5
        img[:,:,0][hi_px] += np.float32(0.03)
        img[:,:,1][hi_px] += np.float32(0.015)
        del avg, shadow_px, hi_px

        h, w = img.shape[:2]
        Y = np.linspace(-1, 1, h, dtype=np.float32)
        X = np.linspace(-1, 1, w, dtype=np.float32)
        dist = np.sqrt(Y[:,None]**2 + X[None,:]**2)
        vignette = np.float32(1.0) - np.float32(0.3) * np.clip(dist - 0.5, 0, 1)
        for c in range(3):
            img[:,:,c] *= vignette
        del dist, vignette

        np.clip(img, 0, 1, out=img)
        return (img * 255).astype(np.uint8)

    return grade_frame
```

- [ ] **Step 2: Commit**

```bash
git add color_grading.py
git commit -m "feat: format-aware color grader factory"
```

---

### Task 5: Captions — Format-Aware Rendering

**Files:**
- Modify: `C:\Users\User\LuminousWill\captions.py`

- [ ] **Step 1: Update render_caption_frame() to accept format-specific parameters**

Replace the `render_caption_frame` function signature and the lines that use config values (lines 101-182):

```python
def render_caption_frame(text, highlight_word, frame_width, frame_height,
                         font_size=None, position_y=None, stroke_width=None):
    """
    # Renders a single caption frame as a numpy array (RGBA)
    # Accepts optional overrides for format-specific caption styling
    """

    img = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    _font_size = font_size or config.CAPTION_FONT_SIZE
    _position_y = position_y or config.CAPTION_POSITION[1]
    _stroke_width = stroke_width or config.CAPTION_STROKE_WIDTH

    try:
        font = ImageFont.truetype("arialbd.ttf", _font_size)
    except OSError:
        try:
            font = ImageFont.truetype("Arial Bold.ttf", _font_size)
        except OSError:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", _font_size)
            except OSError:
                font = ImageFont.load_default()
                print("[CAPTIONS] WARNING: Using default font (Arial Bold not found)")

    words = text.split()
    lines = wrap_text_to_lines(words, font, draw, frame_width - 100)

    line_height = _font_size + 8
    total_text_height = len(lines) * line_height
    y_start = int(frame_height * _position_y) - total_text_height // 2

    for line_idx, line_words in enumerate(lines):
        line_text = " ".join(line_words)
        line_width = draw.textlength(line_text, font=font)
        x = (frame_width - line_width) // 2
        y = y_start + line_idx * line_height

        for word in line_words:
            is_highlight = False
            if highlight_word:
                clean_word = word.strip(".,!?;:'\"").lower()
                clean_highlight = highlight_word.strip(".,!?;:'\"").lower()
                if clean_word == clean_highlight:
                    is_highlight = True

            color = config.CAPTION_HIGHLIGHT_COLOR if is_highlight else config.CAPTION_COLOR

            for dx in range(-_stroke_width, _stroke_width + 1):
                for dy in range(-_stroke_width, _stroke_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text(
                            (x + dx, y + dy), word,
                            font=font,
                            fill=config.CAPTION_STROKE_COLOR,
                        )

            draw.text((x, y), word, font=font, fill=color)
            word_width = draw.textlength(word + " ", font=font)
            x += word_width

    return np.array(img)
```

- [ ] **Step 2: Commit**

```bash
git add captions.py
git commit -m "feat: format-aware caption rendering with configurable size/position/stroke"
```

---

### Task 6: Visuals — Landscape Search & Longer Clips

**Files:**
- Modify: `C:\Users\User\LuminousWill\visuals.py`

- [ ] **Step 1: Update search_and_download_videos() to accept format profile**

Replace the function signature and add orientation/clip-duration logic. Change lines 40-125:

```python
def search_and_download_videos(script_segments, output_dir, profile=None):
    """
    # For each script segment, searches Pexels + Pixabay for matching footage.
    # Uses profile for orientation (portrait/landscape) and clip preferences.
    """

    os.makedirs(output_dir, exist_ok=True)
    downloaded_clips = []
    used_pexels_ids = set()
    used_pixabay_ids = set()

    has_pexels = bool(config.PEXELS_API_KEY)
    has_pixabay = bool(config.PIXABAY_API_KEY)

    if not has_pexels and not has_pixabay:
        print("[VISUALS] ERROR: No API keys configured for Pexels or Pixabay!")
        return []

    # Format-specific search orientation
    orientation = profile["pexels_orientation"] if profile else config.PEXELS_ORIENTATION

    # Expanded fallback queries for landscape
    if orientation == "landscape":
        landscape_fallbacks = [
            "dark cityscape night skyline", "mountain peak dark clouds dramatic",
            "ocean waves dark cinematic", "dark highway driving night",
            "storm clouds dramatic sky", "dark forest aerial cinematic",
            "modern architecture night dark", "dark desert landscape cinematic",
            "river dark moody cinematic", "dark stadium empty cinematic",
            "dark bridge night lights", "rain dark street cinematic",
        ]
    else:
        landscape_fallbacks = None

    for i, segment in enumerate(script_segments):
        keywords = segment["visual_keywords"]
        print(f"[VISUALS] ({i+1}/{len(script_segments)}) Searching: {keywords}")

        video_path = None

        if i % 2 == 0 and has_pexels:
            video_path = search_pexels_one(keywords, output_dir, i, used_pexels_ids, orientation)
            if not video_path and has_pixabay:
                print(f"[VISUALS] Pexels miss, trying Pixabay...")
                video_path = search_pixabay_one(keywords, output_dir, i, used_pixabay_ids)
        elif has_pixabay:
            video_path = search_pixabay_one(keywords, output_dir, i, used_pixabay_ids)
            if not video_path and has_pexels:
                print(f"[VISUALS] Pixabay miss, trying Pexels...")
                video_path = search_pexels_one(keywords, output_dir, i, used_pexels_ids, orientation)
        elif has_pexels:
            video_path = search_pexels_one(keywords, output_dir, i, used_pexels_ids, orientation)

        # Fallback: simpler keywords
        if not video_path:
            simple_keywords = keywords.split()[:2]
            fallback_query = " ".join(simple_keywords)
            print(f"[VISUALS] Trying simpler query: {fallback_query}")
            if has_pexels:
                video_path = search_pexels_one(fallback_query, output_dir, i, used_pexels_ids, orientation)
            if not video_path and has_pixabay:
                video_path = search_pixabay_one(fallback_query, output_dir, i, used_pixabay_ids)

        # Last resort: format-specific fallbacks
        if not video_path:
            fallbacks = landscape_fallbacks if landscape_fallbacks else [
                "businessman suit dark", "luxury car night", "man walking alone city night",
                "dark gym workout", "boxing training dark", "running athlete dark",
                "modern skyscraper night", "dark cinematic portrait", "chess dark dramatic",
                "wolf dark forest", "dark ocean waves", "man rooftop city night",
            ]
            for fallback in fallbacks:
                if has_pexels:
                    video_path = search_pexels_one(fallback, output_dir, i, used_pexels_ids, orientation)
                if not video_path and has_pixabay:
                    video_path = search_pixabay_one(fallback, output_dir, i, used_pixabay_ids)
                if video_path:
                    break

        if video_path:
            downloaded_clips.append(video_path)
            print(f"[VISUALS] Downloaded: {os.path.basename(video_path)}")

        time.sleep(1)

    print(f"[VISUALS] Downloaded {len(downloaded_clips)} clips total")
    return downloaded_clips
```

- [ ] **Step 2: Update search_pexels_one() to accept orientation parameter**

Change the function signature (line 132) and the params dict:

```python
def search_pexels_one(query, output_dir, index, used_ids, orientation=None):
    """
    # Searches Pexels and downloads one matching video clip
    # Uses the provided orientation (portrait/landscape)
    """

    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": config.PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": orientation or config.PEXELS_ORIENTATION,
        "size": config.PEXELS_SIZE,
        "per_page": config.PEXELS_PER_PAGE,
    }
```

The rest of `search_pexels_one` stays the same — only the signature and `params` dict change.

- [ ] **Step 3: Update _get_best_pexels_file() to prefer landscape for horizontal format**

The existing function already handles both orientations correctly (it sorts by portrait first, falls back to landscape). For horizontal format, the Pexels API `orientation=landscape` parameter already filters results to landscape videos, so no change needed to this function.

- [ ] **Step 4: Commit**

```bash
git add visuals.py
git commit -m "feat: format-aware visual search with landscape orientation and expanded fallbacks"
```

---

### Task 7: Voiceover — Format-Aware Speech Rate

**Files:**
- Modify: `C:\Users\User\LuminousWill\voiceover.py`

- [ ] **Step 1: Update generate_voiceover() to accept profile for stability override**

Change the function signature and voice_settings usage (lines 13-78):

```python
def generate_voiceover(script_text, output_path, profile=None):
    """
    # Generates voiceover audio from script text using ElevenLabs
    # Accepts optional profile for format-specific voice settings
    """

    print("[VOICEOVER] Generating speech with ElevenLabs...")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}/with-timestamps"

    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    # Use profile stability if provided, else default
    voice_settings = dict(config.VOICE_SETTINGS)
    if profile and "voice_stability" in profile:
        voice_settings["stability"] = profile["voice_stability"]

    payload = {
        "text": script_text,
        "model_id": config.ELEVENLABS_MODEL_ID,
        "voice_settings": voice_settings,
        "speed": config.VOICE_SPEED,
    }
```

The rest of `generate_voiceover` stays exactly the same (lines after the payload are unchanged).

- [ ] **Step 2: Commit**

```bash
git add voiceover.py
git commit -m "feat: format-aware voiceover stability setting"
```

---

### Task 8: Entry Points — CLI, Gradio, Web Frontend

**Files:**
- Modify: `C:\Users\User\LuminousWill\main.py`
- Modify: `C:\Users\User\luminous-will-api\app.py`
- Modify: `C:\Users\User\luminous-will-web\app\page.tsx`

- [ ] **Step 1: Update main.py with --format flag**

Replace the entry point section (lines 210-233):

```python
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Luminous Will Video Pipeline")
    parser.add_argument("topic", nargs="?", default=None, help="Video topic")
    parser.add_argument("--format", choices=["short", "long"], default="short",
                        help="Video format: short (9:16, 60-90s) or long (16:9, 8-12min)")
    parser.add_argument("--list", action="store_true", help="List available topics")
    args = parser.parse_args()

    if args.list:
        list_topics()
    else:
        from config import VideoFormat
        fmt = VideoFormat.HORIZONTAL_LONG if args.format == "long" else VideoFormat.VERTICAL_SHORT
        run_pipeline(topic=args.topic, video_format=fmt)
```

- [ ] **Step 2: Update run_pipeline() to accept and pass video_format**

Replace the `run_pipeline` function signature and update the calls inside it (lines 80-193):

```python
def run_pipeline(topic=None, video_format=None):
    """
    # Main pipeline: runs all steps in sequence
    # Accepts video_format for dual-format support
    """

    from config import VideoFormat, get_format_profile

    if video_format is None:
        video_format = VideoFormat.VERTICAL_SHORT

    profile = get_format_profile(video_format)

    start_time = time.time()
    print("\n" + "=" * 60)
    print("  LUMINOUS WILL - VIDEO PIPELINE")
    print(f"  Format: {video_format.value} ({profile['width']}x{profile['height']})")
    print("=" * 60)

    # --- STEP 1: VALIDATE ---
    print("\n[STEP 1/6] Validating setup...")
    if not validate_setup():
        return None

    validate_references()

    # --- STEP 2: GENERATE SCRIPT ---
    print("\n[STEP 2/6] Generating script...")
    script_segments, topic = generate_script(topic, video_format=video_format)
    full_script = get_script_text(script_segments)
    print(f"[SCRIPT] Topic: {topic}")
    print(f"[SCRIPT] Segments: {len(script_segments)}")
    print(f"[SCRIPT] Full text:\n  {full_script[:200]}...")

    safe_topic = topic.replace(" ", "_").replace("'", "")[:50]
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_name = f"{safe_topic}_{timestamp}"
    video_temp = os.path.join(config.TEMP_DIR, video_name)
    os.makedirs(video_temp, exist_ok=True)

    # --- STEP 3: GENERATE VOICEOVER ---
    print("\n[STEP 3/6] Generating voiceover...")
    voiceover_path = os.path.join(video_temp, "voiceover.mp3")
    word_timestamps = generate_voiceover(full_script, voiceover_path, profile=profile)
    audio_duration = get_audio_duration(voiceover_path)
    print(f"[VOICEOVER] Duration: {audio_duration:.1f}s")

    # --- STEP 4: DOWNLOAD STOCK FOOTAGE ---
    print("\n[STEP 4/6] Downloading stock footage...")
    clips_dir = os.path.join(video_temp, "clips")
    clip_paths = search_and_download_videos(script_segments, clips_dir, profile=profile)

    if not clip_paths:
        print("[ERROR] No footage downloaded. Check your Pexels API key.")
        return None

    # --- STEP 5: BUILD CAPTIONS ---
    print("\n[STEP 5/6] Building word-synced captions...")
    caption_events = create_caption_clips(
        word_timestamps, script_segments, audio_duration
    )

    # --- STEP 6: ASSEMBLE FINAL VIDEO ---
    print("\n[STEP 6/6] Assembling final video...")
    output_path = os.path.join(config.OUTPUT_DIR, f"{video_name}.mp4")
    music_path = find_background_music()

    if not music_path:
        print("[MUSIC] No local music found, downloading from Pixabay...")
        music_path = download_background_music()

    if music_path:
        print(f"[MUSIC] Using: {os.path.basename(music_path)}")
    else:
        print("[MUSIC] No background music available - video will have voiceover only")

    assemble_video(
        clip_paths=clip_paths,
        voiceover_path=voiceover_path,
        caption_events=caption_events,
        script_segments=script_segments,
        music_path=music_path,
        output_path=output_path,
        video_format=video_format,
    )

    # --- DONE ---
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  VIDEO COMPLETE!")
    print(f"  Format: {video_format.value}")
    print(f"  Topic: {topic}")
    print(f"  Output: {output_path}")
    print(f"  Time: {elapsed:.0f} seconds")
    print("=" * 60 + "\n")

    return output_path
```

- [ ] **Step 3: Update Gradio app.py with format dropdown**

In `C:\Users\User\luminous-will-api\app.py`, update the `generate_video` function and UI to support format selection.

Replace the `generate_video` function (lines 46-116):

```python
def generate_video(topic, video_format_str="short", progress=gr.Progress()):
    # --- Main pipeline with format support ---

    from config import VideoFormat, get_format_profile

    fmt = VideoFormat.HORIZONTAL_LONG if video_format_str == "long" else VideoFormat.VERTICAL_SHORT
    profile = get_format_profile(fmt)

    start_time = time.time()

    progress(0.0, desc="Checking setup...")
    ok, msg = validate_setup()
    if not ok:
        raise gr.Error(f"Setup error: {msg}")

    validate_references()

    progress(0.05, desc="Generating script...")
    if not topic or topic.strip() == "":
        topic = None
    script_segments, topic = generate_script(topic, video_format=fmt)
    full_script = get_script_text(script_segments)

    safe_topic = topic.replace(" ", "_").replace("'", "")[:50]
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_name = f"{safe_topic}_{timestamp}"
    video_temp = os.path.join(config.TEMP_DIR, video_name)
    os.makedirs(video_temp, exist_ok=True)

    progress(0.10, desc="Creating voiceover (ElevenLabs)...")
    voiceover_path = os.path.join(video_temp, "voiceover.mp3")
    word_timestamps = generate_voiceover(full_script, voiceover_path, profile=profile)
    audio_duration = get_audio_duration(voiceover_path)

    progress(0.25, desc="Downloading stock footage...")
    clips_dir = os.path.join(video_temp, "clips")
    clip_paths = search_and_download_videos(script_segments, clips_dir, profile=profile)

    if not clip_paths:
        raise gr.Error("No footage downloaded. Check Pexels/Pixabay API keys.")

    progress(0.45, desc="Building word-synced captions...")
    caption_events = create_caption_clips(word_timestamps, script_segments, audio_duration)

    progress(0.50, desc="Getting background music...")
    music_path = find_background_music()
    if not music_path:
        music_path = download_background_music()

    progress(0.55, desc="Assembling video...")
    output_path = os.path.join(config.OUTPUT_DIR, f"{video_name}.mp4")

    assemble_video(
        clip_paths=clip_paths,
        voiceover_path=voiceover_path,
        caption_events=caption_events,
        script_segments=script_segments,
        music_path=music_path,
        output_path=output_path,
        video_format=fmt,
    )

    progress(0.95, desc="Cleaning up...")
    shutil.rmtree(video_temp, ignore_errors=True)

    elapsed = time.time() - start_time
    progress(1.0, desc=f"Done! ({elapsed:.0f}s)")

    return output_path, f"**{topic}** ({fmt.value})\n\nGenerated in {elapsed:.0f} seconds | {len(script_segments)} segments | {audio_duration:.0f}s voiceover"
```

Update the Gradio UI to add format dropdown. Replace lines 158-192:

```python
with gr.Blocks(
    title="Luminous Will - Video Generator",
    css=custom_css,
    theme=gr.themes.Base(
        primary_hue="amber",
        neutral_hue="zinc",
        font=gr.themes.GoogleFont("Inter"),
    ),
) as demo:

    gr.HTML('<h1 class="main-title">LUMINOUS WILL</h1>')
    gr.HTML('<p class="subtitle">Dark Motivation Video Generator</p>')

    with gr.Row():
        with gr.Column(scale=1):
            format_dropdown = gr.Dropdown(
                choices=["Vertical Short (9:16)", "Horizontal Long (16:9)"],
                value="Vertical Short (9:16)",
                label="Video Format",
                info="Short = 60-90s for Reels/TikTok. Long = 8-12 min for YouTube.",
            )
            topic_dropdown = gr.Dropdown(
                choices=["(Random)"] + config.TRENDING_TOPICS,
                value="(Random)",
                label="Select Topic",
                info="Pick a topic or choose Random",
            )
            custom_topic = gr.Textbox(
                label="Or Type a Custom Topic",
                placeholder="e.g., Why discipline beats motivation",
                lines=1,
            )
            generate_btn = gr.Button(
                "Generate Video",
                variant="primary",
                size="lg",
            )

        with gr.Column(scale=2):
            video_output = gr.Video(label="Generated Video")
            info_output = gr.Markdown(label="Details")

    def on_generate(format_choice, dropdown_topic, custom, progress=gr.Progress()):
        topic = custom.strip() if custom and custom.strip() else None
        if topic is None and dropdown_topic and dropdown_topic != "(Random)":
            topic = dropdown_topic
        fmt_str = "long" if "Long" in format_choice else "short"
        return generate_video(topic, fmt_str, progress)

    generate_btn.click(
        fn=on_generate,
        inputs=[format_dropdown, topic_dropdown, custom_topic],
        outputs=[video_output, info_output],
    )
```

- [ ] **Step 4: Update web frontend page.tsx with format selector**

In `C:\Users\User\luminous-will-web\app\page.tsx`, add a format toggle. Add state after line 64:

```typescript
const [videoFormat, setVideoFormat] = useState<"short" | "long">("short");
```

Add the format selector UI after the header (after line 200, before the topic selection):

```tsx
{/* --- Format selector --- */}
<div className="mb-6">
  <h2 className="text-sm font-semibold uppercase tracking-wider mb-3" style={{ color: "#666" }}>
    Format
  </h2>
  <div className="grid grid-cols-2 gap-3">
    <button
      onClick={() => setVideoFormat("short")}
      className={`p-3 rounded-xl border text-sm transition-all ${
        videoFormat === "short"
          ? "border-[#E8A817] bg-[#E8A817]/10 text-[#E8A817]"
          : "border-[#1a1a1a] bg-[#0a0a0a] text-[#666] hover:border-[#333]"
      }`}
    >
      <div className="font-semibold">9:16 Short</div>
      <div className="text-xs mt-1 opacity-70">60-90s · Reels/TikTok</div>
    </button>
    <button
      onClick={() => setVideoFormat("long")}
      className={`p-3 rounded-xl border text-sm transition-all ${
        videoFormat === "long"
          ? "border-[#E8A817] bg-[#E8A817]/10 text-[#E8A817]"
          : "border-[#1a1a1a] bg-[#0a0a0a] text-[#666] hover:border-[#333]"
      }`}
    >
      <div className="font-semibold">16:9 Long</div>
      <div className="text-xs mt-1 opacity-70">8-12 min · YouTube</div>
    </button>
  </div>
</div>
```

Update the Gradio client call (line 132-135) to pass format:

```typescript
const result = await client.predict("/on_generate", {
  format_choice: videoFormat === "long" ? "Horizontal Long (16:9)" : "Vertical Short (9:16)",
  dropdown_topic: customTopic.trim() ? "(Random)" : (selectedTopic || "(Random)"),
  custom: customTopic.trim() || "",
});
```

Update the video container to adjust aspect ratio (line 283):

```tsx
<div className="video-container mx-auto" style={{ maxWidth: videoFormat === "long" ? "640px" : "360px" }}>
```

- [ ] **Step 5: Commit all entry point changes**

```bash
cd C:\Users\User\LuminousWill && git add main.py && git commit -m "feat: add --format CLI flag for dual-format pipeline"
cd C:\Users\User\luminous-will-api && git add app.py && git commit -m "feat: add format dropdown to Gradio UI"
cd C:\Users\User\luminous-will-web && git add app/page.tsx && git commit -m "feat: add format selector to web frontend"
```

---

## Phase 2: Scheduled Posting System (Tasks 9-17)

### File Structure — Phase 2

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `LuminousWill/queue_manager.py` | Queue CRUD operations on queue.json |
| Create | `LuminousWill/scheduler.py` | Cron-triggered video generation |
| Create | `LuminousWill/metadata_generator.py` | Gemini metadata per platform |
| Create | `LuminousWill/thumbnail.py` | Auto thumbnail extraction + overlay |
| Create | `LuminousWill/publisher.py` | Upload orchestrator |
| Create | `LuminousWill/youtube_adapter.py` | YouTube Data API v3 |
| Create | `LuminousWill/tiktok_adapter.py` | TikTok Content Posting API |
| Create | `LuminousWill/instagram_adapter.py` | Instagram Graph API |
| Create | `LuminousWill/facebook_adapter.py` | Facebook Graph API |
| Modify | `LuminousWill/requirements.txt` | Add oauth/API packages |
| Create | `luminous-will-web/app/dashboard/page.tsx` | Review queue dashboard |
| Create | `luminous-will-web/app/dashboard/[id]/page.tsx` | Video review panel |
| Create | `luminous-will-web/app/api/queue/route.ts` | Queue API |
| Create | `luminous-will-web/app/api/queue/[id]/approve/route.ts` | Approve endpoint |
| Create | `luminous-will-web/app/api/queue/[id]/reject/route.ts` | Reject endpoint |
| Create | `luminous-will-web/lib/queue.ts` | Queue operations |
| Create | `luminous-will-web/components/VideoReviewCard.tsx` | Queue list item |

---

### Task 9: Queue Manager

**Files:**
- Create: `C:\Users\User\LuminousWill\queue_manager.py`

- [ ] **Step 1: Create queue_manager.py**

```python
import os
import json
import uuid
from datetime import datetime
import config

# ============================================================
# QUEUE MANAGER
# Manages the video review queue stored in queue.json
# Supports: add, list, get, update status, delete
# ============================================================

QUEUE_FILE = os.path.join(config.BASE_DIR, "queue.json")


def _load_queue():
    # Loads the queue from disk, returns list of entries
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, "r") as f:
        return json.load(f)


def _save_queue(entries):
    # Saves the queue to disk
    with open(QUEUE_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def add_entry(video_path, thumbnail_path, topic, video_format, metadata, target_platforms):
    # Adds a new video to the review queue
    entry = {
        "id": str(uuid.uuid4()),
        "format": video_format,
        "topic": topic,
        "video_path": video_path,
        "thumbnail_path": thumbnail_path,
        "metadata": metadata,
        "target_platforms": target_platforms,
        "status": "pending_review",
        "created_at": datetime.utcnow().isoformat(),
        "scheduled_post_time": None,
        "post_results": {},
        "error": None,
    }
    entries = _load_queue()
    entries.append(entry)
    _save_queue(entries)
    print(f"[QUEUE] Added: {entry['id'][:8]}... ({topic})")
    return entry


def list_entries(status=None):
    # Returns all entries, optionally filtered by status
    entries = _load_queue()
    if status:
        entries = [e for e in entries if e["status"] == status]
    return entries


def get_entry(entry_id):
    # Returns a single entry by ID
    entries = _load_queue()
    for e in entries:
        if e["id"] == entry_id:
            return e
    return None


def update_entry(entry_id, updates):
    # Updates fields on an existing entry
    entries = _load_queue()
    for e in entries:
        if e["id"] == entry_id:
            e.update(updates)
            _save_queue(entries)
            print(f"[QUEUE] Updated: {entry_id[:8]}... -> {updates}")
            return e
    return None


def approve_entry(entry_id, scheduled_time=None):
    # Moves entry to approved status
    return update_entry(entry_id, {
        "status": "approved",
        "scheduled_post_time": scheduled_time,
    })


def reject_entry(entry_id):
    # Marks entry as rejected
    return update_entry(entry_id, {"status": "rejected"})


def mark_posted(entry_id, post_results):
    # Marks entry as posted with platform URLs
    return update_entry(entry_id, {
        "status": "posted",
        "post_results": post_results,
    })


def mark_failed(entry_id, error_msg):
    # Marks entry as failed with error message
    return update_entry(entry_id, {
        "status": "failed",
        "error": error_msg,
    })


def delete_entry(entry_id):
    # Removes an entry from the queue
    entries = _load_queue()
    entries = [e for e in entries if e["id"] != entry_id]
    _save_queue(entries)
    print(f"[QUEUE] Deleted: {entry_id[:8]}...")
```

- [ ] **Step 2: Add queue.json to .gitignore**

Add to `.gitignore`:
```
queue.json
```

- [ ] **Step 3: Commit**

```bash
git add queue_manager.py .gitignore
git commit -m "feat: add queue manager for video review pipeline"
```

---

### Task 10: Metadata Generator

**Files:**
- Create: `C:\Users\User\LuminousWill\metadata_generator.py`

- [ ] **Step 1: Create metadata_generator.py**

```python
import json
import config
import google.generativeai as genai

# ============================================================
# METADATA GENERATOR
# Uses Gemini to generate platform-optimized titles, descriptions,
# hashtags, and SEO metadata for each social platform
# ============================================================


def generate_metadata(topic, script_segments, video_format, chapters=None):
    # Generates platform-specific metadata for all 4 platforms
    # Returns dict keyed by platform name

    if not config.GEMINI_API_KEY:
        return _fallback_metadata(topic, video_format)

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Build script summary for context
    script_text = " ".join([s["text"] for s in script_segments[:10]])
    chapter_text = ""
    if chapters:
        chapter_text = "\n".join([f"{c['time']} - {c['title']}" for c in chapters])

    prompt = f"""Generate social media metadata for a dark motivation video.

TOPIC: {topic}
FORMAT: {"YouTube long-form (8-12 min)" if video_format == "long" else "Short-form vertical (60-90s)"}
SCRIPT EXCERPT: {script_text[:500]}
{"CHAPTERS:\n" + chapter_text if chapter_text else ""}

BRAND: Luminous Will — stoic, dark psychology, power, self-improvement. No emojis. No fluff.

Generate metadata for ALL 4 platforms. Respond with ONLY a JSON object:

{{
  "youtube": {{
    "title": "SEO title, max 60 chars, keyword-front-loaded",
    "description": "Full description with SEO keywords, chapters, and CTA. Max 2000 chars.",
    "tags": ["15-20 relevant tags"],
    "category": "Education or People & Blogs"
  }},
  "tiktok": {{
    "caption": "Short hook caption, max 150 chars",
    "hashtags": ["5-8 trending + niche hashtags"]
  }},
  "instagram": {{
    "caption": "Caption with hook, body, CTA. Max 2200 chars. Line breaks for readability.",
    "hashtags": ["20-30 hashtags mix of broad and niche"]
  }},
  "facebook": {{
    "description": "Description with hook and CTA. 3-5 hashtags inline.",
    "hashtags": ["3-5 hashtags"]
  }}
}}"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        metadata = json.loads(raw)
        print(f"[METADATA] Generated metadata for all platforms")
        return metadata

    except Exception as e:
        print(f"[METADATA] Gemini error: {e}, using fallback")
        return _fallback_metadata(topic, video_format)


def _fallback_metadata(topic, video_format):
    # Basic metadata when Gemini is unavailable
    base_tags = ["motivation", "darkpsychology", "stoic", "mindset", "selfimprovement",
                 "discipline", "mentalstrength", "success", "psychology", "power"]

    return {
        "youtube": {
            "title": f"{topic} | Luminous Will",
            "description": f"{topic}\n\nDark motivation for the disciplined mind.\n\n#LuminousWill #DarkMotivation #Stoic",
            "tags": base_tags + [topic.lower().replace(" ", "")],
            "category": "Education",
        },
        "tiktok": {
            "caption": f"{topic}",
            "hashtags": base_tags[:8],
        },
        "instagram": {
            "caption": f"{topic}\n\nFollow @luminouswill for more.",
            "hashtags": base_tags + ["reels", "motivationaldaily", "mindsetshift"],
        },
        "facebook": {
            "description": f"{topic}\n\n#motivation #darkpsychology #stoic",
            "hashtags": base_tags[:5],
        },
    }
```

- [ ] **Step 2: Commit**

```bash
git add metadata_generator.py
git commit -m "feat: add Gemini-powered platform metadata generator"
```

---

### Task 11: Thumbnail Generator

**Files:**
- Create: `C:\Users\User\LuminousWill\thumbnail.py`

- [ ] **Step 1: Create thumbnail.py**

```python
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip
import config

# ============================================================
# THUMBNAIL GENERATOR
# Extracts the best frame from a video and overlays title text
# in the Luminous Will amber brand style
# ============================================================

THUMB_WIDTH = 1280
THUMB_HEIGHT = 720


def generate_thumbnail(video_path, title, output_path=None):
    # Generates a branded thumbnail from the video
    # Returns path to the saved thumbnail JPG

    if output_path is None:
        output_path = video_path.replace(".mp4", "_thumb.jpg")

    # --- Extract candidate frames ---
    clip = VideoFileClip(video_path)
    duration = clip.duration
    num_candidates = 10

    best_frame = None
    best_score = -1

    for i in range(num_candidates):
        t = (i + 1) * duration / (num_candidates + 1)
        frame = clip.get_frame(t)
        score = _score_frame(frame)
        if score > best_score:
            best_score = score
            best_frame = frame

    clip.close()

    if best_frame is None:
        # Fallback: black frame
        best_frame = np.zeros((THUMB_HEIGHT, THUMB_WIDTH, 3), dtype=np.uint8)

    # --- Resize to thumbnail dimensions ---
    img = Image.fromarray(best_frame)
    img = img.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)

    # --- Add dark gradient bar at bottom ---
    draw = ImageDraw.Draw(img)
    for y in range(THUMB_HEIGHT - 200, THUMB_HEIGHT):
        alpha = (y - (THUMB_HEIGHT - 200)) / 200.0
        overlay_color = (0, 0, 0, int(alpha * 200))
        draw.line([(0, y), (THUMB_WIDTH, y)], fill=(0, 0, 0))

    # Re-draw with proper alpha blending
    overlay = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for y in range(THUMB_HEIGHT - 200, THUMB_HEIGHT):
        alpha = int(((y - (THUMB_HEIGHT - 200)) / 200.0) * 220)
        overlay_draw.line([(0, y), (THUMB_WIDTH, y)], fill=(0, 0, 0, alpha))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)

    # --- Add title text ---
    draw = ImageDraw.Draw(img)
    font_size = 52
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    # Wrap title to fit
    words = title.upper().split()
    lines = []
    current_line = []
    for word in words:
        test = " ".join(current_line + [word])
        if draw.textlength(test, font=font) < THUMB_WIDTH - 120:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    # Draw title text centered near bottom
    line_height = font_size + 10
    total_height = len(lines) * line_height
    y_start = THUMB_HEIGHT - total_height - 40

    for i, line in enumerate(lines):
        line_width = draw.textlength(line, font=font)
        x = (THUMB_WIDTH - line_width) // 2
        y = y_start + i * line_height

        # Black stroke
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill="black")

        # Amber text
        draw.text((x, y), line, font=font, fill="#E8A817")

    # --- Save ---
    img = img.convert("RGB")
    img.save(output_path, "JPEG", quality=90)
    print(f"[THUMBNAIL] Saved: {output_path}")

    return output_path


def _score_frame(frame):
    # Scores a frame for thumbnail quality
    # Higher = better (more contrast, visual interest, not too dark)
    gray = np.mean(frame, axis=2)
    brightness = np.mean(gray)
    contrast = np.std(gray)

    # Penalize too dark or too bright
    brightness_score = 1.0 - abs(brightness - 80) / 128.0
    contrast_score = contrast / 64.0

    return brightness_score * 0.4 + contrast_score * 0.6
```

- [ ] **Step 2: Commit**

```bash
git add thumbnail.py
git commit -m "feat: add auto thumbnail generator with brand overlay"
```

---

### Task 12: Publisher + Platform Adapters

**Files:**
- Create: `C:\Users\User\LuminousWill\publisher.py`
- Create: `C:\Users\User\LuminousWill\youtube_adapter.py`
- Create: `C:\Users\User\LuminousWill\tiktok_adapter.py`
- Create: `C:\Users\User\LuminousWill\instagram_adapter.py`
- Create: `C:\Users\User\LuminousWill\facebook_adapter.py`
- Modify: `C:\Users\User\LuminousWill\requirements.txt`

- [ ] **Step 1: Add publishing dependencies to requirements.txt**

Append to `requirements.txt`:

```
# --- Social Media Publishing ---
google-api-python-client>=2.0.0   # YouTube Data API v3
google-auth-oauthlib>=1.0.0       # Google OAuth2 flow
requests-oauthlib>=1.3.0          # OAuth2 for TikTok/Facebook
schedule>=1.2.0                    # Cron-style scheduler
```

- [ ] **Step 2: Create publisher.py**

```python
import os
import config
from queue_manager import mark_posted, mark_failed

# ============================================================
# PUBLISHER
# Orchestrates uploading approved videos to social platforms
# Calls platform-specific adapters for each target platform
# ============================================================


def publish_entry(queue_entry):
    # Publishes a video to all target platforms
    # Returns dict of {platform: {url, id}} results

    video_path = queue_entry["video_path"]
    metadata = queue_entry["metadata"]
    target_platforms = queue_entry["target_platforms"]
    thumbnail_path = queue_entry.get("thumbnail_path")
    entry_id = queue_entry["id"]

    if not os.path.exists(video_path):
        mark_failed(entry_id, f"Video file not found: {video_path}")
        return None

    results = {}
    errors = []

    for platform in target_platforms:
        platform_meta = metadata.get(platform, {})
        print(f"[PUBLISHER] Uploading to {platform}...")

        try:
            if platform == "youtube":
                from youtube_adapter import YouTubeAdapter
                adapter = YouTubeAdapter()
                result = adapter.upload(video_path, platform_meta, thumbnail_path)

            elif platform == "tiktok":
                from tiktok_adapter import TikTokAdapter
                adapter = TikTokAdapter()
                result = adapter.upload(video_path, platform_meta)

            elif platform == "instagram":
                from instagram_adapter import InstagramAdapter
                adapter = InstagramAdapter()
                result = adapter.upload(video_path, platform_meta)

            elif platform == "facebook":
                from facebook_adapter import FacebookAdapter
                adapter = FacebookAdapter()
                result = adapter.upload(video_path, platform_meta)

            else:
                print(f"[PUBLISHER] Unknown platform: {platform}")
                continue

            if result:
                results[platform] = result
                print(f"[PUBLISHER] {platform}: {result.get('url', 'uploaded')}")

        except Exception as e:
            error_msg = f"{platform}: {str(e)}"
            errors.append(error_msg)
            print(f"[PUBLISHER] Error on {platform}: {e}")

    if results:
        mark_posted(entry_id, results)
    elif errors:
        mark_failed(entry_id, "; ".join(errors))

    return results
```

- [ ] **Step 3: Create youtube_adapter.py**

```python
import os
import json
import config

# ============================================================
# YOUTUBE ADAPTER
# Uploads videos to YouTube via Data API v3
# Uses OAuth2 for authentication (one-time consent)
# Supports resumable uploads for large files
# ============================================================

TOKEN_FILE = os.path.join(config.BASE_DIR, ".youtube_token.json")
CLIENT_SECRETS_FILE = os.path.join(config.BASE_DIR, "client_secrets.json")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
           "https://www.googleapis.com/auth/youtube"]


class YouTubeAdapter:

    def __init__(self):
        self.service = None

    def authenticate(self):
        # Authenticates with YouTube using stored OAuth2 tokens
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None

        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                if not os.path.exists(CLIENT_SECRETS_FILE):
                    raise FileNotFoundError(
                        f"YouTube client_secrets.json not found at {CLIENT_SECRETS_FILE}. "
                        "Download it from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
                creds = flow.run_local_server(port=8090)

            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        self.service = build("youtube", "v3", credentials=creds)
        return True

    def upload(self, video_path, metadata, thumbnail_path=None):
        # Uploads a video to YouTube with metadata
        from googleapiclient.http import MediaFileUpload

        if not self.service:
            self.authenticate()

        title = metadata.get("title", "Luminous Will")[:100]
        description = metadata.get("description", "")[:5000]
        tags = metadata.get("tags", [])[:50]
        category = metadata.get("category", "Education")

        # Map category name to ID
        category_ids = {"Education": "27", "People & Blogs": "22", "Entertainment": "24"}
        category_id = category_ids.get(category, "27")

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": "unlisted",
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)

        request = self.service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        print("[YOUTUBE] Starting resumable upload...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"[YOUTUBE] Upload progress: {int(status.progress() * 100)}%")

        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"[YOUTUBE] Uploaded: {video_url}")

        # Upload thumbnail if available
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                self.service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
                ).execute()
                print("[YOUTUBE] Thumbnail set")
            except Exception as e:
                print(f"[YOUTUBE] Thumbnail upload failed: {e}")

        return {"url": video_url, "video_id": video_id}
```

- [ ] **Step 4: Create tiktok_adapter.py**

```python
import os
import json
import requests
import config

# ============================================================
# TIKTOK ADAPTER
# Uploads videos via TikTok Content Posting API
# Requires creator account + approved developer app
# Token refresh: 24-hour expiry
# ============================================================

TOKEN_FILE = os.path.join(config.BASE_DIR, ".tiktok_token.json")

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")


class TikTokAdapter:

    def __init__(self):
        self.access_token = None
        self._load_token()

    def _load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                self.access_token = data.get("access_token")

    def _save_token(self, token_data):
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f, indent=2)
        self.access_token = token_data.get("access_token")

    def refresh_token(self):
        # Refreshes the TikTok access token
        if not os.path.exists(TOKEN_FILE):
            raise Exception("TikTok not authenticated. Run OAuth flow first.")

        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)

        refresh = data.get("refresh_token")
        if not refresh:
            raise Exception("No refresh token available")

        resp = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
            "client_key": TIKTOK_CLIENT_KEY,
            "client_secret": TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        })

        if resp.status_code == 200:
            self._save_token(resp.json())
            print("[TIKTOK] Token refreshed")
        else:
            raise Exception(f"Token refresh failed: {resp.status_code}")

    def upload(self, video_path, metadata):
        # Uploads a video to TikTok
        if not self.access_token:
            raise Exception("TikTok not authenticated")

        caption = metadata.get("caption", "")
        hashtags = metadata.get("hashtags", [])
        full_caption = f"{caption} {' '.join('#' + h for h in hashtags)}"[:150]

        file_size = os.path.getsize(video_path)

        # Step 1: Initialize upload
        init_resp = requests.post(
            "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json={
                "post_info": {
                    "title": full_caption,
                    "privacy_level": "SELF_ONLY",
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                },
            },
        )

        if init_resp.status_code != 200:
            raise Exception(f"TikTok init failed: {init_resp.status_code} - {init_resp.text}")

        data = init_resp.json().get("data", {})
        upload_url = data.get("upload_url")
        publish_id = data.get("publish_id")

        if not upload_url:
            raise Exception("No upload URL returned from TikTok")

        # Step 2: Upload video file
        with open(video_path, "rb") as f:
            upload_resp = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(file_size),
                },
                data=f,
            )

        if upload_resp.status_code not in (200, 201):
            raise Exception(f"TikTok upload failed: {upload_resp.status_code}")

        print(f"[TIKTOK] Uploaded, publish_id: {publish_id}")
        return {"url": f"https://www.tiktok.com", "publish_id": publish_id}
```

- [ ] **Step 5: Create instagram_adapter.py**

```python
import os
import json
import time
import requests
import config

# ============================================================
# INSTAGRAM ADAPTER
# Uploads Reels via Instagram Graph API (through Facebook)
# Requires Facebook Business/Creator account
# Token refresh: 60-day long-lived tokens
# ============================================================

TOKEN_FILE = os.path.join(config.BASE_DIR, ".instagram_token.json")

FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")


class InstagramAdapter:

    def __init__(self):
        self.access_token = None
        self.ig_user_id = None
        self._load_token()

    def _load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                self.access_token = data.get("access_token")
                self.ig_user_id = data.get("ig_user_id")

    def _save_token(self, token_data):
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f, indent=2)
        self.access_token = token_data.get("access_token")
        self.ig_user_id = token_data.get("ig_user_id")

    def upload(self, video_path, metadata):
        # Uploads a Reel to Instagram using container-based flow
        if not self.access_token or not self.ig_user_id:
            raise Exception("Instagram not authenticated")

        caption = metadata.get("caption", "")
        hashtags = metadata.get("hashtags", [])
        full_caption = f"{caption}\n\n{' '.join('#' + h for h in hashtags)}"

        # The video must be accessible via URL for Instagram API
        # For local files, you'd need to host temporarily
        # This implementation assumes the video is hosted (e.g., on the web server)
        # For local-only usage, see note below

        # Step 1: Create container
        container_resp = requests.post(
            f"https://graph.facebook.com/v21.0/{self.ig_user_id}/media",
            data={
                "media_type": "REELS",
                "video_url": video_path,  # Must be a public URL
                "caption": full_caption[:2200],
                "access_token": self.access_token,
            },
        )

        if container_resp.status_code != 200:
            raise Exception(f"Instagram container failed: {container_resp.text}")

        container_id = container_resp.json().get("id")

        # Step 2: Wait for container to be ready
        for _ in range(30):
            status_resp = requests.get(
                f"https://graph.facebook.com/v21.0/{container_id}",
                params={
                    "fields": "status_code",
                    "access_token": self.access_token,
                },
            )
            status = status_resp.json().get("status_code")
            if status == "FINISHED":
                break
            elif status == "ERROR":
                raise Exception("Instagram container processing failed")
            time.sleep(5)

        # Step 3: Publish
        publish_resp = requests.post(
            f"https://graph.facebook.com/v21.0/{self.ig_user_id}/media_publish",
            data={
                "creation_id": container_id,
                "access_token": self.access_token,
            },
        )

        if publish_resp.status_code != 200:
            raise Exception(f"Instagram publish failed: {publish_resp.text}")

        media_id = publish_resp.json().get("id")
        print(f"[INSTAGRAM] Published, media_id: {media_id}")

        return {"url": f"https://www.instagram.com/reel/{media_id}", "media_id": media_id}
```

- [ ] **Step 6: Create facebook_adapter.py**

```python
import os
import json
import requests
import config

# ============================================================
# FACEBOOK ADAPTER
# Uploads videos to Facebook Page/Profile via Graph API
# Shares OAuth credentials with Instagram adapter
# Token refresh: 60-day long-lived tokens
# ============================================================

TOKEN_FILE = os.path.join(config.BASE_DIR, ".facebook_token.json")


class FacebookAdapter:

    def __init__(self):
        self.access_token = None
        self.page_id = None
        self._load_token()

    def _load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                self.access_token = data.get("access_token")
                self.page_id = data.get("page_id")

    def upload(self, video_path, metadata):
        # Uploads a video to Facebook Page
        if not self.access_token:
            raise Exception("Facebook not authenticated")

        description = metadata.get("description", "")
        hashtags = metadata.get("hashtags", [])
        full_desc = f"{description}\n\n{' '.join('#' + h for h in hashtags)}"

        target_id = self.page_id or "me"

        # Upload video to Facebook
        with open(video_path, "rb") as video_file:
            resp = requests.post(
                f"https://graph-video.facebook.com/v21.0/{target_id}/videos",
                data={
                    "description": full_desc,
                    "access_token": self.access_token,
                },
                files={
                    "source": video_file,
                },
            )

        if resp.status_code != 200:
            raise Exception(f"Facebook upload failed: {resp.text}")

        video_id = resp.json().get("id")
        print(f"[FACEBOOK] Uploaded, video_id: {video_id}")

        return {"url": f"https://www.facebook.com/watch/?v={video_id}", "video_id": video_id}
```

- [ ] **Step 7: Commit all publisher files**

```bash
git add publisher.py youtube_adapter.py tiktok_adapter.py instagram_adapter.py facebook_adapter.py requirements.txt
git commit -m "feat: add publisher orchestrator and 4 platform adapters"
```

---

### Task 13: Scheduler

**Files:**
- Create: `C:\Users\User\LuminousWill\scheduler.py`

- [ ] **Step 1: Create scheduler.py**

```python
import os
import time
import random
import schedule
import config
from config import VideoFormat
from main import run_pipeline
from queue_manager import add_entry
from metadata_generator import generate_metadata
from thumbnail import generate_thumbnail
from script_generator import extract_chapters

# ============================================================
# SCHEDULER
# Generates videos on a cron schedule and queues them for review
# Long-form: Mon/Thu at 2 AM
# Short-form: Daily at 3 AM
# ============================================================

# --- Track used topics to avoid repetition ---
USED_TOPICS_FILE = os.path.join(config.BASE_DIR, ".used_topics.json")


def _load_used_topics():
    import json
    if os.path.exists(USED_TOPICS_FILE):
        with open(USED_TOPICS_FILE, "r") as f:
            return json.load(f)
    return []


def _save_used_topic(topic):
    import json
    used = _load_used_topics()
    used.append(topic)
    # Keep last 100 to allow recycling
    used = used[-100:]
    with open(USED_TOPICS_FILE, "w") as f:
        json.dump(used, f)


def _pick_topic():
    # Picks a topic that hasn't been used recently
    used = set(_load_used_topics())
    available = [t for t in config.TRENDING_TOPICS if t not in used]
    if not available:
        available = config.TRENDING_TOPICS
    topic = random.choice(available)
    _save_used_topic(topic)
    return topic


def generate_and_queue(video_format):
    # Generates a video and adds it to the review queue
    fmt = VideoFormat(video_format)
    topic = _pick_topic()
    fmt_str = fmt.value

    print(f"\n[SCHEDULER] Generating {fmt_str} video: {topic}")

    try:
        # Run the pipeline
        output_path = run_pipeline(topic=topic, video_format=fmt)

        if not output_path or not os.path.exists(output_path):
            print(f"[SCHEDULER] Pipeline failed for: {topic}")
            return

        # Generate thumbnail
        thumb_path = generate_thumbnail(output_path, topic)

        # Generate platform metadata
        # For long-form, we'd need chapters — pass empty for now
        metadata = generate_metadata(topic, [], fmt_str)

        # Determine target platforms based on format
        if fmt == VideoFormat.HORIZONTAL_LONG:
            targets = ["youtube"]
        else:
            targets = ["tiktok", "instagram", "facebook"]

        # Add to review queue
        add_entry(
            video_path=output_path,
            thumbnail_path=thumb_path,
            topic=topic,
            video_format=fmt_str,
            metadata=metadata,
            target_platforms=targets,
        )

        print(f"[SCHEDULER] Queued for review: {topic} ({fmt_str})")

    except Exception as e:
        print(f"[SCHEDULER] Error: {e}")


def run_scheduler():
    # Starts the scheduler loop
    # Configure schedules from environment or defaults
    long_schedule = os.getenv("SCHEDULE_LONG_FORM", "monday,thursday")
    short_schedule = os.getenv("SCHEDULE_SHORT_FORM", "daily")

    if "monday" in long_schedule:
        schedule.every().monday.at("02:00").do(generate_and_queue, "long")
    if "thursday" in long_schedule:
        schedule.every().thursday.at("02:00").do(generate_and_queue, "long")

    if short_schedule == "daily":
        schedule.every().day.at("03:00").do(generate_and_queue, "short")

    print("[SCHEDULER] Started. Schedules:")
    for job in schedule.get_jobs():
        print(f"  - {job}")
    print("[SCHEDULER] Waiting for next run... (Ctrl+C to stop)")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        fmt = sys.argv[2] if len(sys.argv) > 2 else "short"
        generate_and_queue(fmt)
    else:
        run_scheduler()
```

- [ ] **Step 2: Commit**

```bash
git add scheduler.py
git commit -m "feat: add video scheduler with cron-based generation and queue integration"
```

---

### Task 14: Web Dashboard — Queue API Routes

**Files:**
- Create: `C:\Users\User\luminous-will-web\app\api\queue\route.ts`
- Create: `C:\Users\User\luminous-will-web\app\api\queue\[id]\approve\route.ts`
- Create: `C:\Users\User\luminous-will-web\app\api\queue\[id]\reject\route.ts`
- Create: `C:\Users\User\luminous-will-web\lib\queue.ts`

- [ ] **Step 1: Create lib/queue.ts**

```typescript
// Queue operations — reads/writes queue.json from the Python pipeline directory
import { readFile, writeFile } from "fs/promises";
import path from "path";

// Path to the shared queue.json (Python pipeline writes, web reads)
const QUEUE_PATH = process.env.QUEUE_JSON_PATH || path.join(process.cwd(), "..", "LuminousWill", "queue.json");

export interface QueueEntry {
  id: string;
  format: "short" | "long";
  topic: string;
  video_path: string;
  thumbnail_path: string;
  metadata: {
    youtube?: { title: string; description: string; tags: string[]; category: string };
    tiktok?: { caption: string; hashtags: string[] };
    instagram?: { caption: string; hashtags: string[] };
    facebook?: { description: string; hashtags: string[] };
  };
  target_platforms: string[];
  status: "pending_review" | "approved" | "posting" | "posted" | "rejected" | "failed";
  created_at: string;
  scheduled_post_time: string | null;
  post_results: Record<string, { url: string; video_id?: string }>;
  error: string | null;
}

export async function loadQueue(): Promise<QueueEntry[]> {
  try {
    const data = await readFile(QUEUE_PATH, "utf-8");
    return JSON.parse(data);
  } catch {
    return [];
  }
}

export async function saveQueue(entries: QueueEntry[]): Promise<void> {
  await writeFile(QUEUE_PATH, JSON.stringify(entries, null, 2));
}

export async function getEntry(id: string): Promise<QueueEntry | null> {
  const entries = await loadQueue();
  return entries.find((e) => e.id === id) || null;
}

export async function updateEntry(id: string, updates: Partial<QueueEntry>): Promise<QueueEntry | null> {
  const entries = await loadQueue();
  const idx = entries.findIndex((e) => e.id === id);
  if (idx === -1) return null;
  entries[idx] = { ...entries[idx], ...updates };
  await saveQueue(entries);
  return entries[idx];
}
```

- [ ] **Step 2: Create app/api/queue/route.ts**

```typescript
import { NextResponse } from "next/server";
import { loadQueue } from "@/lib/queue";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status");

  let entries = await loadQueue();

  if (status) {
    entries = entries.filter((e) => e.status === status);
  }

  // Sort by created_at descending (newest first)
  entries.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return NextResponse.json(entries);
}
```

- [ ] **Step 3: Create app/api/queue/[id]/approve/route.ts**

```typescript
import { NextResponse } from "next/server";
import { updateEntry } from "@/lib/queue";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await request.json().catch(() => ({}));
  const scheduledTime = body.scheduled_post_time || null;

  const entry = await updateEntry(id, {
    status: "approved",
    scheduled_post_time: scheduledTime,
  });

  if (!entry) {
    return NextResponse.json({ error: "Entry not found" }, { status: 404 });
  }

  return NextResponse.json(entry);
}
```

- [ ] **Step 4: Create app/api/queue/[id]/reject/route.ts**

```typescript
import { NextResponse } from "next/server";
import { updateEntry } from "@/lib/queue";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const entry = await updateEntry(id, { status: "rejected" });

  if (!entry) {
    return NextResponse.json({ error: "Entry not found" }, { status: 404 });
  }

  return NextResponse.json(entry);
}
```

- [ ] **Step 5: Add QUEUE_JSON_PATH to .env.local**

```
QUEUE_JSON_PATH=C:\Users\User\LuminousWill\queue.json
```

- [ ] **Step 6: Commit**

```bash
cd C:\Users\User\luminous-will-web
git add lib/queue.ts app/api/queue/ .env.local
git commit -m "feat: add queue API routes for dashboard"
```

---

### Task 15: Web Dashboard — Queue List Page

**Files:**
- Create: `C:\Users\User\luminous-will-web\app\dashboard\page.tsx`
- Create: `C:\Users\User\luminous-will-web\app\dashboard\layout.tsx`

- [ ] **Step 1: Create dashboard layout**

Create `app/dashboard/layout.tsx`:

```tsx
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="py-6 px-6 border-b border-[#1a1a1a] flex items-center justify-between">
        <div className="flex items-center gap-4">
          <a href="/" className="text-xl font-bold tracking-[4px]" style={{ color: "#E8A817" }}>
            LUMINOUS WILL
          </a>
          <span className="text-xs uppercase tracking-wider" style={{ color: "#555" }}>
            Dashboard
          </span>
        </div>
        <a
          href="/"
          className="text-xs uppercase tracking-wider hover:text-[#E8A817] transition-colors"
          style={{ color: "#555" }}
        >
          Generator
        </a>
      </header>
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">{children}</main>
    </div>
  );
}
```

- [ ] **Step 2: Create dashboard queue list page**

Create `app/dashboard/page.tsx`:

```tsx
"use client";

import { useState, useEffect } from "react";

interface QueueEntry {
  id: string;
  format: "short" | "long";
  topic: string;
  status: string;
  created_at: string;
  thumbnail_path: string;
  target_platforms: string[];
  post_results: Record<string, { url: string }>;
}

const STATUS_COLORS: Record<string, string> = {
  pending_review: "#E8A817",
  approved: "#22c55e",
  posting: "#3b82f6",
  posted: "#22c55e",
  rejected: "#ef4444",
  failed: "#ef4444",
};

export default function DashboardPage() {
  const [entries, setEntries] = useState<QueueEntry[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQueue();
  }, [filter]);

  const fetchQueue = async () => {
    setLoading(true);
    const params = filter !== "all" ? `?status=${filter}` : "";
    const res = await fetch(`/api/queue${params}`);
    const data = await res.json();
    setEntries(data);
    setLoading(false);
  };

  const handleApprove = async (id: string) => {
    await fetch(`/api/queue/${id}/approve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    fetchQueue();
  };

  const handleReject = async (id: string) => {
    await fetch(`/api/queue/${id}/reject`, { method: "POST" });
    fetchQueue();
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold" style={{ color: "#E8A817" }}>
          Review Queue
        </h1>
        <div className="flex gap-2">
          {["all", "pending_review", "approved", "posted", "rejected"].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-1 text-xs uppercase tracking-wider rounded-lg border transition-all ${
                filter === s
                  ? "border-[#E8A817] text-[#E8A817] bg-[#E8A817]/10"
                  : "border-[#1a1a1a] text-[#555] hover:border-[#333]"
              }`}
            >
              {s.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16 text-[#555]">Loading...</div>
      ) : entries.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-[#555]">No videos in queue</p>
          <p className="text-xs text-[#333] mt-2">Videos will appear here after scheduled generation</p>
        </div>
      ) : (
        <div className="space-y-4">
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="p-4 rounded-xl border border-[#1a1a1a] bg-[#0a0a0a] flex items-center gap-4"
            >
              <div className="w-24 h-14 bg-[#111] rounded-lg flex-shrink-0 flex items-center justify-center">
                <span className="text-xs text-[#333]">
                  {entry.format === "long" ? "16:9" : "9:16"}
                </span>
              </div>

              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-medium text-white truncate">{entry.topic}</h3>
                <div className="flex items-center gap-3 mt-1">
                  <span
                    className="text-xs uppercase tracking-wider px-2 py-0.5 rounded"
                    style={{
                      color: STATUS_COLORS[entry.status] || "#555",
                      background: `${STATUS_COLORS[entry.status] || "#555"}15`,
                    }}
                  >
                    {entry.status.replace("_", " ")}
                  </span>
                  <span className="text-xs text-[#444]">{formatDate(entry.created_at)}</span>
                  <span className="text-xs text-[#444]">
                    {entry.target_platforms.join(", ")}
                  </span>
                </div>
              </div>

              {entry.status === "pending_review" && (
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={() => handleApprove(entry.id)}
                    className="px-4 py-2 text-xs uppercase tracking-wider rounded-lg bg-[#22c55e]/10 border border-[#22c55e]/30 text-[#22c55e] hover:bg-[#22c55e]/20 transition-all"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(entry.id)}
                    className="px-4 py-2 text-xs uppercase tracking-wider rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/30 text-[#ef4444] hover:bg-[#ef4444]/20 transition-all"
                  >
                    Reject
                  </button>
                </div>
              )}

              {entry.status === "posted" && entry.post_results && (
                <div className="flex gap-2 flex-shrink-0">
                  {Object.entries(entry.post_results).map(([platform, result]) => (
                    <a
                      key={platform}
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1 text-xs uppercase tracking-wider rounded-lg border border-[#1a1a1a] text-[#888] hover:text-[#E8A817] hover:border-[#E8A817] transition-all"
                    >
                      {platform}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd C:\Users\User\luminous-will-web
git add app/dashboard/
git commit -m "feat: add review queue dashboard with approve/reject flow"
```

---

### Task 16: Sync Pipeline to API Repo

**Files:**
- Modify: All pipeline files in `C:\Users\User\luminous-will-api\`

- [ ] **Step 1: Copy updated pipeline files to luminous-will-api**

The API repo is a copy of the pipeline modules. Copy all modified Python files:

```bash
cp C:\Users\User\LuminousWill\config.py C:\Users\User\luminous-will-api\config.py
cp C:\Users\User\LuminousWill\script_generator.py C:\Users\User\luminous-will-api\script_generator.py
cp C:\Users\User\LuminousWill\video_assembler.py C:\Users\User\luminous-will-api\video_assembler.py
cp C:\Users\User\LuminousWill\visuals.py C:\Users\User\luminous-will-api\visuals.py
cp C:\Users\User\LuminousWill\voiceover.py C:\Users\User\luminous-will-api\voiceover.py
cp C:\Users\User\LuminousWill\captions.py C:\Users\User\luminous-will-api\captions.py
cp C:\Users\User\LuminousWill\color_grading.py C:\Users\User\luminous-will-api\color_grading.py
cp C:\Users\User\LuminousWill\brand_reference.py C:\Users\User\luminous-will-api\brand_reference.py
```

- [ ] **Step 2: Update the API config.py paths for HF Spaces**

In the API copy, the paths use `/tmp`. Make sure the copied config.py still has the `/tmp` overrides at the bottom. If the copy overwrote them, re-add:

```python
# --- HF Spaces path overrides (at bottom of config.py) ---
if os.getenv("SPACE_ID"):
    OUTPUT_DIR = os.path.join("/tmp", "luminous_output")
    TEMP_DIR = os.path.join("/tmp", "luminous_temp")
    MUSIC_DIR = os.path.join("/tmp", "luminous_music")
```

- [ ] **Step 3: Update API requirements.txt**

Add the same new dependencies to the API requirements.txt:

```
google-generativeai>=0.8.0
```

- [ ] **Step 4: Commit**

```bash
cd C:\Users\User\luminous-will-api
git add -A
git commit -m "feat: sync pipeline with dual-format support from local"
```

---

### Task 17: Add Token Files to .gitignore

**Files:**
- Modify: `C:\Users\User\LuminousWill\.gitignore`

- [ ] **Step 1: Update .gitignore with all sensitive files**

Add these entries:

```
# --- Queue and tokens ---
queue.json
.youtube_token.json
.tiktok_token.json
.instagram_token.json
.facebook_token.json
.used_topics.json
client_secrets.json

# --- Existing ---
.env
temp/
output/
__pycache__/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add token files and queue to gitignore"
```

---

## Post-Implementation Checklist

- [ ] Install new Python dependencies: `pip install -r requirements.txt`
- [ ] Set GEMINI_API_KEY in `.env`
- [ ] Test short-form generation still works: `python main.py --format short`
- [ ] Test long-form generation: `python main.py --format long --topic "The psychology of silence and power"`
- [ ] Test scheduler manual run: `python scheduler.py --now short`
- [ ] Test web dashboard loads: `cd luminous-will-web && npm run dev`, visit `/dashboard`
- [ ] Set up Google Cloud Console project for YouTube API (one-time)
- [ ] Set up TikTok Developer app (one-time)
- [ ] Set up Facebook Developer app for Instagram + Facebook (one-time)
