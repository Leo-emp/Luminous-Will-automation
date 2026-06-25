# Premium Quality Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the Luminous Will video pipeline from basic dark motivation videos to premium YouTube channel quality (Motiversity/Mulligan Brothers tier) across all 15 spec sections.

**Architecture:** Incremental upgrades to the existing Python pipeline (`C:\Users\User\LuminousWill`) and Next.js web app (`C:\Users\User\luminous-will-web`). Each task modifies 1-3 files and is independently testable. The pipeline follows a linear flow: script → voiceover → footage → captions → assembly → thumbnail → metadata. The web app is a separate Next.js 15 project deployed on Vercel.

**Tech Stack:** Python 3.11+, MoviePy 2.x, Pillow, NumPy, Google Generative AI (Gemini 2.5 Flash), ElevenLabs API, Pexels/Pixabay/Storyblocks APIs, Next.js 15, React 19, Tailwind CSS 4, GitHub Actions

## Global Constraints

- All Python files use heavy `#` comments throughout (learning codebase — user preference)
- Brand aesthetic: dark, moody, cinematic. Amber accent `#E8A817`. No bright/happy/colorful content
- Voice: Adam (ElevenLabs ID `pNInz6obpgDQGcFmaJgB`), speed 0.83, `eleven_multilingual_v2`
- Format profiles: `VERTICAL_SHORT` (1080×1920, 60-90s) and `HORIZONTAL_LONG` (1920×1080, 8-12min)
- Storyblocks/Epidemic Sound are optional — pipeline must work identically without API keys
- All config values loaded from `.env` via `python-dotenv`
- Web app: black background, Inter font, amber accents, responsive
- No breaking changes to existing pipeline behavior when premium APIs are not configured
- Font fallback: Montserrat Bold → Arial Bold → system default

---

### Task 1: Config, Font & Test Infrastructure

**Files:**
- Modify: `config.py`
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Create: `pytest.ini`
- Download: `assets/fonts/Montserrat-Bold.ttf`

**Interfaces:**
- Consumes: existing `config.py` structure, `.env` file
- Produces: New config fields used by every subsequent task:
  - `config.STORYBLOCKS_API_KEY: str`
  - `config.STORYBLOCKS_API_SECRET: str`
  - `config.EPIDEMIC_SOUND_API_KEY: str`
  - `config.CAPTION_FONT_FILE: str` (path to Montserrat-Bold.ttf)
  - Format profile keys: `voiceover_boost_db`, `music_level_db`, `ken_burns_enabled`, `crossfade_duration`, `quality`

- [ ] **Step 1: Download Montserrat Bold font**

```bash
cd C:\Users\User\LuminousWill
mkdir -p assets/fonts
curl -L -o assets/fonts/Montserrat-Bold.ttf "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf"
```

Verify: file should be ~80-100KB TTF file.

- [ ] **Step 2: Create pytest infrastructure**

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
```

Create `tests/__init__.py` (empty file).

Add `pytest` to `requirements.txt`:
```
pytest>=7.0.0               # unit testing
```

- [ ] **Step 3: Update config.py with all new fields**

Replace the full `config.py` with:

```python
import os
from dotenv import load_dotenv
from enum import Enum

# ============================================================
# CONFIGURATION FILE FOR LUMINOUS WILL VIDEO PIPELINE
# Fill in your API keys in the .env file before running
# ============================================================

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# --- API Keys (set these in .env file) ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "").strip()
FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY", "").strip()

# --- Gemini API Key ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# --- Premium API Keys (optional — pipeline works without these) ---
# Storyblocks: premium stock footage + music
STORYBLOCKS_API_KEY = os.getenv("STORYBLOCKS_API_KEY", "").strip()
STORYBLOCKS_API_SECRET = os.getenv("STORYBLOCKS_API_SECRET", "").strip()
# Epidemic Sound: premium music (future slot)
EPIDEMIC_SOUND_API_KEY = os.getenv("EPIDEMIC_SOUND_API_KEY", "").strip()

# --- Video Format System ---
# Each format has its own resolution, bitrate, caption style, and search orientation
class VideoFormat(Enum):
    VERTICAL_SHORT = "short"    # 9:16, 60-90s
    HORIZONTAL_LONG = "long"    # 16:9, 8-12 min

# --- Format Profiles ---
# Each profile contains ALL format-specific settings
FORMAT_PROFILES = {
    VideoFormat.VERTICAL_SHORT: {
        # --- Resolution & output ---
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "bitrate": "12000k",
        "quality": "1080p",                  # default quality, overridable with --quality 4k
        # --- Search ---
        "pexels_orientation": "portrait",
        "duration_range": (60, 90),
        # --- Captions ---
        "caption_font_size": 65,
        "caption_position_y": 0.83,
        "caption_stroke_width": 2,
        # --- Color grading ---
        "brightness_factor": 0.55,
        "saturation_factor": 0.45,
        # --- Audio mixing (dB-based) ---
        "voiceover_boost_db": 1.5,           # +1.5 dB boost for voice clarity
        "music_level_db": -9,                # -9 dB constant, no ducking
        # --- Ken Burns ---
        "ken_burns_enabled": True,           # global toggle for motion effects
        # --- Transitions ---
        "transition_type": "mixed",          # "mixed" = per-segment crossfade or cut
        "crossfade_duration": 1.0,           # seconds for crossfade transitions
        # --- Clips ---
        "clip_duration_range": (2.5, 10),
        # --- Voice ---
        "voice_stability": 0.62,
        "script_source": "gemini",           # now gemini for both formats
    },
    VideoFormat.HORIZONTAL_LONG: {
        # --- Resolution & output ---
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "bitrate": "15000k",
        "quality": "1080p",
        # --- Search ---
        "pexels_orientation": "landscape",
        "duration_range": (480, 720),
        # --- Captions ---
        "caption_font_size": 48,
        "caption_position_y": 0.88,
        "caption_stroke_width": 3,
        # --- Color grading ---
        "brightness_factor": 0.60,
        "saturation_factor": 0.45,
        # --- Audio mixing (dB-based) ---
        "voiceover_boost_db": 1.5,
        "music_level_db": -9,
        # --- Ken Burns ---
        "ken_burns_enabled": True,
        # --- Transitions ---
        "transition_type": "mixed",
        "crossfade_duration": 1.0,
        # --- Clips ---
        "clip_duration_range": (8, 15),
        # --- Voice ---
        "voice_stability": 0.55,
        "script_source": "gemini",
    },
}

# --- 4K Resolution Overrides ---
# Applied when --quality 4k is passed
QUALITY_4K = {
    VideoFormat.VERTICAL_SHORT: {
        "width": 2160,
        "height": 3840,
        "bitrate": "30000k",
        "quality": "4k",
    },
    VideoFormat.HORIZONTAL_LONG: {
        "width": 3840,
        "height": 2160,
        "bitrate": "30000k",
        "quality": "4k",
    },
}


def get_format_profile(fmt: VideoFormat, quality: str = "1080p") -> dict:
    # Returns the full settings profile for a given format
    # If quality="4k", applies 4K resolution overrides
    profile = dict(FORMAT_PROFILES[fmt])
    if quality == "4k" and fmt in QUALITY_4K:
        profile.update(QUALITY_4K[fmt])
    return profile


# --- ElevenLabs Voice Settings ---
# Voice: Adam - Deep English Story Voice (free plan compatible)
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam voice ID
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"
VOICE_SETTINGS = {
    "stability": 0.62,           # 62% stability - controlled = authoritative tone
    "similarity_boost": 0.80,    # 80% similarity boost - consistent deep voice
    "style": 0.0,                # 0% style - no variation = commanding delivery
    "use_speaker_boost": True,   # speaker boost enabled - deeper resonance
}
VOICE_SPEED = 0.83  # matched to user's preferred pace

# --- Video Settings ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_FORMAT = "mp4"

# --- Caption Style ---
CAPTION_FONT_SIZE = 65
CAPTION_COLOR = "white"
CAPTION_HIGHLIGHT_COLOR = "#E8A817"  # warm amber (matched from video frames)
CAPTION_FONT = "Arial-Bold"
CAPTION_POSITION = ("center", 0.83)
CAPTION_STROKE_COLOR = "black"
CAPTION_STROKE_WIDTH = 2

# --- Font paths ---
# Montserrat Bold for premium captions and thumbnails
# Falls back to Arial Bold if not found
CAPTION_FONT_FILE = os.path.join(os.path.dirname(__file__), "assets", "fonts", "Montserrat-Bold.ttf")

# --- Color Grading (dark aesthetic) ---
BRIGHTNESS_FACTOR = 0.55
SATURATION_FACTOR = 0.45
CONTRAST_FACTOR = 1.20

# --- Audio Settings (legacy — new code uses dB values from profiles) ---
VOICEOVER_VOLUME = 1.0
MUSIC_VOLUME = 0.32

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# --- Logo Outro ---
LOGO_DURATION = 3

# --- Clip Settings ---
MIN_CLIP_DURATION = 2.5
MAX_CLIP_DURATION = 10

# --- Pexels Search Settings ---
PEXELS_ORIENTATION = "portrait"
PEXELS_SIZE = "large"
PEXELS_PER_PAGE = 10

# --- Trending Topics for Script Generation ---
TRENDING_TOPICS = [
    "The psychology of silence and power",
    "Why high-value people walk alone",
    "Dark psychology of manipulation tactics",
    "The quiet leader vs the loud victim",
    "Why loneliness is a superpower",
    "The psychology behind fake friends",
    "Signs of a mentally strong person",
    "Why successful people are quiet",
    "The art of not reacting",
    "Psychology of self-discipline",
    "Why people disrespect you (and how to stop it)",
    "The dark truth about comfort zones",
    "How emotional control changes everything",
    "The psychology of revenge vs moving on",
    "Why nice people finish last (the truth)",
    "Signs you are becoming dangerous (in a good way)",
    "The wolf mentality - psychology of lone wolves",
    "Why you should never explain yourself",
    "The 48 laws of power - key lessons",
    "Dark truths about human nature",
    "Why being feared is better than being loved",
    "The stoic mindset that changes your life",
    "Psychology of body language and dominance",
    "Why your silence terrifies them",
    "The power of walking away",
    "How narcissists manipulate you",
    "The mindset of a high-value man",
    "Why you attract toxic people",
    "The psychology of winning alone",
    "Why most people will never succeed",
    "The hidden envy around you",
    "Comfort is killing your potential",
]
```

- [ ] **Step 4: Write config tests**

Create `tests/test_config.py`:
```python
import os
import config
from config import VideoFormat, get_format_profile, QUALITY_4K

def test_format_profiles_exist():
    # Both format profiles must be defined
    assert VideoFormat.VERTICAL_SHORT in config.FORMAT_PROFILES
    assert VideoFormat.HORIZONTAL_LONG in config.FORMAT_PROFILES

def test_profile_has_all_required_keys():
    # Every profile must have the new premium fields
    required_keys = [
        "width", "height", "fps", "bitrate", "quality",
        "voiceover_boost_db", "music_level_db",
        "ken_burns_enabled", "crossfade_duration",
        "caption_font_size", "caption_position_y",
    ]
    for fmt in VideoFormat:
        profile = get_format_profile(fmt)
        for key in required_keys:
            assert key in profile, f"Missing '{key}' in {fmt.value} profile"

def test_4k_quality_override():
    # 4K mode should override resolution and bitrate
    profile = get_format_profile(VideoFormat.VERTICAL_SHORT, quality="4k")
    assert profile["width"] == 2160
    assert profile["height"] == 3840
    assert profile["bitrate"] == "30000k"
    assert profile["quality"] == "4k"

def test_default_quality_is_1080p():
    # Default quality should remain 1080p
    profile = get_format_profile(VideoFormat.VERTICAL_SHORT)
    assert profile["quality"] == "1080p"
    assert profile["width"] == 1080

