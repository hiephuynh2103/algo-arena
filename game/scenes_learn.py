import pygame

import ui
from ui import W, H, text, text_box, panel, Button, TEXT, MUTED, ACCENT, ACCENT2, GOLD, RED, GREEN, LINE, PANEL, PANEL2
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
            panel(surf, r, PANEL2 if r.collidepoint(mp) else PANEL, GREEN if ok else (ACCENT if r.collidepoint(mp) else LINE), 14, 2 if ok else 1)
            text(surf, f"{pz['id'].upper()} · {pz['topic']}", (r.x + 20, r.y + 14), 13, GOLD, True)
            if ok:
                text(surf, "✔ Đã hoàn thành", (r.right - 20, r.y + 14), 13, GREEN, True, right=True)
            text(surf, pz["title"], (r.x + 20, r.y + 40), 21, TEXT, True)
            text_box(surf, pz["goal"], (r.x + 20, r.y + 76, r.w - 40, 44), 14, (205, 213, 234))
            names = ", ".join(CARDS[c]["name"] for c in pz["unlocks"])
            text(surf, "Phần thưởng: mở khoá " + names + " · +40 XP", (r.x + 20, r.bottom - 34), 13, ACCENT)
        text(surf, "Mỗi thử thách phải hạ đối thủ trong MỘT lượt. Có nút Gợi ý nếu bí.", (W // 2, H - 26), 13, MUTED, center=True)


class TutorialScene(Scene):
    title = "Hướng dẫn theo chủ đề"

    def enter(self):
        from scenes_menu import MenuScene
        self.sel = 0
        self.page = 0
        self.buttons = [back_button(self.app, lambda: MenuScene(self.app))]
        self.side = []
        for i, t in enumerate(TUTORIALS):
            b = Button((30, 90 + i * 64, 300, 54), t["title"], lambda i=i: self.select(i), size=15)
            b.idx = i
            self.side.append(b)
        self.prev_b = Button((370, 630, 140, 46), "◀ Trước", lambda: self.turn(-1))
        self.next_b = Button((1110, 630, 140, 46), "Tiếp ▶", lambda: self.turn(1), "primary")
        self.prac_b = Button((830, 630, 270, 46), "Thực hành ngay →", self.practice, "primary")
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
            b.kind = "primary" if b.idx == self.sel else "normal"
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
                text(surf, "✔", (b.rect.right - 20, b.rect.centery), 16, GREEN if b.idx != self.sel else (6, 32, 28), True, center=True)
        R = pygame.Rect(360, 80, 900, 536)
        panel(surf, R)
        title, lines = self.tut["pages"][self.page]
        text(surf, self.tut["title"].upper(), (R.x + 36, R.y + 28), 13, GOLD, True)
        text(surf, title, (R.x + 36, R.y + 52), 30, TEXT, True)
        y = R.y + 120
        for ln in lines:
            pygame.draw.circle(surf, ACCENT, (R.x + 46, y + 12), 5)
            y = text_box(surf, ln, (R.x + 64, y, R.w - 110, 120), 19, (220, 226, 242)) + 16
        for k in range(n):
            pygame.draw.circle(surf, ACCENT if k == self.page else LINE, (R.centerx - (n - 1) * 12 + k * 24, R.bottom - 24), 6)
        text(surf, f"Trang {self.page + 1}/{n}", (R.right - 24, R.bottom - 32), 13, MUTED, right=True)
