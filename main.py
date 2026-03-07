# main.py
import os
import time
import ctypes
import cv2
import numpy as np
import mss
import pyautogui
import requests
import psutil
import pyperclip
from pathlib import Path
from ctypes import wintypes

try:
    import pygetwindow as gw
except Exception:
    gw = None

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
EnumWindows = user32.EnumWindows
IsWindowVisible = user32.IsWindowVisible
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetClassNameW = user32.GetClassNameW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowRect = user32.GetWindowRect
ShowWindow = user32.ShowWindow
SW_MINIMIZE = 6

THIS_DIR = Path(__file__).parent
TEMPLATE_PATH = THIS_DIR / "notepad_icon.png"
MONITOR_INDEX = 1
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1.0
ORB_FEATURES = 1000
MIN_GOOD_MATCHES = 8
MIN_INLIERS = 5
TEMPLATE_SCORE_THRESHOLD = 0.70
ANNOTATED_DIR = THIS_DIR / "annotated"
JSON_API = "https://jsonplaceholder.typicode.com/posts"
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.06

FOLDER_YELLOW_H_LOW = 15
FOLDER_YELLOW_H_HIGH = 45
FOLDER_MIN_S = 80
FOLDER_MIN_V = 80
FOLDER_YELLOW_RATIO_THRESHOLD = 0.18
FOLDER_BOTTOM_VS_TOP_RATIO = 1.6

MISSING_SHEET_BRIGHTNESS = 240.0
MISSING_SHEET_VARIANCE = 200.0
LINE_SIMILARITY_THRESHOLD = 0.12
CORRELATION_THRESHOLD = 0.66
HIGH_CORRELATION_OVERRIDE = 0.88

def log(*a, **k):
    print(time.strftime("[%H:%M:%S]"), *a, **k)

def resolve_save_dir_desktop_tjm():
    try:
        if os.name == 'nt':
            from ctypes import create_unicode_buffer
            CSIDL_DESKTOPDIRECTORY = 0x10
            buf = create_unicode_buffer(260)
            res = ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buf)
            if res == 0:
                candidate = Path(buf.value)
                if candidate.exists():
                    return candidate / "tjm-project"
    except Exception:
        pass
    candidate = Path.home() / "Desktop"
    if candidate.exists():
        return candidate / "tjm-project"
    return Path.home() / "tjm-project"

SAVE_DIR = resolve_save_dir_desktop_tjm()

def grab_screenshot():
    with mss.mss() as sct:
        monitor = sct.monitors[MONITOR_INDEX]
        sct_img = sct.grab(monitor)
        img = np.array(sct_img)[:, :, :3]
        return img

def load_template(path):
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Template not found: {path}")
    if img.shape[-1] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img

def enhance_contrast_gray(bgr_img):
    gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    return clahe.apply(gray)

def detect_with_orb(screenshot, template):
    gray_s = enhance_contrast_gray(screenshot)
    gray_t = enhance_contrast_gray(template)
    orb = cv2.ORB_create(nfeatures=ORB_FEATURES)
    kp1, des1 = orb.detectAndCompute(gray_t, None)
    kp2, des2 = orb.detectAndCompute(gray_s, None)
    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        return None
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)
    good = []
    for m_n in matches:
        if len(m_n) < 2:
            continue
        m, n = m_n
        if m.distance < 0.75 * n.distance:
            good.append(m)
    if len(good) < MIN_GOOD_MATCHES:
        return None
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1,1,2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1,1,2)
    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if H is None:
        return None
    h, w = template.shape[:2]
    corners = np.float32([[0,0],[w,0],[w,h],[0,h]]).reshape(-1,1,2)
    transformed = cv2.perspectiveTransform(corners, H)
    cx = int(np.mean(transformed[:,0,0])); cy = int(np.mean(transformed[:,0,1]))
    inliers = int(mask.sum()) if mask is not None else 0
    return {"center": (cx, cy), "poly": transformed, "inliers": inliers, "good_matches": len(good)}

def detect_with_sift(screenshot, template):
    try:
        sift = cv2.SIFT_create()
    except Exception:
        return None
    gray_s = enhance_contrast_gray(screenshot)
    gray_t = enhance_contrast_gray(template)
    kp1, des1 = sift.detectAndCompute(gray_t, None)
    kp2, des2 = sift.detectAndCompute(gray_s, None)
    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        return None
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des1, des2, k=2)
    good = []
    for m_n in matches:
        if len(m_n) < 2:
            continue
        m, n = m_n
        if m.distance < 0.7 * n.distance:
            good.append(m)
    if len(good) < MIN_GOOD_MATCHES:
        return None
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1,1,2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1,1,2)
    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if H is None:
        return None
    h, w = template.shape[:2]
    corners = np.float32([[0,0],[w,0],[w,h],[0,h]]).reshape(-1,1,2)
    transformed = cv2.perspectiveTransform(corners, H)
    cx = int(np.mean(transformed[:,0,0])); cy = int(np.mean(transformed[:,0,1]))
    inliers = int(mask.sum()) if mask is not None else 0
    return {"center": (cx, cy), "poly": transformed, "inliers": inliers, "good_matches": len(good)}

