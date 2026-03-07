"""
grounding.py — Local Vision-Based Desktop Icon Grounding using OpenCV
100% free, no API key, no internet required.

Approach: masked multi-scale template matching.
- Alpha mask excludes transparent background pixels from scoring entirely,
  so wallpaper colour never affects results (works on any background).
- Multiple template scales (0.5x to 2.5x) handle medium and large icon views.
- Works for ANY reference icon, not tailored to any specific colour or shape.
"""

from __future__ import annotations
import sys
from pathlib import Path
import cv2
import numpy as np
import mss

SCREEN_W, SCREEN_H = 1920, 1080
SCREENSHOT_DIR     = Path("screenshots")
_REF_EXTENSIONS    = (".png", ".ico", ".bmp", ".jpg", ".jpeg", ".webp")

MATCH_THRESHOLD    = 0.55

FOLDER_H_LOW, FOLDER_H_HIGH = 15, 45
FOLDER_MIN_S, FOLDER_MIN_V  = 80, 80
FOLDER_YELLOW_RATIO         = 0.18
FOLDER_BOTTOM_TOP_RATIO     = 1.6


# ── Reference discovery ───────────────────────────────────────────────────────

def find_reference_icon_path(script_dir: Path | None = None) -> Path:
    base  = script_dir or Path(sys.argv[0]).resolve().parent
    _skip = {"main", "grounding", "utils", "readme", "pyproject",
              "setup", "conftest", "test"}
    for ext in _REF_EXTENSIONS:
        p = base / f"target_icon{ext}"
        if p.exists():
            print(f"[Grounding] Reference icon (explicit): {p}"); return p
    candidates = [f for f in base.iterdir()
                  if f.suffix.lower() in _REF_EXTENSIONS
                  and f.stem.lower() not in _skip]
    if candidates:
        candidates.sort(key=lambda f: f.name.lower())
        print(f"[Grounding] Reference icon (auto-discovered): {candidates[0]}")
        return candidates[0]
    raise FileNotFoundError(f"No reference icon found in {base}")


# ── Image helpers ─────────────────────────────────────────────────────────────

def _load_reference(path: Path) -> tuple[np.ndarray, np.ndarray | None]:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Cannot read: {path}")
    if img.ndim == 3 and img.shape[2] == 4:
        alpha = img[:, :, 3]
        bgr   = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        mask  = np.where(alpha > 30, np.uint8(255), np.uint8(0))
        return bgr, mask
    return img, None


def _capture_screen() -> np.ndarray:
    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[1])
        return np.array(raw)[:, :, :3]


# ── Folder filter ─────────────────────────────────────────────────────────────

