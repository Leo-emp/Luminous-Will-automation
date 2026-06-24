import random
import json
import os
import config
import google.generativeai as genai
from datetime import date

# ============================================================
# SCRIPT GENERATOR — TASK 10 REWRITE
# Both short-form AND long-form now use Gemini AI
# No more template scripts — every video is unique
#
# Key features:
#   - Gemini-powered generation for both video formats
#   - History tracking in generated_history.json
#   - Hook quality validation (_is_strong_hook)
#   - Motion style heuristics per segment
#   - Emergency fallback (10 pre-written hooks, NO templates)
# ============================================================


# --- Path to the history file at the project root ---
# This file tracks every video we've generated to avoid repetition
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_history.json")


# ============================================================
# EMERGENCY FALLBACK HOOKS
# Only used when Gemini API is completely down.
# These are strong, scroll-stopping hooks with "you" or emotional triggers.
# NOT the old template scripts — these are minimal safety nets only.
# ============================================================
EMERGENCY_HOOKS = [
    "You were never meant to be average.",
    "Your brain is being hijacked right now.",
    "Comfort is killing your potential slowly.",
    "You're not lazy — you're scared.",
    "Your emotions are being used against you.",
    "The most dangerous thing you can do is stay the same.",
    "Most people are loyal to their needs, not to you.",
    "You don't need anyone's permission to become great.",
    "You're living in the wrong timeline.",
    "The silence you fear is the power you need.",
]


# ============================================================
# HISTORY MANAGEMENT
# Tracks all videos we've generated so we avoid repeating the
# same topic, hook, or angle too soon.
# ============================================================

def load_generated_history():
    """
    # Loads the video generation history from generated_history.json
    # Returns a list of dicts, each with: topic, hook, angle, date
    # If the file doesn't exist yet, returns an empty list
    """
    if not os.path.exists(HISTORY_FILE):
        # --- File doesn't exist yet — return empty history ---
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        return history
    except (json.JSONDecodeError, IOError) as e:
        # --- Corrupted or unreadable file — return empty rather than crash ---
        print(f"[HISTORY] Warning: could not load history file: {e}")
        return []


def save_to_history(topic, hook, angle):
    """
    # Saves a new entry to generated_history.json
    # Called after every successful script generation
    # Appends to the existing list (never overwrites old entries)
    #
    # Args:
    #   topic (str): the video topic (e.g. "Power of Silence")
    #   hook  (str): the opening hook sentence
    #   angle (str): the psychological angle (e.g. "silence as power tool")
    """
    history = load_generated_history()

    # --- Build the new entry with today's date ---
    new_entry = {
        "topic": topic,
        "hook": hook,
        "angle": angle,
        "date": str(date.today()),
    }

    history.append(new_entry)

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        print(f"[HISTORY] Saved entry: {topic}")
    except IOError as e:
        # --- Can't write history — not a fatal error, just warn ---
        print(f"[HISTORY] Warning: could not save history: {e}")


# ============================================================
# HOOK QUALITY VALIDATION
# A "strong" hook directly addresses the viewer or triggers emotion.
# Generic philosophical statements are weak — they don't stop the scroll.
# ============================================================

def _is_strong_hook(text):
    """
    # Checks if a hook is strong enough for dark motivation content.
    # A strong hook must contain at least one of:
    #   - Personal address: "you" or "your" (speaks directly to the viewer)
    #   - Emotional trigger words (creates psychological tension)
    #
    # Returns True if strong, False if generic/weak
    #
    # Examples:
    #   Strong: "You're not lazy, you're scared"  (has "you")
    #   Strong: "This is slowly killing your potential"  (has emotional trigger + "your")
    #   Weak:   "Life is about choices"  (no personal address, no trigger)
    """

    # --- Normalize to lowercase for easy matching ---
    lower = text.lower()

    # --- Check for personal/direct address ---
    # These words connect the hook directly to the viewer
    personal_words = ["you", "your"]
    for word in personal_words:
        # Match whole words only — "your" shouldn't match "yours" accidentally
        # Simple approach: check if " you " or starts with "you"
        if f" {word} " in f" {lower} " or lower.startswith(word):
            return True

    # --- Check for emotional trigger words ---
    # These words create psychological tension and make people stop scrolling
    emotional_triggers = [
        "scared", "alone", "silence", "killing", "dangerous",
        "dying", "fear", "threat", "hijacked", "trap",
        "destroying", "wired", "rewired", "broken", "manipulated",
        "toxic", "weak", "failing", "dead", "lost",
        "betrayal", "secret", "truth", "lie", "lied",
        "never", "stop", "warning", "urgent", "critical",
    ]
    for trigger in emotional_triggers:
        if trigger in lower:
            return True

    # --- No personal address and no emotional trigger found — weak hook ---
    return False


