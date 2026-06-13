import json
import config
import google.generativeai as genai

# ============================================================
# METADATA GENERATOR
# Uses Gemini to generate platform-optimized titles, descriptions,
# hashtags, and SEO metadata for each social platform
# ============================================================


def generate_metadata(topic, script_segments, video_format, chapters=None):
    # Generates platform-specific metadata for all 4 platforms
    # Returns dict keyed by platform name

    if not config.GEMINI_API_KEY:
        return _fallback_metadata(topic, video_format)

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Build script summary for context
    script_text = " ".join([s["text"] for s in script_segments[:10]])
    chapter_text = ""
    if chapters:
        chapter_text = "\n".join([f"{c['time']} - {c['title']}" for c in chapters])

    prompt = f"""Generate social media metadata for a dark motivation video.

TOPIC: {topic}
FORMAT: {"YouTube long-form (8-12 min)" if video_format == "long" else "Short-form vertical (60-90s)"}
SCRIPT EXCERPT: {script_text[:500]}
{"CHAPTERS:\n" + chapter_text if chapter_text else ""}

BRAND: Luminous Will — stoic, dark psychology, power, self-improvement. No emojis. No fluff.

Generate metadata for ALL 4 platforms. Respond with ONLY a JSON object:

{{
  "youtube": {{
    "title": "SEO title, max 60 chars, keyword-front-loaded",
    "description": "Full description with SEO keywords, chapters, and CTA. Max 2000 chars.",
    "tags": ["15-20 relevant tags"],
    "category": "Education or People & Blogs"
  }},
  "tiktok": {{
    "caption": "Short hook caption, max 150 chars",
    "hashtags": ["5-8 trending + niche hashtags"]
  }},
  "instagram": {{
    "caption": "Caption with hook, body, CTA. Max 2200 chars. Line breaks for readability.",
    "hashtags": ["20-30 hashtags mix of broad and niche"]
  }},
  "facebook": {{
    "description": "Description with hook and CTA. 3-5 hashtags inline.",
    "hashtags": ["3-5 hashtags"]
  }}
}}"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        metadata = json.loads(raw)
        print(f"[METADATA] Generated metadata for all platforms")
        return metadata

    except Exception as e:
        print(f"[METADATA] Gemini error: {e}, using fallback")
        return _fallback_metadata(topic, video_format)


def _fallback_metadata(topic, video_format):
    # Basic metadata when Gemini is unavailable
    base_tags = ["motivation", "darkpsychology", "stoic", "mindset", "selfimprovement",
                 "discipline", "mentalstrength", "success", "psychology", "power"]

    return {
        "youtube": {
            "title": f"{topic} | Luminous Will",
            "description": f"{topic}\n\nDark motivation for the disciplined mind.\n\n#LuminousWill #DarkMotivation #Stoic",
            "tags": base_tags + [topic.lower().replace(" ", "")],
            "category": "Education",
        },
        "tiktok": {
            "caption": f"{topic}",
            "hashtags": base_tags[:8],
        },
        "instagram": {
            "caption": f"{topic}\n\nFollow @luminouswill for more.",
            "hashtags": base_tags + ["reels", "motivationaldaily", "mindsetshift"],
        },
        "facebook": {
            "description": f"{topic}\n\n#motivation #darkpsychology #stoic",
            "hashtags": base_tags[:5],
        },
    }
