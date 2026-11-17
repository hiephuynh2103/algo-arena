import pygame

import ui
from ui import W, H, text, text_box, panel, Button, TEXT, MUTED, ACCENT, ACCENT2, GOLD, RED, GREEN, LINE, PANEL, PANEL2
from scenes_base import Scene, back_button
from engine import CARDS, CATEGORY_LABEL, DECK_SIZE, MAX_COPIES, STARTER_DECK, validate_deck, card_cost_label

CW, CH = 128, 176
GRID_X, GRID_Y = 20, 120
COLS = 6


def unlock_text(cid):
    out = []
    for u in CARDS[cid]["unlock"]:
        if u.startswith("level:"):
            out.append("cấp " + u.split(":")[1])
        elif u.startswith("puzzle:"):
            out.append("thử thách " + u.split(":")[1].upper())
    return "Mở khoá: " + " hoặc ".join(out) if out else ""


class DeckScene(Scene):
    title = "Xây dựng bộ bài"

    def enter(self):
        from scenes_menu import MenuScene
        a = self.app
        self.deck = list(a.deck)
        self.filter = None
        self.scroll = 0
        self.hover = None
        self.msg = ""
        self.saving = False
        self.buttons = [back_button(a, lambda: MenuScene(a))]
        cats = [(None, "Tất cả")] + list(CATEGORY_LABEL.items())
        for i, (k, lab) in enumerate(cats):
            b = Button((GRID_X + i * 140, 70, 132, 36), lab, lambda k=k: self.set_filter(k), size=13)
            b.cat = k
            self.buttons.append(b)
        self.buttons += [
            Button((900, 600, 170, 46), "Lưu bộ bài", self.save, "primary"),
            Button((1078, 600, 182, 46), "Bộ khởi đầu", self.reset, size=15),
            Button((900, 654, 360, 36), "Xoá hết", lambda: self.deck.clear(), "ghost", 14),
        ]

    def set_filter(self, k):
        self.filter = k
        self.scroll = 0

    def reset(self):
        self.deck = list(STARTER_DECK)

    def visible(self):
        ids = [c for c in CARDS if self.filter is None or CARDS[c]["cat"] == self.filter]
        un = self.app.unlocked
        return sorted(ids, key=lambda c: (c not in un, CARDS[c]["cost"], CARDS[c]["name"]))

    def grid_rect(self, idx):
        row, col = divmod(idx, COLS)
        return pygame.Rect(GRID_X + col * (CW + 12), GRID_Y + (row - self.scroll) * (CH + 14), CW, CH)

    def save(self):
        ok, msg = validate_deck(self.deck, self.app.unlocked)
        if not ok:
            self.msg = msg
            return
        a = self.app
        if not a.user:
            a.local_deck = list(self.deck)
            a.toast("Đã lưu bộ bài (offline)")
            return
        if self.saving:
            return
        self.saving = True
        body = {"name": "Bộ bài chính", "cards": self.deck, "activate": True}
        did = a.user.get("active_deck_id")
        coro = a.net.put(f"/api/decks/{did}", body) if did else a.net.post("/api/decks", body)

        def done(_):
            def got(me):
                a.user = me
                self.saving = False
                a.toast("Đã lưu bộ bài lên máy chủ", GREEN)
            a.spawn(a.net.get("/api/me"), got)
            a.spawn(a.net.post("/api/events", {"type": "deck_builder_save", "data": {"size": len(self.deck)}}))

        def fail(e):
            self.saving = False
            self.msg = str(e)

        a.spawn(coro, done, fail)

    def handle(self, e):
        if super().handle(e):
            return True
        vis = self.visible()
        if e.type == pygame.MOUSEWHEEL:
            rows = (len(vis) + COLS - 1) // COLS
            self.scroll = max(0, min(max(0, rows - 3), self.scroll - e.y))
        elif e.type == pygame.MOUSEMOTION:
            self.hover = None
            for i, cid in enumerate(vis):
                r = self.grid_rect(i)
                if r.collidepoint(e.pos) and r.y >= GRID_Y - 5:
                    self.hover = cid
            for i, (cid, r) in enumerate(self.deck_rows()):
                if r.collidepoint(e.pos):
                    self.hover = cid
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, cid in enumerate(vis):
                r = self.grid_rect(i)
                if r.collidepoint(e.pos) and r.y >= GRID_Y - 5 and r.bottom <= H:
                    self.add(cid)
                    return True
            for cid, r in self.deck_rows():
                if r.collidepoint(e.pos):
                    self.deck.remove(cid)
                    self.msg = ""
                    return True
        return False

    def add(self, cid):
        if cid not in self.app.unlocked:
            self.msg = f"Chưa mở khoá {CARDS[cid]['name']}. {unlock_text(cid)}"
        elif len(self.deck) >= DECK_SIZE:
            self.msg = f"Bộ bài đã đủ {DECK_SIZE} thẻ. Bấm vào thẻ bên phải để bỏ bớt."
        elif self.deck.count(cid) >= MAX_COPIES:
            self.msg = f"Tối đa {MAX_COPIES} bản mỗi thẻ"
        else:
            self.deck.append(cid)
            self.msg = ""

    def deck_rows(self):
        uniq = sorted(set(self.deck), key=lambda c: (CARDS[c]["cost"], CARDS[c]["name"]))
        return [(cid, pygame.Rect(900, 136 + i * 30, 360, 27)) for i, cid in enumerate(uniq)]

    def draw(self, surf):
        super().draw(surf)
        for b in self.buttons:
            if hasattr(b, "cat"):
                if b.cat == self.filter:
                    pygame.draw.rect(surf, ACCENT, b.rect, 2, border_radius=10)
        vis = self.visible()
        un = self.app.unlocked
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(0, GRID_Y - 12, 880, H - GRID_Y + 12))
        for i, cid in enumerate(vis):
            r = self.grid_rect(i)
            if r.bottom < GRID_Y - 12 or r.y > H:
                continue
            n = self.deck.count(cid)
            badge = (f"{n}/{MAX_COPIES}", GOLD) if n else None
            ui.draw_card(surf, r, cid, playable=cid in un, locked=cid not in un, compact=True, badge=badge,
                         highlight=self.hover == cid)
            if cid in un:
                text_box(surf, CARDS[cid]["text"], (r.x + 8, r.y + 76, r.w - 16, r.h - 80), 10, (225, 230, 245))
        surf.set_clip(clip)

        # Bộ bài hiện tại
        R = pygame.Rect(890, 70, 380, 520)
        panel(surf, R)
        n = len(self.deck)
        text(surf, "Bộ bài của bạn", (R.x + 14, R.y + 14), 18, TEXT, True)
        text(surf, f"{n}/{DECK_SIZE}", (R.right - 14, R.y + 14), 18, GREEN if n == DECK_SIZE else GOLD, True, right=True)
        text(surf, "Bấm thẻ bên trái để thêm, bấm dòng bên dưới để bỏ", (R.x + 14, R.y + 46), 11, MUTED)
        mp = pygame.mouse.get_pos()
        for cid, r in self.deck_rows():
            c = CARDS[cid]
            panel(surf, r, ui.CAT_COLOR[c["cat"]] if r.collidepoint(mp) else PANEL2, LINE, 8)
            pygame.draw.circle(surf, ACCENT2, (r.x + 16, r.centery), 11)
            text(surf, card_cost_label(cid), (r.x + 16, r.centery), 12, (10, 12, 20), True, center=True)
            text(surf, c["name"], (r.x + 34, r.y + 5), 14, TEXT)
            text(surf, f"×{self.deck.count(cid)}", (r.right - 12, r.y + 5), 14, GOLD, True, right=True)
        # đường cong năng lượng
        curve = [0] * 6
        for cid in self.deck:
            curve[min(5, max(0, CARDS[cid]["cost"]))] += 1
        bx, by = R.x + 20, R.bottom - 20
        text(surf, "Phân bố chi phí", (bx, by - 70), 11, MUTED)
        for k, v in enumerate(curve):
            h = v * 6
            pygame.draw.rect(surf, ACCENT2, (bx + k * 30, by - h - 14, 22, h), border_radius=3)
            text(surf, "X" if k == 0 and any(CARDS[c]["cost"] < 0 for c in self.deck) else str(k), (bx + k * 30 + 11, by - 6), 10, MUTED, center=True)
        if self.msg:
            text_box(surf, self.msg, (R.x + 196, R.bottom - 92, 176, 86), 12, RED)
        if self.hover:
            mp = pygame.mouse.get_pos()
            extra = unlock_text(self.hover) if self.hover not in un else None
            ui.draw_card_detail(surf, (mp[0] + 18, mp[1] - 120), self.hover, extra)
