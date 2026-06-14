# Luminous Will: Dual-Format Pipeline + Scheduled Posting

**Date:** 2026-06-13
**Status:** Approved
**Scope:** Add 16:9 YouTube long-form format support and scheduled posting with review queue to all 4 social platforms

---

## Overview

Two features added to the Luminous Will automated video pipeline:

1. **16:9 Horizontal Long-Form** — 8-12 minute YouTube videos with Gemini-generated scripts, alongside existing 9:16 vertical shorts
2. **Scheduled Posting with Review Queue** — Auto-generate videos on a schedule, review in web dashboard, publish to YouTube, TikTok, Instagram, and Facebook

Design principle: **quality over efficiency**. Each format is a separate, purpose-built generation run — not one derived from the other.

---

## Architecture

Three existing repos, all modified:

```
LuminousWill/              (local Python pipeline — core engine)
luminous-will-api/         (HF Spaces Gradio — cloud backend)
luminous-will-web/         (Next.js — frontend + review dashboard)
```

Connection flow unchanged: Web → Gradio API → Pipeline modules.

New flow for scheduled posting:

```
Cron (scheduler.py)
  → Generate video (pipeline)
  → Save to queue (queue.json)
  → Web dashboard shows pending videos
  → User approves/rejects
  → Publisher uploads to selected platforms
  → Queue updated with post URLs
```

---

## Feature 1: 16:9 Long-Form Support

### 1.1 Format System

New `VideoFormat` enum in `config.py` with two profiles:

#### VERTICAL_SHORT (9:16) — existing, unchanged

| Setting | Value |
|---------|-------|
| Resolution | 1080 x 1920 |
| FPS | 30 |
| Bitrate | 12000k |
| Pexels orientation | portrait |
| Duration | 60-90 seconds |
| Caption font size | 65 |
| Caption position | 83% down |
| Caption stroke width | 2px |
| Brightness factor | 0.55 |
| Music volume | 0.32 (flat) |
| Transitions | Hard cuts |
| Script source | Template-based |

#### HORIZONTAL_LONG (16:9) — new

| Setting | Value |
|---------|-------|
| Resolution | 1920 x 1080 |
| FPS | 30 |
| Bitrate | 15000k |
| Pexels orientation | landscape |
| Duration | 8-12 minutes |
| Caption font size | 48 |
| Caption position | 88% down (lower third) |
| Caption stroke width | 3px |
| Brightness factor | 0.60 |
| Music volume | Dynamic ducking |
| Transitions | 0.5s crossfade |
| Script source | Gemini API |

Rationale for differences:
- **15000k bitrate**: Landscape has more visual detail to preserve than portrait
- **Brightness 0.60**: Landscape footage reads darker at the same settings due to more visual information; slight bump maintains the dark aesthetic without losing detail
- **Caption stroke 3px**: Wider stroke for readability against busy landscape backgrounds
- **Lower-third captions (88%)**: Cinematic standard for landscape video; avoids obstructing main visual content
- **Crossfade transitions**: Long-form benefits from flow; hard cuts feel jarring over 8-12 minutes
- **Dynamic music ducking**: Music auto-dips during intense voiceover, rises during visual pauses — adds production quality over flat volume

### 1.2 Script Generator — Gemini Long-Form

New function `generate_long_script()` in `script_generator.py`.

**Input:** Topic string (from 32 existing topics or Gemini-suggested trending topics)

**Output:** List of 40-60 segments, each containing:
```python
{
    "text": str,              # Voiceover text for this segment
    "visual_keywords": str,   # Stock footage search query
    "mood": str,              # Visual mood (dark, intense, reflective, powerful)
    "emphasis_words": list,   # Words to highlight in captions
    "chapter": str | None,    # YouTube chapter title (every 5-8 segments)
}
```

**Gemini prompt engineering:**
- Voice: stoic, dark motivation, no fluff, no clichés, short punchy sentences even in long-form
- Structure: hook (first 30s) → setup → escalation → climax → resolution → callback to opening hook
- Chapters: natural breakpoints every 60-90 seconds for YouTube chapter markers
- Calibrated against `brand_reference.py` voice guidelines

**API:** Gemini 2.5 Flash (cost-effective for long text generation, high quality)

**Existing `generate_script()`** for 9:16 shorts remains untouched.

### 1.3 Video Assembler Changes

**New `fit_to_horizontal()` function:**
- Same crop-to-fit approach as `fit_to_vertical()` — no black bars, no padding
- Target: 1920x1080
- Landscape footage fills perfectly
- Portrait footage: resized by height, center-cropped horizontally

