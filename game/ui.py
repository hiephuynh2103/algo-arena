"""Thành phần giao diện dùng chung: font, màu, chữ xuống dòng, nút, thẻ bài."""
import os
import pygame

from engine import CARDS, CATEGORY_LABEL, card_cost_label

W, H = 1280, 720
HERE = os.path.dirname(os.path.abspath(__file__))

BG = (13, 18, 32)
PANEL = (21, 28, 47)
PANEL2 = (28, 37, 64)
LINE = (42, 53, 86)
TEXT = (231, 236, 247)
MUTED = (147, 160, 191)
ACCENT = (45, 212, 191)
ACCENT2 = (124, 140, 255)
GOLD = (245, 196, 81)
RED = (248, 113, 113)
GREEN = (74, 222, 128)
ORANGE = (251, 146, 60)
BLUE = (96, 165, 250)
PINK = (244, 114, 182)

CAT_COLOR = {"ds": (20, 120, 110), "search": (37, 99, 235), "sort": (124, 58, 237),
             "graph": (194, 92, 20), "paradigm": (190, 50, 120)}
RATING_COLOR = {"optimal": GREEN, "acceptable": GOLD, "trap": RED, "missed": ORANGE,
                "failed": RED, "neutral": MUTED}
RATING_LABEL = {"optimal": "TỐI ƯU", "acceptable": "CHƯA TỐI ƯU", "trap": "BẪY",
                "missed": "BỎ LỠ", "failed": "THẤT BẠI", "neutral": ""}

_fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        path = os.path.join(HERE, "assets", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        try:
            _fonts[key] = pygame.font.Font(path, size)
        except Exception:
            _fonts[key] = pygame.font.Font(None, size + 4)
    return _fonts[key]


def text(surf, s, pos, size=16, color=TEXT, bold=False, center=False, right=False):
    img = font(size, bold).render(str(s), True, color)
    r = img.get_rect()
    if center:
        r.center = pos
    elif right:
        r.topright = pos
    else:
        r.topleft = pos
    surf.blit(img, r)
    return r


def wrap(s, size, width, bold=False):
    f = font(size, bold)
    lines = []
    for para in str(s).split("\n"):
        words = para.split(" ")
        cur = ""
        for w_ in words:
            t = (cur + " " + w_).strip()
            if f.size(t)[0] <= width:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w_
        lines.append(cur)
    return lines


def text_box(surf, s, rect, size=14, color=TEXT, bold=False, line_gap=3, max_lines=None):
    x, y, w, h = rect
    lh = font(size, bold).get_linesize() + line_gap - 4
    lines = wrap(s, size, w, bold)
    if max_lines:
        lines = lines[:max_lines]
    for ln in lines:
        if y + lh > rect[1] + h + 2:
            break
        text(surf, ln, (x, y), size, color, bold)
        y += lh
    return y


def panel(surf, rect, color=PANEL, border=LINE, radius=12, width=1):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, width, border_radius=radius)