# ============================================================
# MOTION STYLE HEURISTICS
# Determines the Ken Burns motion effect based on visual content.
# This is used by the video assembler (Task 6) to add cinematic movement.
# ============================================================

def _infer_motion_style(visual_keywords):
    """
    # Infers the best Ken Burns motion style from a segment's visual keywords.
    #
    # Three styles:
    #   "ken_burns_pan"  — slow sideways drift, good for wide landscapes
    #   "ken_burns_zoom" — slow push-in, good for portraits and close-ups
    #   "static"         — no movement, good for action footage that already moves
    #
    # Logic:
    #   landscape/nature/mountain/ocean/clouds → ken_burns_pan
    #   portrait/face/silhouette/close-up      → ken_burns_zoom
    #   action/running/training/fighting       → static
    #   default                                → static
    #
    # Args:
    #   visual_keywords (str): the search keywords for this segment
    #
    # Returns: "ken_burns_pan" | "ken_burns_zoom" | "static"
    """

    # --- Normalize for matching ---
    lower = visual_keywords.lower()

    # --- Action keywords → footage already has natural motion, keep static ---
    # Adding Ken Burns on top of fast-moving clips looks bad
    action_keywords = [
        "running", "boxing", "training", "fighting", "sprint",
        "action", "workout", "exercise", "punching", "climbing",
        "jumping", "driving fast", "racing",
    ]
    for kw in action_keywords:
        if kw in lower:
            return "static"

    # --- Landscape/nature keywords → pan slowly across the wide scene ---
    # Mountains, oceans, cityscapes all look great with a horizontal drift
    landscape_keywords = [
        "landscape", "mountain", "ocean", "clouds", "nature",
        "forest", "valley", "horizon", "field", "sky",
        "cityscape", "aerial", "highway", "desert", "river",
    ]
    for kw in landscape_keywords:
        if kw in lower:
            return "ken_burns_pan"

    # --- Portrait/close-up keywords → slow zoom in for intimacy ---
    # Faces, silhouettes, and close subjects feel more intense with a push-in
    portrait_keywords = [
        "portrait", "face", "silhouette", "close-up", "close up",
        "closeup", "man standing", "man sitting", "person",
        "eyes", "hands", "chess board",
    ]
    for kw in portrait_keywords:
        if kw in lower:
            return "ken_burns_zoom"

    # --- Default: static is always safe ---
    return "static"


# ============================================================
# SHORT-FORM HEURISTIC ENRICHMENT
# Adds motion_style and transition fields to segments that came
# from Gemini without those fields (e.g. when Gemini generates
# short-form scripts without per-segment transition choices)
# ============================================================

def _build_short_form_heuristics(segments):
    """
    # Adds motion_style and transition fields to short-form segments
    # based on visual_keywords and mood changes between segments.
    #
    # Called after Gemini returns a short-form script, OR on any
    # segment list that's missing these fields.
    #
    # Transition logic:
    #   - mood changes between segments → "crossfade" (smooth blend)
    #   - same mood → "cut" (sharp, energetic)
    #   - last segment always → "crossfade" (softer ending)
    #
    # Args:
    #   segments (list[dict]): script segments, each with at minimum
    #                          "visual_keywords" and "mood" fields
    #
    # Returns: the same list with motion_style and transition added
    """

    enriched = []

    for i, seg in enumerate(segments):
        # --- Copy the segment so we don't mutate the original ---
        s = dict(seg)

        # --- Infer motion style from visual keywords ---
        visual_keywords = s.get("visual_keywords", "")
        s["motion_style"] = _infer_motion_style(visual_keywords)

        # --- Choose transition based on mood change ---
        # If the next segment has a different mood, crossfade smoothly
        # If same mood, a sharp cut keeps the energy high
        current_mood = s.get("mood", "dark")
        is_last = (i == len(segments) - 1)

        if is_last:
            # --- Always end with a crossfade for a softer finish ---
            s["transition"] = "crossfade"
        else:
            next_mood = segments[i + 1].get("mood", "dark")
            if current_mood != next_mood:
                # --- Mood shift → smooth crossfade to signal the change ---
                s["transition"] = "crossfade"
            else:
                # --- Same mood → sharp cut keeps the intensity ---
                s["transition"] = "cut"

        enriched.append(s)

    return enriched


# ============================================================
# TOPIC DISCOVERY
# Uses Gemini to discover fresh viral topic ideas based on
# what's already been done (from history) and trending niches.
# ============================================================