def test_db_values_match_spec():
    # dB values must match the approved spec
    for fmt in VideoFormat:
        profile = get_format_profile(fmt)
        assert profile["voiceover_boost_db"] == 1.5
        assert profile["music_level_db"] == -9

def test_font_file_path_configured():
    # Font file path should point to assets/fonts/
    assert "Montserrat-Bold.ttf" in config.CAPTION_FONT_FILE
    assert "assets" in config.CAPTION_FONT_FILE

def test_storyblocks_keys_default_empty():
    # Premium API keys should default to empty (not crash)
    assert isinstance(config.STORYBLOCKS_API_KEY, str)
    assert isinstance(config.EPIDEMIC_SOUND_API_KEY, str)

def test_script_source_is_gemini():
    # Both formats now use gemini for script generation
    for fmt in VideoFormat:
        profile = get_format_profile(fmt)
        assert profile["script_source"] == "gemini"
```

- [ ] **Step 5: Run tests**

Run: `cd C:\Users\User\LuminousWill && python -m pytest tests/test_config.py -v`
Expected: All 8 tests PASS

- [ ] **Step 6: Commit**

```bash
git add config.py requirements.txt pytest.ini tests/ assets/fonts/Montserrat-Bold.ttf
git commit -m "feat: add premium config fields, Montserrat font, test infrastructure"
```

---

### Task 2: Adaptive Color Grading

**Files:**
- Modify: `color_grading.py` (full rewrite)
- Create: `tests/test_color_grading.py`

**Interfaces:**
- Consumes: `config.BRIGHTNESS_FACTOR`, `config.SATURATION_FACTOR`, `config.CONTRAST_FACTOR`, format profile
- Produces: `create_grader(profile) -> Callable[[np.ndarray], np.ndarray]` — same signature as before so `video_assembler.py` needs zero changes. Also produces `apply_dark_grade(frame) -> np.ndarray` for standalone use.

- [ ] **Step 1: Write color grading tests**

Create `tests/test_color_grading.py`:
```python
import numpy as np

def _make_frame(brightness=128, shape=(100, 100, 3)):
    # Helper: creates a solid-color test frame
    return np.full(shape, brightness, dtype=np.uint8)

def test_s_curve_produces_valid_output():
    from color_grading import _s_curve
    # S-curve should map 0→0, 0.5→~0.5, 1→1
    assert abs(_s_curve(0.0) - 0.0) < 0.01
    assert abs(_s_curve(1.0) - 1.0) < 0.01
    # Midpoint should be close to 0.5
    assert abs(_s_curve(0.5) - 0.5) < 0.1

def test_s_curve_increases_contrast():
    from color_grading import _s_curve
    # S-curve should push darks darker and lights lighter
    assert _s_curve(0.25) < 0.25  # dark values get darker
    assert _s_curve(0.75) > 0.75  # light values get lighter

def test_adaptive_intensity_dark_source():
    from color_grading import _get_adaptive_intensity
    # Already-dark frame (avg brightness < 30%) should get light touch
    dark_frame = _make_frame(brightness=50)  # ~20% brightness
    intensity = _get_adaptive_intensity(dark_frame)
    assert intensity < 1.0, "Dark frames should get reduced grade intensity"

def test_adaptive_intensity_bright_source():
    from color_grading import _get_adaptive_intensity
    # Bright frame (avg brightness > 60%) should get aggressive grade
    bright_frame = _make_frame(brightness=200)  # ~78% brightness
    intensity = _get_adaptive_intensity(bright_frame)
    assert intensity > 1.0, "Bright frames should get extra grade intensity"

def test_graded_frame_is_darker():
    from color_grading import apply_dark_grade
    # Graded frame should be darker than input (on average)
    frame = _make_frame(brightness=150)
    graded = apply_dark_grade(frame)
    assert graded.mean() < frame.mean()

def test_graded_frame_valid_range():
    from color_grading import apply_dark_grade
    # Output must be valid uint8 (0-255, no overflow)
    frame = _make_frame(brightness=200)
    graded = apply_dark_grade(frame)
    assert graded.dtype == np.uint8
    assert graded.min() >= 0
    assert graded.max() <= 255

def test_create_grader_returns_callable():
    from color_grading import create_grader
    profile = {"brightness_factor": 0.55, "saturation_factor": 0.45}
    grader = create_grader(profile)
    assert callable(grader)

def test_selective_saturation_preserves_blues():
    from color_grading import apply_dark_grade
    # Create a blue-ish frame — blues should be preserved more than greens
    blue_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    blue_frame[:, :, 2] = 180  # strong blue channel
    blue_frame[:, :, 0] = 40   # low red
    blue_frame[:, :, 1] = 40   # low green
    graded = apply_dark_grade(blue_frame)
    # Blue channel should still be the dominant channel
    assert graded[:, :, 2].mean() > graded[:, :, 0].mean()
    assert graded[:, :, 2].mean() > graded[:, :, 1].mean()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_color_grading.py -v`
Expected: FAIL — `_s_curve` and `_get_adaptive_intensity` don't exist yet

- [ ] **Step 3: Rewrite color_grading.py**

Replace the full file with:
```python
import numpy as np
import config

# ============================================================
# PREMIUM COLOR GRADING
# Applies cinematic dark aesthetic to stock footage
# Upgraded from mechanical linear transforms to film-quality:
#   - S-curve contrast (smooth, cinematic)
#   - Lift-Gamma-Gain model (industry standard)
#   - Selective saturation (preserve blues/golds, mute greens/reds)
#   - Adaptive intensity (reads source brightness, adjusts strength)
#   - Smooth shadow rolloff (deep blacks with retained detail)
#
# Every clip should look naturally shot on a cinema camera in
# dark moody conditions — not like stock footage with a filter
# ============================================================


def _s_curve(x, strength=1.0):
    """
    # S-curve contrast function (attempt to model film response)
    # Maps 0-1 input to 0-1 output with boosted contrast
    # strength controls how pronounced the S-curve is
    # At strength=1.0: shadows pushed ~15% darker, highlights ~15% brighter
    """
    # --- Attempt to be a softer curve, using a sine-based S ---
    # Sine-based S-curve: maps [0,1] to [0,1] with smooth rolloff
    import math
    # Base S-curve: sin remapped from [-pi/2, pi/2] to [0, 1]
    curved = 0.5 + 0.5 * math.sin((x - 0.5) * math.pi)
    # Blend between linear and curved based on strength
    return x + strength * (curved - x)


def _s_curve_array(arr, strength=1.0):
    """
    # Vectorized S-curve for numpy arrays
    # Same math as _s_curve but operates on full frames
    """
    curved = 0.5 + 0.5 * np.sin((arr - 0.5) * np.pi)
    return arr + np.float32(strength) * (curved - arr)


def _get_adaptive_intensity(frame):
    """
    # Reads the source frame brightness and returns a grade intensity multiplier
    # Already dark clips get a lighter grade (0.8x) to avoid crushing
    # Medium clips get full grade (1.0x)
    # Bright clips get aggressive grade (1.2x) to bring them into brand range
    #
    # Samples the first frame to determine the base brightness level
    """
    # --- Convert to grayscale and measure average brightness ---
    gray = np.mean(frame.astype(np.float32), axis=2)
    avg_brightness = np.mean(gray) / 255.0  # normalize to 0-1

    if avg_brightness < 0.30:
        # --- Already dark: light touch to avoid crushing details ---
        return 0.8
    elif avg_brightness > 0.60:
        # --- Bright source: needs aggressive darkening ---
        return 1.2
    else:
        # --- Medium brightness: standard full grade ---
        return 1.0


def apply_dark_grade(frame):
    """
    # Applies premium dark cinematic grading to a single frame
    # Uses the default config values (standalone use)
    #
    # Processing chain:
    #   1. Adaptive intensity measurement
    #   2. Lift-Gamma-Gain (shadows/mids/highlights control)
    #   3. S-curve contrast
    #   4. Selective saturation (preserve blues/golds, mute greens/reds)
    #   5. Split toning (cool shadows + warm highlights)
    #   6. Smooth vignette
    #
    # Args:
    #   frame: numpy array (H, W, 3) RGB uint8
    # Returns:
    #   graded frame as numpy array (H, W, 3) RGB uint8
    """
    grader = create_grader({
        "brightness_factor": config.BRIGHTNESS_FACTOR,
        "saturation_factor": config.SATURATION_FACTOR,
    })
    return grader(frame)


def apply_dark_grade_filter(get_frame, t):
    """
    # MoviePy-compatible filter function
    # Use with clip.transform(apply_dark_grade_filter)
    """
    return apply_dark_grade(get_frame(t))


def create_grader(profile):
    """
    # Returns a grading function calibrated to the format profile settings
    # The returned function takes a uint8 frame and returns a uint8 frame
    # Used by video_assembler.py: clip.image_transform(grader)
    """
    brightness = profile.get("brightness_factor", config.BRIGHTNESS_FACTOR)
    saturation = profile.get("saturation_factor", config.SATURATION_FACTOR)

    def grade_frame(frame):
        # --- Convert to float32 for processing ---
        img = frame.astype(np.float32) / 255.0

        # --- Step 0: Adaptive intensity —read source brightness ---
        intensity = _get_adaptive_intensity(frame)

        # --- Step 1: Lift-Gamma-Gain darkening ---
        # Lift (shadows): slight blue push, darken shadows
        # Gamma (midtones): reduce overall brightness
        # Gain (highlights): slight warm push
        #
        # Effective brightness = brightness_factor * intensity
        effective_brightness = brightness * intensity
        img *= np.float32(effective_brightness)

        # --- Step 2: Selective saturation ---
        # Convert to luminance for desaturation blend
        lum = (np.float32(0.299) * img[:,:,0]
             + np.float32(0.587) * img[:,:,1]
             + np.float32(0.114) * img[:,:,2])

        # --- Per-channel saturation factors ---
        # Preserve blues (ch 2) and warm tones, mute greens (ch 1) and reds (ch 0)
        sat_r = saturation * 0.7   # mute reds (distracting in dark content)
        sat_g = saturation * 0.6   # mute greens harder (most distracting)
        sat_b = saturation * 1.2   # preserve blues (brand color — cool shadows)

        img[:,:,0] = lum + np.float32(sat_r) * (img[:,:,0] - lum)
        img[:,:,1] = lum + np.float32(sat_g) * (img[:,:,1] - lum)
        img[:,:,2] = lum + np.float32(sat_b) * (img[:,:,2] - lum)
        del lum

        # --- Step 3: S-curve contrast ---
        # Applies the film-look S-curve for cinematic contrast
        # Strength scaled by intensity so dark clips don't get over-contrasted
        s_strength = 0.6 * intensity
        img = _s_curve_array(img, strength=s_strength)

        # --- Step 4: Smooth shadow rolloff ---
        # Instead of hard black crush, use a smooth rolloff
        # Shadows below 0.08 are compressed but NOT clipped
        shadow_mask = img < 0.10
        img[shadow_mask] = img[shadow_mask] * np.float32(0.5)

        # --- Step 5: Split toning ---
        avg = img.mean(axis=-1)

        # Shadows: subtle cool blue tint
        shadow_px = avg < 0.25
        img[:,:,2][shadow_px] += np.float32(0.04 * intensity)

        # Highlights: warm amber tint (brand color influence)
        hi_px = avg > 0.5
        img[:,:,0][hi_px] += np.float32(0.03 * intensity)
        img[:,:,1][hi_px] += np.float32(0.015 * intensity)
        del avg, shadow_px, hi_px

        # --- Step 6: Subtle vignette ---
        h, w = img.shape[:2]
        Y = np.linspace(-1, 1, h, dtype=np.float32)
        X = np.linspace(-1, 1, w, dtype=np.float32)
        dist = np.sqrt(Y[:,None]**2 + X[None,:]**2)
        vignette = np.float32(1.0) - np.float32(0.3) * np.clip(dist - 0.5, 0, 1)
        for c in range(3):
            img[:,:,c] *= vignette
        del dist, vignette

        # --- Clamp and return ---
        np.clip(img, 0, 1, out=img)
        return (img * 255).astype(np.uint8)

    return grade_frame
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_color_grading.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add color_grading.py tests/test_color_grading.py
git commit -m "feat: premium adaptive color grading with S-curve and selective saturation"
```

---

### Task 3: Caption Animations — Word-by-Word Reveal

**Files:**
- Modify: `captions.py`
- Modify: `video_assembler.py` (burn_captions function only)
- Create: `tests/test_captions.py`

**Interfaces:**
- Consumes: `config.CAPTION_FONT_FILE`, caption events with `words` array (already present)
- Produces: `render_caption_frame(text, highlight_word, frame_width, frame_height, font_size, position_y, stroke_width, words, current_time)` — updated signature with two new optional params. When `current_time` is not passed, renders all words visible (backward compatible).

- [ ] **Step 1: Write caption animation tests**

Create `tests/test_captions.py`:
```python
import numpy as np

