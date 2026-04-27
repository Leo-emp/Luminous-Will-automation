import numpy as np
import config

# ============================================================
# COLOR GRADING
# Applies dark, cinematic aesthetic to stock footage
# Matches the Luminous Will brand: moody, desaturated, high contrast
#
# CALIBRATED from real video analysis:
#   - Target brightness: 24% (V channel ~61/255)
#   - Target saturation: 28% (mix of B&W and warm tones)
#   - Cool shadow tints, warm highlight tints
#   - High contrast with crushed blacks
#
# Reference videos analyzed:
#   - "The quiet leader vs the loud victim" (brightness 24%, sat 10%)
#   - "High value solitude" (brightness 25%, sat 47%)
# ============================================================


def apply_dark_grade(frame):
    """
    # Applies dark cinematic color grading to a single frame
    # Calibrated to match actual Luminous Will video look
    #
    # Processing chain:
    #   1. Reduce brightness -> dark overall tone
    #   2. Reduce saturation -> moody/desaturated
    #   3. Boost contrast -> punchy darks and lights
    #   4. Crush blacks -> deep shadows (no milky grays)
    #   5. Split toning -> cool shadows + warm highlights
    #
    # Args:
    #   frame: numpy array (H, W, 3) RGB uint8
    #
    # Returns:
    #   graded frame as numpy array (H, W, 3) RGB uint8
    """

    # --- Convert to float for precision ---
    img = frame.astype(np.float64) / 255.0

    # --- Step 1: Reduce brightness ---
    # Target: 24% average brightness (measured from real videos)
    img = img * config.BRIGHTNESS_FACTOR

    # --- Step 2: Desaturate ---
    # Blend between grayscale and original color
    # Using standard luminance weights (ITU-R BT.601)
    gray = np.dot(img[..., :3], [0.299, 0.587, 0.114])
    gray = np.stack([gray] * 3, axis=-1)
    # saturation_factor of 0.45 means 45% of original color kept
    img = gray + config.SATURATION_FACTOR * (img - gray)

    # --- Step 3: Boost contrast ---
    # Use a lower midpoint (0.25) to keep the dark aesthetic
    # while still allowing some highlight detail
    midpoint = 0.25
    img = midpoint + config.CONTRAST_FACTOR * (img - midpoint)

    # --- Step 4: Crush blacks ---
    # Push near-black values to true black for deeper shadows
    # This prevents the "washed out" look on dark footage
    black_crush_threshold = 0.08
    crush_mask = img < black_crush_threshold
    img[crush_mask] = img[crush_mask] * 0.3  # push dark pixels darker

    # --- Step 5: Split toning ---
    # Cool shadows (blue tint) + warm highlights (amber tint)
    # This is a signature look of dark motivation content
    avg_brightness = img.mean(axis=-1, keepdims=True)

    # Shadows: add subtle blue tint (measured from videos)
    shadows_mask = avg_brightness < 0.25
    shadow_tint = np.zeros_like(img)
    shadow_tint[..., 2] = 0.04  # blue channel boost in shadows
    img = img + shadow_tint * shadows_mask

    # Highlights: add subtle warm/amber tint (measured from videos)
    highlights_mask = avg_brightness > 0.5
    highlight_tint = np.zeros_like(img)
    highlight_tint[..., 0] = 0.03  # red channel boost in highlights
    highlight_tint[..., 1] = 0.015  # slight green for amber tone
    img = img + highlight_tint * highlights_mask

    # --- Step 6: Subtle vignette effect ---
    # Darkens the edges of the frame, draws eye to center
    # Common in cinematic dark content
    h, w = img.shape[:2]
    Y, X = np.ogrid[:h, :w]
    # Normalized distance from center (0 at center, 1 at corners)
    center_y, center_x = h / 2, w / 2
    dist = np.sqrt(((X - center_x) / center_x) ** 2 + ((Y - center_y) / center_y) ** 2)
    # Vignette: darken edges gently (multiply by 0.7-1.0)
    vignette = 1.0 - 0.3 * np.clip(dist - 0.5, 0, 1)
    img = img * vignette[..., np.newaxis]

    # --- Clamp values and convert back to uint8 ---
    img = np.clip(img, 0, 1)
    return (img * 255).astype(np.uint8)


def apply_dark_grade_filter(get_frame, t):
    """
    # MoviePy-compatible filter function
    # Use with clip.transform(apply_dark_grade_filter)
    """
    return apply_dark_grade(get_frame(t))