def discover_topics():
    """
    # Uses Gemini to discover new viral topic ideas for dark motivation content.
    # Avoids topics already in the generation history.
    #
    # Returns: list of topic strings (typically 10-15 suggestions)
    # Fallback: returns config.TRENDING_TOPICS if Gemini is unavailable
    """

    if not config.GEMINI_API_KEY:
        # --- No API key — return the built-in topic list ---
        print("[TOPICS] No Gemini API key, returning built-in topics")
        return config.TRENDING_TOPICS

    # --- Get topics we've already covered to avoid repetition ---
    history = load_generated_history()
    used_topics = [entry["topic"] for entry in history]

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""You are a content strategist for "Luminous Will" — a dark motivation YouTube/TikTok channel.

CHANNEL NICHE: Dark psychology, stoic philosophy, power dynamics, self-mastery.
BRAND TONE: Intense, commanding, no fluff. Speaks to people who want to level up.

TOPICS ALREADY USED (avoid these):
{json.dumps(used_topics, indent=2)}

Generate 12 fresh viral topic ideas for short-form dark motivation videos (60-90 seconds).
Each topic should be:
- Specific (not vague like "mindset tips")
- Psychologically interesting
- Relatable to young ambitious adults (18-35)
- Different from the used topics above

OUTPUT FORMAT — respond with ONLY a JSON array of strings, no markdown:
["Topic idea 1", "Topic idea 2", ...]"""

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # --- Strip markdown fences if Gemini added them ---
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

        topics = json.loads(raw_text)
        print(f"[TOPICS] Discovered {len(topics)} new topics via Gemini")
        return topics

    except Exception as e:
        print(f"[TOPICS] Topic discovery failed: {e}")
        print("[TOPICS] Falling back to built-in topics")
        return config.TRENDING_TOPICS


# ============================================================
# EMERGENCY FALLBACK SCRIPT BUILDER
# Only runs when Gemini API is completely down.
# Uses the 10 pre-written emergency hooks + generic dark segments.
# This is NOT the old template approach — it's a minimal safety net.
# ============================================================

def _build_emergency_script(topic, num_segments=25):
    """
    # Emergency fallback when Gemini is completely unavailable.
    # Builds a minimal but usable script from:
    #   - 10 pre-written strong hooks (see EMERGENCY_HOOKS above)
    #   - Generic dark motivation segments about the topic
    #
    # This is different from the old template approach:
    #   Old: 5 full pre-written scripts picked by topic name
    #   New: one random strong hook + generic segments (always works)
    #
    # Args:
    #   topic       (str): the video topic
    #   num_segments (int): how many segments to generate (default 25)
    #
    # Returns: list of segment dicts with all required fields
    """

    print(f"[SCRIPT] EMERGENCY: Building fallback script for '{topic}'")

    # --- Pick one of the 10 strong emergency hooks at random ---
    hook_text = random.choice(EMERGENCY_HOOKS)

    # --- Generic dark motivation sentences that work for any topic ---
    # These are universal truths that fit the brand voice
    generic_lines = [
        f"This is the truth about {topic} that nobody talks about.",
        "Most people will ignore this message.",
        "The ones who pay attention will change everything.",
        "You already know something is wrong.",
        "That feeling you have? It's a signal.",
        "The world rewards those who do the hard things.",
        "Every day you wait is a day someone else gets ahead.",
        "Your standards are either rising or falling.",
        "There is no neutral. You are either growing or shrinking.",
        "The weak ask for permission. The strong take action.",
        "Pain is temporary. Regret lasts forever.",
        "You are exactly where your decisions brought you.",
        "Change the decisions, change the destination.",
        "The version of you that succeeds already exists.",
        "You just have to become them.",
        "Stop asking when. Start asking how.",
        "Discipline is not a punishment. It is a gift you give yourself.",
        "The days you don't feel like it are the days that matter most.",
        "Your comfort zone is a beautiful place where nothing grows.",
        "What you allow, you teach the world to give you.",
        "Silence your critics by outworking them.",
        "The path is hard. Good. Hard paths build strong people.",
        "Start before you are ready.",
        "Finish what you started.",
        "Your future self is watching.",
    ]

    # --- Build the segments list ---
    segments = []

    # --- First segment is always the hook ---
    segments.append({
        "text": hook_text,
        "visual_keywords": "dark cinematic man silhouette dramatic",
        "visual_keywords_alt": [
            "dark dramatic cinematic opener",
            "man silhouette night powerful",
            "dark atmospheric moody cinematic",
        ],
        "mood": "intense",
        "emphasis_word": hook_text.split()[0],  # first word of hook
        "chapter": "Introduction",
        "motion_style": "ken_burns_zoom",
        "transition": "cut",
    })

    # --- Fill remaining segments with generic lines ---
    # Shuffle so the order is different each time
    shuffled = generic_lines[:]
    random.shuffle(shuffled)

    for i, line in enumerate(shuffled[:num_segments - 1]):
        # --- Alternate moods to create variety ---
        mood_cycle = ["dark", "intense", "reflective", "powerful"]
        mood = mood_cycle[i % len(mood_cycle)]

        # --- Visual keywords rotate through dark cinematic themes ---
        visual_options = [
            "dark storm clouds cinematic dramatic",
            "man walking alone dark city night",
            "wolf forest night dark cinematic",
            "dark mountain peak clouds fog",
            "chess board dark cinematic strategy",
            "athlete training dark gym silhouette",
            "ocean waves dark cinematic slow motion",
            "man silhouette rooftop night dark",
        ]
        visual = visual_options[i % len(visual_options)]

        segments.append({
            "text": line,
            "visual_keywords": visual,
            "visual_keywords_alt": [],
            "mood": mood,
            "emphasis_word": "",
            "chapter": None,
            "motion_style": _infer_motion_style(visual),
            "transition": "crossfade" if mood == "reflective" else "cut",
        })

    print(f"[SCRIPT] Emergency fallback: {len(segments)} segments built")
    return segments


# ============================================================
# SHORT-FORM GEMINI SCRIPT GENERATION
# 25 segments, 60-90s total, punchy dark motivation
# ============================================================

def _generate_short_script_gemini(topic, custom_hook=None):
    """
    # Generates a short-form (60-90s) script using Gemini AI.
    # Returns 25 segments with hook validation and motion heuristics.
    #
    # If custom_hook is provided, Gemini will use it as the opener.
    # If not, Gemini chooses its own hook, which we then validate.
    # If the hook is weak, we regenerate or substitute an emergency hook.
    #
    # Args:
    #   topic       (str): the video topic
    #   custom_hook (str): optional override for the first segment
    #
    # Returns: list of 25 segment dicts
    """

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # --- Build hook instruction for the prompt ---
    # If caller supplied a hook, lock Gemini to use it
    # Otherwise let Gemini create one (we validate it after)
    if custom_hook:
        hook_instruction = f'USE THIS EXACT HOOK as the first segment text: "{custom_hook}"'
    else:
        hook_instruction = (
            "Create a POWERFUL opening hook that:\n"
            "- Directly addresses the viewer using 'you' or 'your'\n"
            "- OR contains a shocking emotional trigger word\n"
            "- Is ONE sentence, max 12 words\n"
            "- Makes someone stop scrolling immediately"
        )

    prompt = f"""You are a scriptwriter for "Luminous Will" — dark motivation, stoic philosophy, psychology of power.

