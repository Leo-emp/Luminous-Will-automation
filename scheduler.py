import os
import time
import random
import schedule
import config
from config import VideoFormat
from main import run_pipeline
from queue_manager import add_entry
from metadata_generator import generate_metadata
from thumbnail import generate_thumbnail, generate_reel_thumbnail
from script_generator import extract_chapters

# ============================================================
# SCHEDULER
# Generates videos on a cron schedule and queues them for review
# Long-form: Mon/Thu at 2 AM
# Short-form: Daily at 3 AM
# Quote reels: Daily at 4 AM
# ============================================================

# --- Track used topics to avoid repetition ---
USED_TOPICS_FILE = os.path.join(config.BASE_DIR, ".used_topics.json")


def _load_used_topics():
    import json
    if os.path.exists(USED_TOPICS_FILE):
        with open(USED_TOPICS_FILE, "r") as f:
            return json.load(f)
    return []


def _save_used_topic(topic):
    import json
    used = _load_used_topics()
    used.append(topic)
    # Keep last 100 to allow recycling
    used = used[-100:]
    with open(USED_TOPICS_FILE, "w") as f:
        json.dump(used, f)


def _pick_topic():
    # Picks a topic that hasn't been used recently
    used = set(_load_used_topics())
    available = [t for t in config.TRENDING_TOPICS if t not in used]
    if not available:
        available = config.TRENDING_TOPICS
    topic = random.choice(available)
    _save_used_topic(topic)
    return topic


def generate_and_queue(video_format):
    # Generates a video and adds it to the review queue
    fmt = VideoFormat(video_format)
    topic = _pick_topic()
    fmt_str = fmt.value

    print(f"\n[SCHEDULER] Generating {fmt_str} video: {topic}")

    try:
        # Run the pipeline
        output_path = run_pipeline(topic=topic, video_format=fmt)

        if not output_path or not os.path.exists(output_path):
            print(f"[SCHEDULER] Pipeline failed for: {topic}")
            return

        # Generate thumbnail
        thumb_path = generate_thumbnail(output_path, topic)

        # Generate platform metadata
        metadata = generate_metadata(topic, [], fmt_str)

        # Determine target platforms based on format
        if fmt == VideoFormat.HORIZONTAL_LONG:
            targets = ["youtube"]
        else:
            targets = ["tiktok", "instagram", "facebook"]

        # Add to review queue
        add_entry(
            video_path=output_path,
            thumbnail_path=thumb_path,
            topic=topic,
            video_format=fmt_str,
            metadata=metadata,
            target_platforms=targets,
        )

        print(f"[SCHEDULER] Queued for review: {topic} ({fmt_str})")

    except Exception as e:
        print(f"[SCHEDULER] Error: {e}")


def generate_reel_and_queue():
    # Generates a quote reel and adds it to the review queue
    from quote_reel import run_quote_reel
    from metadata_generator import generate_reel_metadata
    topic = _pick_topic()

    print(f"\n[SCHEDULER] Generating quote reel: {topic}")

    try:
        output_path, quotes = run_quote_reel(topic=topic, num_quotes=5)

        if not output_path or not os.path.exists(output_path):
            print(f"[SCHEDULER] Reel pipeline failed for: {topic}")
            return

        # Generate 9:16 reel thumbnail from the rendered slides
        thumb_path = generate_reel_thumbnail(output_path, topic)

        metadata = generate_reel_metadata(topic, quotes)

        targets = ["tiktok", "instagram", "youtube"]

        add_entry(
            video_path=output_path,
            thumbnail_path=thumb_path,
            topic=topic,
            video_format="reel",
            metadata=metadata,
            target_platforms=targets,
        )

        print(f"[SCHEDULER] Reel queued for review: {topic}")

    except Exception as e:
        print(f"[SCHEDULER] Reel error: {e}")


def _post_approved():
    # Auto-posts approved entries whose scheduled time has passed
    from datetime import datetime
    from publisher import publish_entry
    from queue_manager import list_entries as _list

    approved = _list(status="approved")
    if not approved:
        return

    now = datetime.utcnow().isoformat()
    for entry in approved:
        scheduled = entry.get("scheduled_post_time")
        if scheduled and scheduled > now:
            continue
        topic = entry.get("topic", "unknown")
        print(f"[SCHEDULER] Auto-posting approved: {topic}")
        try:
            publish_entry(entry)
        except Exception as e:
            print(f"[SCHEDULER] Auto-post failed: {e}")


def run_scheduler():
    # Starts the scheduler loop
    long_schedule = os.getenv("SCHEDULE_LONG_FORM", "monday,thursday")
    short_schedule = os.getenv("SCHEDULE_SHORT_FORM", "daily")
    reel_schedule = os.getenv("SCHEDULE_REELS", "daily")

    if "monday" in long_schedule:
        schedule.every().monday.at("02:00").do(generate_and_queue, "long")
    if "thursday" in long_schedule:
        schedule.every().thursday.at("02:00").do(generate_and_queue, "long")

    if short_schedule == "daily":
        schedule.every().day.at("03:00").do(generate_and_queue, "short")

    if reel_schedule == "daily":
        schedule.every().day.at("04:00").do(generate_reel_and_queue)

    # Check for approved entries every 15 minutes and auto-post if due
    schedule.every(15).minutes.do(_post_approved)

    print("[SCHEDULER] Started. Schedules:")
    for job in schedule.get_jobs():
        print(f"  - {job}")
    print("[SCHEDULER] Waiting for next run... (Ctrl+C to stop)")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        fmt = sys.argv[2] if len(sys.argv) > 2 else "short"
        if fmt == "reel":
            generate_reel_and_queue()
        else:
            generate_and_queue(fmt)
    else:
        run_scheduler()
