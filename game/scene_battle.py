import time

import pygame

import ui
from ui import (W, H, text, text_box, panel, bar, Button, Floating, TEXT, MUTED, ACCENT, ACCENT2, GOLD, RED,
                GREEN, ORANGE, BLUE, LINE, PANEL, PANEL2, RATING_COLOR, RATING_LABEL)
from scenes_base import Scene
from engine import CARDS, CHALLENGES, Game, replay, choose_action, card_cost_label
from engine.challenges import best_answer
from engine.engine import CHALLENGE_LIFETIME

AI_DELAY = 0.9
HAND_Y = 486
CARD_W, CARD_H = 140, 200

ENEMY_RECT = pygame.Rect(20, 14, 560, 112)
CHAL_RECT = pygame.Rect(20, 140, 560, 220)
PLAYED_RECT = pygame.Rect(596, 140, 290, 312)
PLAYER_RECT = pygame.Rect(20, 372, 560, 80)
LOG_RECT = pygame.Rect(900, 14, 360, 384)


def replay_scene(app, m):
    """m: dict có seed, player_deck, ai_deck, actions, difficulty (+ username)."""
    names = (m.get("username") or app.name, "AI " + {"easy": "Dễ", "normal": "Thường", "hard": "Khó"}[m["difficulty"]])
    g = Game(m["seed"], m["player_deck"], m["ai_deck"], names=names)
    return BattleScene(app, g, mode="replay", difficulty=m["difficulty"], replay_data=m)


