import math
import numpy as np
import config

# ============================================================
# PREMIUM COLOR GRADING
# Applies cinematic dark aesthetic to stock footage
# Upgraded from mechanical linear transforms to film-quality:
#   - S-curve contrast (smooth, cinematic)
#   - Lift-Gamma-Gain model (industry standard)
#   - Selective saturation (preserve blues/golds, mute greens/reds)
#   - Adaptive intensity (reads source brightness, adjusts strength)
#   - Smooth shadow rolloff (deep blacks with retained detail)
#
# Every clip should look naturally shot on a cinema camera in
# dark moody conditions — not like stock footage with a filter
# ============================================================


def _s_curve(x, strength=1.0):
    """
    # S-curve contrast function (models film response)
    # Maps 0-1 input to 0-1 output with boosted contrast
    # strength controls how pronounced the S-curve is
    # At strength=1.0: shadows pushed ~15% darker, highlights ~15% brighter
    #
    # Formula: blend between linear (x) and sine-shaped curve
    #   sine curve: 0.5 + 0.5 * sin((x - 0.5) * pi)
    #   This naturally anchors at 0→0, 0.5→0.5, 1→1
    #   Then blend: x + strength * (curved - x)
    #
    # Args:
    #   x: float in [0, 1]
    #   strength: float, how strong the S-curve effect is (default 1.0)
    # Returns:
    #   float in [0, 1]
    """
    # --- Sine-based S-curve: remaps [0,1] to [0,1] smoothly ---
    # sin((-pi/2)) = -1  → 0.5 + 0.5*(-1) = 0.0  (x=0)
    # sin(0)       = 0   → 0.5 + 0.5*(0)  = 0.5  (x=0.5)
    # sin(pi/2)    = 1   → 0.5 + 0.5*(1)  = 1.0  (x=1)
    curved = 0.5 + 0.5 * math.sin((x - 0.5) * math.pi)

    # --- Blend between linear and S-curved based on strength ---
    # At strength=0: pure linear (no change)
    # At strength=1: full S-curve effect
    return x + strength * (curved - x)


def _s_curve_array(arr, strength=1.0):
    """
    # Vectorized S-curve for numpy arrays
    # Same math as _s_curve() but operates on full (H, W) or (H, W, C) arrays
    # Uses np.sin for fast GPU-friendly computation
    #
    # Args:
    #   arr: numpy float32 array, values in [0, 1]
    #   strength: float, how strong the S-curve effect is (default 1.0)
    # Returns:
    #   numpy float32 array, same shape as input, values in [0, 1]
    """
    # --- Vectorized sine S-curve — same formula as _s_curve() ---
    curved = 0.5 + 0.5 * np.sin((arr - 0.5) * np.pi)

    # --- Blend: linear + strength * (S-curved - linear) ---
    return arr + np.float32(strength) * (curved - arr)


def _get_adaptive_intensity(frame):
    """
    # Reads the source frame brightness and returns a grade intensity multiplier
    # The goal: all output clips land in the ~20-30% brightness target range
    #
    # Already dark clips (< 30% avg): get a lighter grade (0.8x)
    #   → prevents detail-crushing in already-dark footage
    # Medium clips (30–60% avg): get full grade (1.0x)
    #   → standard cinematic treatment
    # Bright clips (> 60% avg): get aggressive grade (1.2x)
    #   → pulls bright stock footage down into brand range
    #
    # Args:
    #   frame: numpy uint8 array (H, W, 3)
    # Returns:
    #   float multiplier (0.8, 1.0, or 1.2)
    """
    # --- Convert frame to float and measure average brightness ---
    # Average across all 3 channels to get luminance estimate
    gray = np.mean(frame.astype(np.float32), axis=2)
    avg_brightness = np.mean(gray) / 255.0  # normalize to 0-1 range

    if avg_brightness < 0.30:
        # --- Already dark: light touch to avoid crushing shadow details ---
        return 0.8
    elif avg_brightness > 0.60:
        # --- Bright source: needs aggressive darkening to hit brand target ---
        return 1.2
    else:
        # --- Medium brightness: standard full grade ---
        return 1.0


