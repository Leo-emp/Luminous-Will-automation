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

# Vercel Blob: cloud storage for generated videos, thumbnails, and queue
# Set this to enable cloud upload after video generation
BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()

# --- Video Format System ---
# Each format has its own resolution, bitrate, caption style, and search orientation
class VideoFormat(Enum):
    VERTICAL_SHORT = "short"    # 9:16, 60-90s
    HORIZONTAL_LONG = "long"    # 16:9, 8-12 min
    QUOTE_REEL = "reel"         # 9:16, 10-20s, text on image + beats, no voiceover

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
        "voiceover_boost_db": 3.0,           # +3 dB boost — phone-optimized, voice cuts through
        "music_level_db": -11,               # -11 dB — audible but never overpowers voice on phone
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
# Measured from actual Luminous Will videos:
# Caption center sits at 83.2% from top (between 80.1% and 86.3%)
# White text with gold/amber highlight, bold sans-serif, thin black stroke
CAPTION_FONT_SIZE = 65       # measured from real videos
CAPTION_COLOR = "white"
CAPTION_HIGHLIGHT_COLOR = "#E8A817"  # warm amber (matched from video frames)
CAPTION_FONT = "Arial-Bold"
CAPTION_POSITION = ("center", 0.83)  # 83% from top (measured: 83.2%)
CAPTION_STROKE_COLOR = "black"
CAPTION_STROKE_WIDTH = 2     # thinner stroke for cleaner look (matched from videos)

# --- Font paths ---
# Montserrat Bold for premium captions and thumbnails
# Falls back to Arial Bold if not found
CAPTION_FONT_FILE = os.path.join(os.path.dirname(__file__), "assets", "fonts", "Montserrat-Bold.ttf")

# --- Color Grading (dark aesthetic) ---
# Measured from actual videos:
#   Avg brightness: 24% (V channel ~61/255) -> very dark
#   Avg saturation: 28% (mix of B&W scenes + warm wildlife)
#   High contrast with cool shadows and warm highlights
BRIGHTNESS_FACTOR = 0.55    # darken footage (measured: 24% target brightness)
SATURATION_FACTOR = 0.45    # desaturate for moody look (measured: 28% target)
CONTRAST_FACTOR = 1.20      # stronger contrast (measured from videos)

# --- Audio Settings (legacy — new code uses dB values from profiles) ---
VOICEOVER_VOLUME = 1.0      # full volume for voiceover (always dominant, crystal clear)
MUSIC_VOLUME = 0.32         # 32% volume - intense motivational feel, voice still dominant
                            # voice is ~3x louder so it stays crystal clear
                            # music hits hard for instant motivation energy

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# --- Logo Outro ---
LOGO_DURATION = 3  # seconds to show logo at end

# --- Clip Settings ---
# Measured from actual videos: avg 7.2s, median 5.4s, range 1.8-23.8s
MIN_CLIP_DURATION = 2.5  # minimum seconds per visual clip
MAX_CLIP_DURATION = 10   # maximum seconds per visual clip

# --- Pexels Search Settings ---
PEXELS_ORIENTATION = "portrait"  # 9:16 vertical footage
PEXELS_SIZE = "large"            # high quality footage
PEXELS_PER_PAGE = 10             # results per search query

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
