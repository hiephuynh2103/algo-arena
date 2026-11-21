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


def wash(surf, rect, pigment="paper", edge=None):
    """A real pigment wash cut to a slightly uneven pen contour."""
    r = pygame.Rect(rect)
    if min(r.size) < 1:
        return
    def paint():
        tile = pygame.Surface(r.size, pygame.SRCALPHA)
        plate(tile, pigment, tile.get_rect(), cover=True)
        rng = random.Random(r.w * 73 + r.h)
        w, h = r.w - 1, r.h - 1
        points = [(2, 1)]
        for x in range(18, w-4, 22):
            points.append((x, rng.choice((0, 1, 1, 2))))
        points += [(w-2, 1), (w, h//2), (w-1, h-2)]
        for x in range(w-16, 4, -25):
            points.append((x, h-rng.choice((0, 1, 2))))
        points += [(1, h-1), (0, h//2)]
        mask = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255,255,255), points)
        tile.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        if edge:
            pygame.draw.aalines(tile, edge, True, points)
        return tile
    surf.blit(_cached(("watercolor", r.size, pigment, edge), paint), r)


def draw_background(surf, t=0.0):
    plate(surf, "paper", (0, 0, W, H), cover=True)
    plate(surf, "journey", (0, 0, W, 68), cover=True)
    wash(surf, (W//2-300, 5, 600, 55), "indigo")


def panel(surf, rect, color=None, border=None, radius=14, width=1, glass=True, shadow_on=True, accent=None):
    r = pygame.Rect(rect)
    wash(surf, r, "indigo", accent or border or RULE)


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
        draw_book_button(self, surf)


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
        wash(surf, r, "paper", OCHRE if self.focus else RULE)
        shown = ("•" * len(self.value)) if self.password else self.value
        inner = r.inflate(-26, -6)
        old = surf.get_clip()
        surf.set_clip(old.clip(inner))
        label = shown or self.placeholder
        img = render(label, 17, INK if shown else SLATE)
        x = min(inner.x, inner.right - img.get_width()-3)
        surf.blit(img, (x, r.centery-img.get_height()//2))
        if self.focus and int(self.t*2)%2 == 0:
            cx = x + img.get_width()+1 if shown else inner.x
            pygame.draw.line(surf, OCHRE, (cx,r.y+11),(cx,r.bottom-11),2)
        surf.set_clip(old)


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
def draw_card(surf, rect, cid, playable=True, highlight=False, locked=False, compact=False, badge=None, lift=0):
    import board
    r = pygame.Rect(rect).move(0, -lift)
    if r.h < 100:
        wash(surf, r, "paper", RULE)
        text_box(surf, CARDS[cid]["name"], r.inflate(-6,-6), 11, INK, 2)
        return
    board.card(surf, r, cid, playable, highlight, badge)
    if locked:
        tag = pygame.Rect(r.x+3, r.bottom-26, r.w-6, 23)
        wash(surf, tag, "indigo")
        text(surf, "Chưa mở khoá", tag.center, 11, CREAM, 2, center=True)


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
    text(surf, "ALGO ARENA", center, size, INK, 3, center=True)




INK = (20, 37, 48)
NAVY = (26, 48, 60)
SLATE = (46, 70, 80)
RULE = (76, 96, 100)
PAPER = (233, 223, 197)
CREAM = (248, 240, 217)
SAND = (195, 187, 165)
STEEL = (171, 190, 189)
AMBER = (241, 183, 82)
OCHRE = (135, 82, 34)


def plate(surf, name, rect, cover=False):
    """Scale once from the master illustration, with a centered crop or inset."""
    r = pygame.Rect(rect)
    def load():
        filename = os.path.join(HERE, "assets", "fieldbook", name + ".jpg")
        return pygame.image.load(filename).convert()
    source = _cached(("plate-master", name), load)

    def resize():
        if cover:
            crop = r.fit(source.get_rect())
            crop.center = source.get_rect().center
            return pygame.transform.smoothscale(source.subsurface(crop), r.size)
        return pygame.transform.smoothscale(source, source.get_rect().fit(r).size)
    art = _cached(("plate", name, r.size, cover), resize)
    surf.blit(art, art.get_rect(center=r.center))


class BookButton(Button):
    """Notebook menu controls share the standard button renderer."""


def draw_book_button(button, surf):
    r = button.rect
    row = button.kind == "row"
    primary = button.kind in ("primary", "gold")
    pigment = "ochre" if primary else "paper" if row else "indigo"
    if not button.enabled:
        pigment = "sage"
    elif button.hover:
        pigment = "paper" if primary else "sage"
    fg = CREAM if pigment == "indigo" else INK
    wash(surf, r, pigment, OCHRE if button.hover else RULE)
    if row:
        icon(surf, button.icon, (r.x + 19, r.centery), 21, OCHRE)
        text(surf, button.label, (r.x + 46, r.centery - font(button.size, 2).get_height() // 2), button.size, fg, 2)
        icon(surf, "next", (r.right - 16, r.centery), 11, OCHRE)
    else:
        width, height = text_size(button.label, button.size, 2)
        gap = 8 if button.label and button.icon else 0
        side = button.size if button.icon else 0
        x = r.centerx - (width + side + gap) // 2
        if button.icon:
            icon(surf, button.icon, (x + side // 2, r.centery), side, fg)
        text(surf, button.label, (x + side + gap, r.centery - height // 2), button.size, fg, 2)


def fit_text(surf, label, rect, size, color=INK, weight=2):
    r = pygame.Rect(rect)
    while size > 10 and text_size(label, size, weight)[0] > r.w:
        size -= 1
    old = surf.get_clip()
    surf.set_clip(old.clip(r))
    text(surf, label, (r.x, r.centery - font(size, weight).get_height() // 2), size, color, weight)
    surf.set_clip(old)
