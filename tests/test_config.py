import os
import config
from config import VideoFormat, get_format_profile, QUALITY_4K

def test_format_profiles_exist():
    # Both format profiles must be defined
    assert VideoFormat.VERTICAL_SHORT in config.FORMAT_PROFILES
    assert VideoFormat.HORIZONTAL_LONG in config.FORMAT_PROFILES

def test_profile_has_all_required_keys():
    # Every profile must have the new premium fields
    required_keys = [
        "width", "height", "fps", "bitrate", "quality",
        "voiceover_boost_db", "music_level_db",
        "ken_burns_enabled", "crossfade_duration",
        "caption_font_size", "caption_position_y",
    ]
    for fmt in VideoFormat:
        profile = get_format_profile(fmt)
        for key in required_keys:
            assert key in profile, f"Missing '{key}' in {fmt.value} profile"

def test_4k_quality_override():
    # 4K mode should override resolution and bitrate
    profile = get_format_profile(VideoFormat.VERTICAL_SHORT, quality="4k")
    assert profile["width"] == 2160
    assert profile["height"] == 3840
    assert profile["bitrate"] == "30000k"
    assert profile["quality"] == "4k"

def test_default_quality_is_1080p():
    # Default quality should remain 1080p
    profile = get_format_profile(VideoFormat.VERTICAL_SHORT)
    assert profile["quality"] == "1080p"
    assert profile["width"] == 1080

def test_db_values_match_spec():
    # dB values must match the approved spec
    for fmt in VideoFormat:
        profile = get_format_profile(fmt)
        assert profile["voiceover_boost_db"] == 1.5
        assert profile["music_level_db"] == -9

def test_font_file_path_configured():
    # Font file path should point to assets/fonts/
    assert "Montserrat-Bold.ttf" in config.CAPTION_FONT_FILE
    assert "assets" in config.CAPTION_FONT_FILE

def test_storyblocks_keys_default_empty():
    # Premium API keys should default to empty (not crash)
    assert isinstance(config.STORYBLOCKS_API_KEY, str)
    assert isinstance(config.EPIDEMIC_SOUND_API_KEY, str)

def test_script_source_is_gemini():
    # Both formats now use gemini for script generation
    for fmt in VideoFormat:
        profile = get_format_profile(fmt)
        assert profile["script_source"] == "gemini"
