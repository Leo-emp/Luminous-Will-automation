import os
import sys
import argparse
from datetime import datetime, timedelta
from queue_manager import (
    list_entries, get_entry, approve_entry, reject_entry, delete_entry
)
from publisher import publish_entry

# ============================================================
# REVIEW CLI
# Review, approve, and publish queued videos from the terminal.
#
# Usage:
#   python review.py                  -> list all pending videos
#   python review.py --all            -> list all entries (any status)
#   python review.py approve <id>     -> approve + auto-post immediately
#   python review.py approve <id> --schedule 2h  -> approve + post in 2 hours
#   python review.py reject <id>      -> reject entry
#   python review.py delete <id>      -> permanently remove
#   python review.py post             -> post all approved entries now
#   python review.py preview <id>     -> open video file in default player
# ============================================================


def cmd_list(show_all=False):
    # Lists pending entries (or all entries with --all)
    if show_all:
        entries = list_entries()
    else:
        entries = list_entries(status="pending_review")

    if not entries:
        print("[REVIEW] No entries found.")
        return

    print(f"\n{'ID':10s} {'Status':16s} {'Format':6s} {'Topic':35s} {'Created':20s}")
    print("-" * 90)
    for e in entries:
        short_id = e["id"][:8]
        status = e["status"]
        fmt = e.get("format", "?")
        topic = e.get("topic", "unknown")[:35]
        created = e.get("created_at", "")[:19]
        platforms = ", ".join(e.get("target_platforms", []))

        # Color-code status
        if status == "pending_review":
            status_str = "PENDING"
        elif status == "approved":
            status_str = "APPROVED"
        elif status == "posted":
            status_str = "POSTED"
        elif status == "rejected":
            status_str = "REJECTED"
        elif status == "failed":
            status_str = "FAILED"
        else:
            status_str = status.upper()

        print(f"{short_id:10s} {status_str:16s} {fmt:6s} {topic:35s} {created:20s}")
        if status == "posted" and e.get("post_results"):
            for p, r in e["post_results"].items():
                url = r.get("url", "uploaded")
                print(f"{'':10s}   -> {p}: {url}")
        if status == "failed" and e.get("error"):
            print(f"{'':10s}   !! {e['error'][:60]}")

    print(f"\nTotal: {len(entries)} entries")
    pending = len([e for e in entries if e["status"] == "pending_review"])
    if pending > 0:
        print(f"Pending review: {pending}")
        print(f"\nApprove: python review.py approve <id>")


def _resolve_id(short_id):
    # Resolves a short ID prefix to the full UUID
    entries = list_entries()
    matches = [e for e in entries if e["id"].startswith(short_id)]
    if len(matches) == 0:
        print(f"[REVIEW] No entry found matching: {short_id}")
        return None
    if len(matches) > 1:
        print(f"[REVIEW] Ambiguous ID '{short_id}', matches:")
        for m in matches:
            print(f"  {m['id'][:8]} — {m.get('topic', '?')}")
        return None
    return matches[0]["id"]


def cmd_approve(short_id, schedule_delay=None):
    # Approves an entry and optionally schedules posting
    full_id = _resolve_id(short_id)
    if not full_id:
        return

    scheduled_time = None
    if schedule_delay:
        # Parse delay like "2h", "30m", "1d"
        unit = schedule_delay[-1].lower()
        try:
            val = int(schedule_delay[:-1])
        except ValueError:
            print(f"[REVIEW] Invalid schedule format: {schedule_delay} (use 2h, 30m, 1d)")
            return
        if unit == "h":
            scheduled_time = (datetime.utcnow() + timedelta(hours=val)).isoformat()
        elif unit == "m":
            scheduled_time = (datetime.utcnow() + timedelta(minutes=val)).isoformat()
        elif unit == "d":
            scheduled_time = (datetime.utcnow() + timedelta(days=val)).isoformat()
        else:
            print(f"[REVIEW] Unknown unit '{unit}' — use h (hours), m (minutes), d (days)")
            return

    entry = approve_entry(full_id, scheduled_time=scheduled_time)
    if entry:
        topic = entry.get("topic", "unknown")
        if scheduled_time:
            print(f"[REVIEW] Approved '{topic}' — scheduled for {scheduled_time}")
        else:
            print(f"[REVIEW] Approved '{topic}' — posting now...")
            entry = get_entry(full_id)
            results = publish_entry(entry)
            if results:
                print(f"[REVIEW] Posted to: {', '.join(results.keys())}")
            else:
                print(f"[REVIEW] Publishing failed — check error with: python review.py --all")


def cmd_reject(short_id):
    # Rejects an entry
    full_id = _resolve_id(short_id)
    if not full_id:
        return
    entry = reject_entry(full_id)
    if entry:
        print(f"[REVIEW] Rejected: {entry.get('topic', 'unknown')}")


def cmd_delete(short_id):
    # Permanently removes an entry
    full_id = _resolve_id(short_id)
    if not full_id:
        return
    delete_entry(full_id)
    print(f"[REVIEW] Deleted: {short_id}")


def cmd_post_approved():
    # Posts all approved entries that are due (scheduled_time passed or no schedule)
    approved = list_entries(status="approved")
    if not approved:
        print("[REVIEW] No approved entries to post.")
        return

    now = datetime.utcnow().isoformat()
    posted = 0

    for entry in approved:
        scheduled = entry.get("scheduled_post_time")
        if scheduled and scheduled > now:
            print(f"[REVIEW] Skipping {entry['id'][:8]} — scheduled for {scheduled}")
            continue

        topic = entry.get("topic", "unknown")
        print(f"[REVIEW] Posting: {topic}...")
        results = publish_entry(entry)
        if results:
            print(f"[REVIEW] Posted '{topic}' to: {', '.join(results.keys())}")
            posted += 1

    print(f"\n[REVIEW] Posted {posted}/{len(approved)} approved entries")


def cmd_preview(short_id):
    # Opens the video file in the default system player
    full_id = _resolve_id(short_id)
    if not full_id:
        return

    entry = get_entry(full_id)
    if not entry:
        print(f"[REVIEW] Entry not found: {short_id}")
        return

    video_path = entry.get("video_path", "")
    if not os.path.exists(video_path):
        print(f"[REVIEW] Video file not found: {video_path}")
        return

    print(f"[REVIEW] Opening: {video_path}")
    os.startfile(video_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Luminous Will — Review Queue")
    parser.add_argument("command", nargs="?", default="list",
                        choices=["list", "approve", "reject", "delete", "post", "preview"],
                        help="Command to run")
    parser.add_argument("id", nargs="?", default=None, help="Entry ID (first 8 chars)")
    parser.add_argument("--all", action="store_true", help="Show all entries, not just pending")
    parser.add_argument("--schedule", default=None, help="Schedule posting delay (2h, 30m, 1d)")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(show_all=args.all)
    elif args.command == "approve":
        if not args.id:
            print("[REVIEW] Usage: python review.py approve <id> [--schedule 2h]")
        else:
            cmd_approve(args.id, schedule_delay=args.schedule)
    elif args.command == "reject":
        if not args.id:
            print("[REVIEW] Usage: python review.py reject <id>")
        else:
            cmd_reject(args.id)
    elif args.command == "delete":
        if not args.id:
            print("[REVIEW] Usage: python review.py delete <id>")
        else:
            cmd_delete(args.id)
    elif args.command == "post":
        cmd_post_approved()
    elif args.command == "preview":
        if not args.id:
            print("[REVIEW] Usage: python review.py preview <id>")
        else:
            cmd_preview(args.id)
