Vision-Based Desktop Automation — Notepad Launcher

Project goal
A lightweight Python program that visually finds a Notepad desktop icon on a 1920×1080 desktop, double-clicks it, and types/saves the first 10 posts fetched from the demo API.

Quick summary

Visual grounding via masked, multi-scale template matching (OpenCV).

Color-aware matching and simple heuristics (blue-region rejection and folder-thumbnail rejection) to reduce wallpaper false positives.

Annotated screenshots saved to ./screenshots/ inside the repo for inspection.

Runtime writes output files to a Desktop folder named tjm-project (this folder should exist on the user’s Desktop at runtime and is outside the repo).

Quick links

Demo posts API used: JSONPlaceholder

Repository hosting: GitHub

Repo layout (what this repo contains)
desktop-vision-automation/        <-- repo root
├─ main.py                       # entrypoint (automation loop).
├─ grounding.py                  # detection engine (OpenCV).
├─ utils.py                      # Windows helpers (desktop path, Notepad control).
├─ notepad_icon.png              # reference icon (PNG) used for matching reeplace with your own  │                                # if needed with the same name.
├─ requirements.txt              # pip-installable deps (recommended).
├─ README.md                     # this file.
├─ screenshots/
│  ├─ top-left.png
│  ├─ center.png
│  └─ bottom-right.png
└─ .gitignore

Note: The runtime output folder tjm-project is expected to be created on the Desktop (outside the repo) before running the script and it has 10 test posts already and you can delete them if you want. The repo contains the code and the required annotated screenshots.

Installation & run (generic instructions)

Create a Python virtual environment and activate it:

python -m venv .venv
.venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

(If you prefer uv or poetry, install via your chosen tool using the included lockfile.)

Ensure a folder named tjm-project exists on the Desktop (this is where the script will save files at runtime). Example: create a folder named tjm-project on the Desktop.

Run the program:

python main.py

Dependencies

numpy==2.4.2
opencv-python==4.13.0.92
mss==10.1.0
pyautogui
pyperclip
pywin32
requests

(Adjust versions if you prefer; these reflect the packages used by the code.)

Why an annotated image may show a bounding box but the run printed “rejected”

The detector saves the best candidate for each attempt (so you can inspect what it considered). After generating that candidate it applies final checks (threshold, blue-region rejection, folder-thumbnail rejection). If those heuristics reject the candidate, the run prints Rejected but the candidate image is kept for debugging. If you prefer only accepted detections to be saved, change that behavior in grounding.py (easy one-line edit).

.gitignore (recommended contents — put at repo root)
# Virtualenv
.venv/
venv/

# Python cache
__pycache__/
*.pyc

# OS and editor
.DS_Store
Thumbs.db
.vscode/
.idea/

# Keep screenshots but ignore temporary ones
screenshots/tmp_*
screenshots/*.log

Notes for users

The program expects a Notepad shortcut to be present on the Desktop before running.

The code is written to work with 1920×1080 desktop resolution (adjustable in code if required).

The code is written to work with windows 10/11.

The detection is template based — replace notepad_icon.png with another PNG (transparent background recommended) to target a different icon.
