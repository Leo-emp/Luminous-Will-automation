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

# --- Color Grading (dark aesthetic) ---
# Measured from actual videos:
#   Avg brightness: 24% (V channel ~61/255) -> very dark
#   Avg saturation: 28% (mix of B&W scenes + warm wildlife)
#   High contrast with cool shadows and warm highlights
BRIGHTNESS_FACTOR = 0.55    # darken footage (measured: 24% target brightness)
SATURATION_FACTOR = 0.45    # desaturate for moody look (measured: 28% target)
CONTRAST_FACTOR = 1.20      # stronger contrast (measured from videos)

# --- Audio Settings ---
VOICEOVER_VOLUME = 1.0      # full volume for voiceover (always dominant, crystal clear)
MUSIC_VOLUME = 0.15         # 15% volume - loud enough to feel encouraging/motivational
                            # but voice is ~7x louder so it's always crystal clear
                            # Increase to 0.20 if you want more energy
                            # Decrease to 0.10 if music feels too strong

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
]