**Crossfade transitions (long-form only):**
- 0.5s crossfade between segments
- Smooth visual flow for 8-12 minute runtime
- Short-form keeps hard cuts (punchy, snappy)

**Dynamic music ducking (long-form only):**
- Analyze voiceover amplitude per segment
- During voiceover: music at 25% volume
- During pauses/transitions: music rises to 45% volume
- Smooth 0.3s ramp between levels
- Short-form keeps flat 32% (simpler, works for 60-90s)

**Chapter metadata (long-form only):**
- Extract chapter titles and timestamps from script segments
- Embed in MP4 metadata for YouTube auto-chapters
- Also output as text for video description

**Format-aware assembly:**
- `assemble_video(segments, format=VideoFormat)` selects:
  - `fit_to_horizontal()` or `fit_to_vertical()`
  - Transition style
  - Music mixing mode
  - Export bitrate and settings

### 1.4 Visuals Changes

**Orientation switching:**
- `HORIZONTAL_LONG` → Pexels `orientation="landscape"`, Pixabay landscape filter
- Existing portrait search unchanged for shorts

**Longer clips for long-form:**
- Short-form: 3-5s per segment clip (existing)
- Long-form: 8-15s per segment clip — less jarring, more cinematic pacing
- Prefer longer source videos from Pexels (filter by duration)

**Enhanced deduplication:**
- 8-12 min videos need 40-60 unique clips
- Broader keyword variety per segment (Gemini `visual_keywords` already diverse)
- Track used video IDs across entire generation run
- Expanded fallback queries for landscape-appropriate footage (cityscapes, mountains, oceans, architecture, storms, forests)

### 1.5 Voiceover Changes

**Speech rate per format:**
- Short-form: existing ElevenLabs settings (stability 0.50)
- Long-form: stability bumped to 0.55 for more gravitas over 8-12 minutes
- Slightly slower pacing suits narrative long-form delivery

No structural changes — ElevenLabs handles any script length via chunked generation.

### 1.6 Entry Points

**CLI (`main.py`):**
```
python main.py                          # Default: 9:16 short (backwards compatible)
python main.py --format short           # Explicit: 9:16 short
python main.py --format long            # New: 16:9 long-form
python main.py --format long --topic "discipline"  # Long-form with specific topic
```

**Gradio (`app.py`):**
- New format dropdown: "Vertical Short (9:16)" / "Horizontal Long (16:9)"
- Duration estimate updates based on selection
- Progress steps adjusted for long-form (more segments = more steps)

**Web frontend (`page.tsx`):**
- Format selector toggle/dropdown on generation page
- Video player aspect ratio switches based on format

---

## Feature 2: Scheduled Posting with Review Queue

### 2.1 Queue System

**Storage:** `queue.json` file in project root (simple, no DB dependency)

**Queue entry schema:**
```python
{
    "id": str,                    # UUID
    "format": "short" | "long",
    "topic": str,
    "video_path": str,            # Path to generated MP4
    "thumbnail_path": str,        # Auto-generated thumbnail
    "metadata": {
        "youtube": {
            "title": str,
            "description": str,
            "tags": list[str],
            "chapters": list[{"time": str, "title": str}],
            "category": str,
        },
        "tiktok": {
            "caption": str,
            "hashtags": list[str],
        },
        "instagram": {
            "caption": str,
            "hashtags": list[str],
        },
        "facebook": {
            "description": str,
        }
    },
    "target_platforms": list[str], # Which platforms to post to
    "status": str,                 # pending_review | approved | posting | posted | rejected | failed
    "created_at": str,             # ISO timestamp
    "scheduled_post_time": str,    # When to post (after approval)
    "post_results": {              # Filled after posting
        "youtube": {"url": str, "video_id": str},
        "tiktok": {"url": str},
        "instagram": {"url": str},
        "facebook": {"url": str},
    },
    "error": str | None,
}
```

### 2.2 Scheduler

**`scheduler.py`** — Cron-triggered video generation.

**Schedule configuration (in config or .env):**
```python
SCHEDULE_LONG_FORM = "0 2 * * 1,4"     # Mon/Thu at 2 AM (long-form)
SCHEDULE_SHORT_FORM = "0 3 * * *"       # Daily at 3 AM (shorts)
```

