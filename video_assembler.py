import os
import json
import subprocess
import numpy as np
from PIL import Image
from moviepy import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_videoclips, vfx, afx
)
import config
# color_grading imports are done inside create_base_video() to keep them local
from captions import render_caption_frame

# ============================================================
# VIDEO ASSEMBLER
# Assembles the final video from all components:
# - Stock footage clips (color graded)
# - Voiceover audio
# - Word-synced captions with highlights
# - Background music (encouraging but never overpowering voice)
# - Logo outro
#
# CRITICAL: Each visual clip is synced to its matching script
# segment so visuals always match what's being said at that
# exact moment in the voiceover.
# ============================================================


def assemble_video(
    clip_paths,
    voiceover_path,
    caption_events,
    script_segments,
    music_path,
    output_path,
    video_format=None,
    work_dir=None,
):
    """
    # Main assembly function - builds the complete video
    # Format-aware: uses profile settings for resolution, bitrate,
    # transitions, and music mixing mode.
    # work_dir: topic-specific temp dir for caching graded clips + base video
    """

    from config import VideoFormat, get_format_profile

    if video_format is None:
        video_format = VideoFormat.VERTICAL_SHORT

    profile = get_format_profile(video_format)
    print(f"[ASSEMBLER] Format: {video_format.value} ({profile['width']}x{profile['height']})")
    print("[ASSEMBLER] Starting video assembly...")

    # --- Step 1: Load voiceover and get total duration ---
    voiceover = AudioFileClip(voiceover_path)
    total_duration = voiceover.duration
    print(f"[ASSEMBLER] Voiceover duration: {total_duration:.1f}s")

    # --- Step 2: Build the visual timeline ---
    visual_timeline = build_visual_timeline(
        clip_paths, script_segments, caption_events, total_duration
    )

    # --- Step 3: Create base video (with caching in work_dir) ---
    base_video = create_base_video(visual_timeline, total_duration, profile, script_segments, work_dir=work_dir)
    base_video_path = base_video.filename
    base_video.close()
    del base_video
    print(f"[ASSEMBLER] Base video ready: {base_video_path}")

    frame_w = profile["width"]
    frame_h = profile["height"]

    # --- Step 4: Generate ASS subtitle file for ffmpeg caption burn ---
    print(f"[ASSEMBLER] Generating {len(caption_events)} captions as ASS subtitles")
    ass_path = os.path.join(work_dir or config.TEMP_DIR, "captions.ass")
    _generate_ass_subtitles(caption_events, ass_path, profile)

    # --- Step 5: Create logo outro clip ---
    logo_outro_path = os.path.join(work_dir or config.TEMP_DIR, "logo_outro.mp4")
    _ensure_logo_outro(logo_outro_path, profile)

    # --- Step 6: Final compose via ffmpeg (captions + audio + logo) ---
    import gc
    gc.collect()
    print(f"[ASSEMBLER] Exporting final video via ffmpeg to: {output_path}")
    _ffmpeg_final_compose(
        base_video_path=base_video_path,
        ass_path=ass_path,
        voiceover_path=voiceover_path,
        music_path=music_path,
        logo_path=logo_outro_path,
        output_path=output_path,
        profile=profile,
        total_duration=total_duration,
    )

    print(f"[ASSEMBLER] Video exported successfully: {output_path}")
    validate_output(output_path, profile)
    return output_path


def validate_output(output_path, profile):
    """
    # Post-render quality gate — checks file isn't corrupted or broken
    # before it gets uploaded and added to the review queue.
    # Falls through with a warning if ffprobe isn't available.
    """
    if not os.path.exists(output_path):
        raise ValueError(f"[VALIDATE] Output file missing: {output_path}")

    file_size = os.path.getsize(output_path)
    if file_size < 500_000:
        raise ValueError(f"[VALIDATE] Output too small ({file_size} bytes), likely corrupted")

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", output_path],
            capture_output=True, text=True, timeout=30
        )
        info = json.loads(result.stdout)

        # Check for video stream
        streams = info.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)

        if not has_video:
            raise ValueError("[VALIDATE] No video stream found in output")
        if not has_audio:
            print("[VALIDATE] Warning: no audio stream — video may be silent")

        # Check resolution matches target
        video_stream = next(s for s in streams if s.get("codec_type") == "video")
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        expected_w = profile.get("width", profile.get("resolution", [0,0])[0] if "resolution" in profile else 0)
        expected_h = profile.get("height", profile.get("resolution", [0,0])[1] if "resolution" in profile else 0)
        if expected_w and expected_h and (width != expected_w or height != expected_h):
            print(f"[VALIDATE] Warning: resolution {width}x{height} != expected {expected_w}x{expected_h}")

        # Check video vs audio stream durations match (OOM truncation guard)
        video_dur = float(video_stream.get("duration", 0))
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        audio_dur = float(audio_stream.get("duration", 0)) if audio_stream else 0
        if audio_dur > 0 and video_dur > 0 and video_dur < audio_dur * 0.8:
            raise ValueError(
                f"[VALIDATE] Video truncated: video={video_dur:.1f}s vs audio={audio_dur:.1f}s "
                f"(encoder likely OOM'd mid-render)"
            )

        # Check duration is reasonable
        duration = float(info.get("format", {}).get("duration", 0))
        if duration < 5:
            raise ValueError(f"[VALIDATE] Duration too short ({duration:.1f}s)")

        print(f"[VALIDATE] Passed — {width}x{height}, video={video_dur:.1f}s, audio={audio_dur:.1f}s, {file_size/1_000_000:.1f}MB")

    except (FileNotFoundError, json.JSONDecodeError):
        print("[VALIDATE] Warning: ffprobe not available, skipping quality check")


