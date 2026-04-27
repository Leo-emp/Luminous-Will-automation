import random
import config

# ============================================================
# SCRIPT GENERATOR
# Generates motivational/psychological scripts with punchy hooks
# ============================================================


# --- Hook templates that stop the scroll ---
# These are proven viral hook formulas for dark motivation content
HOOK_TEMPLATES = [
    "If you {action}, you need to hear this.",
    "Stop {bad_habit}. Here's why.",
    "The reason you feel {emotion} isn't what you think.",
    "Most people will ignore this. But the smart ones won't.",
    "This one habit is quietly destroying your life.",
    "They don't want you to know this.",
    "If nobody told you this today, listen carefully.",
    "The harsh truth about {topic} nobody talks about.",
    "You're not {problem}. You're just surrounded by the wrong people.",
    "A psychologist once said something that changed everything.",
    "Read this before it's too late.",
    "The difference between you and them? This.",
    "This is why you always feel {emotion}.",
    "Pay attention. This will change how you see everything.",
    "Here's what {bad_people} don't want you to figure out.",
    "If you're always the one trying, read this.",
    "One sentence that will change your entire mindset.",
    "You were never {problem}. You were just {truth}.",
    "Some people need to hear this right now.",
    "The psychology behind why {topic} will shock you.",
]


def generate_script(topic=None, custom_hook=None):
    """
    # Generates a full video script with:
    # 1. A punchy hook (first 2 seconds)
    # 2. Main content broken into caption-friendly segments
    # 3. A strong closing line
    #
    # Returns a list of script segments, each with:
    #   - text: the spoken words
    #   - visual_keywords: what footage to search for
    #   - emphasis_word: the word to highlight in captions
    """

    # --- Pick a random topic if none given ---
    if topic is None:
        topic = random.choice(config.TRENDING_TOPICS)

    print(f"[SCRIPT] Generating script for: {topic}")

    # --- This is a TEMPLATE script generator ---
    # For production, replace this with an LLM API call
    # The structure below shows the exact format needed
    script = get_template_script(topic)

    return script, topic