def bar(surf, rect, frac, color=ACCENT, back=(15, 21, 40)):
    pygame.draw.rect(surf, back, rect, border_radius=rect[3] // 2)
    frac = max(0.0, min(1.0, frac))
    if frac > 0:
        r = pygame.Rect(rect)
        r.w = max(r.h, int(r.w * frac))
        pygame.draw.rect(surf, color, r, border_radius=rect[3] // 2)


class Button:
    def __init__(self, rect, label, cb=None, kind="normal", size=17, enabled=True, tip=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.cb = cb
        self.kind = kind
        self.size = size
        self.enabled = enabled
        self.hover = False
        self.tip = tip

    def draw(self, surf):
        if self.kind == "primary":
            c = ACCENT if self.enabled else (40, 70, 70)
            fg = (6, 32, 28)
        elif self.kind == "danger":
            c, fg = (70, 30, 38), (254, 202, 202)
        elif self.kind == "ghost":
            c, fg = PANEL, MUTED
        else:
            c, fg = PANEL2, TEXT
        if not self.enabled:
            fg = MUTED
        if self.hover and self.enabled:
            c = tuple(min(255, v + 25) for v in c)
        pygame.draw.rect(surf, c, self.rect, border_radius=10)
        if self.kind != "primary":
            pygame.draw.rect(surf, ACCENT if (self.hover and self.enabled) else LINE, self.rect, 1, border_radius=10)
        text(surf, self.label, self.rect.center, self.size, fg, bold=True, center=True)

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
        panel(surf, self.rect, (15, 21, 40), ACCENT if self.focus else LINE, 10)
        shown = ("•" * len(self.value)) if self.password else self.value
        if shown:
            r = text(surf, shown, (self.rect.x + 12, self.rect.y + 10), 18)
        else:
            r = text(surf, self.placeholder, (self.rect.x + 12, self.rect.y + 10), 18, MUTED)
            r.w = 0
        if self.focus and int(self.t * 2) % 2 == 0:
            x = self.rect.x + 12 + (r.w if shown else 0) + 2
            pygame.draw.line(surf, TEXT, (x, self.rect.y + 10), (x, self.rect.bottom - 10), 2)


# ---------------------------------------------------------------- Thẻ bài
_card_cache = {}


def _card_face(cid, w, h, compact):
    key = (cid, w, h, compact)
    if key in _card_cache:
        return _card_cache[key]
    c = CARDS[cid]
    base = CAT_COLOR[c["cat"]]
    top = tuple(min(255, int(v * 1.05) + 10) for v in base)
    bottom = tuple(int(v * 0.45) for v in base)
    card = pygame.Surface((w, h), pygame.SRCALPHA)
    for yy in range(h):
        t = yy / max(1, h - 1)
        col = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        pygame.draw.line(card, col, (0, yy), (w, yy))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=12)
    card.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    # chi phí
    pygame.draw.circle(card, (12, 16, 30), (18, 18), 15)
    text(card, card_cost_label(cid), (18, 18), 16, TEXT, True, center=True)
    pad = 8
    fs = 12 if compact else 13
    y = 7
    for ln in wrap(c["name"], fs, w - 44, bold=True)[:2]:
        text(card, ln, (38, y), fs, TEXT, True)
        y += 16
    y = max(y, 38)
    text(card, CATEGORY_LABEL[c["cat"]], (pad, y), 10, (220, 225, 240))
    y += 14
    text(card, c["complexity"], (pad, y), 10, GOLD)
    y += 18
    if not compact:
        pygame.draw.line(card, (200, 205, 225), (pad, y - 3), (w - pad, y - 3))
        text_box(card, c["text"], (pad, y, w - 2 * pad, h - y - 6), 11, (235, 238, 248))
    _card_cache[key] = card
    return card


def draw_card(surf, rect, cid, playable=True, highlight=False, locked=False, compact=False, badge=None):
    r = pygame.Rect(rect)
    surf.blit(_card_face(cid, r.w, r.h, compact), r)
    border = GOLD if highlight else ((255, 255, 255) if playable else (60, 60, 80))
    pygame.draw.rect(surf, border, r, 3 if highlight else 1, border_radius=12)
    pygame.draw.circle(surf, ACCENT2 if playable else MUTED, (r.x + 18, r.y + 18), 15, 2)
    if locked:
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        s.fill((10, 12, 20, 170))
        surf.blit(s, r)
        text(surf, "✖ Chưa mở khoá", r.center, 13, MUTED, True, center=True)
    if not playable and not locked:
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        s.fill((10, 12, 20, 90))
        surf.blit(s, r)
    if badge:
        label, col = badge
        bw = font(11, True).size(label)[0] + 12
        br = pygame.Rect(r.right - bw - 4, r.y - 9, bw, 18)
        pygame.draw.rect(surf, col, br, border_radius=9)
        text(surf, label, br.center, 11, (10, 12, 20), True, center=True)


def draw_card_detail(surf, pos, cid, extra=None):
    """Khung phóng to khi rê chuột: hiệu ứng + bài học."""
    c = CARDS[cid]
    w, h = 300, 250
    x = min(max(10, pos[0]), W - w - 10)
    y = min(max(10, pos[1]), H - h - 10)
    r = pygame.Rect(x, y, w, h)
    panel(surf, r, (18, 24, 42), ACCENT, 12, 2)
    text(surf, c["name"], (x + 14, y + 12), 17, TEXT, True)
    text(surf, f"Chi phí {card_cost_label(cid)} · {CATEGORY_LABEL[c['cat']]} · {c['complexity']}", (x + 14, y + 38), 12, GOLD)
    yy = text_box(surf, c["text"], (x + 14, y + 62, w - 28, 80), 13)
    pygame.draw.line(surf, LINE, (x + 14, yy + 4), (x + w - 14, yy + 4))
    text_box(surf, "★ " + c["lesson"], (x + 14, yy + 12, w - 28, h - (yy - y) - 20), 12, MUTED)
    if extra:
        text(surf, extra, (x + 14, y + h - 22), 12, ACCENT)


def draw_card_back(surf, rect):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, (35, 44, 80), r, border_radius=8)
    pygame.draw.rect(surf, ACCENT2, r, 1, border_radius=8)
    text(surf, "{ }", r.center, 14, ACCENT2, True, center=True)


class Floating:
    """Chữ nổi (sát thương, đánh giá...)"""
    def __init__(self, s, pos, color, size=26, life=1.3):
        self.s, self.x, self.y, self.color, self.size, self.life, self.t = s, pos[0], pos[1], color, size, life, 0

    def update(self, dt):
        self.t += dt
        self.y -= 40 * dt
        return self.t < self.life

    def draw(self, surf):
        a = max(0, min(255, int(255 * (1 - self.t / self.life) * 1.5)))
        img = font(self.size, True).render(self.s, True, self.color)
        img.set_alpha(a)
        surf.blit(img, img.get_rect(center=(self.x, self.y)))
