"""Đồ hoạ bàn đấu (vẽ thủ tục, không dùng ảnh ngoài): bàn gỗ, mặt da, khung chân dung hình vòm,
giọt máu, khiên giáp, pha lê năng lượng, bánh răng trang trí, nút kết thúc lượt."""
import math
import random

import pygame

import ui
from ui import W, H, mix, lighten, darken, text, vgradient, radial

GOLD_A = (236, 196, 112)
GOLD_B = (150, 104, 44)
GOLD_D = (92, 60, 24)

BOARD = pygame.Rect(96, 112, 1088, 500)

_cache = {}


def _c(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


# ------------------------------------------------------------------ bàn
def _gear(s, center, r, teeth, color, hole=(30, 18, 10)):
    cx, cy = center
    pts = []
    for i in range(teeth * 2):
        a = i * math.pi / teeth
        rr = r if i % 2 == 0 else r * 0.82
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    pygame.draw.polygon(s, darken(color, .35), [(x + 3, y + 4) for x, y in pts])
    pygame.draw.polygon(s, color, pts)
    pygame.draw.polygon(s, lighten(color, .3), pts, 2)
    pygame.draw.circle(s, darken(color, .2), center, int(r * .62))
    pygame.draw.circle(s, lighten(color, .2), center, int(r * .62), 2)
    pygame.draw.circle(s, hole, center, int(r * .24))


def _build_board():
    s = pygame.Surface((W, H))
    # gỗ tối toàn màn hình
    s.blit(vgradient(W, H, (58, 34, 20), (30, 17, 10)), (0, 0))
    rng = random.Random(3)
    for _ in range(260):
        y = rng.randint(0, H)
        x = rng.randint(-200, W)
        ln = rng.randint(80, 420)
        c = (70 + rng.randint(-10, 14), 42 + rng.randint(-8, 8), 24)
        pygame.draw.line(s, c, (x, y), (x + ln, y + rng.randint(-3, 3)), 1)
    # trang trí hai bên: tháp bánh răng
    for side in (-1, 1):
        bx = 46 if side < 0 else W - 46
        _gear(s, (bx, 200), 58, 12, (126, 84, 44))
        _gear(s, (bx + side * 10, 330), 40, 10, (150, 70, 120))
        _gear(s, (bx, 470), 64, 14, (70, 112, 96))
        _gear(s, (bx - side * 8, 600), 36, 9, (126, 84, 44))
        for k in range(4):
            pygame.draw.circle(s, (232, 210, 160), (bx + side * 24, 250 + k * 70), 5)
    # bóng bàn
    sh = ui.shadow(BOARD.w, BOARD.h, 48, 26, 200)
    s.blit(sh, (BOARD.x - 26, BOARD.y - 26))
    # viền gỗ chạm khắc
    outer = BOARD.inflate(36, 36)
    s.blit(vgradient(outer.w, outer.h, (120, 74, 40, 255), (74, 42, 22, 255), 58), outer)
    pygame.draw.rect(s, GOLD_B, outer, 3, border_radius=58)
    for k in range(0, outer.w, 34):
        pygame.draw.circle(s, darken(GOLD_B, .2), (outer.x + k + 17, outer.y + 9), 3)
        pygame.draw.circle(s, darken(GOLD_B, .2), (outer.x + k + 17, outer.bottom - 9), 3)
    # mặt da
    felt = vgradient(BOARD.w, BOARD.h, (186, 128, 92, 255), (150, 98, 70, 255), 44)
    s.blit(felt, BOARD)
    tex = pygame.Surface(BOARD.size, pygame.SRCALPHA)
    for _ in range(1600):
        x, y = rng.randint(0, BOARD.w), rng.randint(0, BOARD.h)
        tex.set_at((x, y), (255, 230, 200, rng.randint(10, 30)) if rng.random() < .5 else (60, 30, 10, rng.randint(10, 30)))
    s.blit(tex, BOARD)
    s.blit(radial(380, (255, 214, 160), 60), (BOARD.centerx - 380, BOARD.centery - 380))
    # vân trang trí (đường chỉ vàng bên trong)
    inner = BOARD.inflate(-26, -26)
    pygame.draw.rect(s, (214, 168, 100), inner, 2, border_radius=34)
    pygame.draw.rect(s, (120, 70, 40), inner.inflate(-10, -10), 1, border_radius=30)
    # đường giữa sân + huy hiệu
    cy = BOARD.centery
    for x0, x1 in ((inner.x + 30, BOARD.centerx - 60), (BOARD.centerx + 60, inner.right - 30)):
        pygame.draw.line(s, (120, 74, 44), (x0, cy), (x1, cy), 2)
        pygame.draw.line(s, (214, 168, 100), (x0, cy - 3), (x1, cy - 3), 1)
    pygame.draw.circle(s, GOLD_D, (BOARD.centerx, cy), 34)
    pygame.draw.circle(s, GOLD_A, (BOARD.centerx, cy), 34, 3)
    pygame.draw.circle(s, (120, 30, 36), (BOARD.centerx, cy), 24)
    text(s, "A", (BOARD.centerx, cy), 26, GOLD_A, 3, center=True)
    # 4 góc: hoa văn tròn
    for (x, y) in ((inner.x + 26, inner.y + 26), (inner.right - 26, inner.y + 26),
                   (inner.x + 26, inner.bottom - 26), (inner.right - 26, inner.bottom - 26)):
        pygame.draw.circle(s, GOLD_D, (x, y), 14)
        pygame.draw.circle(s, GOLD_A, (x, y), 14, 2)
        pygame.draw.circle(s, (150, 40, 50), (x, y), 6)
    # nền ô bài toán & nhật ký khắc chìm
    return s


def draw_board(surf):
    surf.blit(_c("board", _build_board), (0, 0))


# ------------------------------------------------------------------ khung chân dung vòm
def _arch_points(r, steps=24):
    x, y, w, h = r
    rad = w / 2
    pts = [(x, y + h), (x, y + rad)]
    for i in range(steps + 1):
        a = math.pi + i * math.pi / steps
        pts.append((x + rad + rad * math.cos(a), y + rad + rad * math.sin(a)))
    pts += [(x + w, y + rad), (x + w, y + h)]
    return pts


def _portrait(kind, letter, w, h):
    s = pygame.Surface((w + 24, h + 24), pygame.SRCALPHA)
    frame = pygame.Rect(4, 4, w + 16, h + 16)
    pic = pygame.Rect(12, 12, w, h)
    # khung vàng
    pygame.draw.polygon(s, (40, 22, 8), _arch_points(frame.move(3, 4)))
    pygame.draw.polygon(s, GOLD_B, _arch_points(frame))
    pygame.draw.polygon(s, GOLD_A, _arch_points(frame), 3)
    pygame.draw.polygon(s, GOLD_D, _arch_points(pic.inflate(6, 6)))
    # tranh: nền màu + biểu tượng
    art = pygame.Surface(pic.size, pygame.SRCALPHA)
    if kind == "ai":
        art.blit(vgradient(w, h, (120, 36, 40, 255), (40, 12, 16, 255)), (0, 0))
        cx, cy = w // 2, h // 2 + 10
        for i in range(12):
            a = i * math.pi / 6
            pygame.draw.line(art, (255, 140, 90, 60), (cx, cy), (cx + math.cos(a) * w, cy + math.sin(a) * w), 6)
        art.blit(radial(60, (255, 160, 90), 140), (cx - 60, cy - 60))
        # "mặt" robot cách điệu
        head = pygame.Rect(0, 0, 70, 62)
        head.center = (cx, cy)
        pygame.draw.rect(art, (60, 40, 46), head, border_radius=14)
        pygame.draw.rect(art, (255, 170, 110), head, 3, border_radius=14)
        pygame.draw.circle(art, (255, 220, 120), (cx - 15, cy - 4), 8)
        pygame.draw.circle(art, (255, 220, 120), (cx + 15, cy - 4), 8)
        pygame.draw.line(art, (255, 170, 110), (cx - 14, cy + 18), (cx + 14, cy + 18), 3)
        pygame.draw.line(art, (255, 170, 110), (cx, head.y), (cx, head.y - 14), 3)
        pygame.draw.circle(art, (255, 220, 120), (cx, head.y - 16), 5)
    else:
        art.blit(vgradient(w, h, (40, 96, 120, 255), (14, 30, 46, 255)), (0, 0))
        cx, cy = w // 2, h // 2 + 8
        for i in range(12):
            a = i * math.pi / 6
            pygame.draw.line(art, (140, 230, 255, 50), (cx, cy), (cx + math.cos(a) * w, cy + math.sin(a) * w), 6)
        art.blit(radial(64, (150, 230, 255), 130), (cx - 64, cy - 64))
        pygame.draw.circle(art, (20, 46, 66), (cx, cy), 40)
        pygame.draw.circle(art, (160, 230, 255), (cx, cy), 40, 3)
        text(art, letter, (cx, cy + 1), 40, (230, 248, 255), 3, center=True)
    mask = pygame.Surface(pic.size, pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), _arch_points((0, 0, w, h)))
    art.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(art, pic)
    pygame.draw.polygon(s, (255, 230, 170), _arch_points(pic), 2)
    # bệ dưới
    pygame.draw.rect(s, GOLD_B, (frame.x - 2, frame.bottom - 10, frame.w + 4, 12), border_radius=4)
    pygame.draw.rect(s, GOLD_A, (frame.x - 2, frame.bottom - 10, frame.w + 4, 12), 2, border_radius=4)
    return s


