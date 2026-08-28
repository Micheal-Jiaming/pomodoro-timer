# Pomodoro Timer

A Pomodoro-style desktop timer for Windows. Pick a work length (15 / 30 / 45 min) or a
break length (5 / 10 / 15 min); when the countdown ends the app beeps, raises itself to
the front, and opens a pop-up that prompts you to take a break and asks which duration
to run next — so the work → break → work cycle continues with one click each time.

Written in Python with Tkinter (standard library only) and packaged as a single
self-contained `.exe`.

## Files

```
D:\claude\Pomodoro timer\
├── pomodoro_timer.py       source (single file, 1104 lines / ~42 KB)
├── pomodoro_timer.ico      app icon — a tomato with a countdown ring
├── make_icon.py            redraws the icon (needs Pillow)
├── build_exe.ps1           rebuild script
├── pomodoro-timer.md       this document
├── README.md               public landing page — see Published downloads
├── LICENSE                 Apache-2.0, matching the Android port
├── VERSION                 current version number — see Version control
├── .gitignore              keeps dist\ and caches out of git
├── .gitattributes          stores every file byte for byte
├── tools\
│   ├── shoot_screenshots.py  regenerates the README's screenshots
│   └── test_shortcuts.py     regression test for the keyboard shortcuts
├── docs\
│   └── screenshots\        the four images README.md embeds
└── dist\
    └── PomodoroTimer.exe   standalone build, ~10 MB — not in git, rebuild it
```

The screenshots are **generated, not taken by hand**. `tools\shoot_screenshots.py`
drives the real `PomodoroTimer` class in-process, setting each theme directly and
capturing the window, so re-shooting them after a UI change is one command:

```powershell
py "D:\claude\Pomodoro timer\tools\shoot_screenshots.py"
```

Two things about it are deliberate and must survive any edit:

- It stubs out `save_settings` and restores `%APPDATA%\PomodoroTimer\settings.json`
  from a backup, because posing the app for a screenshot would otherwise overwrite
  the user's own theme, zoom and window size.
- **Every capture is clipped to one window's bounds.** An earlier version grabbed
  the union of the main window and the prompt centred over it; the two did not
  overlap, so the gap between them captured the desktop behind — wallpaper, icons
  and a personal photo — in an image bound for a public repository. The prompt is
  smaller than the main window in both dimensions, so frame 4 now places it wholly
  inside and grabs the main window's rectangle alone. An assertion refuses to
  capture if the prompt ever escapes those bounds; it fires rather than quietly
  producing a leaky image, and it has already caught one regression.

## Using it

Double-click `dist\PomodoroTimer.exe`. Nothing to install.

**Main window** — a circular ring that depletes as time runs out, the remaining time in
the centre, and two rows of duration presets:

| Row | Options |
| --- | --- |
| **WORK** | 15 min · 30 min · 45 min · Custom |
| **BREAK** | 5 min · 10 min · 15 min · Custom |

Clicking a preset arms that duration; press **Start** to run it. Work mode is red, break
mode is green — the ring, the selected preset, and the Start/Pause button all follow the
mode, and the centre label reads `WORK` or `BREAK`. Below that: **Start / Pause**,
**Reset**, the zoom cluster, the theme button, a completed-session counter, and an
**Always on top** toggle. Remaining time is mirrored in the title bar, so it stays
readable from the taskbar.

**Shortcuts** — `Space` start/pause · `R` reset · `1` `2` `3` work presets ·
`4` `5` `6` break presets · `Ctrl` `+` / `Ctrl` `-` bigger/smaller · `Ctrl` `0` back to
100% · `Ctrl` + mouse wheel to zoom · `Ctrl` `L` lock the size · `Ctrl` `T` next theme.

The letter shortcuts work **whatever the Caps Lock state**, and with Shift held. That is
not automatic — see *Keyboard shortcuts and keysym case* below; it was broken until
1.0.10.

### Backgrounds

Three to choose from. The button at the end of the control row shows the one in use and
moves to the next on each click; `Ctrl` `T` does the same.

| Theme | Background | For |
| --- | --- | --- |
| **Black** (default) | `#15171c` | Night, dark desktops |
| **Paper** | `#f4efe6` | Warm cream with ink-dark text — bright rooms |
| **Mist** | `#eaeef3` | Cool light blue-grey — bright rooms, neutral |

