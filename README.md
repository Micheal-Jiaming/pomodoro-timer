# Pomodoro Timer

A Pomodoro-style desktop timer for Windows. Pick a work length (15 / 30 / 45 min) or a
break length (5 / 10 / 15 min); when the countdown ends the app beeps, raises itself to
the front, and asks which duration to run next — so the work → break → work cycle
continues with one click each time.

Python and Tkinter, standard library only, packaged as a single self-contained `.exe`.

## Download

**[Download PomodoroTimer.exe](https://github.com/Micheal-Jiaming/pomodoro-timer/releases/latest/download/PomodoroTimer.exe)** — 10 MB, Windows 64-bit, no installer.

Double-click it and it runs. Nothing to install, nothing left behind.

On first launch Windows shows *"Windows protected your PC"* because the executable is
not code-signed — click **More info → Run anyway**. This is expected for any unsigned
independent build.

## Features

- **Drift-free countdown** — anchored to a deadline rather than accumulated ticks, so it
  stays accurate across a long session.
- **Three themes** — Black, Paper and Mist. Each is a full palette, not just a
  background, and switching changes colour only; the window keeps its exact size.
- **Scalable window** — zoom the whole UI, or lock the aspect ratio while drag-resizing.
- **Always on top**, a completed-session counter, and the remaining time mirrored in the
  title bar so it is readable straight from the taskbar.

### Shortcuts

| Key | Action |
| --- | --- |
| `Space` | Start / pause |
| `R` | Reset |
| `1` `2` `3` | Work presets — 15 / 30 / 45 min |
| `4` `5` `6` | Break presets — 5 / 10 / 15 min |
| `Ctrl` `+` / `Ctrl` `-` | Zoom in / out (`Ctrl` + wheel also works) |
| `Ctrl` `0` | Back to 100% |
| `Ctrl` `L` | Lock the window size |
| `Ctrl` `T` | Next theme |

## Running from source

Requires Python 3 and nothing else:

```
py pomodoro_timer.py
```

To rebuild the executable yourself, install PyInstaller (`py -m pip install pyinstaller`)
and run:

```
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

The built `.exe` is deliberately not tracked in Git — it is reproducible from source, and
released builds are attached to the [Releases](https://github.com/Micheal-Jiaming/pomodoro-timer/releases) page instead.

## Documentation

[**pomodoro-timer.md**](pomodoro-timer.md) is the full project document — how each feature
works, the implementation notes behind the countdown and the window-scaling maths, the
version history, and what has and has not been hand-verified in the current build.

## Android

A Kotlin / Jetpack Compose port lives in a separate project — same timer, same three
palettes, same end-of-countdown prompts.
