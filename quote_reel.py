import os
import random
import textwrap
import numpy as np
import config
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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

    # --- Vertically center the text block ---
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

    # --- Save ---
    if not output_path:
        output_path = os.path.join(config.TEMP_DIR, f"quote_rendered_{random.randint(1000,9999)}.png")
    bg.save(output_path, quality=95)
    print(f"[QUOTE_REEL] Rendered: '{quote_text[:40]}...' style={style_name}")
    return output_path


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


def _assign_zoom_types(bg_types):
    """
    # Assigns a zoom effect to each slide based on its background type
    # Returns list of zoom type strings
    #
    # Rules (matched from viral quote reel patterns):
    #   - plain backgrounds: mostly "static" (clean, no distraction)
    #   - epic backgrounds: "slow_zoom" or "punch_zoom" (show off the art)
    #   - urban backgrounds: "slow_zoom" or "punch_zoom" (add energy)
    #   - At least 1 slide must have punch_zoom for impact
    #   - At least 1 slide must be static for contrast
    """
    # --- Apollo Method finding: NEVER truly static. Always slow zoom. ---
    zoom_map = {
        "plain": ["slow_zoom", "slow_zoom", "slow_zoom"],
        "urban": ["slow_zoom", "punch_zoom", "slow_zoom"],
        "epic": ["slow_zoom", "punch_zoom", "slow_zoom", "punch_zoom"],
    }

    zooms = []
    for bg_type in bg_types:
        pool = zoom_map.get(bg_type, ["slow_zoom"])
        zooms.append(random.choice(pool))

    # --- Guarantee at least 1 punch_zoom for impact ---
    if "punch_zoom" not in zooms:
        for i, bg in enumerate(bg_types):
            if bg != "plain":
                zooms[i] = "punch_zoom"
                break

    return zooms


def assemble_quote_reel(quote_images, audio_path, output_path,
                        duration=None, bg_types=None):
    """
    # Assembles quote images + audio into a video with 3 zoom effects:
    #
    #   static     — no zoom, clean and still (plain backgrounds)
    #   slow_zoom  — gentle 1.0→1.12 zoom over the slide duration
    #   punch_zoom — fast 1.0→1.15 snap zoom on first beat, holds
    #
    # Args:
    #   quote_images: list of rendered quote image paths
    #   audio_path: path to the beat/music audio file
    #   output_path: where to save the final .mp4
    #   duration: target duration in seconds (defaults to audio length)
    #   bg_types: list of background types per slide (for zoom assignment)
    """
    from moviepy import (
        ImageClip, AudioFileClip, CompositeVideoClip,
        concatenate_videoclips
    )

    print("[QUOTE_REEL] Assembling video with zoom effects...")

    # --- Load audio ---
    audio = AudioFileClip(audio_path)
    if duration:
        audio = audio.subclipped(0, min(duration, audio.duration))
    total_duration = audio.duration

    # --- Detect beats for punch zoom sync ---
    beat_times = detect_beats(audio_path)

    # --- Assign zoom type per slide ---
    if not bg_types:
        bg_types = ["urban"] * len(quote_images)
    zoom_types = _assign_zoom_types(bg_types)

    # --- Calculate time per image ---
    num_images = len(quote_images)
    time_per_image = total_duration / num_images

    print(f"[QUOTE_REEL] {num_images} slides, {time_per_image:.1f}s each, {total_duration:.1f}s total")
    for i, (zt, bt) in enumerate(zip(zoom_types, bg_types)):
        print(f"  Slide {i+1}: {bt} bg, {zt} zoom")

    clips = []
    for i, img_path in enumerate(quote_images):
        start_time = i * time_per_image
        end_time = min((i + 1) * time_per_image, total_duration)
        clip_duration = end_time - start_time
        zoom_type = zoom_types[i]

        # --- Find the first beat in this slide's window (for punch zoom) ---
        first_beat = None
        for b in beat_times:
            if start_time <= b < end_time:
                first_beat = b - start_time
                break

        # --- Build zoom function based on type ---
        def make_zoom_func(ztype, dur, beat_t):
            def zoom_func(t):
                if ztype == "static":
                    return 1.0

                elif ztype == "slow_zoom":
                    # --- Smooth zoom from 1.0 to 1.12 over full duration ---
                    return 1.0 + 0.12 * (t / dur)

                elif ztype == "punch_zoom":
                    # --- Snap zoom on first beat, then hold ---
                    if beat_t is not None:
                        dt = t - beat_t
                        if dt < 0:
                            return 1.0
                        elif dt < 0.15:
                            # --- Fast snap in (0 to 0.15 over 0.15s) ---
                            return 1.0 + 0.15 * (dt / 0.15)
                        else:
                            return 1.15
                    else:
                        # --- No beat found, do snap at start ---
                        if t < 0.15:
                            return 1.0 + 0.15 * (t / 0.15)
                        return 1.15

                return 1.0
            return zoom_func

        zoom_fn = make_zoom_func(zoom_type, clip_duration, first_beat)

        # --- Build the frame function ---
        img = Image.open(img_path)
        img_w, img_h = img.size

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

    # --- Pick text style based on background type ---
    # Plain = highlight, crimson, or clean_dark
    # Urban/Epic = rotate through the visual styles
    non_plain_styles = [
        "minimalist", "bold_caps", "handwritten", "stacked", "editorial",
        "glow", "bracket", "billboard", "moody_serif", "graffiti", "strikethrough",
    ]
    plain_styles = ["highlight", "crimson", "clean_dark"]
    # --- Shuffle style order for variety across videos ---
    random.shuffle(non_plain_styles)
    random.shuffle(plain_styles)
    non_plain_idx = 0
    plain_idx = 0
    last_style = None

    for i, quote in enumerate(quotes):
        img_path, bg_type, text_color = quote_bg_data[i]
        if bg_type == "plain":
            style = plain_styles[plain_idx % len(plain_styles)]
            plain_idx += 1
        else:
            style = non_plain_styles[non_plain_idx % len(non_plain_styles)]
            non_plain_idx += 1
        # --- Prevent same style back-to-back ---
        if style == last_style:
            if bg_type == "plain":
                plain_idx += 1
                style = plain_styles[plain_idx % len(plain_styles)]
            else:
                non_plain_idx += 1
                style = non_plain_styles[non_plain_idx % len(non_plain_styles)]
        last_style = style

        out_path = os.path.join(config.TEMP_DIR, f"quote_card_{i}.png")
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
    from metadata_generator import generate_metadata
    metadata = generate_metadata(topic, [], "reel")

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

    return output_path


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
