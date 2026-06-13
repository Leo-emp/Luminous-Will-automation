import os
import json
import uuid
from datetime import datetime
import config

# ============================================================
# QUEUE MANAGER
# Manages the video review queue stored in queue.json
# Supports: add, list, get, update status, delete
# ============================================================

QUEUE_FILE = os.path.join(config.BASE_DIR, "queue.json")


def _load_queue():
    # Loads the queue from disk, returns list of entries
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, "r") as f:
        return json.load(f)


def _save_queue(entries):
    # Saves the queue to disk
    with open(QUEUE_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def add_entry(video_path, thumbnail_path, topic, video_format, metadata, target_platforms):
    # Adds a new video to the review queue
    entry = {
        "id": str(uuid.uuid4()),
        "format": video_format,
        "topic": topic,
        "video_path": video_path,
        "thumbnail_path": thumbnail_path,
        "metadata": metadata,
        "target_platforms": target_platforms,
        "status": "pending_review",
        "created_at": datetime.utcnow().isoformat(),
        "scheduled_post_time": None,
        "post_results": {},
        "error": None,
    }
    entries = _load_queue()
    entries.append(entry)
    _save_queue(entries)
    print(f"[QUEUE] Added: {entry['id'][:8]}... ({topic})")
    return entry


def list_entries(status=None):
    # Returns all entries, optionally filtered by status
    entries = _load_queue()
    if status:
        entries = [e for e in entries if e["status"] == status]
    return entries


def get_entry(entry_id):
    # Returns a single entry by ID
    entries = _load_queue()
    for e in entries:
        if e["id"] == entry_id:
            return e
    return None


def update_entry(entry_id, updates):
    # Updates fields on an existing entry
    entries = _load_queue()
    for e in entries:
        if e["id"] == entry_id:
            e.update(updates)
            _save_queue(entries)
            print(f"[QUEUE] Updated: {entry_id[:8]}... -> {updates}")
            return e
    return None


def approve_entry(entry_id, scheduled_time=None):
    # Moves entry to approved status
    return update_entry(entry_id, {
        "status": "approved",
        "scheduled_post_time": scheduled_time,
    })


def reject_entry(entry_id):
    # Marks entry as rejected
    return update_entry(entry_id, {"status": "rejected"})


def mark_posted(entry_id, post_results):
    # Marks entry as posted with platform URLs
    return update_entry(entry_id, {
        "status": "posted",
        "post_results": post_results,
    })


def mark_failed(entry_id, error_msg):
    # Marks entry as failed with error message
    return update_entry(entry_id, {
        "status": "failed",
        "error": error_msg,
    })


def delete_entry(entry_id):
    # Removes an entry from the queue
    entries = _load_queue()
    entries = [e for e in entries if e["id"] != entry_id]
    _save_queue(entries)
    print(f"[QUEUE] Deleted: {entry_id[:8]}...")
