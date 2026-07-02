import os
import random
import textwrap
import numpy as np
import config
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from ai_quote_gen import (
    AI_SCENE_STYLES, AI_BG_STYLES, ALL_AI_STYLES,
    render_ai_scene_image, render_ai_bg_with_text,
    render_ai_bg_progressive, apply_post_processing,
    render_dynamic_image, render_dynamic_progressive,
)

# ============================================================
# QUOTE REEL GENERATOR
# Creates viral short-form quote videos inspired by @theapollomethod
#
# FORMAT: Single motivational quote on a dark/urban background image
#   - Bold aesthetic text (6 rotating styles)
#   - Beat-synced zoom effect
#   - Viral audio beats (no voiceover)
#   - 10-20 seconds, high replay value
#
# STYLES (rotated randomly):
#   1. HIGHLIGHT  — clean font + yellow marker behind text
#   2. MINIMALIST — simple sans-serif centered on plain bg
#   3. BOLD_CAPS  — thick heavy font, all caps, in-your-face
#   4. HANDWRITTEN— casual brush/marker feel
#   5. STACKED    — multiple short lines stacked vertically
#   6. EDITORIAL  — serif newspaper-style, sophisticated
#
# PIPELINE:
#   1. Gemini generates punchy 1-2 line quotes
#   2. Pexels fetches dark/urban/texture background images
#   3. Pillow renders text in chosen style
#   4. Librosa detects beat peaks in audio
#   5. MoviePy assembles with beat-synced zoom + audio
# ============================================================


# --- Font file paths ---
FONTS_DIR = os.path.join(config.ASSETS_DIR, "fonts")
FONT_FILES = {
    "bebas": os.path.join(FONTS_DIR, "BebasNeue-Regular.ttf"),
    "oswald": os.path.join(FONTS_DIR, "Oswald-Bold.ttf"),
    "playfair": os.path.join(FONTS_DIR, "PlayfairDisplay-Bold.ttf"),
    "caveat": os.path.join(FONTS_DIR, "Caveat-Bold.ttf"),
    "anton": os.path.join(FONTS_DIR, "Anton-Regular.ttf"),
    "marker": os.path.join(FONTS_DIR, "Permanent_Marker.ttf"),
    "montserrat": os.path.join(FONTS_DIR, "Montserrat-Bold.ttf"),
}

# --- Background categories (matched from @theapollomethod's 3 visual styles) ---

# Category 1: Urban/textured real-world photos + aesthetic dark interiors
BG_URBAN_QUERIES = [
    "dark concrete wall", "dark texture background", "black wall",
    "dark urban street", "moody architecture", "dark gym",
    "rain dark city", "dark alley", "concrete floor dark",
    "dark brick wall", "industrial dark", "dark wooden surface",
    "foggy dark street", "shadow wall", "dark minimal interior",
    "grunge wall texture", "dark hallway", "night city street",
    "dark staircase", "dark empty room",
    # --- Aesthetic/luxury dark (ref: IMG_5111 luxury interior) ---
    "dark luxury interior", "dark modern apartment", "dark aesthetic room",
    "dark coffee shop moody", "dark bookshelf aesthetic", "dark desk setup",
    "dark bathroom luxury", "dark bedroom moody", "dark lounge interior",
    # --- Graffiti-ready surfaces (brick, concrete, textured walls) ---
    "brick wall texture", "old brick wall", "concrete wall graffiti",
    "abandoned wall texture", "urban wall texture", "rough concrete surface",
]

# Category 2: Epic/mythological/warrior imagery (Sisyphus, statues, lions, etc.)
BG_EPIC_QUERIES = [
    "greek statue black and white", "ancient warrior statue",
    "lion portrait black and white", "eagle portrait dark",
    "man pushing boulder", "atlas statue", "roman sculpture dark",
    "mountain peak dramatic", "stormy ocean waves dark",
    "boxer silhouette", "spartan helmet", "knight armor dark",
    "wolf portrait dark", "lone man mountain top",
    "chess king piece dark", "dark throne", "sword dark background",
    "muscular man silhouette", "statue of david", "greek god statue",
    "samurai dark", "gladiator", "phoenix dark art",
    "bull portrait dark", "dark horse running",
    # --- Conceptual/symbolic (ref: IMG_5107 chess mirror) ---
    "chess piece mirror", "hourglass dark", "compass dark background",
    "crown dark background", "broken chain dark", "fire dark background",
]

# Category 3: Book page / paper texture backgrounds (from Pexels)
BG_PAPER_QUERIES = [
    "old paper texture", "book page close up", "vintage paper texture",
    "white paper texture", "parchment texture", "aged paper",
    "notebook page blank", "crumpled paper texture", "paper grain close",
    "concrete wall white texture", "white wall texture rough",
    "plaster wall texture light",
]

# --- Background type distribution (controls variety like Apollo Method) ---
# Apollo uses roughly: 35% plain, 35% urban, 30% epic
BG_TYPE_WEIGHTS = {"plain": 35, "urban": 35, "epic": 30}

# --- Safe zone margins (percentage of image dimensions) ---
# Text never enters these zones — matched from Apollo Method's generous margins
MARGIN_X_RATIO = 0.12   # 12% from left/right edges (130px on 1080w)
MARGIN_Y_RATIO = 0.15   # 15% from top/bottom edges (288px on 1920h)

