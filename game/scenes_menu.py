import random
import time

import pygame

import ui
from ui import W, H, text, text_box, panel, bar, Button, TextInput, TEXT, MUTED, ACCENT, ACCENT2, GOLD, RED, GREEN, LINE, PANEL, PANEL2
from scenes_base import Scene, back_button
from engine import CARDS, Game, ai_deck, card_cost_label
from engine.ai import describe_ai, DIFFICULTY_POINTS

DIFF_VI = {"easy": "Dễ", "normal": "Thường", "hard": "Khó"}


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
        text(surf, "ALGO ARENA", (W // 2, H // 2 - 30), 48, ACCENT, True, center=True)
        text(surf, self.msg, (W // 2, H // 2 + 30), 18, MUTED, center=True)


# ====================================================================== Login
class LoginScene(Scene):
    def __init__(self, app, msg=""):
        super().__init__(app)
        self.msg = msg
        self.busy = False
        cx = W // 2
        self.user = TextInput((cx - 200, 300, 400, 46), "Tên đăng nhập")
        self.pw = TextInput((cx - 200, 360, 400, 46), "Mật khẩu (≥ 6 ký tự)", password=True, maxlen=64)
        self.user.focus = True
        self.buttons = [
            Button((cx - 200, 430, 195, 48), "Đăng nhập", lambda: self.submit("login"), "primary"),
            Button((cx + 5, 430, 195, 48), "Đăng ký", lambda: self.submit("register")),
            Button((cx - 200, 492, 400, 40), "Chơi thử offline (không lưu tiến trình)", self.offline, "ghost", 14),
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
            self.msg = "Tên đăng nhập ≥ 3 ký tự, mật khẩu ≥ 6 ký tự"
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
        text(surf, "ALGO ARENA", (W // 2, 130), 54, ACCENT, True, center=True)
        text(surf, "Card battle học Cấu trúc dữ liệu & Giải thuật", (W // 2, 190), 20, MUTED, center=True)
        panel(surf, (W // 2 - 230, 240, 460, 320), (21, 28, 47, 230))
        text(surf, "Đăng nhập bằng tài khoản trên trang web", (W // 2, 266), 15, MUTED, center=True)
        self.user.draw(surf, 1 / 60)
        self.pw.draw(surf, 1 / 60)
        for b in self.buttons:
            b.draw(surf)
        if self.msg:
            text(surf, self.msg, (W // 2, 590), 16, GOLD, center=True)


# ====================================================================== Menu
class MenuScene(Scene):
    def enter(self):
        a = self.app
        items = [
            ("⚔  Đấu với AI", "Chọn độ khó, dùng bộ bài của bạn", lambda: a.go(PlaySetupScene(a))),
            ("◆  Thử thách", "Giải đố theo chủ đề, mở khoá thẻ mới", self._puzzles),
            ("★  Hướng dẫn", "Lý thuyết ngắn + thực hành", self._tutorials),
            ("▤  Bộ bài", "Xây dựng deck 12 thẻ", self._deck),
            ("↺  Lịch sử & Replay", "Xem lại từng nước đi", lambda: a.go(HistoryScene(a))),
            ("♛  Bảng xếp hạng", "Top người chơi", lambda: a.go(LeaderboardScene(a))),
        ]
        self.buttons = []
        for i, (label, sub, cb) in enumerate(items):
            col, row = i % 2, i // 2
            b = Button((W // 2 - 410 + col * 420, 250 + row * 112, 400, 96), label, cb, size=22)
            b.sub = sub
            self.buttons.append(b)
        if self.app.user:
            self.buttons.append(Button((W - 180, 20, 160, 38), "Đăng xuất", self.logout, "ghost", 14))
            self.buttons.append(Button((W - 350, 20, 160, 38), "Trang web ↗", lambda: a.net.go("/"), "ghost", 14))
        else:
            self.buttons.append(Button((W - 200, 20, 180, 38), "Đăng nhập", lambda: a.go(LoginScene(a)), "ghost", 14))

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

    def draw(self, surf):
        self.draw_bg(surf)
        text(surf, "ALGO ARENA", (40, 22), 30, ACCENT, True)
        u = self.app.user
        r = pygame.Rect(W // 2 - 410, 100, 820, 120)
        panel(surf, r)
        if u:
            text(surf, u["username"], (r.x + 24, r.y + 18), 26, TEXT, True)
            text(surf, "Quản trị viên" if u["role"] == "admin" else "Người chơi", (r.x + 24, r.y + 56), 14, ACCENT2)
            text(surf, f"Cấp {u['level']}", (r.x + 300, r.y + 20), 20, GOLD, True)
            bar(surf, (r.x + 300, r.y + 54, 220, 12), u["xp_in_level"] / u["xp_per_level"])
            text(surf, f"{u['xp_in_level']}/{u['xp_per_level']} XP", (r.x + 300, r.y + 74), 13, MUTED)
            for i, (lab, val) in enumerate([("Điểm", u["points"]), ("Thắng", u["wins"]), ("Thua", u["losses"]),
                                            ("Chính xác", f"{u['accuracy']}%")]):
                x = r.x + 560 + i * 66
                text(surf, str(val), (x + 28, r.y + 34), 20, TEXT, True, center=True)
                text(surf, lab, (x + 28, r.y + 64), 11, MUTED, center=True)
            text(surf, f"Thẻ mở khoá: {len(u['unlocked'])}/{len(CARDS)}   ·   Thử thách: {len(u['puzzles_done'])}/6",
                 (r.x + 24, r.y + 88), 13, MUTED)
        else:
            text(surf, "Chế độ khách (offline)", (r.x + 24, r.y + 22), 24, TEXT, True)
            text_box(surf, "Tiến trình, bộ bài và trận đấu sẽ không được lưu lên máy chủ. Đăng nhập để vào bảng "
                     "xếp hạng và lưu replay.", (r.x + 24, r.y + 60, 760, 50), 14, MUTED)
        for b in self.buttons:
            b.draw(surf)
            if hasattr(b, "sub"):
                text(surf, b.sub, (b.rect.centerx, b.rect.bottom - 18), 13, MUTED, center=True)
        text(surf, "Mẹo: rê chuột lên thẻ bất kỳ để xem bài học đi kèm.", (W // 2, H - 26), 13, MUTED, center=True)


# ====================================================================== Chọn độ khó
class PlaySetupScene(Scene):
    title = "Đấu với AI"

    def enter(self):
        a = self.app
        self.buttons = [back_button(a, lambda: MenuScene(a))]
        for i, d in enumerate(("easy", "normal", "hard")):
            b = Button((W // 2 - 465 + i * 315, 130, 300, 150), "", lambda d=d: self.start(d))
            b.diff = d
            self.buttons.append(b)

    def start(self, diff):
        from scene_battle import BattleScene
        seed = random.Random(time.time_ns()).randrange(1, 2_000_000_000)
        deck = self.app.deck
        g = Game(seed, deck, ai_deck(diff, seed), names=(self.app.name, f"AI {DIFF_VI[diff]}"))
        self.app.go(BattleScene(self.app, g, mode="ai", difficulty=diff, deck=deck))

    def draw(self, surf):
        super().draw(surf)
        for b in self.buttons:
            if hasattr(b, "diff"):
                d = b.diff
                text(surf, DIFF_VI[d], (b.rect.centerx, b.rect.y + 34), 28, [GREEN, GOLD, RED][["easy", "normal", "hard"].index(d)], True, center=True)
                text(surf, describe_ai(d).split("–")[1].strip(), (b.rect.centerx, b.rect.y + 76), 15, TEXT, center=True)
                text(surf, f"Thắng: +{DIFFICULTY_POINTS[d]} điểm + Insight", (b.rect.centerx, b.rect.y + 108), 13, MUTED, center=True)
        text(surf, "Bộ bài của bạn", (W // 2 - 465, 310), 18, TEXT, True)
        deck = sorted(self.app.deck, key=lambda c: (CARDS[c]["cost"], c))
        for i, cid in enumerate(deck):
            x = W // 2 - 465 + (i % 6) * 157
            y = 345 + (i // 6) * 180
            ui.draw_card(surf, (x, y, 150, 170), cid, compact=True)
        mp = pygame.mouse.get_pos()
        for i, cid in enumerate(deck):
            x = W // 2 - 465 + (i % 6) * 157
            y = 345 + (i // 6) * 180
            if pygame.Rect(x, y, 150, 170).collidepoint(mp):
                ui.draw_card_detail(surf, (mp[0] + 16, mp[1] - 200), cid)


# ====================================================================== Bảng xếp hạng
class LeaderboardScene(Scene):
    title = "Bảng xếp hạng"

    def enter(self):
        self.rows = None
        self.err = ""
        self.buttons = [back_button(self.app, lambda: MenuScene(self.app))]
        self.app.spawn(self.app.net.get("/api/leaderboard?limit=15"), self.ok, self.fail)

    def ok(self, rows):
        self.rows = rows

    def fail(self, e):
        self.err = "Không tải được bảng xếp hạng: " + str(e)

    def draw(self, surf):
        super().draw(surf)
        r = pygame.Rect(W // 2 - 420, 80, 840, 600)
        panel(surf, r)
        cols = [("Hạng", 30), ("Người chơi", 110), ("Cấp", 380), ("Điểm", 460), ("Thắng", 560), ("Thua", 640), ("Chính xác", 720)]
        for lab, x in cols:
            text(surf, lab, (r.x + x, r.y + 18), 14, MUTED, True)
        pygame.draw.line(surf, LINE, (r.x + 20, r.y + 44), (r.right - 20, r.y + 44))
        if self.err:
            text(surf, self.err, r.center, 16, RED, center=True)
        elif self.rows is None:
            text(surf, "Đang tải…", r.center, 16, MUTED, center=True)
        elif not self.rows:
            text(surf, "Chưa có người chơi nào. Hãy là người đầu tiên!", r.center, 16, MUTED, center=True)
        else:
            for i, row in enumerate(self.rows):
                y = r.y + 56 + i * 36
                me = self.app.user and row["username"] == self.app.user["username"]
                if me:
                    pygame.draw.rect(surf, (30, 50, 70), (r.x + 12, y - 6, r.w - 24, 32), border_radius=8)
                col = [GOLD, (200, 210, 225), ORANGE_][min(row["rank"] - 1, 2)] if row["rank"] <= 3 else TEXT
                vals = [row["rank"], row["username"], row["level"], row["points"], row["wins"], row["losses"], f"{row['accuracy']}%"]
                for (lab, x), v in zip(cols, vals):
                    text(surf, v, (r.x + x, y), 16, col if lab in ("Hạng", "Người chơi") else TEXT, lab == "Điểm")


ORANGE_ = (205, 127, 50)


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

    def handle(self, e):
        if e.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - e.y)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rows:
            for i, row in enumerate(self.rows[self.scroll:self.scroll + 13]):
                if pygame.Rect(W // 2 - 440 + 720, 128 + i * 42, 140, 32).collidepoint(e.pos):
                    if row.get("local"):
                        from scene_battle import replay_scene
                        self.app.go(replay_scene(self.app, row))
                    else:
                        open_replay(self.app, row["id"])
                    return True
        return super().handle(e)

    def draw(self, surf):
        super().draw(surf)
        r = pygame.Rect(W // 2 - 440, 70, 880, 620)
        panel(surf, r)
        heads = [("#", 20), ("Thời gian", 70), ("Độ khó", 270), ("Kết quả", 360), ("Lượt", 460), ("Chính xác", 520), ("Insight", 620)]
        for lab, x in heads:
            text(surf, lab, (r.x + x, r.y + 18), 14, MUTED, True)
        if self.err:
            text(surf, self.err, r.center, 16, RED, center=True)
            return
        if self.rows is None:
            text(surf, "Đang tải…", r.center, 16, MUTED, center=True)
            return
        if not self.rows:
            text(surf, "Chưa có trận nào.", r.center, 16, MUTED, center=True)
            return
        mp = pygame.mouse.get_pos()
        for i, row in enumerate(self.rows[self.scroll:self.scroll + 13]):
            y = r.y + 58 + i * 42
            res = {0: ("Thắng", GREEN), 1: ("Thua", RED), -1: ("Hoà", GOLD)}[row["winner"]]
            when = (row.get("created_at") or "")[:16].replace("T", " ") if not row.get("local") else "phiên này"
            vals = [row["id"], when, DIFF_VI[row["difficulty"]], res[0], row["turns"], f"{row['accuracy']}%", row["insight"]]
            for (lab, x), v in zip(heads, vals):
                text(surf, v, (r.x + x, y + 6), 15, res[1] if lab == "Kết quả" else TEXT)
            br = pygame.Rect(r.x + 720, y, 140, 32)
            panel(surf, br, PANEL2, ACCENT if br.collidepoint(mp) else LINE, 8)
            text(surf, "▶ Xem replay", br.center, 13, TEXT, True, center=True)


def open_replay(app, match_id):
    from scene_battle import replay_scene

    def ok(m):
        app.go(replay_scene(app, m))

    def err(e):
        app.toast("Không mở được replay: " + str(e), RED)
        app.go(MenuScene(app))

    app.spawn(app.net.get(f"/api/matches/{match_id}"), ok, err)
