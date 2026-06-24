# ============================================================
# TESTS FOR CONTEXT-AWARE TRANSITION HEURISTIC
# ============================================================
# Tests the _get_transition_type helper in video_assembler.py
#
# The heuristic decides whether clips transition with a smooth
# crossfade (blended overlap) or a hard cut (instant switch):
#
#   Priority order:
#     1. Explicit "transition" field on the current segment
#     2. First segment (no previous) → crossfade for clean open
#     3. Mood changes between segments → crossfade (emotional shift)
#     4. Same mood continues → hard cut (maintains momentum)
# ============================================================


def test_transition_heuristic_mood_change():
    """
    # When two adjacent segments have DIFFERENT moods,
    # the transition should be "crossfade" — the mood shift
    # deserves a smooth visual blend to signal the change.
    """
    from video_assembler import _get_transition_type

    # Segment A: dark/heavy mood
    seg_a = {"mood": "dark", "transition": None}
    # Segment B: lighter, reflective mood — a clear tonal shift
    seg_b = {"mood": "reflective", "transition": None}

    # A mood change → expect a crossfade between the two clips
    assert _get_transition_type(seg_a, seg_b) == "crossfade"


def test_transition_heuristic_same_mood():
    """
    # When two adjacent segments share the SAME mood,
    # the transition should be a "cut" — keeping the same energy
    # flowing without an interrupting visual blend.
    """
    from video_assembler import _get_transition_type

    # Both segments have identical mood → same energy maintained
    seg_a = {"mood": "intense", "transition": None}
    seg_b = {"mood": "intense", "transition": None}

    # Same mood → hard cut keeps the intensity going
    assert _get_transition_type(seg_a, seg_b) == "cut"


def test_transition_explicit_override():
    """
    # An explicit "transition" field on the current segment
    # overrides the mood-based heuristic entirely.
    # Even when moods match, an explicit "crossfade" wins.
    """
    from video_assembler import _get_transition_type

    # Same mood (would normally → cut) but segment B explicitly requests crossfade
    seg_a = {"mood": "intense", "transition": None}
    seg_b = {"mood": "intense", "transition": "crossfade"}

    # Explicit override wins → crossfade, despite same mood
    assert _get_transition_type(seg_a, seg_b) == "crossfade"


def test_first_segment_crossfade():
    """
    # The very first clip (no previous segment) should always
    # start with a crossfade — this creates a clean, professional
    # fade-in at the beginning of the video rather than a hard cut
    # from black.
    """
    from video_assembler import _get_transition_type

    # Pass None as the previous segment to signal "this is the first clip"
    assert _get_transition_type(None, {"mood": "dark"}) == "crossfade"
