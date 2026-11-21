#!/usr/bin/env python3
"""Valdoria passport spread generator.

Draws, pixel by pixel with only the Python standard library, the open
passport spread of the Republic of Valdoria - an invented Adriatic island
republic - and writes it to /output/entry.png (1024x640, under 1 MiB).

No network, no randomness, no time: two runs are byte-identical.
"""
import math
import os
import struct
import zlib

W, H = 1024, 640
OUT_PATH = "/output/entry.png"

# ---------------------------------------------------------------- font: 5x7
# Each glyph: 7 rows of 5 bits, '#' = ink.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    '<': ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    '>': ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '=': ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '*': ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '#': ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
}


def text_width(text, scale):
    return len(text) * 6 * scale - scale


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(w * h):
            self.px[i * 3] = r
            self.px[i * 3 + 1] = g
            self.px[i * 3 + 2] = b

    def set(self, x, y, color, alpha=255):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            if alpha >= 255:
                self.px[i], self.px[i + 1], self.px[i + 2] = color
            else:
                a = alpha / 255.0
                self.px[i] = int(color[0] * a + self.px[i] * (1 - a))
                self.px[i + 1] = int(color[1] * a + self.px[i + 1] * (1 - a))
                self.px[i + 2] = int(color[2] * a + self.px[i + 2] * (1 - a))

    def fill_rect(self, x0, y0, x1, y1, color, alpha=255):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.set(x, y, color, alpha)

    def hline(self, x0, x1, y, color, alpha=255, thick=1):
        for t in range(thick):
            for x in range(x0, x1 + 1):
                self.set(x, y + t, color, alpha)

    def vline(self, x, y0, y1, color, alpha=255, thick=1):
        for t in range(thick):
            for y in range(y0, y1 + 1):
                self.set(x + t, y, color, alpha)

    def line(self, x0, y0, x1, y1, color, alpha=255, thick=1):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            for t in range(thick):
                self.set(x, y + t, color, alpha)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def rect(self, x0, y0, x1, y1, color, alpha=255, thick=1):
        self.hline(x0, x1, y0, color, alpha, thick)
        self.hline(x0, x1, y1 - thick + 1, color, alpha, thick)
        self.vline(x0, y0, y1, color, alpha, thick)
        self.vline(x1 - thick + 1, y0, y1, color, alpha, thick)

    def ellipse(self, cx, cy, rx, ry, color, alpha=255, fill=True):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                v = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if fill:
                    if v <= 1.0:
                        self.set(x, y, color, alpha)
                else:
                    if 0.92 <= v <= 1.0:
                        self.set(x, y, color, alpha)

    def circle(self, cx, cy, r, color, alpha=255, fill=True):
        self.ellipse(cx, cy, r, r, color, alpha, fill)

    def poly(self, pts, color, alpha=255, fill=True):
        if fill:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            for y in range(min(ys), max(ys) + 1):
                xs_at = []
                for i in range(len(pts)):
                    x0, y0 = pts[i]
                    x1, y1 = pts[(i + 1) % len(pts)]
                    if (y0 <= y < y1) or (y1 <= y < y0):
                        xs_at.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
                xs_at.sort()
                for j in range(0, len(xs_at) - 1, 2):
                    for x in range(int(xs_at[j]), int(xs_at[j + 1]) + 1):
                        self.set(x, y, color, alpha)
        else:
            for i in range(len(pts)):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % len(pts)]
                self.line(x0, y0, x1, y1, color, alpha)

    def text(self, x, y, s, text, color, alpha=255, spacing=1):
        """Draw uppercase 5x7 text; x,y = top-left of first glyph."""
        cx = x
        for ch in text.upper():
            glyph = FONT.get(ch)
            if glyph is None:
                cx += 6 * s
                continue
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == '1':
                        for dy in range(s):
                            for dx in range(s):
                                self.set(cx + col * s + dx, y + row * s + dy, color, alpha)
            cx += (5 + spacing) * s

    def text_center(self, cx, y, s, text, color, alpha=255):
        self.text(cx - text_width(text, s) // 2, y, s, text, color, alpha)


def wrap_text(text, scale, max_w):
    words = text.split(' ')
    lines, cur = [], ''
    for wd in words:
        trial = (cur + ' ' + wd).strip()
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def rotate_blit(dst, src, cx, cy, angle_deg, alpha=255, worn=False):
    """Blit src canvas onto dst, rotated angle_deg about src centre, placed
    so the src centre lands at (cx, cy). Nearest neighbour, deterministic."""
    th = math.radians(angle_deg)
    cos_t, sin_t = math.cos(th), math.sin(th)
    scx, scy = src.w / 2.0, src.h / 2.0
    for y in range(src.h):
        for x in range(src.w):
            i = (y * src.w + x) * 3
            r, g, b = src.px[i], src.px[i + 1], src.px[i + 2]
            if (r, g, b) == (255, 0, 255):
                continue  # magenta = transparent
            dx, dy = x - scx, y - scy
            rx = int(round(cx + dx * cos_t - dy * sin_t))
            ry = int(round(cy + dx * sin_t + dy * cos_t))
            a = alpha
            if worn:
                if ((rx * 73 + ry * 149) % 256) < 42:
                    continue
                a = int(alpha * 0.85)
            dst.set(rx, ry, (r, g, b), a)


def star(dst, cx, cy, r_out, r_in, points, color, alpha=255):
    pts = []
    for i in range(points * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi * i / points - math.pi / 2
        pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
    dst.poly(pts, color, alpha)


# ---------------------------------------------------------------- PNG writer
def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        c = struct.pack('>I', len(data)) + kind + data
        c += struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack('>IIBBBBB', cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', comp) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- MRZ (ICAO 9303)
def mrz_check(text):
    vals = {}
    for i, c in enumerate('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
        vals[c] = i if i < 10 else i - 10 + 10
    vals['<'] = 0
    total = 0
    for i, ch in enumerate(text):
        total += vals[ch] * (7, 3, 1)[i % 3]
    return str(total % 10)


def mrz_lines():
    doc = 'VLD483920'
    line1 = ('P<VLDVOSS<<ELENA<MARA' + '<' * 44)[:44]
    dob = '960312' + mrz_check('960312')
    exp = '340313' + mrz_check('340313')
    personal = ('<' * 14)
    core = doc + mrz_check(doc) + 'VLD' + dob + 'F' + exp + personal + '<'
    line2 = core + mrz_check(core)
    return line1, line2


# ---------------------------------------------------------------- portrait
def draw_portrait(cv, x0, y0, x1, y1):
    """Stylised head-and-shoulders portrait of Elena Mara Voss, 28,
    harbour pilot of Velmara: dark hair in a low knot, navy jacket with
    the gold anchor pin of the Valdorian harbour service."""
    cx = (x0 + x1) // 2
    # studio backdrop: soft vertical bands
    for x in range(x0, x1):
        t = (x - x0) / max(1, (x1 - x0))
        shade = int(168 - 42 * t)
        cv.fill_rect(x, y0, x + 1, y1, (shade, shade + 12, shade + 16))
    for yy in range(y0 + 8, y1, 26):
        cv.line(x0, yy, x1, yy + 18, (140, 152, 158), alpha=26)
    # shoulders / jacket
    cv.poly([(cx - 78, y1), (cx - 62, y1 - 78), (cx - 26, y1 - 96),
             (cx + 26, y1 - 96), (cx + 62, y1 - 78), (cx + 78, y1)],
            (38, 54, 78))
    # shirt V + collar
    cv.poly([(cx - 22, y1 - 94), (cx, y1 - 58), (cx + 22, y1 - 94)], (238, 236, 228))
    cv.poly([(cx - 24, y1 - 96), (cx, y1 - 66), (cx - 6, y1 - 96)], (250, 248, 240))
    cv.poly([(cx + 24, y1 - 96), (cx, y1 - 66), (cx + 6, y1 - 96)], (250, 248, 240))
    # gold anchor pin on the lapel
    cv.circle(cx - 44, y1 - 62, 5, (196, 158, 74))
    cv.circle(cx - 44, y1 - 62, 2, (38, 54, 78))
    # neck
    cv.fill_rect(cx - 15, y1 - 128, cx + 15, y1 - 92, (206, 158, 122))
    cv.fill_rect(cx - 15, y1 - 128, cx + 15, y1 - 118, (186, 138, 104))
    # ears
    cv.ellipse(cx - 52, y1 - 168, 8, 13, (206, 158, 122))
    cv.ellipse(cx + 52, y1 - 168, 8, 13, (206, 158, 122))
    # hair back mass (low knot visible at the sides)
    cv.ellipse(cx, y1 - 178, 52, 68, (58, 40, 28))
    # face
    cv.ellipse(cx, y1 - 172, 50, 62, (217, 169, 132))
    # hair cap: swept fringe
    cv.ellipse(cx, y1 - 214, 52, 40, (58, 40, 28))
    cv.poly([(cx - 52, y1 - 216), (cx - 30, y1 - 186), (cx - 8, y1 - 212),
             (cx + 14, y1 - 188), (cx + 34, y1 - 210), (cx + 52, y1 - 216),
             (cx + 52, y1 - 236), (cx - 52, y1 - 236)], (58, 40, 28))
    # brows, eyes, nose, mouth
    cv.line(cx - 34, y1 - 182, cx - 14, y1 - 184, (74, 52, 36), thick=2)
    cv.line(cx + 14, y1 - 184, cx + 34, y1 - 182, (74, 52, 36), thick=2)
    cv.ellipse(cx - 24, y1 - 174, 7, 4, (42, 30, 22))
    cv.ellipse(cx + 24, y1 - 174, 7, 4, (42, 30, 22))
    cv.line(cx, y1 - 172, cx - 2, y1 - 150, (186, 138, 104), thick=2)
    cv.line(cx - 12, y1 - 138, cx + 12, y1 - 138, (150, 92, 74), thick=2)
    # cheek shading
    cv.ellipse(cx - 34, y1 - 152, 9, 5, (222, 178, 142), alpha=120)
    cv.ellipse(cx + 34, y1 - 152, 9, 5, (222, 178, 142), alpha=120)
    # faint guilloche over the photo, as on a real data page
    for k in range(0, (x1 - x0), 12):
        cv.line(x0 + k, y0, x0 + k + 26, y1, (255, 255, 255), alpha=10)


# ---------------------------------------------------------------- coat of arms
def draw_arms(cv, cx, top, scale=1):
    """Shield of Valdoria: gold eight-point star over three sea waves,
    topped by a small crown."""
    w, h = 46 * scale, 56 * scale
    x0, y0 = cx - w // 2, top
    # crown
    cv.poly([(x0 + 12, y0 + 10), (x0 + 16, y0 + 2), (x0 + 20, y0 + 8),
             (x0 + 23, y0 + 1), (x0 + 26, y0 + 8), (x0 + 30, y0 + 2),
             (x0 + 34, y0 + 10)], (196, 158, 74))
    # shield
    pts = [(x0 + 4, y0 + 12), (x0 + 42, y0 + 12), (x0 + 42, y0 + 36),
           (x0 + 23, y0 + 54), (x0 + 4, y0 + 36)]
    cv.poly(pts, (31, 58, 95))
    cv.poly(pts, (196, 158, 74), fill=False)
    # waves
    for wy in (y0 + 38, y0 + 43):
        for xx in range(x0 + 6, x0 + 40, 8):
            cv.line(xx, wy, xx + 4, wy - 2, (196, 158, 74))
            cv.line(xx + 4, wy - 2, xx + 8, wy, (196, 158, 74))
    # eight-point star
    star(cv, cx, y0 + 24, 10, 4, 8, (196, 158, 74))
    cv.circle(cx, y0 + 24, 2, (31, 58, 95))


# ---------------------------------------------------------------- stamps
def round_stamp(text_lines, r, color, sub=None):
    """A round ink stamp on a magenta-transparent canvas."""
    size = r * 2 + 24
    cv = Canvas(size, size, (255, 0, 255))
    c = size // 2
    cv.circle(c, c, r, color, alpha=225)
    cv.circle(c, c, r - 7, color, alpha=225)
    cv.circle(c, c, r - 7, (255, 0, 255), alpha=255)  # knock out middle ring? no
    # redraw inner ring properly: outer disc outline only
    cv.circle(c, c, r, color, alpha=225, fill=False)
    cv.circle(c, c, r - 7, color, alpha=225, fill=False)
    y = c - (len(text_lines) * 15) // 2 + 4
    for ln in text_lines:
        cv.text_center(c, y, 2, ln, color, alpha=235)
        y += 16
    if sub:
        cv.text_center(c, y + 2, 1, sub, color, alpha=220)
    return cv


def oval_stamp(text_lines, rx, ry, color):
    size_x, size_y = rx * 2 + 24, ry * 2 + 24
    cv = Canvas(size_x, size_y, (255, 0, 255))
    cx, cy = size_x // 2, size_y // 2
    cv.ellipse(cx, cy, rx, ry, color, alpha=225, fill=False)
    cv.ellipse(cx, cy, rx - 7, ry - 7, color, alpha=225, fill=False)
    y = cy - (len(text_lines) * 15) // 2 + 4
    for ln in text_lines:
        cv.text_center(cx, y, 2, ln, color, alpha=235)
        y += 16
    return cv


def rect_stamp(lines, w, h, color):
    cv = Canvas(w + 16, h + 16, (255, 0, 255))
    cv.rect(6, 6, w + 9, h + 9, color, alpha=225, thick=3)
    cv.rect(11, 11, w + 4, h + 4, color, alpha=200, thick=1)
    y = 16
    for ln, s in lines:
        cv.text_center((w + 16) // 2, y, s, ln, color, alpha=235)
        y += 9 * s + 4
    return cv



# ---------------------------------------------------------------- palette
PAPER = (244, 236, 217)
PAPER_DARK = (238, 228, 204)
INK = (31, 58, 95)          # passport navy
GOLD = (176, 138, 58)
GOLD_LT = (196, 158, 74)
GREY = (96, 96, 96)
STAMP_BLUE = (42, 77, 143)
STAMP_PURPLE = (104, 62, 128)
STAMP_RED = (146, 58, 44)
STAMP_GREEN = (46, 110, 92)


def guilloche(cv):
    # faint security waves across the whole spread
    for y0 in range(24, H - 16, 16):
        for x in range(16, W - 16):
            y = y0 + int(2.2 * math.sin((x + y0 * 3) * 0.045))
            cv.set(x, y, (214, 196, 158), alpha=46)
    # faint island watermark on the right page: Valdoria + compass rose
    star(cv, 780, 330, 92, 34, 8, (214, 196, 158), alpha=26)
    cv.circle(780, 330, 30, (214, 196, 158), alpha=26, fill=False)
    # coastline of the island, very faint
    coast = [(640, 470), (700, 430), (760, 452), (820, 420), (880, 448),
             (930, 420), (960, 460), (920, 500), (850, 520), (780, 500),
             (700, 520), (650, 500)]
    cv.poly(coast, (150, 170, 190), alpha=40, fill=False)


def field(cv, x, y, label, value, w, vscale=2):
    cv.text(x, y, 1, label, GREY)
    cv.text(x, y + 9, vscale, value, INK)
    cv.hline(x, x + w, y + 9 + 7 * vscale + 3, (200, 186, 150), thick=1)
    return y + 34


def build_spread():
    cv = Canvas(W, H, PAPER)
    guilloche(cv)
    # outer double border + centre gutter
    cv.rect(10, 10, W - 11, H - 11, INK, thick=2)
    cv.rect(16, 16, W - 17, H - 17, GOLD, thick=1)
    cv.vline(512, 16, H - 17, (200, 186, 150), thick=2)
    cv.vline(510, 16, H - 17, (120, 110, 90), alpha=60, thick=1)

    # ============================== LEFT PAGE: data page
    draw_arms(cv, 262, 26)
    cv.text_center(262, 92, 3, 'REPUBLIC OF VALDORIA', INK)
    cv.text_center(262, 114, 2, 'REPUBLIKA VALDORIJA', GOLD)
    cv.hline(72, 452, 136, GOLD, thick=2)
    cv.text_center(262, 146, 3, 'PASSPORT', INK)
    cv.text(56, 150, 1, 'TYPE P', INK)
    cv.text(430, 150, 1, 'CODE VLD', INK)

    # photo
    cv.fill_rect(46, 176, 238, 428, (255, 255, 255))
    cv.rect(46, 176, 237, 427, INK, thick=2)
    cv.rect(50, 180, 233, 423, GOLD, thick=1)
    draw_portrait(cv, 54, 184, 230, 420)
    # signature squiggle under the photo
    sx, sy = 60, 448
    pts = []
    for i in range(34):
        pts.append((sx + i * 5, sy + int(5 * math.sin(i * 0.9)) - (3 if i % 7 == 0 else 0)))
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], (44, 62, 110), thick=1)
    cv.text(60, 462, 1, 'HOLDER SIGNATURE', GREY)

    # data fields, right of the photo
    x = 258
    y = 178
    y = field(cv, x, y, 'SURNAME / PREZIME', 'VOSS', 228)
    y = field(cv, x, y, 'GIVEN NAMES / IMENA', 'ELENA MARA', 228)
    y = field(cv, x, y, 'NATIONALITY / DRZAVLJANSTVO', 'VALDORIAN', 228)
    y = field(cv, x, y, 'DATE OF BIRTH / DATUM RODENJA', '12 MAR 1996', 228)
    y = field(cv, x, y, 'PLACE OF BIRTH / MJESTO RODENJA', 'VELMARA', 228)
    y = field(cv, x, y, 'SEX / SPOL', 'F', 60)
    y = field(cv, x, y, 'DATE OF ISSUE / DATUM IZDAVANJA', '14 MAR 2024', 228)
    y = field(cv, x, y, 'DATE OF EXPIRY / DATUM ISTEKA', '13 MAR 2034', 228)
    y = field(cv, x, y, 'AUTHORITY / TIJELO', 'MINISTRY OF THE INTERIOR - VELMARA', 228, vscale=1)

    # machine-readable zone
    line1, line2 = mrz_lines()
    cv.hline(40, 484, 520, INK, thick=1)
    cv.text(40, 530, 1, line1, INK)
    cv.text(40, 540, 1, line2, INK)
    cv.text_center(262, 580, 1, 'THIS PASSPORT REMAINS THE PROPERTY OF THE REPUBLIC OF VALDORIA', GREY)

    # ============================== RIGHT PAGE: visas and stamps
    cv.text(548, 34, 3, 'VISAS', INK)
    cv.text(548, 58, 2, 'VIZE', GOLD)
    cv.text(940, 34, 2, '12', INK)
    cv.text(548, 84, 1, 'PASSPORT NO. VLD483920', GREY)

    # Dravnian visa sticker
    vx, vy, vw, vh = 544, 104, 268, 128
    cv.fill_rect(vx, vy, vx + vw, vy + vh, (250, 246, 232))
    cv.rect(vx, vy, vx + vw - 1, vy + vh - 1, INK, thick=2)
    cv.fill_rect(vx + 2, vy + 2, vx + vw - 2, vy + 30, INK)
    cv.text(vx + 10, vy + 8, 2, 'VISA', (244, 236, 217))
    cv.text(vx + 120, vy + 10, 1, 'REPUBLIC OF DRAVNIA', (244, 236, 217))
    star(cv, vx + vw - 22, vy + 16, 9, 4, 5, GOLD_LT)
    yy = vy + 40
    for lab, val in (('TYPE', 'C - MULTIPLE ENTRY'),
                     ('VALID', '28 MAY 2024 - 27 NOV 2024'),
                     ('STAY', '90 DAYS'),
                     ('NO.', 'DV-2024-08117')):
        cv.text(vx + 10, yy, 1, lab, GREY)
        cv.text(vx + 78, yy, 1, val, INK)
        yy += 16
    cv.text(vx + 10, yy + 4, 1, 'ISSUED AT VELMARA, 28 MAY 2024', GREY)

    # stamps
    s1 = round_stamp(['DRAVNIA', 'ENTRY', '02 JUN 2024'], 84, STAMP_BLUE, 'KESTREL GATE')
    rotate_blit(cv, s1, 884, 172, -16, alpha=215, worn=True)
    s2 = oval_stamp(['OSTARA', 'DEPARTED', '19 JAN 2025'], 96, 62, STAMP_PURPLE)
    rotate_blit(cv, s2, 668, 316, 11, alpha=210, worn=True)
    s3 = round_stamp(['KELM', '04 NOV', '2024'], 52, STAMP_GREEN)
    rotate_blit(cv, s3, 902, 330, 18, alpha=210, worn=True)
    s4 = rect_stamp([('ISLE OF TERN', 2), ('ARRIVED 11 SEP 2025', 2),
                     ('HARBOURMASTER', 1)], 300, 74, STAMP_RED)
    rotate_blit(cv, s4, 780, 448, -4, alpha=215, worn=True)

    # telling paperwork detail: the harbourmaster condition
    bx, by, bw, bh = 544, 508, 448, 104
    cv.fill_rect(bx, by, bx + bw, by + bh, (250, 244, 226))
    cv.rect(bx, by, bx + bw - 1, by + bh - 1, STAMP_RED, thick=2)
    cv.text(bx + 12, by + 8, 2, 'CONDITION OF ENTRY', STAMP_RED)
    cv.text(bx + 12, by + 26, 1, 'UVJET ULASKA', GOLD)
    lines = wrap_text('HOLDER MUST REGISTER WITH THE HARBOURMASTER '
                      'WITHIN THREE DAYS OF LANDING.', 1, bw - 24)
    yy = by + 42
    for ln in lines:
        cv.text(bx + 12, yy, 1, ln, INK)
        yy += 11
    cv.text(bx + 12, yy + 2, 1, 'FEE PAID: 40 CROWNS - RECEIPT NO. 1187', INK)
    cv.text(bx + 12, yy + 13, 1, 'PORT OF VELMARA', GREY)
    return cv


def main():
    cv = build_spread()
    out = OUT_PATH
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
    except OSError:
        out = os.path.join('output', 'entry.png')
        os.makedirs('output', exist_ok=True)
    size = write_png(cv, out)
    print('wrote %s (%dx%d, %d bytes)' % (out, W, H, size))


if __name__ == '__main__':
    main()