VOICE RULES:
- Stoic, commanding. Short punchy sentences (max 15 words each).
- No fluff, no clichés ("grind", "hustle", "manifest"), no questions to audience.
- Speak in universal truths. Use "you" and "they". Never say "I" or "we".
- Dark, intense energy. The tone of someone who has seen the worst and emerged stronger.
- Simple language — 8th grade reading level. Short Anglo-Saxon words over Latin ones.

TASK: Generate a 60-90 second short-form video script on the topic: "{topic}"

OPENING HOOK:
{hook_instruction}

STRUCTURE (25 segments total):
- Segment 1: Hook — one shocking sentence that stops the scroll
- Segments 2-5: Setup — frame the problem, make it personal
- Segments 6-16: Core — dark truths, uncomfortable revelations, build intensity
- Segments 17-22: Turn — the wake-up call, the shift in perspective
- Segments 23-25: Close — call to action, final power statement

Generate exactly 25 segments. Each segment is ONE sentence (max 15 words).

OUTPUT FORMAT — respond with ONLY a JSON array, no markdown, no explanation:
[
  {{
    "text": "The sentence spoken in the voiceover.",
    "visual_keywords": "5-6 keywords for stock footage search (portrait orientation, dark cinematic)",
    "mood": "dark|intense|reflective|powerful",
    "emphasis_word": "one_key_word"
  }},
  ...
]

VISUAL KEYWORD RULES:
- Always include "dark" or "cinematic" in keywords
- Use portrait-oriented subjects for vertical video: man standing, silhouette, close-up face, person walking
- Preferred subjects: dark silhouette portrait, man walking dark night, person alone dark, wolf forest dark, lion savanna dark, chess board dark, gym training dark, rain window dark, fire flames dark
- Vary subjects — no two consecutive segments with the same visual theme