def fallback_template_match(screenshot, template, min_score=TEMPLATE_SCORE_THRESHOLD):
    gray_s = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    gray_t = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    th, tw = gray_t.shape[:2]
    best_score = -1
    best_loc = None
    best_scale = 1.0
    for scale in [1.0, 1.25, 0.8, 1.5, 0.6, 2.0, 0.5]:
        rw = int(tw * scale); rh = int(th * scale)
        if rw < 6 or rh < 6 or rw >= gray_s.shape[1] or rh >= gray_s.shape[0]:
            continue
        resized = cv2.resize(gray_t, (rw, rh), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(gray_s, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > best_score:
            best_score = max_val
            best_loc = max_loc
            best_scale = scale
    if best_score < min_score:
        return None
    w = int(tw * best_scale); h = int(th * best_scale)
    x, y = best_loc
    cx = int(x + w/2); cy = int(y + h/2)
    poly = np.array([[[x,y]], [[x+w,y]], [[x+w,y+h]], [[x,y+h]]], dtype=np.float32)
    return {"center": (cx, cy), "poly": poly, "score": best_score, "scale": best_scale}

def annotate_and_save(screenshot_bgr, poly, fname):
    ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
    img = screenshot_bgr.copy()
    pts = np.int32(poly)
    cv2.polylines(img, [pts], True, (0,255,0), 2)
    cv2.imwrite(str(ANNOTATED_DIR / fname), img)

def extract_horizontal_mask(bgr_img, width_target=None):
    gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3,3), 0)
    edges = cv2.Canny(blur, 40, 120)
    kernel_len = max(3, int(max(edges.shape[1], edges.shape[0]) * 0.12))
    hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, hor_kernel)
    _, mask = cv2.threshold(closed, 10, 255, cv2.THRESH_BINARY)
    if width_target is not None and mask.shape[1] != width_target and mask.shape[1] > 0:
        new_h = int(mask.shape[0] * (width_target / mask.shape[1]))
        if new_h <= 0:
            new_h = mask.shape[0]
        mask = cv2.resize(mask, (width_target, new_h), interpolation=cv2.INTER_NEAREST)
    return mask

def horizontal_line_similarity(patch_bgr, template_mask):
    if patch_bgr is None or patch_bgr.size == 0:
        return 0.0
    pat_mask = extract_horizontal_mask(patch_bgr, width_target=template_mask.shape[1])
    h_t, w_t = template_mask.shape
    h_p, w_p = pat_mask.shape
    if h_p > h_t:
        start = (h_p - h_t)//2
        pat_mask_crop = pat_mask[start:start+h_t, :]
    elif h_p < h_t:
        pad_top = (h_t - h_p)//2
        pad_bottom = h_t - h_p - pad_top
        pat_mask_crop = cv2.copyMakeBorder(pat_mask, pad_top, pad_bottom, 0, 0, cv2.BORDER_CONSTANT, value=0)
    else:
        pat_mask_crop = pat_mask
    A = (template_mask > 0).astype(np.uint8)
    B = (pat_mask_crop > 0).astype(np.uint8)
    inter = np.count_nonzero(A & B)
    union = np.count_nonzero(A | B)
    if union == 0:
        return 0.0
    return float(inter) / float(union)

def is_probably_missing_sheet(patch_bgr):
    if patch_bgr is None or patch_bgr.size == 0:
        return False
    gray = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2GRAY)
    mean = float(np.mean(gray))
    var = float(np.var(gray))
    return (mean >= MISSING_SHEET_BRIGHTNESS and var <= MISSING_SHEET_VARIANCE)

