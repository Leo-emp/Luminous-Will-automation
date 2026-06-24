import numpy as np

# ============================================================
# TESTS FOR color_grading.py — Premium Color Grading
#
# These tests verify the film-quality cinematic grading logic:
#   - S-curve math (boundary values, contrast direction)
#   - Adaptive intensity (dark vs bright source frames)
#   - Full grade pipeline (darkens, stays in range, blue preservation)
#   - create_grader factory returns a callable
#
# Run with: python -m pytest tests/test_color_grading.py -v
# ============================================================


def _make_frame(brightness=128, shape=(100, 100, 3)):
    # Helper: creates a solid-color test frame
    # All pixels set to the same brightness value across R, G, B
    return np.full(shape, brightness, dtype=np.uint8)


def test_s_curve_produces_valid_output():
    # S-curve should map 0→0, 0.5→~0.5, 1→1
    # This verifies the math anchors at both ends and the midpoint
    from color_grading import _s_curve
    assert abs(_s_curve(0.0) - 0.0) < 0.01
    assert abs(_s_curve(1.0) - 1.0) < 0.01
    # Midpoint should be close to 0.5 (sine-based S-curve is symmetric)
    assert abs(_s_curve(0.5) - 0.5) < 0.1


def test_s_curve_increases_contrast():
    # S-curve should push darks darker and lights lighter
    # This is the defining property of an S-curve — it ADDS contrast
    from color_grading import _s_curve
    assert _s_curve(0.25) < 0.25  # dark values get darker
    assert _s_curve(0.75) > 0.75  # light values get lighter


def test_adaptive_intensity_dark_source():
    # Already-dark frame (avg brightness < 30%) should get light touch
    # Prevents detail-crushing when source footage is already dark
    from color_grading import _get_adaptive_intensity
    dark_frame = _make_frame(brightness=50)  # ~20% brightness
    intensity = _get_adaptive_intensity(dark_frame)
    assert intensity < 1.0, "Dark frames should get reduced grade intensity"


def test_adaptive_intensity_bright_source():
    # Bright frame (avg brightness > 60%) should get aggressive grade
    # Pulls bright stock footage into the dark brand range
    from color_grading import _get_adaptive_intensity
    bright_frame = _make_frame(brightness=200)  # ~78% brightness
    intensity = _get_adaptive_intensity(bright_frame)
    assert intensity > 1.0, "Bright frames should get extra grade intensity"


def test_graded_frame_is_darker():
    # Graded frame should be darker than input (on average)
    # Core requirement of the Luminous Will dark aesthetic
    from color_grading import apply_dark_grade
    frame = _make_frame(brightness=150)
    graded = apply_dark_grade(frame)
    assert graded.mean() < frame.mean()


def test_graded_frame_valid_range():
    # Output must be valid uint8 (0-255, no overflow)
    # Float processing can produce values outside 0-1 if not clamped
    from color_grading import apply_dark_grade
    frame = _make_frame(brightness=200)
    graded = apply_dark_grade(frame)
    assert graded.dtype == np.uint8
    assert graded.min() >= 0
    assert graded.max() <= 255


def test_create_grader_returns_callable():
    # create_grader() must return a function (used by video_assembler.py)
    # This is a contract test — signature must stay stable
    from color_grading import create_grader
    profile = {"brightness_factor": 0.55, "saturation_factor": 0.45}
    grader = create_grader(profile)
    assert callable(grader)


def test_selective_saturation_preserves_blues():
    # Create a blue-ish frame — blues should be preserved more than greens
    # Brand color is cool/blue shadow tones, so blue must stay dominant
    from color_grading import apply_dark_grade
    blue_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    blue_frame[:, :, 2] = 180  # strong blue channel
    blue_frame[:, :, 0] = 40   # low red
    blue_frame[:, :, 1] = 40   # low green
    graded = apply_dark_grade(blue_frame)
    # Blue channel should still be the dominant channel after grading
    assert graded[:, :, 2].mean() > graded[:, :, 0].mean()
    assert graded[:, :, 2].mean() > graded[:, :, 1].mean()