Generate the script now. 25 segments, JSON array only."""

    response = model.generate_content(prompt)
    raw_text = response.text.strip()

    # --- Strip markdown code fences if Gemini added them ---
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

    segments_raw = json.loads(raw_text)

    # --- Validate and normalize segment structure ---
    validated = []
    for seg in segments_raw:
        validated.append({
            "text": str(seg.get("text", "")),
            "visual_keywords": str(seg.get("visual_keywords", "dark cinematic silhouette")),
            "visual_keywords_alt": [],  # enriched separately by enrich_visual_keywords()
            "mood": str(seg.get("mood", "dark")),
            "emphasis_word": str(seg.get("emphasis_word", "")),
            "chapter": None,  # short-form has no chapters
        })

    # --- Hook validation ---
    # Check if the first segment's hook is actually strong
    if validated and not _is_strong_hook(validated[0]["text"]):
        print(f"[SCRIPT] Hook validation failed: '{validated[0]['text']}'")
        print("[SCRIPT] Substituting emergency hook...")
        # Pick an emergency hook and inject it into the first segment
        validated[0]["text"] = random.choice(EMERGENCY_HOOKS)

    # --- Add motion_style and transition via heuristics ---
    # Gemini doesn't pick transitions for short-form — we do it here
    validated = _build_short_form_heuristics(validated)

    print(f"[SCRIPT] Short-form: {len(validated)} segments generated via Gemini")
    return validated


# ============================================================
# LONG-FORM GEMINI SCRIPT GENERATION
# 50 segments, 8-12 min narrative arc, chapter markers
# ============================================================

def _generate_long_script_gemini(topic):
    """
    # Generates a long-form (8-12 min) script using Gemini AI.
    # Returns 50 segments with narrative arc structure:
    #   hook -> setup -> escalation -> climax -> resolution -> callback
    # Each segment includes chapter markers, motion_style, and transition.
    #
    # Args:
    #   topic (str): the video topic
    #
    # Returns: list of 50 segment dicts
    """

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""You are a scriptwriter for the YouTube channel "Luminous Will" — dark motivation, stoic philosophy, psychology of power.

VOICE RULES:
- Stoic, commanding, no-nonsense. Short punchy sentences even in long form.
- No fluff, no clichés ("grind", "hustle", "manifest"), no questions to the audience.
- Speak in universal truths. Never say "I" or "we". Use "you" and "they".
- Dark, intense energy. The tone of someone who has seen the worst and emerged stronger.
- Simple language — 8th grade reading level.

STRUCTURE for an 8-12 minute script on "{topic}":
1. HOOK (first 30 seconds) — One shocking statement that stops the scroll
2. SETUP (1-2 min) — Frame the problem, make it personal
3. ESCALATION (3-4 min) — Go deeper, reveal uncomfortable truths, build intensity
4. CLIMAX (2-3 min) — The turning point, the harsh lesson, the wake-up call
5. RESOLUTION (1-2 min) — The path forward, actionable transformation
6. CALLBACK (30 seconds) — Circle back to the opening hook with new meaning

Generate exactly 50 segments. Each segment is ONE sentence (max 20 words).

CHAPTER MARKERS: Insert a chapter title every 6-8 segments (for YouTube chapters). Set chapter to null for non-chapter segments.

OUTPUT FORMAT — respond with ONLY a JSON array, no markdown, no explanation:
[
  {{
    "text": "The sentence spoken in the voiceover.",
    "visual_keywords": "5-6 keywords for stock footage search (landscape orientation, dark cinematic)",
    "visual_keywords_alt": [
      "alternative search query 1 — different angle on same visual concept",
      "alternative search query 2 — broader or abstract version",
      "alternative search query 3 — concrete subject that matches the mood"
    ],
    "mood": "dark|intense|reflective|powerful",
    "emphasis_word": "one_key_word",
    "motion_style": "ken_burns_pan|ken_burns_zoom|static",
    "transition": "crossfade|cut",
    "chapter": "Chapter Title Here or null"
  }},
  ...
]

VISUAL KEYWORD RULES:
- Always include "dark" or "cinematic" in keywords
- Use landscape-oriented subjects for horizontal video: cityscapes, mountains, oceans, highways, architecture, storms
- Vary subjects — no two consecutive segments with the same visual theme
- Preferred subjects: dark cityscape night, storm clouds dramatic, mountain peak dark, ocean waves cinematic, businessman walking dark, wolf forest night, lion savanna dark, chess board dark, gym training dark, running athlete silhouette

MOTION STYLE GUIDE:
- ken_burns_pan: slow sideways drift — good for wide landscapes, cityscapes, mountain scenes
- ken_burns_zoom: slow push-in — good for portraits, silhouettes, close-up subjects
- static: no camera movement — good for action footage that already has motion (running, boxing, training)

TRANSITION GUIDE:
- crossfade: smooth blend — use when mood shifts between segments
- cut: sharp edit — use within the same mood for intensity

Generate the script now. 50 segments, JSON array only."""

    response = model.generate_content(prompt)
    raw_text = response.text.strip()

    # --- Strip markdown code fences if Gemini added them ---
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

    segments_raw = json.loads(raw_text)

    # --- Validate and normalize each segment ---
    validated = []
    for seg in segments_raw:
        # --- Parse alt keywords list ---
        raw_alts = seg.get("visual_keywords_alt", [])
        alts = [str(a) for a in raw_alts if a] if isinstance(raw_alts, list) else []

        # --- Normalize motion_style: fallback to heuristic if Gemini didn't set it ---
        motion_style = str(seg.get("motion_style", "")).strip()
        if motion_style not in ("ken_burns_pan", "ken_burns_zoom", "static"):
            motion_style = _infer_motion_style(str(seg.get("visual_keywords", "")))

        # --- Normalize transition: fallback to "cut" if missing ---
        transition = str(seg.get("transition", "")).strip()
        if transition not in ("crossfade", "cut"):
            transition = "cut"

        validated.append({
            "text": str(seg.get("text", "")),
            "visual_keywords": str(seg.get("visual_keywords", "dark cinematic landscape")),
            "visual_keywords_alt": alts,
            "mood": str(seg.get("mood", "dark")),
            "emphasis_word": str(seg.get("emphasis_word", "")),
            "motion_style": motion_style,
            "transition": transition,
            "chapter": seg.get("chapter"),  # None or string
        })

    if len(validated) < 30:
        print(f"[SCRIPT] WARNING: Only {len(validated)} segments generated, expected 50")

    # --- Count chapter markers ---
    chapters = [s for s in validated if s.get("chapter")]
    print(f"[SCRIPT] Long-form: {len(validated)} segments, {len(chapters)} chapters")

    return validated


