import os
import random
import textwrap
import numpy as np
import config
from PIL import Image, ImageDraw, ImageFont

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

# Category 1: Urban/textured real-world photos
BG_URBAN_QUERIES = [
    "dark concrete wall", "dark texture background", "black wall",
    "dark urban street", "moody architecture", "dark gym",
    "rain dark city", "dark alley", "concrete floor dark",
    "dark brick wall", "industrial dark", "dark wooden surface",
    "foggy dark street", "shadow wall", "dark minimal interior",
    "grunge wall texture", "dark hallway", "night city street",
    "dark staircase", "dark empty room",
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
]

# Category 3: Plain/solid color backgrounds (generated programmatically)
BG_PLAIN_COLORS = [
    {"bg": (245, 240, 232), "text": (25, 25, 25)},       # off-white/cream
    {"bg": (235, 230, 220), "text": (30, 30, 30)},        # warm beige
    {"bg": (224, 224, 224), "text": (20, 20, 20)},         # light grey
    {"bg": (200, 195, 185), "text": (25, 25, 25)},         # warm grey
    {"bg": (30, 30, 30), "text": (255, 255, 255)},         # dark charcoal
    {"bg": (15, 15, 15), "text": (255, 255, 255)},         # near black
    {"bg": (245, 245, 245), "text": (15, 15, 15)},         # clean white
    {"bg": (210, 200, 180), "text": (35, 30, 25)},         # parchment
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
        # Yellow marker highlight behind text — Apollo Method signature style
        # Ref: "If I play, I play to win.", "Pain builds you. Comfort weakens you."
        "font_key": "montserrat",
        "base_font_size": 80,
        "text_color": (0, 0, 0),
        "highlight_color": (255, 234, 0),
        "highlight_padding_x": 18,
        "highlight_padding_y": 10,
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
}


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
    # Creates a solid color background image (no Pexels needed)
    # Returns (image_path, text_color_override)
    """
    color_set = random.choice(BG_PLAIN_COLORS)
    img = Image.new("RGB", (1080, 1920), color_set["bg"])

    # --- Add subtle noise/grain for texture (not flat digital) ---
    img_array = np.array(img, dtype=np.int16)
    noise = np.random.randint(-3, 4, img_array.shape, dtype=np.int16)
    img_array = np.clip(img_array + noise, 0, 255)
    img = Image.fromarray(img_array.astype(np.uint8))

    img_path = os.path.join(config.TEMP_DIR, f"quote_bg_plain_{index}.png")
    img.save(img_path, quality=95)
    return img_path, color_set["text"]


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
    if style.get("split_on_sentences"):
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

        # --- Draw yellow highlight bar behind text ---
        if style.get("highlight_color"):
            pad_x = style.get("highlight_padding_x", 16)
            pad_y = style.get("highlight_padding_y", 8)
            rect = [
                x - pad_x,
                y - pad_y,
                x + lw + pad_x,
                y + lh + pad_y + 4,
            ]
            # --- Clamp highlight to image bounds ---
            rect[0] = max(0, rect[0])
            rect[2] = min(target_w, rect[2])
            draw.rectangle(rect, fill=style["highlight_color"])

        # --- Draw text shadow (skip on plain light backgrounds — looks dirty) ---
        if style.get("shadow") and bg_type != "plain":
            shadow_offset = max(3, font_size // 20)
            for sx in range(1, shadow_offset + 1):
                draw.text((x + sx, y + sx), line, font=font, fill=(0, 0, 0))

        # --- Draw main text ---
        draw.text((x, y), line, font=font, fill=text_color_active)

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
    zoom_map = {
        "plain": ["static", "static", "slow_zoom"],
        "urban": ["slow_zoom", "punch_zoom", "slow_zoom"],
        "epic": ["slow_zoom", "punch_zoom", "slow_zoom", "punch_zoom"],
    }

    zooms = []
    for bg_type in bg_types:
        pool = zoom_map.get(bg_type, ["static"])
        zooms.append(random.choice(pool))

    # --- Guarantee at least 1 punch_zoom and 1 static ---
    if "punch_zoom" not in zooms:
        # --- Put punch on first non-plain slide ---
        for i, bg in enumerate(bg_types):
            if bg != "plain":
                zooms[i] = "punch_zoom"
                break
    if "static" not in zooms and len(zooms) > 2:
        zooms[0] = "static"

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
    print("\n[STEP 2/5] Downloading background images...")
    bg_data = search_background_images(count=len(quotes))

    if not bg_data:
        print("[ERROR] No background images downloaded")
        return None

    # --- Pad if fewer backgrounds than quotes ---
    while len(bg_data) < len(quotes):
        bg_data.append(random.choice(bg_data))

    # --- STEP 3: Render quote images ---
    print("\n[STEP 3/5] Rendering quote images...")
    rendered_images = []
    # --- Use different styles for variety ---
    style_names = list(QUOTE_STYLES.keys())
    for i, quote in enumerate(quotes):
        style = style_names[i % len(style_names)]
        img_path, bg_type, text_color = bg_data[i]
        out_path = os.path.join(config.TEMP_DIR, f"quote_card_{i}.png")
        rendered = render_quote_image(
            quote, img_path, style_name=style, output_path=out_path,
            bg_type=bg_type, text_color_override=text_color,
        )
        rendered_images.append(rendered)

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

    # --- Extract bg_types for zoom assignment ---
    slide_bg_types = [bg_data[i][1] for i in range(len(rendered_images))]
    assemble_quote_reel(rendered_images, beat_path, output_path,
                        duration=duration, bg_types=slide_bg_types)

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
