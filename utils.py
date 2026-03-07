"""
utils.py — Windows helper utilities
─────────────────────────────────────
• get_desktop_path()   — resolves the actual desktop path (OneDrive-aware)
• ensure_directory()   — creates a directory if it doesn't exist
• minimize_all_windows() — Win+D to show the desktop
• get_notepad_hwnd()   — find a running Notepad window handle
• wait_for_notepad()   — poll until Notepad appears or timeout
• close_notepad()      — gracefully close Notepad (handles Save prompts)
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pyautogui
import win32api
import win32con
import win32gui


# ─────────────────────────────────────────────────────────────────────────────
# Desktop path — OneDrive-aware, no hard-coded usernames
# ─────────────────────────────────────────────────────────────────────────────

def get_desktop_path() -> Path:
    """
    Return the real desktop path for the current user.

    Strategy (in priority order):
    1. Read HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\
       Shell Folders → Desktop  (always correct, even with OneDrive-redirected
       desktops, because Windows writes the *current* path here at login).
    2. Fall back to %USERPROFILE%\\Desktop.
    3. Fall back to os.path.expanduser("~/Desktop").

    This works regardless of whether OneDrive is active or not, and regardless
    of the machine name / user name.
    """
    # Method 1: registry (most reliable)
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
        )
        value, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        p = Path(value)
        if p.exists():
            return p
    except Exception:
        pass

    # Method 2: environment variable
    try:
        p = Path(os.environ["USERPROFILE"]) / "Desktop"
        if p.exists():
            return p
    except KeyError:
        pass

    # Method 3: Python expanduser
    return Path("~/Desktop").expanduser()


# ─────────────────────────────────────────────────────────────────────────────
# Directory helper
# ─────────────────────────────────────────────────────────────────────────────

def ensure_directory(path: Path) -> Path:
    """Create *path* (and all parents) if it does not exist; return *path*."""
    path.mkdir(parents=True, exist_ok=True)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Window management
# ─────────────────────────────────────────────────────────────────────────────

def minimize_all_windows() -> None:
    """
    Press Win+D to show the desktop (minimises all open windows).
    This clears any pop-ups, dialogs, or foreground windows that could
    obstruct the desktop icons during screenshot capture.
    """
    pyautogui.hotkey("win", "d")
    time.sleep(0.9)   # Give the animation time to finish


def _enum_notepad_windows(hwnd: int, result: list) -> None:
    """win32gui.EnumWindows callback — collects visible Notepad hwnds."""
    if not win32gui.IsWindowVisible(hwnd):
        return
    title = win32gui.GetWindowText(hwnd)
    # Match "Untitled - Notepad", "Notepad", "post_1.txt - Notepad", etc.
    # Exclude "Notepad++" (different app).
    if "Notepad" in title and "++" not in title:
        result.append(hwnd)


def get_notepad_hwnd() -> int | None:
    """Return the HWND of the first visible Notepad window, or None."""
    windows: list[int] = []
    win32gui.EnumWindows(_enum_notepad_windows, windows)
    return windows[0] if windows else None


def wait_for_notepad(timeout: float = 8.0, poll: float = 0.4) -> int | None:
    """
    Poll every *poll* seconds until a Notepad window appears or *timeout*
    seconds elapse.  Returns the hwnd or None.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd = get_notepad_hwnd()
        if hwnd:
            return hwnd
        time.sleep(poll)
    return None


def close_notepad() -> None:
    """
    Close Notepad.  Handles the "Do you want to save?" dialog that appears
    in Windows 10 Notepad (Win11 Notepad with autosave usually doesn't show it,
    but we handle both cases).

    Strategy: send WM_CLOSE; if a Save dialog appears, dismiss with "Don't Save".
    """
    hwnd = get_notepad_hwnd()
    if hwnd is None:
        return   # Already closed

    # Send close message
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    time.sleep(0.6)

    # Check whether a Save/Discard dialog appeared
    # The dialog's title varies by version: "Notepad", "Save", etc.
    # We look for a small dialog that appeared after the WM_CLOSE.
    # Easiest cross-version approach: press Tab until "Don't save" / "No" is
    # focused, then press Enter.  But pressing "N" (shortcut) is more reliable.
    for _ in range(6):
        hwnd2 = get_notepad_hwnd()
        if hwnd2 is None:
            break   # Notepad closed cleanly
        # A dialog is open — try common "Don't save" shortcuts
        pyautogui.press("n")    # Win10: "No"  /  Win11: "Don't save" (first letter)
        time.sleep(0.4)

    # Final fallback — Alt+F4 if window still alive
    hwnd3 = get_notepad_hwnd()
    if hwnd3:
        win32gui.SetForegroundWindow(hwnd3)
        time.sleep(0.2)
        pyautogui.hotkey("alt", "f4")
        time.sleep(0.5)
        pyautogui.press("n")
        time.sleep(0.3)