# ============================================================
# MAIN ENTRY POINT
# Called by other modules (main.py, queue_manager.py, etc.)
# Signature is unchanged from the original: (topic, custom_hook, video_format)
# ============================================================

def generate_script(topic=None, custom_hook=None, video_format=None):
    """
    # Main script generation function — called by all other modules.
    #
    # Generates a complete video script using Gemini AI.
    # Both short-form and long-form now use Gemini (no more templates).
    # Falls back to emergency script if Gemini API is completely down.
    #
    # Args:
    #   topic       (str|None): video topic; picks random from TRENDING_TOPICS if None
    #   custom_hook (str|None): custom opening hook; Gemini picks one if None
    #   video_format (VideoFormat|None): VERTICAL_SHORT or HORIZONTAL_LONG
    #                                    defaults to VERTICAL_SHORT if None
    #
    # Returns: (segments_list, topic_string)
    #   segments_list: list of dicts, each with:
    #     - text          (str): voiceover sentence
    #     - visual_keywords (str): stock footage search terms
    #     - visual_keywords_alt (list): 3 alternative search queries
    #     - mood          (str): dark|intense|reflective|powerful
    #     - emphasis_word (str): word to highlight in captions
    #     - motion_style  (str): ken_burns_pan|ken_burns_zoom|static
    #     - transition    (str): crossfade|cut
    #     - chapter       (str|None): YouTube chapter title (long-form only)
    #   topic_string: the final topic used (may differ from input if random)
    """

    # --- Import here to avoid circular import issues ---
    from config import VideoFormat

    # --- Pick a topic if none was given ---
    if topic is None:
        topic = random.choice(config.TRENDING_TOPICS)

    print(f"[SCRIPT] Generating script for: {topic}")
    print(f"[SCRIPT] Format: {video_format}")

    # --- Route to the right generator based on format ---
    if video_format == VideoFormat.HORIZONTAL_LONG:
        # --- Long-form: 50 segments, narrative arc, chapter markers ---
        segments, topic = _run_long_form(topic)
    else:
        # --- Short-form: 25 segments, punchy, 60-90s (default) ---
        segments, topic = _run_short_form(topic, custom_hook)

    return segments, topic


