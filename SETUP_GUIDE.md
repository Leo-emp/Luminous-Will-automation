# Luminous Will - Complete Setup & Run Guide

This guide will walk you through **everything** you need to do to get the Luminous Will automated video pipeline running on your computer. Follow each step in order.

---

## STEP 1: Install Python (if you don't have it already)

1. Open your browser and go to: https://www.python.org/downloads/
2. Click the big yellow **"Download Python"** button
3. Run the installer
4. **IMPORTANT**: Check the box that says **"Add Python to PATH"** at the bottom of the installer
5. Click **"Install Now"**
6. To verify it worked, open **Command Prompt** (search "cmd" in Windows search bar) and type:
   ```
   python --version
   ```
   You should see something like `Python 3.12.x` or higher

---

## STEP 2: Download This Project

### Option A: Clone with Git (if you have Git installed)
1. Open **Command Prompt**
2. Navigate to where you want the project:
   ```
   cd C:\Users\YourUsername
   ```
3. Clone the repo:
   ```
   git clone https://github.com/Leo-emp/Luminous-Will-automation.git
   ```
4. Enter the project folder:
   ```
   cd Luminous-Will-automation
   ```

### Option B: Download as ZIP (if you don't have Git)
1. Go to https://github.com/Leo-emp/Luminous-Will-automation
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Extract the ZIP file to a folder on your computer (e.g., `C:\Users\YourUsername\Luminous-Will-automation`)
5. Open **Command Prompt** and navigate to that folder:
   ```
   cd C:\Users\YourUsername\Luminous-Will-automation
   ```

---

## STEP 3: Install Required Python Packages

1. Make sure you're in the project folder in Command Prompt
2. Run this command to install all dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Wait for everything to install (this may take a few minutes)
4. You should see "Successfully installed ..." at the end
5. If you get an error about `pip`, try:
   ```
   python -m pip install -r requirements.txt
   ```

---

## STEP 4: Get Your ElevenLabs API Key

1. Go to https://elevenlabs.io/ and log into your account
2. Click your **profile icon** in the bottom-left corner
3. Click **"Profile + API key"**
4. Or go directly to: https://elevenlabs.io/app/settings/api-keys
5. Click **"Create API Key"** (or copy your existing one)
6. **Copy the API key** — you'll need it in Step 6
7. **IMPORTANT**: Keep this key secret. Never share it publicly.

---

## STEP 5: Get Your Free Pexels API Key

1. Go to https://www.pexels.com/api/
2. Click **"Get Started"** (or "Your API Key" if you already have an account)
3. Create a free account if you don't have one
4. Fill in the form:
   - **Name**: Luminous Will
   - **Description**: Automated video production
   - **URL**: (leave blank or put any URL)
5. Click **"Generate API Key"**
6. **Copy the API key** — you'll need it in Step 6
7. This key is **100% free** — Pexels allows 200 requests per hour

---

## STEP 6: Set Up Your API Keys

1. In the project folder, find the file called **`.env.example`**
2. Make a **copy** of this file and rename the copy to **`.env`**
   - In Command Prompt, you can do this:
     ```
     copy .env.example .env
     ```
   - Or manually: right-click the file → Copy → Paste → Rename to `.env`
3. Open the **`.env`** file in any text editor (Notepad works fine)
4. Replace the placeholder text with your actual API keys:
   ```
   ELEVENLABS_API_KEY=sk_abc123your_actual_key_here
   PEXELS_API_KEY=abc123your_actual_pexels_key_here
   ```
5. **Save** the file and close it
6. **NEVER** upload this `.env` file to GitHub — it contains your secret keys (the `.gitignore` file already prevents this)

---

## STEP 7: Add Background Music (Optional but Recommended)

1. Download a free dramatic/motivational background track from one of these sites:
   - https://pixabay.com/music/search/dramatic/ (completely free, no sign-up needed)
   - https://www.chosic.com/free-music/motivational/ (free, royalty-free)
2. Download the `.mp3` file
3. Move/copy the `.mp3` file into the **`assets/music/`** folder inside the project
4. That's it — the pipeline will automatically find and use it
5. The background music volume is set to 10% so your voiceover stays crystal clear
6. You can change the volume in `config.py` by editing the `MUSIC_VOLUME` value

---

## STEP 8: Verify Your Logo is in Place

1. Check that `assets/logo.png` exists in the project folder
2. This is your **Luminous Will** lion logo on a black background
3. It will be shown at the **end of every video** as an outro (3 seconds)
4. If you want to change the logo, just replace `assets/logo.png` with your new logo image
5. The logo will be automatically centered on a black background

---

## STEP 9: Run the Pipeline!

### Generate a video with a random trending topic:
```
python main.py
```

### Generate a video with a specific topic:
```
python main.py "The psychology of silence and power"
```

### Generate a video with another topic:
```
python main.py "Why high-value people walk alone"
```

### Generate a video with a third topic:
```
python main.py "The art of not reacting"
```

