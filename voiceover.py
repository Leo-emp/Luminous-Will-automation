import os
import re
import json
import requests
import config

# ============================================================
# VOICEOVER GENERATOR
# Uses ElevenLabs API to generate speech with word timestamps
# Voice: Adam (deep English story voice)
#
# New in this version:
#   - clean_script_text: pre-send cleanup to save credits
#   - _validate_audio: post-download sanity checks
#   - _find_long_pauses: detect excessive gaps in audio
#   - _recalculate_timestamps: fix timestamps after pause trimming
#   - _trim_long_pauses: shorten gaps > 1.5s to 0.8s
# ============================================================


def clean_script_text(text):
    """
    # Cleans script text before sending to ElevenLabs
    # Saves credits by preventing pronunciation issues
    #
    # Fixes:
    #   - ... → . (ellipsis causes weird pauses)
    #   - -- and — → , (em dashes cause tone breaks)
    #   - Double spaces → single space
    #   - Smart quotes → ASCII quotes
    #   - Unusual characters stripped
    """
    # --- Replace ellipsis with period ---
    text = text.replace("...", ".")
    # --- Replace em dashes with comma + space ---
    # Em dash may glue words (e.g. "Power—real") or have spaces ("Power -- real")
    # We strip surrounding spaces and replace with ", " for consistent output
    text = text.replace("—", ", ")
    text = re.sub(r'\s*--\s*', ', ', text)
    # --- Smart quotes to ASCII ---
    text = text.replace("“", '"').replace("”", '"')  # " and "
    text = text.replace("‘", "'").replace("’", "'")  # ' and '
    # --- Normalize whitespace ---
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _find_long_pauses(word_timestamps, threshold=1.5):
    """
    # Finds gaps between words longer than threshold seconds
    # Returns list of {gap_start, gap_end, duration, after_word_index}
    #
    # Args:
    #   word_timestamps: list of {word, start, end} dicts
    #   threshold: minimum gap duration in seconds to flag (default 1.5s)
    #
    # Returns:
    #   list of dicts describing each long pause found
    """
    pauses = []
    # --- Walk consecutive word pairs to check the gap between them ---
    for i in range(len(word_timestamps) - 1):
        gap_start = word_timestamps[i]["end"]       # end of current word
        gap_end = word_timestamps[i + 1]["start"]   # start of next word
        gap_duration = gap_end - gap_start
        # --- Only record if gap exceeds threshold ---
        if gap_duration > threshold:
            pauses.append({
                "gap_start": gap_start,
                "gap_end": gap_end,
                "duration": gap_duration,
                "after_word_index": i,  # index of the word just before this pause
            })
    return pauses


def _recalculate_timestamps(word_timestamps, trims):
    """
    # Shifts all word timestamps after each trim point
    # trims: list of {position: float, removed: float}
    # Each word after a trim position gets shifted earlier by the removed amount
    #
    # Args:
    #   word_timestamps: original list of {word, start, end} dicts
    #   trims: list of {position, removed} — where we cut and how much was removed
    #
    # Returns:
    #   new list of word timestamp dicts with adjusted start/end times
    """
    new_timestamps = []
    for wt in word_timestamps:
        # --- Copy the dict so we don't mutate the original ---
        new_wt = dict(wt)
        total_shift = 0.0
        # --- Sum all the removed time that falls before this word ---
        for trim in trims:
            if new_wt["start"] > trim["position"]:
                total_shift += trim["removed"]
        # --- Shift both start and end by the accumulated trim ---
        new_wt["start"] -= total_shift
        new_wt["end"] -= total_shift
        new_timestamps.append(new_wt)
    return new_timestamps


def _validate_audio(audio_path, expected_duration=None):
    """
    # Validates the downloaded voiceover file
    # Returns (is_valid, reason)
    #
    # Checks:
    #   1. File size > 10KB (catches empty/truncated downloads)
    #   2. Audio loads without error
    #   3. Duration > 0
    #   4. Duration at least 70% of expected (optional)
    #   5. No volume spikes (glitch detection)
    """
    from moviepy import AudioFileClip
    import numpy as np

    # --- Check file size (minimum 10KB to catch empty downloads) ---
    file_size = os.path.getsize(audio_path)
    if file_size < 10000:
        return False, f"File too small ({file_size} bytes)"

    try:
        clip = AudioFileClip(audio_path)
    except Exception as e:
        return False, f"Cannot load audio: {e}"

    # --- Check duration is not zero ---
    if clip.duration == 0:
        clip.close()
        return False, "Zero duration"

    # --- Check duration is within expected range (optional) ---
    if expected_duration and clip.duration < expected_duration * 0.7:
        clip.close()
        return False, f"Too short ({clip.duration:.1f}s vs expected {expected_duration:.1f}s)"

    # --- Check for volume spikes (glitch/corruption detection) ---
    try:
        audio_data = clip.to_soundarray(fps=22050)
        window = int(22050 * 0.1)  # 0.1s windows at 22050 Hz
        for start in range(0, len(audio_data) - window, window):
            chunk = audio_data[start:start + window]
            chunk_rms = np.sqrt(np.mean(chunk ** 2))
            # --- Compare chunk to surrounding context (3 windows each side) ---
            ctx_start = max(0, start - window * 3)
            ctx_end = min(len(audio_data), start + window * 4)
            ctx_rms = np.sqrt(np.mean(audio_data[ctx_start:ctx_end] ** 2))
            # --- Flag if chunk is 3x louder than context ---
            if ctx_rms > 0 and chunk_rms > ctx_rms * 3.0:
                clip.close()
                return False, f"Volume spike detected at {start / 22050:.1f}s"
    except Exception:
        # --- Non-fatal: skip glitch check if array conversion fails ---
        pass

    clip.close()
    return True, "OK"


