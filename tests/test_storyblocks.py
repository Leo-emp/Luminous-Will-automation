# ============================================================
# TESTS FOR STORYBLOCKS INTEGRATION
# Tests the optional premium footage source
# Storyblocks is only active when API key + secret are configured
# ============================================================


def test_storyblocks_disabled_without_key(monkeypatch):
    # --- When STORYBLOCKS_API_KEY is empty, is_storyblocks_available() must return False ---
    # This ensures the pipeline gracefully skips Storyblocks when no key is set
    import config
    monkeypatch.setattr(config, "STORYBLOCKS_API_KEY", "")
    from storyblocks import is_storyblocks_available
    assert is_storyblocks_available() is False


def test_storyblocks_enabled_with_key(monkeypatch):
    # --- When BOTH key AND secret are set, is_storyblocks_available() must return True ---
    # Both are required: the HMAC signature needs the secret, the API call needs the key
    import config
    monkeypatch.setattr(config, "STORYBLOCKS_API_KEY", "test_key")
    monkeypatch.setattr(config, "STORYBLOCKS_API_SECRET", "test_secret")
    from storyblocks import is_storyblocks_available
    assert is_storyblocks_available() is True


def test_scoring_resolution_bonus():
    # --- 4K video should score higher than HD due to resolution bonus ---
    # Resolution bonus: +1.0 for 4K (>=3840), +0.5 for HD (>=1920)
    from visuals import _score_video_relevance
    # 4K video — same URL so keyword overlap is identical, only resolution differs
    video_4k = {"url": "dark-lion-cinematic", "image": "", "user": {"name": ""}, "width": 3840, "height": 2160}
    video_hd = {"url": "dark-lion-cinematic", "image": "", "user": {"name": ""}, "width": 1920, "height": 1080}
    score_4k = _score_video_relevance(video_4k, "lion power", "dark lion cinematic", source="pexels")
    score_hd = _score_video_relevance(video_hd, "lion power", "dark lion cinematic", source="pexels")
    # 4K must score at least as high as HD (it gets +1.0 vs +0.5)
    assert score_4k >= score_hd


def test_scoring_rejects_below_720p():
    # --- Video below 720p should receive a -3.0 penalty making score very low ---
    # This discourages downloading low-quality footage
    from visuals import _score_video_relevance
    video_low = {"url": "dark-lion", "image": "", "user": {"name": ""}, "width": 480, "height": 360}
    score = _score_video_relevance(video_low, "lion", "dark lion", source="pexels")
    # -3.0 penalty should push score below 1.0 for a simple 1-word query match
    assert score < 1.0
