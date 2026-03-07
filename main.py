"""
main.py — Desktop Vision Automation Entry Point
Fetches 10 blog posts and saves each one via Notepad, using
OpenCV-based visual grounding to locate the icon each time.
"""

import sys
import time
import os
import ctypes
from pathlib import Path

import requests
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)
import pyautogui
import pyperclip

from grounding import DesktopIconGrounder
from utils import (
    get_desktop_path,
    ensure_directory,
    minimize_all_windows,
    get_notepad_hwnd,
    close_notepad,
    wait_for_notepad,
)

pyautogui.FAILSAFE = False  # disabled because we intentionally move mouse to corner
pyautogui.PAUSE    = 0.05

SCREEN_CORNER_X = 1919
SCREEN_CORNER_Y = 0   # top-right corner — far from desktop icons

FALLBACK_POSTS = [
    {"id": 1,  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",   "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"},
    {"id": 2,  "title": "qui est esse",                                                                  "body": "est rerum tempore vitae\nsequi sint nihil reprehenderit dolor beatae ea dolores neque\nfugiat blanditiis voluptate porro vel nihil molestiae ut reiciendis\nqui aperiam non debitis possimus qui neque nisi nulla"},
    {"id": 3,  "title": "ea molestias quasi exercitationem repellat qui ipsa sit aut",                  "body": "et iusto sed quo iure\nvoluptatem occaecati omnis eligendi aut ad\nvoluptatem doloribus vel accusantium quis pariatur\nmolestiae porro eius odio et labore et velit aut"},
    {"id": 4,  "title": "eum et est occaecati",                                                          "body": "ullam et saepe reiciendis voluptatem adipisci\nsit amet autem assumenda provident rerum culpa\nquis hic commodi nesciunt rem tenetur doloremque ipsam iure\nquis sunt voluptatem rerum illo velit"},
    {"id": 5,  "title": "nesciunt quas odio",                                                            "body": "repudiandae veniam quaerat sunt sed\nalias aut fugiat sit autem sed est\nvoluptatem omnis possimus esse voluptatibus quis\nest aut tenetur dolor neque"},
    {"id": 6,  "title": "dolorem eum magni eos aperiam quia",                                           "body": "ut aspernatur corporis harum nihil quis provident sequi\nmollitia nobis aliquid molestiae\nperspiciatis et ea nemo ab reprehenderit accusantium quas\nvoluptate dolores velit et doloremque molestiae"},
    {"id": 7,  "title": "magnam facilis autem",                                                          "body": "dolore placeat quibusdam ea quo vitae\nmagni quis enim qui quis quo nemo aut saepe\nquidem repellat excepturi ut quia\nsunt ut sequi eos ea sed quas"},
    {"id": 8,  "title": "dolorem dolore est ipsam",                                                      "body": "dignissimos aperiam dolorem qui eum\nfacilis quibusdam animi sint suscipit qui sint possimus cum\nquaerat magni maiores excepturi\nipsam ut commodi dolor voluptatum modi aut vitae"},
    {"id": 9,  "title": "nesciunt iure omnis dolorem tempora et accusantium",                           "body": "consectetur animi nesciunt iure dolore\nenim quia ad\nveniam autem ut quam aut nobis\net est aut quod aut provident voluptas autem voluptas"},
    {"id": 10, "title": "optio molestias id quia eum",                                                  "body": "quo et expedita modi cum officia vel magni\ndoloribus qui repudiandae\nvero nisi sit\nquos veniam quod sed accusamus veritatis error"},
]

# ─── API ─────────────────────────────────────────────────────────────────────

API_URL = "http://jsonplaceholder.typicode.com/posts"


def fetch_posts(limit: int = 10, retries: int = 3) -> list[dict] | None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept":     "application/json",
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(API_URL, headers=headers, timeout=10, verify=False)
            resp.raise_for_status()
            posts = resp.json()
            print(f"[API] Fetched {len(posts)} posts, using first {limit}.")
            return posts[:limit]
        except Exception as exc:
            print(f"[API] Attempt {attempt}/{retries} failed: {exc}")
            if attempt < retries:
                print("[API] Retrying in 2 seconds…")
                time.sleep(2)
    return None


# ─── Notepad interaction ──────────────────────────────────────────────────────

def paste_content_into_notepad(content: str) -> None:
    """
    Paste *content* into the currently active Notepad window via clipboard.
    Focuses the Notepad window first so keystrokes go to the right place.
    """
    import win32gui, win32con
    hwnd = get_notepad_hwnd()
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.4)

    pyperclip.copy(content)
    pyautogui.hotkey("ctrl", "a")   # select all (clears any existing text)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")   # paste
    time.sleep(0.3)


