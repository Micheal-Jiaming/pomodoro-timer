"""Pomodoro Timer - a work/break timer with 15 / 30 / 45 minute presets.

When a session ends the app beeps, raises itself, and opens a pop-up that
tells you to take a break and lets you pick the next duration. When the break
ends, a second pop-up asks which work session to run next.

Run with:  python pomodoro_timer.py
"""

import json
import os
import sys
import time
import tkinter as tk
from tkinter import simpledialog

try:  # Windows-only sound support; degrades to the Tk bell elsewhere.
    import winsound
except ImportError:  # pragma: no cover - non-Windows
    winsound = None


WORK_PRESETS = (15, 30, 45)      # minutes
BREAK_PRESETS = (5, 10, 15)      # minutes

# Backgrounds. Each theme is a whole palette, not just a background colour: the
# two light ones need their own, deeper accents so white button text stays
# readable on them. Every theme uses the same fonts and paddings, so the window
# is exactly the same size whichever is chosen.
THEMES = {
    "black": dict(
        BG="#15171c", CARD="#1e2128", CARD_HOVER="#2a2e37",
        FG="#eef1f6", MUTED="#8b93a5", TRACK="#2b2f39",
        ACCENT="#e2564a", ACCENT_HOVER="#f06b5f",          # work
        ACCENT_BREAK="#3fa66c", BREAK_HOVER="#4cbd7c",     # break
        ACCENT_LOCK="#4a6fa5",   # size locked — neither work nor break
        ON_ACCENT="#ffffff",
    ),
    "paper": dict(
        BG="#f4efe6", CARD="#e5ded0", CARD_HOVER="#d8d0be",
        FG="#2e2a24", MUTED="#7b7267", TRACK="#d6cebe",
        ACCENT="#cf4a3d", ACCENT_HOVER="#e05a4c",
        ACCENT_BREAK="#2f8f5c", BREAK_HOVER="#3aa46b",
        ACCENT_LOCK="#41628f",
        ON_ACCENT="#ffffff",
    ),
    "mist": dict(
        BG="#eaeef3", CARD="#d9e0e9", CARD_HOVER="#c9d2de",
        FG="#26303c", MUTED="#6c7b8d", TRACK="#c8d2dd",
        ACCENT="#cf4a3d", ACCENT_HOVER="#e05a4c",
        ACCENT_BREAK="#2f8f5c", BREAK_HOVER="#3aa46b",
        ACCENT_LOCK="#41628f",
        ON_ACCENT="#ffffff",
    ),
}
THEME_ORDER = ("black", "paper", "mist")
DEFAULT_THEME = "black"

# The active palette, as module-level names. Changing theme rebinds these and
# then rebuilds every widget, so nothing is left holding a stale colour.
BG = CARD = CARD_HOVER = FG = MUTED = TRACK = ""
ACCENT = ACCENT_HOVER = ACCENT_BREAK = BREAK_HOVER = ACCENT_LOCK = ON_ACCENT = ""


def apply_theme(name):
    """Make `name` the active palette; returns the name actually applied."""
    if name not in THEMES:
        name = DEFAULT_THEME
    globals().update(THEMES[name])
    return name


apply_theme(DEFAULT_THEME)

FONT = "Segoe UI"

SCALE_MIN = 0.5           # half size
SCALE_MAX = 2.5           # two and a half times
SCALE_STEP = 0.1

SETTINGS_PATH = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"),
    "PomodoroTimer", "settings.json",
)