def test_word_visibility_before_start():
    from captions import _is_word_visible
    # Word that hasn't started yet should be invisible
    visible, scale = _is_word_visible(word_start=2.0, word_end=2.5, current_time=1.0)
    assert visible is False

def test_word_visibility_during_animation():
    from captions import _is_word_visible
    # Word during its 0.08s animation window should be visible with scale < 1.0
    visible, scale = _is_word_visible(word_start=2.0, word_end=2.5, current_time=2.03)
    assert visible is True
    assert 0.9 <= scale < 1.0, f"Scale should be animating, got {scale}"

def test_word_visibility_after_settled():
    from captions import _is_word_visible
    # Word after animation should be fully visible at scale 1.0
    visible, scale = _is_word_visible(word_start=2.0, word_end=2.5, current_time=2.5)
    assert visible is True
    assert scale == 1.0

def test_word_visibility_no_current_time():
    from captions import _is_word_visible
    # When current_time is None, all words should be visible (backward compat)
    visible, scale = _is_word_visible(word_start=2.0, word_end=2.5, current_time=None)
    assert visible is True
    assert scale == 1.0

def test_render_caption_frame_returns_rgba():
    from captions import render_caption_frame
    frame = render_caption_frame("test words", None, 1080, 1920)
    assert frame.shape == (1920, 1080, 4)
    assert frame.dtype == np.uint8

def test_font_loading_fallback():
    from captions import _load_font
    # Should return a font object even if Montserrat isn't installed
    font = _load_font(65)
    assert font is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_captions.py -v`
Expected: FAIL — `_is_word_visible` and `_load_font` don't exist yet

- [ ] **Step 3: Rewrite captions.py**

Replace the full file — key changes: Montserrat font, `_is_word_visible()` helper, `_load_font()`, time-aware `render_caption_frame()`:

```python
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import config

# ============================================================
# CAPTION GENERATOR — PREMIUM
# Creates word-synced captions with word-by-word reveal animation
# Style: Montserrat Bold, white text, amber highlight on emphasis
# Animation: words appear one at a time, scale-in from 90%→100%
# ============================================================

# --- Animation timing ---
REVEAL_DURATION = 0.08   # seconds for scale-in animation per word


def _load_font(size):
    """
    # Loads the caption font with fallback chain:
    #   1. Montserrat Bold (premium, from assets/fonts/)
    #   2. Arial Bold (system font, Windows)
    #   3. PIL default (last resort)
    """
    # --- Try Montserrat Bold first (premium font) ---
    if os.path.exists(config.CAPTION_FONT_FILE):
        try:
            return ImageFont.truetype(config.CAPTION_FONT_FILE, size)
        except OSError:
            pass

    # --- Fallback: Arial Bold ---
    for font_path in ["arialbd.ttf", "Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue

    # --- Last resort: PIL default ---
    print("[CAPTIONS] WARNING: No suitable font found, using PIL default")
    return ImageFont.load_default()


def _is_word_visible(word_start, word_end, current_time):
    """
    # Determines if a word should be visible and its scale factor
    # Used for the word-by-word reveal animation
    #
    # Returns: (visible: bool, scale: float)
    #   visible=False → don't draw this word
    #   visible=True, scale=0.9-1.0 → animating in
    #   visible=True, scale=1.0 → fully settled
    #
    # When current_time is None, all words are visible (backward compat)
    """
    if current_time is None:
        return True, 1.0

    if current_time < word_start:
        # --- Word hasn't started yet → invisible ---
        return False, 0.0

    # --- Word is active or past → calculate scale ---
    elapsed = current_time - word_start
    if elapsed < REVEAL_DURATION:
        # --- Animating: scale from 90% to 100% over REVEAL_DURATION ---
        progress = elapsed / REVEAL_DURATION
        scale = 0.9 + 0.1 * progress
        return True, scale
    else:
        # --- Fully settled ---
        return True, 1.0


def create_caption_clips(word_timestamps, script_segments, video_duration):
    """
    # Creates caption data synced to each word from the voiceover
    # Groups words into display chunks (3-5 words at a time)
    # Highlights the emphasis word in each segment
    #
    # Args:
    #   word_timestamps: list of {word, start, end} from ElevenLabs
    #   script_segments: original script with emphasis_word info
    #   video_duration: total video duration in seconds
    #
    # Returns:
    #   list of caption events: {text, start, end, highlight_word, words}
    """

    print("[CAPTIONS] Building word-synced caption events...")

    if not word_timestamps:
        print("[CAPTIONS] WARNING: No timestamps, using fallback timing")
        return create_fallback_captions(script_segments, video_duration)

    # --- Build emphasis word lookup ---
    emphasis_words = set()
    for seg in script_segments:
        if "emphasis_word" in seg:
            emphasis_words.add(seg["emphasis_word"].lower())

    # --- Group words into display chunks ---
    # Show 4 words at a time for readability
    caption_events = []
    chunk_size = 4
    i = 0

    while i < len(word_timestamps):
        chunk_end = min(i + chunk_size, len(word_timestamps))
        chunk = word_timestamps[i:chunk_end]

        words_in_chunk = [w["word"] for w in chunk]
        caption_text = " ".join(words_in_chunk)

        # --- Check if any word in this chunk should be highlighted ---
        highlight_word = None
        for word_data in chunk:
            clean_word = word_data["word"].strip(".,!?;:'\"").lower()
            if clean_word in emphasis_words:
                highlight_word = word_data["word"]
                break

        start_time = chunk[0]["start"]
        end_time = chunk[-1]["end"]

        caption_events.append({
            "text": caption_text,
            "start": start_time,
            "end": end_time,
            "highlight_word": highlight_word,
            "words": chunk,  # individual word timing for per-word animation
        })

        i = chunk_end

    print(f"[CAPTIONS] Created {len(caption_events)} caption events")
    return caption_events


def create_fallback_captions(script_segments, video_duration):
    """
    # Fallback when no word timestamps available
    # Divides time equally among segments
    """
    time_per_segment = video_duration / len(script_segments)
    events = []
    for i, seg in enumerate(script_segments):
        events.append({
            "text": seg["text"],
            "start": i * time_per_segment,
            "end": (i + 1) * time_per_segment,
            "highlight_word": seg.get("emphasis_word"),
            "words": [],
        })
    return events


def render_caption_frame(text, highlight_word, frame_width, frame_height,
                         font_size=None, position_y=None, stroke_width=None,
                         words=None, current_time=None):
    """
    # Renders a single caption frame as a numpy array (RGBA)
    # Now supports word-by-word reveal animation:
    #   - If words and current_time are provided, only draws visible words
    #   - Each word scales in from 90%→100% over 0.08s
    #   - If not provided, draws all words (backward compatible)
    #
    # Args:
    #   text: caption text to render
    #   highlight_word: word to highlight in amber (or None)
    #   frame_width/frame_height: output dimensions
    #   font_size: override (default: config.CAPTION_FONT_SIZE)
    #   position_y: override (default: config.CAPTION_POSITION[1])
    #   stroke_width: override (default: config.CAPTION_STROKE_WIDTH)
    #   words: list of {word, start, end} for per-word timing
    #   current_time: current playback time in seconds
    #
    # Returns: numpy array (H, W, 4) RGBA
    """

    # --- Create transparent image ---
    img = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # --- Load font ---
    _font_size = font_size or config.CAPTION_FONT_SIZE
    _position_y = position_y or config.CAPTION_POSITION[1]
    _stroke_width = stroke_width or config.CAPTION_STROKE_WIDTH
    font = _load_font(_font_size)

    # --- Split text into words ---
    text_words = text.split()

    # --- Build word visibility map ---
    # Each word gets a (visible, scale) pair
    word_states = []
    if words and current_time is not None:
        for i, tw in enumerate(text_words):
            if i < len(words):
                vis, scale = _is_word_visible(words[i]["start"], words[i]["end"], current_time)
            else:
                vis, scale = True, 1.0
            word_states.append((vis, scale))
    else:
        # --- No timing info: all words visible ---
        word_states = [(True, 1.0)] * len(text_words)

    # --- Wrap text to lines ---
    lines = wrap_text_to_lines(text_words, font, draw, frame_width - 100)

    # --- Calculate vertical position ---
    line_height = _font_size + 8
    total_text_height = len(lines) * line_height
    y_start = int(frame_height * _position_y) - total_text_height // 2

    # --- Track which word index we're on across lines ---
    word_idx = 0

    # --- Draw each line ---
    for line_idx, line_words in enumerate(lines):
        line_text = " ".join(line_words)
        line_width = draw.textlength(line_text, font=font)
        x = (frame_width - line_width) // 2
        y = y_start + line_idx * line_height

        for word in line_words:
            vis, scale = word_states[word_idx] if word_idx < len(word_states) else (True, 1.0)
            word_idx += 1

            if not vis:
                # --- Word not visible yet: skip drawing but advance position ---
                word_width = draw.textlength(word + " ", font=font)
                x += word_width
                continue

            # --- Determine color (highlight or normal) ---
            is_highlight = False
            if highlight_word:
                clean_word = word.strip(".,!?;:'\"").lower()
                clean_highlight = highlight_word.strip(".,!?;:'\"").lower()
                if clean_word == clean_highlight:
                    is_highlight = True

            color = config.CAPTION_HIGHLIGHT_COLOR if is_highlight else config.CAPTION_COLOR

            # --- Apply scale animation via font size ---
            # Scale from 90% to 100% of font size during reveal
            if scale < 1.0:
                scaled_size = max(int(_font_size * scale), 10)
                scaled_font = _load_font(scaled_size)
                # Vertical offset to keep baseline aligned
                y_offset = int((_font_size - scaled_size) * 0.5)
            else:
                scaled_font = font
                y_offset = 0

            # --- Draw black stroke for readability ---
            for dx in range(-_stroke_width, _stroke_width + 1):
                for dy in range(-_stroke_width, _stroke_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text(
                            (x + dx, y + dy + y_offset), word,
                            font=scaled_font,
                            fill=config.CAPTION_STROKE_COLOR,
                        )

            # --- Draw the word ---
            draw.text((x, y + y_offset), word, font=scaled_font, fill=color)

            # --- Advance x position (always use full-size spacing) ---
            word_width = draw.textlength(word + " ", font=font)
            x += word_width

    return np.array(img)


def wrap_text_to_lines(words, font, draw, max_width):
    """
    # Wraps words into lines that fit within max_width
    # Returns list of lists of words per line
    """
    lines = []
    current_line = []

    for word in words:
        test_line = current_line + [word]
        test_text = " ".join(test_line)
        text_width = draw.textlength(test_text, font=font)

        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(current_line)
            current_line = [word]

    if current_line:
        lines.append(current_line)

    return lines


# --- Quick test ---
if __name__ == "__main__":
    frame = render_caption_frame(
        "Your silence is your greatest weapon",
        "weapon",
        config.VIDEO_WIDTH,
        config.VIDEO_HEIGHT,
    )
    test_img = Image.fromarray(frame)
    test_path = os.path.join(config.TEMP_DIR, "test_caption.png")
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    test_img.save(test_path)
    print(f"Test caption saved to: {test_path}")
```

- [ ] **Step 4: Update burn_captions in video_assembler.py**

In `video_assembler.py`, replace the `burn_captions` inner function (inside `assemble_video`, around line 71-93) to pass `t` and `words` to the renderer:

```python
    def burn_captions(get_frame, t):
        frame = get_frame(t)
        for i, event in enumerate(caption_events):
            if event["start"] <= t < event["end"]:
                # --- Time-aware rendering: pass current time + word timing ---
                cache_key = (i, int(t * 12.5))  # cache per ~80ms for animation
                if cache_key not in _caption_render_cache:
                    _caption_render_cache.clear()
                    rgba = render_caption_frame(
                        event["text"],
                        event.get("highlight_word"),
                        frame_w,
                        frame_h,
                        font_size=profile["caption_font_size"],
                        position_y=profile["caption_position_y"],
                        stroke_width=profile["caption_stroke_width"],
                        words=event.get("words"),
                        current_time=t,
                    )
                    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
                    rgb = rgba[:, :, :3].astype(np.float32)
                    _caption_render_cache[cache_key] = (alpha, rgb)
                a, rgb = _caption_render_cache[cache_key]
                result = frame.astype(np.float32)
                result = result * (1.0 - a) + rgb * a
                return result.astype(np.uint8)
        return frame
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_captions.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add captions.py video_assembler.py tests/test_captions.py
git commit -m "feat: word-by-word caption reveal with Montserrat Bold font"
```

---

### Task 4: Audio Mixing — dB-Based, No Ducking

**Files:**
- Modify: `video_assembler.py` (mix_audio function only)
- Create: `tests/test_audio_mixing.py`

**Interfaces:**
- Consumes: `profile["voiceover_boost_db"]`, `profile["music_level_db"]` from Task 1
- Produces: `mix_audio(voiceover, music_path, voiceover_duration, profile) -> AudioClip` — same signature, new behavior

- [ ] **Step 1: Write audio mixing tests**

Create `tests/test_audio_mixing.py`:
```python
import math

def test_db_to_linear_positive():
    from video_assembler import _db_to_linear
    # +1.5 dB should be ~1.19x
    gain = _db_to_linear(1.5)
    assert abs(gain - 1.189) < 0.01

def test_db_to_linear_negative():
    from video_assembler import _db_to_linear
    # -9 dB should be ~0.355x
    gain = _db_to_linear(-9)
    assert abs(gain - 0.355) < 0.01

def test_db_to_linear_zero():
    from video_assembler import _db_to_linear
    # 0 dB should be exactly 1.0x (unity)
    gain = _db_to_linear(0)
    assert gain == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_audio_mixing.py -v`
Expected: FAIL — `_db_to_linear` doesn't exist yet

- [ ] **Step 3: Rewrite mix_audio in video_assembler.py**

Add the `_db_to_linear` helper at module level, then replace `mix_audio`:

```python
def _db_to_linear(db):
    """
    # Converts decibels to linear gain
    # Formula: linear = 10^(dB/20)
    # +1.5 dB → 1.19x, -9 dB → 0.355x, 0 dB → 1.0x
    """
    return 10 ** (db / 20.0)


def mix_audio(voiceover, music_path, voiceover_duration, profile=None):
    """
    # Mixes voiceover with background music using dB-based levels
    # No ducking — constant music level throughout (spec §6)
    #
    # Levels from profile:
    #   voiceover_boost_db: +1.5 dB (clarity + authority)
    #   music_level_db: -9 dB constant (supports, never overpowers)
    #
    # Music gets fade-in (2s) and fade-out (3s) at the edges
    """

    total_duration = voiceover_duration + config.LOGO_DURATION

    # --- Apply voiceover boost ---
    vo_boost_db = profile.get("voiceover_boost_db", 1.5) if profile else 1.5
    vo_gain = _db_to_linear(vo_boost_db)
    boosted_voiceover = voiceover.with_volume_scaled(vo_gain)
    audio_layers = [boosted_voiceover]

    if music_path and os.path.exists(music_path):
        try:
            music = AudioFileClip(music_path)

            # --- Loop music if shorter than video ---
            if music.duration < total_duration:
                loops = int(total_duration / music.duration) + 1
                music = music.looped(n=loops)

            music = music.subclipped(0, total_duration)

            # --- Apply constant dB level to music ---
            music_db = profile.get("music_level_db", -9) if profile else -9
            music_gain = _db_to_linear(music_db)
            music = music.with_volume_scaled(music_gain)

            print(f"[ASSEMBLER] Audio mix: voice {vo_boost_db:+.1f}dB ({vo_gain:.2f}x), "
                  f"music {music_db:+.1f}dB ({music_gain:.3f}x) — constant, no ducking")

            # --- Fade in/out at edges ---
            music = music.with_effects([afx.AudioFadeIn(2.0), afx.AudioFadeOut(3.0)])
            audio_layers.append(music)

        except Exception as e:
            print(f"[ASSEMBLER] Could not load music: {e}")

    if len(audio_layers) > 1:
        return CompositeAudioClip(audio_layers)
    else:
        return boosted_voiceover
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_audio_mixing.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add video_assembler.py tests/test_audio_mixing.py
git commit -m "feat: dB-based audio mixing, remove ducking system"
```

---

### Task 5: Voiceover Validation & Cleanup

**Files:**
- Modify: `voiceover.py`
- Create: `tests/test_voiceover.py`

**Interfaces:**
- Consumes: ElevenLabs API response (audio + timestamps)
- Produces: `generate_voiceover(script_text, output_path, profile) -> list[dict]` — same return type, now with cleaned text + validated audio + trimmed pauses + recalculated timestamps

- [ ] **Step 1: Write voiceover tests**

Create `tests/test_voiceover.py`:
```python
def test_clean_script_text_ellipsis():
    from voiceover import clean_script_text
    assert clean_script_text("Wait... Think again...") == "Wait. Think again."

def test_clean_script_text_em_dash():
    from voiceover import clean_script_text
    assert clean_script_text("Power—real power") == "Power, real power"
    assert clean_script_text("Power -- real power") == "Power, real power"

def test_clean_script_text_double_spaces():
    from voiceover import clean_script_text
    assert "  " not in clean_script_text("too  many   spaces")

def test_clean_script_text_smart_quotes():
    from voiceover import clean_script_text
    result = clean_script_text("“Hello” ‘world’")
    assert "“" not in result
    assert "”" not in result
    assert '"' in result or "'" in result

def test_find_long_pauses_detects_gap():
    from voiceover import _find_long_pauses
    timestamps = [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 2.5, "end": 3.0},  # 2.0s gap (> 1.5s threshold)
    ]
    pauses = _find_long_pauses(timestamps, threshold=1.5)
    assert len(pauses) == 1
    assert pauses[0]["gap_start"] == 0.5
    assert pauses[0]["gap_end"] == 2.5

def test_find_long_pauses_ignores_short():
    from voiceover import _find_long_pauses
    timestamps = [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 1.0, "end": 1.5},  # 0.5s gap (under threshold)
    ]
    pauses = _find_long_pauses(timestamps, threshold=1.5)
    assert len(pauses) == 0

