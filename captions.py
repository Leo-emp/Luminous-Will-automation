import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import config

# ============================================================
# CAPTION GENERATOR — PREMIUM
# Creates word-synced captions with word-by-word reveal animation
# Style: Montserrat Bold, white text, amber highlight on emphasis
# Animation: words appear one at a time, scale-in from 90%→100%
# ============================================================

# --- Animation timing constant ---
# Each word animates from 90% to 100% scale over this duration (seconds)
REVEAL_DURATION = 0.08   # 80ms scale-in animation per word


def _load_font(size):
    """
    # Loads the caption font with a 3-step fallback chain:
    #   1. Montserrat Bold (premium, from assets/fonts/) — brand font
    #   2. Arial Bold (system font, Windows) — reliable fallback
    #   3. PIL default (last resort) — always available
    #
    # Args:
    #   size: font size in pixels
    #
    # Returns: PIL ImageFont object
    """

    # --- Step 1: Try Montserrat Bold (the premium brand font) ---
    # config.CAPTION_FONT_FILE points to assets/fonts/Montserrat-Bold.ttf
    if os.path.exists(config.CAPTION_FONT_FILE):
        try:
            return ImageFont.truetype(config.CAPTION_FONT_FILE, size)
        except OSError:
            # File exists but can't be loaded (corrupted, wrong format, etc.)
            pass

    # --- Step 2: Try Arial Bold (Windows system font) ---
    # Check multiple path formats since Windows has inconsistent font naming
    for font_path in ["arialbd.ttf", "Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue  # Try the next path variant

    # --- Step 3: PIL default (always works, no TrueType features) ---
    print("[CAPTIONS] WARNING: No suitable font found, using PIL default")
    return ImageFont.load_default()


def _is_word_visible(word_start, word_end, current_time):
    """
    # Determines if a word should be visible at the given playback time
    # and what scale factor to apply during the reveal animation.
    #
    # Animation states:
    #   Before word_start: invisible (not yet revealed)
    #   0 to REVEAL_DURATION after start: animating — scale 0.9 → 1.0
    #   After REVEAL_DURATION: fully settled at scale 1.0
    #
    # Backward compatibility:
    #   When current_time is None, returns (True, 1.0) so old code paths
    #   that don't pass timing info still render all words normally.
    #
    # Args:
    #   word_start: when this word begins in the voiceover (seconds)
    #   word_end: when this word ends in the voiceover (seconds)
    #   current_time: current playback position (seconds), or None
    #
    # Returns: (visible: bool, scale: float)
    #   visible=False → skip drawing this word entirely
    #   visible=True, scale in [0.9, 1.0] → draw at this scale
    """

    # --- Backward compat: no timing info → all words visible, full scale ---
    if current_time is None:
        return True, 1.0

    # --- Word hasn't started yet → invisible ---
    if current_time < word_start:
        return False, 0.0

    # --- Word is active or past: calculate animation scale ---
    # elapsed = how many seconds since this word started
    elapsed = current_time - word_start

    if elapsed < REVEAL_DURATION:
        # --- Still animating: interpolate scale from 90% to 100% ---
        # progress: 0.0 at start of animation, 1.0 at end
        progress = elapsed / REVEAL_DURATION
        # scale linearly from 0.9 to 1.0
        scale = 0.9 + 0.1 * progress
        return True, scale
    else:
        # --- Animation complete: fully settled at 100% ---
        return True, 1.0


def create_caption_clips(word_timestamps, script_segments, video_duration):
    """
    # Creates caption data synced to each word from the voiceover
    # Groups words into display chunks (4 words at a time for readability)
    # Highlights the emphasis word in each segment with amber color
    #
    # Args:
    #   word_timestamps: list of {word, start, end} from ElevenLabs
    #   script_segments: original script with emphasis_word info
    #   video_duration: total video duration in seconds
    #
    # Returns:
    #   list of caption events: {text, start, end, highlight_word, words}
    #   Each event's 'words' field is a list of {word, start, end} for
    #   per-word animation timing in render_caption_frame.
    """

    print("[CAPTIONS] Building word-synced caption events...")

    # --- No timestamps available: fall back to segment-level timing ---
    if not word_timestamps:
        print("[CAPTIONS] WARNING: No timestamps, using fallback timing")
        return create_fallback_captions(script_segments, video_duration)

    # --- Build emphasis word lookup from script segments ---
    # These words will be highlighted amber in captions
    emphasis_words = set()
    for seg in script_segments:
        if "emphasis_word" in seg:
            emphasis_words.add(seg["emphasis_word"].lower())

    # --- Group words into display chunks ---
    # 4 words per chunk is the sweet spot for readability vs coverage
    caption_events = []
    chunk_size = 4
    i = 0

    while i < len(word_timestamps):
        # Slice out the next chunk of words
        chunk_end = min(i + chunk_size, len(word_timestamps))
        chunk = word_timestamps[i:chunk_end]

        # Build display text from chunk words
        words_in_chunk = [w["word"] for w in chunk]
        caption_text = " ".join(words_in_chunk)

        # --- Check if any word in this chunk should be highlighted ---
        # Strip punctuation for matching, then use original word for display
        highlight_word = None
        for word_data in chunk:
            clean_word = word_data["word"].strip(".,!?;:'\"").lower()
            if clean_word in emphasis_words:
                highlight_word = word_data["word"]
                break  # Only highlight one word per chunk

        # Caption timing: first word starts it, last word ends it
        start_time = chunk[0]["start"]
        end_time = chunk[-1]["end"]

        caption_events.append({
            "text": caption_text,
            "start": start_time,
            "end": end_time,
            "highlight_word": highlight_word,
            "words": chunk,   # individual word timing for per-word animation
        })

        i = chunk_end

    print(f"[CAPTIONS] Created {len(caption_events)} caption events")
    return caption_events


def create_fallback_captions(script_segments, video_duration):
    """
    # Fallback caption creator when no word-level timestamps are available
    # Divides total video time equally among script segments
    # Each segment becomes one caption with no per-word animation
    """

    # Divide time equally: each segment gets the same slice of audio time
    time_per_segment = video_duration / len(script_segments)
    events = []

    for i, seg in enumerate(script_segments):
        events.append({
            "text": seg["text"],
            "start": i * time_per_segment,
            "end": (i + 1) * time_per_segment,
            "highlight_word": seg.get("emphasis_word"),
            "words": [],  # empty: no per-word animation possible
        })

    return events


def render_caption_frame(text, highlight_word, frame_width, frame_height,
                         font_size=None, position_y=None, stroke_width=None,
                         words=None, current_time=None):
    """
    # Renders a single caption frame as a numpy array (RGBA)
    # Supports word-by-word reveal animation via words + current_time params.
    #
    # Animation behavior:
    #   - If words and current_time are provided: only draws words that have
    #     started, each animating from 90%→100% scale over 0.08 seconds
    #   - If words/current_time are omitted: draws all words (backward compatible)
    #
    # Highlight behavior:
    #   - The highlight_word is drawn in amber (#E8A817) instead of white
    #   - Matching is case-insensitive and strips punctuation
    #
    # Text rendering:
    #   - Words are wrapped to fit within frame_width - 100px margin
    #   - Each line is center-aligned horizontally
    #   - Black stroke is drawn around each word for readability
    #   - Animating words use a scaled-down font, vertically offset to
    #     align the baseline with full-size words
    #
    # Args:
    #   text: caption text string (space-separated words)
    #   highlight_word: word to highlight in amber (or None)
    #   frame_width: output frame width in pixels (e.g. 1080)
    #   frame_height: output frame height in pixels (e.g. 1920)
    #   font_size: optional override (default: config.CAPTION_FONT_SIZE = 65)
    #   position_y: optional vertical position ratio (default: config.CAPTION_POSITION[1] = 0.83)
    #   stroke_width: optional stroke width (default: config.CAPTION_STROKE_WIDTH = 2)
    #   words: list of {word, start, end} per-word timing (for animation)
    #   current_time: current video playback time in seconds (for animation)
    #
    # Returns: numpy array (frame_height, frame_width, 4) RGBA uint8
    """

    # --- Create a fully transparent canvas ---
    # RGBA: red, green, blue, alpha — alpha=0 means fully transparent
    img = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # --- Resolve settings (use overrides or fall back to config defaults) ---
    _font_size = font_size or config.CAPTION_FONT_SIZE
    _position_y = position_y or config.CAPTION_POSITION[1]
    _stroke_width = stroke_width or config.CAPTION_STROKE_WIDTH

    # --- Load the primary font at full size ---
    font = _load_font(_font_size)

    # --- Split text into individual words for per-word rendering ---
    text_words = text.split()

    # --- Build the visibility/scale map for each word ---
    # Each entry is (visible: bool, scale: float 0.9..1.0)
    word_states = []

    if words and current_time is not None:
        # --- Time-aware mode: check each word against current playback time ---
        for i, tw in enumerate(text_words):
            if i < len(words):
                # We have timing data for this word — check visibility
                vis, scale = _is_word_visible(words[i]["start"], words[i]["end"], current_time)
            else:
                # More display words than timing entries → show at full scale
                vis, scale = True, 1.0
            word_states.append((vis, scale))
    else:
        # --- Static mode (no timing): all words visible at full scale ---
        # This is the backward-compatible behavior when current_time is None
        word_states = [(True, 1.0)] * len(text_words)

    # --- Wrap words into display lines (respects frame margin) ---
    # Leaves 50px margin on each side (100px total)
    lines = wrap_text_to_lines(text_words, font, draw, frame_width - 100)

    # --- Calculate vertical starting position ---
    # Line spacing: font_size + 8px gap between baselines
    line_height = _font_size + 8
    total_text_height = len(lines) * line_height
    # Position center of text block at the configured y ratio
    y_start = int(frame_height * _position_y) - total_text_height // 2

    # --- Track which word index we're on across all lines ---
    # Lines are just display groupings — word_states is indexed linearly
    word_idx = 0

    # --- Render each line ---
    for line_idx, line_words in enumerate(lines):
        # --- Center this line horizontally ---
        line_text = " ".join(line_words)
        line_width = draw.textlength(line_text, font=font)
        x = (frame_width - line_width) // 2
        y = y_start + line_idx * line_height

        # --- Render each word in the line ---
        for word in line_words:
            # Get this word's visibility and scale state
            vis, scale = word_states[word_idx] if word_idx < len(word_states) else (True, 1.0)
            word_idx += 1

            if not vis:
                # --- Word not visible yet: skip drawing but advance x position ---
                # We must advance x so later words stay properly spaced
                word_width = draw.textlength(word + " ", font=font)
                x += word_width
                continue

            # --- Determine word color (amber highlight or white default) ---
            is_highlight = False
            if highlight_word:
                # Strip punctuation for case-insensitive comparison
                clean_word = word.strip(".,!?;:'\"").lower()
                clean_highlight = highlight_word.strip(".,!?;:'\"").lower()
                if clean_word == clean_highlight:
                    is_highlight = True

            # Apply amber highlight color or standard white
            color = config.CAPTION_HIGHLIGHT_COLOR if is_highlight else config.CAPTION_COLOR

            # --- Handle scale animation ---
            # Scale < 1.0 means this word is still animating in (90%→100%)
            if scale < 1.0:
                # Compute the scaled-down font size (minimum 10px to avoid PIL errors)
                scaled_size = max(int(_font_size * scale), 10)
                scaled_font = _load_font(scaled_size)
                # Vertical offset: push word down to keep baselines aligned
                # Without this, smaller words would "float" above the baseline
                y_offset = int((_font_size - scaled_size) * 0.5)
            else:
                # Fully settled: use the main font, no vertical offset needed
                scaled_font = font
                y_offset = 0

            # --- Draw black stroke for readability over any background ---
            # Iterate over a square of offsets to create the stroke effect
            for dx in range(-_stroke_width, _stroke_width + 1):
                for dy in range(-_stroke_width, _stroke_width + 1):
                    if dx != 0 or dy != 0:
                        # Skip the center position (that's where the colored text goes)
                        draw.text(
                            (x + dx, y + dy + y_offset),
                            word,
                            font=scaled_font,
                            fill=config.CAPTION_STROKE_COLOR,
                        )

            # --- Draw the word in its color ---
            draw.text((x, y + y_offset), word, font=scaled_font, fill=color)

            # --- Advance x: always use full-size word width for consistent spacing ---
            # This means spacing never shrinks during animation, preventing text jumps
            word_width = draw.textlength(word + " ", font=font)
            x += word_width

    # --- Convert PIL image to numpy array and return ---
    # Output shape: (frame_height, frame_width, 4) — H×W×RGBA
    return np.array(img)


def wrap_text_to_lines(words, font, draw, max_width):
    """
    # Wraps a flat list of words into display lines that fit within max_width
    # Uses greedy line-filling: adds words until the line is full
    #
    # Args:
    #   words: list of word strings
    #   font: PIL ImageFont for measuring text width
    #   draw: PIL ImageDraw for textlength measurements
    #   max_width: maximum allowed line width in pixels
    #
    # Returns: list of lists — each inner list is one line's words
    """
    lines = []
    current_line = []

    for word in words:
        # --- Test if adding this word still fits within max_width ---
        test_line = current_line + [word]
        test_text = " ".join(test_line)
        text_width = draw.textlength(test_text, font=font)

        if text_width <= max_width:
            # Word fits: add it to the current line
            current_line.append(word)
        else:
            # Word doesn't fit: finalize the current line and start a new one
            if current_line:
                lines.append(current_line)
            current_line = [word]

    # --- Don't forget the last line (the loop ends before appending it) ---
    if current_line:
        lines.append(current_line)

    return lines


# --- Quick test (runs when this file is executed directly, not via pytest) ---
if __name__ == "__main__":
    # Render a test caption frame and save it to the temp directory
    frame = render_caption_frame(
        "Your silence is your greatest weapon",
        "weapon",
        config.VIDEO_WIDTH,
        config.VIDEO_HEIGHT,
    )
    test_img = Image.fromarray(frame)
    test_path = os.path.join(config.TEMP_DIR, "test_caption.png")
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    test_img.save(test_path)
    print(f"Test caption saved to: {test_path}")