def _format_ass_time(seconds):
    """Convert seconds to ASS timestamp format: H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _generate_ass_subtitles(caption_events, ass_path, profile):
    """
    # Generates an ASS subtitle file from caption events.
    # Matches the Luminous Will caption style:
    #   - Montserrat Bold (or Arial Bold fallback)
    #   - White text with black outline
    #   - Amber (#E8A817) highlight on emphasis words
    #   - Positioned at 60% from top (short) or 88% (long)
    """
    font_size = profile.get("caption_font_size", 65)
    position_y = profile.get("caption_position_y", 0.60)
    stroke_width = profile.get("caption_stroke_width", 2)
    frame_h = profile["height"]

    # --- ASS vertical position: distance from bottom in pixels ---
    margin_bottom = int(frame_h * (1.0 - position_y))

    # --- Check which font is available ---
    font_name = "Montserrat"
    font_file = os.path.join(os.path.dirname(__file__), "assets", "fonts", "Montserrat-Bold.ttf")
    if not os.path.exists(font_file):
        font_name = "Arial"

    # --- ASS color format: &HBBGGRR (BGR, not RGB) ---
    white = "&H00FFFFFF"
    amber = "&H0017A8E8"  # #E8A817 in BGR
    black = "&H00000000"

    lines = []
    lines.append("[Script Info]")
    lines.append("Title: Luminous Will Captions")
    lines.append(f"PlayResX: {profile['width']}")
    lines.append(f"PlayResY: {profile['height']}")
    lines.append("ScaledBorderAndShadow: yes")
    lines.append("")
    lines.append("[V4+ Styles]")
    lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
    lines.append(f"Style: Default,{font_name},{font_size},{white},{white},{black},&H00000000,-1,0,0,0,100,100,0,0,1,{stroke_width},0,2,10,10,{margin_bottom},1")
    lines.append("")
    lines.append("[Events]")
    lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

    for event in caption_events:
        start_time = event["start"]
        end = _format_ass_time(event["end"])
        text = event["text"]
        highlight = event.get("highlight_word", "")
        words = event.get("words", [])

        if words and len(words) > 0:
            # --- Word-by-word reveal using ASS \kf (karaoke fade) tags ---
            # Each word gets a \kf tag with duration in centiseconds
            # Words are invisible until their karaoke time arrives
            parts = []
            for w in words:
                word_text = w["word"]
                # --- Duration from event start to this word's start (centiseconds) ---
                delay_cs = max(0, int((w["start"] - start_time) * 100))
                word_dur_cs = max(1, int((w["end"] - w["start"]) * 100))

                parts.append("{\\kf" + str(delay_cs) + "}" + word_text)

            start = _format_ass_time(start_time)
            styled = " ".join(parts)
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{styled}")
        else:
            # --- Fallback: show full line at once ---
            start = _format_ass_time(start_time)
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[ASSEMBLER] ASS subtitles written: {len(caption_events)} events")


def _ensure_logo_outro(logo_path, profile):
    """
    # Creates a logo outro video clip via ffmpeg if it doesn't exist yet.
    """
    if os.path.exists(logo_path) and os.path.getsize(logo_path) > 10_000:
        return

    # --- Use the black-background outro image (matches old videos) ---
    outro_img = os.path.join(os.path.dirname(__file__), "assets", "references", "quiet_leader_outro.png")
    if not os.path.exists(outro_img):
        outro_img = config.LOGO_PATH
    if not os.path.exists(outro_img):
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([
            ff, "-y", "-f", "lavfi",
            "-i", f"color=c=black:s={profile['width']}x{profile['height']}:d={config.LOGO_DURATION}:r={profile['fps']}",
            "-c:v", "libx264", "-preset", "ultrafast", "-an", logo_path,
        ], capture_output=True, timeout=30)
        return

    w, h = profile["width"], profile["height"]
    dur = config.LOGO_DURATION
    fps = profile["fps"]

    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([
        ff, "-y", "-loop", "1", "-i", outro_img,
        "-t", str(dur), "-r", str(fps),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,fade=t=in:st=0:d=1",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-an", logo_path,
    ], capture_output=True, timeout=60)
    print(f"[ASSEMBLER] Logo outro created: {dur}s")


def _ffmpeg_final_compose(base_video_path, ass_path, voiceover_path, music_path,
                          logo_path, output_path, profile, total_duration):
    """
    # Final composition entirely via ffmpeg — no Python frame processing.
    # Combines: base video + ASS captions + logo outro + voiceover + music
    """
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()

    # --- Voiceover boost and music level from profile ---
    vo_boost_db = profile.get("voiceover_boost_db", 1.5)
    music_db = profile.get("music_level_db", -9)

    # --- Escape backslashes and colons in ASS path for ffmpeg on Windows ---
    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

    # --- Build the ffmpeg command ---
    cmd = [ff, "-y"]

    # Inputs
    cmd += ["-i", base_video_path]     # 0: base video (no audio)
    cmd += ["-i", voiceover_path]      # 1: voiceover
    has_music = music_path and os.path.exists(music_path)
    if has_music:
        cmd += ["-i", music_path]      # 2: music
    if os.path.exists(logo_path):
        cmd += ["-i", logo_path]       # 2 or 3: logo outro

    # --- Video filter: burn ASS subtitles ---
    cmd += ["-filter_complex"]

    filter_parts = []

    # --- Concat base + logo if logo exists ---
    if os.path.exists(logo_path):
        logo_idx = 3 if has_music else 2
        filter_parts.append(f"[0:v][{logo_idx}:v]concat=n=2:v=1:a=0[vcat]")
        filter_parts.append(f"[vcat]ass='{ass_escaped}'[vout]")
    else:
        filter_parts.append(f"[0:v]ass='{ass_escaped}'[vout]")

    # --- Audio filter: boost voiceover + mix with music ---
    # alimiter at the end prevents clipping at the louder boost levels
    # limit=0.95 keeps peaks just below digital max (no distortion)
    # attack=5ms catches transients, release=50ms for smooth recovery
    filter_parts.append(f"[1:a]volume={vo_boost_db}dB[vo]")
    if has_music:
        video_dur = total_duration + config.LOGO_DURATION
        filter_parts.append(f"[2:a]aloop=loop=-1:size=2e+09,atrim=0:{video_dur},volume={music_db}dB,afade=t=in:st=0:d=2,afade=t=out:st={video_dur-3}:d=3[mus]")
        filter_parts.append(f"[vo][mus]amix=inputs=2:duration=longest,alimiter=limit=0.95:attack=5:release=50[aout]")
    else:
        filter_parts.append(f"[vo]alimiter=limit=0.95:attack=5:release=50[aout]")

    cmd += [";".join(filter_parts)]
    cmd += ["-map", "[vout]", "-map", "[aout]"]

    # --- Output settings ---
    cmd += [
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",    # standard pixel format — phones/browsers can't play yuv444p
        "-preset", "ultrafast",
        "-threads", "1",
        "-b:v", profile["bitrate"],
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path,
    ]

    print(f"[ASSEMBLER] Running ffmpeg final compose...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        print(f"[ASSEMBLER] ffmpeg stderr: {result.stderr[-1000:]}")
        raise RuntimeError(f"[ASSEMBLER] ffmpeg failed with code {result.returncode}")

    print(f"[ASSEMBLER] ffmpeg compose complete")


def build_visual_timeline(clip_paths, script_segments, caption_events, total_duration):
    """
    # Maps each visual clip to the EXACT time range of its matching
    # script segment so the visual always matches the storyline.
    #
    # How it works:
    #   - Each script segment has a corresponding downloaded clip
    #   - We use word timestamps from captions to find when each
    #     segment starts and ends in the voiceover
    #   - The clip plays during that exact time window
    #
    # Example:
    #   Script segment: "A lion doesn't lose sleep over the opinion of sheep"
    #   Visual keywords: "lion portrait dark dramatic"
    #   Voiceover says this at: 28.5s - 32.1s
    #   -> Lion footage plays from 28.5s to 32.1s
    #
    # Returns: list of {path, start, end, duration}
    """

    num_clips = len(clip_paths)
    num_segments = len(script_segments)
    if num_clips == 0:
        return []

    # --- Calculate time boundaries for each script segment ---
    # Use caption events (which have word timestamps) to find when
    # each segment of the script is being spoken
    segment_times = calculate_segment_times(
        script_segments, caption_events, total_duration
    )

    timeline = []

    for i in range(num_clips):
        # Get the time window for this segment
        if i < len(segment_times):
            start = segment_times[i]["start"]
            end = segment_times[i]["end"]
        else:
            # More clips than segments: distribute remaining time evenly
            remaining_start = segment_times[-1]["end"] if segment_times else 0
            remaining_duration = total_duration - remaining_start
            extra_clips = num_clips - len(segment_times)
            clip_idx = i - len(segment_times)
            per_clip = remaining_duration / extra_clips if extra_clips > 0 else 0
            start = remaining_start + clip_idx * per_clip
            end = start + per_clip

        timeline.append({
            "path": clip_paths[i],
            "start": start,
            "end": end,
            "duration": end - start,
        })

        # Log what visual is playing during which part of the script
        segment_text = script_segments[i]["text"][:50] if i < num_segments else "..."
        print(f"[TIMELINE] {start:.1f}s-{end:.1f}s: \"{segment_text}...\"")

    return timeline


def calculate_segment_times(script_segments, caption_events, total_duration):
    """
    # Figures out WHEN each script segment is spoken in the voiceover
    # by matching segment text to caption event timestamps.
    #
    # This is what ensures visuals sync to the storyline:
    #   - When the voice says "lion", the lion clip is playing
    #   - When the voice says "chess", the chess clip is playing
    #
    # Returns: list of {start, end} times for each segment
    """

    segment_times = []
    num_segments = len(script_segments)

    if not caption_events:
        # Fallback: divide time equally if no timestamps available
        per_segment = total_duration / num_segments
        for i in range(num_segments):
            segment_times.append({
                "start": i * per_segment,
                "end": (i + 1) * per_segment,
            })
        return segment_times

    # --- Match each script segment to caption timestamps ---
    # Caption events contain word-level timing from ElevenLabs
    # We find which caption events belong to which script segment
    # by matching the words in each segment to the caption text

    # Build a flat list of all words with their timestamps
    all_words = []
    for event in caption_events:
        if event.get("words"):
            for w in event["words"]:
                all_words.append(w)
        else:
            # If no individual word timing, use event timing
            for word in event["text"].split():
                all_words.append({
                    "word": word,
                    "start": event["start"],
                    "end": event["end"],
                })

    if not all_words:
        # Fallback: divide time equally
        per_segment = total_duration / num_segments
        for i in range(num_segments):
            segment_times.append({
                "start": i * per_segment,
                "end": (i + 1) * per_segment,
            })
        return segment_times

    # --- Walk through script segments and find their time boundaries ---
    word_index = 0

    for seg_idx, segment in enumerate(script_segments):
        seg_words = segment["text"].split()
        seg_word_count = len(seg_words)

        # Find the start time: where this segment's first word begins
        if word_index < len(all_words):
            seg_start = all_words[word_index]["start"]
        else:
            # Past the end of timestamps, estimate from last known position
            seg_start = all_words[-1]["end"] if all_words else 0

        # Find the end time: where this segment's last word ends
        end_index = min(word_index + seg_word_count - 1, len(all_words) - 1)
        if end_index >= 0 and end_index < len(all_words):
            seg_end = all_words[end_index]["end"]
        else:
            seg_end = total_duration

        segment_times.append({
            "start": seg_start,
            "end": seg_end,
        })

        # Advance the word pointer past this segment's words
        word_index += seg_word_count

    # --- Make sure the last segment extends to the end of the audio ---
    if segment_times:
        segment_times[-1]["end"] = total_duration

    return segment_times


def _pre_downscale_if_needed(clip_path, target_w, target_h, temp_dir, idx):
    """
    # If a clip is larger than 2x the target resolution, downscale it
    # via ffmpeg BEFORE MoviePy loads it — prevents numpy OOM on 4K clips.
    # Returns the (possibly downscaled) path.
    """
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", clip_path],
            capture_output=True, text=True, timeout=10
        )
        parts = result.stdout.strip().split(",")
        if len(parts) < 2:
            return clip_path
        src_w, src_h = int(parts[0]), int(parts[1])

        # --- Only downscale if source is more than 1.5x target in either dimension ---
        if src_w <= target_w * 1.5 and src_h <= target_h * 1.5:
            return clip_path

        downscaled_path = os.path.join(temp_dir, f"ds_{idx:03d}.mp4")
        if os.path.exists(downscaled_path) and os.path.getsize(downscaled_path) > 10_000:
            return downscaled_path

        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        # --- Scale to fit within target bounds, keeping aspect ratio ---
        scale_filter = f"scale='min({target_w*2},iw)':min'({target_h*2},ih)':force_original_aspect_ratio=decrease"
        subprocess.run([
            ff, "-y", "-i", clip_path,
            "-vf", f"scale=w='min({target_w*2},iw)':h='min({target_h*2},ih)':force_original_aspect_ratio=decrease",
            "-c:v", "libx264", "-preset", "ultrafast", "-an", downscaled_path,
        ], capture_output=True, timeout=120)

        if os.path.exists(downscaled_path) and os.path.getsize(downscaled_path) > 10_000:
            print(f"[ASSEMBLER] Pre-downscaled clip {idx}: {src_w}x{src_h} → target-safe")
            return downscaled_path
    except Exception:
        pass
    return clip_path


def _ffmpeg_lut_grade(ffmpeg_exe, input_path, output_path, lut_path, vignette_path, profile):
    """
    # Applies color grading + vignette to a clip using ffmpeg's native filters.
    # This is the fast path — replaces the per-frame Python grading pipeline.
    #
    # Two-step filter chain:
    #   1. lut3d — applies the pre-computed 3D LUT (exact same color math as Python)
    #   2. blend=multiply — multiplies with the vignette mask image (edge darkening)
    #
    # The vignette PNG is looped to match the video length, then blended
    # frame-by-frame with the LUT-graded output. blend=multiply correctly
    # multiplies each RGB channel by the mask value (255=keep, 185=darken 27%).
    #
    # Args:
    #   ffmpeg_exe: str — path to the ffmpeg binary
    #   input_path: str — ungraded intermediate clip (near-lossless CRF 4)
    #   output_path: str — where to save the graded clip
    #   lut_path: str — .cube LUT file matching the clip's brightness level
    #   vignette_path: str — vignette mask PNG at target resolution
    #   profile: dict — format profile with bitrate, fps settings
    """
    import subprocess

    # --- Convert Windows paths to forward slashes for ffmpeg filter strings ---
    # ffmpeg's filter parser treats backslashes as escape characters
    lut_ffmpeg = lut_path.replace('\\', '/').replace(':', '\\:')
    vig_ffmpeg = vignette_path.replace('\\', '/')

    # --- Build the ffmpeg filter chain ---
    # [0:v] = ungraded video input
    # [1:v] = vignette mask (looped via -loop 1)
    # Step 1: Apply 3D LUT (color grading steps 1-5 baked in)
    # Step 2: Blend with vignette mask (step 6 — edge darkening)
    # shortest=1 = stop when video ends (vignette loops forever)
    filter_complex = (
        f"[0:v]lut3d=file='{lut_ffmpeg}'[graded];"
        f"[graded][1:v]blend=all_mode=multiply:shortest=1"
    )

    cmd = [
        ffmpeg_exe, "-y",
        "-i", input_path,                    # ungraded video
        "-loop", "1", "-i", vignette_path,   # vignette mask (looped)
        "-filter_complex", filter_complex,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-b:v", profile["bitrate"],
        "-pix_fmt", "yuv420p",               # force standard pixel format (blend with RGB PNG promotes to yuv444p which most players can't decode)
        "-an",                                # no audio in base clips
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        # --- If LUT grading fails, raise so caller can handle ---
        raise RuntimeError(
            f"[ASSEMBLER] ffmpeg LUT grade failed (exit {result.returncode}): "
            f"{result.stderr[-500:] if result.stderr else 'no stderr'}"
        )


def _get_source_duration(clip_path):
    """
    # Gets a clip's duration in seconds via ffprobe.
    # Used to check whether a source clip needs looping
    # (i.e. source is shorter than the needed segment duration).
    # Returns 0.0 on any error — caller will attempt without looping.
    """
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", clip_path],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _measure_brightness_ffmpeg(ffmpeg_exe, clip_path):
    """
    # Measures the average brightness of a clip's first frame via ffmpeg.
    # Returns "dark", "medium", or "bright" — used to pick the matching LUT.
    #
    # How it works:
    #   1. Extracts the first video frame from the source clip
    #   2. Scales it down to 64x64 pixels (enough for brightness estimation)
    #   3. Converts to grayscale (single byte per pixel)
    #   4. Reads raw bytes via pipe and computes the average
    #
    # This replaces the MoviePy approach (clip.get_frame(0) + numpy mean)
    # and runs in ~50ms without loading the clip into Python memory.
    #
    # Same thresholds as _get_adaptive_intensity() in color_grading.py:
    #   avg < 0.30 → "dark"   (LUT with intensity=0.8 — boosts dark footage)
    #   avg > 0.60 → "bright" (LUT with intensity=1.2 — tames bright footage)
    #   else       → "medium" (LUT with intensity=1.0 — standard grading)
    """
    try:
        # --- Extract one 64x64 grayscale frame (4096 bytes) via pipe ---
        result = subprocess.run(
            [ffmpeg_exe, "-i", clip_path, "-vframes", "1",
             "-vf", "scale=64:64", "-f", "rawvideo", "-pix_fmt", "gray",
             "pipe:1"],
            capture_output=True, timeout=10,
        )
        if result.returncode == 0 and len(result.stdout) > 0:
            # --- Sum all pixel values and normalize to 0.0–1.0 range ---
            avg = sum(result.stdout) / len(result.stdout) / 255.0
            if avg < 0.30:
                return "dark"
            elif avg > 0.60:
                return "bright"
    except Exception:
        pass
    # --- Default to medium if measurement fails ---
    return "medium"


def _ffmpeg_full_clip(ffmpeg_exe, source_path, output_path, profile,
                      needed_dur, lut_path, vignette_path,
                      kb_params=None, crossfade_dur=0.0, loop_source=False):
    """
    # Single-pass ffmpeg command that replaces the ENTIRE MoviePy clip pipeline.
    # Does everything in one native C invocation — no Python frame processing:
    #
    #   1. Resize + center crop → target resolution (replaces fit_clip / fit_to_vertical)
    #   2. Ken Burns zoom animation  (replaces _apply_ken_burns with per-frame PIL)
    #   3. Fade from black           (replaces vfx.CrossFadeIn)
    #   4. 3D LUT color grading      (replaces Python grading pipeline)
    #   5. Vignette mask blend        (replaces the separate _ffmpeg_lut_grade pass)
    #
    # Speed:  ~2-5s per clip  (was ~40s with MoviePy two-pass approach)
    # Quality: identical — same lanczos resize, same LUT math, same vignette
    # Compat:  forces yuv420p — plays on phones, TikTok, all browsers
    #
    # For clips shorter than needed: pass loop_source=True and ffmpeg will
    # loop the input infinitely via -stream_loop, trimmed to needed_dur.
    #
    # Ken Burns zoom uses ffmpeg's time-based crop expressions:
    #   crop_w(t) = target_w * max_scale / (start_scale + delta * t / duration)
    #   This produces the exact same progressive zoom as the Python version.
    #   Pan-only styles (scale 1.0→1.0) have no visible effect and are
    #   treated as static to avoid unnecessary processing.
    #
    # Args:
    #   ffmpeg_exe:    str  — path to ffmpeg binary
    #   source_path:   str  — original stock footage clip
    #   output_path:   str  — where to write the fully graded clip
    #   profile:       dict — format profile (width, height, bitrate, etc.)
    #   needed_dur:    float — exact duration this clip needs to be (seconds)
    #   lut_path:      str  — .cube LUT file matching clip brightness level
    #   vignette_path: str  — vignette mask PNG at target resolution
    #   kb_params:     dict — ken burns params from _get_ken_burns_params(), or None
    #   crossfade_dur: float — fade-from-black duration (0 = no fade)
    #   loop_source:   bool — True if source clip is shorter than needed_dur
    """
    target_w = profile["width"]
    target_h = profile["height"]

    # --- Determine if this is a zoom ken burns or static/pan ---
    # Pan with scale 1.0→1.0 produces no visible motion (crop window = full frame)
    # so we treat pan and static identically — simple resize + crop
    has_zoom = (kb_params is not None and
                kb_params.get("start_scale") != kb_params.get("end_scale"))

    # --- Build the video filter chain (applied to [0:v] input) ---
    filters = []

    if has_zoom:
        # --- Ken Burns ZOOM: overscan the clip, then animated crop ---
        # max_scale determines the oversized canvas (e.g. 1.12x = 12% bigger)
        # The crop window starts at one size and shrinks/grows over the duration
        max_s = max(kb_params["start_scale"], kb_params["end_scale"])
        ow = int(target_w * max_s)
        oh = int(target_h * max_s)
        # --- Make dimensions even for h264 compatibility ---
        ow += ow % 2
        oh += oh % 2

        # Step A: Scale source to fill the oversized canvas, then center crop
        # force_original_aspect_ratio=increase → overscan (no black bars)
        # Subsequent crop removes any overshoot from aspect mismatch
        filters.append(
            f"scale={ow}:{oh}:force_original_aspect_ratio=increase:flags=lanczos"
        )
        filters.append(f"crop={ow}:{oh}")

        # Step B: Time-animated crop — creates the zoom motion
        # At each time t, the crop window size is:
        #   w(t) = target_w * max_s / (start_s + delta_s * t / duration)
        #   h(t) = target_h * max_s / (start_s + delta_s * t / duration)
        # For zoom-in (1.0→1.12):  window shrinks from 1210→1080 (push-in effect)
        # For zoom-out (1.12→1.0): window grows from 1080→1210 (pull-back effect)
        ss = kb_params["start_scale"]        # start scale (e.g. 1.0)
        ds = kb_params["end_scale"] - ss     # delta scale (e.g. 0.12 or -0.12)
        dur = needed_dur

        # --- ffmpeg time expressions using 't' (seconds since clip start) ---
        # CRITICAL: 't' is NAN during filter initialization (before first frame).
        # If the expression returns NAN, the crop filter can't allocate output
        # buffers and the entire filter chain fails. Guard with if(isnan(t)).
        # Use integer ow/oh (not float target_w*max_s) to avoid precision issues.
        cw_expr = f"if(isnan(t),{ow},{ow}/({ss}+{ds}*t/{dur}))"
        ch_expr = f"if(isnan(t),{oh},{oh}/({ss}+{ds}*t/{dur}))"
        filters.append(
            f"crop=w='{cw_expr}':h='{ch_expr}':x='(iw-ow)/2':y='(ih-oh)/2'"
        )

        # Step C: Scale the variable-size crop back to exact target resolution
        filters.append(f"scale={target_w}:{target_h}:flags=lanczos")
    else:
        # --- STATIC or PAN: simple resize + center crop to target ---
        # force_original_aspect_ratio=increase fills the target (overscans)
        # crop takes the center target_w x target_h — same as fit_to_vertical()
        filters.append(
            f"scale={target_w}:{target_h}"
            f":force_original_aspect_ratio=increase:flags=lanczos"
        )
        filters.append(f"crop={target_w}:{target_h}")

    # --- Force square pixel aspect ratio (SAR 1:1) ---
    # Without this, the filter chain can produce clips with weird SARs
    # (e.g. 154880:154791) inherited from source footage aspect transforms.
    # All clips must have matching SAR for the final concat + compose to work.
    filters.append("setsar=1")

    # --- Crossfade: fade from black at clip start ---
    # Replaces MoviePy's vfx.CrossFadeIn — smooth transition from pure black
    if crossfade_dur > 0:
        filters.append(f"fade=t=in:st=0:d={crossfade_dur}")

    # --- LUT color grading: apply the pre-computed 3D lookup table ---
    # The .cube file encodes the exact same color math as the 7-step Python
    # grading pipeline, but ffmpeg's lut3d runs at native C speed
    lut_ffmpeg = lut_path.replace('\\', '/').replace(':', '\\:')
    filters.append(f"lut3d=file='{lut_ffmpeg}'")

    # --- Combine filter chain + vignette blend into filter_complex ---
    # [0:v] = source video → all filters → [graded]
    # [graded] + [1:v] (vignette PNG, looped) → multiply blend → output
    vf_chain = ",".join(filters)
    filter_complex = (
        f"[0:v]{vf_chain}[graded];"
        f"[graded][1:v]blend=all_mode=multiply:shortest=1"
    )

    # --- Build the full ffmpeg command ---
    cmd = [ffmpeg_exe, "-y"]

    # --- Loop the source input if it's shorter than what we need ---
    # -stream_loop -1 = infinite loop; -t on output trims to exact duration
    if loop_source:
        cmd += ["-stream_loop", "-1"]

    cmd += ["-i", source_path]
    # --- Vignette mask input: looped PNG blended with graded video ---
    cmd += ["-loop", "1", "-i", vignette_path]
    cmd += ["-filter_complex", filter_complex]
    cmd += [
        "-t", str(needed_dur),           # trim output to exact needed duration
        "-r", str(profile["fps"]),       # force consistent frame rate across all clips
        "-c:v", "libx264",               # h264 encoding
        "-preset", "ultrafast",          # fastest encode — still good quality at this bitrate
        "-b:v", profile["bitrate"],      # target bitrate from format profile
        "-pix_fmt", "yuv420p",           # CRITICAL: force standard pixel format
        "-an",                            # no audio in individual base clips
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(
            f"[ASSEMBLER] ffmpeg full clip failed (exit {result.returncode}): "
            f"{result.stderr[-500:] if result.stderr else 'no stderr'}"
        )


def create_base_video(visual_timeline, total_duration, profile, script_segments=None, work_dir=None):
    """
    # Creates the base video by processing all clips through PURE FFMPEG.
    # Zero MoviePy frame processing — everything runs in native C.
    #
    # Per-clip pipeline (single ffmpeg command via _ffmpeg_full_clip):
    #   1. Resize + center crop to target resolution (lanczos)
    #   2. Ken Burns zoom animation (time-based ffmpeg crop expressions)
    #   3. Crossfade / fade from black (ffmpeg fade filter)
    #   4. 3D LUT color grading (pre-computed lookup table)
    #   5. Vignette mask blend (multiply with edge-darkening PNG)
    #
    # Speed: ~2-5s per clip (was ~40s with MoviePy two-pass approach).
    # For a 25-clip video: ~2 min vs ~18 min. Cached re-runs: ~1 min.
    #
    # All graded clips are concatenated via ffmpeg concat demuxer.
    # Every intermediate is cached — retries skip already-processed clips.
    """
    import subprocess
    from color_grading import prepare_lut_assets
    import imageio_ffmpeg

    # --- Use topic-specific work_dir for caching, fall back to shared dir ---
    if work_dir:
        temp_clip_dir = os.path.join(work_dir, "graded_clips")
    else:
        temp_clip_dir = os.path.join(config.TEMP_DIR, "_graded_clips")
    os.makedirs(temp_clip_dir, exist_ok=True)

    # --- Check for cached base video (skip everything if it exists) ---
    base_path = os.path.join(temp_clip_dir, "base_video.mp4")
    if os.path.exists(base_path) and os.path.getsize(base_path) > 100_000:
        try:
            cached_base = VideoFileClip(base_path)
            if abs(cached_base.duration - total_duration) < 2.0:
                print(f"[ASSEMBLER] BASE VIDEO CACHED — reusing {cached_base.duration:.1f}s")
                return cached_base
            cached_base.close()
        except Exception:
            pass

    # --- Generate LUT assets (3 .cube files + 1 vignette PNG) ---
    # These are cached in the graded_clips dir — only created once per format.
    # The 3 LUTs correspond to the 3 adaptive brightness levels:
    #   dark (0.8), medium (1.0), bright (1.2)
    lut_paths, vignette_path = prepare_lut_assets(profile, temp_clip_dir)

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    frame_w = profile["width"]
    frame_h = profile["height"]
    bitrate = profile["bitrate"]

    ken_burns_globally_enabled = profile.get("ken_burns_enabled", False)
    script_segments_ref = script_segments if script_segments else []

    graded_paths = []
    actual_duration = 0.0
    crossfade_duration = profile.get("crossfade_duration", 1.0)

    for idx, entry in enumerate(visual_timeline):
        needed = entry["duration"]
        if needed <= 0:
            continue

        graded_path = os.path.join(temp_clip_dir, f"graded_{idx:03d}.mp4")

        # --- Skip if cached graded clip exists with matching duration ---
        if os.path.exists(graded_path) and os.path.getsize(graded_path) > 10_000:
            try:
                cached_dur = float(subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                     "-of", "csv=p=0", graded_path],
                    capture_output=True, text=True, timeout=10
                ).stdout.strip())
                if abs(cached_dur - needed) < 0.5:
                    print(f"[ASSEMBLER] CACHED clip {idx+1}/{len(visual_timeline)} ({cached_dur:.1f}s)")
                    actual_duration += needed
                    graded_paths.append(graded_path)
                    continue
            except Exception:
                pass

        try:
            clip_source = entry["path"]

            # --- Determine Ken Burns parameters ---
            # ffmpeg handles zoom via animated crop expressions — no Python needed
            kb_params = None
            if ken_burns_globally_enabled and idx < len(script_segments_ref):
                motion_style = script_segments_ref[idx].get("motion_style", "static")
                kb_params = _get_ken_burns_params(motion_style, needed)
                if kb_params:
                    print(f"[ASSEMBLER] Ken Burns: {motion_style} on clip {idx+1}/{len(visual_timeline)}")

            # --- Determine transition type (crossfade or hard cut) ---
            prev_seg = script_segments_ref[idx - 1] if idx > 0 and idx < len(script_segments_ref) + 1 else None
            curr_seg = script_segments_ref[idx] if idx < len(script_segments_ref) else None
            transition_type = _get_transition_type(prev_seg, curr_seg)

            crossfade_dur = 0.0
            if transition_type == "crossfade" and needed > crossfade_duration:
                crossfade_dur = crossfade_duration
                print(f"[ASSEMBLER] Transition: crossfade ({crossfade_duration}s) on clip {idx+1}/{len(visual_timeline)}")
            elif transition_type == "cut":
                print(f"[ASSEMBLER] Transition: cut (hard) on clip {idx+1}/{len(visual_timeline)}")

            # --- Measure brightness via ffmpeg to pick the right LUT ---
            # Reads one 64x64 grayscale frame (~50ms) — no MoviePy needed
            intensity_key = _measure_brightness_ffmpeg(ffmpeg_exe, clip_source)
            lut_file = lut_paths[intensity_key]

            # --- Check if source clip needs looping (shorter than segment) ---
            source_dur = _get_source_duration(clip_source)
            loop_source = source_dur > 0 and source_dur < needed

            # --- SINGLE FFMPEG PASS: resize + crop + kb + fade + LUT + vignette ---
            # Replaces the entire MoviePy pipeline — runs in ~2-5s per clip
            _ffmpeg_full_clip(
                ffmpeg_exe, clip_source, graded_path, profile,
                needed, lut_file, vignette_path,
                kb_params=kb_params, crossfade_dur=crossfade_dur,
                loop_source=loop_source,
            )

            actual_duration += needed
            graded_paths.append(graded_path)
            print(f"[ASSEMBLER] Graded clip {idx+1}/{len(visual_timeline)} [{intensity_key}]")

        except Exception as e:
            # --- Fallback: generate a plain black clip if ffmpeg fails ---
            print(f"[ASSEMBLER] Error on clip {idx}: {e}")
            try:
                subprocess.run([
                    ffmpeg_exe, "-y", "-f", "lavfi",
                    "-i", f"color=c=black:s={frame_w}x{frame_h}:d={needed}:r={profile['fps']}",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-an", graded_path,
                ], capture_output=True, timeout=30)
            except Exception:
                # --- Last resort: numpy black frame via MoviePy ---
                black = np.zeros((frame_h, frame_w, 3), dtype=np.uint8)
                blk = ImageClip(black).with_duration(needed)
                blk.write_videofile(
                    graded_path, fps=profile["fps"], codec="libx264",
                    preset="ultrafast", threads=1,
                    audio=False, logger=None,
                )
                blk.close()
            actual_duration += needed
            graded_paths.append(graded_path)

    # --- Extend if total clip duration is shorter than voiceover ---
    # Uses the last visual clip, looped if needed, with same LUT grading
    if actual_duration < total_duration and graded_paths:
        gap = total_duration - actual_duration
        filler_path = os.path.join(temp_clip_dir, "graded_filler.mp4")

        # --- Check filler cache ---
        need_filler = True
        if os.path.exists(filler_path) and os.path.getsize(filler_path) > 10_000:
            try:
                cached_dur = float(subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                     "-of", "csv=p=0", filler_path],
                    capture_output=True, text=True, timeout=10
                ).stdout.strip())
                if abs(cached_dur - gap) < 0.5:
                    print(f"[ASSEMBLER] CACHED filler ({cached_dur:.1f}s)")
                    need_filler = False
            except Exception:
                pass

        if need_filler:
            print(f"[ASSEMBLER] Extending last clip by {gap:.1f}s to fill duration")
            last_path = visual_timeline[-1]["path"]

            # --- Same pure-ffmpeg approach for the filler clip ---
            intensity_key = _measure_brightness_ffmpeg(ffmpeg_exe, last_path)
            lut_file = lut_paths[intensity_key]

            # --- Check if the last source clip needs looping to fill the gap ---
            source_dur = _get_source_duration(last_path)
            loop_source = source_dur > 0 and source_dur < gap

            _ffmpeg_full_clip(
                ffmpeg_exe, last_path, filler_path, profile,
                gap, lut_file, vignette_path,
                kb_params=None, crossfade_dur=0.0,
                loop_source=loop_source,
            )

        graded_paths.append(filler_path)

    # --- Concatenate via ffmpeg ---
    concat_list = os.path.join(temp_clip_dir, "concat_list.txt")
    with open(concat_list, "w") as f:
        for p in graded_paths:
            f.write(f"file '{p.replace(os.sep, '/')}'\n")

    subprocess.run([
        ffmpeg_exe, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list, "-c", "copy", base_path,
    ], capture_output=True)

    return VideoFileClip(base_path)


def fit_to_vertical(clip):
    """
    # Resizes and crops a clip to 1080x1920 (9:16 portrait)
    # If clip is landscape, we crop the center
    # If clip is portrait, we just resize
    """

    target_w = config.VIDEO_WIDTH   # 1080
    target_h = config.VIDEO_HEIGHT  # 1920
    target_ratio = target_w / target_h  # 0.5625

    clip_w, clip_h = clip.size
    clip_ratio = clip_w / clip_h

    if clip_ratio > target_ratio:
        # Clip is wider than needed (landscape) -> crop sides
        new_h = target_h
        new_w = int(clip_w * (target_h / clip_h))
        clip = clip.resized(height=new_h)
        # Crop center
        x_center = new_w // 2
        x1 = x_center - target_w // 2
        clip = clip.cropped(x1=x1, y1=0, x2=x1 + target_w, y2=target_h)
    else:
        # Clip is taller or matches -> crop top/bottom
        new_w = target_w
        new_h = int(clip_h * (target_w / clip_w))
        clip = clip.resized(width=new_w)
        # Crop center vertically
        y_center = new_h // 2
        y1 = y_center - target_h // 2
        y1 = max(0, y1)
        clip = clip.cropped(x1=0, y1=y1, x2=target_w, y2=y1 + target_h)

    return clip


def fit_to_horizontal(clip, profile):
    """
    # Resizes and crops a clip to 1920x1080 (16:9 landscape)
    # Landscape footage fills perfectly; portrait is center-cropped
    """
    target_w = profile["width"]    # 1920
    target_h = profile["height"]   # 1080
    target_ratio = target_w / target_h  # 1.7778

    clip_w, clip_h = clip.size
    clip_ratio = clip_w / clip_h

    if clip_ratio > target_ratio:
        # Clip is wider than needed -> crop sides
        new_h = target_h
        new_w = int(clip_w * (target_h / clip_h))
        clip = clip.resized(height=new_h)
        x_center = new_w // 2
        x1 = x_center - target_w // 2
        clip = clip.cropped(x1=x1, y1=0, x2=x1 + target_w, y2=target_h)
    else:
        # Clip is taller or matches -> crop top/bottom
        new_w = target_w
        new_h = int(clip_h * (target_w / clip_w))
        clip = clip.resized(width=new_w)
        y_center = new_h // 2
        y1 = y_center - target_h // 2
        y1 = max(0, y1)
        clip = clip.cropped(x1=0, y1=y1, x2=target_w, y2=y1 + target_h)

    return clip


def fit_clip(clip, profile):
    """
    # Routes to the correct fit function based on format profile
    """
    if profile["width"] > profile["height"]:
        return fit_to_horizontal(clip, profile)
    else:
        return fit_to_vertical(clip)


def create_caption_overlay(caption_events, total_duration, profile=None):
    """
    # Creates transparent caption overlay clips
    """
    frame_w = profile["width"] if profile else config.VIDEO_WIDTH
    frame_h = profile["height"] if profile else config.VIDEO_HEIGHT

    caption_clips = []
    for event in caption_events:
        caption_frame = render_caption_frame(
            event["text"],
            event.get("highlight_word"),
            frame_w,
            frame_h,
            font_size=profile["caption_font_size"] if profile else None,
            position_y=profile["caption_position_y"] if profile else None,
            stroke_width=profile["caption_stroke_width"] if profile else None,
        )
        caption_clip = (
            ImageClip(caption_frame)
            .with_duration(event["end"] - event["start"])
            .with_start(event["start"])
        )
        caption_clips.append(caption_clip)

    return caption_clips


def _get_transition_type(prev_segment, current_segment):
    """
    # Determines what kind of transition to use between two consecutive clips.
    # Returns "crossfade" (smooth blend) or "cut" (instant switch).
    #
    # Priority order — first matching rule wins:
    #   1. Explicit "transition" field on current_segment → use it directly
    #   2. First segment (prev_segment is None) → crossfade for a clean open
    #   3. Mood changed between segments → crossfade (signals emotional shift)
    #   4. Same mood continues → hard cut (keeps momentum / energy flowing)
    #
    # Args:
    #   prev_segment    — dict with "mood" and optional "transition" keys,
    #                     or None if current_segment is the very first clip
    #   current_segment — dict with "mood" and optional "transition" keys
    #
    # Returns: "crossfade" | "cut"
    """

    # --- First segment: always crossfade for a professional clean open ---
    # Avoids a hard cut from pure black at the very start of the video
    if prev_segment is None:
        return "crossfade"

    # --- Explicit override: script generator can force a specific transition ---
    # Supports "crossfade" or "cut" in the segment's "transition" field
    explicit = current_segment.get("transition") if current_segment else None
    if explicit in ("crossfade", "cut"):
        return explicit

    # --- Heuristic: compare mood of adjacent segments ---
    # A mood change signals a tonal shift → use crossfade to smooth it
    # Same mood continuing → hard cut preserves the clip energy / pace
    prev_mood = prev_segment.get("mood", "")
    curr_mood = current_segment.get("mood", "") if current_segment else ""

    if prev_mood != curr_mood:
        # Emotional shift between segments → blend with a crossfade
        return "crossfade"
    else:
        # Same emotional energy continues → snap hard cut keeps momentum
        return "cut"


def _get_ken_burns_params(motion_style, duration):
    """
    # Returns a dict of motion parameters for the given motion_style,
    # or None if the clip should be static (no motion effect).
    #
    # Called once per clip — cheap, no VideoClip work happens here.
    #
    # Supported styles:
    #   "ken_burns_zoom"  — slow push-in: scales 1.0x → 1.12x over the clip
    #   "ken_burns_pan"   — slow horizontal drift: 5% pan, constant scale
    #   "slow_zoom_out"   — pull-back: scales 1.12x → 1.0x over the clip
    #   "static" / None   — no motion; returns None so caller skips processing
    #
    # The 1.12x overscan is enough to cover the full crop window travel
    # without ever showing blank/black edges.
    #
    # Parameters returned:
    #   start_scale — clip scale at t=0  (relative to target output size)
    #   end_scale   — clip scale at t=duration
    #   pan_x       — fractional horizontal drift from center (0 = no drift)
    #   pan_y       — fractional vertical drift from center  (0 = no drift)
    """

    # --- Static or unknown style → no motion ---
    if not motion_style or motion_style == "static":
        return None

    if motion_style == "ken_burns_zoom":
        # --- Slow zoom IN: start native, end 12% larger ---
        # Creates a subtle "push-in" that adds energy to a clip
        return {
            "start_scale": 1.0,    # native size at start
            "end_scale": 1.12,     # 12% larger at end — enough to see motion
            "pan_x": 0.0,          # no horizontal drift on a pure zoom
            "pan_y": 0.0,          # no vertical drift
        }

    elif motion_style == "ken_burns_pan":
        # --- Horizontal pan: constant scale, 5% drift left-to-right ---
        # Creates a slow slide; works great on wide landscape footage
        return {
            "start_scale": 1.0,    # constant scale throughout
            "end_scale": 1.0,      # no zoom, pure horizontal motion
            "pan_x": 0.05,         # 5% of clip width as horizontal travel
            "pan_y": 0.0,          # no vertical drift
        }

    elif motion_style == "slow_zoom_out":
        # --- Pull-back / reveal: starts zoomed in, eases out to native ---
        # Opposite of ken_burns_zoom; good for opening-style shots
        return {
            "start_scale": 1.12,   # start 12% larger (zoomed in)
            "end_scale": 1.0,      # pull back to native size
            "pan_x": 0.0,          # no horizontal drift
            "pan_y": 0.0,          # no vertical drift
        }

    else:
        # --- Unknown style → treat as static, no crash ---
        return None


def _apply_ken_burns(clip, params, target_w, target_h):
    """
    # Applies Ken Burns motion to a MoviePy VideoClip.
    #
    # How it works:
    #   1. The clip is resized to a slightly LARGER canvas (the overscan)
    #      so the crop window always has pixels to draw from at every frame.
    #   2. A crop window of (target_w, target_h) pixels moves over the
    #      oversized canvas as time progresses — this creates the motion.
    #   3. Each cropped frame is PIL-resized back to (target_w, target_h)
    #      to guarantee pixel-perfect output dimensions.
    #
    # The crop_at_time function is passed to clip.transform(), which
    # calls it for every frame with (get_frame, t) — MoviePy 2.x API.
    #
    # Args:
    #   clip      — MoviePy VideoClip already sized to (target_w, target_h)
    #   params    — dict from _get_ken_burns_params(); None → return unchanged
    #   target_w  — output width in pixels  (e.g. 1080)
    #   target_h  — output height in pixels (e.g. 1920)
    #
    # Returns: new VideoClip with motion baked in
    """

    # --- params=None means static; skip all processing ---
    if params is None:
        return clip

    duration = clip.duration
    start_scale = params["start_scale"]
    end_scale = params["end_scale"]
    pan_x = params["pan_x"]
    # pan_y available but not used in current styles (always 0.0)

    # --- Oversize the clip to the maximum scale needed ---
    # If end_scale=1.12 the clip needs to be 12% bigger than target
    # so we never crop outside the available pixels.
    max_scale = max(start_scale, end_scale)
    oversized_w = int(target_w * max_scale)
    oversized_h = int(target_h * max_scale)

    # Resize clip to the oversized canvas; this is a cheap scalar operation
    clip = clip.resized((oversized_w, oversized_h))

    def crop_at_time(get_frame, t):
        """
        # Per-frame crop function injected into MoviePy's transform pipeline.
        # Called with (get_frame callable, t float) — MoviePy 2.x signature.
        #
        # At each time t:
        #   1. Read the oversized frame via get_frame(t)
        #   2. Compute current progress (0.0 → 1.0)
        #   3. Determine crop window size based on current zoom level
        #   4. Determine crop window center based on pan offset
        #   5. Clamp window to frame boundaries (prevents IndexError)
        #   6. Crop the numpy array slice
        #   7. PIL-resize back to (target_w, target_h) — LANCZOS quality
        """
        # --- Get the raw oversized frame ---
        frame = get_frame(t)
        h, w = frame.shape[:2]

        # --- Normalised progress: 0.0 at clip start, 1.0 at clip end ---
        progress = t / duration if duration > 0 else 0.0

        # --- Interpolate scale linearly between start and end ---
        current_scale = start_scale + (end_scale - start_scale) * progress

        # --- Size of the crop window in pixels ---
        # A larger current_scale means we've zoomed in → crop window shrinks
        # A smaller current_scale means we've zoomed out → crop window grows
        # Division by current_scale maps the zoom level to window size.
        crop_w = int(target_w * (max_scale / current_scale))
        crop_h = int(target_h * (max_scale / current_scale))

        # --- Crop center: oversized canvas center + pan offset ---
        # pan_x is a fraction of w; (progress - 0.5) makes it drift
        # from -0.5*pan to +0.5*pan across the clip duration, centered.
        cx = w // 2 + int(w * pan_x * (progress - 0.5))
        cy = h // 2   # vertical center (no vertical pan in current styles)

        # --- Calculate crop rectangle, clamped to frame boundaries ---
        x1 = max(0, cx - crop_w // 2)
        y1 = max(0, cy - crop_h // 2)
        x2 = min(w, x1 + crop_w)
        y2 = min(h, y1 + crop_h)

        # --- Slice numpy array to get the crop ---
        cropped = frame[y1:y2, x1:x2]

        # --- Resize back to exact output dimensions using PIL LANCZOS ---
        # PIL LANCZOS gives cinema-quality downscaling (better than nearest/bilinear)
        from PIL import Image
        img = Image.fromarray(cropped)
        img = img.resize((target_w, target_h), Image.LANCZOS)

        # Convert back to numpy for MoviePy to use as a frame
        return np.array(img)

    # --- Wrap the clip so every frame goes through crop_at_time ---
    # MoviePy 2.x transform(func) where func is (get_frame, t) → frame
    return clip.transform(crop_at_time)


def create_logo_outro(profile=None):
    """
    # Creates the logo outro clip sized to match the current format
    """

    if not os.path.exists(config.LOGO_PATH):
        print("[ASSEMBLER] WARNING: Logo not found, skipping outro")
        return None

    if profile is None:
        frame_w = config.VIDEO_WIDTH
        frame_h = config.VIDEO_HEIGHT
    else:
        frame_w = profile["width"]
        frame_h = profile["height"]

    logo_img = Image.open(config.LOGO_PATH).convert("RGBA")

    img_ratio = logo_img.width / logo_img.height
    target_ratio = frame_w / frame_h

    if img_ratio > target_ratio:
        new_w = frame_w
        new_h = int(new_w / img_ratio)
    else:
        new_h = frame_h
        new_w = int(new_h * img_ratio)

    logo_img = logo_img.resize((new_w, new_h), Image.LANCZOS)

    bg = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 255))
    x = (frame_w - new_w) // 2
    y = (frame_h - new_h) // 2
    bg.paste(logo_img, (x, y), logo_img)

    logo_array = np.array(bg.convert("RGB"))
    logo_clip = ImageClip(logo_array).with_duration(config.LOGO_DURATION)
    logo_clip = logo_clip.with_effects([vfx.CrossFadeIn(1.0)])

    return logo_clip


def _db_to_linear(db):
    """
    # Converts decibels (dB) to a linear gain multiplier.
    # This is the standard audio formula used in all DAWs and broadcast tools.
    #
    # Formula: linear = 10 ^ (dB / 20)
    #
    # Key values used in this pipeline:
    #   +1.5 dB  →  1.189x  (voiceover clarity boost — slightly louder)
    #    0.0 dB  →  1.000x  (unity gain — no change)
    #   -9.0 dB  →  0.355x  (music level — present but never competing with voice)
    #
    # Why /20 and not /10?
    #   - /20 is for amplitude (voltage/pressure/PCM sample values)
    #   - /10 is for power (watts) — audio software always uses /20
    """
    return 10 ** (db / 20.0)


def mix_audio(voiceover, music_path, voiceover_duration, profile=None):
    """
    # Mixes voiceover with background music using dB-based constant levels.
    # No ducking — music plays at a fixed level throughout (spec §6).
    #
    # Levels pulled from profile (set in Task 1 config):
    #   voiceover_boost_db: +1.5 dB  — adds clarity and authority to the voice
    #   music_level_db:      -9.0 dB  — music supports without overpowering
    #
    # Music also gets a 2s fade-in at the start and 3s fade-out at the end
    # so it doesn't cut in/out abruptly at the video edges.
    #
    # Signature preserved from before: mix_audio(voiceover, music_path,
    #   voiceover_duration, profile=None) -> AudioClip
    """

    # --- Total video duration = voiceover + logo outro ---
    total_duration = voiceover_duration + config.LOGO_DURATION

    # --- Apply voiceover boost ---
    # Pull from profile if provided, otherwise fall back to +1.5 dB default
    vo_boost_db = profile.get("voiceover_boost_db", 1.5) if profile else 1.5
    vo_gain = _db_to_linear(vo_boost_db)
    boosted_voiceover = voiceover.with_volume_scaled(vo_gain)

    # Start with just the boosted voice; music will be appended if available
    audio_layers = [boosted_voiceover]

    if music_path and os.path.exists(music_path):
        try:
            music = AudioFileClip(music_path)

            # --- Loop music if the track is shorter than the video ---
            # e.g. a 60s music file for a 90s video needs to loop 2x
            if music.duration < total_duration:
                loops = int(total_duration / music.duration) + 1
                # MoviePy 2.x: use .looped(n=N) not concatenate_audioclips
                music = music.looped(n=loops)

            # --- Trim to exact video duration ---
            # MoviePy 2.x: use .subclipped(start, end) not .subclip(start, end)
            music = music.subclipped(0, total_duration)

            # --- Apply constant dB level to music ---
            # Pull from profile if provided, otherwise fall back to -9 dB default
            music_db = profile.get("music_level_db", -9) if profile else -9
            music_gain = _db_to_linear(music_db)
            # MoviePy 2.x: use .with_volume_scaled(gain) not .volumex(gain)
            music = music.with_volume_scaled(music_gain)

            print(
                f"[ASSEMBLER] Audio mix: voice {vo_boost_db:+.1f}dB ({vo_gain:.3f}x), "
                f"music {music_db:+.1f}dB ({music_gain:.3f}x) — constant level, no ducking"
            )

            # --- Fade in and out at video edges ---
            # 2s fade-in prevents music from cutting in abruptly at frame 0
            # 3s fade-out gives a natural finish as the logo outro ends
            music = music.with_effects([afx.AudioFadeIn(2.0), afx.AudioFadeOut(3.0)])
            audio_layers.append(music)

        except Exception as e:
            print(f"[ASSEMBLER] Could not load music: {e}")

    # --- Combine layers into a single composite audio clip ---
    if len(audio_layers) > 1:
        return CompositeAudioClip(audio_layers)
    else:
        # No music loaded — return just the boosted voiceover
        return boosted_voiceover


# --- Quick test ---
if __name__ == "__main__":
    print("Video assembler module loaded successfully")
    print(f"Output resolution: {config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}")
    print(f"FPS: {config.VIDEO_FPS}")
    print(f"Music volume: {config.MUSIC_VOLUME*100:.0f}% (voice is {1.0/config.MUSIC_VOLUME:.0f}x louder)")
