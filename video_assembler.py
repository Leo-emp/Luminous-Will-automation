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
# - Background music (low volume)
# - Logo outro
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
    # Each script segment gets one clip, timed to match the voiceover
    visual_timeline = build_visual_timeline(
        clip_paths, caption_events, total_duration
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
    final_audio = mix_audio(voiceover, music_path, total_duration)
    final_video = final_video.with_audio(final_audio)

    # --- Step 8: Export ---
    print(f"[ASSEMBLER] Exporting to: {output_path}")
    final_video.write_videofile(
        output_path,
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="8000k",
        preset="medium",
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


def build_visual_timeline(clip_paths, caption_events, total_duration):
    """
    # Maps each clip to a time range in the video
    # Distributes clips evenly across the voiceover duration
    #
    # Returns: list of {path, start, end, duration}
    """

    num_clips = len(clip_paths)
    if num_clips == 0:
        return []

    # --- Calculate duration per clip ---
    duration_per_clip = total_duration / num_clips

    timeline = []
    for i, path in enumerate(clip_paths):
        start = i * duration_per_clip
        end = (i + 1) * duration_per_clip
        timeline.append({
            "path": path,
            "start": start,
            "end": end,
            "duration": end - start,
        })

    return timeline


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

    # --- Concatenate all clips ---
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
    # Mixes voiceover with background music
    # Voiceover is at full volume, music is very low
    # Music fades in/out and loops to match video length
    """

    # Total duration including logo outro
    total_duration = voiceover_duration + config.LOGO_DURATION

    # --- Start with voiceover ---
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

            # Lower volume significantly so voiceover is clear
            music = music.with_volume_scaled(config.MUSIC_VOLUME)

            # Fade in/out the music
            music = music.audio_fadein(2.0).audio_fadeout(2.0)

            audio_layers.append(music)
            print(f"[ASSEMBLER] Background music added at {config.MUSIC_VOLUME*100:.0f}% volume")

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
