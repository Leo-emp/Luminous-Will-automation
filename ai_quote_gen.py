import os
import json
import random
import numpy as np
import config
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ============================================================
# AI QUOTE IMAGE GENERATOR
# Fully automated pipeline — Gemini acts as creative director,
# designing unique scene prompts for every quote. No fixed templates.
#
# Flow:
#   1. Gemini analyzes the quote and designs a scene concept
#   2. AI image provider (fal.ai / Gemini / Imagen 4) renders it
#   3. Post-processing applies cinematic film look
#
# Two render modes:
#   scene  — text baked into AI-generated environment (subway, wall, billboard)
#   bg     — AI symbolic background + Pillow text overlay (chess, mountain, lion)
# ============================================================

# --- Font paths (shared with quote_reel.py) ---
FONTS_DIR = os.path.join(config.ASSETS_DIR, "fonts")
FONT_FILES = {
    "bebas": os.path.join(FONTS_DIR, "BebasNeue-Regular.ttf"),
    "oswald": os.path.join(FONTS_DIR, "Oswald-Bold.ttf"),
    "playfair": os.path.join(FONTS_DIR, "PlayfairDisplay-Bold.ttf"),
    "caveat": os.path.join(FONTS_DIR, "Caveat-Bold.ttf"),
    "anton": os.path.join(FONTS_DIR, "Anton-Regular.ttf"),
    "marker": os.path.join(FONTS_DIR, "Permanent_Marker.ttf"),
    "montserrat": os.path.join(FONTS_DIR, "Montserrat-Bold.ttf"),
}

# ============================================================
# STYLE DNA — the aesthetic rules extracted from 61 reference images
# This is the "creative brief" that Gemini uses to design every scene
# ============================================================

STYLE_DNA = """You are a professional image prompt engineer for "Luminous Will", a dark motivational quote brand.
You write highly detailed, structured prompts that produce cinematic, reference-quality images with text baked in.

═══ PHOTOGRAPHY SPECIFICATIONS ═══

CAMERA & LENS (always specify one):
- "shot on Sony A7IV, 35mm f/1.4, shallow depth of field"
- "shot on Canon R5, 85mm f/1.2, bokeh background"
- "shot on Hasselblad X2D, 45mm f/3.5, medium format film look"
- "shot on Leica M11, 50mm Summilux, street photography"
- "drone shot, DJI Mavic 3, wide angle" (for aerial/landscape)
- "iPhone 15 Pro, night mode, 24mm" (for raw/authentic feel)

LIGHTING (always specify setup):
- "single hard key light from 45 degrees camera-left, no fill, deep shadows"
- "overhead practical fluorescent, harsh pools of light, dark falloff"
- "backlit rim light only, subject in silhouette, lens flare"
- "golden hour side light, long shadows, warm-to-cool gradient"
- "stadium/arena overhead spots, cone of light on subject, everything else dark"
- "candlelight / single bulb, warm close glow, rapid falloff to black"

EXPOSURE & GRADE:
- Underexposed by 1-2 stops. Average scene brightness 15-25%.
- Crushed blacks with lifted shadow floor (never pure 0,0,0 — aim for RGB 8-15 in darkest areas)
- Highlight rolloff: soft, filmic, no clipping. Brightest whites at 240-250, not 255.
- Color: desaturated 60-90%. When color exists, only warm amber/gold accents.
- Grain: visible organic film grain, ISO 800-3200 look.

COMPOSITION (always specify):
- "text occupies upper 40% of frame, subject fills lower 60%"
- "text centered vertically, subject as background element at 30% opacity"
- "text bottom-left aligned at 10% margin, subject upper-right"
- "text across full width of frame at 50% height, scene above and below"
- Rule of thirds or centered. Never random placement.
- 70%+ negative space (dark areas). Images should breathe.

═══ TEXT SPECIFICATIONS ═══

CRITICAL — the quote text MUST be physically part of the scene. Include the EXACT quote using "{quote}".

TEXT RENDERING RULES (always specify ALL of these in your prompt):
- Font style: "bold condensed sans-serif capitals" or "heavy block letters" or "clean geometric sans-serif"
- Size: "text is very large, each word spans 60-80% of the frame width"
- Color: "pure white text" or "off-white cream text" or "warm amber gold text"
- Weight: "ultra-bold, heavy, thick strokes with strong visual weight"
- Spacing: "tight letter-spacing, words stacked vertically one per line"
- Integration: HOW the text exists in the scene:
  * Printed/painted on a surface (wall, canvas, floor, billboard, sign)
  * Carved/etched/engraved into material (stone, metal, wood, concrete)
  * Projected/displayed (LED board, lightbox, screen, projector)
  * Written by hand (chalk, marker, spray paint, brush)

NEGATIVE TEXT INSTRUCTIONS (always include):
"No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no logos, no extra text beyond the quote."

═══ SCENE CATEGORIES ═══

Pick ONE category, ONE specific scene. Vary across batches.

1. GYM & FITNESS:
   Barbell/chalk dust, heavy bag, weight plates, pull-up bar silhouette,
   empty gym at 5am, rubber mat, squat rack, kettlebell, battle ropes

2. BOXING & COMBAT:
   Ring canvas, hanging gloves, hand wraps, corner stool, speed bag,
   punching bag in warehouse, octagon cage, fighter silhouette

3. URBAN & STREET:
   Subway billboard, spray paint wall, dark alley, rooftop ledge,
   parking garage, bridge underpass, fire escape, empty lot at night

4. NATURE & ELEMENTS:
   Mountain rock face, ocean wave, lightning, lone cliff tree,
   frozen lake, dark canyon, fog forest, sand dunes, storm clouds

5. LUXURY & POWER:
   Chess piece/shadow, crown on velvet, empty throne, dark office,
   leather journal, watch face, dark car interior, whiskey glass

6. CLASSICAL & ARTISTIC:
   Gallery canvas, marble statue, old library, cathedral pillar,
   newspaper marker, typewriter, piano keys, broken sculpture

7. INDUSTRIAL & GRIT:
   Welding sparks, train tunnel, construction barrier, anchor chain,
   prison wall, furnace glow, motorcycle chrome, steel girders

8. HUMAN SILHOUETTES:
   Cliff edge figure, runner on road, rain walker, hooded doorway,
   lone bench, warrior smoke, meditating figure, wall climber

═══ OUTPUT FORMAT ═══

Respond with valid JSON only:
{
    "prompt": "FULL detailed prompt (4-6 sentences minimum) with {quote} placeholder, camera/lens, lighting, composition, text specs, negative instructions",
    "grain": 8-22,
    "vignette": 0.2-0.5,
    "desaturate": 0.0-0.95,
    "grade": "warm_grit"
}

═══ EXAMPLE PROMPT (this is the quality bar) ═══

"A dark moody boxing gym interior, shot on Sony A7IV 35mm f/1.4. A worn leather heavy bag hangs from chains in the center of the frame, occupying the lower 60%. Single hard overhead spotlight creates a cone of light on the bag, everything else falls to deep shadow. The text '{quote}' is printed in very large ultra-bold condensed white sans-serif capital letters on the dark concrete wall behind the bag, each word on its own line, spanning 70% of the frame width. Text occupies the upper 40% of the composition. Underexposed, crushed blacks, heavy film grain ISO 1600, desaturated to near-monochrome with only warm amber tones from the spotlight. No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no logos, no extra text beyond the quote. Cinematic, editorial, 9:16 portrait orientation."

Every prompt you write must be AT LEAST this detailed. Vague prompts produce amateur results.

═══ COLOR GRADE PRESETS ═══

Pick the grade that best matches the scene's emotional tone. Be precise — the wrong grade ruins the mood.

CORE CINEMATIC:
- "warm_grit"      — gym, training, chalk dust. Warm amber highlights, cool shadows, gritty texture.
- "cold_noir"      — urban night, rain, subway, alleys. Strong blue shadows, deep blacks, noir.
- "neutral_bw"     — silhouettes, chiaroscuro, B&W. Zero tinting, pure light vs shadow.
- "warm_luxury"    — crown, throne, velvet, gold. Deep true blacks, rich golden highlights, elegant.
- "cold_epic"      — mountains, ocean, storm. Blue-teal atmosphere, lifted haze, vast scale.
- "raw_industrial" — welding, steel, sparks, tunnel. Hot amber highlights, punchy contrast, heavy clarity.
- "film_classic"   — marble statue, canvas, library. Aged film warmth, cream tones, painterly.
- "amber_glow"     — backlit 3D letters, lightbox, candles. Soft warm golden glow, low contrast.

HOLLYWOOD FILM LOOKS:
- "teal_orange"    — blockbuster action (Transformers, Mad Max). Teal shadows, orange highlights, high impact.
- "bleach_bypass"  — war/grit films (300, Sin City). Metallic, extreme contrast, desaturated, gritty texture.
- "moonlight_blue" — lone wolf, night scenes. Cold blue throughout, silvery highlights, contemplative.
- "golden_hour"    — sunrise/sunset motivation. Warm amber throughout, everything glows, inspirational.

DARK MOTIVATION AESTHETIC:
- "neon_glow"      — cyberpunk, neon signs, LED. Magenta+teal against deep black, futuristic.
- "blood_red"      — villain mindset, sigma, aggressive. Red-shifted, deep blacks, intimidating.
- "dark_sepia"     — stoic philosophy, ancient wisdom. Warm brown vintage, aged parchment feel.
- "matte_faded"    — nostalgic, dreamy, vintage IG. Lifted everything, low contrast, no true blacks.

SPECIALIZED MOOD:
- "steel_chrome"   — military, discipline, wolf. Cold metallic silver-blue, sharp and clean.
- "emerald_shadow" — Matrix-inspired, calculated, mysterious. Green in shadows and mids.
- "smoke_ash"      — battlefield, destruction, aftermath. Heavily desaturated, warm ash undertone.
- "copper_patina"  — aged warrior, weathered, resilient. Copper highlights, dark green shadows.

═══ HARD RULES ═══

- NEVER: bright colors, pastels, saturated, cheerful, stock photo feel, cartoon, anime, illustration
- NEVER: cluttered compositions, multiple subjects competing, busy backgrounds
- NEVER: small text, thin fonts, decorative/script fonts, text that's hard to read
- ALWAYS: photorealistic, cinematic, dark, moody, professional
- ALWAYS: specify camera, lens, lighting, composition, text placement
- ALWAYS: include negative text instructions at the end of the prompt
- ALWAYS: make every scene UNIQUE within a batch"""