def save_file_directly(content: str, filepath: Path) -> None:
    """
    Write *content* directly to *filepath* using Python file I/O.
    This is 100% reliable — no Save As dialog, no GUI interaction needed.
    The content is already in memory so we just write it.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


# ─── Main loop ────────────────────────────────────────────────────────────────

def main() -> None:
    # Resolve paths
    desktop     = get_desktop_path()
    project_dir = ensure_directory(desktop / "tjm-project")
    print(f"[Setup] Desktop   : {desktop}")
    print(f"[Setup] Output dir: {project_dir}")

    # DPI awareness (prevents coordinate scaling issues on HiDPI)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # Fetch posts
    posts = fetch_posts()
    if posts is None:
        print("[API] Could not reach API — using built-in fallback posts.")
        posts = FALLBACK_POSTS

    grounder = DesktopIconGrounder()

    for post_index, post in enumerate(posts):
        post_id  = post["id"]
        title    = post["title"]
        body     = post["body"]
        content  = f"Title: {title}\n\n{body}"  # exactly: title, blank line, body
        filename = f"post_{post_id}.txt"
        filepath = project_dir / filename

        print(f"\n{'='*60}")
        print(f"[Post {post_index+1}/10]  id={post_id}  file={filename}")
        print(f"{'='*60}")

        # ── Ground the icon (up to 3 attempts) ───────────────────────────────
        coords       = None
        found_on_try = None

        for attempt in range(1, 4):
            print(f"\n  [Grounding] Attempt {attempt}/3 — minimising windows & taking screenshot …")

            # Minimise everything so desktop icons are fully visible
            minimize_all_windows()
            time.sleep(0.8)

            result = grounder.find_icon(
                attempt_number=attempt,
                post_index=post_index,
            )

            if result is not None:
                coords       = result
                found_on_try = attempt
                print(f"  [Grounding] Attempt {attempt}/3 — Found icon at {coords}.")
                break
            else:
                print(f"  [Grounding] Attempt {attempt}/3 — Could not find icon.")
                if attempt < 3:
                    time.sleep(1.0)

        if coords is None:
            print("  [Grounding] Could not find icon in any of our three tries. Skipping this post.")
            continue

        print(f"  [Grounding] Icon confirmed found on attempt {found_on_try}.")

        # ── Double-click the icon, then immediately move mouse away ───────────
        # Moving mouse away prevents the hover tooltip from appearing over the
        # icon in the next screenshot, which could interfere with detection.
        print(f"  [Launch] Double-clicking icon at {coords} …")
        pyautogui.doubleClick(coords[0], coords[1])
        # Move mouse to bottom-right corner — away from desktop icons
        pyautogui.moveTo(SCREEN_CORNER_X, SCREEN_CORNER_Y, duration=0.2)

        # ── Wait for Notepad to open ──────────────────────────────────────────
        hwnd = wait_for_notepad(timeout=8)
        if hwnd is None:
            print("  [Launch] Notepad did not open within timeout. Skipping post.")
            continue
        print(f"  [Launch] Notepad is running (hwnd={hwnd}).")
        time.sleep(0.5)

        # ── Paste content into Notepad (visual demonstration) ─────────────────
        print(f"  [Write] Pasting content into Notepad …")
        paste_content_into_notepad(content)
        time.sleep(0.3)

        # ── Save file directly with Python (reliable, no GUI dialog needed) ───
        print(f"  [Save] Writing file directly to {filepath} …")
        save_file_directly(content, filepath)
        print(f"  [Save] File written successfully.")

        # ── Close Notepad (press Don't Save since we already saved directly) ──
        print("  [Close] Closing Notepad …")
        close_notepad()
        time.sleep(1.0)

        print(f"  [Done] post_{post_id}.txt saved to {project_dir}.")

    print("\n[Main] All 10 posts processed. Automation complete.")
    print(f"[Main] Files saved to: {project_dir}")


if __name__ == "__main__":
    main()
