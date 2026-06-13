import os
import config
from queue_manager import mark_posted, mark_failed

# ============================================================
# PUBLISHER
# Orchestrates uploading approved videos to social platforms
# Calls platform-specific adapters for each target platform
# ============================================================


def publish_entry(queue_entry):
    # Publishes a video to all target platforms
    # Returns dict of {platform: {url, id}} results

    video_path = queue_entry["video_path"]
    metadata = queue_entry["metadata"]
    target_platforms = queue_entry["target_platforms"]
    thumbnail_path = queue_entry.get("thumbnail_path")
    entry_id = queue_entry["id"]

    if not os.path.exists(video_path):
        mark_failed(entry_id, f"Video file not found: {video_path}")
        return None

    results = {}
    errors = []

    for platform in target_platforms:
        platform_meta = metadata.get(platform, {})
        print(f"[PUBLISHER] Uploading to {platform}...")

        try:
            if platform == "youtube":
                from youtube_adapter import YouTubeAdapter
                adapter = YouTubeAdapter()
                result = adapter.upload(video_path, platform_meta, thumbnail_path)

            elif platform == "tiktok":
                from tiktok_adapter import TikTokAdapter
                adapter = TikTokAdapter()
                result = adapter.upload(video_path, platform_meta)

            elif platform == "instagram":
                from instagram_adapter import InstagramAdapter
                adapter = InstagramAdapter()
                result = adapter.upload(video_path, platform_meta)

            elif platform == "facebook":
                from facebook_adapter import FacebookAdapter
                adapter = FacebookAdapter()
                result = adapter.upload(video_path, platform_meta)

            else:
                print(f"[PUBLISHER] Unknown platform: {platform}")
                continue

            if result:
                results[platform] = result
                print(f"[PUBLISHER] {platform}: {result.get('url', 'uploaded')}")

        except Exception as e:
            error_msg = f"{platform}: {str(e)}"
            errors.append(error_msg)
            print(f"[PUBLISHER] Error on {platform}: {e}")

    if results:
        mark_posted(entry_id, results)
    elif errors:
        mark_failed(entry_id, "; ".join(errors))

    return results
