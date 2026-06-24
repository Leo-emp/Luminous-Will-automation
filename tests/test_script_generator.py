import json
import os

# ============================================================
# TESTS FOR SCRIPT GENERATOR
# Tests history loading, hook validation, motion style heuristics,
# and segment field generation — all without calling Gemini
# ============================================================


def test_generated_history_loads():
    # --- Test that generated_history.json loads correctly ---
    # The file is pre-seeded with 17 videos, so we expect at least 17 entries
    from script_generator import load_generated_history
    history = load_generated_history()
    assert isinstance(history, list)
    assert len(history) >= 17  # pre-seeded with 17 videos


def test_generated_history_has_required_fields():
    # --- Test that every history entry has the 4 required fields ---
    # topic: what the video is about
    # hook: the opening line that grabs attention
    # angle: the specific psychological/philosophical angle
    # date: when this video was generated
    from script_generator import load_generated_history
    history = load_generated_history()
    for entry in history:
        assert "topic" in entry
        assert "hook" in entry
        assert "angle" in entry
        assert "date" in entry


def test_hook_validation_rejects_generic():
    # --- Generic hooks without "you" or emotional triggers should be WEAK ---
    # "Life is about choices" has no personal address or emotional trigger
    # so it should fail our quality check
    from script_generator import _is_strong_hook
    # Generic hook without "you" or emotional trigger → weak
    assert _is_strong_hook("Life is about choices") is False


def test_hook_validation_accepts_personal():
    # --- Personal hooks using "you" or emotional triggers should be STRONG ---
    # "If you're always alone, this is for you" directly addresses the viewer
    # with "you" twice — that's a strong, personal hook
    from script_generator import _is_strong_hook
    # Personal hook with "you" → strong
    assert _is_strong_hook("If you're always alone, this is for you") is True


def test_segment_has_motion_and_transition():
    # --- After running heuristics, every segment must have both fields ---
    # motion_style: how the Ken Burns effect moves (pan, zoom, or static)
    # transition: how we cut to the next clip (crossfade, cut, etc.)
    from script_generator import _build_short_form_heuristics
    segments = [
        {"text": "test", "visual_keywords": "dark lion cinematic", "mood": "dark"},
        {"text": "test2", "visual_keywords": "mountain peak clouds", "mood": "reflective"},
    ]
    enriched = _build_short_form_heuristics(segments)
    for seg in enriched:
        assert "motion_style" in seg
        assert "transition" in seg


def test_motion_style_heuristic():
    # --- The motion style heuristic should correctly classify visual keywords ---
    # landscape/nature/mountain/ocean/clouds → ken_burns_pan (slow sideways drift)
    # action/running/training/fighting → static (footage already has motion)
    # portrait/face/silhouette → ken_burns_zoom (slow push-in for intimacy)
    # anything else → static (safe default)
    from script_generator import _infer_motion_style
    assert _infer_motion_style("mountain peak landscape clouds") == "ken_burns_pan"
    assert _infer_motion_style("man running boxing training") == "static"
    assert _infer_motion_style("chess board silhouette portrait") == "ken_burns_zoom"
    assert _infer_motion_style("random words here") == "static"