Each theme is a whole palette, not just a background. The two light ones carry their own,
deeper red and green (`#cf4a3d` / `#2f8f5c`) so the white text on the Start button and the
selected preset stays readable; on Black the original brighter pair is used. Work is red
and break is green in all three, and pop-ups follow the current theme.

Every theme uses the same fonts and paddings, so switching changes only colour — the
window keeps its exact size and proportions. The choice is remembered along with the size.

### Window size

The whole interface scales, from **50% to 250%** — useful when it's pinned on top of what
you're working on and you want it out of the way.

Three ways to change it:

- **Drag any window edge or corner.** Pull one side and the other follows in proportion —
  widen the window and it gets taller to match, so the interface scales evenly instead of
  stretching. The corner you aren't holding stays put, and the percentage keeps up as you
  drag.
- **The `−` / `+` buttons** next to Reset, in 10% steps. The percentage between them is a
  button too — click it to snap back to 100%.
- **The keyboard:** `Ctrl` `+`, `Ctrl` `-`, `Ctrl` `0`, or `Ctrl` + mouse wheel.

However you resize it, the window ends up exactly the size the interface needs — no
border of dead space, nothing clipped. Pop-ups follow the current scale too.

At the 50% floor the window is about 308 × 269, roughly a third of the screen area it
takes at 100%. It doesn't shrink further because point sizes are whole numbers and stop
at 6pt: the footer line can't get any narrower and still be text.

### Locking the size

Once it's the size you want, click **Lock** (or press `Ctrl` `L`). The button turns blue
and reads **Locked**, and the size stops moving:

- the window can't be resized — Windows won't even offer the drag handles
- `−`, `+` and the percentage grey out
- `Ctrl` `+`, `Ctrl` `-`, `Ctrl` `0` and `Ctrl` + wheel do nothing

The timer itself is unaffected: presets, Start/Pause, Reset, the shortcuts and the
end-of-session pop-ups all work exactly as before. Click **Locked** to unlock.

The size, the lock and the theme are all remembered in
`%APPDATA%\PomodoroTimer\settings.json` and restored on the next launch — so a locked
window comes back the same size, still locked, in the same colours. Delete that file to
start over from an unlocked 100% in Black; an unrecognised theme name in it falls back to
Black rather than failing to start.

The **icon** — in the taskbar, on the desktop, and in the window title bar — is a red
tomato with a green calyx and stem, wrapped around a white countdown ring that echoes the
ring in the app window: white for time remaining, pale for time already spent. It is
drawn at 1024 px and downsampled into the `.ico`, which carries every size from 256 px
down to 16 px so it stays legible in a crowded taskbar.

**Custom** is per-row: the work button asks for a session length, the break button for a
break length, both 1–180 minutes.

### End of a countdown

Three beeps, the window comes to the front, and a modal pop-up opens.

*After a work session* — "Session finished — time for a break."
- **Take a break:** 5 / 10 / 15 min — starts a green break countdown immediately
- **Or start the next session now:** 15 / 30 / 45 min — skips the break
- **Not now** — dismisses and leaves the timer idle

*After a break* — "Break's over — ready for the next round?"
- **Next session:** 15 / 30 / 45 min
- **Need a bit longer?** +5 / +10 min of extra break
- **Not now**

## Sharing it

Copy `dist\PomodoroTimer.exe` anywhere — Desktop, USB stick, network share — and
double-click. Python, Tkinter, and the icon are bundled inside.

- **Windows 64-bit only.** Not macOS, Linux, or 32-bit Windows.
- **SmartScreen warns once** ("Windows protected your PC") because the exe isn't
  code-signed → **More info → Run anyway**. Only a code-signing certificate removes this;
  zipping does not help.

### Published downloads