# --- Quote style definitions ---
# Matched to @theapollomethod's actual styles from their viral posts
QUOTE_STYLES = {
    "highlight": {
        # Yellow-green marker highlight — Apollo Method signature style
        # Ref: "It's going to happen because I'm going to make it happen."
        "font_key": "playfair",
        "base_font_size": 80,
        "text_color": (15, 15, 15),
        "highlight_color": (200, 255, 0),
        "highlight_padding_x": 18,
        "highlight_padding_y": 12,
        "alignment": "left",
        "uppercase": False,
        "line_spacing_ratio": 1.8,
        "split_on_sentences": False,
        "bg_darken": 0.55,
    },
    "minimalist": {
        # Clean simple centered text — "No risk, no story.", "It's you vs you."
        "font_key": "montserrat",
        "base_font_size": 85,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "center",
        "uppercase": False,
        "line_spacing_ratio": 1.6,
        "split_on_sentences": False,
        "shadow": True,
        "bg_darken": 0.50,
    },
    "bold_caps": {
        # Thick heavy ALL CAPS — "WINNING ISN'T FOR EVERYONE.", "MAKE IT HAPPEN."
        "font_key": "anton",
        "base_font_size": 110,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "left",
        "uppercase": True,
        "line_spacing_ratio": 1.2,
        "split_on_sentences": False,
        "shadow": True,
        "bg_darken": 0.50,
    },
    "handwritten": {
        # Casual brush/marker — "Dream big, work hard, stay humble."
        "font_key": "marker",
        "base_font_size": 85,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "center",
        "uppercase": False,
        "line_spacing_ratio": 1.6,
        "split_on_sentences": True,
        "shadow": True,
        "bg_darken": 0.50,
    },
    "stacked": {
        # Each sentence on its own line — "Work hard. Dress good. Eat well."
        "font_key": "oswald",
        "base_font_size": 72,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "left",
        "uppercase": True,
        "line_spacing_ratio": 1.7,
        "split_on_sentences": True,
        "shadow": True,
        "bg_darken": 0.50,
    },
    "editorial": {
        # Serif newspaper-style — "What if it all works out?"
        "font_key": "playfair",
        "base_font_size": 90,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "center",
        "uppercase": False,
        "line_spacing_ratio": 1.5,
        "split_on_sentences": False,
        "shadow": True,
        "bg_darken": 0.55,
    },
    "glow": {
        # Warm backlit 3D text — ref: IMG_5112 "I WILL WIN"
        # Dark letters with golden glow radiating from behind on smooth dark wall
        "font_key": "bebas",
        "base_font_size": 180,
        "text_color": (60, 55, 45),
        "highlight_color": None,
        "alignment": "center",
        "uppercase": True,
        "line_spacing_ratio": 1.6,
        "split_per_word": True,
        "split_on_sentences": False,
        "shadow": False,
        "glow": True,
        "glow_color": (255, 220, 130),
        "glow_radius": 40,
        "glow_passes": 12,
        "force_plain_bg": True,
        "plain_color": (25, 23, 22),
    },
    "crimson": {
        # Deep red serif on cream — ref: IMG_5110 "Do it for your future self."
        # Elegant, feminine, premium magazine feel
        "font_key": "playfair",
        "base_font_size": 85,
        "text_color": (140, 15, 15),
        "highlight_color": None,
        "alignment": "center",
        "uppercase": False,
        "line_spacing_ratio": 1.6,
        "split_on_sentences": False,
        "shadow": False,
        "bg_darken": 0.0,
        "force_plain_bg": True,
        "plain_color": (245, 240, 232),
    },
    "bracket": {
        # Bracketed stencil text — ref: IMG_5108 "[don't wish for it, work for it]"
        # White text inside square bracket frame on dark bg
        "font_key": "montserrat",
        "base_font_size": 70,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "center",
        "uppercase": False,
        "line_spacing_ratio": 1.6,
        "split_on_sentences": False,
        "shadow": True,
        "brackets": True,
        "bg_darken": 0.45,
    },
    "billboard": {
        # Massive impact text — ref: IMG_5114 "YOU ONLY FAIL WHEN YOU STOP TRYING"
        # One word per line, fills the frame, maximum visual weight
        "font_key": "anton",
        "base_font_size": 140,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "left",
        "uppercase": True,
        "line_spacing_ratio": 1.1,
        "split_on_sentences": False,
        "shadow": True,
        "bg_darken": 0.45,
    },
    "moody_serif": {
        # White serif caps on dark moody photos — ref: IMG_5111 "YOUR ONLY LIMIT IS YOUR MIND"
        # Each word on its own line, serif elegance on dark aesthetic backgrounds
        "font_key": "playfair",
        "base_font_size": 100,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "center",
        "uppercase": True,
        "line_spacing_ratio": 1.4,
        "split_on_sentences": True,
        "shadow": True,
        "bg_darken": 0.50,
    },
    "clean_dark": {
        # White sans-serif on pure black — ref: IMG_5109 "Stick to the plan. Not your mood."
        # Minimal, centered, clean, no background image needed
        "font_key": "montserrat",
        "base_font_size": 80,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "center",
        "uppercase": False,
        "line_spacing_ratio": 1.6,
        "split_on_sentences": False,
        "shadow": False,
        "bg_darken": 0.0,
        "force_plain_bg": True,
        "plain_color": (10, 10, 10),
    },
    "graffiti": {
        # Spray paint text on brick/concrete — ref: IMG_5117 "SUCCESS IS THE BEST REVENGE"
        # Raw urban energy, red or white spray paint on real walls
        "font_key": "marker",
        "base_font_size": 100,
        "text_color": (220, 30, 30),
        "highlight_color": None,
        "alignment": "left",
        "uppercase": True,
        "line_spacing_ratio": 1.3,
        "split_on_sentences": False,
        "shadow": False,
        "spray_paint": True,
        "bg_darken": 0.55,
    },
    "strikethrough": {
        # Crossed-out text + replacement — ref: video14 "~~I FAILED~~ I WILL TRY AGAIN"
        # Top line has strikethrough, bottom line is the real message
        "font_key": "anton",
        "base_font_size": 90,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "center",
        "uppercase": True,
        "line_spacing_ratio": 2.0,
        "split_on_sentences": True,
        "shadow": True,
        "strikethrough": True,
        "bg_darken": 0.55,
    },
    # ============================================================
    # NEW STYLES — identified from TikTok quote reel reference images
    # (Drive folder: "TikTok quote reel images", 61 references)
    # ============================================================
    "divider": {
        # Two-part quote split by horizontal rule — ref: IMG_5129 "NO ONE CARES. — WORK HARDER."
        # Also ref: IMG_5133 "DO IT TIRED. — DO IT ANYWAY.", IMG_5155 "SMALL STEPS. BIG RESULTS."
        # Huge condensed caps, horizontal line between the two halves, subway poster aesthetic
        "font_key": "anton",
        "base_font_size": 120,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "left",
        "uppercase": True,
        "line_spacing_ratio": 1.3,
        "split_on_sentences": True,
        "shadow": True,
        "divider_line": True,       # draws a horizontal rule between sentence groups
        "bg_darken": 0.45,
    },
    "gradient_fade": {
        # Gray-to-white text progression — ref: IMG_5143 "PROGRESS OVER COMFORT."
        # Earlier words in muted gray, final keyword in bright white = emphasis
        # Pure black background, massive wide text, left-aligned, lower-third position
        "font_key": "montserrat",
        "base_font_size": 150,
        "text_color": (255, 255, 255),  # base color (used for last line)
        "highlight_color": None,
        "alignment": "left",
        "uppercase": True,
        "line_spacing_ratio": 1.05,
        "split_per_word": True,
        "shadow": False,
        "gradient_text": True,      # each line gets progressively brighter
        "force_plain_bg": True,
        "plain_color": (5, 5, 5),
        "vertical_position": "lower",
    },
    "echo_repeat": {
        # Same phrase repeated with opacity gradient — ref: IMG_5165 "FOCUS ON THE MISSION" x7
        # Center line is full white, lines above/below fade to dark gray
        # Wire-frame/abstract art aesthetic, monospace feel
        "font_key": "montserrat",
        "base_font_size": 36,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "center",
        "uppercase": True,
        "line_spacing_ratio": 1.6,
        "split_on_sentences": False,
        "shadow": False,
        "echo_repeat": True,        # repeats text 7x with fading opacity
        "echo_count": 7,            # number of repetitions
        "force_plain_bg": True,
        "plain_color": (8, 8, 8),
    },
    "poster": {
        # Three-tier hierarchy — ref: IMG_5136 "CONSISTENCY / Do it, Do it tired.../ footnote"
        # Small spaced header keyword at top + large bold body + tiny subtitle at bottom
        # Framed poster on dark background, premium typography
        "font_key": "oswald",
        "base_font_size": 90,
        "text_color": (255, 255, 255),
        "highlight_color": None,
        "alignment": "left",
        "uppercase": False,
        "line_spacing_ratio": 1.3,
        "split_on_sentences": True,
        "shadow": False,
        "poster_layout": True,      # enables 3-tier rendering (header/body/footer)
        "force_plain_bg": True,
        "plain_color": (12, 12, 12),
    },
    "dual_weight": {
        # Large accent keyword + smaller subtitle — ref: IMG_5151 "MINDSET IS EVERYTHING"
        # First 1-2 words massive in gold/accent, rest smaller underneath
        # Dark cinematic background, editorial hierarchy
        "font_key": "bebas",
        "base_font_size": 160,
        "text_color": (220, 195, 120),  # warm gold for the big keyword
        "highlight_color": None,
        "alignment": "center",
        "uppercase": True,
        "line_spacing_ratio": 1.4,
        "split_on_sentences": False,
        "shadow": False,
        "dual_weight": True,        # splits into big keyword + smaller subtitle
        "subtitle_color": (200, 200, 200),  # lighter gray for subtitle
        "subtitle_font_key": "montserrat",
        "subtitle_size_ratio": 0.35,  # subtitle is 35% of main keyword size
        "bg_darken": 0.50,
    },
}

# --- Graffiti color variations (randomly picked per render) ---
GRAFFITI_COLORS = [
    (220, 30, 30),    # red spray paint
    (255, 255, 255),  # white spray paint
    (230, 220, 50),   # yellow spray paint
]


def generate_quotes(topic=None, count=5):
    """
    # Uses Gemini to generate short punchy motivational quotes
    # Returns a list of quote strings
    """
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    # --- Pick a random topic if none given ---
    if not topic:
        topic = random.choice(config.TRENDING_TOPICS)

    prompt = f"""Generate {count} short, punchy motivational quotes about: {topic}

RULES:
- Each quote must be 3-12 words maximum
- They should feel like something you'd see spray-painted on a wall or printed on a sign
- Raw, real, no fluff — like street wisdom
- Mix styles: some imperative ("Do it."), some observational ("Winners move in silence."), some confrontational ("You're not hungry enough.")
- NO quotation marks, NO attribution, NO author names
- NO emojis, NO hashtags
- Each quote on its own line
- Think @theapollomethod / sigma motivation / dark discipline aesthetic

EXAMPLES of the vibe:
- No risk, no story.
- It's you vs you.
- Comfort kills more dreams than failure ever will.
- Make it happen. Shock everyone.
- Pain builds you. Comfort weakens you.
- Brick by brick. Day by day. A win is a win.

Generate {count} quotes now:"""

    response = model.generate_content(prompt)
    # --- Parse quotes from response (one per line, skip empty) ---
    raw_lines = response.text.strip().split("\n")
    quotes = []
    for line in raw_lines:
        # --- Strip numbering, bullets, dashes ---
        cleaned = line.strip().lstrip("0123456789.-) ").strip()
        if cleaned and len(cleaned) > 2:
            quotes.append(cleaned)

    print(f"[QUOTE_REEL] Generated {len(quotes)} quotes for topic: {topic}")
    return quotes[:count], topic