# ============================================================
# GRADE PRESETS — adaptive color grading matched to scene mood
# Each preset controls: black floor, contrast curve, shadow/highlight
# tinting, and local clarity. Gemini picks one per scene, static
# templates each carry their own.
# ============================================================

GRADE_PRESETS = {
    # ══════════════════════════════════════════════
    # CORE CINEMATIC GRADES (original 8)
    # ══════════════════════════════════════════════

    # Gym, training, chalk dust — warm amber cuts through dark interiors
    "warm_grit": {
        "black_floor": 12, "s_curve": 0.30,
        "shadow_tint": (-15, 3, 8), "shadow_strength": 0.08,
        "highlight_tint": (30, 15, -10), "highlight_strength": 0.12,
        "clarity": 0.35,
    },
    # Urban night, rain, subway — strong cool blue shadows, noir atmosphere
    "cold_noir": {
        "black_floor": 8, "s_curve": 0.28,
        "shadow_tint": (-25, 5, 25), "shadow_strength": 0.15,
        "highlight_tint": (10, 5, -5), "highlight_strength": 0.06,
        "clarity": 0.30,
    },
    # Silhouettes, chiaroscuro — zero tinting, pure light vs shadow
    "neutral_bw": {
        "black_floor": 10, "s_curve": 0.25,
        "shadow_tint": (0, 0, 0), "shadow_strength": 0.0,
        "highlight_tint": (0, 0, 0), "highlight_strength": 0.0,
        "clarity": 0.25,
    },
    # Crown, throne, velvet — deep true blacks, rich golden highlights
    "warm_luxury": {
        "black_floor": 6, "s_curve": 0.22,
        "shadow_tint": (-10, -5, 10), "shadow_strength": 0.06,
        "highlight_tint": (35, 18, -12), "highlight_strength": 0.14,
        "clarity": 0.20,
    },
    # Mountains, ocean, storm — blue-teal atmosphere, lifted haze
    "cold_epic": {
        "black_floor": 14, "s_curve": 0.20,
        "shadow_tint": (-20, 8, 22), "shadow_strength": 0.14,
        "highlight_tint": (5, 3, -3), "highlight_strength": 0.04,
        "clarity": 0.28,
    },
    # Welding, steel, sparks — hot amber highlights, punchy industrial texture
    "raw_industrial": {
        "black_floor": 10, "s_curve": 0.32,
        "shadow_tint": (-8, 2, 5), "shadow_strength": 0.05,
        "highlight_tint": (40, 20, -15), "highlight_strength": 0.15,
        "clarity": 0.40,
    },
    # Marble statue, canvas, library — aged film warmth, painterly
    "film_classic": {
        "black_floor": 16, "s_curve": 0.18,
        "shadow_tint": (5, -3, 8), "shadow_strength": 0.08,
        "highlight_tint": (20, 15, 5), "highlight_strength": 0.10,
        "clarity": 0.22,
    },
    # Backlit 3D letters, lightbox, candlelight — soft warm golden glow
    "amber_glow": {
        "black_floor": 10, "s_curve": 0.24,
        "shadow_tint": (-5, -3, 12), "shadow_strength": 0.06,
        "highlight_tint": (45, 25, -20), "highlight_strength": 0.16,
        "clarity": 0.18,
    },

    # ══════════════════════════════════════════════
    # HOLLYWOOD FILM GRADES
    # ══════════════════════════════════════════════

    # Teal & orange — the blockbuster look (Transformers, Mad Max)
    # Skin pops against cool backgrounds, high visual impact
    "teal_orange": {
        "black_floor": 8, "s_curve": 0.28,
        "shadow_tint": (-20, 12, 25), "shadow_strength": 0.14,
        "highlight_tint": (35, 10, -25), "highlight_strength": 0.14,
        "clarity": 0.30,
    },
    # Bleach bypass — 300, Sin City, Saving Private Ryan
    # Metallic desaturated look, extreme contrast, gritty texture
    "bleach_bypass": {
        "black_floor": 6, "s_curve": 0.38,
        "shadow_tint": (-5, 0, 5), "shadow_strength": 0.03,
        "highlight_tint": (8, 5, -3), "highlight_strength": 0.04,
        "clarity": 0.45,
    },
    # Moonlight — lone wolf, night watch, cold blue silvery
    # Everything pushed cool, silvery highlights, contemplative
    "moonlight_blue": {
        "black_floor": 10, "s_curve": 0.22,
        "shadow_tint": (-20, 5, 30), "shadow_strength": 0.16,
        "highlight_tint": (-5, 5, 15), "highlight_strength": 0.08,
        "clarity": 0.20,
    },
    # Golden hour — sunrise motivation, warm amber throughout
    # Shadows warm too, everything glows, inspirational
    "golden_hour": {
        "black_floor": 14, "s_curve": 0.20,
        "shadow_tint": (10, 5, -10), "shadow_strength": 0.08,
        "highlight_tint": (40, 22, -15), "highlight_strength": 0.14,
        "clarity": 0.15,
    },

    # ══════════════════════════════════════════════
    # SOCIAL MEDIA / DARK MOTIVATION AESTHETIC
    # ══════════════════════════════════════════════

    # Neon glow — cyberpunk, neon signs, LED, magenta+teal against deep black
    # Popular on IG/TikTok for futuristic motivational content
    "neon_glow": {
        "black_floor": 4, "s_curve": 0.30,
        "shadow_tint": (-15, -5, 20), "shadow_strength": 0.12,
        "highlight_tint": (30, -10, 20), "highlight_strength": 0.12,
        "clarity": 0.35,
    },
    # Blood red — villain mindset, sigma grindset, aggressive
    # Red-shifted throughout, deep blacks, intimidating
    "blood_red": {
        "black_floor": 6, "s_curve": 0.35,
        "shadow_tint": (15, -8, -5), "shadow_strength": 0.12,
        "highlight_tint": (25, -5, -10), "highlight_strength": 0.10,
        "clarity": 0.38,
    },
    # Dark sepia — stoic philosophy, Marcus Aurelius, ancient wisdom
    # Warm brown vintage tone, aged parchment feel
    "dark_sepia": {
        "black_floor": 18, "s_curve": 0.16,
        "shadow_tint": (12, 5, -8), "shadow_strength": 0.10,
        "highlight_tint": (25, 15, 0), "highlight_strength": 0.12,
        "clarity": 0.18,
    },
    # Matte faded — lifted everything, low contrast, IG vintage
    # Nostalgic, dreamy, no true blacks, soft everywhere
    "matte_faded": {
        "black_floor": 22, "s_curve": 0.12,
        "shadow_tint": (5, 3, 5), "shadow_strength": 0.05,
        "highlight_tint": (10, 8, 0), "highlight_strength": 0.06,
        "clarity": 0.12,
    },

    # ══════════════════════════════════════════════
    # SPECIALIZED MOOD GRADES
    # ══════════════════════════════════════════════

    # Steel chrome — military discipline, wolf aesthetic, cold metallic
    # Silver-blue throughout, sharp and clean, no warmth
    "steel_chrome": {
        "black_floor": 6, "s_curve": 0.30,
        "shadow_tint": (-10, 0, 12), "shadow_strength": 0.08,
        "highlight_tint": (-5, 3, 10), "highlight_strength": 0.06,
        "clarity": 0.35,
    },
    # Emerald shadow — Matrix-inspired, calculated, mysterious
    # Green pushed into shadows and mids, desaturated other colors
    "emerald_shadow": {
        "black_floor": 8, "s_curve": 0.26,
        "shadow_tint": (-10, 12, -5), "shadow_strength": 0.12,
        "highlight_tint": (-5, 10, -8), "highlight_strength": 0.08,
        "clarity": 0.28,
    },
    # Smoke ash — battlefield, destruction, post-apocalyptic
    # Heavily desaturated with warm ash undertone, muted everything
    "smoke_ash": {
        "black_floor": 14, "s_curve": 0.22,
        "shadow_tint": (5, 2, -3), "shadow_strength": 0.06,
        "highlight_tint": (12, 8, -5), "highlight_strength": 0.08,
        "clarity": 0.30,
    },
    # Copper patina — aged, weathered, resilient, bronze warrior
    # Warm copper highlights, dark green shadows, old-world power
    "copper_patina": {
        "black_floor": 10, "s_curve": 0.26,
        "shadow_tint": (-8, 8, -3), "shadow_strength": 0.10,
        "highlight_tint": (35, 15, -18), "highlight_strength": 0.13,
        "clarity": 0.32,
    },
}

