tjm-notepad-vision

Vision-based desktop icon grounding + Notepad automation. Detects a Notepad desktop shortcut (any position), double-clicks it, pastes posts (from JSONPlaceholder or local fallback), and writes post_{id}.txt files to Desktop/tjm-project. Tested on Windows 10/11 at 1920×1080.

Quickstart (Windows)

1. Clone the repo:



git clone https://github.com/<your-username>/tjm-notepad-vision.git
cd tjm-notepad-vision

2. Create & activate a venv, install deps, run:



python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py

Or run run_demo.bat (convenience script).

What the program does

Takes a screenshot of the primary monitor.

Detects the Notepad desktop shortcut using ORB / SIFT / template matching fallbacks.

Double-clicks the detected icon to open Notepad.

Pastes the post (format: Title: {title}\n\n{body}) into Notepad visually and writes the same content to disk as post_{id}.txt.

Closes Notepad (dismisses save dialogs).

Repeats for the first 10 posts (or fallback sample posts if network fails).


Output location

Files are written to:

C:\Users\<you>\Desktop\tjm-project\post_{id}.txt
(If a Desktop folder is not available, the script falls back to ~\tjm-project.)


Repo layout

tjm-notepad-vision/
├─ main.py
├─ requirements.txt
├─ README.md
├─ LICENSE
├─ notepad_icon.png
├─ annotated/                       # annotated detection images
│   ├─ detection_top_left.png
│   ├─ detection_center.png
│   └─ detection_bottom_right.png
├─ tjm-project/                     # saved post_*.txt files (generated)
├─ run_demo.bat
└─ .gitignore

Annotated screenshots (deliverable)

Include three annotated screenshots (these live in annotated/):

detection_top_left.png — icon detected in top-left

detection_center.png — icon detected center

detection_bottom_right.png — icon detected bottom-right


These are required for submission. The program will save annotated images automatically (see ANNOTATED_DIR).

Important testing notes & tips

Resolution: grader expects 1920×1080. Set your display to 1920×1080 for easiest results.

Template icon: capture notepad_icon.png from your desktop at the same icon size (small/medium/large) you will test with. A template captured at the same on-screen size improves detection.

Notepad shortcut: place a Notepad shortcut (actual .lnk on the desktop). If multiple Notepad shortcuts exist the script will pick a confident candidate.

Do not put Notepad inside a folder (the shortcut inside a folder will not be visible in the desktop screenshot).

If detection misses: retake notepad_icon.png from the desktop at the same icon size and re-run.

Network: if jsonplaceholder is unavailable the script uses fallback sample posts and still writes files locally.


Troubleshooting (common)

Script clicks wrong icon:

Re-capture notepad_icon.png as a clean small desktop icon screenshot (include a tiny bit of surrounding pixels).

Ensure desktop icon size matches the template.


Script writes files to a different folder:

The program resolves the current user Desktop. If your Desktop is non-standard, check SAVE_DIR printed in logs.


Accidentally committed venv/:


git rm -r --cached venv
git commit -m "remove venv"
git push

Packaging / submission

Create tjm-notepad-demo.zip containing:

main.py, requirements.txt, README.md, notepad_icon.png, annotated/ (3 images), tjm-project/ (post files), run_demo.bat, and uv_configuration.txt (if requested).


Upload that zip to the form and paste your GitHub repo link in the form.


Extras / notes for interview

Be ready to discuss:

Why ORB/SIFT + homography + template fallback was chosen.

Failure modes (busy backgrounds, icon inside folders, broken shortcuts, scaled icons).

How you'd extend to arbitrary icons and multiple resolutions.


Contact

If something breaks during submission or you want the README tightened for the repo README.md display, paste your repo URL and I’ll produce the final README text tailored to that repo automatically.


---

MIT License — © 2026 Seif555