def get_template_script(topic):
    """
    # Returns a pre-written template script
    # Replace this function with LLM-generated scripts for variety
    # Each segment = one caption group shown on screen
    """

    # --- Collection of full scripts organized by topic ---
    scripts = {

        # =====================================================
        # SCRIPT: The psychology of silence and power
        # =====================================================
        "The psychology of silence and power": [
            {
                "text": "The most powerful people in the room never raise their voice.",
                "visual_keywords": "businessman dark office silhouette",
                "emphasis_word": "powerful",
            },
            {
                "text": "And there's a psychological reason for that.",
                "visual_keywords": "dark chess pieces close up",
                "emphasis_word": "psychological",
            },
            {
                "text": "When you stay silent, people can't read you.",
                "visual_keywords": "man thinking alone dark room",
                "emphasis_word": "silent",
            },
            {
                "text": "They can't predict your next move.",
                "visual_keywords": "chess strategy dark cinematic",
                "emphasis_word": "predict",
            },
            {
                "text": "And that makes you dangerous.",
                "visual_keywords": "lion walking slowly dark",
                "emphasis_word": "dangerous",
            },
            {
                "text": "Psychologists call this the power of ambiguity.",
                "visual_keywords": "dark shadows mysterious man",
                "emphasis_word": "ambiguity",
            },
            {
                "text": "When people don't know what you're thinking,",
                "visual_keywords": "man in suit looking away dark",
                "emphasis_word": "thinking",
            },
            {
                "text": "they fill the gap with their own fears.",
                "visual_keywords": "dark hallway shadows cinematic",
                "emphasis_word": "fears",
            },
            {
                "text": "Your silence becomes their anxiety.",
                "visual_keywords": "rain window dark moody",
                "emphasis_word": "anxiety",
            },
            {
                "text": "The loud ones? They expose everything.",
                "visual_keywords": "crowd arguing people shouting",
                "emphasis_word": "expose",
            },
            {
                "text": "Their emotions. Their insecurities. Their weaknesses.",
                "visual_keywords": "broken glass dark aesthetic",
                "emphasis_word": "weaknesses",
            },
            {
                "text": "But the silent ones? They observe.",
                "visual_keywords": "eagle eye close up dark",
                "emphasis_word": "observe",
            },
            {
                "text": "They calculate. They wait.",
                "visual_keywords": "man watching city night rooftop",
                "emphasis_word": "wait",
            },
            {
                "text": "And when they finally speak, the whole room listens.",
                "visual_keywords": "confident man speaking dark boardroom",
                "emphasis_word": "listens",
            },
            {
                "text": "Remember this. Your silence is not weakness.",
                "visual_keywords": "lion resting powerful dark",
                "emphasis_word": "weakness",
            },
            {
                "text": "It's your greatest weapon.",
                "visual_keywords": "sword dark cinematic close up",
                "emphasis_word": "weapon",
            },
            {
                "text": "Master it.",
                "visual_keywords": "man walking away dark cinematic",
                "emphasis_word": "Master",
            },
        ],

        # =====================================================
        # SCRIPT: Why high-value people walk alone
        # =====================================================
        "Why high-value people walk alone": [
            {
                "text": "If you're always alone, this message is for you.",
                "visual_keywords": "man walking alone dark street night",
                "emphasis_word": "alone",
            },
            {
                "text": "High-value people don't have big friend groups.",
                "visual_keywords": "solitary man dark aesthetic",
                "emphasis_word": "High-value",
            },
            {
                "text": "Not because they can't socialize.",
                "visual_keywords": "crowd busy people dark city",
                "emphasis_word": "socialize",
            },
            {
                "text": "But because they refuse to lower their standards.",
                "visual_keywords": "man in suit looking down dark",
                "emphasis_word": "standards",
            },
            {
                "text": "They've learned that most people drain your energy.",
                "visual_keywords": "tired person dark room moody",
                "emphasis_word": "drain",
            },
            {
                "text": "Most people gossip instead of building.",
                "visual_keywords": "people whispering dark scene",
                "emphasis_word": "gossip",
            },
            {
                "text": "They complain instead of creating.",
                "visual_keywords": "dark workspace laptop night",
                "emphasis_word": "creating",
            },
            {
                "text": "And they criticize instead of growing.",
                "visual_keywords": "plant growing dark time lapse",
                "emphasis_word": "growing",
            },
            {
                "text": "A lion doesn't lose sleep over the opinion of sheep.",
                "visual_keywords": "lion portrait dark dramatic",
                "emphasis_word": "lion",
            },
            {
                "text": "Your solitude is not loneliness.",
                "visual_keywords": "man on mountain top dark sky",
                "emphasis_word": "solitude",
            },
            {
                "text": "It's a sign that you've outgrown your environment.",
                "visual_keywords": "dark city skyline night cinematic",
                "emphasis_word": "outgrown",
            },
            {
                "text": "The right people will find you.",
                "visual_keywords": "sunrise dark clouds dramatic",
                "emphasis_word": "find",
            },
            {
                "text": "But only when you stop settling for the wrong ones.",
                "visual_keywords": "man walking away dramatic dark",
                "emphasis_word": "settling",
            },
            {
                "text": "Walk alone if you have to.",
                "visual_keywords": "lone wolf dark forest",
                "emphasis_word": "alone",
            },
            {
                "text": "Your future self will thank you.",
                "visual_keywords": "mirror reflection man dark",
                "emphasis_word": "future",
            },
        ],

        # =====================================================
        # SCRIPT: The art of not reacting
        # =====================================================
        "The art of not reacting": [
            {
                "text": "Stop reacting to everything. Here's why.",
                "visual_keywords": "calm water dark reflection",
                "emphasis_word": "reacting",
            },
            {
                "text": "Every time you react emotionally, you give away your power.",
                "visual_keywords": "chess king falling dark",
                "emphasis_word": "power",
            },
            {
                "text": "The person who made you angry now controls you.",
                "visual_keywords": "puppet strings dark artistic",
                "emphasis_word": "controls",
            },
            {
                "text": "That's exactly what they wanted.",
                "visual_keywords": "dark silhouette manipulation",
                "emphasis_word": "wanted",
            },
            {
                "text": "But when you don't react, something shifts.",
                "visual_keywords": "still man dark room confident",
                "emphasis_word": "shifts",
            },
            {
                "text": "You become unpredictable.",
                "visual_keywords": "dark fog mysterious cinematic",
                "emphasis_word": "unpredictable",
            },
            {
                "text": "And unpredictable people cannot be manipulated.",
                "visual_keywords": "lion staring dark intense",
                "emphasis_word": "manipulated",
            },
            {
                "text": "Train yourself to pause before you speak.",
                "visual_keywords": "man meditating dark room",
                "emphasis_word": "pause",
            },
            {
                "text": "Breathe before you respond.",
                "visual_keywords": "dark ocean waves slow motion",
                "emphasis_word": "Breathe",
            },
            {
                "text": "Let them wonder what you're thinking.",
                "visual_keywords": "dark mysterious eyes close up",
                "emphasis_word": "wonder",
            },
            {
                "text": "The most powerful response is no response at all.",
                "visual_keywords": "empty dark room silence",
                "emphasis_word": "powerful",
            },
            {
                "text": "Master your emotions before they master you.",
                "visual_keywords": "man walking alone night city dark",
                "emphasis_word": "Master",
            },
        ],
    }

    # --- Return matching script or default ---
    if topic in scripts:
        return scripts[topic]

    # --- Fallback: return the silence and power script ---
    return scripts["The psychology of silence and power"]


def get_all_visual_keywords(script):
    """
    # Extracts all visual keywords from a script
    # Used to batch-download footage before assembly
    """
    return [segment["visual_keywords"] for segment in script]


def get_script_text(script):
    """
    # Returns the full script as a single string
    # Used for generating the voiceover
    """
    return " ".join([segment["text"] for segment in script])


# --- Quick test ---
if __name__ == "__main__":
    script, topic = generate_script("The psychology of silence and power")
    print(f"\nTopic: {topic}")
    print(f"Segments: {len(script)}")
    print(f"\nFull script:\n{get_script_text(script)}")