class BattleScene(Scene):
    def __init__(self, app, game, mode="ai", difficulty="normal", deck=None, puzzle=None, replay_data=None):
        super().__init__(app)
        self.g = game
        self.mode = mode
        self.difficulty = difficulty
        self.deck = deck
        self.puzzle = puzzle
        self.rd = replay_data
        self.ev_i = 0
        self.log_i = 0
        self.floats = []
        self.ai_timer = AI_DELAY
        self.banner = None          # (text, timer)
        self.last = None            # (cid, who, rating, explain)
        self.hover = None
        self.started = time.time()
        self.finished = False
        self.overlay = None         # thông báo kết thúc puzzle
        self.show_hint = False
        self.step = 0
        self.autoplay = False
        self.auto_t = 0

    def enter(self):
        self.build_buttons()
        if self.mode == "ai":
            self.banner = ["LƯỢT CỦA BẠN", 1.2]
        self.consume_events()

    # ------------------------------------------------------------ nút bấm
    def build_buttons(self):
        a = self.app
        self.buttons = []
        bx, by = 900, 408
        if self.mode == "ai":
            self.end_btn = Button((bx, by, 220, 56), "Kết thúc lượt ▶", self.end_turn, "primary", 18)
            self.buttons += [self.end_btn, Button((bx + 230, by, 130, 56), "Đầu hàng", self.surrender, "danger", 15)]
        elif self.mode == "puzzle":
            self.end_btn = Button((bx, by, 170, 56), "Kết thúc lượt", self.end_turn, "primary", 16)
            self.buttons += [self.end_btn,
                             Button((bx + 178, by, 88, 56), "Gợi ý", self.toggle_hint, size=15),
                             Button((bx + 272, by, 88, 56), "Làm lại", self.restart, size=15)]
        else:
            self.buttons += [
                Button((bx, by, 64, 56), "|◀", lambda: self.goto(0), size=16),
                Button((bx + 72, by, 64, 56), "◀", lambda: self.goto(self.step - 1), size=16),
                Button((bx + 144, by, 72, 56), "Chạy", self.toggle_auto, "primary", 15),
                Button((bx + 224, by, 64, 56), "▶", lambda: self.goto(self.step + 1), size=16),
                Button((bx + 296, by, 64, 56), "▶|", lambda: self.goto(len(self.rd["actions"])), size=16),
            ]
        self.buttons.append(Button((W - 110, H - 46, 96, 34), "Thoát", self.quit, "ghost", 14))

    def quit(self):
        from scenes_menu import MenuScene
        if self.mode == "puzzle":
            from scenes_learn import PuzzleListScene
            self.app.go(PuzzleListScene(self.app))
        else:
            self.app.go(MenuScene(self.app))

    def my_turn(self):
        return self.mode in ("ai", "puzzle") and not self.g.over and self.g.current == 0 and not self.finished

    def end_turn(self):
        if not self.my_turn():
            return
        self.g.apply({"t": "end"})
        self.consume_events()
        if self.mode == "ai" and not self.g.over:
            self.banner = ["LƯỢT CỦA MÁY", 1.0]
            self.ai_timer = AI_DELAY

    def surrender(self):
        if self.mode != "ai" or self.finished:
            return
        self.finish(surrender=True)

    def toggle_hint(self):
        self.show_hint = not self.show_hint

    def restart(self):
        self.app.go(BattleScene(self.app, Game(0, [], [], puzzle=self.puzzle), mode="puzzle", puzzle=self.puzzle))

    # ------------------------------------------------------------ replay
    def toggle_auto(self):
        self.autoplay = not self.autoplay
        self.auto_t = 0
        for b in self.buttons:
            if b.label in ("Chạy", "Dừng"):
                b.label = "Dừng" if self.autoplay else "Chạy"

    def goto(self, k):
        k = max(0, min(len(self.rd["actions"]), k))
        forward_one = k == self.step + 1
        prev_events = len(self.g.events)
        self.step = k
        self.g = replay(self.rd["seed"], self.rd["player_deck"], self.rd["ai_deck"], self.rd["actions"],
                        names=(self.g.players[0].name, self.g.players[1].name), upto=k)
        if forward_one:                 # tua 1 bước: phát lại hiệu ứng của bước đó
            self.ev_i = prev_events
            self.consume_events()
            return
        self.ev_i = len(self.g.events)
        self.floats = []
        # thẻ chơi gần nhất + đánh giá của nó (nếu có)
        self.last = None
        for ev in reversed(self.g.events):
            if ev["kind"] == "play":
                self.last = (ev["card"], ev["who"], ev["rating"], ev.get("explain", ""))
                break

    # ------------------------------------------------------------ sự kiện engine → hiệu ứng
    def consume_events(self):
        evs = self.g.events[self.ev_i:]
        self.ev_i = len(self.g.events)
        for ev in evs:
            k = ev["kind"]
            if k == "damage":
                pos = (ENEMY_RECT.centerx, ENEMY_RECT.y + 60) if ev["target"] == 1 else (PLAYER_RECT.centerx, PLAYER_RECT.y + 30)
                if ev["amount"]:
                    self.floats.append(Floating(f"-{ev['amount']}", pos, RED, 34))
                if ev["absorbed"]:
                    self.floats.append(Floating(f"chặn {ev['absorbed']}", (pos[0] + 90, pos[1] + 10), BLUE, 20))
            elif k == "play":
                rating = ev["rating"]
                self.last = (ev["card"], ev["who"], rating, ev.get("explain", ""))
                if rating in ("optimal", "acceptable", "trap", "failed"):
                    self.floats.append(Floating(RATING_LABEL[rating], PLAYED_RECT.center, RATING_COLOR[rating], 30, 1.6))
            elif k == "solve":
                who = self.g.players[ev["who"]].name
                self.app.toast(f"✔ {who} giải bài toán: {CHALLENGES[ev['challenge']]['title']}", GREEN)
            elif k == "turn" and self.mode == "ai" and ev["who"] == 0:
                self.banner = ["LƯỢT CỦA BẠN", 1.0]

    # ------------------------------------------------------------ vòng lặp
    def update(self, dt):
        super().update(dt)
        self.floats = [f for f in self.floats if f.update(dt)]
        if self.banner:
            self.banner[1] -= dt
            if self.banner[1] <= 0:
                self.banner = None
        if self.mode == "ai" and not self.g.over and self.g.current == 1 and not self.finished:
            self.ai_timer -= dt
            if self.ai_timer <= 0:
                self.g.apply(choose_action(self.g, self.difficulty))
                self.consume_events()
                self.ai_timer = AI_DELAY
        if self.mode == "replay" and self.autoplay:
            self.auto_t += dt
            if self.auto_t >= 0.9:
                self.auto_t = 0
                if self.step >= len(self.rd["actions"]):
                    self.autoplay = False
                else:
                    self.goto(self.step + 1)
        if self.g.over and not self.finished and self.mode in ("ai", "puzzle"):
            self.finish_t = getattr(self, "finish_t", 1.2) - dt
            if self.finish_t <= 0:
                self.finish()

    def finish(self, surrender=False):
        self.finished = True
        if self.mode == "puzzle":
            self.finish_puzzle()
            return
        g = self.g
        data = {"difficulty": self.difficulty, "seed": g.seed, "player_deck": self.deck, "actions": g.actions,
                "surrender": surrender, "duration_sec": int(time.time() - self.started)}
        summary = g.summary(0)
        if surrender and not g.over:
            summary["winner"] = 1
        record = {"seed": g.seed, "player_deck": self.deck, "ai_deck": self._ai_deck(), "actions": list(g.actions),
                  "difficulty": self.difficulty, "winner": summary["winner"], "turns": g.turn,
                  "accuracy": summary["accuracy"], "insight": summary["insight"]}
        if self.app.user:
            body = {k: data[k] for k in ("difficulty", "seed", "player_deck", "actions", "surrender", "duration_sec")}

            def ok(res):
                self.app.user = res["user"]
                self.app.go(ResultScene(self.app, record, summary, g, res))

            def err(e):
                self.app.toast("Không lưu được trận đấu: " + str(e), RED)
                self.app.go(ResultScene(self.app, record, summary, g, None))

            self.app.spawn(self.app.net.post("/api/matches", body), ok, err)
        else:
            self.app.local_matches.append(record)
            self.app.go(ResultScene(self.app, record, summary, g, None))

    def _ai_deck(self):
        from engine import ai_deck
        return ai_deck(self.difficulty, self.g.seed)

    def finish_puzzle(self):
        g, pz = self.g, self.puzzle
        if g.winner != 0:
            self.overlay = ("fail", "Chưa hạ được đối thủ", pz["hint"])
            return
        self.overlay = ("win", "Hoàn thành thử thách!", pz["lesson"])
        if self.app.user:
            def ok(res):
                self.app.user = res["user"]
                if res["new_unlocks"]:
                    names = ", ".join(CARDS[c]["name"] for c in res["new_unlocks"])
                    self.app.toast(f"Mở khoá thẻ mới: {names}", GOLD, 4)
                if res["xp_gain"]:
                    self.app.toast(f"+{res['xp_gain']} XP", ACCENT)
            self.app.spawn(self.app.net.post(f"/api/puzzles/{pz['id']}/complete", {"actions": g.actions}), ok)
        else:
            before = set(self.app.unlocked)
            self.app.local_puzzles.add(pz["id"])
            new = set(self.app.unlocked) - before
            if new:
                self.app.toast("Mở khoá thẻ mới: " + ", ".join(CARDS[c]["name"] for c in new), GOLD, 4)

    # ------------------------------------------------------------ input
    def hand_rects(self, n):
        gap = 10
        total = n * CARD_W + (n - 1) * gap
        x0 = max(20, (W - total) // 2)
        step = CARD_W + gap
        if total > W - 40:
            step = (W - 40 - CARD_W) // max(1, n - 1)
        return [pygame.Rect(x0 + i * step, HAND_Y, CARD_W, CARD_H) for i in range(n)]

    def handle(self, e):
        if self.overlay and e.type == pygame.MOUSEBUTTONDOWN:
            if self.overlay[0] == "win":
                from scenes_learn import PuzzleListScene
                self.app.go(PuzzleListScene(self.app))
            else:
                self.restart()
            return True
        if super().handle(e):
            return True
        if e.type == pygame.MOUSEMOTION:
            self.hover = None
            for i, r in reversed(list(enumerate(self.hand_rects(len(self.g.players[0].hand))))):
                if r.collidepoint(e.pos):
                    self.hover = i
                    break
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.my_turn():
            hand = self.g.players[0].hand
            for i, r in reversed(list(enumerate(self.hand_rects(len(hand))))):
                if r.collidepoint(e.pos):
                    if self.g.can_play(hand[i]):
                        self.g.apply({"t": "play", "i": i})
                        self.consume_events()
                        self.hover = None
                    else:
                        self.app.toast("Không đủ năng lượng", ORANGE, 1.5)
                    return True
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE and self.my_turn():
                self.end_turn()
            if self.mode == "replay":
                if e.key == pygame.K_RIGHT:
                    self.goto(self.step + 1)
                elif e.key == pygame.K_LEFT:
                    self.goto(self.step - 1)
        return False

    # ------------------------------------------------------------ vẽ
    def draw_status(self, surf, rect, p, enemy):
        panel(surf, rect)
        x, y = rect.x + 16, rect.y + 10
        text(surf, p.name, (x, y), 18, TEXT, True)
        bar(surf, (x, y + 30, 260, 16), p.hp / p.max_hp, GREEN if p.hp > 10 else RED)
        text(surf, f"{max(p.hp, 0)}/{p.max_hp}", (x + 130, y + 38), 12, (10, 12, 20), True, center=True)
        if p.block:
            pygame.draw.rect(surf, BLUE, (x + 268, y + 26, 54, 24), border_radius=6)
            text(surf, f"⛨ {p.block}", (x + 295, y + 38), 14, (8, 20, 40), True, center=True)
        # năng lượng
        ex = x + 336
        text(surf, "Năng lượng", (ex, y + 2), 11, MUTED)
        for k in range(p.max_energy):
            pygame.draw.circle(surf, ACCENT2 if k < p.energy else (40, 48, 80), (ex + 8 + k * 22, y + 32), 8)
        # trạng thái
        tags = []
        if p.sorted > 0:
            tags.append((f"ĐÃ SẮP XẾP ({p.sorted})", ACCENT))
        if p.scheduled:
            tags.append(("Queue " + str(p.scheduled), GOLD))
        tags.append((f"Memo {len(p.memo)}", (196, 181, 253)))
        tags.append((f"Insight {p.insight}", GREEN))
        if enemy:
            tags.append((f"Bộ bài {len(p.deck)}", MUTED))
        tx = x
        ty = y + 58 if rect.h > 90 else y + 54
        for lab, col in tags:
            w = ui.font(11, True).size(lab)[0] + 14
            if tx + w > rect.right - 10:
                break
            pygame.draw.rect(surf, (15, 21, 40), (tx, ty, w, 20), border_radius=10)
            pygame.draw.rect(surf, col, (tx, ty, w, 20), 1, border_radius=10)
            text(surf, lab, (tx + w // 2, ty + 10), 11, col, True, center=True)
            tx += w + 6

    def draw(self, surf):
        g = self.g
        self.draw_bg(surf)
        me, ai = g.players
        # --- đối thủ
        self.draw_status(surf, ENEMY_RECT, ai, True)
        if self.mode == "replay":
            for i, cid in enumerate(ai.hand):
                ui.draw_card(surf, (596 + i * 37, 14, 60, 84), cid, compact=True)
        else:
            for i in range(len(ai.hand)):
                ui.draw_card_back(surf, (600 + i * 34, 24, 46, 64))
        if self.mode == "puzzle":
            panel(surf, (596, 14, 290, 112), PANEL)
            text(surf, "THỬ THÁCH", (612, 24), 12, GOLD, True)
            text_box(surf, self.puzzle["goal"], (612, 44, 260, 80), 13)

        # --- bài toán
        panel(surf, CHAL_RECT, (24, 32, 56), GOLD, 14, 2)
        text(surf, "BÀI TOÁN", (CHAL_RECT.x + 18, CHAL_RECT.y + 14), 12, GOLD, True)
        if g.challenge:
            ch = CHALLENGES[g.challenge]
            if not self.puzzle:
                left = CHALLENGE_LIFETIME - g.challenge_age
                text(surf, f"hết hạn sau {left} vòng", (CHAL_RECT.right - 18, CHAL_RECT.y + 14), 12, MUTED, right=True)
            text_box(surf, ch["title"], (CHAL_RECT.x + 18, CHAL_RECT.y + 36, CHAL_RECT.w - 36, 60), 22, TEXT, True)
            text_box(surf, ch["desc"], (CHAL_RECT.x + 18, CHAL_RECT.y + 100, CHAL_RECT.w - 36, 70), 14, (205, 213, 234))
            rw = ", ".join({"dmg": f"{v[1]} sát thương", "heal": f"hồi {v[1]}", "draw": f"rút {v[1]}",
                            "block": f"{v[1]} giáp"}[v[0]] for v in ch["reward"])
            text(surf, f"Thưởng khi giải tối ưu: {rw} · +2 Insight", (CHAL_RECT.x + 18, CHAL_RECT.bottom - 32), 13, GREEN)
        else:
            text(surf, "Đã giải xong bài toán!", CHAL_RECT.center, 20, GREEN, True, center=True)

        # --- thẻ vừa chơi
        panel(surf, PLAYED_RECT)
        text(surf, "VỪA CHƠI", (PLAYED_RECT.x + 14, PLAYED_RECT.y + 10), 12, MUTED, True)
        if self.last:
            cid, who, rating, expl = self.last
            text(surf, g.players[who].name, (PLAYED_RECT.right - 14, PLAYED_RECT.y + 10), 12, ACCENT if who == 0 else RED, True, right=True)
            badge = (RATING_LABEL[rating], RATING_COLOR[rating]) if RATING_LABEL.get(rating) else None
            ui.draw_card(surf, (PLAYED_RECT.x + 75, PLAYED_RECT.y + 36, CARD_W, CARD_H - 30), cid, badge=badge)
            if expl:
                text_box(surf, expl, (PLAYED_RECT.x + 12, PLAYED_RECT.y + 214, PLAYED_RECT.w - 24, 96), 12,
                         RATING_COLOR.get(rating, MUTED))

        # --- người chơi
        self.draw_status(surf, PLAYER_RECT, me, False)

        # --- log
        panel(surf, LOG_RECT)
        text(surf, "NHẬT KÝ TRẬN ĐẤU", (LOG_RECT.x + 14, LOG_RECT.y + 10), 12, MUTED, True)
        y = LOG_RECT.bottom - 22
        colors = {"trap": RED, "solve": GREEN, "challenge": GOLD, "play": TEXT, "end": GOLD, "turn": MUTED,
                  "effect": (160, 172, 200), "warn": ORANGE, "sys": ACCENT}
        for entry in reversed(g.log[-60:]):
            lines = ui.wrap(entry["text"], 12, LOG_RECT.w - 28)
            for ln in reversed(lines):
                if y < LOG_RECT.y + 32:
                    break
                col = colors.get(entry["kind"], TEXT)
                if entry["kind"] == "play":
                    col = ACCENT if entry["who"] == 0 else (252, 165, 165)
                text(surf, ln, (LOG_RECT.x + 14, y), 12, col)
                y -= 17
            if y < LOG_RECT.y + 32:
                break

        # --- tay bài
        hand = me.hand
        rects = self.hand_rects(len(hand))
        for i, (cid, r) in enumerate(zip(hand, rects)):
            rr = r.move(0, -18) if i == self.hover else r
            playable = self.my_turn() and g.can_play(cid)
            badge = None
            if self.show_hint and self.puzzle and g.challenge:
                opt, _ = best_answer(g.challenge)
                if cid == opt:
                    badge = ("GỢI Ý", GOLD)
            ui.draw_card(surf, rr, cid, playable=playable or self.mode == "replay", highlight=(i == self.hover and playable), badge=badge)
        if not hand:
            text(surf, "(không còn thẻ trên tay)", (W // 2, HAND_Y + 90), 16, MUTED, center=True)

        # --- nút & trạng thái lượt
        if self.mode in ("ai", "puzzle"):
            self.end_btn.enabled = self.my_turn()
        for b in self.buttons:
            b.draw(surf)
        if self.mode == "replay":
            text(surf, f"Bước {self.step}/{len(self.rd['actions'])} · Lượt {g.turn} · ←/→ để tua", (900, 470), 13, MUTED)
        else:
            who = "Lượt của bạn" if g.current == 0 else "Máy đang suy nghĩ…"
            text(surf, f"Lượt {g.turn} · {who}", (900, 470), 13, ACCENT if g.current == 0 else GOLD)
        if self.show_hint and self.puzzle:
            panel(surf, (596, 14, 290, 112), (40, 34, 14), GOLD)
            text_box(surf, "Gợi ý: " + self.puzzle["hint"], (610, 24, 264, 96), 13, GOLD)

        if self.hover is not None and self.hover < len(hand):
            r = rects[self.hover]
            ui.draw_card_detail(surf, (r.x - 80, r.y - 262), hand[self.hover])

        for f in self.floats:
            f.draw(surf)
        if self.banner:
            s = pygame.Surface((W, 90), pygame.SRCALPHA)
            s.fill((10, 14, 28, 200))
            surf.blit(s, (0, H // 2 - 120))
            text(surf, self.banner[0], (W // 2, H // 2 - 75), 38, ACCENT if "BẠN" in self.banner[0] else GOLD, True, center=True)
        if g.over and self.mode == "replay":
            text(surf, g._result_text(), (W // 2, H // 2 - 75), 30, GOLD, True, center=True)
        if self.overlay:
            kind, title, body = self.overlay
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((5, 8, 16, 210))
            surf.blit(s, (0, 0))
            r = pygame.Rect(W // 2 - 300, H // 2 - 140, 600, 280)
            panel(surf, r, PANEL, GREEN if kind == "win" else ORANGE, 16, 2)
            text(surf, title, (r.centerx, r.y + 46), 30, GREEN if kind == "win" else ORANGE, True, center=True)
            text_box(surf, ("Bài học: " if kind == "win" else "Gợi ý: ") + body, (r.x + 40, r.y + 96, r.w - 80, 120), 16)
            text(surf, "Bấm chuột để " + ("quay lại danh sách thử thách" if kind == "win" else "thử lại"),
                 (r.centerx, r.bottom - 34), 14, MUTED, center=True)


# ====================================================================== Kết quả & giải thích
class ResultScene(Scene):
    def __init__(self, app, record, summary, game, server):
        super().__init__(app)
        self.rec, self.s, self.g, self.server = record, summary, game, server
        self.scroll = 0

    def enter(self):
        from scenes_menu import MenuScene, PlaySetupScene
        a = self.app
        self.buttons = [
            Button((40, H - 76, 210, 52), "▶ Xem replay", lambda: a.go(replay_scene(a, dict(self.rec, username=a.name))), "primary"),
            Button((262, H - 76, 170, 52), "Đấu lại", lambda: a.go(PlaySetupScene(a))),
            Button((444, H - 76, 150, 52), "Menu", lambda: a.go(MenuScene(a)), "ghost"),
        ]

    def handle(self, e):
        if e.type == pygame.MOUSEWHEEL:
            n = len(self.s["decisions"])
            self.scroll = max(0, min(max(0, n - 5), self.scroll - e.y))
        return super().handle(e)

    def draw(self, surf):
        self.draw_bg(surf)
        s = self.s
        w = s["winner"]
        title, col = ("CHIẾN THẮNG!", GREEN) if w == 0 else ("HOÀ", GOLD) if w == -1 else ("THẤT BẠI", RED)
        text(surf, title, (330, 70), 46, col, True, center=True)
        r = pygame.Rect(40, 120, 580, 470)
        panel(surf, r)
        stats = [("Độ chính xác lựa chọn", f"{s['accuracy']}%"), ("Insight", s["insight"]),
                 ("Bài toán đã giải", s["solved"]), ("Số lượt", s["turns"]),
                 ("Máu còn lại", f"{max(0, s['hp'])} – đối thủ {max(0, s['enemy_hp'])}")]
        for i, (lab, val) in enumerate(stats):
            y = r.y + 22 + i * 40
            text(surf, lab, (r.x + 24, y), 16, MUTED)
            text(surf, val, (r.right - 24, y), 18, TEXT, True, right=True)
        c = s["counts"]
        y = r.y + 230
        text(surf, "Phân loại quyết định của bạn", (r.x + 24, y), 15, TEXT, True)
        items = [("optimal", c.get("optimal", 0)), ("acceptable", c.get("acceptable", 0)), ("trap", c.get("trap", 0)),
                 ("missed", c.get("missed", 0)), ("failed", c.get("failed", 0))]
        total = max(1, sum(v for _, v in items))
        x = r.x + 24
        for k, v in items:
            ww = int((r.w - 48) * v / total)
            if ww:
                pygame.draw.rect(surf, RATING_COLOR[k], (x, y + 30, ww, 18))
                x += ww
        for i, (k, v) in enumerate(items):
            text(surf, f"{RATING_LABEL[k]}: {v}", (r.x + 24 + (i % 3) * 180, y + 60 + (i // 3) * 24), 13, RATING_COLOR[k], True)
        y = r.y + 360
        if self.server:
            sv = self.server
            text(surf, f"+{sv['xp_gain']} XP   ·   +{sv['points_gain']} điểm xếp hạng", (r.x + 24, y), 17, ACCENT, True)
            if sv.get("level_up"):
                text(surf, f"LÊN CẤP {sv['level']}!", (r.x + 24, y + 30), 18, GOLD, True)
            if sv.get("new_unlocks"):
                text_box(surf, "Mở khoá thẻ mới: " + ", ".join(CARDS[c]["name"] for c in sv["new_unlocks"]),
                         (r.x + 24, y + 58, r.w - 48, 44), 14, GOLD)
        elif self.app.user:
            text(surf, "Trận đấu chưa được lưu lên máy chủ.", (r.x + 24, y), 15, ORANGE)
        else:
            text(surf, "Chế độ khách: trận đấu chỉ lưu trong phiên này.", (r.x + 24, y), 15, MUTED)

        # giải thích sau trận
        R = pygame.Rect(650, 40, 590, 630)
        panel(surf, R)
        text(surf, "GIẢI THÍCH SAU TRẬN", (R.x + 20, R.y + 16), 16, GOLD, True)
        text(surf, "Lăn chuột để xem thêm", (R.right - 20, R.y + 18), 12, MUTED, right=True)
        decs = s["decisions"]
        if not decs:
            text_box(surf, "Không có quyết định nào liên quan đến bài toán. Hãy thử dùng thẻ phù hợp với bài toán giữa sân "
                     "để nhận thưởng và Insight!", (R.x + 20, R.y + 60, R.w - 40, 80), 15, MUTED)
        y = R.y + 52
        for d in decs[self.scroll:]:
            ch = CHALLENGES[d["challenge"]]["title"] if d.get("challenge") else "—"
            lines = ui.wrap(d["explain"], 13, R.w - 60)
            h = 58 + 17 * len(lines)
            if y + h > R.bottom - 10:
                break
            col = RATING_COLOR[d["rating"]]
            panel(surf, (R.x + 14, y, R.w - 28, h - 6), (18, 24, 42), col, 10)
            text(surf, f"Lượt {d['turn']} · {CARDS[d['card']]['name']}", (R.x + 28, y + 8), 14, TEXT, True)
            text(surf, RATING_LABEL[d["rating"]], (R.right - 28, y + 8), 13, col, True, right=True)
            text(surf, "Bài toán: " + ch, (R.x + 28, y + 28), 12, MUTED)
            yy = y + 46
            for ln in lines:
                text(surf, ln, (R.x + 28, yy), 13, (215, 222, 240))
                yy += 17
            y += h
        for b in self.buttons:
            b.draw(surf)
