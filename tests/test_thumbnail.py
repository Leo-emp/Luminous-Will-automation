import numpy as np

# ============================================================
# TESTS FOR PREMIUM THUMBNAIL GENERATOR
# Tests the frame scoring logic in isolation (no video needed)
# Covers: contrast preference, darkness penalty, sharpness scoring
# ============================================================


def test_frame_scoring_prefers_contrast():
    # High contrast frames should score higher than flat uniform frames
    # This ensures we pick visually interesting frames for thumbnails
    from thumbnail import _score_frame

    # High contrast: top half bright (200), bottom half dark (20)
    high_contrast = np.zeros((100, 100, 3), dtype=np.uint8)
    high_contrast[:50, :] = 200   # top half bright
    high_contrast[50:, :] = 20    # bottom half dark

    # Flat frame: every pixel the same (boring, low contrast)
    flat = np.full((100, 100, 3), 100, dtype=np.uint8)

    # High contrast frame must score strictly higher
    assert _score_frame(high_contrast) > _score_frame(flat)


def test_frame_scoring_penalizes_too_dark():
    # Very dark frames (near black) should score lower than medium brightness
    # Ensures we don't pick unusable near-black frames for thumbnails
    from thumbnail import _score_frame

    # Very dark: near black (value 10 out of 255)
    very_dark = np.full((100, 100, 3), 10, dtype=np.uint8)

    # Medium brightness: mid-gray (value 80 out of 255)
    medium = np.full((100, 100, 3), 80, dtype=np.uint8)

    # Medium brightness frame must score higher than very dark frame
    assert _score_frame(medium) > _score_frame(very_dark)


def test_frame_scoring_includes_sharpness():
    # Frames with sharp edges should score higher than blurry uniform frames
    # This rewards frames with clear subjects/motion (more visually interesting)
    from thumbnail import _score_frame

    # Sharp frame: black background with a crisp white square in the middle
    # The hard edge creates strong gradient signal = high sharpness
    sharp = np.zeros((100, 100, 3), dtype=np.uint8)
    sharp[40:60, 40:60] = 255   # sharp white square on black background

    # Blurry/uniform frame: mid-gray, no edges at all
    blurry = np.full((100, 100, 3), 128, dtype=np.uint8)

    # Sharp frame must score higher due to sharpness component
    assert _score_frame(sharp) > _score_frame(blurry)
