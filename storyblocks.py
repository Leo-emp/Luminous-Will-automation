import os
import time
import hmac
import hashlib
import requests
import config

# ============================================================
# STORYBLOCKS API CLIENT
# Premium stock footage + music search and download
# Only active when STORYBLOCKS_API_KEY and STORYBLOCKS_API_SECRET
# are both set in .env — falls back silently when not configured
#
# API AUTHENTICATION:
#   Storyblocks uses HMAC-SHA256 signing:
#     1. Build a message string: "<endpoint_path><expires_timestamp>"
#     2. Sign it with STORYBLOCKS_API_SECRET using HMAC-SHA256
#     3. Pass APIKEY, EXPIRES, and HMAC as query params
#
# ENDPOINTS:
#   - Videos: https://api.graphicstock.com/api/v2/videos/search
#   - Audio:  https://api.graphicstock.com/api/v2/audio/search
# ============================================================


def is_storyblocks_available():
    """
    # Checks if Storyblocks API is fully configured (key AND secret required)
    # Returns True only when both are non-empty strings
    # The HMAC signature requires both to function correctly
    """
    # --- Both key and secret must be present for authenticated requests ---
    return bool(config.STORYBLOCKS_API_KEY and config.STORYBLOCKS_API_SECRET)


def _build_hmac_signature(endpoint_path, expires):
    """
    # Builds the HMAC-SHA256 signature for Storyblocks API authentication
    # Message format: "<endpoint_path><expires_timestamp>"
    # Example: "/api/v2/videos/search1748000000"
    #
    # Args:
    #   endpoint_path: the API path (e.g. "/api/v2/videos/search")
    #   expires: Unix timestamp integer (5 minutes from now)
    #
    # Returns: lowercase hex string of the HMAC digest
    """
    # --- Build the message to sign ---
    # Storyblocks expects: path + expires concatenated (no separator)
    message = f"{endpoint_path}{expires}"

    # --- Generate HMAC-SHA256 signature using the API secret as the key ---
    signature = hmac.new(
        config.STORYBLOCKS_API_SECRET.encode("utf-8"),  # secret as bytes
        message.encode("utf-8"),                         # message as bytes
        hashlib.sha256                                    # SHA-256 digest algorithm
    ).hexdigest()

    return signature


def search_storyblocks_video(query, orientation="portrait", used_ids=None):
    """
    # Searches Storyblocks video library for footage matching the query
    # Returns a list of video result dicts (or empty list if unavailable)
    #
    # Args:
    #   query: search terms (e.g. "dark lion cinematic")
    #   orientation: "portrait" (9:16) or "landscape" (16:9) — not all APIs support this
    #   used_ids: set of video IDs already used in this pipeline run (to avoid repeats)
    #
    # Returns: list of video metadata dicts from Storyblocks API
    """
    # --- Skip gracefully if API keys are not configured ---
    if not is_storyblocks_available():
        return []

    # --- Default used_ids to empty set if not provided ---
    if used_ids is None:
        used_ids = set()

    # --- Define the endpoint path (used in both URL and HMAC message) ---
    endpoint_path = "/api/v2/videos/search"
    endpoint_url = f"https://api.graphicstock.com{endpoint_path}"

    # --- Set expiry 5 minutes from now (Storyblocks tokens are short-lived) ---
    expires = int(time.time()) + 300

    # --- Generate HMAC-SHA256 authentication signature ---
    signature = _build_hmac_signature(endpoint_path, expires)

    # --- Build query parameters ---
    params = {
        "APIKEY": config.STORYBLOCKS_API_KEY,    # public API key
        "EXPIRES": expires,                        # timestamp when this request expires
        "HMAC": signature,                         # HMAC signature for auth verification
        "keywords": query,                         # search terms
        "content_type": "footage",                 # video footage only (not images)
        "results_per_page": 15,                    # fetch enough candidates to score
    }

    try:
        # --- Make the API request with a 15-second timeout ---
        response = requests.get(endpoint_url, params=params, timeout=15)

        if response.status_code != 200:
            print(f"[STORYBLOCKS] API error: {response.status_code} for query '{query}'")
            return []

        data = response.json()
        # --- Storyblocks returns results in a "results" array ---
        results = data.get("results", [])

        # --- Filter out video IDs already used in this video production run ---
        available = [r for r in results if r.get("id") not in used_ids]

        print(f"[STORYBLOCKS] Found {len(available)} videos for '{query}'")
        return available

    except Exception as e:
        # --- Never crash the pipeline — log and return empty list ---
        print(f"[STORYBLOCKS] Search error: {e}")
        return []


def download_storyblocks_video(video_meta, output_dir, index):
    """
    # Downloads a Storyblocks video clip from its preview or comp URL
    # Returns the local file path if successful, or None if download fails
    #
    # Args:
    #   video_meta: dict from Storyblocks search result (contains download URLs)
    #   output_dir: directory to save the downloaded clip
    #   index: clip index number (used in filename, e.g. clip_003.mp4)
    #
    # Returns: str file path on success, None on failure
    """
    # --- Try preview_url first, fall back to comp_download_url ---
    # preview_url: watermarked preview (lower quality but always available)
    # comp_download_url: comp/draft version for licensed subscribers
    download_url = video_meta.get("preview_url") or video_meta.get("comp_download_url")

    if not download_url:
        print(f"[STORYBLOCKS] No download URL in video metadata")
        return None

    # --- Build the output file path ---
    file_path = os.path.join(output_dir, f"clip_{index:03d}.mp4")

    try:
        # --- Stream download with 60-second timeout for large video files ---
        response = requests.get(download_url, stream=True, timeout=60)

        if response.status_code != 200:
            print(f"[STORYBLOCKS] Download failed: HTTP {response.status_code}")
            return None

        # --- Write the file in 8KB chunks to avoid memory issues ---
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # --- Sanity check: reject suspiciously small files (< 50KB = probably an error page) ---
        file_size = os.path.getsize(file_path)
        if file_size < 50000:
            print(f"[STORYBLOCKS] File too small ({file_size} bytes), likely an error — removing")
            os.remove(file_path)
            return None

        print(f"[STORYBLOCKS] Downloaded: {os.path.basename(file_path)} ({file_size // 1024}KB)")
        return file_path

    except Exception as e:
        # --- Never crash the pipeline — log and return None ---
        print(f"[STORYBLOCKS] Download error: {e}")
        return None


def search_storyblocks_music(query, used_ids=None):
    """
    # Searches Storyblocks audio/music library for background tracks
    # Returns a list of audio result dicts (or empty list if unavailable)
    #
    # Args:
    #   query: search terms (e.g. "dark cinematic orchestral")
    #   used_ids: set of track IDs already used to avoid repeating music
    #
    # Returns: list of audio metadata dicts from Storyblocks API
    """
    # --- Skip gracefully if API keys are not configured ---
    if not is_storyblocks_available():
        return []

    # --- Default used_ids to empty set if not provided ---
    if used_ids is None:
        used_ids = set()

    # --- Define the audio search endpoint ---
    endpoint_path = "/api/v2/audio/search"
    endpoint_url = f"https://api.graphicstock.com{endpoint_path}"

    # --- Set expiry timestamp for this signed request ---
    expires = int(time.time()) + 300

    # --- Generate HMAC-SHA256 signature for the audio endpoint ---
    signature = _build_hmac_signature(endpoint_path, expires)

    # --- Build query parameters ---
    params = {
        "APIKEY": config.STORYBLOCKS_API_KEY,    # public API key
        "EXPIRES": expires,                        # expiry timestamp
        "HMAC": signature,                         # authentication signature
        "keywords": query,                         # search terms
        "content_type": "music",                   # music tracks only (not sound effects)
        "results_per_page": 10,                    # reasonable batch for scoring
    }

    try:
        # --- Make the API request ---
        response = requests.get(endpoint_url, params=params, timeout=15)

        if response.status_code != 200:
            print(f"[STORYBLOCKS] Music API error: {response.status_code}")
            return []

        data = response.json()
        results = data.get("results", [])

        # --- Filter out already-used track IDs ---
        available = [r for r in results if r.get("id") not in used_ids]

        print(f"[STORYBLOCKS] Found {len(available)} music tracks for '{query}'")
        return available

    except Exception as e:
        # --- Never crash the pipeline — log and return empty list ---
        print(f"[STORYBLOCKS] Music search error: {e}")
        return []
