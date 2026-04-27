import os
from dotenv import load_dotenv

# ============================================================
# CONFIGURATION FILE FOR LUMINOUS WILL VIDEO PIPELINE
# Fill in your API keys in the .env file before running
# ============================================================

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# --- API Keys (set these in .env file) ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# --- ElevenLabs Voice Settings ---
# Voice: Adam - Deep English Story Voice
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam voice ID
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"
VOICE_SETTINGS = {
    "stability": 0.50,           # 50% stability
    "similarity_boost": 0.75,    # 75% similarity boost
    "style": 0.04,               # 4% style
    "use_speaker_boost": True,   # speaker boost enabled
}
VOICE_SPEED = 0.83  # speed 0.83

# --- Video Settings ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_FORMAT = "mp4"

# --- Caption Style ---
# White text with highlighted keyword in gold/amber
CAPTION_FONT_SIZE = 70
CAPTION_COLOR = "white"
CAPTION_HIGHLIGHT_COLOR = "#FFB800"  # gold/amber for emphasis words
CAPTION_FONT = "Arial-Bold"
CAPTION_POSITION = ("center", 0.82)  # 82% from top (near bottom)
CAPTION_STROKE_COLOR = "black"
CAPTION_STROKE_WIDTH = 3

# --- Color Grading (dark aesthetic) ---
BRIGHTNESS_FACTOR = 0.65    # darken footage
SATURATION_FACTOR = 0.55    # desaturate for moody look
CONTRAST_FACTOR = 1.15      # slight contrast boost

# --- Audio Settings ---
VOICEOVER_VOLUME = 1.0      # full volume for voiceover
MUSIC_VOLUME = 0.10         # 10% volume for background music (very low so voice is clear)

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
MIN_CLIP_DURATION = 3  # minimum seconds per visual clip
MAX_CLIP_DURATION = 6  # maximum seconds per visual clip

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
]
