"""Drives the original launcher's wizard under wine, from inside the same
virtual desktop, with Win32 calls only: no real mouse or keyboard.

    python.exe wizard_drive.py <scenario> <outdir> [<System dir>]

Run by wizard-capture.sh, which sets up wine and the game files around it.
Scenarios: firstrun, changevideo, splash, safe, recovery. Each capture is a
.bmp of the window as the screen shows it, and a .json of its controls:
class, id, text, rectangle relative to the window's client area, visible,
checked, a list's items. Each scenario also writes <scenario>.log.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import subprocess
import sys
import time

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32")

SYSDIR = sys.argv[3] if len(sys.argv) > 3 else r"X:\Documents\projects\deusex\gamefiles\System"
EXE = SYSDIR + r"\DeusEx.exe"

BM_GETCHECK, BM_SETCHECK, BM_CLICK = 0xF0, 0xF1, 0xF5
LB_GETCOUNT, LB_GETTEXT, LB_GETTEXTLEN, LB_GETCURSEL = 0x18B, 0x189, 0x18A, 0x188
WM_GETTEXT, WM_GETTEXTLENGTH = 0x0D, 0x0E

WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.GetDlgCtrlID.restype = ctypes.c_int
user32.GetParent.restype = wt.HWND
user32.GetDC.restype = wt.HDC
gdi32.CreateCompatibleDC.restype = wt.HDC
gdi32.CreateCompatibleBitmap.restype = wt.HBITMAP
gdi32.SelectObject.restype = wt.HGDIOBJ

OUT = None
LOG = []


def log(msg):
    line = "%7.2f %s" % (time.monotonic() - T0, msg)
    LOG.append(line)
    print(line, flush=True)


def text_of(h):
    n = user32.SendMessageW(h, WM_GETTEXTLENGTH, 0, 0)
    buf = ctypes.create_unicode_buffer(max(n, 0) + 1)
    user32.SendMessageW(h, WM_GETTEXT, len(buf), ctypes.cast(buf, ctypes.c_void_p).value)
    return buf.value


def class_of(h):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, buf, 256)
    return buf.value


def pid_of(h):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    return pid.value


def top_windows():
    out = []

    def cb(h, _):
        out.append(h)
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def descendants(h):
    out = []

    def cb(c, _):
        out.append(c)
        return True
    user32.EnumChildWindows(h, WNDENUMPROC(cb), 0)
    return out


def rect_of(h):
    r = wt.RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    return r


def client_origin(h):
    p = wt.POINT(0, 0)
    user32.ClientToScreen(h, ctypes.byref(p))
    return p.x, p.y


def find_window(pred, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        for h in top_windows():
            if user32.IsWindowVisible(h) and pred(h):
                return h
        time.sleep(0.05)
    return None


def child_by_id(h, cid):
    for c in descendants(h):
        if user32.GetDlgCtrlID(c) == cid and user32.IsWindowVisible(c):
            return c
    return None


def controls(h):
    ox, oy = client_origin(h)
    wr = rect_of(h)
    rows = []
    for c in descendants(h):
        r = rect_of(c)
        cls = class_of(c)
        row = {
            "id": user32.GetDlgCtrlID(c), "class": cls, "text": text_of(c),
            "x": r.left - ox, "y": r.top - oy, "w": r.right - r.left, "h": r.bottom - r.top,
            "visible": bool(user32.IsWindowVisible(c)),
            "parent_id": user32.GetDlgCtrlID(user32.GetParent(c)),
        }
        if cls.lower() == "button":
            row["checked"] = user32.SendMessageW(c, BM_GETCHECK, 0, 0)
        if cls.lower() == "listbox":
            items = []
            for i in range(user32.SendMessageW(c, LB_GETCOUNT, 0, 0)):
                n = user32.SendMessageW(c, LB_GETTEXTLEN, i, 0)
                buf = ctypes.create_unicode_buffer(max(n, 0) + 1)
                user32.SendMessageW(c, LB_GETTEXT, i, ctypes.cast(buf, ctypes.c_void_p).value)
                items.append(buf.value)
            row["items"] = items
            row["selected"] = user32.SendMessageW(c, LB_GETCURSEL, 0, 0)
        rows.append(row)
    return {"title": text_of(h), "class": class_of(h),
            "window": [wr.left, wr.top, wr.right - wr.left, wr.bottom - wr.top],
            "client_origin": [ox - wr.left, oy - wr.top], "controls": rows}


def save_bmp(path, w, h, pixels):
    row = w * 4
    header = struct.pack("<2sIHHI", b"BM", 14 + 40 + row * h, 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, w, -h, 1, 32, 0, row * h, 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(header + info + pixels)


def capture(h, name):
    time.sleep(0.4)            # let it finish painting
    r = rect_of(h)
    w, hh = r.right - r.left, r.bottom - r.top
    screen = user32.GetDC(None)
    mem = gdi32.CreateCompatibleDC(screen)
    bmp = gdi32.CreateCompatibleBitmap(screen, w, hh)
    old = gdi32.SelectObject(mem, bmp)
    gdi32.BitBlt(mem, 0, 0, w, hh, screen, r.left, r.top, 0x00CC0020)
    buf = ctypes.create_string_buffer(w * hh * 4)
    info = struct.pack("<IiiHHIIiiII", 40, w, -hh, 1, 32, 0, 0, 0, 0, 0, 0)
    bi = ctypes.create_string_buffer(info, 40 + 16)
    gdi32.GetDIBits(mem, bmp, 0, hh, buf, bi, 0)
    gdi32.SelectObject(mem, old)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(None, screen)
    save_bmp(os.path.join(OUT, name + ".bmp"), w, hh, buf.raw)
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(controls(h), f, indent=1)
    log("captured %s (%dx%d) %r" % (name, w, hh, text_of(h)))


def click(h, cid, name):
    c = child_by_id(h, cid)
    if not c:
        log("no visible control %d (%s)" % (cid, name))
        return False
    log("click %s (%d)" % (name, cid))
    user32.SendMessageW(c, BM_CLICK, 0, 0)
    return True


def set_check(h, cid, state):
    c = child_by_id(h, cid)
    if c:
        user32.SendMessageW(c, BM_SETCHECK, state, 0)
        log("set %d checked=%d" % (cid, state))


def wait_list_ready(h, timeout=45):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        lb = child_by_id(h, 1103)
        if lb:
            n = user32.SendMessageW(lb, LB_GETCOUNT, 0, 0)
            if n > 0:
                buf = ctypes.create_unicode_buffer(512)
                user32.SendMessageW(lb, LB_GETTEXT, 0, ctypes.cast(buf, ctypes.c_void_p).value)
                if not buf.value.startswith("Detecting"):
                    return True
        time.sleep(0.2)
    return False


def launch(args):
    log("launch DeusEx.exe %s" % " ".join(args))
    return subprocess.Popen([EXE] + args, cwd=SYSDIR)


def wizard(proc, title_start, timeout=60):
    return find_window(lambda h: pid_of(h) == proc.pid and text_of(h).startswith(title_start), timeout)


def settle(proc, timeout=20):
    try:
        proc.wait(timeout)
        log("DeusEx.exe exited %s" % proc.returncode)
    except subprocess.TimeoutExpired:
        log("DeusEx.exe still running")


def scenario_firstrun():
    p = launch(["-firstrun"])
    w = wizard(p, "Deus Ex First-Time")
    if not w:
        log("no wizard"); return
    capture(w, "01-renderer-detecting")
    log("list ready: %s" % wait_list_ready(w))
    capture(w, "02-renderer-first-compatible")
    click(w, 1110, "All")
    capture(w, "03-renderer-first-all")
    click(w, 1109, "Compatible")
    capture(w, "04-renderer-first-compatible-again")
    click(w, 1004, "Next")
    time.sleep(0.5)
    capture(w, "05-after-renderer")
    for i in range(3):
        if child_by_id(w, 1100) or child_by_id(w, 1002):
            break
        click(w, 1004, "Next")
        time.sleep(0.5)
        capture(w, "06-page-%d" % i)
    if child_by_id(w, 1100):
        capture(w, "07-detail")
        click(w, 1004, "Next")
        time.sleep(0.5)
    capture(w, "08-firsttime")
    click(w, 3, "Back")
    time.sleep(0.5)
    capture(w, "09-back-to-detail")
    click(w, 2, "Cancel")
    settle(p)


def scenario_changevideo():
    p = launch(["-changevideo"])
    w = wizard(p, "Deus Ex Video")
    if not w:
        log("no wizard"); return
    wait_list_ready(w)
    capture(w, "11-renderer-video")
    click(w, 2, "Cancel")
    settle(p)


def scenario_safe():
    p = launch(["-safe"])
    w = wizard(p, "Deus Ex Safe Mode")
    if not w:
        log("no wizard"); return
    capture(w, "20-safemode")
    click(w, 1109, "Safe mode")
    time.sleep(0.5)
    capture(w, "21-safeoptions-defaults")
    set_check(w, 1109, 0)          # No3DSound off; No3DVideo, Window, Res stay on
    capture(w, "22-safeoptions-no3dsound-off")
    click(w, 1004, "Run!")
    settle(p, 30)
    box = find_window(lambda h: text_of(h) == "Cd Required At Startup", 60)
    if not box:
        log("no CD prompt"); return
    capture(box, "23-cd-prompt")
    relaunched = pid_of(box)
    for h in top_windows():
        if pid_of(h) == relaunched:
            r = rect_of(h)
            log("relaunched window %#x class=%r title=%r visible=%d rect=%d,%d %dx%d" % (
                h, class_of(h), text_of(h), user32.IsWindowVisible(h),
                r.left, r.top, r.right - r.left, r.bottom - r.top))
            if user32.IsWindowVisible(h) and class_of(h) == "#32770" and not text_of(h):
                user32.SetWindowPos(box, 1, 0, 0, 0, 0, 0x13)   # the prompt to the bottom, unmoved
                capture(h, "24-splash-behind-cd-prompt")
                user32.SetWindowPos(box, 0, 0, 0, 0, 0, 0x13)
    marker = os.path.join(OUT, "cdprompt.ready")
    open(marker, "w").close()
    log("waiting for the go file")
    go = os.path.join(OUT, "cdprompt.go")
    end = time.monotonic() + 300
    while not os.path.exists(go) and time.monotonic() < end:
        time.sleep(0.2)
    cancel = child_by_id(box, 2)
    log("cancel the CD prompt: %s" % bool(cancel))
    if cancel:
        user32.SendMessageW(cancel, BM_CLICK, 0, 0)
    time.sleep(3)


def scenario_splash():
    p = launch(["-changevideo"])
    seen = {}
    end = time.monotonic() + 12
    while time.monotonic() < end:
        for h in top_windows():
            if pid_of(h) != p.pid:
                continue
            r = rect_of(h)
            key = (h, bool(user32.IsWindowVisible(h)))
            if key not in seen:
                seen[key] = True
                log("window %#x class=%r title=%r visible=%d rect=%d,%d %dx%d" % (
                    h, class_of(h), text_of(h), user32.IsWindowVisible(h),
                    r.left, r.top, r.right - r.left, r.bottom - r.top))
                if user32.IsWindowVisible(h) and not text_of(h) and "splash" not in " ".join(LOG[-3:]):
                    capture(h, "12-splash-%x" % h)
        if wizard(p, "Deus Ex Video", 0.01):
            break
        time.sleep(0.02)
    w = wizard(p, "Deus Ex Video")
    if w:
        wait_list_ready(w)
        click(w, 2, "Cancel")
    settle(p)


def scenario_make():
    p = launch(["-make"])
    box = find_window(lambda h: pid_of(h) == p.pid and class_of(h) == "#32770", 30)
    if not box:
        log("no error box"); return
    capture(box, "40-make-error")
    ok = child_by_id(box, 1) or child_by_id(box, 2)
    if ok:
        user32.SendMessageW(ok, BM_CLICK, 0, 0)
    settle(p)


def scenario_recovery():
    p = launch([])
    w = wizard(p, "Deus Ex Recovery Mode")
    if not w:
        log("no wizard"); return
    capture(w, "30-recoverymode")
    click(w, 2, "Cancel")
    settle(p)


if __name__ == "__main__":
    T0 = time.monotonic()
    scenario, OUT = sys.argv[1], sys.argv[2]
    os.makedirs(OUT, exist_ok=True)
    try:
        globals()["scenario_" + scenario]()
    finally:
        with open(os.path.join(OUT, scenario + ".log"), "w", encoding="utf-8") as f:
            f.write("\n".join(LOG) + "\n")