def resource_path(name):
    """Locate a bundled data file, both from source and inside a PyInstaller exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def load_settings():
    try:
        # utf-8-sig: a hand-edit in Notepad leaves a BOM that plain utf-8 chokes on.
        with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except OSError:
        pass  # remembering the size is a nicety, not worth crashing over


def scaled(value, scale, minimum=1):
    """A pixel measurement from the 100% design, resized."""
    return max(minimum, int(round(value * scale)))


def font_at(size, scale, style="normal"):
    return (FONT, max(6, int(round(size * scale))), style)


def fmt(seconds):
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


# --------------------------------------------------------------- aspect lock
WM_SIZING = 0x0214
GWLP_WNDPROC = -4
# Which edge the drag loop reports, per WMSZ_* in winuser.h
EDGE_LEFT = frozenset((1, 4, 7))        # LEFT, TOPLEFT, BOTTOMLEFT
EDGE_TOP = frozenset((3, 4, 5))         # TOP, TOPLEFT, TOPRIGHT
EDGE_SIDE = frozenset((1, 2))           # LEFT, RIGHT — height follows width
EDGE_UPDOWN = frozenset((3, 6))         # TOP, BOTTOM — width follows height
# WMSZ_* only ever runs 1..8. A WM_SIZING carrying anything else did not come
# from the drag loop, so its lparam is not a rectangle we should write through.
EDGE_VALID = frozenset(range(1, 9))
# GetSystemMetrics indices for the box spanning every monitor.
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
# Slack around that box, in px. A real drag can push a frame well off-screen,
# so this has to be generous or the check would fight ordinary resizing.
SCREEN_SLACK = 4096


class AspectLock:
    """Hold a window to one width:height ratio while its border is dragged.

    Tk accepts `wm aspect` but never applies it on Windows, so the constraint has
    to be imposed where the drag actually happens: WM_SIZING carries the
    rectangle the drag loop proposes, and a window procedure is free to rewrite
    it before the window is resized. Dragging one side then moves the other in
    step, live, with no snapping after the fact.
    """

    def __init__(self, root):
        self.root = root
        self.ratio = 0.0            # client width / client height
        self.extra = (0, 0)         # frame size minus client size
        self.active = False
        self._hwnd = None
        self._old_proc = None
        self._proc = None           # kept alive for as long as it is installed
        self._calls = 0
        self._sizing_calls = 0
        self._last_error = None

    # -- setup ----------------------------------------------------------
    def install(self):
        """Prepare the hook and attach it. False if that isn't possible here."""
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            from ctypes import wintypes

            self._ctypes = ctypes
            self._user32 = ctypes.windll.user32
            long_ptr = ctypes.c_ssize_t
            lresult = ctypes.c_ssize_t

            self._rect_type = type("RECT", (ctypes.Structure,), {"_fields_": [
                ("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG),
            ]})

            set_long = getattr(self._user32, "SetWindowLongPtrW", None)
            if set_long is None:  # 32-bit Python
                set_long = self._user32.SetWindowLongW
            set_long.restype = long_ptr
            set_long.argtypes = [wintypes.HWND, ctypes.c_int, long_ptr]
            self._user32.CallWindowProcW.restype = lresult
            self._user32.CallWindowProcW.argtypes = [
                long_ptr, wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                wintypes.LPARAM,
            ]

            proc_type = ctypes.WINFUNCTYPE(
                lresult, wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                wintypes.LPARAM,
            )
            self._proc = proc_type(self._dispatch)
            self._proc_addr = ctypes.cast(self._proc, ctypes.c_void_p).value
            self._set_long = set_long
        except Exception:
            self._proc = None
            return False       # fall back to snapping the window after a drag
        self.active = True
        return self.attach()

    def attach(self):
        """(Re)subclass the current wrapper window.

        Tk builds a toplevel's real window lazily and throws it away again for
        some `wm` calls — `-topmost` among them, which this app toggles — so the
        window alive at startup is not the one that ends up on screen. Every
        entry point that might follow such a call comes back through here.
        """
        if not self.active:
            return False
        try:
            hwnd = int(self.root.wm_frame(), 16)
            if hwnd == self._hwnd and self._old_proc:
                return True
            old = self._set_long(hwnd, GWLP_WNDPROC, self._proc_addr)
            if not old:
                return False
            self._hwnd, self._old_proc = hwnd, old
        except Exception:
            return False
        return True

    def remove(self):
        if not self.active:
            return
        try:
            if self._old_proc:
                self._set_long(self._hwnd, GWLP_WNDPROC, self._old_proc)
        except Exception:
            pass
        self.active = False    # keep self._proc alive; Windows may still call it

    def set_ratio(self, width, height):
        """Adopt the ratio of a `width` x `height` client area."""
        if not self.active or width <= 0 or height <= 0:
            return
        self.ratio = width / height
        try:
            frame, client = self._rect_type(), self._rect_type()
            self._user32.GetWindowRect(self._hwnd, self._ctypes.byref(frame))
            self._user32.GetClientRect(self._hwnd, self._ctypes.byref(client))
            self.extra = (
                (frame.right - frame.left) - (client.right - client.left),
                (frame.bottom - frame.top) - (client.bottom - client.top),
            )
        except Exception:
            pass  # keep the previous border allowance

    def mouse_held(self):
        """True while the primary button is down, i.e. a drag is still running."""
        if not self.active:
            return False
        try:
            return bool(self._user32.GetAsyncKeyState(0x01) & 0x8000)
        except Exception:
            return False

    def _plausible(self, rect):
        """True when a proposed rectangle looks like one the drag loop sent.

        `rect` reaches us as a raw pointer in the message's lparam, so its
        contents are only as trustworthy as whoever posted the message. Before
        writing four LONGs back through that pointer, check the rectangle is
        non-degenerate and lands somewhere on the desktop. A rectangle far
        outside it means the pointer did not come from a real resize, and the
        right response is to refuse rather than to clamp it into range: a wrong
        pointer is a bug or a forged message, not a small numerical error.

        Returns False if the desktop bounds cannot be read at all, since an
        unverifiable rectangle should not be trusted either.
        """
        try:
            metric = self._user32.GetSystemMetrics
            left = metric(SM_XVIRTUALSCREEN) - SCREEN_SLACK
            top = metric(SM_YVIRTUALSCREEN) - SCREEN_SLACK
            right = left + metric(SM_CXVIRTUALSCREEN) + 2 * SCREEN_SLACK
            bottom = top + metric(SM_CYVIRTUALSCREEN) + 2 * SCREEN_SLACK
        except Exception:
            return False
        # A zero or inverted extent is never something the drag loop proposes.
        if rect.right <= rect.left or rect.bottom <= rect.top:
            return False
        return (left <= rect.left and rect.right <= right
                and top <= rect.top and rect.bottom <= bottom)

    # -- the window procedure -------------------------------------------
    def _dispatch(self, hwnd, msg, wparam, lparam):
        result = self._user32.CallWindowProcW(
            self._old_proc, hwnd, msg, wparam, lparam
        )
        self._calls += 1
        # `int(wparam) in EDGE_VALID` gates the cast below. This window
        # procedure is reachable by any process that can SendMessage to our
        # hwnd, and the WM_SIZING branch writes through a caller-supplied
        # pointer, so both the edge code and the rectangle are validated before
        # anything is written. Same-session, equal-or-higher integrity is
        # required to send at all, so this is defence in depth rather than a
        # remotely reachable hole - but it is four arbitrary writes otherwise.
        if msg == WM_SIZING and self.ratio > 0 and int(wparam) in EDGE_VALID:
            self._sizing_calls += 1
            try:
                rect = self._ctypes.cast(
                    lparam, self._ctypes.POINTER(self._rect_type)
                ).contents
                if self._plausible(rect):
                    self._constrain(int(wparam), rect)
                    return 1  # TRUE: the rectangle was adjusted
            except Exception as exc:
                self._last_error = repr(exc)
        return result

    def _constrain(self, edge, rect):
        """Rewrite the proposed rectangle so the two sides stay in proportion."""
        pad_w, pad_h = self.extra
        width = rect.right - rect.left - pad_w
        height = rect.bottom - rect.top - pad_h
        if width <= 0 or height <= 0:
            return
        if edge in EDGE_UPDOWN:
            width = int(round(height * self.ratio))
        else:
            # Sides and corners alike take their lead from the width.
            height = int(round(width / self.ratio))
        # Move only the edges the user isn't holding, so the anchored corner
        # stays where it is.
        if edge in EDGE_TOP:
            rect.top = rect.bottom - (height + pad_h)
        else:
            rect.bottom = rect.top + height + pad_h
        if edge in EDGE_LEFT:
            rect.left = rect.right - (width + pad_w)
        else:
            rect.right = rect.left + width + pad_w


class PomodoroTimer:
    def __init__(self, root):
        self.root = root
        self.total = WORK_PRESETS[0] * 60
        self.remaining = float(self.total)
        self.running = False
        self.end_at = 0.0
        self.mode = "work"          # "work" | "break"
        self.sessions_done = 0
        self._job = None

        # Interface scaling. Every pixel measurement below is written for 100%
        # and passed through self.px(); fonts through self.font().
        self.scale = 1.0
        self.locked = False         # frozen size: no dragging, no zoom shortcuts
        self.container = None
        self._base_w = 0            # natural window size at 100%, measured once
        self._base_h = 0
        self._resize_job = None
        self._save_job = None
        self._unfreeze_job = None
        self._min_w = 0
        self._min_h = 0
        # Mapping a window emits junk sizes (200x200, 120x1, …) before it
        # settles; none of them are the user resizing anything.
        self._ignore_configure = True
        self._last_size = (0, 0)

        self.on_top = tk.BooleanVar(value=False)

        settings = load_settings()
        # The palette has to be settled before any widget is built.
        self.theme = apply_theme(settings.get("theme", DEFAULT_THEME))

        root.title("Pomodoro Timer")
        root.configure(bg=BG)
        root.resizable(True, True)
        try:
            root.iconbitmap(resource_path("pomodoro_timer.ico"))
        except tk.TclError:
            pass  # icon is cosmetic; run without it if missing

        self._build_ui()
        self._bind_keys()
        self._render()
        self._measure_base()
        self.aspect = AspectLock(root)
        self.aspect.install()   # if it can't, drags snap into proportion instead
        self._sync_aspect()
        self.set_scale(settings.get("scale", 1.0), force=True)
        self.set_locked(settings.get("locked", False), save=False)
        root.bind("<Configure>", self._on_configure)
        root.bind("<Destroy>", self._on_destroy)
        root.bind("<Map>", self._sync_aspect, add="+")   # the real window exists now
        self._cancel(("_unfreeze_job",))   # startup gets the longer grace period
        self._unfreeze_job = root.after(600, self._resume_configure)

    # --------------------------------------------------------------- sizing
    def px(self, value):
        return scaled(value, self.scale)

    def font(self, size, style="normal"):
        return font_at(size, self.scale, style)

    def _measure_base(self):
        """Remember the natural 100% size — the reference every scale works from."""
        self.root.update_idletasks()
        self._base_w = self.root.winfo_reqwidth()
        self._base_h = self.root.winfo_reqheight()
        # The smallest size has to be measured too, not derived: point sizes are
        # whole numbers and bottom out at 6, so the layout at 50% is wider than
        # half of the layout at 100%. Deriving it would let a drag clip the UI.
        self.scale = SCALE_MIN
        self._rebuild()
        self.root.update_idletasks()
        self._min_w = self.root.winfo_reqwidth()
        self._min_h = self.root.winfo_reqheight()
        self.scale = 1.0
        self._rebuild()
        self.root.update_idletasks()
        self.root.minsize(self._min_w, self._min_h)

    def set_scale(self, value, snap=True, force=False):
        """Scale to `value` (1.0 = 100%) and, unless dragging, refit the window."""
        if self.locked and not force:
            return
        try:
            value = max(SCALE_MIN, min(SCALE_MAX, round(float(value), 2)))
        except (TypeError, ValueError):
            return
        if abs(value - self.scale) < 0.005:
            return
        self.scale = value
        self._rebuild()
        if snap:
            self._fit_window()
        self._save_soon()

    def nudge_scale(self, delta):
        self.set_scale(self.scale + delta)

    # ---------------------------------------------------------------- theme
    def cycle_theme(self):
        order = THEME_ORDER
        nxt = order[(order.index(self.theme) + 1) % len(order)] \
            if self.theme in order else DEFAULT_THEME
        self.set_theme(nxt)

    def set_theme(self, name, save=True):
        """Repaint in `name`. Sizes are identical across themes, so the window
        keeps its dimensions and only the colours change."""
        self.theme = apply_theme(name)
        self.root.configure(bg=BG)
        self._rebuild()
        if save:
            self._save_soon()

    # ----------------------------------------------------------------- lock
    def toggle_lock(self):
        self.set_locked(not self.locked)

    def set_locked(self, locked, save=True):
        """Freeze the size: the window stops resizing and zooming does nothing."""
        self.locked = bool(locked)
        # A non-resizable window can't be dragged bigger, which is most of the job.
        self.root.resizable(not self.locked, not self.locked)
        self._render()
        if save:
            self._save_soon()

    def _rebuild(self):
        """Throw the widgets away and lay them out again at the current scale."""
        if self.container is not None:
            self.container.destroy()
        self._build_ui()
        self._render()
        self._sync_aspect()

    def _sync_aspect(self, event=None):
        """Point the drag constraint at the proportions of the current layout."""
        aspect = getattr(self, "aspect", None)
        if aspect is None or not aspect.active:
            return
        aspect.attach()         # cheap, and covers a window Tk swapped under us
        self.root.update_idletasks()
        aspect.set_ratio(self.root.winfo_reqwidth(), self.root.winfo_reqheight())

    def _fit_window(self):
        """Resize the window to exactly the layout it holds."""
        self.root.update_idletasks()
        # Drop any drag still queued: it measured the window we're about to replace.
        self._cancel(("_resize_job",))
        width, height = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        # Recording the size we ask for is enough to recognise, and ignore, the
        # `<Configure>` it echoes back. A timed blackout instead of this would
        # swallow a real drag that happened to land inside the window.
        self._last_size = (width, height)
        self.root.geometry(f"{width}x{height}")

    def _resume_configure(self):
        self._unfreeze_job = None
        self._ignore_configure = False
        size = (self.root.winfo_width(), self.root.winfo_height())
        stale = size != self._last_size
        # Whatever the window ended up as is the new baseline to compare against.
        self._last_size = size
        if stale and not self.locked and self._base_w:
            # Someone resized us while we weren't listening — a drag that both
            # began and ended inside the grace period. Catch up rather than
            # leave the layout at a size nobody asked for.
            self._cancel(("_resize_job",))
            self._resize_job = self.root.after(60, self._scale_to_window)

    def _cancel(self, names):
        for name in names:
            job = getattr(self, name, None)
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, name, None)

    def _on_destroy(self, event):
        """Closing mid-countdown left `after` callbacks firing into a dead window."""
        if event.widget is not self.root:
            return
        pending_save = self._save_job is not None
        self._cancel(("_resize_job", "_save_job", "_unfreeze_job", "_job"))
        self.aspect.remove()
        if pending_save:
            self._save_state()  # flush a size change made in the last moment

    def _on_configure(self, event):
        """The user dragged an edge — follow along, once the dragging settles."""
        if event.widget is not self.root or not self._base_w:
            return
        size = (event.width, event.height)
        if size == self._last_size:
            return  # a move, not a resize — the scale must not budge
        self._last_size = size
        if self._ignore_configure or self.locked:
            return
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(120, self._scale_to_window)

    def _scale_to_window(self):
        self._resize_job = None
        if self.locked:
            return
        width, height = self.root.winfo_width(), self.root.winfo_height()
        if width < self._min_w or height < self._min_h:
            # Below minsize the window manager would never let a drag land, so
            # this is a transient from a window still being mapped.
            return
        # Measure against the layout that's actually on screen, not against the
        # 100% size: the natural size isn't linear in the scale (the footer text
        # collapses below 85%), so comparing to the base would jump the moment
        # anything nudged the window. Relative, a fitted window infers its own
        # scale exactly and only a genuine drag moves it.
        need_w = max(1, self.root.winfo_reqwidth())
        need_h = max(1, self.root.winfo_reqheight())
        target = self.scale * min(width / need_w, height / need_h)
        target = max(SCALE_MIN, min(SCALE_MAX, round(target, 2)))
        if abs(target - self.scale) < 0.03:
            return  # ignore jitter, and never fight the drag with a rebuild loop
        self.scale = target
        self._rebuild()
        self._shrink_to_fit(width, height)
        self._save_soon()
        self._snap_when_idle()

    def _snap_when_idle(self):
        """Close the last few pixels between the window and the layout in it.

        The ratio the drag preserved is the one the previous layout had, and the
        new one differs slightly, so a drag can leave a thin margin. Squaring it
        up would fight a drag that's still going, hence the wait for the button.
        """
        if self.locked:
            return
        if self.aspect.mouse_held():
            self._cancel(("_resize_job",))
            self._resize_job = self.root.after(200, self._snap_when_idle)
            return
        self.root.update_idletasks()
        if (self.root.winfo_width() != self.root.winfo_reqwidth()
                or self.root.winfo_height() != self.root.winfo_reqheight()):
            self._fit_window()

    def _shrink_to_fit(self, width, height):
        """Trim the scale until the layout fits the window the user dragged.

        Point sizes are whole numbers, so a scale can round up into needing more
        room than the drag allowed; left alone that clips the edges of the UI.
        """
        for _ in range(3):
            self.root.update_idletasks()
            need_w = max(1, self.root.winfo_reqwidth())
            need_h = max(1, self.root.winfo_reqheight())
            if need_w <= width and need_h <= height:
                return
            smaller = round(self.scale * min(width / need_w, height / need_h), 2)
            if smaller >= self.scale:
                smaller = round(self.scale - 0.01, 2)   # always make progress
            if smaller < SCALE_MIN:
                return
            self.scale = smaller
            self._rebuild()

    def _save_soon(self):
        if self._save_job is not None:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(700, self._save_state)

    def _save_state(self):
        # Safe to call directly: drops the scheduled write rather than leaving
        # it to fire later, possibly into a window that has since closed.
        self._cancel(("_save_job",))
        settings = load_settings()
        settings["scale"] = self.scale
        settings["locked"] = self.locked
        settings["theme"] = self.theme
        save_settings(settings)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        px, font = self.px, self.font
        self.container = tk.Frame(self.root, bg=BG)
        self.container.pack(expand=True)   # stays centred in any spare space
        parent = self.container

        tk.Label(
            parent, text="P O M O D O R O   T I M E R", bg=BG, fg=MUTED,
            font=font(10, "bold"),
        ).pack(pady=(px(18), px(6)))

        size = px(260)
        self.canvas = tk.Canvas(
            parent, width=size, height=size, bg=BG,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack(padx=px(30))

        inset = px(18)
        box = (inset, inset, size - inset, size - inset)
        ring = max(2, px(14))
        self.canvas.create_arc(
            *box, start=90, extent=-359.99, style="arc", width=ring, outline=TRACK,
        )
        self.arc = self.canvas.create_arc(
            *box, start=90, extent=-359.99, style="arc", width=ring, outline=ACCENT,
        )
        self.time_text = self.canvas.create_text(
            size / 2, px(122), text="15:00", fill=FG, font=font(44, "bold"),
        )
        self.mode_text = self.canvas.create_text(
            size / 2, px(164), text="WORK", fill=MUTED, font=font(10, "bold"),
        )

        # Duration presets: work lengths on one row, break lengths on the next
        presets = tk.Frame(parent, bg=BG)
        presets.pack(pady=(px(14), px(4)))
        self.work_buttons = self._preset_row(presets, 0, "WORK", WORK_PRESETS, "work")
        self.break_buttons = self._preset_row(
            presets, 1, "BREAK", BREAK_PRESETS, "break"
        )

        # Controls, with the zoom cluster tucked in beside them
        controls = tk.Frame(parent, bg=BG)
        controls.pack(pady=(px(8), px(4)))
        self.start_btn = tk.Button(
            controls, text="Start", width=12, command=self.toggle,
            **self._btn_style(primary=True),
        )
        self.start_btn.pack(side="left", padx=px(4))
        tk.Button(
            controls, text="Reset", width=10, command=self.reset,
            **self._btn_style(),
        ).pack(side="left", padx=px(4))
        self._zoom_cluster(controls).pack(side="left", padx=(px(14), 0))

        # Footer
        footer = tk.Frame(parent, bg=BG)
        footer.pack(fill="x", padx=px(24), pady=(px(10), px(16)))
        self.status = tk.Label(
            footer, text="", bg=BG, fg=MUTED, font=font(9),
        )
        self.status.pack(side="left", padx=(0, px(10)))

        tk.Checkbutton(
            footer, text="Always on top", variable=self.on_top,
            command=self.apply_on_top,
            bg=BG, fg=MUTED, selectcolor=CARD, activebackground=BG,
            activeforeground=FG, font=font(9), bd=0, highlightthickness=0,
        ).pack(side="right")

    def _zoom_cluster(self, parent):
        """Shrink / percentage / grow, then the padlock that freezes the lot."""
        frame = tk.Frame(parent, bg=BG)
        small = self._btn_style()
        small.update(
            font=self.font(10, "bold"), padx=self.px(2), disabledforeground=MUTED,
        )
        minus = tk.Button(
            frame, text="−", width=2, command=lambda: self.nudge_scale(-SCALE_STEP),
            **small,
        )
        minus.pack(side="left", padx=self.px(1))
        self.zoom_label = tk.Button(
            frame, text="100%", width=5, command=lambda: self.set_scale(1.0),
            **small,
        )
        self.zoom_label.pack(side="left", padx=self.px(1))
        plus = tk.Button(
            frame, text="+", width=2, command=lambda: self.nudge_scale(SCALE_STEP),
            **small,
        )
        plus.pack(side="left", padx=self.px(1))
        self.zoom_buttons = (minus, self.zoom_label, plus)

        self.lock_btn = tk.Button(
            frame, text="Lock", width=6, command=self.toggle_lock, **small,
        )
        self.lock_btn.pack(side="left", padx=(self.px(6), self.px(1)))

        # Named rather than a swatch, so it says what it is and what's next.
        self.theme_btn = tk.Button(
            frame, text=self.theme.title(), width=6, command=self.cycle_theme,
            **small,
        )
        self.theme_btn.pack(side="left", padx=(self.px(6), self.px(1)))
        return frame

    def _preset_row(self, parent, row, label, minutes_list, mode):
        """One labelled row of duration buttons, plus a Custom entry for that mode."""
        tk.Label(
            parent, text=label, bg=BG, fg=MUTED, font=self.font(9, "bold"),
            width=6, anchor="e",
        ).grid(row=row, column=0, padx=(0, self.px(6)), pady=self.px(3))

        buttons = {}
        for column, minutes in enumerate(minutes_list, start=1):
            b = tk.Button(
                parent, text=f"{minutes} min", width=6,
                command=lambda m=minutes: self.set_duration(m, mode),
                **self._btn_style(),
            )
            b.grid(row=row, column=column, padx=self.px(3), pady=self.px(3))
            buttons[minutes] = b

        tk.Button(
            parent, text="Custom", width=6,
            command=lambda: self.ask_custom(mode),
            **self._btn_style(),
        ).grid(
            row=row, column=len(minutes_list) + 1,
            padx=self.px(3), pady=self.px(3),
        )
        return buttons

    def _btn_style(self, primary=False):
        return dict(
            bg=ACCENT if primary else CARD,
            fg=ON_ACCENT if primary else FG,
            activebackground=ACCENT_HOVER if primary else CARD_HOVER,
            activeforeground=ON_ACCENT if primary else FG,
            font=self.font(10, "bold" if primary else "normal"),
            relief="flat", bd=0, padx=self.px(6), pady=self.px(7), cursor="hand2",
            highlightthickness=0,
        )

    def _bind_keys(self):
        self.root.bind("<space>", lambda e: self.toggle())
        self.root.bind("<r>", lambda e: self.reset())
        for i, minutes in enumerate(WORK_PRESETS, start=1):
            self.root.bind(str(i), lambda e, m=minutes: self.set_duration(m, "work"))
        for i, minutes in enumerate(BREAK_PRESETS, start=len(WORK_PRESETS) + 1):
            self.root.bind(str(i), lambda e, m=minutes: self.set_duration(m, "break"))

        for seq in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
            self.root.bind(seq, lambda e: self.nudge_scale(SCALE_STEP))
        for seq in ("<Control-minus>", "<Control-underscore>", "<Control-KP_Subtract>"):
            self.root.bind(seq, lambda e: self.nudge_scale(-SCALE_STEP))
        self.root.bind("<Control-0>", lambda e: self.set_scale(1.0))
        self.root.bind("<Control-MouseWheel>", self._on_wheel)
        self.root.bind("<Control-l>", lambda e: self.toggle_lock())
        self.root.bind("<Control-t>", lambda e: self.cycle_theme())

    def _on_wheel(self, event):
        self.nudge_scale(SCALE_STEP if event.delta > 0 else -SCALE_STEP)
        return "break"

    # --------------------------------------------------------------- timer
    def set_duration(self, minutes, mode="work"):
        self.stop_ticking()
        self.mode = mode
        self.total = int(minutes * 60)
        self.remaining = float(self.total)
        self.running = False
        self._render()

    def ask_custom(self, mode="work"):
        noun = "Break" if mode == "break" else "Session"
        minutes = simpledialog.askinteger(
            f"Custom {noun.lower()}", f"{noun} length in minutes (1-180):",
            parent=self.root, minvalue=1, maxvalue=180,
            initialvalue=self.total // 60,
        )
        if minutes:
            self.set_duration(minutes, mode)

    def toggle(self):
        if self.running:
            self.pause()
        else:
            self.start()

    def start(self):
        if self.remaining <= 0:
            self.remaining = float(self.total)
        self.end_at = time.monotonic() + self.remaining
        self.running = True
        self._tick()

    def pause(self):
        self.remaining = max(0.0, self.end_at - time.monotonic())
        self.running = False
        self.stop_ticking()
        self._render()

    def reset(self):
        self.stop_ticking()
        self.running = False
        self.remaining = float(self.total)
        self._render()

    def stop_ticking(self):
        if self._job is not None:
            self.root.after_cancel(self._job)
            self._job = None

    def _tick(self):
        self.remaining = max(0.0, self.end_at - time.monotonic())
        self._render()
        if self.remaining <= 0:
            self.running = False
            self._job = None
            self._finish()
            return
        self._job = self.root.after(200, self._tick)

    def _finish(self):
        finished_mode = self.mode
        if finished_mode == "work":
            self.sessions_done += 1
        self._render()
        self.alert()
        self.raise_window()
        if finished_mode == "work":
            self.show_break_prompt()
        else:
            self.show_next_session_prompt()

    # -------------------------------------------------------------- render
    def _render(self):
        colour = ACCENT if self.mode == "work" else ACCENT_BREAK
        fraction = (self.remaining / self.total) if self.total else 0
        extent = -359.99 * max(0.0, min(1.0, fraction))
        if extent == 0:
            extent = -0.01  # keep the arc item valid at zero
        self.canvas.itemconfigure(self.arc, extent=extent, outline=colour)
        self.canvas.itemconfigure(self.time_text, text=fmt(self.remaining))
        self.canvas.itemconfigure(
            self.mode_text,
            text=("BREAK" if self.mode == "break" else "WORK")
            + ("" if self.running or self.remaining <= 0 else "  ·  PAUSED"),
        )
        self.start_btn.configure(
            text="Pause" if self.running else "Start",
            bg=colour,
            activebackground=BREAK_HOVER if self.mode == "break" else ACCENT_HOVER,
        )

        rows = (
            ("work", self.work_buttons, ACCENT),
            ("break", self.break_buttons, ACCENT_BREAK),
        )
        for mode, buttons, row_colour in rows:
            for minutes, button in buttons.items():
                active = self.mode == mode and minutes * 60 == self.total
                button.configure(
                    bg=row_colour if active else CARD,
                    fg=ON_ACCENT if active else FG,
                )

        self.zoom_label.configure(text=f"{int(round(self.scale * 100))}%")
        self.theme_btn.configure(text=self.theme.title())
        for button in self.zoom_buttons:
            button.configure(state="disabled" if self.locked else "normal")
        self.lock_btn.configure(
            text="Locked" if self.locked else "Lock",
            bg=ACCENT_LOCK if self.locked else CARD,
            fg="#ffffff" if self.locked else FG,
            activebackground=ACCENT_LOCK if self.locked else "#2a2e37",
        )
        # One wording at every scale: an adaptive string would change the window's
        # proportions partway through a resize.
        self.status.configure(
            text=f"Sessions completed: {self.sessions_done}"
                 f"    ·    Space = start/pause, R = reset"
        )
        self.root.title(
            f"{fmt(self.remaining)} · {self.mode.title()} — Pomodoro Timer"
        )

    # --------------------------------------------------------- attention
    def alert(self, times=3):
        try:
            if winsound is not None:
                try:
                    winsound.Beep(880, 180)
                except RuntimeError:
                    winsound.MessageBeep()
            else:
                self.root.bell()
            if times > 1:
                self.root.after(260, lambda: self.alert(times - 1))
        except tk.TclError:
            pass  # window closed mid-alert

    def apply_on_top(self):
        """Toggling -topmost can make Tk rebuild the window, so re-hook after it."""
        self.root.attributes("-topmost", self.on_top.get())
        self._sync_aspect()

    def raise_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self._sync_aspect()
        if not self.on_top.get():
            self.root.after(1200, self._drop_topmost)
        self.root.focus_force()

    def _drop_topmost(self):
        self.root.attributes("-topmost", False)
        self._sync_aspect()

    # ----------------------------------------------------------- pop-ups
    def show_break_prompt(self):
        dialog = Popup(
            self.root,
            title="Time's up!",
            heading="Session finished — time for a break.",
            sub=f"You've completed {self.sessions_done} session"
                f"{'s' if self.sessions_done != 1 else ''} so far.",
            accent=ACCENT_BREAK,
            scale=self.scale,
        )
        dialog.add_row(
            "Take a break:",
            [(f"{m} min", lambda m=m: self._begin(m, "break")) for m in BREAK_PRESETS],
            accent=ACCENT_BREAK,
        )
        dialog.add_row(
            "Or start the next session now:",
            [(f"{m} min", lambda m=m: self._begin(m, "work")) for m in WORK_PRESETS],
            accent=ACCENT,
        )
        dialog.add_dismiss("Not now")
        dialog.show()

    def show_next_session_prompt(self):
        dialog = Popup(
            self.root,
            title="Break over",
            heading="Break's over — ready for the next round?",
            sub="Pick how long you want to focus for.",
            accent=ACCENT,
            scale=self.scale,
        )
        dialog.add_row(
            "Next session:",
            [(f"{m} min", lambda m=m: self._begin(m, "work")) for m in WORK_PRESETS],
            accent=ACCENT,
        )
        dialog.add_row(
            "Need a bit longer?",
            [(f"+{m} min break", lambda m=m: self._begin(m, "break"))
             for m in BREAK_PRESETS[:2]],
            accent=ACCENT_BREAK,
        )
        dialog.add_dismiss("Not now")
        dialog.show()

    def _begin(self, minutes, mode):
        self.set_duration(minutes, mode)
        self.start()


class Popup:
    """A small modal dialog built from a heading plus rows of choice buttons."""

    def __init__(self, parent, title, heading, sub, accent, scale=1.0):
        self.parent = parent
        self.scale = scale
        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.configure(bg=BG)
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.protocol("WM_DELETE_WINDOW", self.close)

        px, font = self.px, self.font
        tk.Frame(self.win, bg=accent, height=px(4)).pack(fill="x")
        body = tk.Frame(self.win, bg=BG)
        body.pack(padx=px(26), pady=(px(20), px(6)))

        tk.Label(
            body, text=heading, bg=BG, fg=FG, font=font(14, "bold"),
            wraplength=px(360), justify="left",
        ).pack(anchor="w")
        tk.Label(
            body, text=sub, bg=BG, fg=MUTED, font=font(10),
            wraplength=px(360), justify="left",
        ).pack(anchor="w", pady=(px(4), 0))

        self.body = body

    def px(self, value):
        return scaled(value, self.scale)

    def font(self, size, style="normal"):
        return font_at(size, self.scale, style)

    def add_row(self, label, buttons, accent):
        tk.Label(
            self.body, text=label, bg=BG, fg=MUTED, font=self.font(9, "bold"),
        ).pack(anchor="w", pady=(self.px(16), self.px(6)))
        row = tk.Frame(self.body, bg=BG)
        row.pack(anchor="w")
        for text, action in buttons:
            tk.Button(
                row, text=text, width=11,
                command=lambda a=action: self._choose(a),
                bg=accent, fg=ON_ACCENT, activebackground=accent,
                activeforeground=ON_ACCENT, font=self.font(10, "bold"),
                relief="flat", bd=0, padx=self.px(6), pady=self.px(7),
                cursor="hand2", highlightthickness=0,
            ).pack(side="left", padx=(0, self.px(8)))

    def add_dismiss(self, text):
        tk.Button(
            self.body, text=text, command=self.close,
            bg=BG, fg=MUTED, activebackground=BG, activeforeground=FG,
            font=self.font(9, "underline"), relief="flat", bd=0, cursor="hand2",
            highlightthickness=0,
        ).pack(anchor="w", pady=(self.px(18), self.px(14)))

    def show(self):
        self.win.update_idletasks()
        px, py = self.parent.winfo_rootx(), self.parent.winfo_rooty()
        pw, ph = self.parent.winfo_width(), self.parent.winfo_height()
        w, h = self.win.winfo_width(), self.win.winfo_height()
        self.win.geometry(f"+{px + (pw - w) // 2}+{max(0, py + (ph - h) // 2)}")
        self.win.attributes("-topmost", True)
        self.win.lift()
        self.win.focus_force()
        try:
            self.win.grab_set()
        except tk.TclError:
            pass

    def _choose(self, action):
        self.close()
        action()

    def close(self):
        try:
            self.win.grab_release()
        except tk.TclError:
            pass
        self.win.destroy()


def main():
    root = tk.Tk()
    try:  # crisper rendering on high-DPI Windows displays
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    PomodoroTimer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