**Behavior:**
1. Cron fires → scheduler picks topic (rotating from 32 topics + Gemini trending suggestions)
2. Runs full pipeline for the scheduled format
3. Auto-generates platform-specific metadata via Gemini
4. Auto-generates thumbnail (best frame extraction + title overlay)
5. Saves entry to queue with status `pending_review`
6. Sends notification (optional: email or push) that a new video is ready for review

**Topic rotation:**
- Tracks previously used topics to avoid repetition
- Can request Gemini to suggest trending/seasonal topics
- Manual topic override via queue or dashboard

### 2.3 Metadata Generator

**`metadata_generator.py`** — Gemini-powered, platform-optimized metadata.

Per platform, Gemini generates:

**YouTube:**
- SEO-optimized title (60 chars max, keyword-front-loaded)
- Description with chapters, keywords, CTA, links
- 15-20 relevant tags
- Category suggestion

**TikTok:**
- Short caption (150 chars max)
- 5-8 trending + niche hashtags
- Hook line for the caption

**Instagram:**
- Caption with line breaks, hook, CTA (2200 char max)
- 20-30 hashtags (mix of broad + niche)
- Reel cover text suggestion

**Facebook:**
- Description with hook and CTA
- 3-5 hashtags (Facebook favors fewer)

### 2.4 Thumbnail Generator

**`thumbnail.py`** — Auto-generated thumbnails for each video.

