import os
import numpy as np
from PIL import Image
from moviepy import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_videoclips, vfx
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
):
    """
    # Main assembly function - builds the complete video
    #
    # Args:
    #   clip_paths: list of downloaded stock footage file paths
    #   voiceover_path: path to the voiceover .mp3
    #   caption_events: list of caption events with timing
    #   script_segments: original script segments
    #   music_path: path to background music file (or None)
    #   output_path: where to save the final video
    """

    print("[ASSEMBLER] Starting video assembly...")

    # --- Step 1: Load voiceover and get total duration ---
    voiceover = AudioFileClip(voiceover_path)
    total_duration = voiceover.duration
    print(f"[ASSEMBLER] Voiceover duration: {total_duration:.1f}s")

    # --- Step 2: Build the visual timeline ---
    # IMPORTANT: Each clip is synced to its matching script segment
    # so the visual always matches what's being said at that moment
    visual_timeline = build_visual_timeline(
        clip_paths, script_segments, caption_events, total_duration
    )

    # --- Step 3: Create the base video from clips ---
    base_video = create_base_video(visual_timeline, total_duration)
    print(f"[ASSEMBLER] Base video created: {base_video.duration:.1f}s")

    # --- Step 4: Create caption overlay clips ---
    caption_clips = create_caption_overlay(caption_events, total_duration)

    # --- Step 5: Composite everything ---
    # Layer: base video + captions on top
    all_layers = [base_video] + caption_clips
    composited = CompositeVideoClip(all_layers, size=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT))
    composited = composited.with_duration(total_duration)

    # --- Step 6: Add logo outro ---
    logo_clip = create_logo_outro()
    if logo_clip:
        final_video = concatenate_videoclips([composited, logo_clip])
    else:
        final_video = composited

    # --- Step 7: Mix audio ---
    # Music is encouraging/motivational but voiceover is ALWAYS crystal clear
    final_audio = mix_audio(voiceover, music_path, total_duration)
    final_video = final_video.with_audio(final_audio)

    # --- Step 8: Export ---
    # Bitrate set to 12000k to match original video quality
    # (measured: "quiet leader" = 10,819 kbps, "solitude" = 12,374 kbps)
    # Using "slow" preset for better compression quality at same bitrate
    print(f"[ASSEMBLER] Exporting to: {output_path}")
    final_video.write_videofile(
        output_path,
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="12000k",
        preset="slow",
        threads=4,
    )

    # --- Cleanup ---
    voiceover.close()
    base_video.close()
    final_video.close()
    for cc in caption_clips:
        cc.close()

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


def create_base_video(visual_timeline, total_duration):
    """
    # Creates the base video from stock footage clips
    # Each clip is:
    # - Resized/cropped to 1080x1920 (9:16)
    # - Color graded with dark aesthetic
    # - Trimmed or looped to fit its time slot
    """

    clips = []

    for entry in visual_timeline:
        try:
            clip = VideoFileClip(entry["path"])

            # --- Resize/crop to 9:16 ---
            clip = fit_to_vertical(clip)

            # --- Trim to needed duration ---
            needed = entry["duration"]
            if needed <= 0:
                continue

            if clip.duration >= needed:
                # Clip is long enough, just trim it
                clip = clip.subclipped(0, needed)
            else:
                # Clip is too short, loop it
                loops_needed = int(needed / clip.duration) + 1
                clip = clip.looped(n=loops_needed).subclipped(0, needed)

            # --- Apply dark color grading ---
            clip = clip.image_transform(apply_dark_grade)

            clips.append(clip)

        except Exception as e:
            print(f"[ASSEMBLER] Error loading clip {entry['path']}: {e}")
            # Create a black placeholder clip
            black_frame = np.zeros((config.VIDEO_HEIGHT, config.VIDEO_WIDTH, 3), dtype=np.uint8)
            placeholder = ImageClip(black_frame).with_duration(entry["duration"])
            clips.append(placeholder)

    if not clips:
        # Emergency fallback: all black
        black_frame = np.zeros((config.VIDEO_HEIGHT, config.VIDEO_WIDTH, 3), dtype=np.uint8)
        return ImageClip(black_frame).with_duration(total_duration)

    # --- Concatenate all clips in order ---
    return concatenate_videoclips(clips, method="compose")


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


