r"""Regenerate the four screenshots that README.md embeds.

Run from anywhere:  py "D:\claude\Pomodoro timer\tools\shoot_screenshots.py"

Rather than automating the built exe through the GUI, this drives the real
PomodoroTimer class in-process: each theme is set by calling set_theme directly,
so there are no timing races against an animation and no synthetic keystrokes to
land in the wrong window.

Two constraints are not cosmetic, and a future edit must preserve both.

1. save_settings is stubbed out and settings.json is restored from a backup
   afterwards. The app persists theme, zoom and window size, so posing it for a
   screenshot would otherwise overwrite whatever the user actually chose.

2. Every capture is clipped to a SINGLE window's bounds. An earlier version
   grabbed the union of the main window and the prompt centred over it; because
   the two did not overlap, the gap between them captured the desktop behind --
   wallpaper, icons and a personal photo -- in an image bound for a public
   repository. The prompt is smaller than the main window in both dimensions, so
   frame 4 places it entirely inside and grabs the main window's rectangle alone.
"""
import ctypes
import os
import shutil
import sys
import time
from ctypes import wintypes

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PROJECT, "docs", "screenshots")
sys.path.insert(0, PROJECT)

# Match main(): without this the window is captured at the wrong scale on a
# high-DPI display, and the window rectangles come back in virtual coordinates.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import tkinter as tk

from PIL import ImageGrab

import pomodoro_timer as pt

DWMWA_EXTENDED_FRAME_BOUNDS = 9


def visible_rect(win):
    """The window's true on-screen bounds.

    GetWindowRect includes the invisible resize border Windows 11 adds, which
    would put a band of desktop around every capture; the DWM attribute gives
    the bounds actually painted on screen.
    """
    win.update_idletasks()
    hwnd = wintypes.HWND(int(win.wm_frame(), 16))
    rect = wintypes.RECT()
    failed = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd, ctypes.c_uint(DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect), ctypes.sizeof(rect))
    if failed:
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def move_visible_to(win, x, y):
    """Move the window so its *visible* top-left corner lands exactly on (x, y).

    Tk's geometry() positions by the frame origin, which on Windows 11 sits
    outside the visible bounds by the width of the invisible resize border, and
    that offset is large enough to push a centred prompt clean off its parent.
    Measuring the border and driving SetWindowPos directly makes the placement
    exact instead of approximate.
    """
    hwnd = wintypes.HWND(int(win.wm_frame(), 16))
    frame = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(frame))
    visible_left, visible_top = visible_rect(win)[:2]
    border_x = visible_left - frame.left
    border_y = visible_top - frame.top
    SWP_NOSIZE, SWP_NOZORDER = 0x0001, 0x0004
    ctypes.windll.user32.SetWindowPos(
        hwnd, None, x - border_x, y - border_y, 0, 0, SWP_NOSIZE | SWP_NOZORDER)


def pump(win, ms=600):
    """Keep the event loop turning so the window is fully painted before capture."""
    win.lift()
    win.attributes("-topmost", True)
    win.update()
    deadline = time.time() + ms / 1000.0
    while time.time() < deadline:
        win.update()
        time.sleep(0.02)


def grab(box, name):
    image = ImageGrab.grab(bbox=box, all_screens=True)
    image.save(os.path.join(OUT, name))
    print(f"  {name}  {image.width}x{image.height}")


def main():
    backup = None
    if os.path.exists(pt.SETTINGS_PATH):
        backup = pt.SETTINGS_PATH + ".shootbak"
        shutil.copy2(pt.SETTINGS_PATH, backup)
    pt.save_settings = lambda *args, **kwargs: None

    os.makedirs(OUT, exist_ok=True)

    root = tk.Tk()
    app = pt.PomodoroTimer(root)
    app.set_scale(1.0)          # capture at 100%, not whatever zoom was saved
    root.update()
    root.geometry("+200+110")
    pump(root)

    for index, theme in enumerate(pt.THEME_ORDER, start=1):
        app.set_theme(theme, save=False)
        root.update()
        pump(root, 400)
        grab(visible_rect(root), f"{index}-{theme}.png")

    # Frame 4: the end-of-session prompt over the timer it interrupted.
    app.set_theme("black", save=False)
    app.sessions_done = 3       # so the counter agrees with the prompt's wording
    app._render()
    root.update()
    pump(root, 300)
    main_box = visible_rect(root)

    app.show_break_prompt()
    popup = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
    pump(popup, 300)

    left, top, right, bottom = visible_rect(popup)
    width, height = right - left, bottom - top
    assert width <= main_box[2] - main_box[0] and height <= main_box[3] - main_box[1], \
        "prompt no longer fits inside the main window; frame 4 would capture desktop"

    want_x = main_box[0] + (main_box[2] - main_box[0] - width) // 2
    want_y = main_box[1] + (main_box[3] - main_box[1] - height) // 2
    move_visible_to(popup, want_x, want_y)
    pump(popup, 500)

    final = visible_rect(popup)
    assert (final[0] >= main_box[0] and final[1] >= main_box[1]
            and final[2] <= main_box[2] and final[3] <= main_box[3]), \
        f"prompt {final} escaped the main window {main_box}; refusing to capture desktop"
    grab(main_box, "4-break-prompt.png")

    root.destroy()
    if backup:
        shutil.copy2(backup, pt.SETTINGS_PATH)
        os.remove(backup)
        print("settings.json restored")


if __name__ == "__main__":
    main()