def apply_dark_grade(frame):
    """
    # Applies premium dark cinematic grading to a single frame
    # Standalone function — uses default config values
    # For format-specific grading, use create_grader() instead
    #
    # Processing chain:
    #   1. Adaptive intensity measurement (reads source brightness)
    #   2. Lift-Gamma-Gain (shadows/mids/highlights control)
    #   3. Selective saturation (preserve blues/golds, mute greens/reds)
    #   4. S-curve contrast (film-look cinematic punch)
    #   5. Smooth shadow rolloff (deep blacks, retained detail)
    #   6. Split toning (cool shadows + warm highlights)
    #   7. Subtle vignette (draw focus to center)
    #
    # Args:
    #   frame: numpy array (H, W, 3) RGB uint8
    # Returns:
    #   graded frame as numpy array (H, W, 3) RGB uint8
    """
    # --- Delegate to create_grader with default config values ---
    grader = create_grader({
        "brightness_factor": config.BRIGHTNESS_FACTOR,
        "saturation_factor": config.SATURATION_FACTOR,
    })
    return grader(frame)


def apply_dark_grade_filter(get_frame, t):
    """
    # MoviePy-compatible filter function
    # Use with clip.transform(apply_dark_grade_filter)
    #
    # Args:
    #   get_frame: callable, takes time t → returns frame
    #   t: float, time in seconds
    # Returns:
    #   graded frame as numpy array (H, W, 3) RGB uint8
    """
    return apply_dark_grade(get_frame(t))