The repository is **public** at <https://github.com/Micheal-Jiaming/pomodoro-timer>, and
built executables are attached to GitHub Releases rather than committed — which is how
`dist\` stays ignored while a download still exists for people who won't build from
source. The permanent link to the newest build is:

```
https://github.com/Micheal-Jiaming/pomodoro-timer/releases/latest/download/PomodoroTimer.exe
```

`README.md` is the public landing page: what the app is, the four screenshots, what each
control does, the shortcut table and the SmartScreen warning to expect. It is written for
somebody deciding whether to download the thing. **This document remains the record** —
architecture, reasoning and verification status — and the README links here for it. Keep
the two from drifting: a changed shortcut or preset needs the same edit in both, and the
screenshots need regenerating whenever the interface moves.

It is modelled on the Android port's README, at the user's request, down to the screenshot
table and the Apache-2.0 licence; look there first if the two should stay consistent.

**Publishing a later build.** Bump `VERSION`, commit and tag as usual, rebuild the exe,
then attach it to a new release:

```powershell
gh release create v1.1.0 "dist\PomodoroTimer.exe" --title "Pomodoro Timer v1.1.0" --notes "..."
```

The `releases/latest/download/` URL follows the newest release automatically, so it never
has to be updated anywhere it has been shared.

Note that the released exe tracks the *source* it was built from, and the two numbers
drift apart on purpose. **v1.0.7 is the published binary.** 1.0.8 added this section and
the README; 1.0.9 added the screenshots, the licence and `tools\shoot_screenshots.py`.
Neither touched `pomodoro_timer.py`, so neither needed a rebuild or a release of its own —
publish a new binary only when the source behind it actually changed.

## On Android

There is a port at `D:\claude\Pomodoro timer Android` — Kotlin and Jetpack Compose, same
timer, same three palettes, same end-of-countdown prompts. The built app is at
`Pomodoro timer Android\dist\PomodoroTimer-debug.apk` on this machine — it is not
in version control, so a fresh clone has to build it; drag it onto an emulator, or
`adb install` it. Its `Pomodoro timer Android.md` covers rebuilding.

The timer came across whole, including the drift-free deadline and the three 880 Hz beeps.
The two features that didn't are the window-management ones — **Always on top** and
**window scaling / lock** — because an Android app doesn't own a window it can size or
raise. A *Keep screen on* switch stands in for the first; the layout simply adapts to
whatever window the system gives it in place of the second.

## Rebuilding after a source edit

Requires Python 3 and PyInstaller (`py -m pip install pyinstaller`):

```powershell
powershell -ExecutionPolicy Bypass -File "D:\claude\Pomodoro timer\build_exe.ps1"
```

Build artifacts go to `%TEMP%\pomodorotimer-build`, so only `dist\PomodoroTimer.exe`
changes in the project. The script wraps:

```
py -m PyInstaller --onefile --windowed --clean --noconfirm --name PomodoroTimer
   --icon pomodoro_timer.ico --add-data "pomodoro_timer.ico;." pomodoro_timer.py
```

Running from source still works unchanged: `py pomodoro_timer.py`.

### Changing the icon

Edit the shape, colours, or ring position in `make_icon.py`, then regenerate and rebuild:

```powershell
py "D:\claude\Pomodoro timer\make_icon.py"
powershell -ExecutionPolicy Bypass -File "D:\claude\Pomodoro timer\build_exe.ps1"
```

`make_icon.py` needs Pillow (`py -m pip install pillow`); the app itself does not. Windows
caches icons aggressively, so a replaced exe may keep showing the old picture in Explorer —
renaming the file or logging out refreshes it.

## Version control

This project is its own Git repository, with two remotes:

| Remote | Points at |
|---|---|
| `origin` | `https://github.com/Micheal-Jiaming/pomodoro-timer` — **public** |
| `mirror` | `D:\claude\repos\pomodoro-timer.git` — local bare copy |

The repository name matches this document's filename (`pomodoro-timer`); the
folder keeps its own name because the rebuild commands above refer to it by
absolute path. Authentication is the GitHub CLI acting as git's credential
helper (`gh auth setup-git`), so pushes need no interactive prompt.

