# Vision-Based Desktop Automation — Notepad Launcher

**Project goal**  
A robust Python program that visually finds a Notepad desktop icon on Windows at 1920×1080, double-clicks it, and types/saves the first 10 posts from the JSONPlaceholder API (or fallback posts if offline).

---

## Highlights (what changed)
- **Color-aware matching:** template matching is performed separately on each B, G, R channel and the per-channel scores are averaged. This reduces false positives caused by grayscale similarity to wallpaper patterns.
- **Blue-region rejection:** a lightweight HSV-based heuristic rejects candidates that are overwhelmingly blue (fixes the highlighted-blue wallpaper failure mode).
- **Annotated screenshots:** the program saves an annotated `latest_detection.png` to `./screenshots/` every attempt. For debugging, the code currently saves top candidates even when they are rejected (so you can inspect failure cases).
- **Tuning:** default `MATCH_THRESHOLD = 0.66` (lower to ~0.62 if you get false negatives, raise if you get false positives).

---

## Requirements / Target environment
- OS: Windows 10 / 11 at 1920×1080  
- Python: 3.11+ (recommended)  
- Tools: `uv` (optional, used for running in this project)  
- Key Python deps: `opencv-python`, `numpy`, `pyautogui`, `mss` (or pyautogui screenshot), `pyperclip`, `pywin32`, `requests`

---

## Project layout (what to include in the repo)
