import math
import random
import time

import pygame

import ui
from ui import (W, H, text, text_box, panel, bar, chip, icon, Button, TextInput, TEXT, MUTED, ACCENT, ACCENT2,
                GOLD, RED, GREEN, ORANGE, LINE, PANEL, PANEL2)
from scenes_base import Scene, back_button
from engine import CARDS, Game, ai_deck
from engine.ai import describe_ai, DIFFICULTY_POINTS

DIFF_VI = {"easy": "Dễ", "normal": "Thường", "hard": "Khó"}
DIFF_COLOR = {"easy": GREEN, "normal": GOLD, "hard": RED}
_fan_cache = {}


def card_fan(surf, center, cards, flip=False, t=0.0):
    """Quạt thẻ trang trí (xoay sẵn, cache)."""
    cx, cy = center
    n = len(cards)
    for i, cid in enumerate(cards):
        ang = (i - (n - 1) / 2) * 13 * (-1 if flip else 1)
        key = (cid, ang)
        img = _fan_cache.get(key)
        if img is None:
            base = pygame.Surface((150, 212), pygame.SRCALPHA)
            ui.draw_card(base, (5, 5, 140, 200), cid, playable=False)
            img = pygame.transform.rotozoom(base, ang, 1.0)
            _fan_cache[key] = img
        bob = math.sin(t * 1.2 + i) * 4
        dx = (i - (n - 1) / 2) * 46 * (-1 if flip else 1)
        dy = abs(i - (n - 1) / 2) * 14
        surf.blit(img, img.get_rect(center=(cx + dx, cy + dy + bob)))


def menu(app):
    return MenuScene(app)


# ====================================================================== Boot
class BootScene(Scene):
    def enter(self):
        self.msg = "Đang kết nối máy chủ…"
        if not self.app.net.token():
            self.app.go(LoginScene(self.app))
            return
        self.app.spawn(self.app.net.get("/api/me"), self.on_me, self.on_err)

    def on_me(self, me):
        self.app.user = me
        h = self.app.net.url_hash()
        if h.startswith("#replay="):
            self.app.net.clear_hash()
            try:
                mid = int(h.split("=", 1)[1])
            except ValueError:
                mid = None
            if mid:
                open_replay(self.app, mid)
                return
        self.app.go(MenuScene(self.app))

    def on_err(self, e):
        self.app.go(LoginScene(self.app, str(e) if e.status != 401 else ""))

    def draw(self, surf):
        self.draw_bg(surf)
        ui.logo(surf, (W // 2, H // 2 - 30), 60, self.t)
        for i in range(3):
            a = (math.sin(self.t * 5 - i * .6) + 1) / 2
            pygame.draw.circle(surf, ui.mix(ui.PANEL2, ACCENT, a), (W // 2 - 20 + i * 20, H // 2 + 50), 5)
        text(surf, self.msg, (W // 2, H // 2 + 84), 16, MUTED, center=True)


# ====================================================================== Login
class LoginScene(Scene):
    def __init__(self, app, msg=""):
        super().__init__(app)
        self.msg = msg
        self.busy = False
        cx = W // 2
        self.user = TextInput((cx - 190, 318, 380, 50), "Tên đăng nhập")
        self.pw = TextInput((cx - 190, 380, 380, 50), "Mật khẩu (ít nhất 6 ký tự)", password=True, maxlen=64)
        self.user.focus = True
        self.buttons = [
            Button((cx - 190, 450, 186, 50), "Đăng nhập", lambda: self.submit("login"), "primary", 17),
            Button((cx + 4, 450, 186, 50), "Đăng ký", lambda: self.submit("register"), size=17),
            Button((cx - 190, 512, 380, 40), "Chơi thử offline (không lưu tiến trình)", self.offline, "ghost", 14),
        ]

    def offline(self):
        self.app.user = None
        self.app.offline = True
        self.app.go(MenuScene(self.app))

    def submit(self, kind):
        if self.busy:
            return
        u, p = self.user.value.strip(), self.pw.value
        if len(u) < 3 or len(p) < 6:
            self.msg = "Tên đăng nhập ít nhất 3 ký tự, mật khẩu ít nhất 6 ký tự"
            return
        self.busy = True
        self.msg = "Đang xử lý…"

        def ok(r):
            self.app.net.set_token(r["token"])
            self.app.user = r["user"]
            self.app.offline = False
            self.app.toast(f"Xin chào {r['user']['username']}!")
            self.app.go(MenuScene(self.app))

        def err(e):
            self.busy = False
            self.msg = str(e)

        self.app.spawn(self.app.net.post(f"/api/auth/{kind}", {"username": u, "password": p}), ok, err)

    def handle(self, e):
        self.user.handle(e)
        self.pw.handle(e)
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_TAB:
                self.user.focus, self.pw.focus = self.pw.focus, self.user.focus
            elif e.key == pygame.K_RETURN:
                self.submit("login")
        super().handle(e)

    def draw(self, surf):
        self.draw_bg(surf)
        card_fan(surf, (190, 470), ["stack", "bfs", "dp"], False, self.t)
        card_fan(surf, (W - 190, 470), ["dijkstra", "quick_sort", "heap"], True, self.t)
        ui.logo(surf, (W // 2, 128), 62, self.t)
        text(surf, "Card battle học Cấu trúc dữ liệu & Giải thuật", (W // 2, 188), 19, MUTED, 1, center=True)
        r = pygame.Rect(W // 2 - 222, 238, 444, 340)
        panel(surf, r, (40, 22, 11), accent=(150, 112, 58), radius=18)
        text(surf, "Đăng nhập", (r.x + 32, r.y + 26), 22, TEXT, 3)
        text(surf, "Dùng chung tài khoản với trang web", (r.right - 32, r.y + 34), 12, MUTED, right=True)
        self.user.draw(surf, 1 / 60)
        self.pw.draw(surf, 1 / 60)
        for b in self.buttons:
            b.draw(surf)
        if self.msg:
            text(surf, self.msg, (W // 2, 606), 15, GOLD, 2, center=True)
        text(surf, "Pygame · WebAssembly · FastAPI · PostgreSQL", (W // 2, H - 28), 12, (140, 116, 86), center=True)


# ====================================================================== Menu
class Tile:
    def __init__(self, rect, title, sub, icon_name, color, cb):
        self.rect = pygame.Rect(rect)
        self.title, self.sub, self.icon, self.color, self.cb = title, sub, icon_name, color, cb
        self.hover = False
        self.h = 0.0

    def handle(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.cb()
            return True
        return False

    def draw(self, surf, dt):
        self.h += ((1.0 if self.hover else 0.0) - self.h) * min(1, dt * 12)
        r = self.rect.move(0, -int(self.h * 4))
        if self.h > 0.02:
            g = ui.glow(r.w, r.h, self.color, 16, 18, int(150 * self.h))
            surf.blit(g, (r.x - 18, r.y - 18))
        panel(surf, r, (45, 25, 13), accent=ui.mix((116, 88, 50), self.color, self.h), radius=16, width=2 if self.h > .5 else 1)
        ic = pygame.Rect(r.x + 22, r.centery - 30, 60, 60)
        surf.blit(ui.vgradient(60, 60, (*ui.lighten(self.color, .1), 255), (*ui.darken(self.color, .35), 255), 16), ic)
        icon(surf, self.icon, ic.center, 34, (255, 255, 255))
        text(surf, self.title, (r.x + 100, r.centery - 24), 21, TEXT, 3)
        text(surf, self.sub, (r.x + 100, r.centery + 6), 13, MUTED)
        icon(surf, "next", (r.right - 26, r.centery), 14, ui.mix(MUTED, self.color, self.h))


class MenuScene(Scene):
    def enter(self):
        a = self.app
        items = [
            ("Đấu với AI", "Chọn độ khó, dùng bộ bài của bạn", "sword", RED, lambda: a.go(PlaySetupScene(a))),
            ("Thử thách", "Giải đố theo chủ đề, mở khoá thẻ mới", "puzzle", ORANGE, self._puzzles),
            ("Hướng dẫn", "Lý thuyết ngắn rồi thực hành ngay", "book", ACCENT, self._tutorials),
            ("Bộ bài", "Xây dựng bộ bài 12 thẻ", "deck", ACCENT2, self._deck),
            ("Lịch sử & Replay", "Xem lại từng nước đi", "replay", (90, 170, 255), lambda: a.go(HistoryScene(a))),
            ("Bảng xếp hạng", "Top người chơi", "crown", GOLD, lambda: a.go(LeaderboardScene(a))),
        ]
        self.tiles = []
        for i, (t, s, ic, c, cb) in enumerate(items):
            col, row = i % 2, i // 2
            self.tiles.append(Tile((W // 2 - 400 + col * 410, 268 + row * 132, 390, 112), t, s, ic, c, cb))
        if self.app.user:
            self.buttons = [Button((W - 176, 22, 154, 40), "Đăng xuất", self.logout, "ghost", 14, icon_name="logout"),
                            Button((W - 340, 22, 156, 40), "Trang web", lambda: a.net.go("/"), "ghost", 14, icon_name="globe")]
        else:
            self.buttons = [Button((W - 176, 22, 154, 40), "Đăng nhập", lambda: a.go(LoginScene(a)), "ghost", 14)]
        self.dt = 1 / 60

    def _puzzles(self):
        from scenes_learn import PuzzleListScene
        self.app.go(PuzzleListScene(self.app))

    def _tutorials(self):
        from scenes_learn import TutorialScene
        self.app.go(TutorialScene(self.app))

    def _deck(self):
        from scene_deck import DeckScene
        self.app.go(DeckScene(self.app))

    def logout(self):
        self.app.net.set_token("")
        self.app.user = None
        self.app.go(LoginScene(self.app, "Đã đăng xuất"))

    def handle(self, e):
        for t in self.tiles:
            if t.handle(e):
                return True
        return super().handle(e)

    def update(self, dt):
        super().update(dt)
        self.dt = dt

    def draw(self, surf):
        self.draw_bg(surf)
        card_fan(surf, (110, 560), ["linear_search", "merge_sort", "union_find"], False, self.t)
        card_fan(surf, (W - 110, 560), ["kruskal", "trie", "recursion"], True, self.t)
        # logo nhỏ
        mark = pygame.Rect(24, 20, 44, 44)
        self.screen_logo(surf, mark)
        text(surf, "ALGO ARENA", (78, 24), 24, TEXT, 3)
        text(surf, "Card battle học thuật toán", (78, 50), 12, MUTED)
        u = self.app.user
        r = pygame.Rect(W // 2 - 400, 92, 800, 148)
        panel(surf, r, (43, 24, 12), accent=(150, 112, 58), radius=18)
        if u:
            av = pygame.Rect(r.x + 24, r.y + 26, 72, 72)
            surf.blit(ui.vgradient(72, 72, (*ACCENT, 255), (*ACCENT2, 255), 36), av)
            text(surf, u["username"][:1].upper(), av.center, 34, (23, 17, 4), 3, center=True)
            text(surf, u["username"], (r.x + 114, r.y + 24), 26, TEXT, 3)
            chip(surf, "Quản trị viên" if u["role"] == "admin" else "Người chơi", (r.x + 114, r.y + 62), ACCENT2, 11)
            # cấp độ
            lx = r.x + 114
            text(surf, f"Cấp {u['level']}", (lx, r.y + 92), 15, GOLD, 3)
            bar(surf, (lx + 66, r.y + 97, 170, 12), u["xp_in_level"] / u["xp_per_level"], GOLD)
            text(surf, f"{u['xp_in_level']}/{u['xp_per_level']} XP", (lx + 244, r.y + 92), 12, MUTED)
            text(surf, f"Thẻ mở khoá {len(u['unlocked'])}/{len(CARDS)}  ·  Thử thách {len(u['puzzles_done'])}/6",
                 (lx, r.y + 118), 12, MUTED)
            stats = [("Điểm", u["points"], GOLD), ("Thắng", u["wins"], GREEN), ("Thua", u["losses"], RED),
                     ("Chính xác", f"{u['accuracy']}%", ACCENT)]
            for i, (lab, val, c) in enumerate(stats):
                sr = pygame.Rect(r.x + 466 + (i % 2) * 162, r.y + 18 + (i // 2) * 58, 152, 52)
                pygame.draw.rect(surf, (29, 15, 7), sr, border_radius=12)
                pygame.draw.rect(surf, ui.darken(c, .45), sr, 1, border_radius=12)
                pygame.draw.rect(surf, c, (sr.x, sr.y + 12, 4, sr.h - 24), border_radius=2)
                text(surf, str(val), (sr.x + 16, sr.y + 6), 21, TEXT, 3)
                text(surf, lab, (sr.x + 16, sr.y + 32), 11, MUTED)
        else:
            text(surf, "Chế độ khách", (r.x + 30, r.y + 28), 26, TEXT, 3)
            text_box(surf, "Tiến trình, bộ bài và trận đấu sẽ không được lưu lên máy chủ. Đăng nhập để vào bảng "
                     "xếp hạng và lưu replay.", (r.x + 30, r.y + 72, 740, 60), 15, MUTED)
        for t in self.tiles:
            t.draw(surf, self.dt)
        for b in self.buttons:
            b.draw(surf)
        text(surf, "Mẹo: rê chuột lên thẻ bất kỳ để xem bài học đi kèm", (W // 2, H - 22), 12, (150, 126, 96), center=True)

    def screen_logo(self, surf, r):
        surf.blit(ui.vgradient(r.w, r.h, (*ACCENT, 255), (*ACCENT2, 255), 12), r)
        text(surf, "A", r.center, 26, (23, 17, 4), 3, center=True)


# ====================================================================== Chọn độ khó
class PlaySetupScene(Scene):
    title = "Đấu với AI"

    def enter(self):
        a = self.app
        self.buttons = [back_button(a, lambda: MenuScene(a))]
        self.tiles = []
        subs = {"easy": "AI chơi ngẫu nhiên. Hợp để làm quen luật.",
                "normal": "AI tham lam: luôn chọn nước có lợi nhất ngay.",
                "hard": "AI tìm kiếm DFS 3 nước đi trong mỗi lượt."}
        for i, d in enumerate(("easy", "normal", "hard")):
            t = Tile((W // 2 - 480 + i * 326, 96, 308, 140), f"{DIFF_VI[d]}", subs[d],
                     "bolt", DIFF_COLOR[d], lambda d=d: self.start(d))
            t.diff = d
            self.tiles.append(t)
        self.dt = 1 / 60
        self.hover = None

    def start(self, diff):
        from scene_battle import BattleScene
        seed = random.Random(time.time_ns()).randrange(1, 2_000_000_000)
        deck = self.app.deck
        g = Game(seed, deck, ai_deck(diff, seed), names=(self.app.name, f"AI {DIFF_VI[diff]}"))
        self.app.go(BattleScene(self.app, g, mode="ai", difficulty=diff, deck=deck))

    def handle(self, e):
        for t in self.tiles:
            if t.handle(e):
                return True
        return super().handle(e)

    def update(self, dt):
        super().update(dt)
        self.dt = dt

    def deck_rects(self):
        deck = sorted(self.app.deck, key=lambda c: (CARDS[c]["cost"], c))
        out = []
        for i, cid in enumerate(deck):
            x = W // 2 - 480 + (i % 6) * 163
            y = 302 + (i // 6) * 196
            out.append((cid, pygame.Rect(x, y, 150, 182)))
        return out

    def draw(self, surf):
        super().draw(surf)
        for t in self.tiles:
            t.draw(surf, self.dt)
            text(surf, f"+{DIFFICULTY_POINTS[t.diff]} điểm khi thắng", (t.rect.x + 100, t.rect.bottom - 30), 12, t.color, 2)
            n = {"easy": 1, "normal": 2, "hard": 3}[t.diff]
            for k in range(3):
                pygame.draw.circle(surf, t.color if k < n else (70, 49, 31), (t.rect.right - 70 + k * 16, t.rect.y + 26), 5)
        text(surf, "Bộ bài của bạn", (W // 2 - 480, 262), 18, TEXT, 3)
        text(surf, "Sửa trong mục Bộ bài", (W // 2 + 480, 266), 12, MUTED, right=True)
        mp = pygame.mouse.get_pos()
        hov = None
        for cid, r in self.deck_rects():
            h = r.collidepoint(mp)
            ui.draw_card(surf, r, cid, compact=True, highlight=h, lift=6 if h else 0)
            if h:
                hov = cid
        if hov:
            ui.draw_card_detail(surf, (mp[0] + 18, mp[1] - 220), hov)


# ====================================================================== Bảng xếp hạng
MEDAL = [(255, 202, 87), (200, 210, 225), (205, 127, 50)]


class LeaderboardScene(Scene):
    title = "Bảng xếp hạng"

    def enter(self):
        self.rows = None
        self.err = ""
        self.buttons = [back_button(self.app, lambda: MenuScene(self.app))]
        self.app.spawn(self.app.net.get("/api/leaderboard?limit=12"), self.ok, self.fail)

    def ok(self, rows):
        self.rows = rows

    def fail(self, e):
        self.err = "Không tải được bảng xếp hạng: " + str(e)

    def draw(self, surf):
        super().draw(surf)
        r = pygame.Rect(W // 2 - 440, 84, 880, 610)
        panel(surf, r, (40, 22, 11), radius=18)
        cols = [("HẠNG", 34), ("NGƯỜI CHƠI", 120), ("CẤP", 420), ("ĐIỂM", 500), ("THẮNG", 600), ("THUA", 690), ("CHÍNH XÁC", 770)]
        for lab, x in cols:
            text(surf, lab, (r.x + x, r.y + 22), 11, MUTED, 3)
        pygame.draw.line(surf, LINE, (r.x + 20, r.y + 48), (r.right - 20, r.y + 48))
        if self.err:
            text(surf, self.err, r.center, 16, RED, center=True)
        elif self.rows is None:
            text(surf, "Đang tải…", r.center, 16, MUTED, center=True)
        elif not self.rows:
            icon(surf, "crown", (r.centerx, r.centery - 30), 60, (110, 84, 50))
            text(surf, "Chưa có người chơi nào. Hãy là người đầu tiên!", (r.centerx, r.centery + 20), 16, MUTED, center=True)
        else:
            for i, row in enumerate(self.rows):
                y = r.y + 58 + i * 45
                rr = pygame.Rect(r.x + 14, y, r.w - 28, 40)
                me = self.app.user and row["username"] == self.app.user["username"]
                if me:
                    pygame.draw.rect(surf, (56, 51, 14), rr, border_radius=10)
                    pygame.draw.rect(surf, ACCENT, rr, 1, border_radius=10)
                elif i % 2 == 0:
                    pygame.draw.rect(surf, (43, 25, 13), rr, border_radius=10)
                cy = y + 20
                if row["rank"] <= 3:
                    pygame.draw.circle(surf, MEDAL[row["rank"] - 1], (r.x + 46, cy), 14)
                    text(surf, row["rank"], (r.x + 46, cy), 14, (20, 16, 8), 3, center=True)
                else:
                    text(surf, row["rank"], (r.x + 46, cy), 15, MUTED, 2, center=True)
                text(surf, row["username"], (r.x + 120, cy - 11), 16, TEXT, 2)
                text(surf, row["level"], (r.x + 420, cy - 11), 16, GOLD, 2)
                text(surf, row["points"], (r.x + 500, cy - 12), 17, TEXT, 3)
                text(surf, row["wins"], (r.x + 600, cy - 11), 16, GREEN)
                text(surf, row["losses"], (r.x + 690, cy - 11), 16, RED)
                bar(surf, (r.x + 762, cy - 4, 50, 8), row["accuracy"] / 100, ACCENT)
                text(surf, f"{row['accuracy']}%", (r.x + 818, cy - 10), 13, TEXT)


# ====================================================================== Lịch sử
class HistoryScene(Scene):
    title = "Lịch sử trận đấu & Replay"

    def enter(self):
        self.rows = None
        self.err = ""
        self.scroll = 0
        self.buttons = [back_button(self.app, lambda: MenuScene(self.app))]
        if self.app.user:
            self.app.spawn(self.app.net.get("/api/matches/mine?limit=50"), self.ok, self.fail)
        else:
            self.rows = [dict(m, id=i + 1, local=True) for i, m in enumerate(self.app.local_matches)][::-1]

    def ok(self, rows):
        self.rows = rows

    def fail(self, e):
        self.err = str(e)

    def row_rects(self):
        r = pygame.Rect(W // 2 - 460, 84, 920, 610)
        return [(row, pygame.Rect(r.x + 14, r.y + 58 + i * 46, r.w - 28, 40))
                for i, row in enumerate((self.rows or [])[self.scroll:self.scroll + 12])]

    def handle(self, e):
        if e.type == pygame.MOUSEWHEEL and self.rows:
            self.scroll = max(0, min(max(0, len(self.rows) - 12), self.scroll - e.y))
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for row, rr in self.row_rects():
                if rr.collidepoint(e.pos):
                    if row.get("local"):
                        from scene_battle import replay_scene
                        self.app.go(replay_scene(self.app, row))
                    else:
                        open_replay(self.app, row["id"])
                    return True
        return super().handle(e)

    def draw(self, surf):
        super().draw(surf)
        r = pygame.Rect(W // 2 - 460, 84, 920, 610)
        panel(surf, r, (40, 22, 11), radius=18)
        heads = [("#", 26), ("THỜI GIAN", 80), ("ĐỘ KHÓ", 270), ("KẾT QUẢ", 370), ("LƯỢT", 480), ("CHÍNH XÁC", 550), ("INSIGHT", 660)]
        for lab, x in heads:
            text(surf, lab, (r.x + x, r.y + 22), 11, MUTED, 3)
        pygame.draw.line(surf, LINE, (r.x + 20, r.y + 48), (r.right - 20, r.y + 48))
        if self.err:
            text(surf, self.err, r.center, 16, RED, center=True)
            return
        if self.rows is None:
            text(surf, "Đang tải…", r.center, 16, MUTED, center=True)
            return
        if not self.rows:
            icon(surf, "replay", (r.centerx, r.centery - 30), 60, (110, 84, 50))
            text(surf, "Chưa có trận nào. Vào Đấu với AI để chơi trận đầu tiên!", (r.centerx, r.centery + 22), 16, MUTED, center=True)
            return
        mp = pygame.mouse.get_pos()
        for row, rr in self.row_rects():
            hov = rr.collidepoint(mp)
            pygame.draw.rect(surf, (59, 36, 18) if hov else (43, 25, 13), rr, border_radius=10)
            if hov:
                pygame.draw.rect(surf, ACCENT, rr, 1, border_radius=10)
            res = {0: ("Thắng", GREEN), 1: ("Thua", RED), -1: ("Hoà", GOLD)}[row["winner"]]
            when = (row.get("created_at") or "")[:16].replace("T", " ") if not row.get("local") else "phiên này"
            cy = rr.centery - 10
            text(surf, row["id"], (r.x + 26, cy), 15, MUTED)
            text(surf, when, (r.x + 80, cy), 15, TEXT)
            chip(surf, DIFF_VI[row["difficulty"]], (r.x + 270, cy - 1), DIFF_COLOR[row["difficulty"]], 11)
            chip(surf, res[0], (r.x + 370, cy - 1), res[1], 11, filled=True)
            text(surf, row["turns"], (r.x + 480, cy), 15, TEXT)
            text(surf, f"{row['accuracy']}%", (r.x + 550, cy), 15, TEXT)
            text(surf, row["insight"], (r.x + 660, cy), 15, GREEN)
            br = pygame.Rect(rr.right - 150, rr.y + 6, 138, 28)
            surf.blit(ui.vgradient(br.w, br.h, (*ACCENT, 255) if hov else (71, 44, 24, 255), (*ui.darken(ACCENT, .3), 255) if hov else (51, 30, 17, 255), 8), br)
            icon(surf, "play", (br.x + 18, br.centery), 14, (23, 25, 4) if hov else TEXT)
            text(surf, "Xem replay", (br.x + 32, br.centery - 9), 13, (23, 25, 4) if hov else TEXT, 2)


def open_replay(app, match_id):
    from scene_battle import replay_scene

    def ok(m):
        app.go(replay_scene(app, m))

    def err(e):
        app.toast("Không mở được replay: " + str(e), RED)
        app.go(MenuScene(app))

    app.spawn(app.net.get(f"/api/matches/{match_id}"), ok, err)