### See all available topics:
```
python main.py --list
```

### See help:
```
python main.py --help
```

---

## STEP 10: Find Your Finished Video

1. After the pipeline finishes, your video will be saved in the **`output/`** folder
2. The file name will be based on the topic + timestamp, like:
   ```
   output/The_psychology_of_silence_and_power_20260428_143022.mp4
   ```
3. Open it with any video player to review
4. The video is ready to upload directly to Instagram Reels, TikTok, or YouTube Shorts

---

## What Happens When You Run the Pipeline

Here's exactly what the script does when you run it:

1. **[STEP 1/6] Validates Setup** — Checks that your API keys are set and the logo file exists
2. **[STEP 2/6] Generates Script** — Picks a script with a punchy hook, motivational body, and strong closing
3. **[STEP 3/6] Generates Voiceover** — Sends the script to ElevenLabs API, gets back audio + word-by-word timestamps
4. **[STEP 4/6] Downloads Stock Footage** — Searches Pexels for matching dark/cinematic clips for each script segment, downloads them
5. **[STEP 5/6] Builds Captions** — Creates word-synced subtitle overlays with gold keyword highlighting
6. **[STEP 6/6] Assembles Final Video** — Combines everything: color-graded clips + voiceover + captions + background music + logo outro → exports as .mp4

The whole process takes about **2-5 minutes** depending on your internet speed and computer.

---

## Customization

### Change Voice Settings
Edit `config.py` and modify the `VOICE_SETTINGS` section:
- `stability`: How consistent the voice sounds (0.0 to 1.0)
- `similarity_boost`: How closely it matches the original voice (0.0 to 1.0)
- `style`: How expressive the voice is (0.0 to 1.0)
- `VOICE_SPEED`: How fast the speech is (0.83 = slightly slower than normal)

### Change Caption Style
Edit `config.py` and modify the caption section:
- `CAPTION_FONT_SIZE`: Size of the subtitle text (default: 70)
- `CAPTION_COLOR`: Color of normal words (default: "white")
- `CAPTION_HIGHLIGHT_COLOR`: Color of emphasis words (default: "#FFB800" gold)
- `CAPTION_STROKE_WIDTH`: Thickness of the black outline (default: 3)

### Change Color Grading
Edit `config.py` and modify the color grading section:
- `BRIGHTNESS_FACTOR`: Lower = darker (default: 0.65)
- `SATURATION_FACTOR`: Lower = more desaturated/moody (default: 0.55)
- `CONTRAST_FACTOR`: Higher = more contrast (default: 1.15)

### Change Background Music Volume
Edit `config.py`:
- `MUSIC_VOLUME`: 0.10 = 10% volume (default). Increase to 0.15 or 0.20 if you want louder music.

---

## Troubleshooting

### "ELEVENLABS_API_KEY not set in .env file"
- Make sure you created the `.env` file (not `.env.example`)
- Make sure the key is pasted correctly with no extra spaces
- Make sure the file is named exactly `.env` (not `.env.txt`)

### "Pexels API error: 401"
- Your Pexels API key is invalid or expired
- Go to https://www.pexels.com/api/ and generate a new one

### "No results for: [query]"
- Some specific search terms might not have portrait videos on Pexels
- The pipeline has automatic fallbacks — it will try simpler keywords
- If all fallbacks fail, it uses generic "dark cinematic" footage

### "ModuleNotFoundError: No module named 'moviepy'"
- You didn't install the requirements. Run:
  ```
  pip install -r requirements.txt
  ```

### Video is too dark / too bright
- Adjust `BRIGHTNESS_FACTOR` in `config.py`
- Higher value = brighter (try 0.75), lower value = darker (try 0.55)

### Captions are too small / too big
- Adjust `CAPTION_FONT_SIZE` in `config.py`
- Default is 70. Try 60 for smaller or 80 for bigger.

### ElevenLabs "quota exceeded" error
- Free tier has a monthly character limit
- Wait for your quota to reset, or upgrade your ElevenLabs plan

---

## File Structure

```
Luminous-Will-automation/
├── main.py                  # Run this to create videos
├── config.py                # All settings in one place
├── script_generator.py      # Script templates + hooks
├── voiceover.py             # ElevenLabs text-to-speech
├── visuals.py               # Pexels stock footage downloader
├── captions.py              # Word-synced caption renderer
├── color_grading.py         # Dark aesthetic color filter
├── video_assembler.py       # Puts everything together
├── requirements.txt         # Python package list
├── .env.example             # Template for API keys
├── .env                     # Your actual API keys (DO NOT share)
├── .gitignore               # Keeps secrets out of GitHub
├── README.md                # Project overview
├── SETUP_GUIDE.md           # This file
├── assets/
│   ├── logo.png             # Luminous Will logo
│   └── music/               # Drop background music .mp3 here
├── output/                  # Finished videos saved here
└── temp/                    # Temporary files (auto-created)
```