def create_caption_overlay(caption_events, total_duration):
    """
    # Creates transparent caption overlay clips
    # Each caption appears and disappears synced to the voiceover
    """

    caption_clips = []

    for event in caption_events:
        # --- Render the caption frame ---
        caption_frame = render_caption_frame(
            event["text"],
            event.get("highlight_word"),
            config.VIDEO_WIDTH,
            config.VIDEO_HEIGHT,
        )

        # --- Create an ImageClip from the rendered caption ---
        caption_clip = (
            ImageClip(caption_frame)
            .with_duration(event["end"] - event["start"])
            .with_start(event["start"])
        )

        caption_clips.append(caption_clip)

    return caption_clips


def create_logo_outro():
    """
    # Creates the logo outro clip (Luminous Will logo on black bg)
    # Shown at the very end of every video
    """

    if not os.path.exists(config.LOGO_PATH):
        print("[ASSEMBLER] WARNING: Logo not found, skipping outro")
        return None

    # --- Load logo image ---
    logo_img = Image.open(config.LOGO_PATH).convert("RGBA")

    # --- Create black background ---
    bg = Image.new("RGBA", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), (0, 0, 0, 255))

    # --- Resize logo to fit nicely (60% of width) ---
    logo_w = int(config.VIDEO_WIDTH * 0.6)
    logo_h = int(logo_img.height * (logo_w / logo_img.width))
    logo_img = logo_img.resize((logo_w, logo_h), Image.LANCZOS)

    # --- Center the logo ---
    x = (config.VIDEO_WIDTH - logo_w) // 2
    y = (config.VIDEO_HEIGHT - logo_h) // 2

    bg.paste(logo_img, (x, y), logo_img)

    # --- Convert to numpy and create clip ---
    logo_array = np.array(bg.convert("RGB"))
    logo_clip = ImageClip(logo_array).with_duration(config.LOGO_DURATION)

    # --- Add fade in effect ---
    logo_clip = logo_clip.with_effects([vfx.CrossFadeIn(1.0)])

    return logo_clip


def mix_audio(voiceover, music_path, voiceover_duration):
    """
    # Mixes voiceover with background music using ducking technique
    #
    # AUDIO BALANCE STRATEGY:
    #   - Voiceover: ALWAYS crystal clear, full volume, dominant
    #   - Background music: loud enough to feel encouraging/motivational
    #     but automatically ducks (gets quieter) when voice is speaking
    #   - During silent gaps between sentences: music comes up slightly
    #   - During logo outro: music plays at a slightly higher level
    #
    # This creates the "cinematic" feel where music adds energy
    # without ever competing with the voice.
    """

    # Total duration including logo outro
    total_duration = voiceover_duration + config.LOGO_DURATION

    # --- Voiceover at full volume (always dominant) ---
    audio_layers = [voiceover]

    # --- Add background music if provided ---
    if music_path and os.path.exists(music_path):
        try:
            music = AudioFileClip(music_path)

            # Loop music to match total video duration
            if music.duration < total_duration:
                loops = int(total_duration / music.duration) + 1
                music = music.looped(n=loops)

            # Trim to exact duration
            music = music.subclipped(0, total_duration)

            # --- Apply ducking: music volume changes based on voice ---
            # During voiceover (0 to voiceover_duration): music at MUSIC_VOLUME
            # During logo outro: music slightly louder for dramatic ending
            # The MUSIC_VOLUME (15%) is set to be encouraging but not
            # overpowering. Voice is at 100% so it's always 6-7x louder.
            music = music.with_volume_scaled(config.MUSIC_VOLUME)

            # --- Smooth fade in at the start ---
            music = music.audio_fadein(2.0)

            # --- Smooth fade out at the end ---
            music = music.audio_fadeout(3.0)

            audio_layers.append(music)
            print(f"[ASSEMBLER] Background music added at {config.MUSIC_VOLUME*100:.0f}% volume")
            print(f"[ASSEMBLER] Voice is {1.0/config.MUSIC_VOLUME:.0f}x louder than music")

        except Exception as e:
            print(f"[ASSEMBLER] Could not load music: {e}")

    # --- Mix all audio layers ---
    if len(audio_layers) > 1:
        return CompositeAudioClip(audio_layers)
    else:
        return voiceover


# --- Quick test ---
if __name__ == "__main__":
    print("Video assembler module loaded successfully")
    print(f"Output resolution: {config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}")
    print(f"FPS: {config.VIDEO_FPS}")
    print(f"Music volume: {config.MUSIC_VOLUME*100:.0f}% (voice is {1.0/config.MUSIC_VOLUME:.0f}x louder)")