DEFAULT_GRADE = "cold_noir"


def _parse_json_safe(raw):
    """
    # Robust JSON parsing that handles common LLM output issues:
    # markdown fences, newlines in strings, trailing commas
    """
    # --- Strip markdown code fences ---
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    # --- First try: direct parse ---
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # --- Second try: fix newlines inside JSON strings ---
    import re
    # Replace literal newlines inside quoted strings with spaces
    fixed = re.sub(r'(?<=": ")(.*?)(?=")', lambda m: m.group(0).replace("\n", " "), text, flags=re.DOTALL)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # --- Third try: extract JSON object from surrounding text ---
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("Could not parse JSON from LLM response", text, 0)


def generate_dynamic_prompt(quote_text, previous_concepts=None):
    """
    # Calls Gemini to design a unique scene for this specific quote.
    # Returns a dict with render_mode, prompt, post-processing params, and font settings.
    # Falls back to a random static template if Gemini fails.
    """
    if not config.GEMINI_API_KEY:
        return _random_static_prompt(quote_text)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=config.GEMINI_API_KEY)

        # --- Build the request as a single string prompt ---
        avoid_text = ""
        if previous_concepts:
            avoid_text = f"\n\nAVOID these concepts (already used in this batch): {', '.join(previous_concepts[-6:])}"

        full_prompt = f'{STYLE_DNA}\n\nDesign a scene for this quote: "{quote_text}"{avoid_text}'

        # --- Retry up to 3 times for transient 503 errors ---
        import time as _time
        raw = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=1.0,
                        max_output_tokens=2048,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                        response_mime_type="application/json",
                    ),
                )
                raw = response.text.strip()
                break
            except Exception as retry_err:
                err_msg = str(retry_err)
                # --- Retry on transient 503 (overloaded) ---
                if "503" in err_msg and attempt < 2:
                    print(f"[AI_QUOTE] Gemini 503, retrying in {2 ** attempt}s...")
                    _time.sleep(2 ** attempt)
                    continue
                # --- Rate limited: extract retry delay if available ---
                if "429" in err_msg:
                    import re
                    delay_match = re.search(r'retry in (\d+)', err_msg)
                    if delay_match and attempt < 2:
                        wait = int(delay_match.group(1)) + 1
                        print(f"[AI_QUOTE] Rate limited, waiting {wait}s...")
                        _time.sleep(wait)
                        continue
                raise

        if not raw:
            print("[AI_QUOTE] Gemini returned empty response")
            return _random_static_prompt(quote_text)

        result = _parse_json_safe(raw)

        # --- Validate required fields ---
        if "prompt" not in result:
            print("[AI_QUOTE] Gemini response missing 'prompt' field, using static")
            return _random_static_prompt(quote_text)

        # --- Insert quote text into the prompt ---
        if "{quote}" in result["prompt"]:
            result["prompt"] = result["prompt"].replace("{quote}", quote_text)

        # --- Apply defaults for missing optional fields ---
        result.setdefault("grain", random.randint(10, 18))
        result.setdefault("vignette", round(random.uniform(0.25, 0.45), 2))
        result.setdefault("desaturate", round(random.uniform(0.3, 0.8), 2))
        # --- Validate grade preset, fall back to default if Gemini picks something invalid ---
        if result.get("grade") not in GRADE_PRESETS:
            result["grade"] = DEFAULT_GRADE

        # --- Extract a short concept tag for variety tracking ---
        concept = result.get("prompt", "")[:60]
        result["_concept"] = concept

        print(f"[AI_QUOTE] Gemini designed: [{result['grade']}] {concept}...")
        return result

    except Exception as e:
        print(f"[AI_QUOTE] Gemini creative director failed: {e}")
        return _random_static_prompt(quote_text)


def _random_static_prompt(quote_text):
    """
    # Fallback: pick a random scene from the static template pool
    # Always scene mode — text baked in by AI
    """
    # --- Combine all templates into one pool ---
    all_templates = {}
    for name, style in AI_SCENE_PROMPTS.items():
        all_templates[name] = style
    # --- Convert bg templates to scene mode by adding text instructions ---
    for name, style in AI_BG_PROMPTS.items():
        all_templates[f"bg_{name}"] = {
            "template": (
                style["template"] +
                f' The text "{{quote}}" appears in large bold white capital letters '
                f'integrated into the composition, partially overlapping the subject.'
            ),
            "grain": style.get("grain", 12),
            "vignette": style.get("vignette", 0.35),
            "desaturate": style.get("desaturate", 0.5),
        }

    style_name = random.choice(list(all_templates.keys()))
    style = all_templates[style_name]
    return {
        "prompt": style["template"].format(quote=quote_text),
        "grain": style.get("grain", 12),
        "vignette": style.get("vignette", 0.35),
        "desaturate": style.get("desaturate", 0.5),
        "grade": style.get("grade", DEFAULT_GRADE),
        "_concept": f"static_{style_name}",
    }


# ============================================================
# STATIC SCENE PROMPT TEMPLATES (fallback pool)
# Used when Gemini is unavailable for dynamic prompt generation
# ============================================================

