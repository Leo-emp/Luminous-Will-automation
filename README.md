# Luminous Will - Automated Video Pipeline

Automated video production pipeline for creating dark aesthetic motivational/psychological content for social media (Instagram Reels, TikTok, YouTube Shorts).

## What It Does

Generates complete vertical (9:16) videos automatically:
1. **Script Generation** - Punchy hooks + psychological/motivational content
2. **Voiceover** - ElevenLabs TTS (Adam voice, deep English)
3. **Stock Footage** - Downloads matching dark aesthetic clips from Pexels
4. **Captions** - Word-synced subtitles with keyword highlighting
5. **Color Grading** - Dark cinematic aesthetic applied to all footage
6. **Assembly** - Final video with background music + logo outro

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get API Keys (both free tiers available)
- **ElevenLabs**: https://elevenlabs.io/app/settings/api-keys
- **Pexels**: https://www.pexels.com/api/

### 3. Configure
Copy `.env.example` to `.env` and paste your API keys:
```
ELEVENLABS_API_KEY=your_key_here
PEXELS_API_KEY=your_key_here
```

### 4. Add Background Music (optional)
Drop a `.mp3` file into `assets/music/`

## Usage

```bash
# Generate video with random trending topic
python main.py

# Generate video with specific topic
python main.py "The psychology of silence and power"

# List all available topics
python main.py --list
```

## Project Structure

| File | Purpose |
|------|---------|
| `main.py` | Pipeline orchestrator |
| `config.py` | All settings (voice, colors, grading) |
| `script_generator.py` | Script generation with hooks |
| `voiceover.py` | ElevenLabs TTS with timestamps |
| `visuals.py` | Pexels stock footage downloader |
| `captions.py` | Word-synced caption renderer |
| `color_grading.py` | Dark aesthetic color grading |
| `video_assembler.py` | Final video assembly |

## Voice Settings
- **Voice**: Adam (Deep English Story Voice)
- **Speed**: 0.83
- **Stability**: 50%
- **Similarity Boost**: 75%
- **Style**: 4%
- **Speaker Boost**: Enabled

## Brand
- Channel: **Luminous Will**
- Aesthetic: Dark, cinematic, moody
- Content: Psychological facts, motivational speech
- Format: 1080x1920 (9:16 vertical)
