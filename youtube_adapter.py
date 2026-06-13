import os
import json
import config

# ============================================================
# YOUTUBE ADAPTER
# Uploads videos to YouTube via Data API v3
# Uses OAuth2 for authentication (one-time consent)
# Supports resumable uploads for large files
# ============================================================

TOKEN_FILE = os.path.join(config.BASE_DIR, ".youtube_token.json")
CLIENT_SECRETS_FILE = os.path.join(config.BASE_DIR, "client_secrets.json")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
           "https://www.googleapis.com/auth/youtube"]


class YouTubeAdapter:

    def __init__(self):
        self.service = None

    def authenticate(self):
        # Authenticates with YouTube using stored OAuth2 tokens
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None

        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                if not os.path.exists(CLIENT_SECRETS_FILE):
                    raise FileNotFoundError(
                        f"YouTube client_secrets.json not found at {CLIENT_SECRETS_FILE}. "
                        "Download it from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
                creds = flow.run_local_server(port=8090)

            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        self.service = build("youtube", "v3", credentials=creds)
        return True

    def upload(self, video_path, metadata, thumbnail_path=None):
        # Uploads a video to YouTube with metadata
        from googleapiclient.http import MediaFileUpload

        if not self.service:
            self.authenticate()

        title = metadata.get("title", "Luminous Will")[:100]
        description = metadata.get("description", "")[:5000]
        tags = metadata.get("tags", [])[:50]
        category = metadata.get("category", "Education")

        # Map category name to ID
        category_ids = {"Education": "27", "People & Blogs": "22", "Entertainment": "24"}
        category_id = category_ids.get(category, "27")

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": "unlisted",
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)

        request = self.service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        print("[YOUTUBE] Starting resumable upload...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"[YOUTUBE] Upload progress: {int(status.progress() * 100)}%")

        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"[YOUTUBE] Uploaded: {video_url}")

        # Upload thumbnail if available
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                self.service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
                ).execute()
                print("[YOUTUBE] Thumbnail set")
            except Exception as e:
                print(f"[YOUTUBE] Thumbnail upload failed: {e}")

        return {"url": video_url, "video_id": video_id}