def test_recalculate_timestamps_after_trim():
    from voiceover import _recalculate_timestamps
    timestamps = [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 3.0, "end": 3.5},
    ]
    # Trimmed 1.2s from the pause at position 0.5-3.0
    trims = [{"position": 0.5, "removed": 1.2}]
    new_ts = _recalculate_timestamps(timestamps, trims)
    # "Hello" is before the trim → unchanged
    assert new_ts[0]["start"] == 0.0
    # "world" is after the trim → shifted 1.2s earlier
    assert abs(new_ts[1]["start"] - 1.8) < 0.01
    assert abs(new_ts[1]["end"] - 2.3) < 0.01
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_voiceover.py -v`
Expected: FAIL

- [ ] **Step 3: Add validation functions to voiceover.py**

Add these functions and modify `generate_voiceover`:

```python
import re

def clean_script_text(text):
    """
    # Cleans script text before sending to ElevenLabs
    # Saves credits by preventing pronunciation issues
    #
    # Fixes:
    #   - ... → . (ellipsis causes weird pauses)
    #   - -- and — → , (em dashes cause tone breaks)
    #   - Double spaces → single space
    #   - Smart quotes → ASCII quotes
    #   - Unusual characters stripped
    """
    # --- Replace ellipsis with period ---
    text = text.replace("...", ".")
    # --- Replace em dashes with comma ---
    text = text.replace("—", ",")
    text = text.replace("--", ",")
    # --- Smart quotes to ASCII ---
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    # --- Normalize whitespace ---
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _find_long_pauses(word_timestamps, threshold=1.5):
    """
    # Finds gaps between words longer than threshold seconds
    # Returns list of {gap_start, gap_end, duration, after_word_index}
    """
    pauses = []
    for i in range(len(word_timestamps) - 1):
        gap_start = word_timestamps[i]["end"]
        gap_end = word_timestamps[i + 1]["start"]
        gap_duration = gap_end - gap_start
        if gap_duration > threshold:
            pauses.append({
                "gap_start": gap_start,
                "gap_end": gap_end,
                "duration": gap_duration,
                "after_word_index": i,
            })
    return pauses


def _recalculate_timestamps(word_timestamps, trims):
    """
    # Shifts all word timestamps after each trim point
    # trims: list of {position: float, removed: float}
    # Each word after a trim position gets shifted earlier by the removed amount
    """
    new_timestamps = []
    for wt in word_timestamps:
        new_wt = dict(wt)
        total_shift = 0.0
        for trim in trims:
            if new_wt["start"] > trim["position"]:
                total_shift += trim["removed"]
        new_wt["start"] -= total_shift
        new_wt["end"] -= total_shift
        new_timestamps.append(new_wt)
    return new_timestamps


def _validate_audio(audio_path, expected_duration=None):
    """
    # Validates the downloaded voiceover file
    # Returns (is_valid, reason)
    """
    from moviepy import AudioFileClip
    import numpy as np

    # --- Check file size ---
    file_size = os.path.getsize(audio_path)
    if file_size < 10000:
        return False, f"File too small ({file_size} bytes)"

    try:
        clip = AudioFileClip(audio_path)
    except Exception as e:
        return False, f"Cannot load audio: {e}"

    # --- Check duration ---
    if clip.duration == 0:
        clip.close()
        return False, "Zero duration"

    if expected_duration and clip.duration < expected_duration * 0.7:
        clip.close()
        return False, f"Too short ({clip.duration:.1f}s vs expected {expected_duration:.1f}s)"

    # --- Check for volume spikes (glitches) ---
    try:
        audio_data = clip.to_soundarray(fps=22050)
        window = int(22050 * 0.1)  # 0.1s windows
        for start in range(0, len(audio_data) - window, window):
            chunk = audio_data[start:start + window]
            chunk_rms = np.sqrt(np.mean(chunk ** 2))
            # Check surrounding context
            ctx_start = max(0, start - window * 3)
            ctx_end = min(len(audio_data), start + window * 4)
            ctx_rms = np.sqrt(np.mean(audio_data[ctx_start:ctx_end] ** 2))
            if ctx_rms > 0 and chunk_rms > ctx_rms * 3.0:
                clip.close()
                return False, f"Volume spike detected at {start / 22050:.1f}s"
    except Exception:
        pass

    clip.close()
    return True, "OK"


