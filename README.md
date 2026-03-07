# tjm-notepad-vision

Vision-based desktop icon grounding + Notepad automation (tested on Windows 10/11 at 1920×1080).

## What this does
- Detects a Notepad desktop icon from a screenshot using ORB / SIFT / template fallbacks
- Double-clicks the detected icon, pastes a post (from JSONPlaceholder) into Notepad, saves file `post_{id}.txt` into Desktop/tjm-project
- Writes authoritative files in the repo `tjm-project/` for grading

## Quickstart (Windows)
1. Clone the repo:
   `git clone https://github.com/<your-username>/tjm-notepad-vision.git`
2. From repo root:
