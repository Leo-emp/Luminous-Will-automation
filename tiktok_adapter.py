import os
import json
import requests
import config

# ============================================================
# TIKTOK ADAPTER
# Uploads videos via TikTok Content Posting API
# Requires creator account + approved developer app
# Token refresh: 24-hour expiry
# ============================================================

TOKEN_FILE = os.path.join(config.BASE_DIR, ".tiktok_token.json")

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")


class TikTokAdapter:

    def __init__(self):
        self.access_token = None
        self._load_token()

    def _load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                self.access_token = data.get("access_token")

    def _save_token(self, token_data):
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f, indent=2)
        self.access_token = token_data.get("access_token")

    def refresh_token(self):
        # Refreshes the TikTok access token
        if not os.path.exists(TOKEN_FILE):
            raise Exception("TikTok not authenticated. Run OAuth flow first.")

        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)

        refresh = data.get("refresh_token")
        if not refresh:
            raise Exception("No refresh token available")

        resp = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
            "client_key": TIKTOK_CLIENT_KEY,
            "client_secret": TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        })

        if resp.status_code == 200:
            self._save_token(resp.json())
            print("[TIKTOK] Token refreshed")
        else:
            raise Exception(f"Token refresh failed: {resp.status_code}")

    def upload(self, video_path, metadata):
        # Uploads a video to TikTok
        if not self.access_token:
            raise Exception("TikTok not authenticated")

        caption = metadata.get("caption", "")
        hashtags = metadata.get("hashtags", [])
        full_caption = f"{caption} {' '.join('#' + h for h in hashtags)}"[:150]

        file_size = os.path.getsize(video_path)

        # Step 1: Initialize upload
        init_resp = requests.post(
            "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json={
                "post_info": {
                    "title": full_caption,
                    "privacy_level": "SELF_ONLY",
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                },
            },
        )

        if init_resp.status_code != 200:
            raise Exception(f"TikTok init failed: {init_resp.status_code} - {init_resp.text}")

        data = init_resp.json().get("data", {})
        upload_url = data.get("upload_url")
        publish_id = data.get("publish_id")

        if not upload_url:
            raise Exception("No upload URL returned from TikTok")

        # Step 2: Upload video file
        with open(video_path, "rb") as f:
            upload_resp = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(file_size),
                },
                data=f,
            )

        if upload_resp.status_code not in (200, 201):
            raise Exception(f"TikTok upload failed: {upload_resp.status_code}")

        print(f"[TIKTOK] Uploaded, publish_id: {publish_id}")
        return {"url": "https://www.tiktok.com", "publish_id": publish_id}
