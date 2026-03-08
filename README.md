# Vision-Based Desktop Automation with Dynamic Icon Grounding

A Python automation tool that uses computer vision to locate a Notepad desktop
icon regardless of its position, launches it, and saves 10 blog posts fetched
from the JSONPlaceholder API as `.txt` files.

---

## How it meets the assignment requirements

| Requirement | How it is met |
|---|---|
| Capture desktop screenshot | `mss` captures a full 1920×1080 screenshot before each launch |
| Locate Notepad icon regardless of position | Masked multi-scale template matching scans the entire screen at 12 scales |
| Return centre coordinates for clicking | `find_icon()` returns `(x, y)` of the matched icon centre |
| Double-click to launch | `pyautogui.doubleClick()` at the returned coordinates |
| Fetch 10 posts from JSONPlaceholder | `requests` fetches `https://jsonplaceholder.typicode.com/posts` |
| Format: `Title: {title}\n\n{body}` | Applied in `main.py` before pasting |
| Save as `post_{id}.txt` in `Desktop/tjm-project/` | Written directly with Python `open()` — no Save As dialog needed |
| Close Notepad after each post | `WM_CLOSE` + "Don't Save" dismissal in `utils.py` |
| Repeat for all 10 posts | Loop in `main.py` re-grounds the icon fresh each iteration |
| Handle icon not found | 3 attempts with 1s delay; saves debug screenshot on each failure |
| Validate Notepad launched | `wait_for_notepad()` polls for window title match up to 8s |
| Graceful API fallback | 10 hardcoded fallback posts used if API is unreachable |
| Handle existing files | Python `open()` overwrites silently |
| Annotated screenshots | Saved to `screenshots/` with bounding box, corner markers, coordinates |

---

## Visual grounding approach

Detection uses **masked multi-scale template matching** (OpenCV, fully local,
no API key, no internet required):

1. Reference PNG placed next to `main.py` — any icon, any size
2. Alpha channel extracted as mask — transparent pixels excluded from scoring
   entirely so wallpaper colour never affects the result
3. Template matched at 12 scales (0.5× to 2.5×) against a CLAHE-enhanced
   greyscale screenshot using `TM_CCORR_NORMED` with the alpha mask
4. Folder-thumbnail false-positive filter rejects yellow Windows folder icons
5. Best match above confidence threshold is accepted and clicked

Works for **any icon** — replace `notepad_icon.png` with any PNG to target a
different application.

---

## Project structure

```
desktop-vision-automation/
├── main.py              # entry point — fetch posts, automation loop
├── grounding.py         # OpenCV icon detection engine
├── utils.py             # Windows helpers (desktop path, Notepad control)
├── notepad_icon.png     # reference icon — replace to target a different app
├── requirements.txt     # pip-installable dependencies
├── pyproject.toml       # uv project config
├── uv.lock              # uv lockfile
├── .gitignore
├── README.md
└── screenshots/
    ├── top-left.png     # annotated detection — icon in top-left
    ├── center.png       # annotated detection — icon in centre
    └── bottom-right.png # annotated detection — icon in bottom-right
```

> **If you downloaded as a ZIP from GitHub**, rename the extracted folder from
> `desktop-vision-automation-main` to `desktop-vision-automation` before
> running, or clone directly:
> ```
> git clone <repo-url>
> ```

---

## Prerequisites

- Windows 10 or 11 at 1920×1080 resolution
- Python 3.10+ from [python.org](https://www.python.org/downloads/)
  *(Microsoft Store Python does **not** work with pywin32)*
- A Notepad shortcut icon present on the Desktop before running

---

## Installation & run

### Option A — uv (recommended, fastest)
```powershell
git clone <repo-url>
cd desktop-vision-automation
uv sync
uv run python main.py
```

### Option B — pip + venv
```powershell
git clone <repo-url>
cd desktop-vision-automation
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Dependencies

Listed in both `requirements.txt` (pip) and `pyproject.toml` (uv):

| Package | Purpose |
|---|---|
| `opencv-python` | Template matching, image processing |
| `mss` | Fast desktop screenshot capture |
| `pyautogui` | Mouse control, keyboard input |
| `pyperclip` | Clipboard paste into Notepad |
| `pywin32` | Windows API — window focus, process detection |
| `requests` | Fetch posts from JSONPlaceholder API |
| `Pillow` | Image support (pyautogui dependency) |

---

## Output

- **Post files:** `Desktop/tjm-project/post_1.txt` through `post_10.txt`
- **Latest detection:** `screenshots/latest_detection.png` — overwritten each run, shows red bounding box, corner markers, coordinates and confidence score
- **Failed attempts:** `screenshots/debug_failed_post{N}_attempt{N}.png` — saved when detection fails so you can inspect what the camera saw

---

## Error handling

- **Icon not found:** retries up to 3 times with 1s delay between attempts
- **Notepad did not open:** 8s timeout with window title check; post is skipped
- **API unreachable:** falls back to 10 built-in posts (same content as JSONPlaceholder) so the automation completes fully offline
- **Save dialog:** handled by sending `WM_CLOSE` then pressing `N` (Don't Save); Alt+F4 fallback if dialog persists

---

## Discussion notes

**Why template matching over alternatives?**
Fully local, free, zero setup — no API key, no model download, no internet.
The alpha mask makes it genuinely background-independent.

**When would detection fail?**
- Icon removed from desktop (handled: 3 retries + skip)
- Extremely busy wallpaper with patterns similar to the icon shape
- Non-standard DPI scaling (mitigated by `SetProcessDpiAwareness`)

**How to target a different icon**
Replace `notepad_icon.png` with a PNG of the new target (transparent background
recommended). The file is auto-discovered — no code change needed.

**How to change screen resolution**
Update `SCREEN_W, SCREEN_H` in `grounding.py`.