def patch_template_correlation(patch_bgr, template_bgr):
    try:
        g_patch = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2GRAY)
        g_tpl = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
        g_tpl_rs = cv2.resize(g_tpl, (g_patch.shape[1], g_patch.shape[0]), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(g_patch, g_tpl_rs, cv2.TM_CCOEFF_NORMED)
        _, maxval, _, _ = cv2.minMaxLoc(res)
        return float(maxval)
    except Exception:
        return -1.0

def is_area_folder_like(screenshot_bgr, center, template_w, template_h):
    cx, cy = int(center[0]), int(center[1])
    pad_w = int(template_w * 0.8)
    pad_h = int(template_h * 0.8)
    x1 = max(0, cx - pad_w); y1 = max(0, cy - pad_h)
    x2 = min(screenshot_bgr.shape[1], cx + pad_w)
    y2 = min(screenshot_bgr.shape[0], cy + pad_h)
    region = screenshot_bgr[y1:y2, x1:x2]
    if region.size == 0:
        return False
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    lower = np.array([FOLDER_YELLOW_H_LOW, FOLDER_MIN_S, FOLDER_MIN_V])
    upper = np.array([FOLDER_YELLOW_H_HIGH, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    total = mask.size
    yellow_ratio = float(np.count_nonzero(mask)) / total
    h = region.shape[0]
    half = max(1, h // 2)
    top_mask = mask[0:half, :]
    bottom_mask = mask[half:h, :]
    top_ratio = float(np.count_nonzero(top_mask)) / top_mask.size
    bottom_ratio = float(np.count_nonzero(bottom_mask)) / bottom_mask.size
    if yellow_ratio >= FOLDER_YELLOW_RATIO_THRESHOLD and bottom_ratio >= top_ratio * FOLDER_BOTTOM_VS_TOP_RATIO:
        try:
            tpl = load_template(TEMPLATE_PATH)
            tpl_resized = cv2.resize(region, (tpl.shape[1], tpl.shape[0]), interpolation=cv2.INTER_AREA)
            g_patch = cv2.cvtColor(tpl_resized, cv2.COLOR_BGR2GRAY)
            g_tpl = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
            _, g_patch = cv2.threshold(g_patch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            _, g_tpl = cv2.threshold(g_tpl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            res = cv2.matchTemplate(g_patch, g_tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            return (max_val < TEMPLATE_SCORE_THRESHOLD)
        except Exception:
            return True
    return False

def is_confident_notepad(candidate, template, screenshot):
    if candidate is None:
        return False
    try:
        cx, cy = candidate['center']
        tw, th = template.shape[1], template.shape[0]
        x1 = max(0, int(cx - tw//2)); y1 = max(0, int(cy - th//2))
        x2 = min(screenshot.shape[1], x1 + tw); y2 = min(screenshot.shape[0], y1 + th)
        patch = screenshot[y1:y2, x1:x2]
        if patch.size == 0:
            return False
    except Exception:
        return False
    if is_probably_missing_sheet(patch):
        return False
    feature_ok = False
    if 'good_matches' in candidate and 'inliers' in candidate:
        if candidate['good_matches'] >= MIN_GOOD_MATCHES and candidate['inliers'] >= MIN_INLIERS:
            feature_ok = True
    corr = patch_template_correlation(patch, template)
    template_ok = (corr >= CORRELATION_THRESHOLD)
    tpl_mask = extract_horizontal_mask(template)
    line_sim = horizontal_line_similarity(patch, tpl_mask)
    if (feature_ok or template_ok) and (line_sim >= LINE_SIMILARITY_THRESHOLD):
        if not is_area_folder_like(screenshot, candidate['center'], template.shape[1], template.shape[0]):
            return True
        else:
            return False
    if corr >= HIGH_CORRELATION_OVERRIDE and line_sim >= (LINE_SIMILARITY_THRESHOLD * 0.7):
        return True
    return False

def get_console_hwnd():
    try:
        return int(kernel32.GetConsoleWindow())
    except Exception:
        return 0

def minimize_all_visible_top_windows_except_console():
    console_hwnd = get_console_hwnd()
    collected = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum_proc(hwnd, lParam):
        try:
            if not IsWindowVisible(hwnd):
                return True
            if hwnd == console_hwnd:
                return True
            cls = _get_class_name(hwnd)
            if cls in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd", "Progman", "Button"):
                return True
            length = GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            title = _get_window_text(hwnd)
            rect = _get_window_rect(hwnd)
            if rect is None:
                return True
            pid = wintypes.DWORD()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pid = int(pid.value)
            collected.append({"hwnd": int(hwnd), "rect": rect, "title": title, "class": cls, "pid": pid})
        except Exception:
            pass
        return True
    try:
        EnumWindows(_enum_proc, 0)
    except Exception:
        pass
    minimized = []
    for info in collected:
        hwnd = info['hwnd']
        try:
            ShowWindow(hwnd, SW_MINIMIZE)
            time.sleep(0.01)
            minimized.append(info)
        except Exception:
            pass
    time.sleep(0.12)
    return minimized

def _get_window_text(hwnd):
    length = GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    return ""

def _get_class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, buf, ctypes.sizeof(buf))
    return buf.value or ""

def _get_window_rect(hwnd):
    rect = wintypes.RECT()
    if GetWindowRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return None

def click_and_verify(x, y, timeout=4.0):
    sx, sy = int(x), int(y)
    pyautogui.moveTo(sx, sy, duration=0.12)
    pyautogui.doubleClick()
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any('notepad.exe' in (p.name().lower()) for p in psutil.process_iter()):
            time.sleep(0.35)
            return True
        time.sleep(0.12)
    return False

def type_and_save_post(post):
    title = post.get('title',''); body = post.get('body','')
    text = f"Title: {title}\n\n{body}"
    pyperclip.copy(text); time.sleep(0.08)
    if gw is not None:
        try:
            wins = [w for w in gw.getAllWindows() if 'notepad' in (w.title or '').lower()]
            if wins:
                wins[0].activate(); time.sleep(0.12)
        except Exception:
            pass
    pyautogui.hotkey('ctrl', 'v'); time.sleep(0.18)
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    filename = SAVE_DIR / f"post_{post.get('id',0)}.txt"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text)
        log("Wrote file:", filename)
    except Exception as e:
        log("ERROR writing file:", e)
    if gw is not None:
        try:
            wins = [w for w in gw.getAllWindows() if 'notepad' in (w.title or '').lower()]
            for w in wins:
                try:
                    w.activate(); time.sleep(0.12); w.close(); time.sleep(0.18)
                except Exception:
                    pass
        except Exception:
            pass
    else:
        try:
            pyautogui.hotkey('alt', 'f4'); time.sleep(0.12)
        except Exception:
            pass
    for _ in range(3):
        pyautogui.press('n'); time.sleep(0.06)
    time.sleep(0.18)

def fetch_posts(limit=10):
    try:
        r = requests.get(JSON_API, timeout=5)
        r.raise_for_status()
        return r.json()[:limit]
    except Exception:
        fallback=[]
        for i in range(1, limit+1):
            fallback.append({"userId":1,"id":i,"title":f"Sample Title {i}","body":"Fallback post body for offline testing."})
        return fallback

def find_icon_and_click(template):
    screenshot = grab_screenshot()
    res = detect_with_orb(screenshot, template)
    if res and is_confident_notepad(res, template, screenshot):
        annotate_and_save(screenshot, res['poly'], "detection_orb.png")
        cx, cy = res['center']
        if click_and_verify(cx, cy):
            return True
    res2 = detect_with_sift(screenshot, template)
    if res2 and is_confident_notepad(res2, template, screenshot):
        annotate_and_save(screenshot, res2['poly'], "detection_sift.png")
        cx, cy = res2['center']
        if click_and_verify(cx, cy):
            return True
    res3 = fallback_template_match(screenshot, template)
    if res3 and is_confident_notepad(res3, template, screenshot):
        annotate_and_save(screenshot, res3['poly'], "detection_tmpl.png")
        cx, cy = res3['center']
        if click_and_verify(cx, cy):
            return True
    return False

def main():
    log("Starting")
    log("SAVE_DIR =", str(SAVE_DIR))
    try:
        template = load_template(TEMPLATE_PATH)
    except Exception as e:
        log("ERROR loading template:", e)
        return
    posts = fetch_posts(10)
    if not posts:
        log("No posts fetched; exiting.")
        return
    for i, post in enumerate(posts, start=1):
        log(f"=== Post {i} id={post.get('id')} ===")
        success = False
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            log(f"Attempt {attempt} - minimizing other windows")
            minimized = minimize_all_visible_top_windows_except_console()
            if minimized:
                log(f"Minimized {len(minimized)} windows")
            time.sleep(0.12)
            try:
                ok = find_icon_and_click(template)
                if ok:
                    log("Clicked icon and likely opened Notepad.")
                    success = True
                    break
                else:
                    log("Icon not found on this screenshot.")
            except Exception as e:
                log("Detection error:", repr(e))
            time.sleep(RETRY_DELAY)
        if not success:
            log(f"Could not find Notepad icon after {RETRY_ATTEMPTS} attempts. Skipping post.")
            continue
        time.sleep(0.35)
        type_and_save_post(post)
        log("Saved post:", post.get('id'))
    log("Finished. Annotated detection images in:", ANNOTATED_DIR)
    log("Saved text files in:", SAVE_DIR)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        log("Program crashed unexpectedly.")