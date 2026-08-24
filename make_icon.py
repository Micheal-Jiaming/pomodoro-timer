"""Regenerate pomodoro_timer.ico - a tomato with a countdown ring.

Everything is drawn at 1024 px and downsampled into the .ico, so the small
sizes Windows actually shows (16/24/32/48 px) stay clean.

Needs Pillow:  py -m pip install pillow
Run with:      py make_icon.py
"""

import math
import os

from PIL import Image, ImageDraw

S = 1024
# These two match the ACCENT and ACCENT_BREAK of the *black* theme only, which
# is DEFAULT_THEME. The paper and mist themes use #cf4a3d and #2f8f5c instead.
# The icon is one static asset baked into the .exe, so it cannot follow a theme
# switch at runtime - it is pinned to the default and that is accepted.
RED = (226, 86, 74, 255)        # black theme ACCENT  (#e2564a), work
GREEN = (63, 166, 108, 255)     # black theme ACCENT_BREAK (#3fa66c), break
# A darker green than GREEN so the stem reads as a separate shape against the
# calyx leaves rather than merging into one green blob at 16 px.
GREEN_DEEP = (44, 130, 82, 255)
WHITE = (255, 255, 255, 255)
# White at ~35% over RED, pre-blended: ImageDraw writes pixels instead of
# alpha-compositing them, so a translucent fill would punch a hole instead.
TRACK = (236, 145, 137, 255)

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Tomato body - slightly wider than tall, which is what reads as "tomato"
# rather than "ball".
BODY = (70, 215, 954, 1000)
cx = (BODY[0] + BODY[2]) / 2
cy = (BODY[1] + BODY[3]) / 2
d.ellipse(BODY, fill=RED)

# Calyx: five leaves radiating from the top, as (angle, length) pairs.
# Each leaf is an isoceles triangle - two base corners either side of `base`,
# apex out at `tip`.
#
# Angles are NEGATIVE to point upward. Image coordinates grow y *downward*, so
# a positive angle would aim a leaf at the ground. The five values fan from
# -176 degrees (pointing left) through -90 (straight up) to -4 (pointing
# right); the outer pair are shorter so the fan tapers at its edges.
base = (512, 250)
for angle, length in [(-176, 205), (-142, 250), (-90, 215), (-38, 250), (-4, 205)]:
    a = math.radians(angle)
    tip = (base[0] + length * math.cos(a), base[1] + length * math.sin(a))
    # Unit vector perpendicular to this leaf's direction, obtained by rotating
    # (cos a, sin a) by 90 degrees. Offsetting `base` along it spreads the two
    # base corners sideways, so every leaf sits square-on to its own axis
    # instead of all five sharing one horizontal base.
    px, py = -math.sin(a), math.cos(a)
    half = 62  # half the base width in px at S=1024, tuned by eye: wider fuses
    #            neighbouring leaves together, narrower vanishes at 16 px.
    d.polygon(
        [
            (base[0] + half * px, base[1] + half * py),
            tip,
            (base[0] - half * px, base[1] - half * py),
        ],
        fill=GREEN,
    )
# The five triangles all meet at `base` but their straight edges leave notches
# between adjacent leaves. This disc covers the seams so the calyx reads as one
# joined shape. It looks redundant and is not - do not remove it.
d.ellipse((base[0] - 70, base[1] - 70, base[0] + 70, base[1] + 70), fill=GREEN)

# Stem: a thick vertical line from just inside the calyx up past the top leaves.
d.line([(512, 255), (512, 110)], fill=GREEN_DEEP, width=76)
# Round cap for the stem. d.line leaves a flat, obviously cut end, so this
# circle of the same 76 px diameter sits on the tip to round it off.
d.ellipse((474, 74, 550, 150), fill=GREEN_DEEP)

# Countdown ring inside the body, mirroring the ring in the app window:
# white for time remaining, pale for time already spent.
#
# The *colours* deliberately do not mirror the app, which draws the accent over
# a dark neutral track. On the red tomato body a dark track would disappear, so
# the icon uses white over pre-blended TRACK instead. Same meaning, different
# palette - the two files have not drifted apart.
#
# R and WIDTH are px at S=1024, sized by eye to sit clear of the body's edge.
R, WIDTH = 252, 86
ring = (cx - R, cy - R, cx + R, cy + R)
# PIL measures arc angles clockwise from 3 o'clock, so -90 is 12 o'clock. The
# two arcs share the boundary at 160 and meet again at 270, which is the same
# point as -90 - that is what closes them into a full circle. The split at 160
# leaves a 110-degree "spent" wedge, roughly 31% elapsed.
d.arc(ring, start=-90, end=160, fill=WHITE, width=WIDTH)
d.arc(ring, start=160, end=270, fill=TRACK, width=WIDTH)

# Write next to this script rather than into the current directory, so the
# result lands beside pomodoro_timer.py however the script was invoked.
target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_timer.ico")
# 256 px is the largest size the ICO format holds, which is the whole reason
# the artwork is drawn at 1024 and downsampled: Pillow resamples from the big
# canvas, so the 16 and 24 px entries stay legible instead of turning to mush.
#
# This OVERWRITES any existing pomodoro_timer.ico with no backup and no
# confirmation. If the file is locked the save raises OSError and nothing is
# written - on Windows that happens when Explorer's icon cache or a running
# packaged .exe still holds a handle, so close those first and re-run.
img.save(
    target,
    format="ICO",
    sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)],
)
print("wrote", target)
