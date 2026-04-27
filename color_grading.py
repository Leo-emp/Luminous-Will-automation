import numpy as np
import config

# ============================================================
# COLOR GRADING
# Applies dark, cinematic aesthetic to stock footage
# Matches the Luminous Will brand: moody, desaturated, high contrast
# ============================================================


def apply_dark_grade(frame):
    """
    # Applies dark cinematic color grading to a single frame
    # - Reduces brightness (darker overall)
    # - Reduces saturation (moody/desaturated)
    # - Boosts contrast slightly
    # - Adds subtle cool-warm split toning
    #
    # Args:
    #   frame: numpy array (H, W, 3) RGB uint8
    #
    # Returns:
    #   graded frame as numpy array (H, W, 3) RGB uint8
    """

    # --- Convert to float for processing ---
    img = frame.astype(np.float64) / 255.0

    # --- Step 1: Reduce brightness ---
    img = img * config.BRIGHTNESS_FACTOR

    # --- Step 2: Desaturate ---
    # Convert to grayscale weights, then blend
    gray = np.dot(img[..., :3], [0.299, 0.587, 0.114])
    gray = np.stack([gray] * 3, axis=-1)
    img = gray + config.SATURATION_FACTOR * (img - gray)

    # --- Step 3: Boost contrast ---
    midpoint = 0.3  # slightly lower midpoint for dark aesthetic
    img = midpoint + config.CONTRAST_FACTOR * (img - midpoint)

    # --- Step 4: Subtle split toning ---
    # Cool shadows (slightly blue), warm highlights (slightly amber)
    shadows_mask = img.mean(axis=-1, keepdims=True) < 0.3
    highlights_mask = img.mean(axis=-1, keepdims=True) > 0.6

    # Add tiny blue tint to shadows
    shadow_tint = np.zeros_like(img)
    shadow_tint[..., 2] = 0.03  # blue channel
    img = img + shadow_tint * shadows_mask

    # Add tiny warm tint to highlights
    highlight_tint = np.zeros_like(img)
    highlight_tint[..., 0] = 0.02  # red channel
    highlight_tint[..., 1] = 0.01  # green channel
    img = img + highlight_tint * highlights_mask

    # --- Clamp and convert back to uint8 ---
    img = np.clip(img, 0, 1)
    return (img * 255).astype(np.uint8)


def apply_dark_grade_filter(get_frame, t):
    """
    # MoviePy-compatible filter function
    # Use with clip.transform(apply_dark_grade_filter)
    """
    return apply_dark_grade(get_frame(t))
