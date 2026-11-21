import pygame

import ui
from ui import W, H, text, text_box, panel, chip, icon, Button, TEXT, MUTED, ACCENT, ACCENT2, GOLD, RED, GREEN, ORANGE, LINE, PANEL, PANEL2
from scenes_base import Scene, back_button
from engine import CARDS, Game, PUZZLES, TUTORIALS
from engine.puzzles import PUZZLE_BY_ID


def puzzles_done(app):
    return set(app.user["puzzles_done"]) if app.user else set(app.local_puzzles)


def start_puzzle(app, pz):
    from scene_battle import BattleScene
    g = Game(0, [], [], names=(app.name, "Mục tiêu"), puzzle=pz)
    app.go(BattleScene(app, g, mode="puzzle", puzzle=pz))


class PuzzleListScene(Scene):
    title = "Thử thách theo chủ đề"

    def enter(self):
        from scenes_menu import MenuScene
        self.buttons = [back_button(self.app, lambda: MenuScene(self.app))]
        self.rows = []
        for i, pz in enumerate(PUZZLES):
            col, row = i % 2, i // 2
            r = pygame.Rect(60 + col * 590, 90 + row * 200, 570, 184)
            self.rows.append((pz, r))

    def handle(self, e):
        if super().handle(e):
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for pz, r in self.rows:
                if r.collidepoint(e.pos):
                    start_puzzle(self.app, pz)
                    return True
        return False

    def draw(self, surf):
        super().draw(surf)
        done = puzzles_done(self.app)
        mp = pygame.mouse.get_pos()
        for i, (pz, r) in enumerate(self.rows):
            ok = pz["id"] in done
            hov = r.collidepoint(mp)
            col = GREEN if ok else ORANGE
            ui.wash(surf, r, "indigo", ui.AMBER if hov else ui.RULE)
            art = ("split","bag","graph","boxes","heap","tree")[i]
            ui.plate(surf, art, (r.x+17,r.y+14,58,58))
            if ok:
                icon(surf, "check", (r.right-20,r.y+18), 21, GREEN)
            chip(surf, pz["topic"].upper(), (r.x + 90, r.y + 20), col, 10)
            text(surf, pz["title"], (r.x + 90, r.y + 44), 20, TEXT, 3)
            text_box(surf, pz["goal"], (r.x + 20, r.y + 88, r.w - 40, 44), 14, (205, 213, 234))
            names = ", ".join(CARDS[c]["name"] for c in pz["unlocks"])
            icon(surf, "bolt", (r.x + 28, r.bottom - 25), 16, ACCENT)
            text(surf, "Mở khoá: " + names + "  ·  +40 XP", (r.x + 42, r.bottom - 34), 13, ACCENT, 2)
        text(surf, "Mỗi thử thách phải hạ đối thủ trong MỘT lượt. Có nút Gợi ý nếu bí.", (W // 2, H - 24), 13, ui.INK, center=True)


class TutorialScene(Scene):
    title = "Hướng dẫn theo chủ đề"

    def enter(self):
        from scenes_menu import MenuScene
        self.sel = 0
        self.page = 0
        self.buttons = [back_button(self.app, lambda: MenuScene(self.app))]
        self.side = []
        for i, t in enumerate(TUTORIALS):
            b = Button((30, 90 + i * 64, 300, 54), t["title"], lambda i=i: self.select(i), "ghost", size=15)
            b.idx = i
            self.side.append(b)
        self.prev_b = Button((370, 632, 140, 46), "Trước", lambda: self.turn(-1), icon_name="prev")
        self.next_b = Button((1110, 632, 140, 46), "Tiếp", lambda: self.turn(1), "primary", icon_name="next")
        self.prac_b = Button((834, 632, 266, 46), "Thực hành ngay", self.practice, "gold", icon_name="puzzle")
        self.buttons += self.side + [self.prev_b, self.next_b, self.prac_b]

    def select(self, i):
        self.sel, self.page = i, 0

    @property
    def tut(self):
        return TUTORIALS[self.sel]

    def turn(self, d):
        n = len(self.tut["pages"])
        self.page = max(0, min(n - 1, self.page + d))
        if self.page == n - 1:
            self.mark_done()

    def mark_done(self):
        a = self.app
        tid = self.tut["id"]
        if a.user and tid not in a.user["tutorials_done"]:
            def ok(res):
                a.user = res["user"]
                a.toast("Đã hoàn thành bài: " + self.tut["title"] + " (+15 XP)", GREEN)
            a.spawn(a.net.post(f"/api/tutorials/{tid}/complete"), ok)

    def practice(self):
        pid = self.tut["puzzle"]
        if pid:
            self.mark_done()
            start_puzzle(self.app, PUZZLE_BY_ID[pid])

    def draw(self, surf):
        self.draw_bg(surf)
        self.draw_header(surf)
        done = set(self.app.user["tutorials_done"]) if self.app.user else set()
        for b in self.side:
            b.kind = "primary" if b.idx == self.sel else "ghost"
        n = len(self.tut["pages"])
        self.prev_b.enabled = self.page > 0
        self.next_b.enabled = self.page < n - 1
        self.prac_b.enabled = bool(self.tut["puzzle"]) and self.page == n - 1
        for b in self.buttons:
            if b is self.prac_b and not b.enabled:
                continue
            b.draw(surf)
        for b in self.side:
            if TUTORIALS[b.idx]["id"] in done:
                icon(surf, "check", (b.rect.right - 22, b.rect.centery), 18, GREEN if b.idx != self.sel else (21, 27, 3))
        R = pygame.Rect(360, 80, 900, 536)
        panel(surf, R, (40, 22, 11), radius=18)
        title, lines = self.tut["pages"][self.page]
        chip(surf, self.tut["title"].upper(), (R.x + 36, R.y + 28), GOLD, 11)
        text(surf, title, (R.x + 36, R.y + 60), 32, TEXT, 3)
        y = R.y + 128
        for ln in lines:
            pygame.draw.circle(surf, ACCENT, (R.x + 46, y + 13), 6)
            pygame.draw.circle(surf, (23, 17, 4), (R.x + 46, y + 13), 2)
            y = text_box(surf, ln, (R.x + 66, y, R.w - 110, 120), 19, (222, 228, 244)) + 18
        if y < R.bottom-155:
            ui.plate(surf, "journey", (R.x+34,R.bottom-150,R.w-68,100), cover=True)
        for k in range(n):
            pygame.draw.circle(surf, ACCENT if k == self.page else LINE, (R.centerx - (n - 1) * 12 + k * 24, R.bottom - 24), 6)
        text(surf, f"Trang {self.page + 1}/{n}", (R.right - 24, R.bottom - 32), 13, MUTED, right=True)