**Process:**
1. Extract 10 candidate frames evenly spaced through the video
2. Score each frame: contrast, visual interest, brightness (not too dark)
3. Select highest-scoring frame
4. Overlay: title text in Luminous Will amber (#E8A817) + dark gradient bar at bottom
5. Font: Arial Bold, sized for 1280x720 (YouTube standard)
6. Export as JPG, 1280x720

### 2.5 Publisher — 4 Platform Adapters

**`publisher.py`** — Orchestrator that calls platform-specific adapters.

**Common interface per adapter:**
```python
class PlatformAdapter:
    def authenticate(self) -> bool
    def upload(self, video_path, metadata) -> dict  # Returns {url, id}
    def check_status(self, post_id) -> str
    def refresh_token(self) -> bool
```

#### YouTube Adapter (`youtube_adapter.py`)
- **API:** YouTube Data API v3
- **Auth:** OAuth2 (one-time consent flow via web UI)
- **Upload:** Resumable upload (handles large 8-12 min files)
- **Metadata:** Title, description, tags, category, chapters in description, thumbnail upload, privacy (unlisted → public on schedule)
- **Token refresh:** Hourly expiry, auto-refresh via refresh token

#### TikTok Adapter (`tiktok_adapter.py`)
- **API:** TikTok Content Posting API
- **Auth:** OAuth2 (creator account required + app approval)
- **Upload:** Direct post API for 9:16 videos under 10 min
- **Metadata:** Caption with hashtags
- **Token refresh:** 24-hour expiry, auto-refresh

#### Instagram Adapter (`instagram_adapter.py`)
- **API:** Instagram Graph API (via Facebook Developer)
- **Auth:** Facebook OAuth2 (Business/Creator account required)
- **Upload:** Container-based flow (create container → upload → publish)
- **Metadata:** Caption with hashtags, Reel cover
- **Token refresh:** 60-day long-lived tokens, auto-refresh

#### Facebook Adapter (`facebook_adapter.py`)
- **API:** Facebook Graph API
- **Auth:** Same Facebook OAuth2 as Instagram (shared app credentials)
- **Upload:** Video upload to Page or profile
- **Metadata:** Description with hashtags
- **Token refresh:** Same 60-day tokens as Instagram

### 2.6 Web Dashboard (luminous-will-web)

**New `/dashboard` route** — Review queue and publishing control center.

**Queue View:**
- List of all videos with status badges (pending, approved, posted, rejected)
- Thumbnail preview, topic, format, creation date
- Filter by status, format, platform
- Sort by date

**Video Review Panel (click into a queue entry):**
- Video player (correct aspect ratio per format)
- Editable fields: title, description, hashtags (per platform tabs)
- Platform checkboxes: which platforms to post to
- Schedule picker: set post date/time
- Actions: Approve, Reject, Delete
- On approve: status → `approved`, publisher picks it up at scheduled time

**Platform Connections:**
- Settings page with OAuth connect buttons for each platform
- Status indicators: connected/disconnected/token expiring
- One-time setup per platform

**Posted Videos:**
- Post URLs (clickable links to each platform)
- Post date and platform
- Basic engagement stats if APIs support it (views, likes — YouTube and TikTok provide this)

**Schedule Calendar:**
- Monthly/weekly view showing upcoming scheduled posts
- Drag to reschedule
- Color-coded by platform and format

### 2.7 OAuth Flow

**One-time setup per platform via web UI:**

1. User clicks "Connect YouTube" in dashboard settings
2. Redirected to Google/TikTok/Facebook consent screen
3. Grants permissions (upload, manage videos)
4. Callback returns auth code → exchanged for access + refresh tokens
5. Tokens stored in `.env` or secure environment variables
6. Dashboard shows "Connected" status

**Token management:**
- Each adapter handles its own refresh schedule
- YouTube: refresh before each upload (hourly expiry)
- TikTok: refresh daily
- Facebook/Instagram: refresh every 55 days (before 60-day expiry)
- Failed refresh → dashboard shows warning, re-auth required

---

## Files Changed / Created

### LuminousWill (local pipeline)

**Modified:**
- `config.py` — VideoFormat enum, dual format profiles, schedule config, Gemini API key
- `script_generator.py` — New `generate_long_script()` with Gemini
- `video_assembler.py` — `fit_to_horizontal()`, crossfades, dynamic ducking, format branching
- `visuals.py` — Landscape search, longer clips, enhanced dedup
- `voiceover.py` — Speech rate config per format
- `main.py` — `--format` flag, scheduler integration
- `requirements.txt` — Add google-generativeai, google-auth, google-api-python-client, requests-oauthlib

**New:**
- `scheduler.py` — Cron-triggered generation
- `publisher.py` — Upload orchestrator
- `youtube_adapter.py` — YouTube Data API v3 adapter
- `tiktok_adapter.py` — TikTok Content Posting API adapter
- `instagram_adapter.py` — Instagram Graph API adapter
- `facebook_adapter.py` — Facebook Graph API adapter
- `queue.py` — Queue read/write/update operations
- `metadata_generator.py` — Gemini metadata generation per platform
- `thumbnail.py` — Auto thumbnail extraction and overlay
- `queue.json` — Queue data file (gitignored)

### luminous-will-api (Gradio)

**Modified:**
- `app.py` — Format dropdown, updated progress steps
- `config.py` — Same format system as local
- All pipeline modules synced from local

### luminous-will-web (Next.js)

**Modified:**
- `app/page.tsx` — Format selector on generation page, aspect-ratio-aware player

**New:**
- `app/dashboard/page.tsx` — Review queue list view
- `app/dashboard/[id]/page.tsx` — Single video review/edit panel
- `app/dashboard/calendar/page.tsx` — Schedule calendar view
- `app/dashboard/settings/page.tsx` — Platform OAuth connections
- `app/api/queue/route.ts` — Queue CRUD API routes
- `app/api/queue/[id]/approve/route.ts` — Approve endpoint
- `app/api/queue/[id]/reject/route.ts` — Reject endpoint
- `app/api/auth/[platform]/route.ts` — OAuth callback handlers
- `app/api/publish/route.ts` — Trigger publish for approved videos
- `lib/queue.ts` — Queue operations (read/write queue.json)
- `lib/platforms.ts` — Platform connection status checks
- `components/VideoReviewCard.tsx` — Queue list item component
- `components/MetadataEditor.tsx` — Per-platform metadata editing
- `components/PlatformSelector.tsx` — Platform checkboxes with status
- `components/SchedulePicker.tsx` — Date/time picker for post scheduling
- `components/CalendarView.tsx` — Monthly schedule calendar

---

## Dependencies

**New Python packages:**
- `google-generativeai` — Gemini API for long-form scripts + metadata
- `google-api-python-client` — YouTube Data API v3
- `google-auth-oauthlib` — Google OAuth2 flow
- `requests-oauthlib` — OAuth2 for TikTok/Facebook
- `Pillow` — Thumbnail text overlay (likely already installed via MoviePy)
- `schedule` or system cron — Scheduler trigger

**New npm packages (luminous-will-web):**
- `react-calendar` or similar — Schedule calendar view
- `date-fns` — Date formatting and manipulation

**API accounts required (one-time setup):**
- Google Cloud Console project with YouTube Data API v3 enabled
- TikTok Developer account + approved app
- Facebook Developer account + app with Instagram Graph API access
- Gemini API key (Google AI Studio)

---

## Out of Scope

- Analytics dashboard (engagement metrics beyond basic stats)
- A/B testing thumbnails or titles
- Multi-account support (one account per platform)
- Comment management or community engagement
- Live streaming
- Monetization tracking
