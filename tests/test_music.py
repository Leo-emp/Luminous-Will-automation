# ============================================================
# TESTS FOR music.py
# Covers: mood detection, STORYBLOCKS_MOOD_QUERIES dict,
#         and _epidemic_sound_search placeholder
# ============================================================


def test_dominant_mood_detection():
    # --- Standard case: verify the most-common mood wins ---
    from music import get_dominant_mood
    segments = [
        {"mood": "dark"}, {"mood": "dark"}, {"mood": "intense"},
        {"mood": "dark"}, {"mood": "reflective"},
    ]
    # "dark" appears 3 times — should be the dominant mood
    assert get_dominant_mood(segments) == "dark"


def test_dominant_mood_fallback():
    # --- Edge case: no mood tags at all → should default to "intense" ---
    from music import get_dominant_mood
    # Segments have no "mood" key — get_dominant_mood should return "intense"
    segments = [{"text": "no mood"}, {"text": "also no mood"}]
    assert get_dominant_mood(segments) == "intense"


def test_storyblocks_mood_query_mapping():
    # --- Verify all 4 moods have search queries defined ---
    from music import STORYBLOCKS_MOOD_QUERIES
    # Every mood in the valid set must have a non-empty query string
    for mood in ["dark", "intense", "reflective", "powerful"]:
        assert mood in STORYBLOCKS_MOOD_QUERIES, f"Missing mood key: {mood}"
        assert len(STORYBLOCKS_MOOD_QUERIES[mood]) > 0, f"Empty query for mood: {mood}"


def test_epidemic_sound_placeholder():
    # --- Verify Epidemic Sound returns None (not yet implemented) ---
    from music import _epidemic_sound_search
    # Should always return None since no API key is set and not implemented
    result = _epidemic_sound_search("dark ambient")
    assert result is None