Tracked: `pomodoro_timer.py`, `make_icon.py`, `build_exe.ps1`,
`pomodoro_timer.ico`, `tools\shoot_screenshots.py`, `tools\test_shortcuts.py`,
`docs\screenshots\*.png`, `README.md`, `LICENSE`, `VERSION`, `.gitignore`,
`.gitattributes`, and this document. Ignored: `dist\` and `__pycache__\` —
the exe comes back from `build_exe.ps1`, and a stale one cannot do what newer
source does. `.gitattributes` sets `* -text` so every file is stored and checked
out byte for byte; Git for Windows is configured `core.autocrlf=true`
system-wide and would otherwise rewrite these LF files to CRLF.

The Android port is a **separate** repository
(`github.com/Micheal-Jiaming/Pomodoro-timer-Android`, mirrored at
`D:\claude\repos\Pomodoro timer Android.git`); the two version independently.

**Versioning.** `VERSION` holds the current number; every release is tagged
`v<number>`. The baseline was **1.0.0**. This document deliberately does not list
the releases since — `git tag` and `git log VERSION` are the record, and an
enumeration here would be one release stale the moment the next one ships.

| Update | Bump | Example |
|---|---|---|
| Major — new or changed functionality | +0.1 | 1.0.0 → 1.1.0 |
| Minor — fixes, docs, small tweaks | +0.0.1 | 1.0.0 → 1.0.1 |

**One bump per task, however many commits it takes** — not one per commit. A
task that edits code and then updates this document is a single version; write
the new number into `VERSION` in the task's last commit and tag there. Documented
changes are never exempt: this file is what a later session works from, so a
wrong line in it is a defect like any other. The rule is deliberately mechanical,
because a rule needing judgement gets applied differently by every session.

Then tag and push both remotes:

```powershell
git -C "D:\claude\Pomodoro timer" commit -am "..."
git -C "D:\claude\Pomodoro timer" tag -a v$(cat VERSION) -m "..."
git -C "D:\claude\Pomodoro timer" push origin main --tags
git -C "D:\claude\Pomodoro timer" push mirror main --tags
```

## Implementation notes

- **No clock drift.** The countdown is derived from a `time.monotonic()` deadline rather
  than by decrementing a counter on each tick, so a 45-minute session stays accurate. The
  UI refreshes every 200 ms; pausing stores the remaining time, resuming sets a new
  deadline.
- **Pop-ups surface reliably.** Each is a `Toplevel` with `grab_set` + `-topmost` +
  `focus_force`, centred on the main window, so it appears above whatever you're working
  in. The main window is also briefly raised and (if "Always on top" is off) released
  again after ~1.2 s.
- **Icon path works both ways.** `resource_path()` checks PyInstaller's `sys._MEIPASS`
  unpack directory and falls back to the script's own folder, so the icon loads whether
  the app runs frozen or from source. A missing icon is caught and ignored — it's
  cosmetic.
- **Pre-blended icon colours.** `ImageDraw` writes pixels rather than alpha-compositing
  them, so the ring's pale "spent" arc is an opaque blend of white over red. A translucent
  fill would punch a see-through hole in the tomato instead.
- **Sound** is three 880 Hz `winsound.Beep` calls, falling back to `MessageBeep` and then
  to the Tk bell on non-Windows platforms.
- **Scaling rebuilds rather than stretches.** Every widget is laid out at 100% and passed
  through `self.px()` (pixels) and `self.font()` (point sizes); changing the scale
  destroys the container frame and lays the same widgets out again at the new factor.
  Timer state lives on the instance, so a rebuild mid-countdown is invisible. Button
  widths stay in character units — they follow the font for free.
- **The 100% size is measured, not hard-coded.** The first build runs at 1.0 and its
  requested size becomes the reference (`_base_w` / `_base_h`) that both the drag handler
  and `minsize` work from, so layout edits don't need any constant updated.
- **Resize handling is debounced** 120 ms after the last `<Configure>`, and a rebuild is
  skipped unless the scale moved by more than 0.03 — that keeps a rebuild from feeding
  itself new resize events. A programmatic resize also cancels any drag still queued
  against the window it is about to replace.
- **Proportional dragging is enforced in the window procedure.** Tk accepts `wm aspect`
  but never applies it on Windows — it stores the numbers and ignores them — so
  `AspectLock` subclasses the window with `SetWindowLongPtrW` and rewrites the rectangle
  carried by `WM_SIZING`, the message the drag loop sends before each resize. Dragging one
  side then moves the other live, with no snapping after the fact. Side drags take their
  height from the width, top/bottom drags take their width from the height, and only the
  edges the user isn't holding are moved, so the anchored corner stays put.
- **The `WM_SIZING` branch validates its input before writing** (added in 1.0.5). That
  message carries a `RECT*` in its `lparam`, and the handler writes four `LONG`s back
  through it — so it is one of the few places in this app that writes to an address it
  did not compute. Any process able to `SendMessage` to the window could otherwise place
  those writes. Two gates now stand in front of it: the edge code must be a real `WMSZ_*`
  value (1–8, `EDGE_VALID`), and `_plausible()` must accept the rectangle — non-degenerate
  and inside the virtual desktop plus 4096 px of slack, generous enough that a legitimate
  drag well off-screen still passes. A rectangle that fails is refused outright rather
  than clamped, because a wrong pointer is a forged message or a bug, not a small
  numerical error. This is defence in depth, not a remotely reachable hole: sending the
  message at all requires a same-session process at equal or higher integrity, which is
  an attacker who could edit this source file anyway.
- **The hooked window is not the one Tk starts with.** A toplevel's real window is created
  when it is mapped, and Tk throws it away and rebuilds it for some `wm` calls —
  `-topmost`, which this app toggles, among them. `attach()` re-subclasses whenever the
  handle has changed, and is called on `<Map>`, on every rebuild, and after each
  always-on-top change. Hooking once in `__init__` silently attaches to a window that
  never appears.
- **The scale is inferred relative to the layout on screen**, not to the 100% size:
  `scale × min(width / reqwidth, height / reqheight)`. Point sizes are whole numbers, so
  the natural size isn't quite linear in the scale and measuring against the base would
  make a window that already fits report a different scale and jump. Relative, a fitted
  window infers exactly its own scale.
- **The inference can overshoot, so it is checked.** A scale can round up into needing
  more room than the drag allowed, which clips the edges; `_shrink_to_fit()` trims until
  the layout fits. Afterwards `_snap_when_idle()` pulls the window in to exactly the
  layout size — but not while `GetAsyncKeyState` says the mouse button is still down,
  since resizing a window mid-drag fights the person doing the dragging.
- **Nothing about the footer changes with scale.** An adaptive string (it used to shorten
  below 85%) makes the natural width non-proportional, so the window would change shape
  partway through a resize.
- **Moves are told apart from resizes** by comparing against `_last_size`; `<Configure>`
  fires for a move too, and without that check the app would resize itself when dragged
  across the desk.
- **Startup transients are ignored.** Mapping a window emits junk sizes — 200×200, then
  120×1 — before it settles. `_ignore_configure` covers the first 600 ms, and any size
  below `minsize` is rejected outright, since the window manager would never let a real
  drag land there. Without both, a slow start (the frozen exe) let the 120 ms debounce
  expire mid-transient and the app opened at 50%.
- **`minsize` is measured, not derived.** Halving the 100% size would understate it: the
  6pt floor on font sizes means the layout at 50% is wider than half the layout at 100%.
  The startup measurement builds the UI at `SCALE_MIN` once to find out.
- **A window the app resizes itself is recognised by size, not by a timer.** `_fit_window`
  records the geometry it asks for, and the matching `<Configure>` is skipped on the way
  in. A timed blackout instead of this swallowed drags that both started and finished
  inside the window, leaving the layout at a size nobody chose.
- **Locking** sets `wm resizable 0 0` (the window manager then refuses to resize at all),
  disables the zoom buttons and makes `set_scale()` a no-op unless called with
  `force=True`, which is how the saved size is restored at startup.
- **Themes are whole palettes swapped at module level.** `apply_theme()` rebinds the
  colour names in `globals()` and the app then rebuilds every widget, the same machinery
  scaling uses, so nothing is left holding a colour from the previous theme. Hover and
  "text on accent" colours belong to the theme too — hard-coding them is what makes a
  light theme look half-finished.
- **Settings** are a single JSON file in `%APPDATA%\PomodoroTimer`, written 700 ms after
  the last change so a drag doesn't hammer the disk, and flushed on `<Destroy>` if a write
  is still pending. Any I/O error is swallowed.
- **Pending `after` jobs are cancelled on close.** Closing the window inside one of the
  debounce windows otherwise leaves callbacks firing at a dead interpreter.
- The main class is `PomodoroTimer`; `Popup` builds the end-of-countdown dialogs and
  `AspectLock` holds the window to its proportions while it is being dragged.
- Built and tested with Python 3.13 and PyInstaller 6.21 on Windows 11.

### Keyboard shortcuts and keysym case

Tk matches keysyms **literally**. `root.bind("<Control-t>", ...)` fires for keysym `t`
and for nothing else, so when Caps Lock is on — or Shift is held — the OS delivers `T`,
no binding matches, and the shortcut does nothing at all. There is no error and no
warning; the key simply stops working, which makes it a genuinely hard fault to
diagnose from the outside.

Until 1.0.10 that silently disabled `Ctrl` `T`, `Ctrl` `L` and `R` for anyone typing
with Caps Lock on. It was reported as "Ctrl+L and Ctrl+T don't work", and reproduced by
sending real OS keystrokes with Caps Lock toggled: both worked with it off, both were
dead with it on. Note the failure is invisible to `event_generate("<Control-t>")` in a
test, because that names the keysym directly and so always matches — the bug only
appears through the real keyboard, or by generating the upper-case keysym deliberately.

`PomodoroTimer._bind` now binds both cases. It takes the part of the sequence after the
last `-`, and if that is a single letter it registers the upper-case twin as well.
Sequences whose final component is not a single letter — `<space>`, `<Control-0>`,
`<Control-KP_Add>` — are bound once and untouched; the `rpartition("-")` split is what
keeps `<space>` from being mangled into `<spacE>`, and `tools\test_shortcuts.py` asserts
exactly that alongside the rest.

Digits are unaffected by Caps Lock, so the preset keys `1`–`6` were never broken.

**Run the regression test after touching `_bind` or `_bind_keys`:**

```powershell
py "D:\claude\Pomodoro timer\tools\test_shortcuts.py"
```

It fails 6 of its checks against the pre-1.0.10 code and passes on the fix, so it is
guarding the real defect rather than merely restating the implementation.

## Verification status

Where **1.0.10** stands, so a later session knows what it can rely on and what it
should re-check rather than assume.

**Verified in 1.0.10.**

- `Ctrl` `T`, `Ctrl` `L` and `R` fire with Caps Lock on, with it off, and with Shift
  held. Checked by sending real OS keystrokes to a focused window and reading
  `app.theme` / `app.locked` directly, not by inferring from pixels.
- `tools\test_shortcuts.py` passes on the fix and fails 6 checks against the code
  before it, so it genuinely covers the defect.
- **The shipped `dist\PomodoroTimer.exe` was rebuilt and retested**, not just the
  source: with Caps Lock switched on before launch, Ctrl+T, Ctrl+L, Ctrl+L again and
  Ctrl+T all changed the window, and lock-then-unlock returned it to a byte-identical
  screenshot. That check compares screenshots rather than reading the object, because
  the exe is a separate process.

  Two traps if this is ever re-run. Windows refuses `SetForegroundWindow` to a process
  that is not already in the foreground, so keystrokes silently go to whatever window
  *is* focused and every result comes back meaningless — focus the window with a real
  mouse click on its title bar and assert `GetForegroundWindow` before sending keys.
  And **the toplevel HWND does not survive a lock toggle**: changing `resizable` makes
  Tk rebuild the window, so a cached handle goes stale and `GetWindowRect` starts
  returning zeros. That looks exactly like the app having crashed, and it briefly did;
  re-find the window after every keystroke rather than caching it.
- `tools\shoot_screenshots.py` regenerates all four README images, and its containment
  assertion fires rather than capturing desktop when the prompt is mispositioned — it
  caught exactly that during development.

Older notes, from 1.0.5, follow.

**Verified.**

- Both source files compile (`py -m py_compile`).
- `make_icon.py` runs and writes an `.ico` **byte-identical** to the previous one, which
  is what proves that release's edits to it were comments only.
- `_plausible()` and the `EDGE_VALID` gate pass a 13-case unit test: legitimate drag
  rectangles are accepted — including ones pushed well off-screen — while degenerate,
  inverted and far-out-of-range rectangles are refused. `_constrain()` still produces the
  target ratio, so the aspect maths itself is unchanged.
- `build_exe.ps1` rebuilds cleanly. The resulting standalone build is ~10 MB, and it
  launches and stays running.
- **Interactive dragging still works** — confirmed by hand on Windows 11 after the
  change. This is the check that matters for this release, because the new validation
  sits directly in the resize path: a unit test can say the rectangles are accepted, but
  only a real drag proves the aspect lock still holds the window in proportion.

**Not verified — check these by hand before trusting them.**

- Multi-monitor drags, and dragging onto a monitor with a different DPI, are untested
  against the new bounds check. The slack around the virtual desktop is 4096 px, which
  should absorb both, but that is reasoning rather than evidence.
- The rebuilt exe was launched and closed, not exercised: no countdown was run to
  completion, no theme switched, no size lock toggled in this build.

The previous hand-verified binary (v1.0.4) is **not** recoverable from Git, because
`dist\` is deliberately ignored. If the new build misbehaves, rebuild from tag `v1.0.4`
rather than expecting a checkout to restore the exe.
