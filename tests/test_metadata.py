
# ============================================================
# TEST METADATA GENERATOR
# Tests for viral-optimized social media captions per platform
# Covers: all platforms present, TikTok hashtags, YouTube description
# ============================================================

# We test the fallback function directly since it does not require
# any API key — this makes the tests fast and deterministic


def test_fallback_metadata_has_all_platforms():
    # All 4 target platforms must be present in the fallback dict
    # so every downstream publisher always finds its keys
    from metadata_generator import _fallback_metadata
    meta = _fallback_metadata("Test Topic", "short")
    assert "youtube" in meta
    assert "tiktok" in meta
    assert "instagram" in meta
    assert "facebook" in meta


def test_fallback_metadata_tiktok_has_hashtags():
    # TikTok caption must carry a 'hashtags' list with at least 5 items
    # per spec §13: 5-7 trending + niche hashtags required for reach
    from metadata_generator import _fallback_metadata
    meta = _fallback_metadata("Power of Silence", "short")
    assert "hashtags" in meta["tiktok"]
    assert len(meta["tiktok"]["hashtags"]) >= 5


def test_fallback_metadata_youtube_long_has_description():
    # YouTube long-form must have a real description field
    # (not empty) — SEO depends on a minimum word count in description
    from metadata_generator import _fallback_metadata
    meta = _fallback_metadata("Power of Silence", "long")
    assert "description" in meta["youtube"]
    assert len(meta["youtube"]["description"]) > 20
