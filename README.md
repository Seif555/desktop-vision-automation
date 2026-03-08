# Vision-Based Desktop Automation — Notepad Launcher

## What it does
A Python program that visually locates a Notepad desktop icon on a 1920×1080
Windows desktop, double-clicks it, and saves the first 10 posts fetched from
the JSONPlaceholder demo API as `.txt` files.

## How it works

### Visual grounding
Icon detection uses **masked multi-scale template matching** (OpenCV):

1. A reference PNG of the target icon is placed next to `main.py`
2. A desktop screenshot is taken before each launch
3. The alpha channel is extracted as a mask — transparent pixels are excluded
   from scoring entirely, so the wallpaper colour never affects the result
4. The template is matched against the screenshot at 12 different scales
   (0.5× to 2.5×) to handle different icon view sizes
5. A folder-thumbnail false-positive filter rejects yellow Windows folder icons
6. The best match above the confidence threshold is accepted and clicked

This works for **any icon** — replace `notepad_icon.png` with any PNG to
target a different application.

### Automation workflow
For each of the 10 posts:
1. Minimise all windows to reveal the desktop
2. Screenshot → detect icon → double-click to launch Notepad
3. Paste post content (`Title: {title}\n\n{body}`) into Notepad
4. Save file directly to `Desktop/tjm-project/post_{id}.txt` via Python
5. Close Notepad → repeat

## Repo layout
```
desktop-vision-automation/
├── main.py              # entry point — fetch posts, automation loop
├── grounding.py         # OpenCV icon detection
├── utils.py             # Windows helpers (desktop path, Notepad control)
├── notepad_icon.png     # reference icon — replace to target a different app
├── requirements.txt     # pip dependencies
├── pyproject.toml       # uv configuration
├── uv.lock
├── .gitignore
├── README.md
└── screenshots/
    ├── top-left.png
    ├── center.png
    └── bottom-right.png
```

> **Note:** If you downloaded this as a ZIP from GitHub, rename the extracted
> folder from `desktop-vision-automation-main` to `desktop-vision-automation`
> before running. Or clone directly to avoid this:
> ```
> git clone <repo-url>
> ```

## Installation & run

### Using uv (recommended)
```powershell
git clone <repo-url>
cd desktop-vision-automation
uv sync
uv run python main.py
```

### Using pip
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Requirements
- Windows 10/11 at 1920×1080
- A Notepad shortcut on the Desktop before running
- Python 3.10+

## Output
Files are saved to `Desktop/tjm-project/post_1.txt` through `post_10.txt`.
Annotated detection screenshots are saved to `screenshots/latest_detection.png`
and overwritten on each run. Failed detection attempts are saved as
`screenshots/debug_failed_post{N}_attempt{N}.png`.

## Discussion notes

**Why template matching?**  
No API key, no internet, no model download — fully local and free. The alpha
mask makes it background-independent: transparent pixels are excluded from the
correlation score entirely so wallpaper colour has no effect.

**Known limitations**  
- Very busy wallpapers can produce false positives at the confidence threshold;
  the retry logic (3 attempts) mitigates this
- Small icon view (16px) is harder to match from a medium-size reference

**How to target a different icon**  
Replace `notepad_icon.png` with any PNG of the new target (transparent
background recommended). The file is auto-discovered by name.

**How to change resolution**  
Update `SCREEN_W, SCREEN_H` in `grounding.py`.
