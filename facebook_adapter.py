import os
import json
import requests
import config

# ============================================================
# FACEBOOK ADAPTER
# Uploads videos to Facebook Page/Profile via Graph API
# Shares OAuth credentials with Instagram adapter
# Token refresh: 60-day long-lived tokens
# ============================================================

TOKEN_FILE = os.path.join(config.BASE_DIR, ".facebook_token.json")


class FacebookAdapter:

    def __init__(self):
        self.access_token = None
        self.page_id = None
        self._load_token()

    def _load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                self.access_token = data.get("access_token")
                self.page_id = data.get("page_id")

    def upload(self, video_path, metadata):
        # Uploads a video to Facebook Page
        if not self.access_token:
            raise Exception("Facebook not authenticated")

        description = metadata.get("description", "")
        hashtags = metadata.get("hashtags", [])
        full_desc = f"{description}\n\n{' '.join('#' + h for h in hashtags)}"

        target_id = self.page_id or "me"

        with open(video_path, "rb") as video_file:
            resp = requests.post(
                f"https://graph-video.facebook.com/v21.0/{target_id}/videos",
                data={
                    "description": full_desc,
                    "access_token": self.access_token,
                },
                files={
                    "source": video_file,
                },
            )

        if resp.status_code != 200:
            raise Exception(f"Facebook upload failed: {resp.text}")

        video_id = resp.json().get("id")
        print(f"[FACEBOOK] Uploaded, video_id: {video_id}")

        return {"url": f"https://www.facebook.com/watch/?v={video_id}", "video_id": video_id}
