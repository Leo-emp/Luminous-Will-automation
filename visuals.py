import os
import requests
import time
import random
import config

# ============================================================
# VISUAL SOURCER
# Downloads free vertical stock footage from Pexels API
# Filters for dark, cinematic, high-quality clips
# ============================================================


def search_and_download_videos(script_segments, output_dir):
    """
    # For each script segment, searches Pexels for matching footage
    # Downloads the best vertical (9:16) clip for each segment
    #
    # Args:
    #   script_segments: list of script dicts with 'visual_keywords'
    #   output_dir: directory to save downloaded clips
    #
    # Returns:
    #   list of file paths to downloaded video clips
    """

    os.makedirs(output_dir, exist_ok=True)
    downloaded_clips = []
    # Track used video IDs so we don't reuse the same clip
    used_video_ids = set()

    for i, segment in enumerate(script_segments):
        keywords = segment["visual_keywords"]
        print(f"[VISUALS] ({i+1}/{len(script_segments)}) Searching: {keywords}")

        # --- Search Pexels for matching footage ---
        video_path = search_and_download_one(
            keywords, output_dir, i, used_video_ids
        )

        if video_path:
            downloaded_clips.append(video_path)
            print(f"[VISUALS] Downloaded: {os.path.basename(video_path)}")
        else:
            # Fallback: try simpler keywords
            simple_keywords = keywords.split()[:2]
            fallback_query = " ".join(simple_keywords)
            print(f"[VISUALS] Trying fallback: {fallback_query}")
            video_path = search_and_download_one(
                fallback_query, output_dir, i, used_video_ids
            )
            if video_path:
                downloaded_clips.append(video_path)
            else:
                # Last resort fallback with generic dark aesthetic keywords
                for fallback in ["dark cinematic", "dark aesthetic", "night city", "dark moody"]:
                    video_path = search_and_download_one(
                        fallback, output_dir, i, used_video_ids
                    )
                    if video_path:
                        downloaded_clips.append(video_path)
                        break

        # --- Respect Pexels API rate limits (200 req/hr) ---
        time.sleep(1)

    print(f"[VISUALS] Downloaded {len(downloaded_clips)} clips total")
    return downloaded_clips


def search_and_download_one(query, output_dir, index, used_ids):
    """
    # Searches Pexels and downloads one matching video clip
    # Prefers portrait orientation and high resolution
    #
    # Returns: file path of downloaded clip, or None
    """

    # --- Search the Pexels API ---
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": config.PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": config.PEXELS_ORIENTATION,  # portrait for 9:16
        "size": config.PEXELS_SIZE,                # large/high quality
        "per_page": config.PEXELS_PER_PAGE,
    }

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"[VISUALS] Pexels API error: {response.status_code}")
            return None

        data = response.json()
        videos = data.get("videos", [])

        if not videos:
            print(f"[VISUALS] No results for: {query}")
            return None

        # --- Filter out already-used videos ---
        available = [v for v in videos if v["id"] not in used_ids]
        if not available:
            available = videos  # allow reuse if nothing else found

        # --- Pick a random one from top results for variety ---
        video = random.choice(available[:5])
        used_ids.add(video["id"])

        # --- Find the best quality video file ---
        # Prefer HD (1920x1080) or higher portrait files
        video_file = get_best_video_file(video)

        if not video_file:
            print(f"[VISUALS] No suitable video file found")
            return None

        # --- Download the video ---
        download_url = video_file["link"]
        file_path = os.path.join(output_dir, f"clip_{index:03d}.mp4")

        print(f"[VISUALS] Downloading: {video_file.get('quality', '?')} "
              f"({video_file.get('width', '?')}x{video_file.get('height', '?')})")

        video_response = requests.get(download_url, stream=True)
        with open(file_path, "wb") as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                f.write(chunk)

        return file_path

    except Exception as e:
        print(f"[VISUALS] Error: {e}")
        return None


def get_best_video_file(video_data):
    """
    # Picks the best quality video file from Pexels response
    # Prefers: portrait orientation, HD or higher, mp4 format
    """

    video_files = video_data.get("video_files", [])

    if not video_files:
        return None

    # --- Sort by quality: prefer HD portrait files ---
    portrait_files = []
    landscape_files = []

    for vf in video_files:
        w = vf.get("width", 0)
        h = vf.get("height", 0)
        # Portrait = height > width
        if h > w:
            portrait_files.append(vf)
        else:
            landscape_files.append(vf)

    # --- Prefer portrait, fall back to landscape ---
    candidates = portrait_files if portrait_files else landscape_files

    # --- Sort by resolution (higher is better) ---
    candidates.sort(key=lambda x: x.get("height", 0) * x.get("width", 0), reverse=True)

    # --- Return best quality (but not unnecessarily huge) ---
    for vf in candidates:
        h = vf.get("height", 0)
        # Prefer 1920 height or close to it
        if 720 <= h <= 3840:
            return vf

    # --- Fallback: just return the first one ---
    return candidates[0] if candidates else video_files[0]


# --- Quick test ---
if __name__ == "__main__":
    test_segments = [
        {"visual_keywords": "lion dark dramatic portrait"},
        {"visual_keywords": "man walking alone night city"},
    ]
    clips = search_and_download_videos(test_segments, config.TEMP_DIR)
    print(f"\nDownloaded {len(clips)} test clips")
