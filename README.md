# Vision-Based Desktop Automation with Dynamic Icon Grounding

A Python automation tool that uses computer vision to locate any desktop icon by visual matching, then automates Notepad to save blog posts fetched from an API.

## How It Works

### Icon Grounding
The system uses **masked multi-scale template matching** via OpenCV:

1. A reference image of the target icon (PNG/ICO/BMP) is placed next to `main.py`
2. On each run, a desktop screenshot is captured
3. The alpha channel of the reference image is extracted as a mask — transparent pixels are excluded from scoring entirely, so the wallpaper colour never affects detection
4. The reference is matched against the screenshot at 12 different scales (0.5× to 2.5×) to handle different icon view sizes
5. The best-scoring match above the confidence threshold is accepted
6. A folder-thumbnail false-positive filter rejects yellow Windows folder icons that may contain a thumbnail of the target icon

This approach works for **any icon**, not just Notepad — drop any PNG reference image next to `main.py` and it will find that icon instead.

### Automation Workflow
For each of the 10 posts:
1. Minimise all windows to reveal the desktop
2. Capture screenshot → ground the icon → double-click to launch Notepad
3. Paste post content (`Title: {title}\n\n{body}`) into Notepad
4. Save file directly to `Desktop/tjm-project/post_{id}.txt`
5. Close Notepad → repeat

## Setup

### Prerequisites
- Windows 10/11 at 1920×1080
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- A Notepad shortcut on the desktop
- Python 3.11+ from [python.org](https://www.python.org/downloads/) (not Microsoft Store)

### Install & Run

```powershell
git clone <your-repo-url>
cd desktop-vision-automation
uv sync
uv run python main.py
```

### Reference Icon Setup
Place a PNG screenshot of the target icon (with transparent background) next to `main.py`. The file is auto-discovered — any image file in the project folder works. The included `notepad_icon.png` is used by default.

## Project Structure

```
desktop-vision-automation/
├── main.py              # Entry point — fetch posts, run automation loop
├── grounding.py         # OpenCV icon detection (works for any icon)
├── utils.py             # Windows helpers (desktop path, Notepad management)
├── pyproject.toml       # uv dependency config
├── notepad_icon.png     # Reference icon image (replace to target a different app)
└── screenshots/         # Annotated detection screenshots saved here
```

## Dependencies
- `opencv-python` — image processing and template matching
- `mss` — fast screenshot capture
- `pyautogui` — mouse/keyboard control
- `pyperclip` — clipboard paste for Unicode content
- `pywin32` — Windows API (window focus, process detection)
- `requests` — fetch posts from JSONPlaceholder API

## Error Handling
- **Icon not found**: retries up to 3 times with 1s delay; saves a debug screenshot each failed attempt to `screenshots/`
- **Notepad did not launch**: timeout detection with window title check; skips post after 8s
- **API unreachable**: falls back to 10 built-in posts so automation continues offline
- **File already exists**: directly overwritten (no Save As dialog interaction needed)
- **Folder thumbnail false positive**: rejected by HSV yellow-ratio check

## Annotated Screenshots
The `screenshots/` folder contains `latest_detection.png` — updated after each successful detection showing:
- Red bounding box around the detected icon
- Yellow corner markers
- Centre dot with coordinates and confidence score

## Discussion Notes

**Why template matching over alternatives?**
- No API key, no internet, no model download — runs fully locally and free
- The alpha mask makes it background-independent: transparent pixels are excluded from the correlation score entirely
- Multi-scale matching handles different icon view sizes without retraining anything

**Known limitations**
- Small icon view (16px) is harder to match reliably from a medium reference — a reference taken at the same icon size would improve this
- A very busy wallpaper with patterns similar to the icon shape can produce false positives — the confidence threshold and folder filter mitigate this

**How to extend to any resolution**
Change `SCREEN_W, SCREEN_H` in `grounding.py` — no other changes needed

**How to target a different icon**
Replace `notepad_icon.png` with any PNG of the new target icon (transparent background recommended)