def draw_portrait(surf, rect, kind, letter, glow_color=None, shake=0.0, t=0.0):
    r = pygame.Rect(rect)
    if glow_color:
        g = ui.glow(r.w + 12, r.h + 12, glow_color, r.w // 2, 22, int(150 + 60 * math.sin(t * 4)))
        surf.blit(g, (r.x - 28, r.y - 28))
    img = _c(("portrait", kind, letter, r.w, r.h), lambda: _portrait(kind, letter, r.w, r.h))
    dx = int(math.sin(t * 70) * 6 * shake)
    surf.blit(img, (r.x - 12 + dx, r.y - 12))


def health_drop(surf, center, hp, max_hp):
    cx, cy = center
    col = (210, 40, 46) if hp > 10 else (255, 60, 50)
    pygame.draw.circle(surf, (40, 8, 8), (cx + 2, cy + 7), 21)
    pygame.draw.polygon(surf, (40, 8, 8), [(cx + 2, cy - 23), (cx + 18, cy), (cx - 14, cy)])
    pygame.draw.circle(surf, col, (cx, cy + 5), 19)
    pygame.draw.polygon(surf, col, [(cx, cy - 26), (cx + 16, cy - 2), (cx - 16, cy - 2)])
    pygame.draw.circle(surf, lighten(col, .35), (cx - 7, cy - 2), 5)
    pygame.draw.circle(surf, (255, 220, 180), (cx, cy + 5), 19, 2)
    text(surf, str(max(0, hp)), (cx, cy + 6), 20 if hp < 100 else 16, (255, 255, 255), 3, center=True, shadow=True)


def armor_shield(surf, center, value):
    cx, cy = center
    pts = [(cx, cy - 20), (cx + 17, cy - 13), (cx + 14, cy + 8), (cx, cy + 20), (cx - 14, cy + 8), (cx - 17, cy - 13)]
    pygame.draw.polygon(surf, (30, 30, 40), [(x + 2, y + 3) for x, y in pts])
    pygame.draw.polygon(surf, (150, 160, 176), pts)
    pygame.draw.polygon(surf, (230, 236, 246), pts, 2)
    text(surf, str(value), (cx, cy), 16, (255, 255, 255), 3, center=True, shadow=True)


def round_gem(surf, center, r, color, value, label=None):
    cx, cy = center
    pygame.draw.circle(surf, (24, 14, 8), (cx + 2, cy + 3), r + 6)
    pygame.draw.circle(surf, GOLD_B, (cx, cy), r + 6)
    pygame.draw.circle(surf, GOLD_A, (cx, cy), r + 6, 2)
    surf.blit(vgradient(r * 2, r * 2, (*lighten(color, .3), 255), (*darken(color, .4), 255), r), (cx - r, cy - r))
    pygame.draw.circle(surf, lighten(color, .5), (cx - r // 3, cy - r // 3), max(3, r // 4))
    text(surf, str(value), (cx, cy), int(r * .9), (255, 255, 255), 3, center=True, shadow=True)
    if label:
        text(surf, label, (cx, cy + r + 16), 11, (250, 236, 210), 3, center=True, shadow=True)


def mana_bar(surf, rect, energy, max_energy, total=8):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, (24, 14, 8), r.move(2, 3), border_radius=r.h // 2)
    surf.blit(vgradient(r.w, r.h, (70, 46, 28, 255), (40, 24, 14, 255), r.h // 2), r)
    pygame.draw.rect(surf, GOLD_B, r, 2, border_radius=r.h // 2)
    text(surf, f"{energy}/{max_energy}", (r.x + 34, r.centery), 17, (255, 255, 255), 3, center=True, shadow=True)
    for k in range(total):
        cx, cy = r.x + 78 + k * 26, r.centery
        pts = [(cx, cy - 11), (cx + 9, cy - 3), (cx + 6, cy + 10), (cx - 6, cy + 10), (cx - 9, cy - 3)]
        if k < energy:
            pygame.draw.polygon(surf, (80, 150, 255), pts)
            pygame.draw.polygon(surf, (200, 230, 255), pts, 1)
            pygame.draw.line(surf, (220, 240, 255), (cx - 3, cy - 6), (cx, cy - 9), 2)
        elif k < max_energy:
            pygame.draw.polygon(surf, (40, 50, 80), pts)
            pygame.draw.polygon(surf, (110, 130, 170), pts, 1)
        else:
            pygame.draw.polygon(surf, (50, 34, 22), pts)
            pygame.draw.polygon(surf, (90, 66, 44), pts, 1)


def deck_pile(surf, center, count):
    cx, cy = center
    for k in range(min(5, max(1, count // 3 + 1)) if count else 0):
        r = pygame.Rect(0, 0, 44, 62)
        r.center = (cx - k * 2, cy - k * 2)
        ui.draw_card_back(surf, r)
    if not count:
        pygame.draw.rect(surf, (60, 36, 22), (cx - 22, cy - 31, 44, 62), 2, border_radius=8)
    text(surf, str(count), (cx, cy + 46), 13, (250, 236, 210), 3, center=True, shadow=True)


def end_turn_button(surf, rect, active, hover, t, label="KẾT THÚC LƯỢT", sub=None):
    r = pygame.Rect(rect)
    if active:
        pulse = int(120 + 80 * math.sin(t * 4))
        surf.blit(ui.glow(r.w, r.h, (120, 255, 140) if not sub else (255, 200, 90), r.h // 2, 20, pulse), (r.x - 20, r.y - 20))
    pygame.draw.rect(surf, (24, 14, 8), r.move(3, 4), border_radius=r.h // 2)
    if active:
        top, bot, fg = ((140, 220, 90), (60, 140, 40), (20, 40, 6)) if not sub else ((255, 214, 110), (190, 130, 40), (50, 28, 4))
    else:
        top, bot, fg = (120, 100, 80), (80, 64, 50), (210, 196, 176)
    if hover and active:
        top, bot = lighten(top, .15), lighten(bot, .1)
    surf.blit(vgradient(r.w, r.h, (*top, 255), (*bot, 255), r.h // 2), r)
    surf.blit(vgradient(r.w, r.h // 2, (255, 255, 255, 60), (255, 255, 255, 0), r.h // 2), r)
    pygame.draw.rect(surf, GOLD_A, r, 3, border_radius=r.h // 2)
    text(surf, label, (r.centerx, r.centery - (7 if sub else 0)), 16, fg, 3, center=True)
    if sub:
        text(surf, sub, (r.centerx, r.centery + 12), 11, fg, 2, center=True)


def scroll_plaque(surf, rect):
    r = pygame.Rect(rect)

    def build():
        s = pygame.Surface((r.w + 40, r.h + 30), pygame.SRCALPHA)
        body = pygame.Rect(20, 12, r.w, r.h)
        s.blit(ui.shadow(r.w, r.h, 16, 12, 160), (body.x - 12, body.y - 12))
        s.blit(vgradient(r.w, r.h, (250, 232, 196, 255), (222, 192, 142, 255), 14), body)
        rng = random.Random(9)
        for _ in range(400):
            s.set_at((body.x + rng.randint(2, r.w - 3), body.y + rng.randint(2, r.h - 3)), (160, 120, 70, rng.randint(20, 50)))
        pygame.draw.rect(s, (150, 104, 54), body, 3, border_radius=14)
        pygame.draw.rect(s, (196, 150, 90), body.inflate(-12, -12), 1, border_radius=10)
        for x in (body.x - 6, body.right - 14):
            pygame.draw.rect(s, (120, 70, 36), (x, body.y - 8, 20, r.h + 16), border_radius=8)
            pygame.draw.rect(s, GOLD_A, (x, body.y - 8, 20, r.h + 16), 2, border_radius=8)
        return s
    surf.blit(_c(("plaque", r.w, r.h), build), (r.x - 20, r.y - 12))


def fan_card(card_surface_fn, cid, angle, key_extra):
    """Ảnh thẻ đã xoay (cache)."""
    key = ("fan", cid, round(angle, 1), key_extra)
    if key not in _cache:
        base = card_surface_fn()
        _cache[key] = pygame.transform.rotozoom(base, angle, 1.0)
        if len(_cache) > 400:
            for k in [k for k in _cache if k[0] == "fan"][:100]:
                _cache.pop(k, None)
    return _cache[key]
