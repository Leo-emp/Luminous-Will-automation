import numpy as np
import pytest

# ============================================================
# TESTS FOR Ken Burns Effect — video_assembler.py
#
# Tests the two new helper functions:
#   - _get_ken_burns_params(motion_style, duration) -> dict|None
#   - _apply_ken_burns(clip, params, target_w, target_h) -> VideoClip
#
# Ken Burns is a per-clip motion effect (zoom, pan, zoom-out)
# controlled by the script segment's `motion_style` field.
# The global toggle `profile["ken_burns_enabled"]` must also be True.
#
# Run with: python -m pytest tests/test_ken_burns.py -v
# ============================================================


# -----------------------------------------------------------
# PARAMS TESTS — these just test the pure parameter logic,
# no MoviePy clips required
# -----------------------------------------------------------

def test_ken_burns_zoom_params():
    # ken_burns_zoom: slow zoom IN from 1.0x to 1.12x, no horizontal drift
    # This is the most common style — subtle push-in creates tension
    from video_assembler import _get_ken_burns_params
    params = _get_ken_burns_params("ken_burns_zoom", 5.0)
    # Must return a dict, not None
    assert params is not None, "ken_burns_zoom should return a params dict"
    # Scale starts at native size
    assert params["start_scale"] == 1.0
    # Scale ends 12% larger — enough to see motion without distortion
    assert params["end_scale"] == 1.12
    # No horizontal drift for pure zoom
    assert params["pan_x"] == 0.0


def test_ken_burns_pan_params():
    # ken_burns_pan: horizontal drift with no zoom change
    # Creates a slow slide across the frame — good for wide landscape shots
    from video_assembler import _get_ken_burns_params
    params = _get_ken_burns_params("ken_burns_pan", 5.0)
    assert params is not None, "ken_burns_pan should return a params dict"
    # 5% horizontal drift — subtle but visible
    assert params["pan_x"] == 0.05
    # Scale is constant (no zoom on a pure pan)
    assert params["start_scale"] == 1.0


def test_ken_burns_zoom_out_params():
    # slow_zoom_out: pull-back from 1.12x to 1.0x (reverse zoom)
    # Creates a reveal / "zoom-out" effect — good for opening shots
    from video_assembler import _get_ken_burns_params
    params = _get_ken_burns_params("slow_zoom_out", 5.0)
    assert params is not None, "slow_zoom_out should return a params dict"
    # Starts zoomed in
    assert params["start_scale"] == 1.12
    # Ends at native scale (the pull-back)
    assert params["end_scale"] == 1.0


def test_static_returns_none():
    # "static" motion style means no motion effect at all
    # Returning None is the signal to skip Ken Burns processing
    from video_assembler import _get_ken_burns_params
    params = _get_ken_burns_params("static", 5.0)
    assert params is None, "static style should return None (no motion)"


def test_default_is_static():
    # If motion_style is absent (None), default to static — no motion
    # Segments without a motion_style key should be handled safely
    from video_assembler import _get_ken_burns_params
    params = _get_ken_burns_params(None, 5.0)
    assert params is None, "None motion_style should default to static (None)"