def _run_short_form(topic, custom_hook=None):
    """
    # Internal handler for short-form generation.
    # Calls Gemini, falls back to emergency if API is down.
    # Saves to history on success.
    #
    # Returns: (segments, topic)
    """

    if not config.GEMINI_API_KEY:
        # --- No API key configured at all — use emergency fallback ---
        print("[SCRIPT] WARNING: No Gemini API key, using emergency fallback")
        segments = _build_emergency_script(topic, num_segments=25)
        return segments, topic

    try:
        segments = _generate_short_script_gemini(topic, custom_hook)

        # --- Save to history on successful Gemini generation ---
        hook_text = segments[0]["text"] if segments else ""
        save_to_history(topic, hook_text, f"Gemini-generated on {date.today()}")

        return segments, topic

    except json.JSONDecodeError as e:
        # --- Gemini returned something that wasn't valid JSON ---
        print(f"[SCRIPT] JSON parse error from Gemini short-form: {e}")
        print("[SCRIPT] Using emergency fallback")
        segments = _build_emergency_script(topic, num_segments=25)
        return segments, topic

    except Exception as e:
        # --- Any other Gemini API error (quota, network, etc.) ---
        print(f"[SCRIPT] Gemini API error (short-form): {e}")
        print("[SCRIPT] Using emergency fallback")
        segments = _build_emergency_script(topic, num_segments=25)
        return segments, topic


def _run_long_form(topic):
    """
    # Internal handler for long-form generation.
    # Calls Gemini, falls back to emergency if API is down.
    # Saves to history on success.
    #
    # Returns: (segments, topic)
    """

    if not config.GEMINI_API_KEY:
        # --- No API key — use emergency fallback (50 segments) ---
        print("[SCRIPT] WARNING: No Gemini API key, using emergency fallback")
        segments = _build_emergency_script(topic, num_segments=50)
        return segments, topic

    try:
        segments = _generate_long_script_gemini(topic)

        # --- Save to history on success ---
        hook_text = segments[0]["text"] if segments else ""
        save_to_history(topic, hook_text, f"Gemini long-form on {date.today()}")

        return segments, topic

    except json.JSONDecodeError as e:
        print(f"[SCRIPT] JSON parse error from Gemini long-form: {e}")
        print("[SCRIPT] Using emergency fallback")
        segments = _build_emergency_script(topic, num_segments=50)
        return segments, topic

    except Exception as e:
        print(f"[SCRIPT] Gemini API error (long-form): {e}")
        print("[SCRIPT] Using emergency fallback")
        segments = _build_emergency_script(topic, num_segments=50)
        return segments, topic


# ============================================================
# VISUAL KEYWORD ENRICHMENT
# Batch-adds 3 alternative search queries per segment using Gemini.
# Runs AFTER the main script is generated, as a separate API call.
# ============================================================

def enrich_visual_keywords(segments):
    """
    # Batch-enriches ALL segments with alt visual keywords using Gemini.
    # Works for both short-form and long-form scripts.
    # Skips segments that already have visual_keywords_alt.
    # One API call for the entire video — efficient and consistent.
    #
    # Args:
    #   segments (list[dict]): script segments to enrich
    #
    # Returns: the same segments list with visual_keywords_alt populated
    """

    # --- Find segments missing alt keywords ---
    needs_enrichment = []
    for i, seg in enumerate(segments):
        if not seg.get("visual_keywords_alt"):
            needs_enrichment.append((i, seg))

    if not needs_enrichment:
        print("[SCRIPT] All segments already have alt keywords, skipping enrichment")
        return segments

    if not config.GEMINI_API_KEY:
        print("[SCRIPT] No Gemini API key, skipping visual keyword enrichment")
        return segments

    print(f"[SCRIPT] Enriching {len(needs_enrichment)} segments with alt visual keywords...")

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # --- Build the batch prompt with all segments that need alts ---
    segment_list = []
    for idx, seg in needs_enrichment:
        segment_list.append({
            "index": idx,
            "text": seg.get("text", ""),
            "visual_keywords": seg.get("visual_keywords", ""),
        })

    prompt = f"""You are a visual director for "Luminous Will" — a dark motivation YouTube channel.

For each script segment below, generate 3 ALTERNATIVE stock footage search queries.
Each alt must find footage that visually matches the spoken text and mood.

RULES:
- Every query MUST include "dark" or "cinematic" or "night" or "shadow"
- Alt 1: Rephrase the original keywords with different synonyms
- Alt 2: Zoom out to a broader atmospheric concept
- Alt 3: Use a specific, concrete subject that metaphorically matches the text
- NEVER use: bright, colorful, happy, sunny, cartoon, kids, cute, funny
- Keep each query 4-6 words for best stock footage search results
- Preferred visual subjects: silhouettes, storms, wolves, lions, chess, suits, cityscapes, oceans, mountains, gyms, boxing, architecture, rain, fire, smoke

SEGMENTS:
{json.dumps(segment_list, indent=2)}

OUTPUT FORMAT — respond with ONLY a JSON array, no markdown:
[
  {{"index": 0, "alts": ["alt query 1", "alt query 2", "alt query 3"]}},
  ...
]"""

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # --- Strip markdown code fences if present ---
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

        enrichments = json.loads(raw_text)

        # --- Apply enrichments back to original segments ---
        enrichment_map = {e["index"]: e.get("alts", []) for e in enrichments}
        applied = 0
        for idx, alts in enrichment_map.items():
            if 0 <= idx < len(segments) and alts:
                segments[idx]["visual_keywords_alt"] = [str(a) for a in alts[:3]]
                applied += 1

        print(f"[SCRIPT] Enriched {applied}/{len(needs_enrichment)} segments with alt keywords")

    except Exception as e:
        print(f"[SCRIPT] Visual keyword enrichment failed: {e}")
        print("[SCRIPT] Continuing with primary keywords only")

    return segments