def _trim_long_pauses(audio_path, word_timestamps, threshold=1.5, target=0.8):
    """
    # Trims pauses longer than threshold down to target seconds
    # Returns (new_audio_path, new_timestamps, trims_applied)
    """
    from moviepy import AudioFileClip, concatenate_audioclips

    pauses = _find_long_pauses(word_timestamps, threshold)
    if not pauses:
        return audio_path, word_timestamps, []

    print(f"[VOICEOVER] Found {len(pauses)} long pauses to trim")

    clip = AudioFileClip(audio_path)
    segments = []
    trims = []
    last_end = 0.0

    for pause in pauses:
        # --- Keep audio up to the pause ---
        segments.append(clip.subclipped(last_end, pause["gap_start"]))
        # --- Add target-length silence (0.8s) instead of the full pause ---
        segments.append(clip.subclipped(pause["gap_start"], pause["gap_start"] + target))
        removed = pause["duration"] - target
        trims.append({"position": pause["gap_start"], "removed": removed})
        last_end = pause["gap_end"]

    # --- Add remaining audio ---
    if last_end < clip.duration:
        segments.append(clip.subclipped(last_end, clip.duration))

    # --- Export trimmed audio ---
    trimmed = concatenate_audioclips(segments)
    trimmed_path = audio_path.replace(".mp3", "_trimmed.mp3")
    trimmed.write_audiofile(trimmed_path, logger=None)
    trimmed.close()
    clip.close()

    # --- Recalculate timestamps ---
    new_timestamps = _recalculate_timestamps(word_timestamps, trims)

    print(f"[VOICEOVER] Trimmed {sum(t['removed'] for t in trims):.1f}s of pauses")
    return trimmed_path, new_timestamps, trims
```

Then modify `generate_voiceover` to use these:

```python
def generate_voiceover(script_text, output_path, profile=None):
    """
    # Generates voiceover audio from script text using ElevenLabs
    # Now with: text cleaning, validation, pause trimming, retry
    """

    print("[VOICEOVER] Generating speech with ElevenLabs...")

    # --- Pre-send: Clean script text (saves credits) ---
    cleaned_text = clean_script_text(script_text)
    if cleaned_text != script_text:
        print("[VOICEOVER] Cleaned script text (removed special chars)")

    # --- Build the API request ---
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}/with-timestamps"
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    voice_settings = dict(config.VOICE_SETTINGS)
    if profile and "voice_stability" in profile:
        voice_settings["stability"] = profile["voice_stability"]

    payload = {
        "text": cleaned_text,
        "model_id": config.ELEVENLABS_MODEL_ID,
        "voice_settings": voice_settings,
        "speed": config.VOICE_SPEED,
    }

    # --- Attempt generation (max 1 retry for corruption) ---
    max_attempts = 2
    for attempt in range(max_attempts):
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            print(f"[VOICEOVER] ERROR: API returned {response.status_code}")
            raise Exception(f"ElevenLabs API error: {response.status_code}")

        result = response.json()

        # --- Save audio ---
        import base64
        audio_bytes = base64.b64decode(result["audio_base64"])
        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        # --- Extract word timestamps ---
        word_timestamps = extract_word_timestamps(result.get("alignment", {}))

        # --- Post-download validation ---
        # Estimate expected duration from word count (~2.6 words/sec at 0.83 speed)
        expected_duration = len(cleaned_text.split()) / 2.6
        is_valid, reason = _validate_audio(output_path, expected_duration)

        if is_valid:
            break
        elif attempt < max_attempts - 1:
            print(f"[VOICEOVER] Validation failed ({reason}), retrying once...")
        else:
            print(f"[VOICEOVER] WARNING: Audio validation failed ({reason}), using best attempt")

    # --- Post-process: trim long pauses ---
    output_path, word_timestamps, trims = _trim_long_pauses(
        output_path, word_timestamps, threshold=1.5, target=0.8
    )

    # --- Save timestamps ---
    timestamps_path = output_path.replace(".mp3", "_timestamps.json").replace("_trimmed", "")
    with open(timestamps_path, "w") as f:
        json.dump(word_timestamps, f, indent=2)

    print(f"[VOICEOVER] Audio saved: {output_path}")
    print(f"[VOICEOVER] Found {len(word_timestamps)} words with timestamps")

    return word_timestamps
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_voiceover.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add voiceover.py tests/test_voiceover.py
git commit -m "feat: voiceover text cleaning, validation, and pause trimming"
```

---

### Task 6: Ken Burns Effect

**Files:**
- Modify: `video_assembler.py` (create_base_video function)
- Create: `tests/test_ken_burns.py`

**Interfaces:**
- Consumes: `profile["ken_burns_enabled"]`, segment `motion_style` field (from script generator — defaults to `"static"` if not present)
- Produces: `_apply_ken_burns(clip, motion_style, duration) -> VideoFileClip` — new helper function

- [ ] **Step 1: Write Ken Burns tests**

Create `tests/test_ken_burns.py`:
```python
def test_ken_burns_zoom_params():
    from video_assembler import _get_ken_burns_params
    params = _get_ken_burns_params("ken_burns_zoom", 5.0)
    assert params["start_scale"] == 1.0
    assert params["end_scale"] == 1.12
    assert params["pan_x"] == 0.0

def test_ken_burns_pan_params():
    from video_assembler import _get_ken_burns_params
    params = _get_ken_burns_params("ken_burns_pan", 5.0)
    assert params["pan_x"] == 0.05  # 5% horizontal drift
    assert params["start_scale"] == 1.0

def test_ken_burns_zoom_out_params():
    from video_assembler import _get_ken_burns_params
    params = _get_ken_burns_params("slow_zoom_out", 5.0)
    assert params["start_scale"] == 1.12
    assert params["end_scale"] == 1.0

def test_static_returns_none():
    from video_assembler import _get_ken_burns_params
    params = _get_ken_burns_params("static", 5.0)
    assert params is None

def test_default_is_static():
    from video_assembler import _get_ken_burns_params
    params = _get_ken_burns_params(None, 5.0)
    assert params is None
```

- [ ] **Step 2: Implement Ken Burns in video_assembler.py**

Add these functions to `video_assembler.py`:

```python
def _get_ken_burns_params(motion_style, duration):
    """
    # Returns motion parameters for a clip based on its motion_style
    # Returns None for static clips (no effect)
    #
    # Styles:
    #   ken_burns_zoom: slow zoom in 1.0x → 1.12x
    #   ken_burns_pan: slow horizontal pan, 5% drift
    #   slow_zoom_out: pull-back 1.12x → 1.0x
    #   static/None: no effect
    """
    if not motion_style or motion_style == "static":
        return None

    if motion_style == "ken_burns_zoom":
        return {"start_scale": 1.0, "end_scale": 1.12, "pan_x": 0.0, "pan_y": 0.0}
    elif motion_style == "ken_burns_pan":
        return {"start_scale": 1.0, "end_scale": 1.0, "pan_x": 0.05, "pan_y": 0.0}
    elif motion_style == "slow_zoom_out":
        return {"start_scale": 1.12, "end_scale": 1.0, "pan_x": 0.0, "pan_y": 0.0}
    else:
        return None


