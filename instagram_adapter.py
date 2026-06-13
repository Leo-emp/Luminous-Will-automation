import os
import json
import time
import requests
import config

# ============================================================
# INSTAGRAM ADAPTER
# Uploads Reels via Instagram Graph API (through Facebook)
# Requires Facebook Business/Creator account
# Token refresh: 60-day long-lived tokens
# ============================================================

TOKEN_FILE = os.path.join(config.BASE_DIR, ".instagram_token.json")

FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")


class InstagramAdapter:

    def __init__(self):
        self.access_token = None
        self.ig_user_id = None
        self._load_token()

    def _load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                self.access_token = data.get("access_token")
                self.ig_user_id = data.get("ig_user_id")

    def _save_token(self, token_data):
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f, indent=2)
        self.access_token = token_data.get("access_token")
        self.ig_user_id = token_data.get("ig_user_id")

    def upload(self, video_path, metadata):
        # Uploads a Reel to Instagram using container-based flow
        if not self.access_token or not self.ig_user_id:
            raise Exception("Instagram not authenticated")

        caption = metadata.get("caption", "")
        hashtags = metadata.get("hashtags", [])
        full_caption = f"{caption}\n\n{' '.join('#' + h for h in hashtags)}"

        # Step 1: Create container
        # Note: video_path must be a public URL for Instagram API
        container_resp = requests.post(
            f"https://graph.facebook.com/v21.0/{self.ig_user_id}/media",
            data={
                "media_type": "REELS",
                "video_url": video_path,
                "caption": full_caption[:2200],
                "access_token": self.access_token,
            },
        )

        if container_resp.status_code != 200:
            raise Exception(f"Instagram container failed: {container_resp.text}")

        container_id = container_resp.json().get("id")

        # Step 2: Wait for container to be ready
        for _ in range(30):
            status_resp = requests.get(
                f"https://graph.facebook.com/v21.0/{container_id}",
                params={
                    "fields": "status_code",
                    "access_token": self.access_token,
                },
            )
            status = status_resp.json().get("status_code")
            if status == "FINISHED":
                break
            elif status == "ERROR":
                raise Exception("Instagram container processing failed")
            time.sleep(5)

        # Step 3: Publish
        publish_resp = requests.post(
            f"https://graph.facebook.com/v21.0/{self.ig_user_id}/media_publish",
            data={
                "creation_id": container_id,
                "access_token": self.access_token,
            },
        )

        if publish_resp.status_code != 200:
            raise Exception(f"Instagram publish failed: {publish_resp.text}")

        media_id = publish_resp.json().get("id")
        print(f"[INSTAGRAM] Published, media_id: {media_id}")

        return {"url": f"https://www.instagram.com/reel/{media_id}", "media_id": media_id}