def _pick_bg_type():
    """
    # Randomly picks a background type based on weighted distribution
    # Returns "plain", "urban", or "epic"
    """
    types = list(BG_TYPE_WEIGHTS.keys())
    weights = list(BG_TYPE_WEIGHTS.values())
    return random.choices(types, weights=weights, k=1)[0]


def _create_plain_background(index):
    """
    # Downloads a real paper/book page texture from Pexels
    # Falls back to a generated texture if Pexels fails
    # Returns (image_path, text_color_override)
    """
    queries = random.sample(BG_PAPER_QUERIES, min(3, len(BG_PAPER_QUERIES)))
    for query in queries:
        img_path = _download_pexels_image(query, f"plain_{index}")
        if img_path:
            print(f"[QUOTE_REEL] Background #{index+1}: paper texture")
            return img_path, (15, 15, 15)

    # --- Fallback: generate basic paper texture ---
    base = np.full((1920, 1080, 3), [215, 210, 200], dtype=np.int16)
    noise = np.random.randint(-8, 9, base.shape, dtype=np.int16)
    result = np.clip(base + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(result)
    img_path = os.path.join(config.TEMP_DIR, f"quote_bg_plain_{index}.png")
    img.save(img_path, quality=95)
    return img_path, (15, 15, 15)


def _download_pexels_image(query, index):
    """
    # Downloads a single image from Pexels matching the query
    # Returns image path or None
    """
    import requests

    headers = {"Authorization": config.PEXELS_API_KEY}
    url = "https://api.pexels.com/v1/search"
    params = {
        "query": query,
        "orientation": "portrait",
        "size": "large",
        "per_page": 10,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            return None

        photos = resp.json().get("photos", [])
        if not photos:
            return None

        photo = random.choice(photos)
        img_url = photo["src"]["large2x"]
        img_path = os.path.join(config.TEMP_DIR, f"quote_bg_{index}.jpg")

        img_resp = requests.get(img_url, timeout=30)
        if img_resp.status_code == 200:
            with open(img_path, "wb") as f:
                f.write(img_resp.content)
            print(f"[QUOTE_REEL] Background: {query} -> {photo['photographer']}")
            return img_path
    except Exception as e:
        print(f"[QUOTE_REEL] Pexels error for '{query}': {e}")

    return None


def _fetch_bg(bg_type, index):
    """
    # Fetches a single background of the given type
    # Returns (image_path, bg_type, text_color_override_or_None)
    """
    if bg_type == "plain":
        img_path, text_color = _create_plain_background(index)
        print(f"[QUOTE_REEL] Background #{index+1}: plain solid")
        return (img_path, "plain", text_color)

    elif bg_type == "epic":
        queries = random.sample(BG_EPIC_QUERIES, min(3, len(BG_EPIC_QUERIES)))
        for query in queries:
            img_path = _download_pexels_image(query, index)
            if img_path:
                return (img_path, "epic", None)
        # --- Fallback to plain if epic fails ---
        img_path, text_color = _create_plain_background(index)
        return (img_path, "plain", text_color)

    else:  # urban
        queries = random.sample(BG_URBAN_QUERIES, min(3, len(BG_URBAN_QUERIES)))
        for query in queries:
            img_path = _download_pexels_image(query, index)
            if img_path:
                return (img_path, "urban", None)
        img_path, text_color = _create_plain_background(index)
        return (img_path, "plain", text_color)


def search_background_images(count=5):
    """
    # Gets background images guaranteeing ALL 3 types appear in every video.
    # Minimum 1 plain + 1 urban + 1 epic, remaining slots filled randomly.
    # Order is shuffled so types alternate for maximum visual variety.
    #
    # Returns list of (image_path, bg_type, text_color_override_or_None)
    """
    # --- Guarantee at least 1 of each type ---
    required = ["plain", "urban", "epic"]
    remaining = count - len(required)

    # --- Fill remaining slots with weighted random picks ---
    extra_types = []
    for _ in range(remaining):
        extra_types.append(_pick_bg_type())

    all_types = required + extra_types
    random.shuffle(all_types)

    # --- Fetch each background ---
    results = []
    for i, bg_type in enumerate(all_types):
        results.append(_fetch_bg(bg_type, i))

    return results


def _split_quote_lines(text, style, font, max_text_width):
    """
    # Splits quote text into lines that fit within max_text_width
    # Uses sentence splitting for stacked style, word-wrap for others
    # Dynamically reduces font size if text still doesn't fit
    """
    if style.get("split_per_word"):
        # --- One word per line for maximum impact (glow, billboard) ---
        lines = [w.strip() for w in text.split() if w.strip()]
    elif style.get("split_on_sentences"):
        # --- Split on sentence boundaries (periods, commas for stacked/handwritten) ---
        import re
        raw_parts = re.split(r'(?<=[.!?])\s+', text)
        lines = [p.strip() for p in raw_parts if p.strip()]
        if len(lines) <= 1:
            lines = [s.strip() for s in text.split(",") if s.strip()]
    else:
        lines = textwrap.wrap(text, width=100)

    # --- Verify each line fits within max_text_width, re-wrap if not ---
    final_lines = []
    dummy_img = Image.new("RGB", (10, 10))
    dummy_draw = ImageDraw.Draw(dummy_img)
    for line in lines:
        bbox = dummy_draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_text_width:
            final_lines.append(line)
        else:
            # --- Line too wide, word-wrap it to fit ---
            words = line.split()
            current = ""
            for word in words:
                test = f"{current} {word}".strip()
                bbox = dummy_draw.textbbox((0, 0), test, font=font)
                if bbox[2] - bbox[0] <= max_text_width:
                    current = test
                else:
                    if current:
                        final_lines.append(current)
                    current = word
            if current:
                final_lines.append(current)

    return final_lines


def render_quote_image(quote_text, bg_image_path, style_name=None, output_path=None,
                       bg_type="urban", text_color_override=None):
    """
    # Renders a quote onto a background image using the specified style
    # Returns the path to the rendered image (1080x1920)
    #
    # Matched to @theapollomethod quality standards:
    #   - Safe margins (12% x, 15% y) — text never clips edges
    #   - Dynamic font sizing — short quotes get MASSIVE text
    #   - Sentence-aware line splitting for stacked styles
    #   - Background darkened subtly (texture stays visible)
    #   - Thick yellow highlight bars for highlight style
    """
    # --- Pick random style if not specified ---
    if not style_name:
        style_name = random.choice(list(QUOTE_STYLES.keys()))
    style = QUOTE_STYLES[style_name]

    # --- Load and resize background to 1080x1920 ---
    bg = Image.open(bg_image_path).convert("RGB")
    target_w, target_h = 1080, 1920
    bg_ratio = bg.width / bg.height
    target_ratio = target_w / target_h
    if bg_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * bg_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / bg_ratio)
    bg = bg.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    bg = bg.crop((left, top, left + target_w, top + target_h))

    # --- Force plain color background for styles that need it (crimson, clean_dark) ---
    if style.get("force_plain_bg"):
        plain_color = style.get("plain_color", (10, 10, 10))
        bg = Image.new("RGB", (target_w, target_h), plain_color)
        bg_type = "plain"

    # --- Darken background (skip for plain — they're already the right color) ---
    if bg_type != "plain":
        darken = style.get("bg_darken", 0.55)
        # --- Epic images get slightly less darkening to show the artwork ---
        if bg_type == "epic":
            darken = min(darken + 0.1, 0.65)
        bg_array = np.array(bg, dtype=np.float32)
        bg_array *= darken
        bg = Image.fromarray(bg_array.astype(np.uint8))

    draw = ImageDraw.Draw(bg)

    # --- Override text color for plain backgrounds (dark text on light, white on dark) ---
    if text_color_override:
        text_color_active = text_color_override
        # --- Adjust highlight text color too — black on yellow still works ---
        if style.get("highlight_color"):
            text_color_active = (0, 0, 0)
    else:
        text_color_active = style["text_color"]

    # --- Randomize graffiti spray paint color ---
    if style.get("spray_paint"):
        text_color_active = random.choice(GRAFFITI_COLORS)

    # --- Calculate safe zone ---
    margin_x = int(target_w * MARGIN_X_RATIO)
    margin_y = int(target_h * MARGIN_Y_RATIO)
    max_text_width = target_w - (margin_x * 2)
    max_text_height = target_h - (margin_y * 2)

    # --- Dynamic font sizing: fewer words = bigger text ---
    word_count = len(quote_text.split())
    base_size = style["base_font_size"]
    if word_count <= 5:
        font_size = int(base_size * 1.4)
    elif word_count <= 8:
        font_size = int(base_size * 1.15)
    elif word_count <= 12:
        font_size = base_size
    else:
        font_size = int(base_size * 0.85)

    # --- Load font ---
    font_path = FONT_FILES.get(style["font_key"], FONT_FILES["montserrat"])
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.truetype(FONT_FILES["montserrat"], font_size)

    # --- Prepare text ---
    text = quote_text.upper() if style.get("uppercase") else quote_text

    # --- Split into lines that fit within safe zone ---
    lines = _split_quote_lines(text, style, font, max_text_width)

    # --- Shrink font if text block is too tall for safe zone ---
    while True:
        bbox_test = draw.textbbox((0, 0), "Ay", font=font)
        single_h = bbox_test[3] - bbox_test[1]
        line_spacing = int(single_h * style["line_spacing_ratio"])
        total_h = line_spacing * len(lines)
        if total_h <= max_text_height or font_size <= 40:
            break
        font_size -= 4
        font = ImageFont.truetype(font_path, font_size)
        lines = _split_quote_lines(text, style, font, max_text_width)

    # --- Measure final line dimensions ---
    line_metrics = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        line_metrics.append((lw, lh))

    bbox_ref = draw.textbbox((0, 0), "Ay", font=font)
    ref_h = bbox_ref[3] - bbox_ref[1]
    line_spacing = int(ref_h * style["line_spacing_ratio"])
    total_text_height = line_spacing * len(lines)

    # --- Vertical position: center (default), lower, or upper ---
    vpos = style.get("vertical_position", "center")
    if vpos == "lower":
        start_y = int(target_h * 0.52)
    elif vpos == "upper":
        start_y = int(target_h * 0.15)
    else:
        start_y = (target_h - total_text_height) // 2

    # --- Glow effect: additive light behind text for backlit 3D look ---
    if style.get("glow"):
        glow_color = style.get("glow_color", (220, 180, 100))
        glow_radius = style.get("glow_radius", 25)
        # --- Draw white text on black for light map ---
        light_map = Image.new("RGB", (target_w, target_h), (0, 0, 0))
        light_draw = ImageDraw.Draw(light_map)
        for i, line in enumerate(lines):
            lw, lh = line_metrics[i]
            y = start_y + (i * line_spacing)
            if style["alignment"] == "center":
                x = (target_w - lw) // 2
            elif style["alignment"] == "left":
                x = margin_x
            else:
                x = target_w - lw - margin_x
            x = max(margin_x, min(x, target_w - margin_x - lw))
            # --- Thick text base (multiple offsets) for wider glow ---
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    light_draw.text((x + dx, y + dy), line, font=font,
                                    fill=(255, 255, 255))
        # --- Blur to create soft light spread ---
        light_map = light_map.filter(ImageFilter.GaussianBlur(radius=glow_radius))
        # --- Additive blend: bg + (light_map * glow_color * intensity) ---
        bg_arr = np.array(bg, dtype=np.float32)
        light_arr = np.array(light_map, dtype=np.float32) / 255.0
        glow_intensity = 1.8
        for c in range(3):
            bg_arr[:, :, c] += light_arr[:, :, c] * glow_color[c] * glow_intensity / 255.0 * 255
        bg_arr = np.clip(bg_arr, 0, 255).astype(np.uint8)
        bg = Image.fromarray(bg_arr)
        draw = ImageDraw.Draw(bg)

    # ============================================================
    # SPECIAL RENDERERS — these styles bypass or extend the standard text loop
    # ============================================================

    # --- Echo repeat: same phrase stacked 7x with opacity gradient ---
    # Ref: IMG_5165 "FOCUS ON THE MISSION" repeated, center line bright white
    if style.get("echo_repeat"):
        echo_count = style.get("echo_count", 7)
        # --- Use the full quote as a single line ---
        echo_text = text
        echo_bbox = draw.textbbox((0, 0), echo_text, font=font)
        echo_w = echo_bbox[2] - echo_bbox[0]
        echo_h = echo_bbox[3] - echo_bbox[1]
        echo_spacing = int(echo_h * style["line_spacing_ratio"])
        total_echo_h = echo_spacing * echo_count
        echo_start_y = (target_h - total_echo_h) // 2
        center_idx = echo_count // 2  # middle line = brightest

        for ei in range(echo_count):
            # --- Brightness fades away from center: center=255, edges=40 ---
            dist_from_center = abs(ei - center_idx)
            brightness = max(40, 255 - dist_from_center * 55)
            echo_color = (brightness, brightness, brightness)
            ey = echo_start_y + (ei * echo_spacing)
            ex = (target_w - echo_w) // 2
            ex = max(margin_x, min(ex, target_w - margin_x - echo_w))
            draw.text((ex, ey), echo_text, font=font, fill=echo_color)

        # --- Skip the standard text loop entirely ---
        # (jump straight to brackets/save section below)

    # --- Poster layout: 3-tier hierarchy (header / body / footnote) ---
    # Ref: IMG_5136 "CONSISTENCY / Do it, Do it tired.../ footnote"
    elif style.get("poster_layout"):
        # --- Split into sentences for the body, use first word as header ---
        words = quote_text.split()
        # --- Header = first word (displayed in small letter-spaced caps) ---
        header_text = words[0].upper() if words else text
        # --- Body = full quote (displayed large, sentence-split) ---
        body_text = text
        # --- Footer = small subtitle below (use last sentence or tagline) ---
        sentences = [s.strip() for s in quote_text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        footer_text = sentences[-1].strip() if len(sentences) > 1 else ""

        # --- Header: small spaced caps at top ---
        header_size = max(24, font_size // 4)
        header_font = ImageFont.truetype(font_path, header_size)
        # --- Add letter spacing by inserting spaces between chars ---
        spaced_header = "   ".join(list(header_text))
        hbbox = draw.textbbox((0, 0), spaced_header, font=header_font)
        hw = hbbox[2] - hbbox[0]
        header_x = margin_x
        header_y = margin_y + 40
        header_color = (180, 180, 180)
        draw.text((header_x, header_y), spaced_header, font=header_font, fill=header_color)

        # --- Body: large text below header ---
        body_start_y = header_y + header_size + 60
        for i, line in enumerate(lines):
            lw, lh = line_metrics[i]
            by = body_start_y + (i * line_spacing)
            bx = margin_x
            bx = max(margin_x, min(bx, target_w - margin_x - lw))
            draw.text((bx, by), line, font=font, fill=text_color_active)

        # --- Footer: small text at bottom ---
        if footer_text:
            footer_size = max(20, font_size // 4)
            footer_font = ImageFont.truetype(font_path, footer_size)
            footer_display = footer_text if not style.get("uppercase") else footer_text
            fbbox = draw.textbbox((0, 0), footer_display, font=footer_font)
            fw = fbbox[2] - fbbox[0]
            # --- Small horizontal rule above footer ---
            body_bottom = body_start_y + (len(lines) * line_spacing) + 20
            draw.line([(margin_x, body_bottom), (margin_x + 40, body_bottom)],
                      fill=(120, 120, 120), width=2)
            draw.text((margin_x, body_bottom + 15), footer_display,
                      font=footer_font, fill=(150, 150, 150))

    # --- Dual weight: big keyword + smaller subtitle ---
    # Ref: IMG_5151 "MINDSET IS EVERYTHING" (gold large + gray subtitle)
    elif style.get("dual_weight"):
        words = text.split()
        # --- Split: first 1-2 words = keyword, rest = subtitle ---
        split_at = 1 if len(words) <= 3 else 2
        keyword = " ".join(words[:split_at])
        subtitle = " ".join(words[split_at:])

        # --- Keyword: massive font ---
        kbbox = draw.textbbox((0, 0), keyword, font=font)
        kw = kbbox[2] - kbbox[0]
        kh = kbbox[3] - kbbox[1]

        # --- Subtitle: smaller font ---
        sub_size = max(30, int(font_size * style.get("subtitle_size_ratio", 0.35)))
        sub_font_key = style.get("subtitle_font_key", "montserrat")
        sub_font_path = FONT_FILES.get(sub_font_key, FONT_FILES["montserrat"])
        sub_font = ImageFont.truetype(sub_font_path, sub_size)
        sub_color = style.get("subtitle_color", (200, 200, 200))
        sbbox = draw.textbbox((0, 0), subtitle, font=sub_font)
        sw = sbbox[2] - sbbox[0]
        sh = sbbox[3] - sbbox[1]

        # --- Vertically center the keyword+subtitle block ---
        gap = 30
        total_block_h = kh + gap + sh
        block_start_y = (target_h - total_block_h) // 2

        # --- Draw keyword (centered) ---
        kx = (target_w - kw) // 2
        kx = max(margin_x, min(kx, target_w - margin_x - kw))
        draw.text((kx, block_start_y), keyword, font=font, fill=text_color_active)

        # --- Draw subtitle (centered below keyword) ---
        sx = (target_w - sw) // 2
        sx = max(margin_x, min(sx, target_w - margin_x - sw))
        draw.text((sx, block_start_y + kh + gap), subtitle, font=sub_font, fill=sub_color)

    # --- Standard text loop (for all other styles including divider + gradient_fade) ---
    else:
        for i, line in enumerate(lines):
            lw, lh = line_metrics[i]
            y = start_y + (i * line_spacing)

            # --- Horizontal position (clamped to safe zone) ---
            if style["alignment"] == "center":
                x = (target_w - lw) // 2
            elif style["alignment"] == "left":
                x = margin_x
            else:
                x = target_w - lw - margin_x

            # --- Clamp x so text + width stays inside safe zone ---
            x = max(margin_x, min(x, target_w - margin_x - lw))

            # --- Draw marker highlight behind text (realistic, semi-transparent) ---
            if style.get("highlight_color"):
                pad_x = style.get("highlight_padding_x", 16)
                pad_y = style.get("highlight_padding_y", 12)
                rect_x1 = max(0, x - pad_x)
                rect_y1 = y - pad_y
                rect_x2 = min(target_w, x + lw + pad_x)
                rect_y2 = y + lh + pad_y + 4

                # --- Create semi-transparent highlight overlay (like real marker) ---
                highlight_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
                h_draw = ImageDraw.Draw(highlight_layer)

                # --- Draw main highlight bar with transparency ---
                h_color = style["highlight_color"] + (200,)
                h_draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=h_color)

                # --- Add rough edges (random jitter on top/bottom borders) ---
                for rx in range(rect_x1, rect_x2, 3):
                    jitter_top = random.randint(-2, 3)
                    jitter_bot = random.randint(-2, 3)
                    if jitter_top != 0:
                        edge_color = style["highlight_color"] + (random.randint(80, 150),)
                        h_draw.rectangle([rx, rect_y1 + jitter_top - 2, rx + 3, rect_y1 + 1],
                                         fill=edge_color)
                    if jitter_bot != 0:
                        edge_color = style["highlight_color"] + (random.randint(80, 150),)
                        h_draw.rectangle([rx, rect_y2 - 1, rx + 3, rect_y2 + jitter_bot + 2],
                                         fill=edge_color)

                # --- Composite highlight onto background ---
                bg = Image.alpha_composite(bg.convert("RGBA"), highlight_layer).convert("RGB")
                draw = ImageDraw.Draw(bg)

            # --- Draw text shadow (skip on plain light backgrounds — looks dirty) ---
            if style.get("shadow") and bg_type != "plain":
                shadow_offset = max(3, font_size // 20)
                for sx in range(1, shadow_offset + 1):
                    draw.text((x + sx, y + sx), line, font=font, fill=(0, 0, 0))

            # --- Draw spray paint effect (realistic graffiti on walls) ---
            if style.get("spray_paint"):
                spray_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
                spray_draw = ImageDraw.Draw(spray_layer)
                # --- Draw main text with rough edges via jittered offsets ---
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        alpha = 255 if abs(dx) <= 1 and abs(dy) <= 1 else random.randint(100, 200)
                        spray_draw.text((x + dx, y + dy), line, font=font,
                                        fill=text_color_active + (alpha,))
                # --- Wide overspray cloud around text (big radius, low density) ---
                for cx in range(x - 25, x + lw + 25, 4):
                    for cy in range(y - 20, y + lh + 20, 4):
                        dist_x = 0 if x <= cx <= x + lw else min(abs(cx - x), abs(cx - x - lw))
                        dist_y = 0 if y <= cy <= y + lh else min(abs(cy - y), abs(cy - y - lh))
                        dist = max(dist_x, dist_y)
                        # --- Closer to text = more dots, farther = fewer ---
                        spray_prob = 0.25 if dist < 5 else (0.08 if dist < 15 else 0.03)
                        if random.random() < spray_prob:
                            dot_x = cx + random.randint(-6, 6)
                            dot_y = cy + random.randint(-6, 6)
                            dot_alpha = random.randint(30, 180)
                            dot_size = random.randint(1, 4)
                            spray_draw.ellipse(
                                [dot_x, dot_y, dot_x + dot_size, dot_y + dot_size],
                                fill=text_color_active + (dot_alpha,))
                # --- Paint drips below random letters ---
                if random.random() < 0.6:
                    num_drips = random.randint(1, 3)
                    for _ in range(num_drips):
                        drip_x = x + random.randint(5, max(6, lw - 5))
                        drip_y = y + lh + random.randint(0, 5)
                        drip_len = random.randint(20, 60)
                        drip_width = random.randint(2, 4)
                        for dy_drip in range(drip_len):
                            alpha = max(15, 220 - dy_drip * 4)
                            drip_x_wobble = drip_x + random.randint(-1, 1)
                            spray_draw.rectangle(
                                [drip_x_wobble, drip_y + dy_drip,
                                 drip_x_wobble + drip_width, drip_y + dy_drip + 1],
                                fill=text_color_active + (alpha,))
                bg = Image.alpha_composite(bg.convert("RGBA"), spray_layer).convert("RGB")
                draw = ImageDraw.Draw(bg)

            # --- Gradient fade: each line gets progressively brighter ---
            # Ref: IMG_5143 "PROGRESS OVER COMFORT." (gray→white per line)
            elif style.get("gradient_text"):
                num_lines = len(lines)
                # --- Line 0 = darkest gray, last line = full white ---
                if num_lines > 1:
                    brightness = int(80 + (175 * i / (num_lines - 1)))
                else:
                    brightness = 255
                grad_color = (brightness, brightness, brightness)
                draw.text((x, y), line, font=font, fill=grad_color)

            else:
                # --- Draw main text ---
                draw.text((x, y), line, font=font, fill=text_color_active)

            # --- Strikethrough: draw line through first sentence, keep second clean ---
            if style.get("strikethrough") and i == 0:
                strike_y = y + lh // 2
                strike_color = (180, 40, 40)
                draw.line([(x - 10, strike_y), (x + lw + 10, strike_y)],
                          fill=strike_color, width=max(4, font_size // 18))
                draw.line([(x - 10, strike_y + 2), (x + lw + 10, strike_y + 2)],
                          fill=strike_color, width=max(3, font_size // 22))

            # --- Divider line: horizontal rule between sentence halves ---
            # Ref: IMG_5129 "NO ONE CARES. ——— WORK HARDER."
            if style.get("divider_line") and style.get("split_on_sentences"):
                # --- Draw the divider after the midpoint of the lines ---
                midpoint = len(lines) // 2
                if i == midpoint - 1 and len(lines) >= 2:
                    rule_y = y + lh + (line_spacing - lh) // 2
                    rule_x1 = margin_x
                    rule_x2 = margin_x + min(200, max_text_width // 3)
                    draw.line([(rule_x1, rule_y), (rule_x2, rule_y)],
                              fill=(255, 255, 255), width=3)

    # --- Draw bracket frame around text block if style has brackets ---
    if style.get("brackets"):
        bracket_font_size = int(font_size * 1.8)
        try:
            bracket_font = ImageFont.truetype(FONT_FILES["montserrat"], bracket_font_size)
        except Exception:
            bracket_font = font
        # --- Calculate text block bounds ---
        block_top = start_y - 20
        block_bottom = start_y + (len(lines) * line_spacing) + 20
        max_line_w = max(lw for lw, lh in line_metrics)
        if style["alignment"] == "center":
            block_left = (target_w - max_line_w) // 2 - 40
            block_right = (target_w + max_line_w) // 2 + 40
        else:
            block_left = margin_x - 40
            block_right = margin_x + max_line_w + 40
        # --- Draw square brackets ---
        bracket_color = (255, 255, 255)
        bracket_thickness = 4
        bracket_len = 50
        # --- Top-left bracket [ ---
        draw.line([(block_left, block_top), (block_left + bracket_len, block_top)],
                  fill=bracket_color, width=bracket_thickness)
        draw.line([(block_left, block_top), (block_left, block_bottom)],
                  fill=bracket_color, width=bracket_thickness)
        draw.line([(block_left, block_bottom), (block_left + bracket_len, block_bottom)],
                  fill=bracket_color, width=bracket_thickness)
        # --- Bottom-right bracket ] ---
        draw.line([(block_right - bracket_len, block_top), (block_right, block_top)],
                  fill=bracket_color, width=bracket_thickness)
        draw.line([(block_right, block_top), (block_right, block_bottom)],
                  fill=bracket_color, width=bracket_thickness)
        draw.line([(block_right - bracket_len, block_bottom), (block_right, block_bottom)],
                  fill=bracket_color, width=bracket_thickness)

    # --- Post-processing: grain + vignette to match reference aesthetic ---
    # Pillow-rendered images get lighter grain than AI scenes (they're already clean)
    grain = 8 if bg_type == "plain" else 12
    vignette = 0.25 if bg_type == "plain" else 0.35
    desat = 0.0 if bg_type == "plain" else 0.15
    bg = apply_post_processing(bg, grain_amount=grain,
                               vignette_strength=vignette,
                               desaturate_amount=desat,
                               grade_name="cold_noir")

    # --- Save ---
    if not output_path:
        output_path = os.path.join(config.TEMP_DIR, f"quote_rendered_{random.randint(1000,9999)}.png")
    bg.save(output_path, quality=95)
    print(f"[QUOTE_REEL] Rendered: '{quote_text[:40]}...' style={style_name}")
    return output_path


def render_progressive_frames(quote_text, bg_image_path, style_name=None,
                              output_dir=None, bg_type="urban",
                              text_color_override=None):
    """
    # Renders word-by-word reveal frames for a quote
    # Returns list of image paths: [1 word, 2 words, ..., all words]
    # Used for Apollo Method-style text reveal animation
    """
    if not output_dir:
        output_dir = config.TEMP_DIR
    os.makedirs(output_dir, exist_ok=True)

    words = quote_text.split()
    frame_paths = []
    tag = random.randint(1000, 9999)

    for word_count in range(1, len(words) + 1):
        partial_text = " ".join(words[:word_count])
        out_path = os.path.join(output_dir, f"reveal_{tag}_w{word_count}.png")
        render_quote_image(
            partial_text, bg_image_path, style_name=style_name,
            output_path=out_path, bg_type=bg_type,
            text_color_override=text_color_override,
        )
        frame_paths.append(out_path)

    print(f"[QUOTE_REEL] Progressive frames: {len(frame_paths)} steps for '{quote_text[:30]}...'")
    return frame_paths


def detect_beats(audio_path):
    """
    # Detects beat timestamps in an audio file using librosa
    # Returns list of beat times in seconds
    """
    import librosa

    y, sr = librosa.load(audio_path, sr=22050)
    # --- Get beat frames and convert to seconds ---
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    print(f"[QUOTE_REEL] Detected {len(beat_times)} beats (tempo: {float(tempo):.0f} BPM)")
    return beat_times.tolist()


def _assign_zoom_types(audio_path, segments, beat_times):
    """
    # Selects zoom type per slide based on audio energy at that moment.
    # Analyzes onset strength envelope and maps intensity to zoom:
    #   punch_zoom  — high energy drops (top 25%), snap 1.0→1.08 on beat
    #   slow_zoom   — medium energy (25-55%), smooth 1.0→1.08 over duration
    #   subtle_zoom — low energy (55-80%), smooth 1.0→1.03-1.05
    #   static      — quiet moments (bottom 20%), no movement
    #
    # Different tracks with different beats = different zoom patterns.
    """
    import librosa

    y, sr = librosa.load(audio_path, sr=22050)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    times = librosa.times_like(onset_env, sr=sr)

    # --- Measure average energy per slide segment ---
    energies = []
    for start, end in segments:
        mask = (times >= start) & (times < end)
        if mask.any():
            energies.append(float(onset_env[mask].mean()))
        else:
            energies.append(0.0)

    # --- Normalize to 0-1 range ---
    e_min = min(energies) if energies else 0
    e_max = max(energies) if energies else 1
    e_range = e_max - e_min if e_max > e_min else 1.0
    normed = [(e - e_min) / e_range for e in energies]

    # --- Map energy to zoom type ---
    zooms = []
    for i, energy in enumerate(normed):
        if energy >= 0.75:
            zooms.append("punch_zoom")
        elif energy >= 0.45:
            zooms.append("slow_zoom")
        elif energy >= 0.20:
            zooms.append("subtle_zoom")
        else:
            zooms.append("static")

    # --- Opening hook always gets slow_zoom (sets the tone) ---
    if zooms:
        zooms[0] = "slow_zoom"
    # --- Closing hold: subtle or static (wind down) ---
    if len(zooms) > 1:
        if zooms[-1] == "punch_zoom":
            zooms[-1] = "subtle_zoom"

    print(f"[QUOTE_REEL] Zoom assignment (energy-adaptive):")
    for i, (z, e) in enumerate(zip(zooms, normed)):
        print(f"  Slide {i+1}: {z} (energy: {e:.2f})")

    return zooms


def _map_slides_to_beats(beat_times, num_slides, total_duration):
    """
    # Maps slides to beat boundaries with three-act structure:
    #   Opening (slide 1): ~25% of beats (3-7s hook that lingers)
    #   Middle slides: 1-3 beats each (rapid-fire, beat-synced)
    #   Closing (last slide): ~20% of beats (3-5s CTA hold)
    # Every slide transition lands exactly on a detected beat.
    # Returns list of (start_time, end_time) per slide.
    """
    n_beats = len(beat_times)

    # --- Fallback: not enough beats or only 1 slide ---
    if n_beats < 4 or num_slides <= 1:
        dur = total_duration / max(1, num_slides)
        return [(i * dur, min((i + 1) * dur, total_duration))
                for i in range(num_slides)]

    # --- Three-act beat allocation ---
    open_count = max(3, min(14, round(n_beats * 0.25)))
    close_count = max(3, min(12, round(n_beats * 0.20)))
    middle_total = n_beats - open_count - close_count
    middle_slides = max(0, num_slides - 2)

    # --- Shrink opening/closing if middle doesn't have enough beats ---
    while middle_total < middle_slides and (open_count > 2 or close_count > 2):
        if open_count > close_count:
            open_count -= 1
        else:
            close_count -= 1
        middle_total = n_beats - open_count - close_count

    # --- Only 2 slides: split at midpoint beat ---
    if middle_slides == 0:
        mid = n_beats // 2
        return [(0.0, beat_times[mid]), (beat_times[mid], total_duration)]

    # --- Distribute middle beats evenly, extras to earlier slides ---
    base = middle_total // middle_slides
    extra = middle_total % middle_slides
    per_slide = [base + (1 if i < extra else 0) for i in range(middle_slides)]

    # --- Build segments from beat indices ---
    segments = []
    cursor = min(open_count, n_beats - 1)
    segments.append((0.0, beat_times[cursor]))

    for beats_n in per_slide:
        start_t = beat_times[cursor]
        cursor = min(cursor + max(1, beats_n), n_beats - 1)
        segments.append((start_t, beat_times[cursor]))

    # --- Closing: last beat boundary to end of audio ---
    segments.append((beat_times[cursor], total_duration))

    return segments


def assemble_quote_reel(quote_images, audio_path, output_path,
                        duration=None, bg_types=None):
    """
    # Beat-adaptive video assembler (matched from 6 TikTok reference reels).
    #
    # Slide timing syncs to detected beats with three-act structure:
    #   Opening: first slide holds ~25% of beats (3-7s hook)
    #   Middle: rapid-fire slides, 1-3 beats each (cut on every beat)
    #   Closing: last slide holds ~20% of beats (3-5s CTA)
    #
    # Zoom selected by audio energy per segment (librosa onset_strength):
    #   punch_zoom (high), slow_zoom (medium), subtle_zoom (low), static (quiet)
    # 84% of reference cuts land within 71ms of a beat — we match that.
    """
    from moviepy import (
        ImageClip, AudioFileClip, CompositeVideoClip,
        concatenate_videoclips
    )

    print("[QUOTE_REEL] Assembling beat-synced video...")

    # --- Load audio ---
    audio = AudioFileClip(audio_path)
    if duration:
        audio = audio.subclipped(0, min(duration, audio.duration))
    total_duration = audio.duration

    # --- Detect beats for slide timing ---
    beat_times = detect_beats(audio_path)

    # --- Map slides to beat boundaries (three-act structure) ---
    num_images = len(quote_images)
    segments = _map_slides_to_beats(beat_times, num_images, total_duration)
    zoom_types = _assign_zoom_types(audio_path, segments, beat_times)

    print(f"[QUOTE_REEL] {num_images} slides, {total_duration:.1f}s total, {len(beat_times)} beats detected")
    for i, ((s, e), zt) in enumerate(zip(segments, zoom_types)):
        print(f"  Slide {i+1}: {s:.2f}s-{e:.2f}s ({e-s:.2f}s) {zt}")

    clips = []
    for i, img_entry in enumerate(quote_images):
        start_time, end_time = segments[i]
        clip_duration = max(0.1, end_time - start_time)
        zoom_type = zoom_types[i]

        # --- Check if this is a progressive reveal (list) or static (string) ---
        is_progressive = isinstance(img_entry, list)
        img_path = img_entry[-1] if is_progressive else img_entry

        # --- Build zoom function based on audio energy classification ---
        # --- static: no movement | subtle: 3-5% | slow: ~8% | punch: snap on beat ---
        def make_zoom_func(ztype, dur, seg_start, bt_list):
            if ztype == "static":
                def zoom_func(t):
                    return 1.0
                return zoom_func

            if ztype == "subtle_zoom":
                target = random.uniform(1.03, 1.05)
                def zoom_func(t):
                    return 1.0 + (target - 1.0) * min(t / dur, 1.0)
                return zoom_func

            if ztype == "slow_zoom":
                target = random.uniform(1.06, 1.10)
                def zoom_func(t):
                    return 1.0 + (target - 1.0) * min(t / dur, 1.0)
                return zoom_func

            # --- punch_zoom: snap to target on first beat in segment, then hold ---
            first_beat_offset = 0.0
            for bt in bt_list:
                if bt >= seg_start:
                    first_beat_offset = bt - seg_start
                    break
            target = random.uniform(1.06, 1.10)
            snap_dur = 0.15
            def zoom_func(t):
                # --- Before the beat: static ---
                if t < first_beat_offset:
                    return 1.0
                # --- Snap window: rapid zoom in 0.15s ---
                elapsed = t - first_beat_offset
                if elapsed < snap_dur:
                    return 1.0 + (target - 1.0) * (elapsed / snap_dur)
                # --- After snap: hold at target ---
                return target
            return zoom_func

        zoom_fn = make_zoom_func(zoom_type, clip_duration, start_time, beat_times)

        # --- Build the frame function ---
        img = Image.open(img_path)
        img_w, img_h = img.size

        if is_progressive:
            # --- Word-by-word reveal: switch between pre-rendered frames ---
            def make_progressive_frame_func(frame_paths, dur, w, h, zfn):
                frame_arrays = [np.array(Image.open(p)) for p in frame_paths]
                n = len(frame_arrays)
                # --- Reserve last 30% of duration to hold the final frame ---
                reveal_duration = dur * 0.70
                time_per_word = reveal_duration / n if n > 0 else dur
                def frame_func(t):
                    # --- Pick which word-count frame to show ---
                    if t >= reveal_duration:
                        idx = n - 1
                    else:
                        idx = min(int(t / time_per_word), n - 1)
                    arr = frame_arrays[idx]
                    z = zfn(t)
                    if z <= 1.001:
                        return arr
                    crop_w = int(w / z)
                    crop_h = int(h / z)
                    x1 = (w - crop_w) // 2
                    y1 = (h - crop_h) // 2
                    cropped = arr[y1:y1+crop_h, x1:x1+crop_w]
                    from PIL import Image as PILImage
                    resized = PILImage.fromarray(cropped).resize((w, h), PILImage.LANCZOS)
                    return np.array(resized)
                return frame_func

            frame_fn = make_progressive_frame_func(
                img_entry, clip_duration, img_w, img_h, zoom_fn)
        else:
            # --- Static slide: single image with zoom ---
            def make_frame_func(path, w, h, zfn, is_static):
                img_array = np.array(Image.open(path))
                def frame_func(t):
                    z = zfn(t)
                    if is_static or z <= 1.001:
                        return img_array
                    crop_w = int(w / z)
                    crop_h = int(h / z)
                    x1 = (w - crop_w) // 2
                    y1 = (h - crop_h) // 2
                    cropped = img_array[y1:y1+crop_h, x1:x1+crop_w]
                    from PIL import Image as PILImage
                    frame = PILImage.fromarray(cropped).resize((w, h), PILImage.LANCZOS)
                    return np.array(frame)
                return frame_func

            frame_fn = make_frame_func(img_path, img_w, img_h, zoom_fn,
                                        zoom_type == "static")

        from moviepy import VideoClip
        clip = VideoClip(frame_fn, duration=clip_duration)
        clip = clip.with_fps(30)
        clips.append(clip)

    # --- Concatenate all quote clips ---
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.with_audio(audio)

    # --- Export ---
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        bitrate="12000k",
        logger="bar",
    )

    final_video.close()
    audio.close()
    print(f"[QUOTE_REEL] Video saved: {output_path}")
    return output_path


def run_quote_reel(topic=None, beat_path=None, num_quotes=5, duration=None):
    """
    # Full quote reel pipeline:
    #   1. Generate quotes with Gemini
    #   2. Download background images from Pexels
    #   3. Render quote images (random styles)
    #   4. Pick a beat from assets/music/beats/ or use provided path
    #   5. Assemble beat-synced video
    #
    # Args:
    #   topic: quote theme (None = random trending topic)
    #   beat_path: path to audio file (None = pick from beats folder)
    #   num_quotes: how many quote slides (default 5)
    #   duration: target video length in seconds (None = full audio)
    """
    import time as _time

    start = _time.time()
    print("\n" + "=" * 60)
    print("  LUMINOUS WILL - QUOTE REEL PIPELINE")
    print("=" * 60)

    os.makedirs(config.TEMP_DIR, exist_ok=True)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    # --- STEP 1: Generate quotes ---
    print("\n[STEP 1/5] Generating quotes...")
    quotes, topic = generate_quotes(topic, count=num_quotes)

    if not quotes:
        print("[ERROR] No quotes generated")
        return None

    # --- STEP 2: Download background images ---
    # Extra backgrounds for breathing slides (image-only, no text)
    num_breathing = max(1, len(quotes) // 3)
    total_bgs_needed = len(quotes) + num_breathing
    print(f"\n[STEP 2/5] Downloading background images ({len(quotes)} quote + {num_breathing} breathing)...")
    bg_data = search_background_images(count=total_bgs_needed)

    if not bg_data:
        print("[ERROR] No background images downloaded")
        return None

    # --- Pad if fewer backgrounds than needed ---
    while len(bg_data) < total_bgs_needed:
        bg_data.append(random.choice(bg_data))

    # --- Split backgrounds: quote slides get first N, breathing slides get the rest ---
    quote_bg_data = bg_data[:len(quotes)]
    breathing_bg_data = bg_data[len(quotes):]
    # --- Breathing slides prefer epic imagery (dramatic visuals, no text) ---
    breathing_bg_data.sort(key=lambda x: 0 if x[1] == "epic" else 1)

    # --- STEP 3: Render quote images + breathing slides ---
    print("\n[STEP 3/5] Rendering quote images...")
    rendered_images = []
    slide_types = []

    # ============================================================
    # AUTOMATED STYLE SYSTEM
    #
    # Primary: Gemini dynamically designs unique scenes per quote
    #   → AI provider renders the image (fal.ai / Gemini / Imagen 4)
    #   → Post-processing applies cinematic film look
    #
    # Fallback: Pillow typography styles (when AI is unavailable)
    #   → 19 styles on Pexels backgrounds
    #
    # Mix: ~70% AI-generated, ~30% Pillow for visual variety
    # Word-by-word reveal: 30% chance on any slide
    # ============================================================

    # --- Track used concepts to enforce variety across the batch ---
    used_concepts = []

    # --- Pillow fallback pools ---
    non_plain_styles = [
        "minimalist", "bold_caps", "handwritten", "stacked", "editorial",
        "glow", "bracket", "billboard", "moody_serif", "graffiti", "strikethrough",
        "divider", "dual_weight",
    ]
    plain_styles = ["highlight", "crimson", "clean_dark",
                    "gradient_fade", "echo_repeat", "poster"]
    random.shuffle(non_plain_styles)
    random.shuffle(plain_styles)
    non_plain_idx = 0
    plain_idx = 0

    for i, quote in enumerate(quotes):
        img_path, bg_type, text_color = quote_bg_data[i]

        # --- Decide: AI (70%) or Pillow (30%) for variety ---
        use_ai = (i % 10 < 7)
        # --- Word-by-word reveal: 30% chance on any slide ---
        use_reveal = random.random() < 0.30

        out_path = os.path.join(config.TEMP_DIR, f"quote_card_{i}.png")

        if use_ai:
            print(f"[QUOTE_REEL] Slide {i+1}/{len(quotes)}: AI dynamic")

            if use_reveal:
                # --- AI background + word-by-word reveal ---
                frames, concept = render_dynamic_progressive(
                    quote, config.TEMP_DIR, previous_concepts=used_concepts)
                if frames:
                    rendered_images.append(frames)
                    used_concepts.append(concept)
                    slide_types.append(("quote", bg_type))
                    continue

            # --- Standard AI render (scene or bg, Gemini decides) ---
            rendered, concept = render_dynamic_image(
                quote, out_path, previous_concepts=used_concepts)
            if rendered:
                rendered_images.append(rendered)
                used_concepts.append(concept)
                slide_types.append(("quote", bg_type))
                continue

            # --- AI failed entirely: fall through to Pillow ---
            print(f"[QUOTE_REEL] AI failed for slide {i+1}, falling back to Pillow")

        # --- Pillow fallback ---
        if bg_type == "plain":
            style = plain_styles[plain_idx % len(plain_styles)]
            plain_idx += 1
        else:
            style = non_plain_styles[non_plain_idx % len(non_plain_styles)]
            non_plain_idx += 1

        print(f"[QUOTE_REEL] Slide {i+1}/{len(quotes)}: Pillow / {style}")

        reveal_styles = {"minimalist", "bold_caps", "clean_dark", "moody_serif",
                         "billboard", "editorial", "bracket"}
        if use_reveal and style in reveal_styles:
            frames = render_progressive_frames(
                quote, img_path, style_name=style,
                output_dir=config.TEMP_DIR, bg_type=bg_type,
                text_color_override=text_color,
            )
            rendered_images.append(frames)
        else:
            rendered = render_quote_image(
                quote, img_path, style_name=style, output_path=out_path,
                bg_type=bg_type, text_color_override=text_color,
            )
            rendered_images.append(rendered)
        slide_types.append(("quote", bg_type))

    # --- Create breathing slides (image-only, no text, darkened epic/urban photos) ---
    print(f"[QUOTE_REEL] Creating {num_breathing} breathing slides (image-only)...")
    for i, (img_path, bg_type, _) in enumerate(breathing_bg_data):
        bg = Image.open(img_path).convert("RGB")
        # --- Resize to 1080x1920 ---
        target_w, target_h = 1080, 1920
        bg_ratio = bg.width / bg.height
        target_ratio = target_w / target_h
        if bg_ratio > target_ratio:
            new_h = target_h
            new_w = int(new_h * bg_ratio)
        else:
            new_w = target_w
            new_h = int(new_w / bg_ratio)
        bg = bg.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        bg = bg.crop((left, top, left + target_w, top + target_h))
        # --- Subtle darken for cinematic feel ---
        bg_arr = np.array(bg, dtype=np.float32) * 0.60
        bg = Image.fromarray(bg_arr.astype(np.uint8))
        out_path = os.path.join(config.TEMP_DIR, f"breathing_{i}.png")
        bg.save(out_path, quality=95)
        rendered_images.append(out_path)
        slide_types.append(("breathing", bg_type))
        print(f"[QUOTE_REEL] Breathing slide #{i+1}: {bg_type}")

    # --- Interleave breathing slides between quote slides ---
    # Insert 1 breathing slide every 2-3 quote slides for visual rhythm
    final_images = []
    final_bg_types = []
    quote_slides = [(img, st) for img, st in zip(rendered_images, slide_types) if st[0] == "quote"]
    breathing_slides = [(img, st) for img, st in zip(rendered_images, slide_types) if st[0] == "breathing"]
    breath_idx = 0
    for qi, (qimg, qst) in enumerate(quote_slides):
        final_images.append(qimg)
        final_bg_types.append(qst[1])
        # --- Insert a breathing slide every 2-3 quotes (not after last) ---
        if breath_idx < len(breathing_slides) and qi > 0 and qi % 2 == 0 and qi < len(quote_slides) - 1:
            bimg, bst = breathing_slides[breath_idx]
            final_images.append(bimg)
            final_bg_types.append(bst[1])
            breath_idx += 1

    rendered_images = final_images

    # --- Create branded CTA end card (Apollo Method always ends with one) ---
    print("[QUOTE_REEL] Creating branded CTA end card...")
    cta_img = Image.new("RGB", (1080, 1920), (8, 8, 8))
    cta_draw = ImageDraw.Draw(cta_img)
    # --- Load fonts for CTA ---
    try:
        cta_font_big = ImageFont.truetype(FONT_FILES["bebas"], 72)
        cta_font_small = ImageFont.truetype(FONT_FILES["montserrat"], 36)
    except Exception:
        cta_font_big = ImageFont.truetype(FONT_FILES["montserrat"], 72)
        cta_font_small = ImageFont.truetype(FONT_FILES["montserrat"], 36)
    # --- Draw "LUMINOUS WILL" brand name ---
    brand_text = "LUMINOUS WILL"
    brand_bbox = cta_draw.textbbox((0, 0), brand_text, font=cta_font_big)
    brand_w = brand_bbox[2] - brand_bbox[0]
    cta_draw.text(((1080 - brand_w) // 2, 820), brand_text,
                  font=cta_font_big, fill=(255, 255, 255))
    # --- Draw tagline ---
    tagline = "Follow for daily motivation"
    tag_bbox = cta_draw.textbbox((0, 0), tagline, font=cta_font_small)
    tag_w = tag_bbox[2] - tag_bbox[0]
    cta_draw.text(((1080 - tag_w) // 2, 920), tagline,
                  font=cta_font_small, fill=(160, 160, 160))
    # --- Add logo if exists ---
    if os.path.exists(config.LOGO_PATH):
        try:
            logo = Image.open(config.LOGO_PATH).convert("RGBA")
            logo_size = 120
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
            logo_x = (1080 - logo_size) // 2
            cta_img.paste(logo, (logo_x, 680), logo)
        except Exception:
            pass
    cta_path = os.path.join(config.TEMP_DIR, "cta_end_card.png")
    cta_img.save(cta_path, quality=95)
    rendered_images.append(cta_path)
    final_bg_types.append("plain")

    # --- STEP 4: Select audio beat ---
    print("\n[STEP 4/5] Selecting audio beat...")
    if not beat_path:
        # --- Look for beats in assets/music/beats/ or assets/music/ ---
        beats_dir = os.path.join(config.ASSETS_DIR, "music", "beats")
        if not os.path.exists(beats_dir):
            beats_dir = config.MUSIC_DIR

        beat_files = [f for f in os.listdir(beats_dir)
                      if f.endswith((".mp3", ".wav", ".m4a"))]
        if beat_files:
            beat_path = os.path.join(beats_dir, random.choice(beat_files))
            print(f"[QUOTE_REEL] Using beat: {os.path.basename(beat_path)}")
        else:
            print("[ERROR] No beat files found in assets/music/ or assets/music/beats/")
            print("[HINT] Add .mp3 beat files to assets/music/beats/")
            return None

    # --- STEP 5: Assemble video ---
    print("\n[STEP 5/5] Assembling beat-synced video...")
    safe_topic = topic.replace(" ", "_").replace("'", "")[:50]
    timestamp = _time.strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(config.OUTPUT_DIR, f"reel_{safe_topic}_{timestamp}.mp4")

    # --- Use interleaved bg_types (includes breathing slides) ---
    assemble_quote_reel(rendered_images, beat_path, output_path,
                        duration=duration, bg_types=final_bg_types)

    # --- Upload to cloud if configured ---
    from blob_storage import upload_pipeline_output
    from metadata_generator import generate_reel_metadata
    metadata = generate_reel_metadata(topic, quotes)

    from moviepy import AudioFileClip
    audio_clip = AudioFileClip(beat_path)
    vid_duration = min(duration, audio_clip.duration) if duration else audio_clip.duration
    audio_clip.close()

    queue_entry = upload_pipeline_output(
        topic=topic,
        video_format="reel",
        output_path=output_path,
        thumbnail_path=None,
        metadata=metadata,
        script_text=" | ".join(quotes),
        duration=vid_duration,
    )

    elapsed = _time.time() - start
    print("\n" + "=" * 60)
    print(f"  QUOTE REEL COMPLETE!")
    print(f"  Topic: {topic}")
    print(f"  Quotes: {len(quotes)}")
    print(f"  Output: {output_path}")
    if queue_entry:
        print(f"  Queue ID: {queue_entry['id']}")
    print(f"  Time: {elapsed:.0f} seconds")
    print("=" * 60 + "\n")

    return output_path, quotes


# --- Quick test ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Luminous Will Quote Reel Generator")
    parser.add_argument("topic", nargs="?", default=None, help="Quote theme")
    parser.add_argument("--beat", default=None, help="Path to audio beat file")
    parser.add_argument("--quotes", type=int, default=5, help="Number of quote slides")
    parser.add_argument("--duration", type=int, default=None, help="Target duration in seconds")
    args = parser.parse_args()

    run_quote_reel(
        topic=args.topic,
        beat_path=args.beat,
        num_quotes=args.quotes,
        duration=args.duration,
    )