def _is_folder_thumbnail(screenshot: np.ndarray, cx: int, cy: int,
                          tw: int, th: int) -> bool:
    pad_w = int(tw * 0.8); pad_h = int(th * 0.8)
    x1 = max(0, cx - pad_w); y1 = max(0, cy - pad_h)
    x2 = min(screenshot.shape[1], cx + pad_w)
    y2 = min(screenshot.shape[0], cy + pad_h)
    region = screenshot[y1:y2, x1:x2]
    if region.size == 0:
        return False
    hsv  = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv,
                       np.array([FOLDER_H_LOW,  FOLDER_MIN_S, FOLDER_MIN_V]),
                       np.array([FOLDER_H_HIGH, 255,          255]))
    if float(np.count_nonzero(mask)) / mask.size < FOLDER_YELLOW_RATIO:
        return False
    h = region.shape[0]; half = max(1, h // 2)
    top = float(np.count_nonzero(mask[:half, :])) / max(1, mask[:half, :].size)
    bot = float(np.count_nonzero(mask[half:, :])) / max(1, mask[half:, :].size)
    return bot >= top * FOLDER_BOTTOM_TOP_RATIO


# ── Core detection ────────────────────────────────────────────────────────────

def _detect(screenshot: np.ndarray, template: np.ndarray,
            alpha_mask: np.ndarray | None = None) -> dict | None:
    """
    Masked multi-scale template matching.
    Alpha mask makes matching background-independent: transparent pixels
    in the reference are excluded from scoring entirely.
    """
    th, tw  = template.shape[:2]
    gt_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    gs      = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gs    = clahe.apply(gs)

    scales = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
              1.1, 1.25, 1.5, 1.75, 2.0, 2.5]

    best_score = -1.0; best_loc = None; best_scale = 1.0

    for scale in scales:
        rw = int(tw * scale); rh = int(th * scale)
        if rw < 4 or rh < 4 or rw >= gs.shape[1] or rh >= gs.shape[0]:
            continue
        tpl = cv2.resize(gt_gray, (rw, rh), interpolation=cv2.INTER_AREA)
        if alpha_mask is not None:
            msk = cv2.resize(alpha_mask, (rw, rh), interpolation=cv2.INTER_NEAREST)
            res = cv2.matchTemplate(gs, tpl, cv2.TM_CCORR_NORMED, mask=msk)
        else:
            res = cv2.matchTemplate(gs, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > best_score:
            best_score = max_val; best_loc = max_loc; best_scale = scale

    if best_score < MATCH_THRESHOLD or best_loc is None:
        print(f"  [Grounding] Best score {best_score:.3f} below threshold.")
        return None

    w = int(tw * best_scale); h = int(th * best_scale)
    x, y = best_loc
    poly = np.array([[[x,y]],[[x+w,y]],[[x+w,y+h]],[[x,y+h]]], dtype=np.float32)
    print(f"  [Grounding] score={best_score:.3f} scale={best_scale:.2f} -> ({x+w//2},{y+h//2})")
    return {"center": (x + w//2, y + h//2), "poly": poly, "score": best_score}


# ── Annotation ────────────────────────────────────────────────────────────────

def _annotate_and_save(screenshot: np.ndarray, poly: np.ndarray,
                        cx: int, cy: int, label: str, filename: str) -> None:
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    img = screenshot.copy()
    cv2.polylines(img, [np.int32(poly)], True, (0, 0, 255), 3)
    for pt in np.int32(poly):
        cv2.circle(img, tuple(pt[0]), 5, (0, 255, 255), -1)
    cv2.circle(img, (cx, cy), 6, (0, 0, 255), -1)
    cv2.rectangle(img, (cx - 2, cy - 24),
                  (cx + len(label) * 9, cy - 2), (0, 0, 255), -1)
    cv2.putText(img, label, (cx, cy - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(str(SCREENSHOT_DIR / filename), img)
    print(f"  [Screenshot] Saved -> {SCREENSHOT_DIR / filename}")


# ── Main class ────────────────────────────────────────────────────────────────

class DesktopIconGrounder:
    """
    Locates any desktop icon using masked multi-scale template matching.
    Place a PNG/ICO/BMP of the target icon next to main.py.
    Works on any wallpaper, any icon position.
    No API key or internet required.
    """

    def __init__(self, reference_path: Path | None = None) -> None:
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        ref_path                       = reference_path or find_reference_icon_path()
        self.template, self.alpha_mask = _load_reference(ref_path)
        self.ref_path                  = ref_path
        opaque = (100 * np.count_nonzero(self.alpha_mask) / self.alpha_mask.size
                  if self.alpha_mask is not None else 100)
        print(f"[Grounding] Loaded: {ref_path.name} "
              f"({self.template.shape[1]}x{self.template.shape[0]}px, "
              f"{opaque:.0f}% opaque)")

    def find_icon(self, attempt_number: int = 1,
                  post_index: int = 0) -> tuple[int, int] | None:

        screenshot = _capture_screen()
        result     = _detect(screenshot, self.template, self.alpha_mask)

        if result is None:
            SCREENSHOT_DIR.mkdir(exist_ok=True)
            cv2.imwrite(
                str(SCREENSHOT_DIR / f"debug_failed_post{post_index+1:02d}_attempt{attempt_number}.png"),
                screenshot)
            print(f"  [Grounding] No match — debug screenshot saved.")
            return None

        cx, cy = int(result["center"][0]), int(result["center"][1])

        if _is_folder_thumbnail(screenshot, cx, cy,
                                self.template.shape[1], self.template.shape[0]):
            print(f"  [Grounding] Rejected: folder thumbnail at ({cx},{cy}).")
            return None

        if not (0 <= cx <= SCREEN_W and 0 <= cy <= SCREEN_H):
            print(f"  [Grounding] Coords ({cx},{cy}) off-screen.")
            return None

        label = f"({cx},{cy}) s={result['score']:.2f}"
        _annotate_and_save(screenshot, result["poly"], cx, cy, label,
                           "latest_detection.png")
        print(f"  [Grounding] Match at ({cx},{cy}) score={result['score']:.3f}")
        return (cx, cy)
