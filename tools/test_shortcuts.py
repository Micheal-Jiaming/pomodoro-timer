r"""Regression test for the keyboard shortcuts.

Run:  py "D:\claude\Pomodoro timer\tools\test_shortcuts.py"

Guards the Caps Lock bug: Tk matches keysyms literally, so a shortcut bound only
as `<Control-t>` never fires when Caps Lock or a held Shift delivers `T`, and it
fails silently -- no error, no clue. Ctrl+T and Ctrl+L were both dead for anyone
typing with Caps Lock on, and R was too.

Rather than driving the real keyboard, the upper-case keysym is generated
directly, which is exactly what the OS delivers in that state. That keeps the
test fast and independent of window focus.
"""
import os
import shutil
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pomodoro_timer as pt

LETTER_SHORTCUTS = ("<r>", "<Control-l>", "<Control-t>")
failures = []


def check(condition, message):
    print(("  ok   " if condition else "  FAIL ") + message)
    if not condition:
        failures.append(message)


def main():
    backup = None
    if os.path.exists(pt.SETTINGS_PATH):
        backup = pt.SETTINGS_PATH + ".testbak"
        shutil.copy2(pt.SETTINGS_PATH, backup)
    pt.save_settings = lambda *args, **kwargs: None   # never touch real settings

    root = tk.Tk()
    app = pt.PomodoroTimer(root)
    root.update()

    # event_generate delivers key events to the focused widget, so without this
    # the functional checks below fail wherever the window happens not to have
    # focus -- which is the normal case when the test is run from a terminal.
    # Reporting a broken shortcut because the test window was in the background
    # is worse than not testing at all, so take focus explicitly and say so if
    # it cannot be taken, rather than letting it look like a real failure.
    root.deiconify()
    root.lift()
    root.focus_force()
    root.update()
    focused = root.focus_displayof() is not None

    print("both cases are bound for every letter shortcut:")
    for seq in LETTER_SHORTCUTS:
        upper = seq[:-2] + seq[-2].upper() + ">"
        check(bool(root.bind(seq)), f"{seq} is bound")
        check(bool(root.bind(upper)), f"{upper} is bound (Caps Lock / Shift)")

    print("\nnon-letter shortcuts are unaffected and still bound once:")
    for seq in ("<space>", "<Control-0>", "<Control-KP_Add>"):
        check(bool(root.bind(seq)), f"{seq} is bound")
    check(not root.bind("<spacE>"), "<space> was not mangled into <spacE>")

    print("\nthe upper-case keysym actually triggers the action:")
    if not focused:
        print("  SKIP  window could not take focus; key events cannot be delivered")
        failures.append("could not focus the test window")
    before = app.theme
    root.event_generate("<Control-T>")
    root.update()
    check(app.theme != before, f"Ctrl+Shift+T / Caps Lock changed theme ({before} -> {app.theme})")

    before = app.locked
    root.event_generate("<Control-L>")
    root.update()
    check(app.locked != before, f"Ctrl+Shift+L / Caps Lock toggled lock ({before} -> {app.locked})")

    app.set_duration(30, "work")
    app.start()
    root.update()
    root.event_generate("<R>")
    root.update()
    check(not app.running, "R with Caps Lock on still resets")

    root.destroy()
    if backup:
        shutil.copy2(backup, pt.SETTINGS_PATH)
        os.remove(backup)

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s)")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