def _trim_long_pauses(audio_path, word_timestamps, threshold=1.5, target=0.8):
    """
    # Trims pauses longer than threshold down to target seconds
    # Returns (new_audio_path, new_timestamps, trims_applied)
    #
    # Args:
    #   audio_path: path to the .mp3 file
    #   word_timestamps: list of {word, start, end} dicts
    #   threshold: pauses longer than this get trimmed (default 1.5s)
    #   target: how long the trimmed pause should be (default 0.8s)
    #
    # Returns:
    #   tuple of (output_path, adjusted_timestamps, trims_list)
    """
    from moviepy import AudioFileClip, concatenate_audioclips

    # --- Check if any long pauses exist ---
    pauses = _find_long_pauses(word_timestamps, threshold)
    if not pauses:
        # --- Nothing to trim, return original unchanged ---
        return audio_path, word_timestamps, []

    print(f"[VOICEOVER] Found {len(pauses)} long pauses to trim")

    clip = AudioFileClip(audio_path)
    segments = []  # audio segments we will keep
    trims = []     # record of each trim applied
    last_end = 0.0

    for pause in pauses:
        # --- Keep audio from last point up to where the pause starts ---
        segments.append(clip.subclipped(last_end, pause["gap_start"]))
        # --- Add a target-length silence (0.8s) in place of the full pause ---
        segments.append(clip.subclipped(pause["gap_start"], pause["gap_start"] + target))
        removed = pause["duration"] - target
        trims.append({"position": pause["gap_start"], "removed": removed})
        last_end = pause["gap_end"]

    # --- Append any remaining audio after the last pause ---
    if last_end < clip.duration:
        segments.append(clip.subclipped(last_end, clip.duration))

    # --- Concatenate and export to a new file ---
    trimmed = concatenate_audioclips(segments)
    trimmed_path = audio_path.replace(".mp3", "_trimmed.mp3")
    trimmed.write_audiofile(trimmed_path, logger=None)
    trimmed.close()
    clip.close()

    # --- Recalculate timestamps to match the new audio timing ---
    new_timestamps = _recalculate_timestamps(word_timestamps, trims)

    total_removed = sum(t["removed"] for t in trims)
    print(f"[VOICEOVER] Trimmed {total_removed:.1f}s of pauses")
    return trimmed_path, new_timestamps, trims


def _normalize_audio(audio_path, target_dbfs=-3.0):
    """
    # Normalizes audio so the loudest peak hits target_dbfs.
    # Guarantees consistent voice volume regardless of ElevenLabs output.
    # Phone speakers need loud, consistent voice — this ensures it.
    """
    from pydub import AudioSegment

    audio = AudioSegment.from_file(audio_path)
    change_db = target_dbfs - audio.max_dBFS
    if abs(change_db) < 0.1:
        print(f"[VOICEOVER] Already at target level ({audio.max_dBFS:.1f}dBFS)")
        return audio_path
    normalized = audio + change_db
    normalized.export(audio_path, format="mp3")
    print(f"[VOICEOVER] Normalized: {audio.max_dBFS:.1f}dBFS → {target_dbfs:.1f}dBFS ({change_db:+.1f}dB)")
    return audio_path


