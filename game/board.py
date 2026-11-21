"""Illustrated field notes and card faces for the battle scene."""
import pygame
import ui
from ui import INK, NAVY, SLATE, RULE, PAPER, CREAM, SAND, STEEL, AMBER, OCHRE
from engine import CARDS, CATEGORY_LABEL, card_cost_label

FAMILY_ART = {"graph": "graph", "search": "search", "sort": "sort", "paradigm": "choice", "ds": "index"}
CARD_ART = {"stack": "stack", "undo": "stack", "queue": "queue", "heap": "queue", "dp": "plan"}


def card(surf, rect, cid, playable=True, selected=False, badge=None):
    r = pygame.Rect(rect)
    c = CARDS[cid]
    def paint():
        s = pygame.Surface(r.size)
        s.fill(CREAM if selected else PAPER)
        # A square illustration above the title keeps the subject intact at every hand size.
        top = 8
        side = min(r.w - 16, r.h - 82)
        art = pygame.Rect((r.w - side) // 2, top, side, side)
        ui.plate(s, CARD_ART.get(cid, FAMILY_ART[c["cat"]]), art)
        cost = pygame.Rect(6, 6, 25, 27)
        pygame.draw.rect(s, AMBER if selected else NAVY, cost, border_radius=3)
        ui.text(s, card_cost_label(cid), cost.center, 16, INK if selected else CREAM, 3, center=True)
        y = art.bottom + 6
        fs = 15 if r.w >= 148 else 13
        lines = ui.wrap(c["name"], fs, r.w - 14, 3)
        while len(lines) > 2 and fs > 11:
            fs -= 1
            lines = ui.wrap(c["name"], fs, r.w - 14, 3)
        for line in lines:
            ui.text(s, line, (8, y), fs, INK, 3)
            y += ui.font(fs, 3).get_linesize() - 2
        pygame.draw.line(s, SAND, (8, r.h - 24), (r.w - 9, r.h - 24))
        ui.fit_text(s, CATEGORY_LABEL[c["cat"]], (8, r.h - 23, r.w - 15, 21), 11, OCHRE)
        if not playable:
            pygame.draw.rect(s, SLATE, cost, border_radius=3)
            ui.text(s, card_cost_label(cid), cost.center, 16, CREAM, 3, center=True)
        return s
    face = ui._cached(("field-card", cid, r.size, playable, selected), paint)
    pygame.draw.rect(surf, INK, r.move(2, 3))
    surf.blit(face, r)
    if selected:
        pygame.draw.rect(surf, AMBER, r.inflate(4, 4), 3, border_radius=2)
    if badge:
        label, color = badge
        tag = pygame.Rect(0, 0, ui.text_size(label, 11, 3)[0] + 14, 20)
        tag.topright = r.topright
        pygame.draw.rect(surf, color, tag)
        ui.text(surf, label, tag.center, 11, INK, 3, center=True)


def detail(surf, cid, pos):
    c = CARDS[cid]
    w = 270
    groups = [(c["name"], 20, CREAM, 3),
              (f"Chi phí {card_cost_label(cid)}   ·   {c['complexity']}", 14, AMBER, 2),
              (c["text"], 14, CREAM, 1), (c["lesson"], 13, STEEL, 0)]
    rows = [(ui.wrap(value, size, w - 34, weight), size, color, weight)
            for value, size, color, weight in groups]
    h = 24 + sum(len(lines) * ui.font(size, weight).get_linesize() + 6 for lines, size, _, weight in rows)
    r = pygame.Rect(pos, (w, h))
    pygame.draw.rect(surf, NAVY, r)
    pygame.draw.rect(surf, SAND, r, 1)
    pygame.draw.rect(surf, AMBER, (r.x, r.y, 4, h))
    y = r.y + 12
    for lines, size, color, weight in rows:
        for line in lines:
            ui.text(surf, line, (r.x + 17, y), size, color, weight)
            y += ui.font(size, weight).get_linesize()
        y += 6
    return r


def board(surf):
    surf.fill(INK)
    # Navy cloth, mat seam and plain ivory note surfaces.
    pygame.draw.rect(surf, NAVY, (0, 62, ui.W, 395))
    pygame.draw.rect(surf, (31, 55, 66), (0, 155, ui.W, 209))
    for y in (61, 154, 363, 456):
        pygame.draw.line(surf, RULE, (0, y), (ui.W, y))
