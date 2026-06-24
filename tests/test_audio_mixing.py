import math

# ============================================================
# TEST: dB-to-linear conversion helper
# These tests verify the _db_to_linear function used in
# mix_audio() to set constant volume levels for music
# and voiceover without any RMS-based ducking logic.
# ============================================================


def test_db_to_linear_positive():
    # +1.5 dB should be ~1.19x (voiceover clarity boost)
    # Formula: 10^(1.5/20) = 10^0.075 ≈ 1.189
    from video_assembler import _db_to_linear
    gain = _db_to_linear(1.5)
    assert abs(gain - 1.189) < 0.01, f"Expected ~1.189, got {gain}"


def test_db_to_linear_negative():
    # -9 dB should be ~0.355x (music sits quietly behind voice)
    # Formula: 10^(-9/20) = 10^(-0.45) ≈ 0.355
    from video_assembler import _db_to_linear
    gain = _db_to_linear(-9)
    assert abs(gain - 0.355) < 0.01, f"Expected ~0.355, got {gain}"


def test_db_to_linear_zero():
    # 0 dB should be exactly 1.0x (unity gain — no change)
    # Formula: 10^(0/20) = 10^0 = 1.0
    from video_assembler import _db_to_linear
    gain = _db_to_linear(0)
    assert gain == 1.0, f"Expected 1.0, got {gain}"
