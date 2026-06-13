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
        best_frame = np.zeros((THUMB_HEIGHT, THUMB_WIDTH, 3), dtype=np.uint8)

    # --- Resize to thumbnail dimensions ---
    img = Image.fromarray(best_frame)
    img = img.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)

    # --- Add dark gradient bar at bottom ---
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
