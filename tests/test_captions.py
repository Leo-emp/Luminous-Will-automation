import numpy as np

# ============================================================
# TESTS FOR captions.py — Word-by-Word Caption Reveal
#
# These tests verify the animation timing logic and rendering:
#   - _is_word_visible: visibility state before/during/after animation
#   - _is_word_visible: backward-compat when current_time is None
#   - render_caption_frame: output shape and dtype
#   - _load_font: fallback chain works without Montserrat installed
#
# Run with: python -m pytest tests/test_captions.py -v
# ============================================================


def test_word_visibility_before_start():
    # Word that hasn't started yet should be invisible
    from captions import _is_word_visible
    visible, scale = _is_word_visible(word_start=2.0, word_end=2.5, current_time=1.0)
    assert visible is False


def test_word_visibility_during_animation():
    # Word during its 0.08s animation window should be visible with scale < 1.0
    from captions import _is_word_visible
    visible, scale = _is_word_visible(word_start=2.0, word_end=2.5, current_time=2.03)
    assert visible is True
    assert 0.9 <= scale < 1.0, f"Scale should be animating, got {scale}"


def test_word_visibility_after_settled():
    # Word after animation should be fully visible at scale 1.0
    from captions import _is_word_visible
    visible, scale = _is_word_visible(word_start=2.0, word_end=2.5, current_time=2.5)
    assert visible is True
    assert scale == 1.0


def test_word_visibility_no_current_time():
    # When current_time is None, all words should be visible (backward compat)
    from captions import _is_word_visible
    visible, scale = _is_word_visible(word_start=2.0, word_end=2.5, current_time=None)
    assert visible is True
    assert scale == 1.0


def test_render_caption_frame_returns_rgba():
    # render_caption_frame must return a (H, W, 4) uint8 numpy array
    # Shape is (frame_height, frame_width, 4) — note: H×W not W×H
    from captions import render_caption_frame
    frame = render_caption_frame("test words", None, 1080, 1920)
    assert frame.shape == (1920, 1080, 4)
    assert frame.dtype == np.uint8


def test_font_loading_fallback():
    # _load_font should return a font object even if Montserrat isn't installed
    # The fallback chain: Montserrat → Arial Bold → PIL default
    from captions import _load_font
    font = _load_font(65)
    assert font is not None
