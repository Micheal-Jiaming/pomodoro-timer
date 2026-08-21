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
RED = (226, 86, 74, 255)        # matches the app's work accent
GREEN = (63, 166, 108, 255)     # matches the app's break accent
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
base = (512, 250)
for angle, length in [(-176, 205), (-142, 250), (-90, 215), (-38, 250), (-4, 205)]:
    a = math.radians(angle)
    tip = (base[0] + length * math.cos(a), base[1] + length * math.sin(a))
    px, py = -math.sin(a), math.cos(a)
    half = 62
    d.polygon(
        [
            (base[0] + half * px, base[1] + half * py),
            tip,
            (base[0] - half * px, base[1] - half * py),
        ],
        fill=GREEN,
    )
d.ellipse((base[0] - 70, base[1] - 70, base[0] + 70, base[1] + 70), fill=GREEN)

# Stem
d.line([(512, 255), (512, 110)], fill=GREEN_DEEP, width=76)
d.ellipse((474, 74, 550, 150), fill=GREEN_DEEP)

# Countdown ring inside the body, mirroring the ring in the app window:
# white for time remaining, pale for time already spent.
R, WIDTH = 252, 86
ring = (cx - R, cy - R, cx + R, cy + R)
d.arc(ring, start=-90, end=160, fill=WHITE, width=WIDTH)
d.arc(ring, start=160, end=270, fill=TRACK, width=WIDTH)

target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_timer.ico")
img.save(
    target,
    format="ICO",
    sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)],
)
print("wrote", target)