def create_grader(profile):
    """
    # Returns a grading function calibrated to the format profile settings
    # The returned function takes a uint8 frame and returns a uint8 frame
    # Used by video_assembler.py: clip.image_transform(grader)
    #
    # The grader captures brightness_factor and saturation_factor from the
    # format profile, so each video format (short/long) gets its own
    # calibrated grade — different profiles produce different looks.
    #
    # Args:
    #   profile: dict with optional keys:
    #     - brightness_factor: float (default: config.BRIGHTNESS_FACTOR)
    #     - saturation_factor: float (default: config.SATURATION_FACTOR)
    # Returns:
    #   Callable[[np.ndarray], np.ndarray] — frame → graded frame
    """
    # --- Extract profile settings with config fallbacks ---
    brightness = profile.get("brightness_factor", config.BRIGHTNESS_FACTOR)
    saturation = profile.get("saturation_factor", config.SATURATION_FACTOR)

    def grade_frame(frame):
        """
        # Inner function — captures brightness/saturation from profile above
        # This is the hot path: called once per frame, must be fast
        #
        # Full cinematic grading pipeline:
        #   Step 0: Measure source brightness → adaptive intensity multiplier
        #   Step 1: Lift-Gamma-Gain (brightness darkening with intensity scaling)
        #   Step 2: Selective saturation (per-channel sat factors)
        #   Step 3: S-curve contrast (sine-based film curve)
        #   Step 4: Smooth shadow rolloff (compress sub-10% values gently)
        #   Step 5: Split toning (cool shadow tint + warm highlight tint)
        #   Step 6: Vignette (edge darkening to direct focus)
        """
        # --- Convert to float32 for processing (half the memory of float64) ---
        img = frame.astype(np.float32) / 255.0

        # ----------------------------------------------------------------
        # Step 0: Adaptive intensity
        # Read source brightness to determine how hard to grade
        # ----------------------------------------------------------------
        intensity = _get_adaptive_intensity(frame)

        # ----------------------------------------------------------------
        # Step 1: Lift-Gamma-Gain darkening
        # Scale the whole image down by brightness_factor * intensity
        # Brighter source footage gets multiplied by a larger effective
        # brightness factor to bring it down into the brand range
        # ----------------------------------------------------------------
        # Effective brightness = profile brightness × adaptive intensity
        effective_brightness = brightness * intensity
        img *= np.float32(effective_brightness)

        # ----------------------------------------------------------------
        # Step 2: Selective saturation
        # Blend each channel toward luminance separately
        # Preserve blues (cool brand shadows), mute greens/reds
        # ----------------------------------------------------------------
        # --- Compute luminance (standard ITU-R BT.601 weights) ---
        lum = (np.float32(0.299) * img[:, :, 0]
             + np.float32(0.587) * img[:, :, 1]
             + np.float32(0.114) * img[:, :, 2])

        # --- Per-channel saturation multipliers ---
        # sat_r: mute reds (distracting in dark motivational content)
        # sat_g: mute greens harder (most visually distracting color)
        # sat_b: preserve blues — matches brand cool shadow aesthetic
        sat_r = saturation * 0.7   # 70% of base sat for reds
        sat_g = saturation * 0.6   # 60% of base sat for greens (most muted)
        sat_b = saturation * 1.2   # 120% of base sat for blues (preserved)

        # --- Apply per-channel blend: lum + sat * (channel - lum) ---
        # sat=0 → pure grayscale (lum)
        # sat=1 → original color
        # sat>1 → boosted color (used for blues)
        img[:, :, 0] = lum + np.float32(sat_r) * (img[:, :, 0] - lum)
        img[:, :, 1] = lum + np.float32(sat_g) * (img[:, :, 1] - lum)
        img[:, :, 2] = lum + np.float32(sat_b) * (img[:, :, 2] - lum)

        # --- Preserve gold/amber tones (brand color range) ---
        # Gold/warm tones live in the red-green overlap zone: R > G > B
        # The per-channel multipliers above (sat_r=0.7, sat_g=0.6) mute golds
        # because both their channels get reduced relative to each other.
        # We detect warm pixels and apply a small +0.15 saturation boost back
        # only to the R and G channels of those pixels, restoring the golden hue.
        # Condition: R > G > B AND R > 0.15 (avoids boosting near-black pixels)
        lum_arr = lum  # keep lum alive; we need it for the gold boost below
        warm_mask = (
            (img[:, :, 0] > img[:, :, 1]) &   # R > G (warm hue direction)
            (img[:, :, 1] > img[:, :, 2]) &   # G > B (not a neutral/cool tone)
            (img[:, :, 0] > np.float32(0.15))  # R bright enough to be visible gold
        )
        gold_boost = np.float32(0.15)          # small re-saturation amount for warmth
        # Re-apply saturation for R and G on warm pixels using boosted factors
        img[:, :, 0][warm_mask] = lum_arr[warm_mask] + np.float32(sat_r + gold_boost) * (img[:, :, 0][warm_mask] - lum_arr[warm_mask])
        img[:, :, 1][warm_mask] = lum_arr[warm_mask] + np.float32(sat_g + gold_boost) * (img[:, :, 1][warm_mask] - lum_arr[warm_mask])
        del lum_arr  # free memory (frames are large)

        # ----------------------------------------------------------------
        # Step 3: S-curve contrast
        # Film-quality contrast: darks go darker, lights go lighter
        # Strength is modulated by intensity so dark clips don't over-contrast
        #
        # config.CONTRAST_FACTOR is a multiplier around 1.0 (e.g. 1.20 = +20% contrast)
        # Mapping: (CONTRAST_FACTOR - 1.0) * 3.0 converts it to a [0, 1] S-curve strength
        #   CONTRAST_FACTOR=1.00 → s_base=0.00 (no contrast effect)
        #   CONTRAST_FACTOR=1.20 → s_base=0.60 (standard cinematic punch)
        #   CONTRAST_FACTOR=1.33 → s_base=1.00 (maximum S-curve)
        # Then multiplied by adaptive intensity:
        #   s_base × 0.8 = gentler for already-dark source
        #   s_base × 1.0 = standard for medium source
        #   s_base × 1.2 = more aggressive for bright source
        # ----------------------------------------------------------------
        s_base = (config.CONTRAST_FACTOR - 1.0) * 3.0   # map config scale → S-curve strength
        s_strength = s_base * intensity                   # scale by adaptive intensity
        img = _s_curve_array(img, strength=s_strength)

        # ----------------------------------------------------------------
        # Step 4: Smooth shadow rolloff
        # Instead of a hard binary mask (old: img[mask] *= 0.5 where img < 0.10),
        # use a continuous linear ramp so the transition is gradual:
        #   shadow_weight = clip(pixel / 0.10, 0, 1)
        #   result = pixel * (0.5 + 0.5 * shadow_weight)
        #
        # Behaviour:
        #   pixel = 0.00 → weight=0.0 → multiplier=0.50 (50% compression at pure black)
        #   pixel = 0.05 → weight=0.5 → multiplier=0.75 (half-way compressed)
        #   pixel = 0.10 → weight=1.0 → multiplier=1.00 (no compression at threshold)
        #   pixel > 0.10 → weight=1.0 → multiplier=1.00 (unaffected above threshold)
        # This smoothly rolls off into deep blacks without a visible crush edge
        # ----------------------------------------------------------------
        shadow_weight = np.clip(img / np.float32(0.10), 0.0, 1.0)
        img = img * (np.float32(0.5) + np.float32(0.5) * shadow_weight)

        # ----------------------------------------------------------------
        # Step 5: Split toning
        # Separate treatment for shadows vs highlights
        # Shadows: push blue channel slightly → cool, moody dark tones
        # Highlights: push red + green slightly → warm amber (brand color)
        # ----------------------------------------------------------------
        # --- Compute per-pixel average brightness for zone detection ---
        avg = img.mean(axis=-1)

        # --- Shadow toning: subtle cool blue tint (brand aesthetic) ---
        # Only pixels below 25% brightness (true shadow zone)
        shadow_px = avg < 0.25
        img[:, :, 2][shadow_px] += np.float32(0.04 * intensity)

        # --- Highlight toning: warm amber tint (brand color #E8A817) ---
        # Only pixels above 50% brightness (highlight zone)
        # #E8A817 = R:232, G:168, B:23 → warm orange-amber
        # Simulated by boosting R slightly more than G, leaving B unchanged
        hi_px = avg > 0.5
        img[:, :, 0][hi_px] += np.float32(0.03 * intensity)   # red boost
        img[:, :, 1][hi_px] += np.float32(0.015 * intensity)  # green boost (less)
        del avg, shadow_px, hi_px  # free memory

        # ----------------------------------------------------------------
        # Step 6: Subtle vignette
        # Darkens the corners/edges to draw attention to center
        # Uses distance from center: dist 0 (center) → 1 (corner)
        # Vignette starts at dist=0.5 and fully darkens by 30% at corner
        # ----------------------------------------------------------------
        h, w = img.shape[:2]
        # --- Create normalized coordinate grids from -1 to +1 ---
        Y = np.linspace(-1, 1, h, dtype=np.float32)
        X = np.linspace(-1, 1, w, dtype=np.float32)
        # --- Euclidean distance from center ---
        dist = np.sqrt(Y[:, None]**2 + X[None, :]**2)
        # --- Vignette multiplier: 1.0 at center, ~0.7 at corner ---
        # clip(dist - 0.5, 0, 1): only activates beyond radius 0.5
        vignette = np.float32(1.0) - np.float32(0.3) * np.clip(dist - 0.5, 0, 1)
        # --- Apply to all channels ---
        for c in range(3):
            img[:, :, c] *= vignette
        del dist, vignette  # free memory

        # ----------------------------------------------------------------
        # Final: clamp to [0, 1] and convert back to uint8
        # clip() prevents overflow from split toning additions
        # ----------------------------------------------------------------
        np.clip(img, 0, 1, out=img)
        return (img * 255).astype(np.uint8)

    return grade_frame
