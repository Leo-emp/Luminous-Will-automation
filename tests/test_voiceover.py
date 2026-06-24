# ============================================================
# TESTS FOR voiceover.py — Voiceover Generation & Cleanup
#
# These tests verify the pure-function logic:
#   - clean_script_text: ellipsis, em dashes, double spaces, smart quotes
#   - _find_long_pauses: detects gaps above threshold, ignores short ones
#   - _recalculate_timestamps: shifts word times correctly after trimming
#
# NOTE: _validate_audio and _trim_long_pauses use MoviePy with real
#       audio files, so they are NOT unit-tested here.
#
# Run with: python -m pytest tests/test_voiceover.py -v
# ============================================================


def test_clean_script_text_ellipsis():
    # Ellipsis (...) should be replaced with a period to avoid weird TTS pauses
    from voiceover import clean_script_text
    assert clean_script_text("Wait... Think again...") == "Wait. Think again."


def test_clean_script_text_em_dash():
    # Em dash (—) and double hyphen (--) should become commas for smooth TTS delivery
    from voiceover import clean_script_text
    assert clean_script_text("Power—real power") == "Power, real power"
    assert clean_script_text("Power -- real power") == "Power, real power"


def test_clean_script_text_double_spaces():
    # Double spaces or multiple spaces should be collapsed to single spaces
    from voiceover import clean_script_text
    assert "  " not in clean_script_text("too  many   spaces")


def test_clean_script_text_smart_quotes():
    # Smart/curly quotes should be replaced with standard ASCII quotes
    from voiceover import clean_script_text
    result = clean_script_text("“Hello” ‘world’")
    assert "“" not in result  # left double quote gone
    assert "”" not in result  # right double quote gone
    assert '"' in result or "'" in result  # at least one ASCII quote present


def test_find_long_pauses_detects_gap():
    # A 2.0s gap between words should be detected with threshold=1.5
    from voiceover import _find_long_pauses
    timestamps = [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 2.5, "end": 3.0},  # 2.0s gap (> 1.5s threshold)
    ]
    pauses = _find_long_pauses(timestamps, threshold=1.5)
    assert len(pauses) == 1
    assert pauses[0]["gap_start"] == 0.5
    assert pauses[0]["gap_end"] == 2.5


def test_find_long_pauses_ignores_short():
    # A 0.5s gap should NOT be detected with threshold=1.5
    from voiceover import _find_long_pauses
    timestamps = [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 1.0, "end": 1.5},  # 0.5s gap (under threshold)
    ]
    pauses = _find_long_pauses(timestamps, threshold=1.5)
    assert len(pauses) == 0


def test_recalculate_timestamps_after_trim():
    # Words BEFORE a trim point stay at original time
    # Words AFTER a trim point get shifted earlier by the removed amount
    from voiceover import _recalculate_timestamps
    timestamps = [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 3.0, "end": 3.5},
    ]
    # Trimmed 1.2s from the pause at position 0.5-3.0
    trims = [{"position": 0.5, "removed": 1.2}]
    new_ts = _recalculate_timestamps(timestamps, trims)
    # "Hello" is before the trim → unchanged
    assert new_ts[0]["start"] == 0.0
    # "world" is after the trim → shifted 1.2s earlier
    assert abs(new_ts[1]["start"] - 1.8) < 0.01
    assert abs(new_ts[1]["end"] - 2.3) < 0.01
