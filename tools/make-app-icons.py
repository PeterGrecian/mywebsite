#!/usr/bin/env python3
"""Draw the per-section home-screen app icons: a letter with the red tick
underneath, the family mark shared with the main site's favicon.

Content sits inside the central 80% so the 512 doubles as the maskable icon.
Writes lambda/app-<name>-192.png and -512.png (deploy zips lambda/*.png).
Usage: tools/make-app-icons.py [outdir]
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

APPS = {                      # name: (letter, letter colour); '' = tick only
    'site':      ('', None),     # the main site: just the red tick, larger
    'astro':     ('A', '#8EA6FF'),
    'groceries': ('G', '#7DDC8A'),
    'pi-fleet':  ('P', '#FFB27A'),
    'ytpods':    ('V', '#F2E6CC'),
}
BG, TICK = '#000000', '#FF3B30'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def draw(letter, colour, size=512, ss=4):
    S = size * ss
    im = Image.new('RGB', (S, S), BG)
    d = ImageDraw.Draw(im)
    # Tick: the favicon's path M8 20 L16 28 L32 10 in a 40-unit box,
    # scaled to sit under the letter, inside the 80% safe zone.
    if letter:
        font = ImageFont.truetype(FONT, int(S * 0.42))
        l, t, r, b = d.textbbox((0, 0), letter, font=font)
        w, h = r - l, b - t
        top = S * 0.13                               # letter block top
        d.text(((S - w) / 2 - l, top - t), letter, font=font, fill=colour)
        tw = S * 0.34
        k = tw / 24                                  # path spans x 8..32
        ox, oy = (S - tw) / 2 - 8 * k, top + h + S * 0.11 - 10 * k
    else:                                            # tick alone, centred
        tw = S * 0.44
        k = tw / 24
        ox, oy = (S - tw) / 2 - 8 * k, S / 2 - 19 * k   # path spans y 10..28
    pts = [(ox + x * k, oy + y * k) for x, y in ((8, 20), (16, 28), (32, 10))]
    width = int(5 * k)
    d.line(pts, fill=TICK, width=width, joint='curve')
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=TICK)
    return im.resize((size, size), Image.LANCZOS)


out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'lambda')
for name, (letter, colour) in APPS.items():
    big = draw(letter, colour)
    big.save(os.path.join(out, f'app-{name}-512.png'), optimize=True)
    big.resize((192, 192), Image.LANCZOS).save(os.path.join(out, f'app-{name}-192.png'), optimize=True)
    print(name)
