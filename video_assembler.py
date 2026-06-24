import os
import numpy as np
from PIL import Image
from moviepy import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_videoclips, vfx, afx
)
import config
from color_grading import apply_dark_grade
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
):
    """
    # Main assembly function - builds the complete video
    # Format-aware: uses profile settings for resolution, bitrate,
    # transitions, and music mixing mode.
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

    # --- Step 3: Create base video ---
    # Pass script_segments so create_base_video can look up motion_style
    # for each clip's matching segment (Ken Burns per-segment control)
    base_video = create_base_video(visual_timeline, total_duration, profile, script_segments)
    print(f"[ASSEMBLER] Base video created: {base_video.duration:.1f}s")

    # --- Step 4: Burn captions on-the-fly ---
    print(f"[ASSEMBLER] {len(caption_events)} captions will be burned on-the-fly")
    _caption_render_cache = {}
    frame_w = profile["width"]
    frame_h = profile["height"]

    def burn_captions(get_frame, t):
        # --- Get the base video frame at time t ---
        frame = get_frame(t)
        for i, event in enumerate(caption_events):
            if event["start"] <= t < event["end"]:
                # --- Time-aware cache key: bucket time to ~80ms for animation ---
                # int(t * 12.5) gives us one cache slot per 0.08s (= REVEAL_DURATION)
                # This means we re-render at most 12.5 times per second — enough
                # for smooth word-reveal animation without excessive CPU cost.
                cache_key = (i, int(t * 12.5))
                if cache_key not in _caption_render_cache:
                    # Clear stale entries to prevent unbounded cache growth
                    _caption_render_cache.clear()
                    # --- Render caption with per-word timing info ---
                    # words=event.get("words") passes individual word timestamps
                    # current_time=t lets the renderer decide which words are visible
                    rgba = render_caption_frame(
                        event["text"],
                        event.get("highlight_word"),
                        frame_w,
                        frame_h,
                        font_size=profile["caption_font_size"],
                        position_y=profile["caption_position_y"],
                        stroke_width=profile["caption_stroke_width"],
                        words=event.get("words"),       # per-word timing for animation
                        current_time=t,                 # current playback time
                    )
                    # Pre-compute alpha and RGB for compositing
                    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
                    rgb = rgba[:, :, :3].astype(np.float32)
                    _caption_render_cache[cache_key] = (alpha, rgb)
                a, rgb = _caption_render_cache[cache_key]
                # --- Alpha composite caption over video frame ---
                # result = frame * (1 - alpha) + caption_rgb * alpha
                result = frame.astype(np.float32)
                result = result * (1.0 - a) + rgb * a
                return result.astype(np.uint8)
        return frame

    composited = base_video.transform(burn_captions)
    composited = composited.with_duration(total_duration)

    # --- Step 5: Add logo outro ---
    logo_clip = create_logo_outro(profile)
    if logo_clip:
        final_video = concatenate_videoclips([composited, logo_clip], method="chain")
    else:
        final_video = composited

    # --- Step 6: Mix audio ---
    final_audio = mix_audio(voiceover, music_path, total_duration, profile)
    final_video = final_video.with_audio(final_audio)

    # --- Step 7: Export ---
    print(f"[ASSEMBLER] Exporting final video to: {output_path}")
    final_video.write_videofile(
        output_path,
        fps=profile["fps"],
        codec="libx264",
        audio_codec="aac",
        bitrate=profile["bitrate"],
        preset="slow",
        threads=4,
    )

    # --- Cleanup ---
    voiceover.close()
    base_video.close()
    final_video.close()

    print(f"[ASSEMBLER] Video exported successfully: {output_path}")
    return output_path


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


def create_base_video(visual_timeline, total_duration, profile, script_segments=None):
    """
    # Creates the base video processing clips one at a time.
    # Uses profile for resolution, bitrate, color grading, and transitions.
    #
    # script_segments (optional): list of script segment dicts, each may have
    #   a "motion_style" field ("ken_burns_zoom", "ken_burns_pan",
    #   "slow_zoom_out", "static", or absent → treated as "static").
    #   Used to apply Ken Burns per-clip when profile["ken_burns_enabled"] = True.
    """
    import subprocess
    from color_grading import create_grader

    temp_clip_dir = os.path.join(config.TEMP_DIR, "_graded_clips")
    os.makedirs(temp_clip_dir, exist_ok=True)

    grader = create_grader(profile)
    frame_w = profile["width"]
    frame_h = profile["height"]
    bitrate = profile["bitrate"]

    # --- Determine whether Ken Burns is globally enabled ---
    # The profile flag is the master switch; individual segments can still
    # be "static" which means no motion for that specific clip.
    ken_burns_globally_enabled = profile.get("ken_burns_enabled", False)

    # --- Normalise script_segments to an empty list if not provided ---
    # This keeps the rest of the loop safe with a simple index check.
    script_segments_ref = script_segments if script_segments else []

    graded_paths = []
    actual_duration = 0.0

    # --- Pull crossfade duration from profile (default: 1.0s) ---
    # Used when _get_transition_type returns "crossfade" for a clip
    crossfade_duration = profile.get("crossfade_duration", 1.0)

    for idx, entry in enumerate(visual_timeline):
        needed = entry["duration"]
        if needed <= 0:
            continue

        graded_path = os.path.join(temp_clip_dir, f"graded_{idx:03d}.mp4")
        try:
            clip = VideoFileClip(entry["path"])
            clip = fit_clip(clip, profile)

            if clip.duration >= needed:
                clip = clip.subclipped(0, needed)
            else:
                loops_needed = int(needed / clip.duration) + 1
                clip = concatenate_videoclips([clip] * loops_needed, method="chain")
                clip = clip.subclipped(0, needed)

            # --- Apply Ken Burns motion (if enabled and segment has motion_style) ---
            # Runs AFTER fit_clip (so the clip is already the right size),
            # BEFORE color grading (so we grade the final cropped output).
            #
            # Process:
            #   1. Look up this segment's motion_style (defaults to "static")
            #   2. _get_ken_burns_params returns None for static → skip
            #   3. _apply_ken_burns wraps the clip with a per-frame transform
            if ken_burns_globally_enabled and idx < len(script_segments_ref):
                # Fetch the motion_style for this segment (default: "static")
                motion_style = script_segments_ref[idx].get("motion_style", "static")
                kb_params = _get_ken_burns_params(motion_style, needed)
                if kb_params:
                    # Motion requested — apply the Ken Burns transform
                    clip = _apply_ken_burns(clip, kb_params, frame_w, frame_h)
                    print(f"[ASSEMBLER] Ken Burns: {motion_style} on clip {idx+1}/{len(visual_timeline)}")
                # If kb_params is None (static), no transform is applied

            # --- Apply context-aware transition to start of this clip ---
            # Look up previous segment (None for the first clip) and determine
            # whether to fade in from black (crossfade) or start instantly (cut).
            #
            # _get_transition_type priority:
            #   1. Explicit "transition" field on this segment
            #   2. First clip (idx == 0) → always crossfade for clean open
            #   3. Mood change vs previous segment → crossfade
            #   4. Same mood → hard cut
            prev_seg = script_segments_ref[idx - 1] if idx > 0 and idx < len(script_segments_ref) + 1 else None
            curr_seg = script_segments_ref[idx] if idx < len(script_segments_ref) else None

            transition_type = _get_transition_type(prev_seg, curr_seg)

            if transition_type == "crossfade" and clip.duration > crossfade_duration:
                # --- Apply a fade-in from black at the start of this clip ---
                # CrossFadeIn creates a smooth dissolve from black over `crossfade_duration`
                # seconds — the standard approach when each clip is written individually.
                # For a true between-clip blend you'd need CompositeVideoClip; for the
                # single-file-per-clip pipeline, CrossFadeIn (fade from black) is the
                # correct and efficient approach.
                clip = clip.with_effects([vfx.CrossFadeIn(crossfade_duration)])
                print(f"[ASSEMBLER] Transition: crossfade ({crossfade_duration}s) on clip {idx+1}/{len(visual_timeline)}")
            else:
                # Hard cut: no effect applied — clip starts at full opacity instantly
                if transition_type == "cut":
                    print(f"[ASSEMBLER] Transition: cut (hard) on clip {idx+1}/{len(visual_timeline)}")

            clip = clip.image_transform(grader)

            clip.write_videofile(
                graded_path, fps=profile["fps"], codec="libx264",
                bitrate=bitrate, preset="fast", threads=2,
                audio=False, logger=None,
            )
            clip.close()
            del clip
            actual_duration += needed
            graded_paths.append(graded_path)
            print(f"[ASSEMBLER] Graded clip {idx+1}/{len(visual_timeline)}")

        except Exception as e:
            print(f"[ASSEMBLER] Error on clip {idx}: {e}")
            black = np.zeros((frame_h, frame_w, 3), dtype=np.uint8)
            blk = ImageClip(black).with_duration(needed)
            blk.write_videofile(
                graded_path, fps=profile["fps"], codec="libx264",
                audio=False, logger=None,
            )
            blk.close()
            actual_duration += needed
            graded_paths.append(graded_path)

    # --- Extend if too short ---
    if actual_duration < total_duration and graded_paths:
        gap = total_duration - actual_duration
        print(f"[ASSEMBLER] Extending last clip by {gap:.1f}s to fill duration")
        last_path = visual_timeline[-1]["path"]
        filler_path = os.path.join(temp_clip_dir, "graded_filler.mp4")
        clip = VideoFileClip(last_path)
        clip = fit_clip(clip, profile)
        if clip.duration < gap:
            clip = concatenate_videoclips([clip] * (int(gap / clip.duration) + 1), method="chain")
        clip = clip.subclipped(0, gap)
        clip = clip.image_transform(grader)
        clip.write_videofile(
            filler_path, fps=profile["fps"], codec="libx264",
            bitrate=bitrate, preset="fast", threads=2,
            audio=False, logger=None,
        )
        clip.close()
        graded_paths.append(filler_path)

    # --- Concatenate via ffmpeg ---
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    concat_list = os.path.join(temp_clip_dir, "concat_list.txt")
    with open(concat_list, "w") as f:
        for p in graded_paths:
            f.write(f"file '{p.replace(os.sep, '/')}'\n")

    base_path = os.path.join(temp_clip_dir, "base_video.mp4")
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