# ============================================================
# CHAPTER EXTRACTION
# Extracts YouTube chapter markers from long-form scripts.
# Called by video assembler and metadata generator.
# ============================================================

def extract_chapters(script_segments, caption_events):
    """
    # Extracts YouTube chapter markers from long-form script segments.
    # Returns list of {time: "M:SS", title: str, seconds: float}
    # Used to generate the YouTube video description with timestamps.
    #
    # Args:
    #   script_segments (list[dict]): the script segments
    #   caption_events  (list[dict]): word-level timing from ElevenLabs
    #
    # Returns: list of chapter dicts with time, title, seconds
    """
    chapters = []
    word_index = 0

    for seg in script_segments:
        if seg.get("chapter"):
            # --- Find the timestamp for this segment in the caption events ---
            if word_index < len(caption_events):
                start_time = caption_events[word_index]["start"] if caption_events else 0
            else:
                start_time = 0

            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            chapters.append({
                "time": f"{minutes}:{seconds:02d}",
                "title": seg["chapter"],
                "seconds": start_time,
            })

        word_index += 1

    # --- Ensure first chapter starts at 0:00 ---
    # YouTube requires the first chapter to start at the beginning
    if chapters and chapters[0]["seconds"] > 0:
        chapters.insert(0, {"time": "0:00", "title": "Introduction", "seconds": 0})

    return chapters


# ============================================================
# UTILITY FUNCTIONS
# Small helpers used by other modules
# ============================================================

def get_script_text(script):
    """
    # Returns the full script as a single string.
    # Used by the voiceover module to send to ElevenLabs.
    #
    # Args:
    #   script (list[dict]): list of segment dicts
    #
    # Returns: full script text as one string (space-separated)
    """
    return " ".join([segment["text"] for segment in script])


def get_all_visual_keywords(script):
    """
    # Extracts all visual keywords from a script.
    # Used to batch-download footage before video assembly.
    #
    # Args:
    #   script (list[dict]): list of segment dicts
    #
    # Returns: list of visual keyword strings, one per segment
    """
    return [segment["visual_keywords"] for segment in script]


# ============================================================
# QUICK TEST — run this file directly to check it works
# python script_generator.py
# ============================================================
if __name__ == "__main__":
    # --- Test history loading ---
    print("\n--- Testing history loading ---")
    history = load_generated_history()
    print(f"History entries: {len(history)}")

    # --- Test hook validation ---
    print("\n--- Testing hook validation ---")
    print(f"'Life is about choices' → strong: {_is_strong_hook('Life is about choices')}")
    print(f"'You were never meant to be average' → strong: {_is_strong_hook('You were never meant to be average')}")

    # --- Test motion style heuristic ---
    print("\n--- Testing motion style heuristic ---")
    print(f"mountain landscape → {_infer_motion_style('mountain peak landscape clouds')}")
    print(f"man running boxing → {_infer_motion_style('man running boxing training')}")
    print(f"silhouette portrait → {_infer_motion_style('chess board silhouette portrait')}")

    # --- Test emergency script ---
    print("\n--- Testing emergency fallback ---")
    emergency = _build_emergency_script("Power of Silence", num_segments=5)
    print(f"Emergency segments: {len(emergency)}")
    print(f"First segment: {emergency[0]['text']}")
    for seg in emergency:
        assert "motion_style" in seg
        assert "transition" in seg
    print("All emergency segments have motion_style and transition ✓")