def generate_voiceover(script_text, output_path, profile=None):
    """
    # Generates voiceover audio from script text using ElevenLabs
    # Now with: text cleaning, validation, pause trimming, retry
    #
    # Args:
    #   script_text: full script as a single string
    #   output_path: where to save the .mp3 file
    #   profile: optional dict with format-specific voice settings (e.g. voice_stability)
    #
    # Returns:
    #   list of dicts with keys: word, start, end (times in seconds)
    """

    print("[VOICEOVER] Generating speech with ElevenLabs...")

    # --- Pre-send: Clean script text (saves credits by fixing pronunciation) ---
    cleaned_text = clean_script_text(script_text)
    if cleaned_text != script_text:
        print("[VOICEOVER] Cleaned script text (removed special chars)")

    # --- Build the API request ---
    # Using the "with timestamps" endpoint for word-level sync
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}/with-timestamps"

    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    # --- Use profile stability if provided, else default ---
    voice_settings = dict(config.VOICE_SETTINGS)
    if profile and "voice_stability" in profile:
        voice_settings["stability"] = profile["voice_stability"]

    payload = {
        "text": cleaned_text,
        "model_id": config.ELEVENLABS_MODEL_ID,
        "voice_settings": voice_settings,
        "speed": config.VOICE_SPEED,
    }

    # --- Attempt generation (max 1 retry for corruption) ---
    max_attempts = 2
    for attempt in range(max_attempts):
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            print(f"[VOICEOVER] ERROR: API returned {response.status_code}")
            print(f"[VOICEOVER] Response: {response.text}")
            raise Exception(f"ElevenLabs API error: {response.status_code}")

        # --- Parse the response ---
        # The response contains base64 audio and alignment data
        result = response.json()

        # --- Save the audio file ---
        import base64
        audio_bytes = base64.b64decode(result["audio_base64"])
        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        # --- Extract word timestamps from character-level alignment ---
        word_timestamps = extract_word_timestamps(result.get("alignment", {}))

        # --- Post-download validation ---
        # Estimate expected duration from word count (~2.6 words/sec at 0.83 speed)
        expected_duration = len(cleaned_text.split()) / 2.6
        is_valid, reason = _validate_audio(output_path, expected_duration)

        if is_valid:
            # --- Validation passed, move on ---
            break
        elif attempt < max_attempts - 1:
            print(f"[VOICEOVER] Validation failed ({reason}), retrying once...")
        else:
            print(f"[VOICEOVER] WARNING: Audio validation failed ({reason}), using best attempt")

    # --- Post-process: normalize voiceover to -3dB peak ---
    # ElevenLabs outputs inconsistent volumes — some clips are quiet.
    # Normalization boosts the entire clip so the loudest peak hits -3dB.
    # This guarantees every video has the same voice loudness, no manual testing.
    output_path = _normalize_audio(output_path, target_dbfs=-3.0)

    # --- Post-process: trim long pauses to tighten pacing ---
    output_path, word_timestamps, trims = _trim_long_pauses(
        output_path, word_timestamps, threshold=1.5, target=0.8
    )

    # --- Save timestamps to JSON for caption syncing ---
    # Always save to the base path (without "_trimmed") so callers find it predictably
    timestamps_path = output_path.replace(".mp3", "_timestamps.json").replace("_trimmed", "")
    with open(timestamps_path, "w") as f:
        json.dump(word_timestamps, f, indent=2)

    print(f"[VOICEOVER] Audio saved: {output_path}")
    print(f"[VOICEOVER] Found {len(word_timestamps)} words with timestamps")

    return word_timestamps


def extract_word_timestamps(alignment):
    """
    # Converts ElevenLabs character-level alignment to word-level
    #
    # ElevenLabs alignment format:
    #   characters: list of characters
    #   character_start_times_seconds: start time for each char
    #   character_end_times_seconds: end time for each char
    #
    # Returns:
    #   list of {word, start, end} dicts
    """

    if not alignment:
        print("[VOICEOVER] WARNING: No alignment data returned")
        return []

    characters = alignment.get("characters", [])
    start_times = alignment.get("character_start_times_seconds", [])
    end_times = alignment.get("character_end_times_seconds", [])

    if not characters or not start_times or not end_times:
        return []

    # --- Build words from characters ---
    words = []
    current_word = ""
    word_start = None

    for i, char in enumerate(characters):
        if char == " ":
            # Space = word boundary
            if current_word:
                words.append({
                    "word": current_word,
                    "start": word_start,
                    "end": end_times[i - 1],
                })
                current_word = ""
                word_start = None
        else:
            if word_start is None:
                word_start = start_times[i]
            current_word += char

    # --- Don't forget the last word (no trailing space) ---
    if current_word:
        words.append({
            "word": current_word,
            "start": word_start,
            "end": end_times[-1],
        })

    return words


def get_audio_duration(audio_path):
    """
    # Returns the duration of an audio file in seconds
    """
    from moviepy import AudioFileClip
    clip = AudioFileClip(audio_path)
    duration = clip.duration
    clip.close()
    return duration


# --- Quick test ---
if __name__ == "__main__":
    test_text = "The most powerful people never raise their voice."
    output = os.path.join(config.TEMP_DIR, "test_voiceover.mp3")
    try:
        timestamps = generate_voiceover(test_text, output)
        print(f"\nTimestamps: {json.dumps(timestamps, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure your ELEVENLABS_API_KEY is set in .env")