AI_SCENE_PROMPTS = {
    # ── GYM & FITNESS ──
    "gym_barbell": {
        "template": (
            'Dark empty crossfit gym at 5am, shot on Sony A7IV 35mm f/1.4. A loaded barbell rests on the rubber floor, chalk dust '
            'floating in a cone of harsh overhead spotlight. The text "{quote}" is stenciled in very large ultra-bold condensed '
            'white sans-serif capital letters on the dark rubber floor beneath the barbell, each word on its own line, spanning '
            '70% of frame width. Text occupies the lower 40% of the composition, barbell and chalk dust fill the upper portion. '
            'Underexposed 1.5 stops, crushed blacks, heavy film grain ISO 1600, desaturated to near-monochrome. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 14, "vignette": 0.35, "desaturate": 0.7, "grade": "warm_grit",
    },
    "gym_heavybag": {
        "template": (
            'Dark boxing gym interior, shot on Canon R5 85mm f/1.2. A worn leather heavy bag hangs from chains in the center, '
            'occupying the lower 60% of the frame. Single hard overhead spotlight creates a cone of warm light on the bag, '
            'everything else deep shadow. The text "{quote}" is printed in very large ultra-bold condensed white sans-serif '
            'capital letters on the dark concrete wall behind the bag, each word stacked vertically, spanning 70% of frame width. '
            'Text occupies the upper 40%. Dust particles visible in the light beam. Underexposed, heavy film grain ISO 1600, '
            'desaturated to near-monochrome with warm amber from spotlight only. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 16, "vignette": 0.35, "desaturate": 0.75, "grade": "warm_grit",
    },
    "gym_plates": {
        "template": (
            'Close-up of stacked iron weight plates in a dark gym, shot on Sony A7IV 50mm f/1.4 shallow depth of field. '
            'The largest plate fills the lower half of the frame with visible chalk dust on the metal surface. The text "{quote}" '
            'is engraved into the iron plate in very large bold industrial condensed capital letters, each word on its own line. '
            'Single hard directional light from above-left at 45 degrees creating deep shadows between plates. '
            'Underexposed 2 stops, crushed blacks, raw iron texture, film grain ISO 1200, desaturated 80%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 10, "vignette": 0.3, "desaturate": 0.75, "grade": "warm_grit",
    },
    "gym_mirror": {
        "template": (
            'Dark gym with large wall mirror, shot on Leica M11 50mm Summilux. The text "{quote}" is written in very large '
            'ultra-bold white capital letters on the foggy mirror surface as if traced by a finger, each word on its own line, '
            'spanning 65% of frame width. Dim weight rack reflections visible behind the text at 20% opacity. '
            'Text centered in the frame. Single warm practical bulb above the mirror creating soft amber glow with rapid falloff. '
            'Underexposed, early morning mood, film grain ISO 2000, desaturated 70%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 12, "vignette": 0.4, "desaturate": 0.65, "grade": "warm_grit",
    },

    "gym_stencil": {
        "template": (
            'Looking straight down at a dark concrete gym floor, shot on Canon R5 24mm f/1.4 from directly overhead. '
            'The text "{quote}" is stenciled in very large ultra-bold white lowercase letters on the dark floor, framed by '
            'large square brackets [ ] on both sides, each word on its own line, centered, spanning 65% of frame width. '
            'Gym equipment straps and chalk marks visible at the edges at 15% opacity. Single harsh overhead spotlight creates '
            'a tight pool of light on the text, rapid falloff to black at the edges. Underexposed 2 stops, crushed blacks, '
            'film grain ISO 1600, desaturated 65%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 12, "vignette": 0.3, "desaturate": 0.6, "grade": "warm_grit",
    },

    # ── BOXING & COMBAT ──
    "boxing_ring": {
        "template": (
            'Inside a dark empty boxing ring looking down at the white canvas, shot on Canon R5 24mm f/1.4 wide angle. '
            'The text "{quote}" is printed in very large ultra-bold condensed dark sans-serif capital letters on the white ring '
            'canvas, each word on its own line, centered, spanning 60% of canvas width. Red ring ropes frame the edges at top. '
            'Dramatic overhead arena spotlight creates a pool of warm light on the canvas, everything beyond the ropes is pitch '
            'black. Empty arena seats barely visible in shadow. Film grain ISO 1000, desaturated 60%, underexposed 1 stop. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 14, "vignette": 0.35, "desaturate": 0.55, "grade": "raw_industrial",
    },
    "boxing_gloves": {
        "template": (
            'A pair of worn black boxing gloves hanging from a rusty nail on a dark concrete wall, shot on Hasselblad X2D '
            '45mm f/3.5 medium format. Gloves occupy the lower-right 30% of the frame with shallow depth of field. '
            'The text "{quote}" is painted on the concrete wall in very large ultra-bold white condensed sans-serif capital letters, '
            'each word stacked vertically, spanning 70% of frame width, occupying the upper-left 60% of the composition. '
            'Single hard key light from 45 degrees camera-left, no fill, scuffed leather texture, peeling paint. '
            'Film grain ISO 1600, desaturated 75%, crushed blacks with lifted shadows. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 16, "vignette": 0.3, "desaturate": 0.7, "grade": "warm_grit",
    },
    "boxing_wraps": {
        "template": (
            'Close-up of a fighter wrapping their hands with black hand wraps before a fight, shot on Sony A7IV 85mm f/1.2. '
            'Hands occupy the lower 40% of the frame, dramatic chiaroscuro lighting — only the knuckles and wrap are lit from '
            'above-right, everything else falls to black. The text "{quote}" appears in very large ultra-bold white condensed '
            'sans-serif capital letters in the dark upper 50% of the frame, each word on its own line, left-aligned at 10% margin. '
            'B&W, heavy film grain ISO 2000, crushed blacks, intense pre-fight atmosphere. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 14, "vignette": 0.4, "desaturate": 0.9, "grade": "neutral_bw",
    },

    # ── URBAN & STREET ──
    "subway_poster": {
        "template": (
            'Dark moody subway station interior, shot on Leica M11 35mm Summicron, black and white street photography. '
            'On the white tiled wall hangs a large framed advertisement poster with a solid dark background. The poster displays '
            'the text "{quote}" in very large ultra-bold white condensed sans-serif capital letters, each word on its own line, '
            'centered, spanning 80% of the poster width. A commuter walks past as a motion blur ghost at 1/8 second shutter. '
            'Harsh fluorescent overhead tubes create pools of light and dark shadow. Heavy film grain ISO 3200, B&W. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 18, "vignette": 0.35, "desaturate": 0.95, "grade": "cold_noir",
    },
    "dark_alley": {
        "template": (
            'Dark narrow urban alley at night, shot on Sony A7IV 24mm f/1.4. Single flickering streetlight at the far end creates '
            'a warm pool of light with rapid falloff. Wet pavement reflecting the light in the lower 30% of frame. '
            'The text "{quote}" is spray-painted in very large ultra-bold white condensed capital letters on the dark brick wall, '
            'each word on its own line, left-aligned at 10% margin, spanning 75% of frame width, occupying the center 40% of frame. '
            'Gritty urban noir atmosphere, underexposed 2 stops, film grain ISO 2500, desaturated 85%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 20, "vignette": 0.4, "desaturate": 0.8, "grade": "cold_noir",
    },
    "billboard_city": {
        "template": (
            'Large digital billboard on building in city street, shot from below looking up on Canon R5 16mm f/2.8 wide angle. '
            'The billboard has a dark charcoal background displaying the text "{quote}" in very large ultra-bold white condensed '
            'sans-serif capital letters, one word per line, centered. Billboard occupies the upper 50% of the frame. '
            'City building silhouettes on both sides create a canyon effect. Shot during blue hour, desaturated cool tones. '
            'Crowd of silhouetted people visible at the bottom edge looking up. Film grain ISO 800, underexposed 1 stop. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 8, "vignette": 0.25, "desaturate": 0.4, "grade": "cold_noir",
    },
    "rooftop_city": {
        "template": (
            'Dark rooftop edge overlooking city skyline at night, shot on Sony A7IV 35mm f/1.4 with background bokeh. '
            'Concrete ledge wall runs horizontally across the lower third of the frame. The text "{quote}" is painted in very large '
            'ultra-bold white condensed sans-serif capital letters on the ledge wall, each word on its own line. '
            'Blurred city lights create warm amber bokeh in the upper background. Lone figure silhouette stands at the edge, '
            'small in frame for scale. Underexposed 1.5 stops, cool shadow tones, film grain ISO 1600, desaturated 60%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 12, "vignette": 0.3, "desaturate": 0.55, "grade": "cold_noir",
    },

    "street_spray": {
        "template": (
            'Concrete wall inside a dark parking garage or underpass, shot on Leica M11 35mm Summicron handheld. '
            'Raw concrete surface fills the center 70% of the frame with visible texture and water stains. '
            'The text "{quote}" is spray-painted in very large thick black casual handwritten brush capital letters on the '
            'rough concrete, each word on its own line, slightly uneven baseline for authenticity, spanning 75% of frame width. '
            'Single harsh fluorescent tube above casts a pool of cold light on the wall with hard shadows below. '
            'Raw street art aesthetic, underexposed 1 stop, film grain ISO 2000, desaturated 55%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 14, "vignette": 0.25, "desaturate": 0.5, "grade": "raw_industrial",
    },
    "building_projection": {
        "template": (
            'Dark building exterior wall at night, shot on Sony A7IV 24mm f/1.4. Light concrete or stone facade fills '
            'the frame, three warm spotlights mounted above the wall create dramatic pools of amber light with hard shadows. '
            'The text "{quote}" is painted in very large ultra-bold dark condensed sans-serif capital letters on the illuminated '
            'wall surface, each word on its own line, centered, spanning 65% of frame width, occupying the center 45% of frame. '
            'Dark blue-gray twilight sky visible at the top 15% with building silhouettes. Underexposed 1.5 stops, warm/cool '
            'contrast between spotlights and sky, film grain ISO 1600, desaturated 70%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 16, "vignette": 0.35, "desaturate": 0.65, "grade": "amber_glow",
    },

    # ── NATURE & ELEMENTS ──
    "mountain_rock": {
        "template": (
            'Dramatic snow-capped mountain peak against pure black sky, shot on Hasselblad X2D 90mm f/3.2 medium format. '
            'Mountain fills the lower 55% of the frame, strong side lighting from camera-right creates sharp contrast between '
            'bright white snow and dark rock shadows. The text "{quote}" appears carved into the dark rock face in very large '
            'ultra-bold condensed capital letters, each word stacked, spanning 65% of frame width, positioned in the upper 40%. '
            'Epic scale, B&W, crushed blacks, film grain ISO 800, highlight rolloff on snow. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 10, "vignette": 0.35, "desaturate": 0.9, "grade": "cold_epic",
    },
    "ocean_wave": {
        "template": (
            'Massive dark ocean wave frozen at its peak moment, shot on Canon R5 70-200mm f/2.8 at 1/2000 shutter. '
            'Wave fills the lower 60% with visible spray and foam texture. The text "{quote}" appears in very large ultra-bold '
            'white condensed sans-serif capital letters in the dark stormy sky above the wave crest, each word on its own line, '
            'centered, spanning 70% of frame width. Dramatic underexposed 2 stops, desaturated to near-monochrome with '
            'cold blue-gray tones only. Heavy film grain ISO 2000, crushed blacks. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 16, "vignette": 0.3, "desaturate": 0.75, "grade": "cold_epic",
    },
    "lightning_desert": {
        "template": (
            'Lightning bolt striking desert ground at night, shot on Sony A7IV 24mm f/1.4 long exposure 4 seconds. '
            'Lightning illuminates the landscape from above, cracked desert earth visible in the lower 40% of frame. '
            'The text "{quote}" appears in very large ultra-bold white condensed capital letters across the dark sky in the '
            'upper 45% of the frame, each word on its own line, centered, spanning 75% of frame width. '
            'Purple-black sky, raw power, underexposed, film grain ISO 1600, desaturated 65%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 14, "vignette": 0.25, "desaturate": 0.6, "grade": "cold_epic",
    },

    # ── LUXURY & POWER ──
    "chess_shadow": {
        "template": (
            'Single black chess pawn on a chess board, shot on Hasselblad X2D 80mm f/1.9 with shallow depth of field. '
            'Pawn occupies the lower-center 35% of the frame, casting dramatic elongated shadows behind it that resemble '
            'larger pieces — king, queen, knight. Single hard directional light from camera-left at 15 degrees. '
            'The text "{quote}" appears in very large ultra-bold white condensed sans-serif capital letters in the dark upper '
            '45% of the frame, each word on its own line, centered, spanning 65% of frame width. '
            'B&W, crushed blacks with lifted shadows, film grain ISO 800, conceptual symbolic photography. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 12, "vignette": 0.4, "desaturate": 0.9, "grade": "neutral_bw",
    },
    "empty_throne": {
        "template": (
            'Ornate dark throne sitting empty in a shadowy grand medieval hall, shot on Canon R5 35mm f/1.4. '
            'Throne occupies the center-lower 50% of the frame. Single beam of light from a high window above illuminates '
            'dust particles floating in the air. The text "{quote}" is carved into the dark stone wall behind the throne in '
            'very large ultra-bold condensed capital letters, each word stacked, spanning 60% of frame width, occupying the '
            'upper 40% of composition. Dark medieval power aesthetic, underexposed 2 stops, film grain ISO 1200, desaturated 75%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 10, "vignette": 0.45, "desaturate": 0.7, "grade": "warm_luxury",
    },
    "crown_velvet": {
        "template": (
            'Dark golden crown resting on black velvet fabric, shot on Hasselblad X2D 120mm macro f/4 in studio. '
            'Crown occupies the lower-center 30% of the frame with razor-sharp detail, everything else pure black. '
            'Single directional key light from above-right at 60 degrees, minimal spill, deep shadows. '
            'The text "{quote}" appears in very large ultra-bold white condensed sans-serif capital letters in the upper 50% '
            'of the frame against pure black, each word on its own line, centered, spanning 65% of frame width. '
            'Minimal luxury aesthetic, film grain ISO 400, desaturated 50%, warm amber on crown only. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 8, "vignette": 0.35, "desaturate": 0.45, "grade": "warm_luxury",
    },
    "lion_portrait": {
        "template": (
            'Majestic male lion face portrait, shot on Canon R5 85mm f/1.2 in low-key studio lighting. '
            'Only the mane edge and one amber eye are lit by a single hard key light from camera-right, the rest dissolves '
            'into deep shadow. Lion fills the lower 55% of the frame. The text "{quote}" appears in very large ultra-bold '
            'white condensed sans-serif capital letters across the dark upper 40% of the frame, each word on its own line, '
            'left-aligned at 10% margin, spanning 70% of frame width. Very high contrast, near-silhouette, B&W with warm amber '
            'eye only. Film grain ISO 1000, crushed blacks. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 12, "vignette": 0.4, "desaturate": 0.92, "grade": "neutral_bw",
    },

    # ── HUMAN SILHOUETTES ──
    "cliff_figure": {
        "template": (
            'Lone figure silhouette standing on cliff edge at night, shot on Sony A7IV 35mm f/1.4. '
            'Figure is small, occupying only 15% of the frame in the lower-center, creating vast negative space above. '
            'Dramatic backlight from behind creates a rim of warm light around the person against deep black sky. '
            'The text "{quote}" appears in very large ultra-bold white condensed sans-serif capital letters in the dark sky, '
            'occupying the upper 45% of the frame, each word on its own line, centered, spanning 70% of frame width. '
            'Cinematic, vast scale, underexposed 2 stops, film grain ISO 1600, desaturated 80%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 12, "vignette": 0.3, "desaturate": 0.8, "grade": "neutral_bw",
    },
    "stairs_light": {
        "template": (
            'Silhouette of a person climbing a long concrete staircase toward a bright glowing white doorway at the top, '
            'shot on Leica M11 28mm Summicron. Staircase runs vertically through the center of the frame, figure is small '
            'at 30% height. The text "{quote}" appears in very large ultra-bold white condensed sans-serif capital letters '
            'on the dark wall to the left of the staircase, each word stacked vertically, left-aligned at 8% margin, '
            'spanning 55% of frame width, occupying the left 60% of composition. Pure black background, high contrast, '
            'conceptual. Film grain ISO 800, desaturated 85%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 8, "vignette": 0.3, "desaturate": 0.85, "grade": "neutral_bw",
    },
    "rain_walker": {
        "template": (
            'Man in dark suit walking alone through heavy rain at night, shot on Sony A7IV 50mm f/1.4 at 1/60 shutter. '
            'Figure occupies the center-lower 40% of the frame with motion blur on rain drops. Single streetlight behind '
            'creates a warm halo and rim light. The text "{quote}" appears in very large ultra-bold white condensed sans-serif '
            'capital letters reflected in the wet pavement in the lower 35% of the frame, and also floating in the dark sky '
            'above in the upper 30%, each word on its own line, centered, spanning 70% of frame width. '
            'Cinematic noir, B&W, heavy film grain ISO 2500, crushed blacks. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 18, "vignette": 0.35, "desaturate": 0.92, "grade": "cold_noir",
    },

    # ── INDUSTRIAL & GRIT ──
    "welding_sparks": {
        "template": (
            'Welder in dark workshop with bright orange sparks flying, shot on Canon R5 35mm f/1.4. '
            'Welder silhouette occupies the lower-right 30% of frame, shower of sparks illuminates the scene. '
            'The text "{quote}" is welded into a large steel plate mounted on the wall in very large bold condensed capital '
            'letters, glowing hot orange-amber, each word on its own line, occupying the upper-left 50% of frame, spanning '
            '65% of frame width. Dark industrial atmosphere, only sparks and glowing text illuminate the scene. '
            'Film grain ISO 1600, desaturated 55% with warm amber sparks only. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 14, "vignette": 0.3, "desaturate": 0.5, "grade": "raw_industrial",
    },
    "train_tunnel": {
        "template": (
            'Dark train tracks disappearing into a black tunnel, shot on Leica M11 28mm Summicron from track level. '
            'Tracks create strong perspective lines converging to a single point of light at the tunnel end, occupying the '
            'lower 50% of frame. The text "{quote}" is painted in very large ultra-bold white condensed sans-serif capital '
            'letters on the dark tunnel entrance wall above the tracks, each word on its own line, centered, spanning 75% '
            'of frame width, occupying the upper 45%. Industrial grit, underexposed 2 stops, film grain ISO 2000, '
            'desaturated 80%, cool blue-gray tones. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 18, "vignette": 0.4, "desaturate": 0.8, "grade": "cold_noir",
    },

    # ── CLASSICAL & ARTISTIC ──
    "backlit_3d": {
        "template": (
            'Dark matte wall with 3D raised metal capital letters mounted on the surface, shot on Hasselblad X2D 80mm f/1.9. '
            'The letters spell "{quote}" — one word per line, stacked vertically, each letter made of dark matte brushed metal '
            'casting a warm golden amber backlight glow behind it on the wall. Letters appear to float 2cm off the surface. '
            'Text occupies the center 50% of the frame, spanning 70% of frame width. Minimal elegant luxury aesthetic, '
            'very dark background, warm amber backlighting creating soft halos. Film grain ISO 400, desaturated 35%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 8, "vignette": 0.45, "desaturate": 0.3, "grade": "amber_glow",
    },
    "marble_statue": {
        "template": (
            'Broken classical Greek marble statue in a dark museum, shot on Canon R5 85mm f/1.2. Only the head and one shoulder '
            'are visible in the lower 45% of the frame, dramatically lit from camera-left at 30 degrees with hard key light, '
            'no fill. The text "{quote}" is chiseled into the marble pedestal in very large ultra-bold condensed capital letters, '
            'each word on its own line, occupying the upper 45% of the frame, spanning 65% of frame width. Dark background, '
            'dust particles visible in the light beam, high contrast. Film grain ISO 800, desaturated 75%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 10, "vignette": 0.35, "desaturate": 0.7, "grade": "film_classic",
    },
    "canvas_brush": {
        "template": (
            'Large white canvas hanging on dark wood-paneled wall in a luxury restaurant, shot on Leica M11 50mm Summilux. '
            'Canvas occupies the center 55% of the frame. The text "{quote}" is painted on the canvas in very large thick '
            'black expressive brush strokes, bold uppercase, each word on its own line, spanning 80% of canvas width. '
            'Warm candle glow from below illuminates the canvas edges, dark wood panels and mirrors in soft background bokeh. '
            'Elegant warm ambient lighting, underexposed 1 stop, film grain ISO 600, minimal desaturation 25%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 8, "vignette": 0.3, "desaturate": 0.2, "grade": "film_classic",
    },
    "newspaper_marker": {
        "template": (
            'Newspaper front page held up against city skyline at dusk, shot on iPhone 15 Pro 24mm night mode for authenticity. '
            'Newspaper fills the center 60% of the frame. The text "{quote}" is scrawled across the newspaper in very large '
            'thick black marker/sharpie bold capital letters, each word on its own line, overlapping the printed columns. '
            'City skyline with warm lights visible behind at the top 20% and bottom 20% of frame. '
            'Raw rebellious aesthetic, handheld slight blur, film grain ISO 2000, desaturated 40%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 16, "vignette": 0.25, "desaturate": 0.35, "grade": "film_classic",
    },
    "lightbox_sign": {
        "template": (
            'Warm illuminated rectangular lightbox sign hanging from a dark metal pole, shot on Leica M11 75mm Summilux. '
            'Sign occupies the center 40% of the frame against a deep blue-gray dusky evening sky. The lightbox displays '
            'the text "{quote}" in very large ultra-bold dark condensed sans-serif capital letters on a warm glowing '
            'cream/yellow surface, each word on its own line. The sign emits a soft warm glow with falloff to dark edges. '
            'Vintage film aesthetic, visible stars, film grain ISO 1600, desaturated 45%. '
            'No decorative fonts, no cursive, no thin fonts, no small text, no watermarks, no extra text. 9:16 portrait.'
        ),
        "grain": 20, "vignette": 0.3, "desaturate": 0.4, "grade": "amber_glow",
    },
}

AI_BG_PROMPTS = {}

# --- All AI scene style names (for routing in pipeline) ---
AI_SCENE_STYLES = list(AI_SCENE_PROMPTS.keys())

# --- All AI background style names (for routing in pipeline) ---
AI_BG_STYLES = list(AI_BG_PROMPTS.keys())

# --- Combined list of all AI styles ---
ALL_AI_STYLES = AI_SCENE_STYLES + AI_BG_STYLES


def generate_ai_image(prompt, output_path, aspect_ratio="9:16"):
    """
    # Generates an image using the best available AI provider:
    #   1. fal.ai Flux Pro (if FAL_KEY set) — best for text-in-image, ~$0.01/img
    #   2. Gemini image model (if GEMINI_API_KEY set, paid tier) — free with billing
    #   3. Imagen 4 (if GEMINI_API_KEY set, paid tier) — highest quality
    #
    # Returns the saved image path, or None if all providers fail
    """
    fal_key = os.getenv("FAL_KEY", "").strip()
    gemini_key = config.GEMINI_API_KEY

    # --- Try fal.ai Flux Pro first (best at text rendering) ---
    if fal_key:
        result = _generate_fal_image(prompt, output_path, fal_key, aspect_ratio)
        if result:
            return result

    # --- Try Gemini image generation model (free with paid billing) ---
    if gemini_key:
        result = _generate_gemini_image(prompt, output_path, gemini_key)
        if result:
            return result

    # --- Try Imagen 4 (requires paid plan) ---
    if gemini_key:
        result = _generate_ai_image(prompt, output_path, gemini_key, aspect_ratio)
        if result:
            return result

    print("[AI_QUOTE] No AI image provider available. Set FAL_KEY or upgrade Gemini to paid plan.")
    return None


# --- Max retries for text quality verification ---
MAX_QUALITY_RETRIES = 3


def verify_text_quality(image_path, expected_text):
    """
    # Uses Gemini Vision to verify the text in a generated image
    # is readable, correctly spelled, and matches the expected quote.
    #
    # Returns (passed: bool, reason: str)
    """
    if not config.GEMINI_API_KEY:
        # --- Can't verify without Gemini, assume pass ---
        return True, "no_api_key"

    try:
        from google import genai
        from google.genai import types
        import base64

        client = genai.Client(api_key=config.GEMINI_API_KEY)

        # --- Read image as base64 ---
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        img_b64 = base64.b64encode(img_bytes).decode()

        # --- Ask Gemini to read and verify the text ---
        verify_prompt = (
            f'Read the text visible in this image. The expected text is: "{expected_text}"\n\n'
            f'Respond with valid JSON only:\n'
            f'{{"text_found": "the exact text you see in the image", '
            f'"readable": true/false, '
            f'"matches": true/false, '
            f'"quality": "perfect" or "acceptable" or "poor"}}\n\n'
            f'Rules:\n'
            f'- "readable": can a human easily read every word at phone screen size?\n'
            f'- "matches": does the visible text match the expected text (minor formatting differences OK)?\n'
            f'- "quality": "perfect"=crisp clear text, "acceptable"=readable but slightly rough, '
            f'"poor"=garbled/misspelled/unreadable'
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(role="user", parts=[
                    types.Part(text=verify_prompt),
                    types.Part(inline_data=types.Blob(
                        mime_type="image/png",
                        data=img_bytes,
                    )),
                ]),
            ],
            config=types.GenerateContentConfig(
                max_output_tokens=300,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
            ),
        )

        result = _parse_json_safe(response.text)
        readable = result.get("readable", False)
        matches = result.get("matches", False)
        quality = result.get("quality", "poor")
        text_found = result.get("text_found", "")

        passed = readable and matches and quality != "poor"

        if passed:
            print(f"[AI_QUOTE] Quality check PASSED: quality={quality}")
        else:
            print(f"[AI_QUOTE] Quality check FAILED: readable={readable}, matches={matches}, "
                  f"quality={quality}, found='{text_found[:50]}'")

        return passed, quality

    except Exception as e:
        print(f"[AI_QUOTE] Quality check error (assuming pass): {e}")
        return True, "error"


def _resize_to_target(img, target_w=1080, target_h=1920):
    """
    # Resize and center-crop an image to exactly target dimensions.
    """
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h
    if img_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * img_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / img_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def render_dynamic_image(quote_text, output_path, previous_concepts=None):
    """
    # The main entry point for the automated pipeline.
    # 1. Gemini designs a unique scene concept for this quote
    # 2. AI provider renders the image with text baked in
    # 3. Gemini Vision verifies text quality (auto-retry if garbled)
    # 4. Post-processing applies cinematic film look
    #
    # Returns (output_path, concept_tag) or (None, None) if all AI fails
    """
    # --- Step 1: Gemini designs the scene ---
    design = generate_dynamic_prompt(quote_text, previous_concepts)
    prompt = design["prompt"]
    concept = design.get("_concept", "unknown")

    if not output_path:
        tag = random.randint(1000, 9999)
        output_path = os.path.join(config.TEMP_DIR, f"ai_dynamic_{tag}.png")

    # --- Step 2: Generate + verify loop (up to MAX_QUALITY_RETRIES) ---
    raw_path = output_path.replace(".png", "_raw.png")

    for attempt in range(MAX_QUALITY_RETRIES):
        result = generate_ai_image(prompt, raw_path)
        if not result:
            return None, concept

        # --- Verify text quality ---
        passed, quality = verify_text_quality(raw_path, quote_text)
        if passed:
            if attempt > 0:
                print(f"[AI_QUOTE] Passed on attempt {attempt + 1}")
            break

        if attempt < MAX_QUALITY_RETRIES - 1:
            print(f"[AI_QUOTE] Retry {attempt + 2}/{MAX_QUALITY_RETRIES} — regenerating...")
            try:
                os.remove(raw_path)
            except OSError:
                pass
    else:
        # --- All retries exhausted, use last generated image ---
        print(f"[AI_QUOTE] Max retries reached, using best available image")

    # --- Step 3: Load and resize to 1080x1920 ---
    img = Image.open(raw_path).convert("RGB")
    img = _resize_to_target(img)

    # --- Step 4: Post-processing with adaptive grade ---
    img = apply_post_processing(
        img,
        grain_amount=design.get("grain", 12),
        vignette_strength=design.get("vignette", 0.35),
        desaturate_amount=design.get("desaturate", 0.5),
        grade_name=design.get("grade", DEFAULT_GRADE),
    )

    img.save(output_path, quality=95)
    print(f"[AI_QUOTE] Dynamic image rendered -> {output_path} [grade: {design.get('grade', DEFAULT_GRADE)}]")

    try:
        os.remove(raw_path)
    except OSError:
        pass

    return output_path, concept


def render_dynamic_progressive(quote_text, output_dir, previous_concepts=None):
    """
    # Word-by-word reveal — each frame is a separate AI generation
    # with progressively more words of the quote baked into the same scene.
    # Each frame is verified for text quality before accepting.
    #
    # Returns (list_of_frame_paths, concept_tag) or (None, concept_tag)
    """
    design = generate_dynamic_prompt(quote_text, previous_concepts)
    concept = design.get("_concept", "unknown")
    original_prompt = design["prompt"]

    os.makedirs(output_dir, exist_ok=True)
    tag = random.randint(1000, 9999)

    words = quote_text.split()
    frame_paths = []

    for word_count in range(1, len(words) + 1):
        partial_text = " ".join(words[:word_count])
        frame_prompt = original_prompt.replace(quote_text, partial_text)

        frame_path = os.path.join(output_dir, f"ai_prog_{tag}_w{word_count}.png")
        raw_path = frame_path.replace(".png", "_raw.png")

        # --- Generate + verify loop per frame ---
        frame_ok = False
        for attempt in range(MAX_QUALITY_RETRIES):
            result = generate_ai_image(frame_prompt, raw_path)
            if not result:
                break

            passed, _ = verify_text_quality(raw_path, partial_text)
            if passed:
                frame_ok = True
                break

            if attempt < MAX_QUALITY_RETRIES - 1:
                print(f"[AI_QUOTE] Frame {word_count} retry {attempt + 2}...")
                try:
                    os.remove(raw_path)
                except OSError:
                    pass

        if not frame_ok and not os.path.exists(raw_path):
            print(f"[AI_QUOTE] Progressive frame {word_count} failed, aborting")
            break

        # --- Resize and post-process ---
        img = Image.open(raw_path).convert("RGB")
        img = _resize_to_target(img)
        img = apply_post_processing(
            img,
            grain_amount=design.get("grain", 12),
            vignette_strength=design.get("vignette", 0.35),
            desaturate_amount=design.get("desaturate", 0.5),
            grade_name=design.get("grade", DEFAULT_GRADE),
        )
        img.save(frame_path, quality=95)
        frame_paths.append(frame_path)

        try:
            os.remove(raw_path)
        except OSError:
            pass

    if not frame_paths:
        return None, concept

    print(f"[AI_QUOTE] Progressive frames: {len(frame_paths)} for '{quote_text[:30]}...'")
    return frame_paths, concept


def _generate_fal_image(prompt, output_path, fal_key, aspect_ratio="9:16"):
    """
    # Generates image with fal.ai Flux Pro v1.1
    # Best text-in-image rendering of all Flux models
    # Pricing: ~$0.01-0.04 per image
    # Sign up: https://fal.ai — set FAL_KEY in .env
    """
    try:
        import fal_client
    except ImportError:
        try:
            import fal as fal_client
        except ImportError:
            print("[AI_QUOTE] fal_client not installed. Run: pip install fal-client")
            return None

    # --- Map aspect ratio to pixel dimensions (9:16 portrait) ---
    size_map = {
        "9:16": {"width": 768, "height": 1344},
        "16:9": {"width": 1344, "height": 768},
        "1:1": {"width": 1024, "height": 1024},
    }
    img_size = size_map.get(aspect_ratio, size_map["9:16"])

    try:
        os.environ["FAL_KEY"] = fal_key
        print(f"[AI_QUOTE] Generating with fal.ai Flux Pro...")
        print(f"[AI_QUOTE] Prompt: {prompt[:100]}...")

        result = fal_client.subscribe(
            "fal-ai/flux-pro/v1.1",
            arguments={
                "prompt": prompt,
                "image_size": img_size,
                "num_images": 1,
                "enable_safety_checker": False,
            },
        )

        # --- Download the generated image ---
        if result and "images" in result and len(result["images"]) > 0:
            img_url = result["images"][0]["url"]
            import requests
            resp = requests.get(img_url, timeout=30)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                print(f"[AI_QUOTE] fal.ai image saved: {output_path}")
                return output_path
        print("[AI_QUOTE] fal.ai returned empty result")
        return None

    except Exception as e:
        print(f"[AI_QUOTE] fal.ai generation failed: {e}")
        return None


def _generate_gemini_image(prompt, output_path, api_key):
    """
    # Generates image with Gemini's built-in image generation
    # Uses gemini-2.5-flash-image or gemini-3-pro-image model
    # Requires paid billing enabled at https://ai.dev/projects
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # --- Try models in preference order ---
    models = [
        "gemini-3.1-flash-image",
        "gemini-3-pro-image",
        "gemini-2.5-flash-image",
    ]

    for model_name in models:
        try:
            print(f"[AI_QUOTE] Trying Gemini model: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            # --- Extract image from response parts ---
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    img_bytes = part.inline_data.data
                    with open(output_path, "wb") as f:
                        f.write(img_bytes)
                    print(f"[AI_QUOTE] Gemini image saved: {output_path}")
                    return output_path

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                print(f"[AI_QUOTE] {model_name}: rate limited / paid plan required")
                continue
            print(f"[AI_QUOTE] {model_name} failed: {e}")
            continue

    return None


def _generate_ai_image(prompt, output_path, api_key, aspect_ratio="9:16"):
    """
    # Generates image with Google Imagen 4 (highest quality)
    # Requires paid Gemini plan
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    try:
        print(f"[AI_QUOTE] Trying Imagen 4...")
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                output_mime_type="image/png",
            ),
        )

        if response.generated_images and len(response.generated_images) > 0:
            img_bytes = response.generated_images[0].image.image_bytes
            with open(output_path, "wb") as f:
                f.write(img_bytes)
            print(f"[AI_QUOTE] Imagen 4 saved: {output_path}")
            return output_path

    except Exception as e:
        print(f"[AI_QUOTE] Imagen 4 failed: {e}")

    return None


def apply_post_processing(img, grain_amount=12, vignette_strength=0.4,
                          desaturate_amount=0.0, grade_name=None):
    """
    # Adaptive cinematic color grading — each scene gets a grade matched to its mood.
    # Grade presets control: black floor, contrast curve, shadow/highlight tinting, clarity.
    # Per-image params (grain, vignette, desaturate) layer on top of the grade.
    """
    # --- Resolve grade preset ---
    grade = GRADE_PRESETS.get(grade_name, GRADE_PRESETS[DEFAULT_GRADE])
    if grade_name and grade_name not in GRADE_PRESETS:
        print(f"[AI_QUOTE] Unknown grade '{grade_name}', using '{DEFAULT_GRADE}'")

    black_floor = float(grade["black_floor"])
    s_strength = grade["s_curve"]
    shadow_tint = grade["shadow_tint"]
    shadow_str = grade["shadow_strength"]
    highlight_tint = grade["highlight_tint"]
    highlight_str = grade["highlight_strength"]
    clarity_strength = grade["clarity"]

    arr = np.array(img, dtype=np.float32)

    # ── 1. LIFT BLACKS ──
    arr = arr * ((255.0 - black_floor) / 255.0) + black_floor

    # ── 2. S-CURVE CONTRAST ──
    normalized = arr / 255.0
    curved = normalized + s_strength * np.sin(2.0 * np.pi * (normalized - 0.5)) / (2.0 * np.pi)
    arr = np.clip(curved * 255.0, 0, 255)

    # ── 3. SPLIT TONING ──
    if shadow_str > 0 or highlight_str > 0:
        luminance = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        shadow_mask = np.clip(1.0 - luminance / 80.0, 0, 1)
        highlight_mask = np.clip((luminance - 160.0) / 95.0, 0, 1)

        if shadow_str > 0:
            arr[:, :, 0] += shadow_mask * shadow_str * shadow_tint[0]
            arr[:, :, 1] += shadow_mask * shadow_str * shadow_tint[1]
            arr[:, :, 2] += shadow_mask * shadow_str * shadow_tint[2]

        if highlight_str > 0:
            arr[:, :, 0] += highlight_mask * highlight_str * highlight_tint[0]
            arr[:, :, 1] += highlight_mask * highlight_str * highlight_tint[1]
            arr[:, :, 2] += highlight_mask * highlight_str * highlight_tint[2]

    # ── 4. DESATURATE ──
    if desaturate_amount > 0:
        gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        for c in range(3):
            arr[:, :, c] = arr[:, :, c] * (1.0 - desaturate_amount) + gray * desaturate_amount

    # ── 5. MICRO-CONTRAST (CLARITY) ──
    if clarity_strength > 0:
        from PIL import ImageFilter as _IF
        temp_img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        blurred = temp_img.filter(_IF.GaussianBlur(radius=15))
        blur_arr = np.array(blurred, dtype=np.float32)
        detail = arr - blur_arr
        arr = arr + detail * clarity_strength

    # ── 6. VIGNETTE ──
    if vignette_strength > 0:
        h, w = arr.shape[:2]
        Y, X = np.ogrid[:h, :w]
        cx, cy = w / 2.0, h / 2.0
        dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
        vignette_map = 1.0 - vignette_strength * np.clip(dist, 0, 1.5) ** 2.0
        for c in range(3):
            arr[:, :, c] *= vignette_map

    # ── 7. FILM GRAIN ──
    if grain_amount > 0:
        noise = np.random.normal(0, grain_amount, arr.shape[:2]).astype(np.float32)
        lum = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]) / 255.0
        grain_mask = 4.0 * lum * (1.0 - lum)
        grain_mask = np.clip(grain_mask, 0.2, 1.0)
        for c in range(3):
            arr[:, :, c] += noise * grain_mask

    # ── 8. FINAL CRUSH ──
    arr = np.clip(arr, black_floor, 250.0)

    return Image.fromarray(arr.astype(np.uint8))


def render_ai_scene_image(quote_text, style_name, output_path=None):
    """
    # Generates a complete scene-integrated quote image using Imagen 4
    # The quote text is baked directly into the AI-generated scene
    # (subway billboard, 3D letters, spray paint on wall, etc.)
    #
    # Returns output image path, or None if AI generation fails
    # Caller should fall back to Pillow rendering on None
    """
    if style_name not in AI_SCENE_PROMPTS:
        print(f"[AI_QUOTE] Unknown AI scene style: {style_name}")
        return None

    style = AI_SCENE_PROMPTS[style_name]

    # --- Build the prompt with the quote text inserted ---
    prompt = style["template"].format(quote=quote_text)

    # --- Generate with Imagen 4 ---
    if not output_path:
        tag = random.randint(1000, 9999)
        output_path = os.path.join(config.TEMP_DIR, f"ai_scene_{style_name}_{tag}.png")

    raw_path = output_path.replace(".png", "_raw.png")
    result = generate_ai_image(prompt, raw_path)

    if not result:
        return None

    # --- Load and resize to exactly 1080x1920 ---
    img = Image.open(raw_path).convert("RGB")
    target_w, target_h = 1080, 1920
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h
    if img_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * img_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / img_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))

    # --- Apply adaptive post-processing ---
    img = apply_post_processing(
        img,
        grain_amount=style.get("grain", 12),
        vignette_strength=style.get("vignette", 0.35),
        desaturate_amount=style.get("desaturate", 0.5),
        grade_name=style.get("grade", DEFAULT_GRADE),
    )

    img.save(output_path, quality=95)
    print(f"[AI_QUOTE] Scene image rendered: {style_name} -> {output_path}")

    # --- Clean up raw file ---
    try:
        os.remove(raw_path)
    except OSError:
        pass

    return output_path


def render_ai_bg_with_text(quote_text, style_name, output_path=None):
    """
    # Two-step render:
    #   1. Generate symbolic background with Imagen 4 (chess, mountain, etc.)
    #   2. Overlay quote text using Pillow (perfect text, no AI garbling)
    #
    # Returns output image path, or None if AI generation fails
    """
    if style_name not in AI_BG_PROMPTS:
        print(f"[AI_QUOTE] Unknown AI bg style: {style_name}")
        return None

    style = AI_BG_PROMPTS[style_name]

    # --- Step 1: Generate background with Imagen 4 ---
    bg_prompt = style["template"]
    if not output_path:
        tag = random.randint(1000, 9999)
        output_path = os.path.join(config.TEMP_DIR, f"ai_bg_{style_name}_{tag}.png")

    raw_path = output_path.replace(".png", "_raw.png")
    result = generate_ai_image(bg_prompt, raw_path)

    if not result:
        return None

    # --- Load and resize to 1080x1920 ---
    bg = Image.open(raw_path).convert("RGB")
    target_w, target_h = 1080, 1920
    bg_ratio = bg.width / bg.height
    target_ratio = target_w / target_h
    if bg_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * bg_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / bg_ratio)
    bg = bg.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    bg = bg.crop((left, top, left + target_w, top + target_h))

    # --- Step 2: Overlay text with Pillow ---
    draw = ImageDraw.Draw(bg)

    # --- Load font ---
    font_key = style.get("font_key", "montserrat")
    font_path = FONT_FILES.get(font_key, FONT_FILES["montserrat"])
    text_color = style.get("text_color", (255, 255, 255))
    alignment = style.get("alignment", "left")
    uppercase = style.get("uppercase", False)
    position = style.get("position", "center")

    text = quote_text.upper() if uppercase else quote_text

    # --- Dynamic font sizing based on word count ---
    word_count = len(quote_text.split())
    base_size = style.get("base_font_size", 80)
    if word_count <= 4:
        font_size = int(base_size * 1.35)
    elif word_count <= 7:
        font_size = int(base_size * 1.1)
    elif word_count <= 10:
        font_size = base_size
    else:
        font_size = int(base_size * 0.8)

    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.truetype(FONT_FILES["montserrat"], font_size)

    # --- Safe margins ---
    margin_x = int(target_w * 0.10)
    margin_y = int(target_h * 0.12)
    max_text_width = target_w - (margin_x * 2)

    # --- Split text into lines ---
    import textwrap
    lines = textwrap.wrap(text, width=80)

    # --- Re-wrap lines that are too wide ---
    final_lines = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_text_width:
            final_lines.append(line)
        else:
            words = line.split()
            current = ""
            for word in words:
                test = f"{current} {word}".strip()
                bbox = draw.textbbox((0, 0), test, font=font)
                if bbox[2] - bbox[0] <= max_text_width:
                    current = test
                else:
                    if current:
                        final_lines.append(current)
                    current = word
            if current:
                final_lines.append(current)
    lines = final_lines

    # --- Measure lines ---
    line_metrics = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_metrics.append((bbox[2] - bbox[0], bbox[3] - bbox[1]))

    ref_bbox = draw.textbbox((0, 0), "Ay", font=font)
    ref_h = ref_bbox[3] - ref_bbox[1]
    line_spacing = int(ref_h * 1.25)
    total_text_h = line_spacing * len(lines)

    # --- Calculate text position based on style ---
    if position == "upper_third":
        start_y = int(target_h * 0.15)
    elif position == "upper_left":
        start_y = int(target_h * 0.10)
    elif position == "mid_left":
        start_y = int(target_h * 0.40)
    elif position == "lower_left":
        start_y = int(target_h * 0.65)
    elif position == "lower_third":
        start_y = int(target_h * 0.70)
    else:
        start_y = (target_h - total_text_h) // 2

    # --- Draw each line with shadow for readability ---
    for i, line in enumerate(lines):
        lw, lh = line_metrics[i]
        y = start_y + (i * line_spacing)

        if alignment == "center":
            x = (target_w - lw) // 2
        elif alignment == "left":
            x = margin_x
        else:
            x = target_w - lw - margin_x

        x = max(margin_x, min(x, target_w - margin_x - lw))

        # --- Subtle shadow for readability on complex backgrounds ---
        shadow_offset = max(2, font_size // 25)
        for sx in range(1, shadow_offset + 1):
            draw.text((x + sx, y + sx), line, font=font, fill=(0, 0, 0))

        # --- Main text ---
        draw.text((x, y), line, font=font, fill=text_color)

    # --- Apply adaptive post-processing ---
    bg = apply_post_processing(
        bg,
        grain_amount=style.get("grain", 12),
        vignette_strength=style.get("vignette", 0.35),
        desaturate_amount=style.get("desaturate", 0.5),
        grade_name=style.get("grade", DEFAULT_GRADE),
    )

    bg.save(output_path, quality=95)
    print(f"[AI_QUOTE] BG+text image rendered: {style_name} -> {output_path}")

    # --- Clean up raw background ---
    try:
        os.remove(raw_path)
    except OSError:
        pass

    return output_path


def render_ai_bg_progressive(quote_text, style_name, output_dir=None):
    """
    # Word-by-word reveal for AI background styles
    # Generates the AI background ONCE, then renders multiple text frames
    # Returns list of frame paths (like render_progressive_frames in quote_reel.py)
    """
    if style_name not in AI_BG_PROMPTS:
        return None

    style = AI_BG_PROMPTS[style_name]

    if not output_dir:
        output_dir = config.TEMP_DIR
    os.makedirs(output_dir, exist_ok=True)

    # --- Generate background once ---
    bg_prompt = style["template"]
    tag = random.randint(1000, 9999)
    raw_path = os.path.join(output_dir, f"ai_bg_{style_name}_{tag}_raw.png")
    result = generate_ai_image(bg_prompt, raw_path)

    if not result:
        return None

    # --- Load and resize ---
    bg_original = Image.open(raw_path).convert("RGB")
    target_w, target_h = 1080, 1920
    bg_ratio = bg_original.width / bg_original.height
    target_ratio = target_w / target_h
    if bg_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * bg_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / bg_ratio)
    bg_original = bg_original.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    bg_original = bg_original.crop((left, top, left + target_w, top + target_h))

    # --- Render each word-count frame using the same background ---
    words = quote_text.split()
    frame_paths = []

    for word_count in range(1, len(words) + 1):
        partial_text = " ".join(words[:word_count])
        frame_path = os.path.join(output_dir, f"ai_reveal_{tag}_w{word_count}.png")

        # --- Copy background for each frame ---
        bg = bg_original.copy()
        draw = ImageDraw.Draw(bg)

        # --- Load font and render text (same logic as render_ai_bg_with_text) ---
        font_key = style.get("font_key", "montserrat")
        font_path_str = FONT_FILES.get(font_key, FONT_FILES["montserrat"])
        text_color = style.get("text_color", (255, 255, 255))
        alignment = style.get("alignment", "left")
        uppercase = style.get("uppercase", False)
        position = style.get("position", "center")

        text = partial_text.upper() if uppercase else partial_text

        wc = len(quote_text.split())
        base_size = style.get("base_font_size", 80)
        if wc <= 4:
            font_size = int(base_size * 1.35)
        elif wc <= 7:
            font_size = int(base_size * 1.1)
        elif wc <= 10:
            font_size = base_size
        else:
            font_size = int(base_size * 0.8)

        try:
            font = ImageFont.truetype(font_path_str, font_size)
        except Exception:
            font = ImageFont.truetype(FONT_FILES["montserrat"], font_size)

        margin_x = int(target_w * 0.10)
        max_tw = target_w - (margin_x * 2)

        import textwrap
        lines = textwrap.wrap(text, width=80)
        final_lines = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            if bbox[2] - bbox[0] <= max_tw:
                final_lines.append(line)
            else:
                wds = line.split()
                cur = ""
                for w in wds:
                    t = f"{cur} {w}".strip()
                    bbox = draw.textbbox((0, 0), t, font=font)
                    if bbox[2] - bbox[0] <= max_tw:
                        cur = t
                    else:
                        if cur:
                            final_lines.append(cur)
                        cur = w
                if cur:
                    final_lines.append(cur)
        lines = final_lines

        line_metrics = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_metrics.append((bbox[2] - bbox[0], bbox[3] - bbox[1]))

        ref_bbox = draw.textbbox((0, 0), "Ay", font=font)
        ref_h = ref_bbox[3] - ref_bbox[1]
        line_spacing = int(ref_h * 1.25)
        total_text_h = line_spacing * len(lines)

        if position == "upper_third":
            start_y = int(target_h * 0.15)
        elif position == "upper_left":
            start_y = int(target_h * 0.10)
        elif position == "mid_left":
            start_y = int(target_h * 0.40)
        elif position == "lower_left":
            start_y = int(target_h * 0.65)
        elif position == "lower_third":
            start_y = int(target_h * 0.70)
        else:
            start_y = (target_h - total_text_h) // 2

        for i, line in enumerate(lines):
            lw, lh = line_metrics[i]
            y = start_y + (i * line_spacing)
            if alignment == "center":
                x = (target_w - lw) // 2
            elif alignment == "left":
                x = margin_x
            else:
                x = target_w - lw - margin_x
            x = max(margin_x, min(x, target_w - margin_x - lw))
            shadow_offset = max(2, font_size // 25)
            for sx in range(1, shadow_offset + 1):
                draw.text((x + sx, y + sx), line, font=font, fill=(0, 0, 0))
            draw.text((x, y), line, font=font, fill=text_color)

        # --- Apply adaptive post-processing ---
        bg = apply_post_processing(
            bg,
            grain_amount=style.get("grain", 12),
            vignette_strength=style.get("vignette", 0.35),
            desaturate_amount=style.get("desaturate", 0.5),
            grade_name=style.get("grade", DEFAULT_GRADE),
        )

        bg.save(frame_path, quality=95)
        frame_paths.append(frame_path)

    print(f"[AI_QUOTE] Progressive frames: {len(frame_paths)} for '{quote_text[:30]}...'")

    # --- Clean up raw background ---
    try:
        os.remove(raw_path)
    except OSError:
        pass

    return frame_paths
