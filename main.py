import os
import sys
import shutil
import time
import config
from script_generator import generate_script, get_script_text
from voiceover import generate_voiceover, get_audio_duration
from visuals import search_and_download_videos
from captions import create_caption_clips
from video_assembler import assemble_video

# ============================================================
# LUMINOUS WILL - AUTOMATED VIDEO PIPELINE
# ============================================================
# Creates dark aesthetic motivational videos automatically:
#   1. Generate script with punchy hook
#   2. Generate voiceover (ElevenLabs - Adam voice)
#   3. Download matching stock footage (Pexels)
#   4. Build word-synced captions
#   5. Assemble final video with color grading + music + logo
#
# Usage:
#   python main.py                          -> random trending topic
#   python main.py "your topic here"        -> specific topic
#   python main.py --list                   -> list trending topics
# ============================================================


def validate_setup():
    """
    # Checks that all required API keys and files are present
    # before starting the pipeline
    """

    errors = []

    # --- Check API keys ---
    if not config.ELEVENLABS_API_KEY or config.ELEVENLABS_API_KEY == "your_elevenlabs_api_key_here":
        errors.append("ELEVENLABS_API_KEY not set in .env file")

    if not config.PEXELS_API_KEY or config.PEXELS_API_KEY == "your_pexels_api_key_here":
        errors.append("PEXELS_API_KEY not set in .env file")

    # --- Check logo file ---
    if not os.path.exists(config.LOGO_PATH):
        errors.append(f"Logo file not found at: {config.LOGO_PATH}")

    # --- Check directories ---
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.TEMP_DIR, exist_ok=True)

    if errors:
        print("\n[SETUP ERROR] Fix the following before running:\n")
        for e in errors:
            print(f"  - {e}")
        print(f"\n  Edit your .env file at: {os.path.join(config.BASE_DIR, '.env')}")
        return False

    return True


def find_background_music():
    """
    # Looks for a background music file in the assets/music folder
    # Returns the path to the first .mp3 or .wav found, or None
    """

    if not os.path.exists(config.MUSIC_DIR):
        return None

    for f in os.listdir(config.MUSIC_DIR):
        if f.endswith((".mp3", ".wav", ".m4a")):
            return os.path.join(config.MUSIC_DIR, f)

    return None


def run_pipeline(topic=None):
    """
    # Main pipeline: runs all steps in sequence
    # Creates one complete video from start to finish
    """

    start_time = time.time()
    print("\n" + "=" * 60)
    print("  LUMINOUS WILL - VIDEO PIPELINE")
    print("=" * 60)

    # =====================================================
    # STEP 1: VALIDATE SETUP
    # =====================================================
    print("\n[STEP 1/6] Validating setup...")
    if not validate_setup():
        return None

    # =====================================================
    # STEP 2: GENERATE SCRIPT
    # =====================================================
    print("\n[STEP 2/6] Generating script...")
    script_segments, topic = generate_script(topic)
    full_script = get_script_text(script_segments)
    print(f"[SCRIPT] Topic: {topic}")
    print(f"[SCRIPT] Segments: {len(script_segments)}")
    print(f"[SCRIPT] Full text:\n  {full_script[:200]}...")

    # --- Create a unique output name based on topic ---
    safe_topic = topic.replace(" ", "_").replace("'", "")[:50]
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_name = f"{safe_topic}_{timestamp}"

    # --- Create temp directory for this video ---
    video_temp = os.path.join(config.TEMP_DIR, video_name)
    os.makedirs(video_temp, exist_ok=True)

    # =====================================================
    # STEP 3: GENERATE VOICEOVER
    # =====================================================
    print("\n[STEP 3/6] Generating voiceover...")
    voiceover_path = os.path.join(video_temp, "voiceover.mp3")
    word_timestamps = generate_voiceover(full_script, voiceover_path)
    audio_duration = get_audio_duration(voiceover_path)
    print(f"[VOICEOVER] Duration: {audio_duration:.1f}s")

    # =====================================================
    # STEP 4: DOWNLOAD STOCK FOOTAGE
    # =====================================================
    print("\n[STEP 4/6] Downloading stock footage...")
    clips_dir = os.path.join(video_temp, "clips")
    clip_paths = search_and_download_videos(script_segments, clips_dir)

    if not clip_paths:
        print("[ERROR] No footage downloaded. Check your Pexels API key.")
        return None

    # =====================================================
    # STEP 5: BUILD CAPTIONS
    # =====================================================
    print("\n[STEP 5/6] Building word-synced captions...")
    caption_events = create_caption_clips(
        word_timestamps, script_segments, audio_duration
    )

    # =====================================================
    # STEP 6: ASSEMBLE FINAL VIDEO
    # =====================================================
    print("\n[STEP 6/6] Assembling final video...")
    output_path = os.path.join(config.OUTPUT_DIR, f"{video_name}.mp4")
    music_path = find_background_music()

    if music_path:
        print(f"[MUSIC] Using: {os.path.basename(music_path)}")
    else:
        print("[MUSIC] No background music found in assets/music/")
        print("[MUSIC] Add a .mp3 file to assets/music/ for background music")

    assemble_video(
        clip_paths=clip_paths,
        voiceover_path=voiceover_path,
        caption_events=caption_events,
        script_segments=script_segments,
        music_path=music_path,
        output_path=output_path,
    )

    # =====================================================
    # DONE
    # =====================================================
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  VIDEO COMPLETE!")
    print(f"  Topic: {topic}")
    print(f"  Output: {output_path}")
    print(f"  Time: {elapsed:.0f} seconds")
    print("=" * 60 + "\n")

    # --- Clean up temp files (optional) ---
    # Uncomment the line below to auto-delete temp files after export
    # shutil.rmtree(video_temp, ignore_errors=True)

    return output_path


def list_topics():
    """
    # Prints all available trending topics
    """
    print("\n Available Trending Topics:\n")
    for i, topic in enumerate(config.TRENDING_TOPICS, 1):
        print(f"  {i:2d}. {topic}")
    print(f"\n Total: {len(config.TRENDING_TOPICS)} topics")
    print(f" Usage: python main.py \"topic name here\"")


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":

    # --- Parse command line arguments ---
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--list":
            # Show all available topics
            list_topics()

        elif arg == "--help":
            print("\nLuminous Will Video Pipeline")
            print("Usage:")
            print("  python main.py                  -> random topic")
            print("  python main.py \"topic\"           -> specific topic")
            print("  python main.py --list            -> list topics")
            print("  python main.py --help            -> this help")

        else:
            # Use the provided topic
            run_pipeline(topic=arg)
    else:
        # Random topic
        run_pipeline()
