import os
import json
import time
import uuid
import requests
import config

# ============================================================
# VERCEL BLOB STORAGE
# Uploads generated videos + thumbnails to Vercel Blob
# so they're accessible via URL from the review dashboard.
#
# Also manages queue.json — the shared state between the
# Python pipeline (writes) and the Next.js dashboard (reads).
#
# When BLOB_READ_WRITE_TOKEN is not set, all functions
# silently return None — the pipeline works locally without it.
# ============================================================

# Base URL for all Vercel Blob REST API calls
BLOB_API_URL = "https://blob.vercel-storage.com"


def is_blob_available():
    """
    # Checks if Vercel Blob is configured
    # Returns True if the token is set
    """
    return bool(config.BLOB_READ_WRITE_TOKEN)


def upload_file(file_path, folder="videos"):
    """
    # Uploads a file to Vercel Blob and returns the public URL
    # Uses the Vercel Blob REST API (PUT with authorization)
    #
    # Args:
    #   file_path — local path to the file to upload
    #   folder — destination folder prefix (e.g., "videos", "thumbnails")
    #
    # Returns: public URL string, or None if upload fails/not configured
    """
    if not is_blob_available():
        return None

    if not os.path.exists(file_path):
        print(f"[BLOB] File not found: {file_path}")
        return None

    # --- Build the pathname for Blob storage ---
    filename = os.path.basename(file_path)
    pathname = f"{folder}/{filename}"

    # --- Determine content type based on file extension ---
    ext = os.path.splitext(filename)[1].lower()
    content_types = {
        ".mp4": "video/mp4",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".json": "application/json",
        ".mp3": "audio/mpeg",
    }
    content_type = content_types.get(ext, "application/octet-stream")

    try:
        # --- Read file contents into memory for upload ---
        with open(file_path, "rb") as f:
            file_data = f.read()

        # --- Upload via PUT to Vercel Blob API ---
        # x-add-random-suffix: "0" keeps the exact filename (no hash appended)
        headers = {
            "Authorization": f"Bearer {config.BLOB_READ_WRITE_TOKEN}",
            "x-content-type": content_type,
            "x-add-random-suffix": "0",  # don't add random suffix — use exact name
        }

        response = requests.put(
            f"{BLOB_API_URL}/{pathname}",
            headers=headers,
            data=file_data,
            timeout=120,  # 2 min timeout for large video files
        )

        if response.status_code in (200, 201):
            result = response.json()
            url = result.get("url", "")
            print(f"[BLOB] Uploaded: {pathname} → {url}")
            return url
        else:
            print(f"[BLOB] Upload failed ({response.status_code}): {response.text[:200]}")
            return None

    except Exception as e:
        print(f"[BLOB] Upload error: {e}")
        return None


def load_queue():
    """
    # Loads the current queue from Vercel Blob
    # Returns a list of queue entry dicts, or empty list if not found
    """
    if not is_blob_available():
        return []

    try:
        # --- Download queue.json from Blob using the token for auth ---
        headers = {
            "Authorization": f"Bearer {config.BLOB_READ_WRITE_TOKEN}",
        }
        response = requests.get(
            f"{BLOB_API_URL}/queue.json",
            headers=headers,
            timeout=15,
        )

        if response.status_code == 200:
            return response.json()
        else:
            # --- Queue doesn't exist yet — start fresh ---
            return []

    except Exception as e:
        print(f"[BLOB] Could not load queue: {e}")
        return []


def save_queue(entries):
    """
    # Saves the queue entries list to Vercel Blob as queue.json
    # This overwrites the existing queue.json completely
    #
    # Args:
    #   entries — list of queue entry dicts to serialize and store
    #
    # Returns: True if saved successfully, False otherwise
    """
    if not is_blob_available():
        return False

    try:
        headers = {
            "Authorization": f"Bearer {config.BLOB_READ_WRITE_TOKEN}",
            "x-content-type": "application/json",
            "x-add-random-suffix": "0",
        }

        response = requests.put(
            f"{BLOB_API_URL}/queue.json",
            headers=headers,
            data=json.dumps(entries, indent=2),
            timeout=15,
        )

        if response.status_code in (200, 201):
            print(f"[BLOB] Queue saved ({len(entries)} entries)")
            return True
        else:
            print(f"[BLOB] Queue save failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"[BLOB] Queue save error: {e}")
        return False


def add_to_queue(topic, video_format, video_url, thumbnail_url, metadata, script_text, duration):
    """
    # Adds a new entry to the review queue after video generation
    # The dashboard reads this queue to show videos for review
    #
    # Args:
    #   topic — video topic string
    #   video_format — "short" or "long"
    #   video_url — Blob URL of the uploaded video
    #   thumbnail_url — Blob URL of the uploaded thumbnail
    #   metadata — dict of platform captions from metadata_generator
    #   script_text — full script text
    #   duration — video duration in seconds
    #
    # Returns: the new queue entry dict, or None if not configured
    """
    if not is_blob_available():
        return None

    # --- Build queue entry with all fields the dashboard needs ---
    entry = {
        "id": str(uuid.uuid4())[:8],          # short 8-char ID for readability
        "topic": topic,
        "format": video_format,
        "status": "pending_review",            # dashboard shows these as awaiting approval
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "video_url": video_url,
        "thumbnail_url": thumbnail_url,
        "captions": metadata,                  # per-platform captions from metadata_generator
        "script_text": script_text,
        "duration": duration,
        "target_platforms": ["youtube", "tiktok", "instagram", "facebook"],
        "scheduled_post_time": None,           # set by dashboard when user schedules
        "post_results": {},                    # filled in by publisher after posting
        "error": None,                         # set if publishing fails
    }

    # --- Load existing queue, append new entry, persist back ---
    queue = load_queue()
    queue.append(entry)
    save_queue(queue)

    print(f"[BLOB] Added to queue: {entry['id']} — {topic}")
    return entry


def upload_pipeline_output(topic, video_format, output_path, thumbnail_path, metadata, script_text, duration):
    """
    # Top-level function called by main.py after pipeline completes
    # Uploads video + thumbnail to Blob, then adds queue entry
    #
    # Args:
    #   topic — video topic string
    #   video_format — "short" or "long" (the .value of VideoFormat enum)
    #   output_path — local path to the generated .mp4 file
    #   thumbnail_path — local path to the generated thumbnail .jpg
    #   metadata — dict of platform captions from metadata_generator
    #   script_text — full script text (for dashboard preview)
    #   duration — video duration in seconds
    #
    # Returns: queue entry dict, or None if Blob not configured
    """
    if not is_blob_available():
        print("[BLOB] Vercel Blob not configured — skipping cloud upload")
        print("[BLOB] Set BLOB_READ_WRITE_TOKEN in .env to enable")
        return None

    print("\n[STEP 9/9] Uploading to cloud storage...")

    # --- Upload the main video file ---
    video_url = upload_file(output_path, folder="videos")
    if not video_url:
        print("[BLOB] Video upload failed — skipping queue entry")
        return None

    # --- Upload the thumbnail (may be None if thumbnail generation failed) ---
    thumbnail_url = upload_file(thumbnail_path, folder="thumbnails")

    # --- Register in review queue so the dashboard can display it ---
    entry = add_to_queue(
        topic=topic,
        video_format=video_format,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        metadata=metadata,
        script_text=script_text,
        duration=duration,
    )

    return entry