def _apply_ken_burns(clip, params, target_w, target_h):
    """
    # Applies Ken Burns motion to a clip
    # Oversizes the clip slightly then crops with moving window
    #
    # The clip is rendered at a larger size (12% bigger)
    # then a crop window moves over it to create the motion
    """
    if params is None:
        return clip

    duration = clip.duration
    start_scale = params["start_scale"]
    end_scale = params["end_scale"]
    pan_x = params["pan_x"]

    # --- Resize clip to maximum scale needed ---
    max_scale = max(start_scale, end_scale)
    oversized_w = int(target_w * max_scale)
    oversized_h = int(target_h * max_scale)
    clip = clip.resized((oversized_w, oversized_h))

    def crop_at_time(get_frame, t):
        frame = get_frame(t)
        h, w = frame.shape[:2]
        progress = t / duration if duration > 0 else 0

        # --- Calculate current scale ---
        current_scale = start_scale + (end_scale - start_scale) * progress
        crop_w = int(target_w * (max_scale / current_scale))
        crop_h = int(target_h * (max_scale / current_scale))

        # --- Calculate crop center with pan offset ---
        cx = w // 2 + int(w * pan_x * (progress - 0.5))
        cy = h // 2

        x1 = max(0, cx - crop_w // 2)
        y1 = max(0, cy - crop_h // 2)
        x2 = min(w, x1 + crop_w)
        y2 = min(h, y1 + crop_h)

        cropped = frame[y1:y2, x1:x2]

        # --- Resize back to target ---
        from PIL import Image
        img = Image.fromarray(cropped)
        img = img.resize((target_w, target_h), Image.LANCZOS)
        return np.array(img)

    return clip.transform(crop_at_time)
```

Then in `create_base_video`, after `fit_clip` and before `clip.image_transform(grader)`, add the Ken Burns application:

```python
            # --- Apply Ken Burns motion (if enabled and segment has motion_style) ---
            if profile.get("ken_burns_enabled", False) and idx < len(script_segments_ref):
                motion_style = script_segments_ref[idx].get("motion_style", "static")
                kb_params = _get_ken_burns_params(motion_style, needed)
                if kb_params:
                    clip = _apply_ken_burns(clip, kb_params, frame_w, frame_h)
                    print(f"[ASSEMBLER] Ken Burns: {motion_style} on clip {idx+1}")
```

Note: `create_base_video` needs access to `script_segments`. Modify its signature to accept `script_segments` as a parameter and pass it from `assemble_video`.

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_ken_burns.py -v`
Expected: All 5 tests PASS

- [ ] **Step 4: Commit**

```bash
git add video_assembler.py tests/test_ken_burns.py
git commit -m "feat: selective Ken Burns effect (zoom, pan, zoom-out per clip)"
```

---

### Task 7: Context-Aware Transitions + 4K Output

**Files:**
- Modify: `video_assembler.py` (create_base_video — transition logic)
- Modify: `main.py` (add `--quality 4k` CLI flag)
- Create: `tests/test_transitions.py`

**Interfaces:**
- Consumes: segment `transition` field, `profile["crossfade_duration"]`, `profile["quality"]`
- Produces: Crossfade/hard-cut transitions between clips in the assembled video. New CLI: `python main.py --quality 4k`

- [ ] **Step 1: Write transition tests**

Create `tests/test_transitions.py`:
```python
def test_transition_heuristic_mood_change():
    from video_assembler import _get_transition_type
    seg_a = {"mood": "dark", "transition": None}
    seg_b = {"mood": "reflective", "transition": None}
    assert _get_transition_type(seg_a, seg_b) == "crossfade"

def test_transition_heuristic_same_mood():
    from video_assembler import _get_transition_type
    seg_a = {"mood": "intense", "transition": None}
    seg_b = {"mood": "intense", "transition": None}
    assert _get_transition_type(seg_a, seg_b) == "cut"

def test_transition_explicit_override():
    from video_assembler import _get_transition_type
    seg_a = {"mood": "intense", "transition": None}
    seg_b = {"mood": "intense", "transition": "crossfade"}
    # When segment has explicit transition, use it
    assert _get_transition_type(seg_a, seg_b) == "crossfade"

def test_first_segment_crossfade():
    from video_assembler import _get_transition_type
    # First segment (no previous) should crossfade for clean open
    assert _get_transition_type(None, {"mood": "dark"}) == "crossfade"
```

- [ ] **Step 2: Implement transitions in video_assembler.py**

Add the helper function:

```python
def _get_transition_type(prev_segment, current_segment):
    """
    # Determines transition type between two segments
    # Returns "crossfade" or "cut"
    #
    # Priority:
    #   1. Explicit transition field on current segment
    #   2. First segment → crossfade (clean open)
    #   3. Mood change between segments → crossfade
    #   4. Same mood continues → hard cut (keeps momentum)
    """
    # --- First segment: always crossfade for clean open ---
    if prev_segment is None:
        return "crossfade"

    # --- Explicit override from script generator ---
    explicit = current_segment.get("transition") if current_segment else None
    if explicit in ("crossfade", "cut"):
        return explicit

    # --- Heuristic: mood change → crossfade, same mood → cut ---
    prev_mood = prev_segment.get("mood", "")
    curr_mood = current_segment.get("mood", "") if current_segment else ""

    if prev_mood != curr_mood:
        return "crossfade"
    else:
        return "cut"
```

Then modify the FFmpeg concat in `create_base_video` to apply crossfades between clips that need them. The simplest approach: when a transition is "crossfade", overlap the clips by `crossfade_duration` using MoviePy's `CompositeVideoClip` with `CrossFadeIn`.

- [ ] **Step 3: Add 4K CLI flag to main.py**

Update the argparse section in `main.py`:

```python
    parser.add_argument("--quality", choices=["1080p", "4k"], default="1080p",
                        help="Output quality: 1080p (default) or 4k (premium)")
```

And pass it through:
```python
        run_pipeline(topic=args.topic, video_format=fmt, quality=args.quality)
```

Update `run_pipeline` signature and `get_format_profile` call:
```python
def run_pipeline(topic=None, video_format=None, quality="1080p"):
    ...
    profile = get_format_profile(video_format, quality=quality)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_transitions.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add video_assembler.py main.py tests/test_transitions.py
git commit -m "feat: context-aware transitions and 4K output option"
```

---

### Task 8: Premium Footage — Storyblocks Integration

**Files:**
- Create: `storyblocks.py`
- Modify: `visuals.py`
- Create: `tests/test_storyblocks.py`

**Interfaces:**
- Consumes: `config.STORYBLOCKS_API_KEY`, `config.STORYBLOCKS_API_SECRET`
- Produces: `search_storyblocks_video(query, orientation, used_ids) -> list[dict]` and `download_storyblocks_video(video_meta, output_dir, index) -> str|None`

- [ ] **Step 1: Write Storyblocks tests**

Create `tests/test_storyblocks.py`:
```python
def test_storyblocks_disabled_without_key(monkeypatch):
    import config
    monkeypatch.setattr(config, "STORYBLOCKS_API_KEY", "")
    from storyblocks import is_storyblocks_available
    assert is_storyblocks_available() is False

def test_storyblocks_enabled_with_key(monkeypatch):
    import config
    monkeypatch.setattr(config, "STORYBLOCKS_API_KEY", "test_key")
    monkeypatch.setattr(config, "STORYBLOCKS_API_SECRET", "test_secret")
    from storyblocks import is_storyblocks_available
    assert is_storyblocks_available() is True

def test_scoring_resolution_bonus():
    from visuals import _score_video_relevance
    # 4K video should score higher than HD (via resolution bonus)
    video_4k = {"url": "dark-lion-cinematic", "image": "", "user": {"name": ""}, "width": 3840, "height": 2160}
    video_hd = {"url": "dark-lion-cinematic", "image": "", "user": {"name": ""}, "width": 1920, "height": 1080}
    score_4k = _score_video_relevance(video_4k, "lion power", "dark lion cinematic", source="pexels")
    score_hd = _score_video_relevance(video_hd, "lion power", "dark lion cinematic", source="pexels")
    assert score_4k >= score_hd

def test_scoring_rejects_below_720p():
    from visuals import _score_video_relevance
    # Video below 720p should be heavily penalized
    video_low = {"url": "dark-lion", "image": "", "user": {"name": ""}, "width": 480, "height": 360}
    score = _score_video_relevance(video_low, "lion", "dark lion", source="pexels")
    # Low-res penalty should bring score very low
    assert score < 1.0
```

- [ ] **Step 2: Create storyblocks.py**

```python
import os
import time
import hmac
import hashlib
import requests
import config

# ============================================================
# STORYBLOCKS API CLIENT
# Premium stock footage + music search and download
# Only active when STORYBLOCKS_API_KEY is set in .env
# Falls back silently when not configured
# ============================================================


def is_storyblocks_available():
    """
    # Checks if Storyblocks API is configured
    """
    return bool(config.STORYBLOCKS_API_KEY and config.STORYBLOCKS_API_SECRET)


def search_storyblocks_video(query, orientation="portrait", used_ids=None):
    """
    # Searches Storyblocks video library
    # Returns list of video result dicts
    """
    if not is_storyblocks_available():
        return []

    if used_ids is None:
        used_ids = set()

    # --- Build authenticated request ---
    # Storyblocks uses HMAC-SHA256 authentication
    endpoint = "https://api.graphicstock.com/api/v2/videos/search"
    expires = int(time.time()) + 300

    # --- HMAC signature ---
    message = f"/api/v2/videos/search{expires}"
    signature = hmac.new(
        config.STORYBLOCKS_API_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    params = {
        "APIKEY": config.STORYBLOCKS_API_KEY,
        "EXPIRES": expires,
        "HMAC": signature,
        "keywords": query,
        "content_type": "footage",
        "results_per_page": 15,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=15)
        if response.status_code != 200:
            print(f"[STORYBLOCKS] API error: {response.status_code}")
            return []

        data = response.json()
        results = data.get("results", [])

        # --- Filter out used videos ---
        available = [r for r in results if r.get("id") not in used_ids]
        return available

    except Exception as e:
        print(f"[STORYBLOCKS] Search error: {e}")
        return []


def download_storyblocks_video(video_meta, output_dir, index):
    """
    # Downloads a Storyblocks video clip
    # Returns file path or None
    """
    download_url = video_meta.get("preview_url") or video_meta.get("comp_download_url")
    if not download_url:
        return None

    file_path = os.path.join(output_dir, f"clip_{index:03d}.mp4")

    try:
        response = requests.get(download_url, stream=True, timeout=60)
        if response.status_code != 200:
            return None

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        if os.path.getsize(file_path) < 50000:
            os.remove(file_path)
            return None

        print(f"[STORYBLOCKS] Downloaded: {os.path.basename(file_path)}")
        return file_path

    except Exception as e:
        print(f"[STORYBLOCKS] Download error: {e}")
        return None


def search_storyblocks_music(query, used_ids=None):
    """
    # Searches Storyblocks music/audio library
    # Returns list of audio result dicts
    """
    if not is_storyblocks_available():
        return []

    if used_ids is None:
        used_ids = set()

    endpoint = "https://api.graphicstock.com/api/v2/audio/search"
    expires = int(time.time()) + 300

    message = f"/api/v2/audio/search{expires}"
    signature = hmac.new(
        config.STORYBLOCKS_API_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    params = {
        "APIKEY": config.STORYBLOCKS_API_KEY,
        "EXPIRES": expires,
        "HMAC": signature,
        "keywords": query,
        "content_type": "music",
        "results_per_page": 10,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=15)
        if response.status_code != 200:
            return []

        data = response.json()
        return data.get("results", [])

    except Exception as e:
        print(f"[STORYBLOCKS] Music search error: {e}")
        return []
```

- [ ] **Step 3: Update visuals.py scoring to include resolution bonus**

Add to `_score_video_relevance` in `visuals.py`:

```python
    # --- Score 4: Resolution bonus (new) ---
    width = video_meta.get("width", 0)
    height = video_meta.get("height", 0)
    if width >= 3840 or height >= 3840:
        score += 1.0  # 4K bonus
    elif width >= 1920 or height >= 1920:
        score += 0.5  # HD bonus
    elif width < 720 and height < 720 and width > 0:
        score -= 3.0  # Below 720p penalty
```

And add Storyblocks as the first source in `search_and_download_videos`:

```python
        # --- Try Storyblocks first (premium footage) ---
        from storyblocks import is_storyblocks_available, search_storyblocks_video, download_storyblocks_video
        if is_storyblocks_available():
            sb_results = search_storyblocks_video(keywords, orientation, used_storyblocks_ids)
            for video_meta in sb_results[:5]:
                score = _score_video_relevance(video_meta, script_text, keywords, source="storyblocks")
                all_candidates.append((score, video_meta, "storyblocks"))
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_storyblocks.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add storyblocks.py visuals.py tests/test_storyblocks.py
git commit -m "feat: Storyblocks premium footage integration with scoring improvements"
```

---

### Task 9: Premium Music — Storyblocks + Epidemic Sound

**Files:**
- Modify: `music.py`
- Create: `tests/test_music.py`

**Interfaces:**
- Consumes: `config.STORYBLOCKS_API_KEY`, `config.EPIDEMIC_SOUND_API_KEY`, `storyblocks.search_storyblocks_music()` from Task 8
- Produces: `select_music(script_segments, music_dir) -> str|None` — same signature, new fallback chain

- [ ] **Step 1: Write music tests**

Create `tests/test_music.py`:
```python
def test_dominant_mood_detection():
    from music import get_dominant_mood
    segments = [
        {"mood": "dark"}, {"mood": "dark"}, {"mood": "intense"},
        {"mood": "dark"}, {"mood": "reflective"},
    ]
    assert get_dominant_mood(segments) == "dark"

def test_dominant_mood_fallback():
    from music import get_dominant_mood
    # No mood tags → defaults to "intense"
    segments = [{"text": "no mood"}, {"text": "also no mood"}]
    assert get_dominant_mood(segments) == "intense"

def test_storyblocks_mood_query_mapping():
    from music import STORYBLOCKS_MOOD_QUERIES
    # All 4 moods should have search queries defined
    for mood in ["dark", "intense", "reflective", "powerful"]:
        assert mood in STORYBLOCKS_MOOD_QUERIES
        assert len(STORYBLOCKS_MOOD_QUERIES[mood]) > 0

def test_epidemic_sound_placeholder():
    from music import _epidemic_sound_search
    # Should return None (placeholder — not implemented yet)
    result = _epidemic_sound_search("dark ambient")
    assert result is None
```

- [ ] **Step 2: Update music.py**

Add Storyblocks music layer at the top of the fallback chain and Epidemic Sound placeholder:

```python
# --- Storyblocks mood-to-query mapping for music ---
STORYBLOCKS_MOOD_QUERIES = {
    "dark": "dark ambient cinematic suspense",
    "intense": "intense epic cinematic trailer",
    "reflective": "reflective cinematic piano",
    "powerful": "powerful epic triumphant orchestra",
}


def _epidemic_sound_search(query):
    """
    # Placeholder for future Epidemic Sound integration
    # Returns None when EPIDEMIC_SOUND_API_KEY is empty
    """
    if not config.EPIDEMIC_SOUND_API_KEY:
        return None
    # TODO: implement when Epidemic Sound API access is obtained
    return None


def _storyblocks_music_fallback(mood, output_dir):
    """
    # Searches Storyblocks music library for a mood-matched track
    # Returns file path to downloaded track, or None
    """
    from storyblocks import is_storyblocks_available, search_storyblocks_music

    if not is_storyblocks_available():
        return None

    query = STORYBLOCKS_MOOD_QUERIES.get(mood, STORYBLOCKS_MOOD_QUERIES["intense"])
    results = search_storyblocks_music(query)

    if not results:
        return None

    # --- Download the first result ---
    track = results[0]
    download_url = track.get("preview_url") or track.get("comp_download_url")
    if not download_url:
        return None

    try:
        import requests
        response = requests.get(download_url, timeout=30)
        if response.status_code != 200:
            return None

        os.makedirs(output_dir, exist_ok=True)
        track_name = track.get("title", "storyblocks_track")[:50]
        safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in track_name).strip()
        file_path = os.path.join(output_dir, f"{safe_name or 'premium_track'}.mp3")

        with open(file_path, "wb") as f:
            f.write(response.content)

        if os.path.getsize(file_path) < 50000:
            os.remove(file_path)
            return None

        print(f"[MUSIC] Storyblocks: downloaded \"{track_name}\"")
        return file_path

    except Exception as e:
        print(f"[MUSIC] Storyblocks music error: {e}")
        return None
```

Then update `select_music` to use the new chain:
```
# Priority: Epidemic Sound → Storyblocks → Local mood-matched → Local general → Local any → Freesound
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_music.py -v`
Expected: All 4 tests PASS

- [ ] **Step 4: Commit**

```bash
git add music.py tests/test_music.py
git commit -m "feat: Storyblocks music integration with Epidemic Sound placeholder"
```

---

### Task 10: Script Generation Overhaul — Gemini for Both Formats

**Files:**
- Modify: `script_generator.py` (major rewrite)
- Create: `generated_history.json` (pre-seeded with 17 videos)
- Create: `tests/test_script_generator.py`

**Interfaces:**
- Consumes: `config.GEMINI_API_KEY`, `config.TRENDING_TOPICS`
- Produces: `generate_script(topic, custom_hook, video_format) -> (list[dict], str)` — same signature. Each segment dict now includes `motion_style` and `transition` fields. Also produces `discover_topics() -> list[str]` and `load_generated_history() -> list[dict]`.

- [ ] **Step 1: Create generated_history.json**

```json
[
  {"topic": "Being average is not a choice", "hook": "You were never meant to be average", "angle": "refusing mediocrity as identity", "date": "2026-04-27"},
  {"topic": "Cheap Dopamine", "hook": "Your brain is being hijacked", "angle": "dopamine addiction destroying potential", "date": "2026-04-27"},
  {"topic": "Comfort is a threat", "hook": "Comfort is killing your potential", "angle": "comfort zone as silent destroyer", "date": "2026-04-27"},
  {"topic": "Debt of discipline", "hook": "You owe yourself discipline", "angle": "discipline as debt to future self", "date": "2026-04-27"},
  {"topic": "Emotional Detachment", "hook": "Stop feeling everything", "angle": "strategic emotional control", "date": "2026-04-27"},
  {"topic": "Execution matters the most", "hook": "Ideas are worthless without execution", "angle": "execution over planning", "date": "2026-04-27"},
  {"topic": "Focus on the present", "hook": "You're living in the wrong timeline", "angle": "present moment as only reality", "date": "2026-04-27"},
  {"topic": "High value solitude", "hook": "If you're always alone, this message is for you", "angle": "loneliness as sign of outgrowing environment", "date": "2026-04-27"},
  {"topic": "How to achieve flow state", "hook": "The secret state of peak performance", "angle": "flow state as competitive advantage", "date": "2026-04-27"},
  {"topic": "Human Loyalty", "hook": "Most people are loyal to their needs, not to you", "angle": "transactional nature of loyalty", "date": "2026-04-27"},
  {"topic": "Master your emotions", "hook": "Your emotions are being used against you", "angle": "emotional mastery as power tool", "date": "2026-04-27"},
  {"topic": "Power of Silence", "hook": "The most powerful people never raise their voice", "angle": "psychological authority through silence", "date": "2026-04-27"},
  {"topic": "Procrastination", "hook": "You're not lazy, you're scared", "angle": "procrastination as fear response", "date": "2026-04-27"},
  {"topic": "Stop waiting too long", "hook": "Time is the one thing you can't get back", "angle": "urgency and mortality awareness", "date": "2026-04-27"},
  {"topic": "The quiet leader vs the loud victim", "hook": "The loud ones expose everything", "angle": "quiet leadership vs victimhood", "date": "2026-04-27"},
  {"topic": "Validation", "hook": "You don't need anyone's permission to become great", "angle": "external validation as weakness", "date": "2026-04-27"},
  {"topic": "Why real life feels boring now", "hook": "Your brain has been rewired", "angle": "dopamine desensitization from content", "date": "2026-04-27"}
]
```

- [ ] **Step 2: Write script generator tests**

Create `tests/test_script_generator.py`:
```python
import json
import os

def test_generated_history_loads():
    from script_generator import load_generated_history
    history = load_generated_history()
    assert isinstance(history, list)
    assert len(history) >= 17  # pre-seeded with 17 videos

def test_generated_history_has_required_fields():
    from script_generator import load_generated_history
    history = load_generated_history()
    for entry in history:
        assert "topic" in entry
        assert "hook" in entry
        assert "angle" in entry
        assert "date" in entry

def test_hook_validation_rejects_generic():
    from script_generator import _is_strong_hook
    # Generic hook without "you" or emotional trigger → weak
    assert _is_strong_hook("Life is about choices") is False

def test_hook_validation_accepts_personal():
    from script_generator import _is_strong_hook
    # Personal hook with "you" → strong
    assert _is_strong_hook("If you're always alone, this is for you") is True

def test_segment_has_motion_and_transition():
    from script_generator import _build_short_form_heuristics
    segments = [
        {"text": "test", "visual_keywords": "dark lion cinematic", "mood": "dark"},
        {"text": "test2", "visual_keywords": "mountain peak clouds", "mood": "reflective"},
    ]
    enriched = _build_short_form_heuristics(segments)
    for seg in enriched:
        assert "motion_style" in seg
        assert "transition" in seg

def test_motion_style_heuristic():
    from script_generator import _infer_motion_style
    assert _infer_motion_style("mountain peak landscape clouds") == "ken_burns_pan"
    assert _infer_motion_style("man running boxing training") == "static"
    assert _infer_motion_style("chess board silhouette portrait") == "ken_burns_zoom"
    assert _infer_motion_style("random words here") == "static"
```

- [ ] **Step 3: Rewrite script_generator.py**

Full rewrite with: Gemini for both formats, topic discovery, generated_history.json, hook validation, motion_style and transition fields. Delete the 5 template scripts (keep a minimal 3-segment emergency fallback). Key new functions:

- `load_generated_history() -> list[dict]`
- `save_to_history(topic, hook, angle)`
- `discover_topics() -> list[str]` (Gemini-powered)
- `_is_strong_hook(text) -> bool`
- `_infer_motion_style(visual_keywords) -> str`
- `_build_short_form_heuristics(segments) -> list[dict]`
- `generate_script(topic, custom_hook, video_format) -> (list[dict], str)` — now calls Gemini for both formats

The full implementation is extensive (300+ lines). Key structural changes:
- Delete `HOOK_TEMPLATES`, `get_template_script()`, all 5 script dicts, `_chain_template_scripts()`
- Both formats call Gemini with format-specific prompts
- Short-form prompt: 25 segments, 60-90s, hook validation
- Long-form prompt: 50 segments, narrative arc (unchanged structure, updated to include motion_style + transition)
- Emergency fallback: 10 pre-written hooks + generic segments, only used when Gemini API is completely down

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_script_generator.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add script_generator.py generated_history.json tests/test_script_generator.py
git commit -m "feat: Gemini script generation for both formats with topic discovery"
```

---

### Task 11: Premium Thumbnails

**Files:**
- Modify: `thumbnail.py` (full rewrite)
- Create: `tests/test_thumbnail.py`

**Interfaces:**
- Consumes: `config.CAPTION_FONT_FILE`, `config.GEMINI_API_KEY`
- Produces: `generate_thumbnail(video_path, title, output_path) -> str` — same signature, premium output

- [ ] **Step 1: Write thumbnail tests**

Create `tests/test_thumbnail.py`:
```python
import numpy as np

def test_frame_scoring_prefers_contrast():
    from thumbnail import _score_frame
    # High contrast frame should score higher than flat frame
    high_contrast = np.zeros((100, 100, 3), dtype=np.uint8)
    high_contrast[:50, :] = 200  # top half bright
    high_contrast[50:, :] = 20   # bottom half dark

    flat = np.full((100, 100, 3), 100, dtype=np.uint8)

    assert _score_frame(high_contrast) > _score_frame(flat)

def test_frame_scoring_penalizes_too_dark():
    from thumbnail import _score_frame
    very_dark = np.full((100, 100, 3), 10, dtype=np.uint8)
    medium = np.full((100, 100, 3), 80, dtype=np.uint8)
    # Very dark frames should score lower than medium brightness
    assert _score_frame(medium) > _score_frame(very_dark)

def test_frame_scoring_includes_sharpness():
    from thumbnail import _score_frame
    # Frame with edges should score higher on sharpness than blurry
    sharp = np.zeros((100, 100, 3), dtype=np.uint8)
    sharp[40:60, 40:60] = 255  # sharp white square
    blurry = np.full((100, 100, 3), 128, dtype=np.uint8)
    assert _score_frame(sharp) > _score_frame(blurry)
```

- [ ] **Step 2: Rewrite thumbnail.py**

Key upgrades:
- Sample 20-30 frames (up from 10)
- Score on: contrast, subject presence, color interest, sharpness
- Gemini generates 2-3 word punch line
- Montserrat Bold, all caps, white text with black stroke + amber outer glow
- Enhanced vignette (heavier than video)
- Bottom gradient for text readability

```python
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import VideoFileClip
import config

# ============================================================
# PREMIUM THUMBNAIL GENERATOR
# Picks the most striking frame and adds punchy text overlay
# Goal: looks like a designer made it in Photoshop
# ============================================================

THUMB_WIDTH = 1280
THUMB_HEIGHT = 720


def generate_thumbnail(video_path, title, output_path=None):
    # Generates a premium branded thumbnail
    # Frame scoring: contrast + subject + color + sharpness
    # Text: Gemini 2-3 word punch line, Montserrat Bold, amber glow

    if output_path is None:
        output_path = video_path.replace(".mp4", "_thumb.jpg")

    # --- Extract and score candidate frames ---
    clip = VideoFileClip(video_path)
    duration = clip.duration
    num_candidates = 25  # sample more frames for better selection

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
        best_frame = np.zeros((THUMB_HEIGHT, THUMB_WIDTH, 3), dtype=np.uint8)

    # --- Resize ---
    img = Image.fromarray(best_frame)
    img = img.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)

    # --- Generate punch line via Gemini ---
    punch_line = _generate_punch_line(title)

    # --- Apply premium visual treatment ---
    img = _apply_thumbnail_grade(img)

    # --- Add text overlay ---
    img = _add_text_overlay(img, punch_line)

    # --- Save ---
    img = img.convert("RGB")
    img.save(output_path, "JPEG", quality=95)
    print(f"[THUMBNAIL] Premium thumbnail saved: {output_path}")
    return output_path


def _score_frame(frame):
    # Scores a frame for thumbnail quality (0-10 scale)
    # Factors: contrast, brightness, sharpness, color interest
    gray = np.mean(frame.astype(np.float32), axis=2)
    brightness = np.mean(gray)
    contrast = np.std(gray)

    # --- Brightness score: prefer medium-dark (60-100 range) ---
    brightness_score = 1.0 - abs(brightness - 80) / 128.0

    # --- Contrast score: higher is better ---
    contrast_score = min(contrast / 50.0, 1.5)

    # --- Sharpness score: Laplacian variance ---
    # High variance = sharp edges = more interesting subject
    dy = np.diff(gray, axis=0)
    dx = np.diff(gray, axis=1)
    sharpness = (np.std(dy) + np.std(dx)) / 2.0
    sharpness_score = min(sharpness / 30.0, 1.0)

    # --- Color interest: std dev across channels ---
    color_var = np.std([frame[:,:,0].mean(), frame[:,:,1].mean(), frame[:,:,2].mean()])
    color_score = min(color_var / 30.0, 1.0)

    return (brightness_score * 0.2
            + contrast_score * 0.4
            + sharpness_score * 0.25
            + color_score * 0.15)


def _generate_punch_line(title):
    # Uses Gemini to create a 2-3 word punch line
    # Falls back to first 2 words of title if no API key
    if not config.GEMINI_API_KEY:
        words = title.upper().split()[:3]
        return " ".join(words)

    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""Generate a 2-3 word punch line for a dark motivation video thumbnail.
Topic: "{title}"
Rules: ALL CAPS, maximum 3 words, punchy, emotional, commanding.
Examples: "STAY SILENT", "COMFORT KILLS", "NEVER AVERAGE", "WALK ALONE"
Respond with ONLY the punch line, nothing else."""
        response = model.generate_content(prompt)
        punch = response.text.strip().upper()
        # Sanitize: max 3 words
        words = punch.split()[:3]
        return " ".join(words)
    except Exception as e:
        print(f"[THUMBNAIL] Gemini punch line failed: {e}")
        words = title.upper().split()[:3]
        return " ".join(words)


def _apply_thumbnail_grade(img):
    # Applies enhanced dark grade for thumbnail (heavier than video)
    # Darker vignette, slightly warmer subject area
    img = img.convert("RGBA")

    # --- Heavy vignette ---
    vignette = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    cx, cy = THUMB_WIDTH // 2, THUMB_HEIGHT // 2
    max_dist = ((THUMB_WIDTH/2)**2 + (THUMB_HEIGHT/2)**2) ** 0.5
    for y in range(THUMB_HEIGHT):
        for x in range(0, THUMB_WIDTH, 4):  # step by 4 for performance
            dist = ((x - cx)**2 + (y - cy)**2) ** 0.5
            alpha = int(min(1.0, max(0, (dist / max_dist - 0.3) * 1.5)) * 180)
            vdraw.rectangle([x, y, x+4, y+1], fill=(0, 0, 0, alpha))

    img = Image.alpha_composite(img, vignette)

    # --- Bottom gradient for text area ---
    gradient = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(gradient)
    for y in range(THUMB_HEIGHT - 250, THUMB_HEIGHT):
        alpha = int(((y - (THUMB_HEIGHT - 250)) / 250.0) * 220)
        gdraw.line([(0, y), (THUMB_WIDTH, y)], fill=(0, 0, 0, alpha))

    img = Image.alpha_composite(img, gradient)
    return img


def _add_text_overlay(img, text):
    # Adds the punch line text with premium styling
    # White text, black stroke, subtle amber glow
    draw = ImageDraw.Draw(img)

    # --- Load Montserrat Bold ---
    font_size = 72
    if os.path.exists(config.CAPTION_FONT_FILE):
        try:
            font = ImageFont.truetype(config.CAPTION_FONT_FILE, font_size)
        except OSError:
            font = ImageFont.truetype("arialbd.ttf", font_size)
    else:
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    # --- Position text centered near bottom ---
    text_width = draw.textlength(text, font=font)
    x = (THUMB_WIDTH - text_width) // 2
    y = THUMB_HEIGHT - 120

    # --- Black stroke (heavy for thumbnail) ---
    stroke = 4
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill="black")

    # --- Amber outer glow (subtle) ---
    glow_font_size = font_size + 2
    try:
        glow_font = ImageFont.truetype(config.CAPTION_FONT_FILE, glow_font_size)
    except OSError:
        glow_font = font
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            draw.text((x + dx - 1, y + dy - 1), text, font=glow_font, fill=(232, 168, 23, 60))

    # --- White text ---
    draw.text((x, y), text, font=font, fill="white")

    return img
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_thumbnail.py -v`
Expected: All 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add thumbnail.py tests/test_thumbnail.py
git commit -m "feat: premium thumbnails with frame scoring and Gemini punch lines"
```

---

### Task 12: Viral Social Media Captions

**Files:**
- Modify: `metadata_generator.py` (rewrite prompt)
- Create: `tests/test_metadata.py`

**Interfaces:**
- Consumes: `config.GEMINI_API_KEY`, topic, script segments, video format
- Produces: `generate_metadata(topic, script_segments, video_format, chapters) -> dict` — same signature, upgraded prompts matching spec §13

- [ ] **Step 1: Write metadata tests**

Create `tests/test_metadata.py`:
```python
def test_fallback_metadata_has_all_platforms():
    from metadata_generator import _fallback_metadata
    meta = _fallback_metadata("Test Topic", "short")
    assert "youtube" in meta
    assert "tiktok" in meta
    assert "instagram" in meta
    assert "facebook" in meta

def test_fallback_metadata_tiktok_has_hashtags():
    from metadata_generator import _fallback_metadata
    meta = _fallback_metadata("Power of Silence", "short")
    assert "hashtags" in meta["tiktok"]
    assert len(meta["tiktok"]["hashtags"]) >= 5

def test_fallback_metadata_youtube_long_has_description():
    from metadata_generator import _fallback_metadata
    meta = _fallback_metadata("Power of Silence", "long")
    assert "description" in meta["youtube"]
    assert len(meta["youtube"]["description"]) > 20
```

- [ ] **Step 2: Rewrite metadata_generator.py Gemini prompt**

Update the prompt to match spec §13 — viral-optimized per platform, personal hooks, natural CTAs, hashtag strategies. Update the fallback to include better default hashtags matching the spec.

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_metadata.py -v`
Expected: All 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add metadata_generator.py tests/test_metadata.py
git commit -m "feat: viral-optimized social media captions per platform"
```

---

### Task 13: Review Dashboard Upgrade

**Files:**
- Modify: `C:\Users\User\luminous-will-web\app\dashboard\page.tsx` (full rewrite)

**Interfaces:**
- Consumes: `/api/queue` endpoint returning `QueueEntry[]` with `video_url`, `thumbnail_url`, `captions`, `script_text` fields
- Produces: Premium review dashboard with video player, thumbnail preview, caption tabs, inline edit, script preview

- [ ] **Step 1: Rewrite dashboard page.tsx**

Full rewrite of `app/dashboard/page.tsx` with:
- Video player (HTML5 `<video>` tag with controls)
- Thumbnail preview image
- Platform caption tabs (TikTok / Instagram / YouTube)
- Inline edit for captions/hashtags
- Expandable script preview
- Large Approve/Reject buttons with confirmation
- Metadata at a glance (topic, format, duration, date, platforms)
- Dark premium styling: #000 bg, #1a1a1a borders, #E8A817 accents
- Responsive layout for mobile review

Key UI components in the rewrite:
- `VideoPlayer` — embedded HTML5 video with poster frame
- `CaptionTabs` — tabbed view for each platform's caption
- `EditableCaption` — textarea that switches between view/edit mode
- `ScriptPreview` — collapsible section showing full script
- `ReviewActions` — large approve/reject buttons

- [ ] **Step 2: Test manually**

Run: `cd C:\Users\User\luminous-will-web && npm run dev`
Open: `http://localhost:3000/dashboard`
Verify: dark theme, responsive layout, all components render

- [ ] **Step 3: Commit**

```bash
cd C:\Users\User\luminous-will-web
git add app/dashboard/page.tsx
git commit -m "feat: premium review dashboard with video player and caption tabs"
```

---

### Task 14: GitHub Actions Cron — Automated Generation

**Files:**
- Create: `C:\Users\User\LuminousWill\.github\workflows\generate.yml`

**Interfaces:**
- Consumes: HF Spaces Gradio API at `https://leoemp-luminous-will.hf.space`
- Produces: Scheduled video generation: shorts daily at 3 AM UTC, long-form Mon/Thu at 2 AM UTC

- [ ] **Step 1: Create workflow file**

Create `.github/workflows/generate.yml`:
```yaml
name: Automated Video Generation

on:
  schedule:
    # Short-form: daily at 3:00 AM UTC
    - cron: '0 3 * * *'
    # Long-form: Monday and Thursday at 2:00 AM UTC
    - cron: '0 2 * * 1,4'
  workflow_dispatch:
    inputs:
      format:
        description: 'Video format (short or long)'
        required: true
        default: 'short'
        type: choice
        options:
          - short
          - long

jobs:
  generate:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Determine format
        id: format
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            echo "format=${{ github.event.inputs.format }}" >> $GITHUB_OUTPUT
          elif [ "${{ github.event.schedule }}" = "0 2 * * 1,4" ]; then
            echo "format=long" >> $GITHUB_OUTPUT
          else
            echo "format=short" >> $GITHUB_OUTPUT
          fi

      - name: Wake HF Space
        run: |
          echo "Waking HF Space..."
          for i in 1 2 3 4 5; do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://leoemp-luminous-will.hf.space/")
            echo "Attempt $i: HTTP $STATUS"
            if [ "$STATUS" = "200" ]; then
              echo "Space is awake!"
              break
            fi
            sleep 15
          done

      - name: Wait for Space to fully load
        run: sleep 30

      - name: Trigger video generation
        run: |
          FORMAT="${{ steps.format.outputs.format }}"
          echo "Triggering $FORMAT generation..."

          # Call the Gradio API predict endpoint
          RESPONSE=$(curl -s -X POST \
            "https://leoemp-luminous-will.hf.space/api/predict" \
            -H "Content-Type: application/json" \
            -d "{\"data\": [\"$FORMAT\", \"\"]}" \
            --max-time 600)

          echo "Response: $RESPONSE"

          # Check for success
          if echo "$RESPONSE" | grep -q "error"; then
            echo "Generation may have failed"
            exit 1
          fi

          echo "Generation triggered successfully"

      - name: Verify generation
        run: |
          echo "Waiting for generation to complete..."
          sleep 60
          # Check queue for new pending_review entry
          echo "Generation workflow complete"
```

- [ ] **Step 2: Commit**

```bash
cd C:\Users\User\LuminousWill
git add .github/workflows/generate.yml
git commit -m "feat: GitHub Actions cron for automated daily video generation"
```

---

## Task Dependency Graph

```
Task 1 (Config + Font + Tests)
├── Task 2 (Color Grading) ─────────────────────┐
├── Task 3 (Caption Animations) ─────────────────┤
├── Task 4 (Audio Mixing) ──────────────────────┤
├── Task 5 (Voiceover Validation) ──────────────┤
├── Task 6 (Ken Burns) ─────────────────────────┤
├── Task 7 (Transitions + 4K) ─────────────────┤── All feed into pipeline
├── Task 8 (Storyblocks Footage) ───────────────┤
├── Task 9 (Storyblocks Music) ─────────────────┤
├── Task 10 (Script Generation) ────────────────┤
├── Task 11 (Thumbnails) ──────────────────────┤
├── Task 12 (Metadata/Captions) ───────────────┘
│
├── Task 13 (Dashboard — independent, web app)
└── Task 14 (GitHub Actions — independent)
```

Tasks 2-12 depend on Task 1 but are largely independent of each other.
Tasks 13-14 are fully independent and can run in parallel with anything.

---

## Spec Coverage Checklist

| Spec Section | Task | Status |
|---|---|---|
| §1 Config & Font Setup | Task 1 | Covered |
| §2 Caption Animations | Task 3 | Covered |
| §3 Ken Burns Effect | Task 6 | Covered |
| §4 Premium Stock Footage | Task 8 | Covered |
| §5 Premium Music | Task 9 | Covered |
| §6 Audio Mixing | Task 4 | Covered |
| §7 Voiceover Validation | Task 5 | Covered |
| §8 Smooth Transitions | Task 7 | Covered |
| §9 Adaptive Color Grading | Task 2 | Covered |
| §10 Script Generation | Task 10 | Covered |
| §11 4K Output Option | Task 7 | Covered |
| §12 Premium Thumbnails | Task 11 | Covered |
| §13 Social Media Captions | Task 12 | Covered |
| §14 Review Dashboard | Task 13 | Covered |
| §15 GitHub Actions Cron | Task 14 | Covered |
