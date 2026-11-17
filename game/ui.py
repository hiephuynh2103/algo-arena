"""Hệ thống giao diện (design system) của Algo Arena.

- Font Be Vietnam Pro (hỗ trợ đầy đủ tiếng Việt), tự fallback sang DejaVu cho ký hiệu.
- Nền gradient + ánh sáng, panel dạng kính mờ có đổ bóng, nút gradient phát sáng.
- Thẻ bài vẽ bằng vector: khung theo nhóm, ô minh hoạ có icon, viên đá chi phí.
- Mọi bề mặt tốn công vẽ đều được cache để chạy mượt trên WebAssembly.
"""
import math
import os
import random

import pygame

from engine import CARDS, CATEGORY_LABEL, card_cost_label

W, H = 1280, 720
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- bảng màu
BG = (20, 10, 4)
PANEL = (39, 23, 12)
PANEL2 = (56, 34, 18)
LINE = (112, 84, 46)
TEXT = (250, 240, 220)
MUTED = (196, 172, 138)
ACCENT = (240, 190, 92)
ACCENT2 = (214, 92, 70)
GOLD = (255, 214, 120)
RED = (255, 107, 107)
GREEN = (80, 230, 140)
ORANGE = (255, 159, 67)
BLUE = (90, 170, 255)
PINK = (244, 114, 182)

CAT_COLOR = {"ds": (24, 170, 150), "search": (59, 130, 246), "sort": (139, 92, 246),
             "graph": (234, 120, 40), "paradigm": (226, 72, 140)}
RATING_COLOR = {"optimal": GREEN, "acceptable": GOLD, "trap": RED, "missed": ORANGE,
                "failed": RED, "neutral": MUTED}
RATING_LABEL = {"optimal": "TỐI ƯU", "acceptable": "CHƯA TỐI ƯU", "trap": "BẪY",
                "missed": "BỎ LỠ", "failed": "THẤT BẠI", "neutral": ""}


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lighten(c, t=0.25):
    return mix(c, (255, 255, 255), t)


def darken(c, t=0.4):
    return mix(c, (0, 0, 0), t)


# ---------------------------------------------------------------- font & chữ
_fonts = {}
_text_cache = {}
WEIGHT_FILE = {0: "BeVietnamPro-Regular.ttf", 1: "BeVietnamPro-SemiBold.ttf",
               2: "BeVietnamPro-Bold.ttf", 3: "BeVietnamPro-ExtraBold.ttf"}


def _weight(bold):
    if bold is True:
        return 2
    if not bold:
        return 0
    return int(bold)


def font(size, bold=False):
    key = (size, _weight(bold))
    if key not in _fonts:
        try:
            _fonts[key] = pygame.font.Font(os.path.join(HERE, "assets", WEIGHT_FILE[key[1]]), size)
        except Exception:
            _fonts[key] = pygame.font.Font(None, size + 4)
    return _fonts[key]


def _fallback(size, bold):
    key = ("dv", size, bool(bold))
    if key not in _fonts:
        fn = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        try:
            _fonts[key] = pygame.font.Font(os.path.join(HERE, "assets", fn), max(8, size - 2))
        except Exception:
            _fonts[key] = pygame.font.Font(None, size + 2)
    return _fonts[key]


_missing = {}


def _has(f, ch):
    k = (id(f), ch)
    if k not in _missing:
        if ch.isspace() or ord(ch) < 128:
            _missing[k] = True
        else:
            m = f.metrics(ch)
            _missing[k] = bool(m and m[0] and (m[0][1] - m[0][0] > 0 or m[0][3] - m[0][2] > 0))
    return _missing[k]


def render(s, size=16, color=TEXT, bold=False):
    """Render chữ có cache + fallback ký hiệu sang DejaVu."""
    s = str(s)
    key = (s, size, _weight(bold), color)
    img = _text_cache.get(key)
    if img is not None:
        return img
    f = font(size, bold)
    if all(_has(f, ch) for ch in s):
        img = f.render(s, True, color)
    else:
        fb = _fallback(size, bold)
        parts, cur, cur_main = [], "", True
        for ch in s:
            main = _has(f, ch)
            if main != cur_main and cur:
                parts.append((cur, cur_main))
                cur = ""
            cur_main = main
            cur += ch
        if cur:
            parts.append((cur, cur_main))
        imgs = [(f if m else fb).render(t, True, color) for t, m in parts]
        h = f.get_height()
        img = pygame.Surface((sum(i.get_width() for i in imgs), h), pygame.SRCALPHA)
        x = 0
        for i in imgs:
            img.blit(i, (x, (h - i.get_height()) // 2))
            x += i.get_width()
    if len(_text_cache) > 4000:
        _text_cache.clear()
    _text_cache[key] = img
    return img


def text_size(s, size=16, bold=False):
    return render(s, size, TEXT, bold).get_size()


def text(surf, s, pos, size=16, color=TEXT, bold=False, center=False, right=False, shadow=False):
    img = render(s, size, color, bold)
    r = img.get_rect()
    if center:
        r.center = pos
    elif right:
        r.topright = pos
    else:
        r.topleft = pos
    if shadow:
        sh = render(s, size, (0, 0, 0), bold).copy()
        sh.set_alpha(150)
        surf.blit(sh, r.move(0, 2))
    surf.blit(img, r)
    return r


def wrap(s, size, width, bold=False):
    lines = []
    for para in str(s).split("\n"):
        cur = ""
        for w_ in para.split(" "):
            t = (cur + " " + w_).strip()
            if text_size(t, size, bold)[0] <= width:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w_
        lines.append(cur)
    return lines


def text_box(surf, s, rect, size=14, color=TEXT, bold=False, line_gap=3, max_lines=None):
    x, y, w, h = rect
    lh = font(size, bold).get_linesize() + line_gap - 2
    lines = wrap(s, size, w, bold)
    if max_lines:
        lines = lines[:max_lines]
    for ln in lines:
        if y + lh > rect[1] + h + 3:
            break
        text(surf, ln, (x, y), size, color, bold)
        y += lh
    return y


# ---------------------------------------------------------------- bề mặt cache
_surf_cache = {}


def _cached(key, builder):
    s = _surf_cache.get(key)
    if s is None:
        s = builder()
        if len(_surf_cache) > 600:
            _surf_cache.clear()
        _surf_cache[key] = s
    return s


def vgradient(w, h, top, bottom, radius=0):
    def build():
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            t = y / max(1, h - 1)
            c = mix(top[:3], bottom[:3], t)
            a = int((top[3] if len(top) > 3 else 255) * (1 - t) + (bottom[3] if len(bottom) > 3 else 255) * t)
            pygame.draw.line(s, (*c, a), (0, y), (w, y))
        if radius:
            m = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(m, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
            s.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return s
    return _cached(("vg", w, h, tuple(top), tuple(bottom), radius), build)


def shadow(w, h, radius=14, spread=14, alpha=110):
    def build():
        s = pygame.Surface((w + spread * 2, h + spread * 2), pygame.SRCALPHA)
        for i in range(spread, 0, -2):
            a = int(alpha * (1 - i / spread) ** 2 / 3)
            pygame.draw.rect(s, (0, 0, 0, a), (spread - i, spread - i + 4, w + i * 2, h + i * 2),
                             border_radius=radius + i)
        return s
    return _cached(("sh", w, h, radius, spread, alpha), build)


def glow(w, h, color, radius=14, spread=16, strength=90):
    def build():
        s = pygame.Surface((w + spread * 2, h + spread * 2), pygame.SRCALPHA)
        for i in range(spread, 0, -2):
            a = int(strength * (1 - i / spread) ** 1.6 / 2.2)
            pygame.draw.rect(s, (*color, a), (spread - i, spread - i, w + i * 2, h + i * 2),
                             border_radius=radius + i)
        return s
    return _cached(("gl", w, h, tuple(color), radius, spread, strength), build)


def radial(r, color, alpha=120):
    def build():
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for i in range(r, 0, -3):
            a = int(alpha * (1 - i / r) ** 2)
            pygame.draw.circle(s, (*color, a), (r, r), i)
        return s
    return _cached(("rad", r, tuple(color), alpha), build)


# ---------------------------------------------------------------- nền
_bg = None
_particles = None


def draw_background(surf, t=0.0):
    global _bg, _particles
    if _bg is None:
        _bg = pygame.Surface((W, H))
        _bg.blit(vgradient(W, H, (24, 12, 6), (15, 7, 3)), (0, 0))
        _bg.blit(radial(520, (190, 110, 40), 70), (-260, -300))
        _bg.blit(radial(560, (150, 36, 40), 80), (W - 520, H - 520))
        _bg.blit(radial(300, (230, 170, 80), 40), (W // 2 - 300, -200))
        grid = pygame.Surface((W, H), pygame.SRCALPHA)
        for x in range(0, W, 48):
            pygame.draw.line(grid, (230, 180, 110, 7), (x, 0), (x, H))
        for y in range(0, H, 48):
            pygame.draw.line(grid, (230, 180, 110, 7), (0, y), (W, y))
        _bg.blit(grid, (0, 0))
        rng = random.Random(7)
        _particles = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(4, 16), rng.uniform(1, 2.4),
                       rng.choice([ACCENT, (255, 140, 60), (255, 224, 170)])) for _ in range(46)]
    surf.blit(_bg, (0, 0))
    for (x, y, sp, r, c) in _particles:
        yy = (y - t * sp) % H
        xx = x + math.sin(t * 0.3 + y) * 10
        a = int(90 + 70 * math.sin(t * 1.3 + x))
        pygame.draw.circle(surf, mix(BG, c, a / 255), (int(xx), int(yy)), int(r))


# ---------------------------------------------------------------- panel, thanh, nút
def panel(surf, rect, color=None, border=None, radius=14, width=1, glass=True, shadow_on=True, accent=None):
    r = pygame.Rect(rect)
    if shadow_on:
        surf.blit(shadow(r.w, r.h, radius), (r.x - 14, r.y - 14))
    base = color if color is not None else PANEL
    top = (*lighten(base[:3], 0.06), 236 if glass else 255)
    bot = (*darken(base[:3], 0.15), 236 if glass else 255)
    surf.blit(vgradient(r.w, r.h, top, bot, radius), r)
    # viền sáng mảnh phía trên
    hl = vgradient(r.w, max(2, r.h // 3), (255, 255, 255, 18), (255, 255, 255, 0), radius)
    surf.blit(hl, r)
    bcol = accent or border or (128, 96, 54)
    pygame.draw.rect(surf, bcol, r, width, border_radius=radius)


def bar(surf, rect, frac, color=ACCENT, back=(23, 12, 6)):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, back, r, border_radius=r.h // 2)
    frac = max(0.0, min(1.0, frac))
    if frac > 0:
        fw = max(r.h, int(r.w * frac))
        surf.blit(vgradient(fw, r.h, (*lighten(color, 0.25), 255), (*darken(color, 0.15), 255), r.h // 2), r.topleft)
        pygame.draw.line(surf, lighten(color, 0.55), (r.x + r.h // 2, r.y + 2), (r.x + fw - r.h // 2, r.y + 2))
    pygame.draw.rect(surf, (120, 90, 50), r, 1, border_radius=r.h // 2)


def chip(surf, label, pos, color, size=11, filled=False):
    w, h = text_size(label, size, 2)
    r = pygame.Rect(pos[0], pos[1], w + 16, h + 6)
    if filled:
        pygame.draw.rect(surf, color, r, border_radius=r.h // 2)
        text(surf, label, r.center, size, (18, 10, 6), 2, center=True)
    else:
        pygame.draw.rect(surf, darken(color, 0.78), r, border_radius=r.h // 2)
        pygame.draw.rect(surf, darken(color, 0.2), r, 1, border_radius=r.h // 2)
        text(surf, label, r.center, size, lighten(color, 0.2), 2, center=True)
    return r


class Button:
    def __init__(self, rect, label, cb=None, kind="normal", size=17, enabled=True, tip=None, icon_name=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.cb = cb
        self.kind = kind
        self.size = size
        self.enabled = enabled
        self.hover = False
        self.tip = tip
        self.icon = icon_name
        self.t = 0.0

    def draw(self, surf):
        r = self.rect
        k = self.kind
        if k == "primary":
            top, bot, fg, glow_c = (255, 224, 140), (200, 142, 52), (44, 24, 6), ACCENT
        elif k == "danger":
            top, bot, fg, glow_c = (120, 44, 60), (80, 26, 40), (255, 214, 214), RED
        elif k == "ghost":
            top, bot, fg, glow_c = (48, 29, 16), (37, 22, 12), MUTED, ACCENT2
        elif k == "gold":
            top, bot, fg, glow_c = (255, 214, 110), (230, 160, 50), (40, 24, 4), GOLD
        else:
            top, bot, fg, glow_c = (71, 44, 24), (51, 30, 17), TEXT, ACCENT2
        if not self.enabled:
            top, bot, fg = (48, 34, 21), (40, 27, 17), (140, 118, 92)
        if self.hover and self.enabled:
            surf.blit(glow(r.w, r.h, glow_c, 12, 14, 120), (r.x - 14, r.y - 14))
            top, bot = lighten(top, 0.12), lighten(bot, 0.08)
            if k in ("ghost", "normal"):
                fg = TEXT
        surf.blit(shadow(r.w, r.h, 12, 8, 90), (r.x - 8, r.y - 8))
        surf.blit(vgradient(r.w, r.h, (*top, 255), (*bot, 255), 12), r)
        surf.blit(vgradient(r.w, r.h // 2, (255, 255, 255, 34), (255, 255, 255, 0), 12), r)
        border = lighten(glow_c, 0.2) if (self.hover and self.enabled) else (255, 255, 255, 40)
        pygame.draw.rect(surf, border if len(border) == 3 else (150, 116, 64), r, 1, border_radius=12)
        weight = 2 if k != "ghost" else 1
        lw, lh = text_size(self.label, self.size, weight) if self.label else (0, 0)
        isz = int(self.size * 1.15)
        total = lw + ((isz + 8) if self.icon else 0)
        x0 = r.centerx - total // 2
        if self.icon:
            icon(surf, self.icon, (x0 + isz // 2, r.centery), isz, fg)
            x0 += isz + 8
        if self.label:
            text(surf, self.label, (x0, r.centery - lh // 2 - 1), self.size, fg, weight)

    def handle(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            if self.enabled and self.cb:
                self.cb()
            return True
        return False


class TextInput:
    def __init__(self, rect, placeholder="", password=False, maxlen=32):
        self.rect = pygame.Rect(rect)
        self.value = ""
        self.placeholder = placeholder
        self.password = password
        self.focus = False
        self.maxlen = maxlen
        self.t = 0

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.focus = self.rect.collidepoint(e.pos)
        elif e.type == pygame.KEYDOWN and self.focus:
            if e.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
                return
            elif e.unicode and e.unicode.isprintable() and len(self.value) < self.maxlen:
                self.value += e.unicode

    def draw(self, surf, dt=0):
        self.t += dt
        r = self.rect
        if self.focus:
            surf.blit(glow(r.w, r.h, ACCENT, 12, 10, 90), (r.x - 10, r.y - 10))
        pygame.draw.rect(surf, (24, 12, 6), r, border_radius=12)
        pygame.draw.rect(surf, ACCENT if self.focus else LINE, r, 2 if self.focus else 1, border_radius=12)
        shown = ("•" * len(self.value)) if self.password else self.value
        ty = r.centery - text_size("Ag", 17)[1] // 2
        if shown:
            tr = text(surf, shown, (r.x + 16, ty), 17)
            cx = tr.right + 2
        else:
            text(surf, self.placeholder, (r.x + 16, ty), 17, (150, 126, 96))
            cx = r.x + 16
        if self.focus and int(self.t * 2) % 2 == 0:
            pygame.draw.line(surf, ACCENT, (cx, r.y + 12), (cx, r.bottom - 12), 2)


# ---------------------------------------------------------------- icon vector
def icon(surf, name, center, size, color):
    cx, cy = center
    s = size
    c = color
    lw = max(2, s // 10)
    if name == "sword":
        pygame.draw.line(surf, c, (cx - s * .38, cy + s * .38), (cx + s * .32, cy - s * .32), lw + 1)
        pygame.draw.line(surf, c, (cx + s * .38, cy + s * .38), (cx - s * .32, cy - s * .32), lw + 1)
        for sx in (-1, 1):
            pygame.draw.line(surf, c, (cx + sx * s * .16, cy + s * .36), (cx + sx * s * .36, cy + s * .16), lw)
    elif name == "puzzle":
        r = pygame.Rect(0, 0, s * .66, s * .66)
        r.center = (cx - s * .04, cy + s * .04)
        pygame.draw.rect(surf, c, r, lw, border_radius=3)
        pygame.draw.circle(surf, c, (r.centerx, r.y), s * .12)
        pygame.draw.circle(surf, c, (r.right, r.centery), s * .12)
    elif name == "book":
        pygame.draw.polygon(surf, c, [(cx, cy - s * .28), (cx - s * .42, cy - s * .36), (cx - s * .42, cy + s * .3), (cx, cy + s * .38)], lw)
        pygame.draw.polygon(surf, c, [(cx, cy - s * .28), (cx + s * .42, cy - s * .36), (cx + s * .42, cy + s * .3), (cx, cy + s * .38)], lw)
    elif name == "deck":
        for i, off in enumerate((-.16, 0, .16)):
            r = pygame.Rect(0, 0, s * .46, s * .64)
            r.center = (cx + off * s, cy - off * s * .3)
            pygame.draw.rect(surf, (23, 12, 6), r, border_radius=4)
            pygame.draw.rect(surf, c, r, lw, border_radius=4)
    elif name == "replay":
        pygame.draw.arc(surf, c, (cx - s * .38, cy - s * .38, s * .76, s * .76), 0.6, 5.6, lw + 1)
        pygame.draw.polygon(surf, c, [(cx + s * .34, cy - s * .36), (cx + s * .38, cy - s * .04), (cx + s * .1, cy - s * .14)])
        pygame.draw.polygon(surf, c, [(cx - s * .08, cy - s * .14), (cx - s * .08, cy + s * .16), (cx + s * .18, cy + s * .01)])
    elif name == "crown":
        pts = [(cx - s * .4, cy + s * .26), (cx - s * .4, cy - s * .2), (cx - s * .16, cy + s * .02), (cx, cy - s * .34),
               (cx + s * .16, cy + s * .02), (cx + s * .4, cy - s * .2), (cx + s * .4, cy + s * .26)]
        pygame.draw.polygon(surf, c, pts)
    elif name in ("play", "next"):
        pygame.draw.polygon(surf, c, [(cx - s * .22, cy - s * .3), (cx + s * .3, cy), (cx - s * .22, cy + s * .3)])
    elif name == "prev":
        pygame.draw.polygon(surf, c, [(cx + s * .22, cy - s * .3), (cx - s * .3, cy), (cx + s * .22, cy + s * .3)])
    elif name == "first":
        pygame.draw.polygon(surf, c, [(cx + s * .28, cy - s * .3), (cx - s * .16, cy), (cx + s * .28, cy + s * .3)])
        pygame.draw.rect(surf, c, (cx - s * .3, cy - s * .3, s * .1, s * .6))
    elif name == "last":
        pygame.draw.polygon(surf, c, [(cx - s * .28, cy - s * .3), (cx + s * .16, cy), (cx - s * .28, cy + s * .3)])
        pygame.draw.rect(surf, c, (cx + s * .2, cy - s * .3, s * .1, s * .6))
    elif name == "pause":
        pygame.draw.rect(surf, c, (cx - s * .26, cy - s * .3, s * .17, s * .6))
        pygame.draw.rect(surf, c, (cx + s * .09, cy - s * .3, s * .17, s * .6))
    elif name == "back":
        pygame.draw.line(surf, c, (cx + s * .3, cy), (cx - s * .28, cy), lw + 1)
        pygame.draw.lines(surf, c, False, [(cx - s * .02, cy - s * .28), (cx - s * .3, cy), (cx - s * .02, cy + s * .28)], lw + 1)
    elif name == "check":
        pygame.draw.lines(surf, c, False, [(cx - s * .32, cy), (cx - s * .08, cy + s * .26), (cx + s * .34, cy - s * .26)], lw + 1)
    elif name == "cross":
        pygame.draw.line(surf, c, (cx - s * .26, cy - s * .26), (cx + s * .26, cy + s * .26), lw + 1)
        pygame.draw.line(surf, c, (cx + s * .26, cy - s * .26), (cx - s * .26, cy + s * .26), lw + 1)
    elif name == "lock":
        pygame.draw.arc(surf, c, (cx - s * .2, cy - s * .38, s * .4, s * .44), 0, math.pi, lw)
        pygame.draw.rect(surf, c, (cx - s * .3, cy - s * .12, s * .6, s * .46), border_radius=3)
    elif name == "shield":
        pts = [(cx, cy - s * .4), (cx + s * .34, cy - s * .26), (cx + s * .28, cy + s * .12), (cx, cy + s * .4),
               (cx - s * .28, cy + s * .12), (cx - s * .34, cy - s * .26)]
        pygame.draw.polygon(surf, c, pts)
    elif name == "bolt":
        pygame.draw.polygon(surf, c, [(cx + s * .08, cy - s * .42), (cx - s * .26, cy + s * .06), (cx - s * .02, cy + s * .06),
                                      (cx - s * .1, cy + s * .42), (cx + s * .26, cy - s * .08), (cx + s * .02, cy - s * .08)])
    elif name == "logout":
        pygame.draw.rect(surf, c, (cx - s * .36, cy - s * .34, s * .4, s * .68), lw, border_radius=3)
        pygame.draw.line(surf, c, (cx - s * .08, cy), (cx + s * .38, cy), lw)
        pygame.draw.lines(surf, c, False, [(cx + s * .2, cy - s * .18), (cx + s * .38, cy), (cx + s * .2, cy + s * .18)], lw)
    elif name == "globe":
        pygame.draw.circle(surf, c, (cx, cy), s * .38, lw)
        pygame.draw.ellipse(surf, c, (cx - s * .16, cy - s * .38, s * .32, s * .76), lw)
        pygame.draw.line(surf, c, (cx - s * .38, cy), (cx + s * .38, cy), lw)
    elif name == "hint":
        pygame.draw.circle(surf, c, (cx, cy - s * .08), s * .26, lw)
        pygame.draw.rect(surf, c, (cx - s * .12, cy + s * .22, s * .24, s * .14), border_radius=2)
    elif name == "flag":
        pygame.draw.line(surf, c, (cx - s * .28, cy - s * .38), (cx - s * .28, cy + s * .4), lw)
        pygame.draw.polygon(surf, c, [(cx - s * .26, cy - s * .38), (cx + s * .34, cy - s * .2), (cx - s * .26, cy)])
    else:
        _cat_icon(surf, name, center, size, c)


def _cat_icon(surf, cat, center, s, c):
    cx, cy = center
    lw = max(2, int(s / 12))
    if cat == "ds":          # ngăn xếp: 4 lớp tách rời, lớp trên cùng sáng nhất
        bh = max(3, s * .12)
        for i in range(4):
            r = pygame.Rect(0, 0, s * (.62 + (.0 if i else .0)), bh)
            r.center = (cx, cy + s * .3 - i * s * .19)
            shade = mix(c, (255, 255, 255), .15 * i) if i == 3 else mix(c, (0, 0, 0), .12 * (3 - i))
            pygame.draw.rect(surf, shade, r, border_radius=max(2, int(bh // 2)))
        pygame.draw.polygon(surf, c, [(cx + s * .38, cy - s * .36), (cx + s * .46, cy - s * .26), (cx + s * .3, cy - s * .26)])
    elif cat == "search":    # kính lúp
        pygame.draw.circle(surf, c, (cx - s * .08, cy - s * .08), s * .27, lw + 1)
        pygame.draw.line(surf, c, (cx + s * .12, cy + s * .12), (cx + s * .36, cy + s * .36), lw + 3)
    elif cat == "sort":      # cột tăng dần
        for i in range(5):
            h = s * (.18 + i * .15)
            pygame.draw.rect(surf, c, (cx - s * .4 + i * s * .17, cy + s * .36 - h, s * .12, h), border_radius=3)
    elif cat == "graph":     # đồ thị
        pts = [(cx - s * .34, cy - s * .2), (cx + s * .02, cy - s * .36), (cx + s * .36, cy - s * .06),
               (cx - s * .12, cy + s * .14), (cx + s * .22, cy + s * .34)]
        for a, b in ((0, 1), (1, 2), (0, 3), (3, 2), (3, 4), (2, 4)):
            pygame.draw.line(surf, c, pts[a], pts[b], lw)
        for p in pts:
            pygame.draw.circle(surf, (23, 12, 6), p, s * .085)
            pygame.draw.circle(surf, c, p, s * .085, lw)
    else:                    # chiến lược: cây đệ quy
        def br(x, y, ang, ln, d):
            if d == 0:
                pygame.draw.circle(surf, lighten(c, .3), (x, y), max(2, s * .04))
                return
            x2, y2 = x + math.cos(ang) * ln, y - math.sin(ang) * ln
            pygame.draw.line(surf, c, (x, y), (x2, y2), max(1, lw - (3 - d)))
            br(x2, y2, ang + .55, ln * .66, d - 1)
            br(x2, y2, ang - .55, ln * .66, d - 1)
        br(cx, cy + s * .4, math.pi / 2, s * .3, 4)


# ---------------------------------------------------------------- thẻ bài
def _card_face(cid, w, h, compact):
    def build():
        c = CARDS[cid]
        col = CAT_COLOR[c["cat"]]
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        rad = 14
        # thân thẻ
        s.blit(vgradient(w, h, (*darken(col, .55), 255), (23, 12, 7, 255), rad), (0, 0))
        # khung ngoài 2 lớp
        pygame.draw.rect(s, (214, 168, 84), (0, 0, w, h), 2, border_radius=rad)
        pygame.draw.rect(s, lighten(col, .1), (2, 2, w - 4, h - 4), 1, border_radius=rad - 2)
        pygame.draw.rect(s, (255, 255, 255, 40), (4, 4, w - 8, h - 8), 1, border_radius=rad - 4)
        # tên
        fs = 12 if w < 135 else 13
        name_lines = wrap(c["name"], fs, w - 46, 3)[:2]
        ny = 9 if len(name_lines) == 2 else 15
        for ln in name_lines:
            text(s, ln, (38, ny), fs, TEXT, 3)
            ny += fs + 3
        # ô minh hoạ
        ay = 42
        ah = int(h * (.42 if compact else .32))
        art = pygame.Rect(8, ay, w - 16, ah)
        s.blit(vgradient(art.w, art.h, (*lighten(col, .1), 255), (*darken(col, .45), 255), 9), art)
        rng = random.Random(cid)
        pat = pygame.Surface(art.size, pygame.SRCALPHA)
        for _ in range(14):
            x, y = rng.randint(0, art.w), rng.randint(0, art.h)
            pygame.draw.circle(pat, (255, 255, 255, rng.randint(10, 32)), (x, y), rng.randint(2, 10))
        for k in range(-art.h, art.w, 12):
            pygame.draw.line(pat, (255, 255, 255, 10), (k, art.h), (k + art.h, 0))
        s.blit(pat, art)
        s.blit(radial(int(ah * .7), lighten(col, .5), 90), (art.centerx - int(ah * .7), art.centery - int(ah * .7)))
        _cat_icon(s, c["cat"], art.center, int(ah * .78), (250, 252, 255))
        pygame.draw.rect(s, (255, 255, 255, 70), art, 1, border_radius=9)
        # dải nhóm + độ phức tạp
        y = art.bottom + 6
        lab = CATEGORY_LABEL[c["cat"]].upper()
        text(s, lab, (10, y), 9, lighten(col, .45), 3)
        cx_w = text_size(c["complexity"], 10, 2)[0]
        if cx_w < w - 20 - text_size(lab, 9, 3)[0] - 6:
            text(s, c["complexity"], (w - 10, y), 10, GOLD, 2, right=True)
            y += 16
        else:
            y += 13
            text(s, c["complexity"], (10, y), 10, GOLD, 2)
            y += 15
        if not compact:
            body = pygame.Rect(8, y + 2, w - 16, h - y - 10)
            pygame.draw.rect(s, (15, 7, 3, 150), body, border_radius=8)
            text_box(s, c["text"], (body.x + 6, body.y + 5, body.w - 12, body.h - 8), 10, (226, 232, 246))
        # viên đá chi phí
        gem = pygame.Surface((34, 34), pygame.SRCALPHA)
        pts = [(17 + 15 * math.cos(math.pi / 6 + i * math.pi / 3), 17 + 15 * math.sin(math.pi / 6 + i * math.pi / 3)) for i in range(6)]
        pygame.draw.polygon(gem, (40, 52, 150), pts)
        pygame.draw.polygon(gem, (124, 146, 255), [(p[0] * .8 + 3.4, p[1] * .8 + 1.4) for p in pts])
        pygame.draw.polygon(gem, (210, 220, 255), pts, 2)
        s.blit(gem, (2, 2))
        text(s, card_cost_label(cid), (19, 19), 16, (255, 255, 255), 3, center=True, shadow=True)
        # ánh sáng chéo
        shine = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(shine, (255, 255, 255, 14), [(0, 0), (w * .55, 0), (0, h * .45)])
        s.blit(shine, (0, 0))
        return s
    return _cached(("card", cid, w, h, compact), build)


def draw_card(surf, rect, cid, playable=True, highlight=False, locked=False, compact=False, badge=None, lift=0):
    r = pygame.Rect(rect).move(0, -lift)
    col = CAT_COLOR[CARDS[cid]["cat"]]
    if highlight:
        surf.blit(glow(r.w, r.h, GOLD, 14, 18, 170), (r.x - 18, r.y - 18))
    elif playable and not locked:
        surf.blit(glow(r.w, r.h, col, 14, 10, 60), (r.x - 10, r.y - 10))
    surf.blit(shadow(r.w, r.h, 14, 12, 140), (r.x - 12, r.y - 12))
    surf.blit(_card_face(cid, r.w, r.h, compact), r)
    if highlight:
        pygame.draw.rect(surf, GOLD, r, 2, border_radius=14)
    if locked:
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (14, 6, 3, 185), (0, 0, r.w, r.h), border_radius=14)
        surf.blit(s, r)
        icon(surf, "lock", (r.centerx, r.centery - 8), 30, (214, 190, 150))
        text(surf, "Chưa mở khoá", (r.centerx, r.centery + 22), 12, (226, 206, 170), 2, center=True)
    elif not playable:
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (14, 6, 3, 120), (0, 0, r.w, r.h), border_radius=14)
        surf.blit(s, r)
    if badge:
        label, bc = badge
        bw = text_size(label, 11, 3)[0] + 16
        br = pygame.Rect(r.right - bw + 4, r.y - 10, bw, 22)
        surf.blit(glow(br.w, br.h, bc, 11, 8, 120), (br.x - 8, br.y - 8))
        pygame.draw.rect(surf, bc, br, border_radius=11)
        text(surf, label, br.center, 11, (18, 10, 6), 3, center=True)


def draw_card_detail(surf, pos, cid, extra=None):
    c = CARDS[cid]
    col = CAT_COLOR[c["cat"]]
    w = 320
    body_h = len(wrap(c["text"], 13, w - 32)) * 19 + len(wrap(c["lesson"], 12, w - 52)) * 18
    h = 108 + body_h + (26 if extra else 0)
    x = min(max(10, pos[0]), W - w - 10)
    y = min(max(10, pos[1]), H - h - 10)
    r = pygame.Rect(x, y, w, h)
    panel(surf, r, (35, 20, 11), accent=lighten(col, .2), radius=14, width=2)
    pygame.draw.rect(surf, col, (x + 2, y + 2, 6, h - 4), border_top_left_radius=12, border_bottom_left_radius=12)
    text(surf, c["name"], (x + 20, y + 14), 18, TEXT, 3)
    cx = x + 20
    for lab, cc in ((f"Chi phí {card_cost_label(cid)}", ACCENT2), (CATEGORY_LABEL[c['cat']], col), (c["complexity"], GOLD)):
        rr = chip(surf, lab, (cx, y + 44), cc, 10)
        cx = rr.right + 6
    yy = text_box(surf, c["text"], (x + 20, y + 76, w - 36, 200), 13, TEXT)
    pygame.draw.line(surf, LINE, (x + 20, yy + 4), (x + w - 16, yy + 4))
    icon(surf, "hint", (x + 28, yy + 22), 16, GOLD)
    text_box(surf, c["lesson"], (x + 42, yy + 12, w - 58, 200), 12, MUTED)
    if extra:
        icon(surf, "lock", (x + 26, y + h - 18), 14, ORANGE)
        text(surf, extra, (x + 40, y + h - 27), 12, ORANGE, 2)


def draw_card_back(surf, rect):
    r = pygame.Rect(rect)

    def build():
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        s.blit(vgradient(r.w, r.h, (120, 34, 42, 255), (48, 14, 18, 255), 8), (0, 0))
        for k in range(-r.h, r.w, 8):
            pygame.draw.line(s, (255, 255, 255, 18), (k, r.h), (k + r.h, 0))
        pygame.draw.rect(s, (226, 182, 96), (0, 0, r.w, r.h), 1, border_radius=8)
        pygame.draw.rect(s, (226, 182, 96, 110), (4, 4, r.w - 8, r.h - 8), 1, border_radius=6)
        text(s, "A", (r.w // 2, r.h // 2), int(r.h * .4), (240, 200, 120), 3, center=True)
        return s
    surf.blit(shadow(r.w, r.h, 8, 6, 120), (r.x - 6, r.y - 6))
    surf.blit(_cached(("back", r.w, r.h), build), r)


class Floating:
    """Chữ nổi (sát thương, đánh giá...) có viền tối, phóng to rồi mờ dần."""
    def __init__(self, s, pos, color, size=26, life=1.3):
        self.s, self.x, self.y, self.color, self.size, self.life, self.t = s, pos[0], pos[1], color, size, life, 0

    def update(self, dt):
        self.t += dt
        self.y -= 36 * dt
        return self.t < self.life

    def draw(self, surf):
        k = min(1.0, self.t / 0.12)
        a = max(0, min(255, int(255 * (1 - self.t / self.life) * 1.6)))
        img = render(self.s, self.size, self.color, 3)
        out = render(self.s, self.size, (0, 0, 0), 3)
        sc = 0.6 + 0.4 * k + (0.15 * (1 - k))
        if sc != 1:
            img = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * sc)), max(1, int(img.get_height() * sc))))
            out = pygame.transform.smoothscale(out, img.get_size())
        img = img.copy()
        out = out.copy()
        img.set_alpha(a)
        out.set_alpha(int(a * .8))
        rr = img.get_rect(center=(self.x, self.y))
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            surf.blit(out, rr.move(dx, dy))
        surf.blit(img, rr)


def logo(surf, center, size=56, t=0.0):
    cx, cy = center
    g = radial(int(size * 3), ACCENT, int(60 + 20 * math.sin(t * 1.5)))
    surf.blit(g, (cx - size * 3, cy - size * 3))
    text(surf, "ALGO ARENA", (cx, cy + 3), size, (0, 0, 0), 3, center=True)
    img = render("ALGO ARENA", size, TEXT, 3)
    grad = vgradient(img.get_width(), img.get_height(), (*lighten(ACCENT, .45), 255), (*ACCENT2, 255))
    tinted = img.copy()
    tinted.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(tinted, tinted.get_rect(center=center))
