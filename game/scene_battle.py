import math
import time

import pygame

import ui
from ui import (W, H, text, text_box, panel, bar, chip, icon, Button, Floating, TEXT, MUTED, ACCENT, ACCENT2, GOLD, RED,
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
PLAYER_RECT = pygame.Rect(20, 370, 560, 104)
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
        self.hp_disp = [p.hp for p in game.players]
        self.hover_k = {}
        self.dt = 1 / 60

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
            self.end_btn = Button((bx, by, 226, 56), "Kết thúc lượt", self.end_turn, "primary", 18, icon_name="next")
            self.buttons += [self.end_btn, Button((bx + 236, by, 124, 56), "Đầu hàng", self.surrender, "danger", 15, icon_name="flag")]
        elif self.mode == "puzzle":
            self.end_btn = Button((bx, by, 170, 56), "Kết thúc lượt", self.end_turn, "primary", 16)
            self.buttons += [self.end_btn,
                             Button((bx + 178, by, 88, 56), "Gợi ý", self.toggle_hint, "gold", 15),
                             Button((bx + 272, by, 88, 56), "Làm lại", self.restart, size=15)]
        else:
            self.buttons += [
                Button((bx, by, 64, 56), "", lambda: self.goto(0), size=16, icon_name="first"),
                Button((bx + 72, by, 64, 56), "", lambda: self.goto(self.step - 1), size=16, icon_name="prev"),
                Button((bx + 144, by, 72, 56), "Chạy", self.toggle_auto, "primary", 15),
                Button((bx + 224, by, 64, 56), "", lambda: self.goto(self.step + 1), size=16, icon_name="next"),
                Button((bx + 296, by, 64, 56), "", lambda: self.goto(len(self.rd["actions"])), size=16, icon_name="last"),
            ]
        self.buttons.append(Button((W - 116, H - 44, 100, 34), "Thoát", self.quit, "ghost", 13, icon_name="back"))

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
        self.dt = dt
        for i, p in enumerate(self.g.players):
            self.hp_disp[i] += (p.hp - self.hp_disp[i]) * min(1, dt * 6)
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
        mid = (n - 1) / 2
        return [pygame.Rect(x0 + i * step, HAND_Y + 4 + int(abs(i - mid) ** 2 * 2), CARD_W, CARD_H) for i in range(n)]

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
    # ------------------------------------------------------------ vẽ
    def draw_status(self, surf, rect, p, idx, enemy):
        col = (255, 120, 120) if enemy else ACCENT
        active = self.g.current == idx and not self.g.over
        if active and self.mode != "replay":
            surf.blit(ui.glow(rect.w, rect.h, col, 14, 14, 110), (rect.x - 14, rect.y - 14))
        panel(surf, rect, (43, 24, 12), accent=ui.mix((120, 90, 50), col, .6 if active else .2), radius=14,
              width=2 if active else 1)
        x, y = rect.x + 14, rect.y + 12
        # avatar
        av = pygame.Rect(x, y, 52, 52)
        surf.blit(ui.vgradient(52, 52, (*ui.lighten(col, .1), 255), (*ui.darken(col, .45), 255), 14), av)
        if enemy:
            icon(surf, "bolt", av.center, 30, (255, 255, 255))
        else:
            text(surf, p.name[:1].upper(), av.center, 26, (23, 17, 4), 3, center=True)
        nx = x + 66
        text(surf, p.name, (nx, y - 2), 17, TEXT, 3)
        # máu
        hp = max(0, self.hp_disp[idx])
        hcol = GREEN if p.hp > 15 else (GOLD if p.hp > 8 else RED)
        bar(surf, (nx, y + 26, 230, 18), hp / p.max_hp, hcol)
        text(surf, f"{max(p.hp, 0)} / {p.max_hp}", (nx + 115, y + 35), 12, (255, 255, 255), 3, center=True, shadow=True)
        if p.block:
            sx = nx + 240
            icon(surf, "shield", (sx + 13, y + 34), 30, (90, 170, 255))
            text(surf, p.block, (sx + 13, y + 33), 13, (31, 17, 4), 3, center=True)
        # năng lượng
        ex = rect.right - 14 - 8 * 22
        text(surf, f"NĂNG LƯỢNG {p.energy}/{p.max_energy}", (rect.right - 14, y - 1), 10, MUTED, 3, right=True)
        for k in range(8):
            cx, cy = ex + 10 + k * 22, y + 32
            pts = [(cx + 9 * math.cos(math.pi / 6 + i * math.pi / 3), cy + 9 * math.sin(math.pi / 6 + i * math.pi / 3)) for i in range(6)]
            if k < p.energy:
                pygame.draw.polygon(surf, (124, 146, 255), pts)
                pygame.draw.polygon(surf, (220, 228, 255), pts, 1)
            elif k < p.max_energy:
                pygame.draw.polygon(surf, (65, 37, 22), pts)
                pygame.draw.polygon(surf, (90, 104, 170), pts, 1)
            else:
                pygame.draw.polygon(surf, (43, 25, 14), pts, 1)
        # trạng thái
        tags = []
        if p.sorted > 0:
            tags.append((f"ĐÃ SẮP XẾP · {p.sorted}", ACCENT))
        if p.scheduled:
            tags.append(("QUEUE " + " → ".join(str(v) for v in p.scheduled), GOLD))
        tags.append((f"MEMO {len(p.memo)}", (196, 181, 253)))
        tags.append((f"INSIGHT {p.insight}", GREEN))
        tags.append((f"BỘ BÀI {len(p.deck)}", MUTED))
        tx, ty = nx, rect.bottom - 30
        for lab, c in tags:
            w = ui.text_size(lab, 10, 3)[0] + 16
            if tx + w > rect.right - 10:
                break
            chip(surf, lab, (tx, ty), c, 10)
            tx += w + 6

    def draw(self, surf):
        g = self.g
        self.draw_bg(surf)
        me, ai = g.players
        # --- đối thủ
        self.draw_status(surf, ENEMY_RECT, ai, 1, True)
        if self.mode == "replay":
            n = max(1, len(ai.hand))
            step = min(44, (286 - 40) // max(1, n - 1)) if n > 1 else 0
            for i, cid in enumerate(ai.hand):
                r = pygame.Rect(600 + i * step, 22, 40, 58)
                cc = ui.CAT_COLOR[CARDS[cid]["cat"]]
                surf.blit(ui.vgradient(40, 58, (*ui.lighten(cc, .1), 255), (*ui.darken(cc, .5), 255), 7), r)
                pygame.draw.rect(surf, ui.lighten(cc, .3), r, 1, border_radius=7)
                ui._cat_icon(surf, CARDS[cid]["cat"], (r.centerx, r.centery + 6), 24, (255, 255, 255))
                text(surf, card_cost_label(cid), (r.x + 9, r.y + 9), 11, (255, 255, 255), 3, center=True)
            text(surf, f"Tay AI: {len(ai.hand)} thẻ (replay hiện bài mở)", (600, 92), 11, MUTED, 2)
        elif not self.puzzle:
            n = len(ai.hand)
            for i in range(n):
                ui.draw_card_back(surf, (604 + i * 32, 26 + abs(i - (n - 1) / 2) * 3, 48, 68))
            text(surf, f"{n} thẻ", (604, 100), 11, MUTED, 2)
        if self.puzzle:
            pr = pygame.Rect(596, 14, 290, 112)
            hint = self.show_hint
            panel(surf, pr, (44, 36, 14) if hint else (43, 24, 12), accent=GOLD, radius=14)
            icon(surf, "hint" if hint else "puzzle", (pr.x + 22, pr.y + 22), 18, GOLD)
            text(surf, "GỢI Ý" if hint else "MỤC TIÊU THỬ THÁCH", (pr.x + 40, pr.y + 13), 11, GOLD, 3)
            text_box(surf, self.puzzle["hint"] if hint else self.puzzle["goal"], (pr.x + 16, pr.y + 40, pr.w - 30, 66), 13)

        # --- bài toán
        cr = CHAL_RECT
        surf.blit(ui.glow(cr.w, cr.h, GOLD, 16, 14, 70), (cr.x - 14, cr.y - 14))
        panel(surf, cr, (34, 32, 40), accent=GOLD, radius=16, width=2)
        rib = pygame.Rect(cr.x + 16, cr.y - 12, 120, 26)
        surf.blit(ui.vgradient(rib.w, rib.h, (255, 214, 110, 255), (220, 150, 40, 255), 13), rib)
        text(surf, "BÀI TOÁN", rib.center, 12, (40, 24, 4), 3, center=True)
        if g.challenge:
            ch = CHALLENGES[g.challenge]
            if not self.puzzle:
                left = CHALLENGE_LIFETIME - g.challenge_age
                for k in range(CHALLENGE_LIFETIME):
                    pygame.draw.circle(surf, GOLD if k < left else (70, 64, 50), (cr.right - 24 - k * 16, cr.y + 22), 5)
                text(surf, "còn", (cr.right - 24 - CHALLENGE_LIFETIME * 16 - 4, cr.y + 14), 11, MUTED, right=True)
            text_box(surf, ch["title"], (cr.x + 20, cr.y + 34, cr.w - 40, 64), 23, TEXT, 3)
            text_box(surf, ch["desc"], (cr.x + 20, cr.y + 100, cr.w - 40, 66), 14, (214, 220, 236))
            pygame.draw.line(surf, (90, 80, 50), (cr.x + 20, cr.bottom - 44), (cr.right - 20, cr.bottom - 44))
            text(surf, "THƯỞNG KHI GIẢI TỐI ƯU", (cr.x + 20, cr.bottom - 32), 10, GOLD, 3)
            tx = cr.x + 180
            for v in ch["reward"]:
                lab = {"dmg": f"{v[1]} sát thương", "heal": f"hồi {v[1]} máu", "draw": f"rút {v[1]} thẻ",
                       "block": f"{v[1]} giáp"}[v[0]]
                rr = chip(surf, lab, (tx, cr.bottom - 36), GREEN, 11)
                tx = rr.right + 6
            chip(surf, "+2 Insight", (tx, cr.bottom - 36), ACCENT2, 11)
        else:
            icon(surf, "check", (cr.centerx, cr.centery - 14), 44, GREEN)
            text(surf, "Đã giải xong bài toán!", (cr.centerx, cr.centery + 26), 20, GREEN, 3, center=True)

        # --- thẻ vừa chơi
        pr = PLAYED_RECT
        panel(surf, pr, (43, 24, 12), radius=16)
        text(surf, "VỪA CHƠI", (pr.x + 16, pr.y + 12), 11, MUTED, 3)
        if self.last:
            cid, who, rating, expl = self.last
            chip(surf, g.players[who].name, (pr.right - 16 - ui.text_size(g.players[who].name, 10, 3)[0] - 16, pr.y + 9),
                 ACCENT if who == 0 else RED, 10)
            badge = (RATING_LABEL[rating], RATING_COLOR[rating]) if RATING_LABEL.get(rating) else None
            ui.draw_card(surf, (pr.centerx - 66, pr.y + 38, 132, 168), cid, compact=True, badge=badge)
            if expl:
                text_box(surf, expl, (pr.x + 14, pr.y + 216, pr.w - 28, 92), 12, ui.lighten(RATING_COLOR.get(rating, MUTED), .2))
        else:
            text(surf, "Chưa có thẻ nào được chơi", pr.center, 13, (146, 122, 92), center=True)

        # --- người chơi
        self.draw_status(surf, PLAYER_RECT, me, 0, False)

        # --- nhật ký
        lr = LOG_RECT
        panel(surf, lr, (34, 18, 9), radius=16)
        text(surf, "NHẬT KÝ TRẬN ĐẤU", (lr.x + 16, lr.y + 12), 11, MUTED, 3)
        pygame.draw.line(surf, LINE, (lr.x + 14, lr.y + 34), (lr.right - 14, lr.y + 34))
        y = lr.bottom - 24
        colors = {"trap": RED, "solve": GREEN, "challenge": GOLD, "play": TEXT, "end": GOLD, "turn": (150, 126, 96),
                  "effect": (214, 192, 156), "warn": ORANGE, "sys": ACCENT}
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(lr.x, lr.y + 36, lr.w, lr.h - 40))
        for entry in reversed(g.log[-60:]):
            col = colors.get(entry["kind"], TEXT)
            if entry["kind"] == "play":
                col = ACCENT if entry["who"] == 0 else (255, 150, 150)
            bold = 2 if entry["kind"] in ("play", "solve", "challenge", "end") else 0
            lines = ui.wrap(entry["text"].strip(), 12, lr.w - 44, bold)
            for j, ln in enumerate(reversed(lines)):
                if y < lr.y + 36:
                    break
                text(surf, ln, (lr.x + 28, y), 12, col, bold)
                if j == len(lines) - 1 and entry["kind"] in ("play", "solve", "challenge", "trap", "end"):
                    pygame.draw.circle(surf, col, (lr.x + 17, y + 8), 3)
                y -= 17
            if y < lr.y + 36:
                break
        surf.set_clip(clip)

        # --- tay bài
        hand = me.hand
        rects = self.hand_rects(len(hand))
        for i, (cid, r) in enumerate(zip(hand, rects)):
            k = self.hover_k.get(i, 0.0)
            k += ((1.0 if i == self.hover else 0.0) - k) * min(1, self.dt * 14)
            self.hover_k[i] = k
        order = [i for i in range(len(hand)) if i != self.hover] + ([self.hover] if self.hover is not None and self.hover < len(hand) else [])
        for i in order:
            cid, r = hand[i], rects[i]
            k = self.hover_k.get(i, 0.0)
            playable = self.my_turn() and g.can_play(cid)
            badge = None
            if self.show_hint and self.puzzle and g.challenge:
                opt, _ = best_answer(g.challenge)
                if cid == opt:
                    badge = ("GỢI Ý", GOLD)
            ui.draw_card(surf, r, cid, playable=playable or self.mode == "replay", highlight=(i == self.hover and playable),
                         badge=badge, lift=int(k * 26))
        if not hand:
            text(surf, "(không còn thẻ trên tay)", (W // 2, HAND_Y + 90), 16, MUTED, center=True)

        # --- nút & trạng thái lượt
        if self.mode in ("ai", "puzzle"):
            self.end_btn.enabled = self.my_turn()
            if self.my_turn() and not any(g.can_play(c) for c in hand):
                r = self.end_btn.rect
                pulse = int(80 + 70 * math.sin(self.t * 5))
                surf.blit(ui.glow(r.w, r.h, ACCENT, 12, 18, pulse + 60), (r.x - 18, r.y - 18))
        for b in self.buttons:
            b.draw(surf)
        sy = 474
        if self.mode == "replay":
            text(surf, f"Bước {self.step}/{len(self.rd['actions'])}  ·  Lượt {g.turn}", (900, sy), 13, TEXT, 2)
            text(surf, "Phím ← → để tua", (1260, sy), 12, MUTED, right=True)
        else:
            mine = g.current == 0
            pygame.draw.circle(surf, ACCENT if mine else GOLD, (906, sy + 9), 5)
            text(surf, f"Lượt {g.turn}  ·  {'Lượt của bạn' if mine else 'Máy đang suy nghĩ…'}", (918, sy), 13,
                 ACCENT if mine else GOLD, 2)

        if self.hover is not None and self.hover < len(hand):
            r = rects[self.hover]
            ui.draw_card_detail(surf, (r.centerx - 160, r.y - 300), hand[self.hover])

        for f in self.floats:
            f.draw(surf)
        if self.banner:
            a = min(1.0, self.banner[1] * 3)
            band = pygame.Surface((W, 110), pygame.SRCALPHA)
            band.blit(ui.vgradient(W, 110, (18, 8, 3, 0), (18, 8, 3, 0)), (0, 0))
            for yy in range(110):
                al = int(220 * a * (1 - abs(yy - 55) / 55) ** .6)
                pygame.draw.line(band, (8, 12, 28, al), (0, yy), (W, yy))
            surf.blit(band, (0, H // 2 - 130))
            col = ACCENT if "BẠN" in self.banner[0] else GOLD
            pygame.draw.line(surf, col, (W // 2 - 260, H // 2 - 108), (W // 2 + 260, H // 2 - 108), 2)
            pygame.draw.line(surf, col, (W // 2 - 260, H // 2 - 42), (W // 2 + 260, H // 2 - 42), 2)
            text(surf, self.banner[0], (W // 2, H // 2 - 75), 40, col, 3, center=True, shadow=True)
        if g.over and self.mode == "replay":
            text(surf, g._result_text(), (W // 2, H // 2 - 75), 32, GOLD, 3, center=True, shadow=True)
        if self.overlay:
            kind, title, body = self.overlay
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((10, 5, 2, 200))
            surf.blit(s, (0, 0))
            col = GREEN if kind == "win" else ORANGE
            r = pygame.Rect(W // 2 - 310, H // 2 - 150, 620, 300)
            surf.blit(ui.glow(r.w, r.h, col, 18, 24, 140), (r.x - 24, r.y - 24))
            panel(surf, r, (43, 24, 12), accent=col, radius=18, width=2)
            icon(surf, "check" if kind == "win" else "replay", (r.centerx, r.y + 46), 44, col)
            text(surf, title, (r.centerx, r.y + 96), 30, col, 3, center=True)
            text_box(surf, ("Bài học: " if kind == "win" else "Gợi ý: ") + body, (r.x + 44, r.y + 132, r.w - 88, 110), 16)
            text(surf, "Bấm chuột để " + ("quay lại danh sách thử thách" if kind == "win" else "thử lại"),
                 (r.centerx, r.bottom - 30), 13, MUTED, center=True)


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
            Button((40, H - 78, 210, 54), "Xem replay", lambda: a.go(replay_scene(a, dict(self.rec, username=a.name))), "primary", icon_name="play"),
            Button((262, H - 78, 170, 54), "Đấu lại", lambda: a.go(PlaySetupScene(a)), icon_name="sword"),
            Button((444, H - 78, 150, 54), "Menu", lambda: a.go(MenuScene(a)), "ghost", icon_name="back"),
        ]

    def handle(self, e):
        if e.type == pygame.MOUSEWHEEL:
            n = len(self.s["decisions"])
            self.scroll = max(0, min(max(0, n - 4), self.scroll - e.y))
        return super().handle(e)

    def draw(self, surf):
        self.draw_bg(surf)
        s = self.s
        w = s["winner"]
        title, col = ("CHIẾN THẮNG!", GREEN) if w == 0 else ("HOÀ", GOLD) if w == -1 else ("THẤT BẠI", RED)
        surf.blit(ui.radial(220, col, 70), (317 - 220, 66 - 220))
        text(surf, title, (317, 66), 48, col, 3, center=True, shadow=True)
        r = pygame.Rect(40, 118, 554, 506)
        panel(surf, r, (43, 24, 12), radius=18)
        big = [("Độ chính xác", f"{s['accuracy']}%", ACCENT), ("Insight", s["insight"], GREEN),
               ("Bài toán đã giải", s["solved"], GOLD)]
        for i, (lab, val, c) in enumerate(big):
            br = pygame.Rect(r.x + 20 + i * 174, r.y + 20, 164, 86)
            pygame.draw.rect(surf, (29, 15, 7), br, border_radius=14)
            pygame.draw.rect(surf, ui.darken(c, .4), br, 1, border_radius=14)
            text(surf, val, (br.centerx, br.y + 32), 32, c, 3, center=True)
            text(surf, lab, (br.centerx, br.y + 66), 12, MUTED, 2, center=True)
        text(surf, f"Số lượt {s['turns']}   ·   Máu còn {max(0, s['hp'])}   ·   Đối thủ {max(0, s['enemy_hp'])}",
             (r.x + 22, r.y + 124), 14, (200, 208, 228))
        c = s["counts"]
        y = r.y + 164
        text(surf, "PHÂN LOẠI QUYẾT ĐỊNH", (r.x + 22, y), 11, MUTED, 3)
        items = [("optimal", c.get("optimal", 0)), ("acceptable", c.get("acceptable", 0)), ("trap", c.get("trap", 0)),
                 ("missed", c.get("missed", 0)), ("failed", c.get("failed", 0))]
        total = sum(v for _, v in items)
        x = r.x + 22
        bw = r.w - 44
        pygame.draw.rect(surf, (29, 15, 7), (x, y + 24, bw, 16), border_radius=8)
        for k, v in items:
            ww = int(bw * v / total) if total else 0
            if ww:
                pygame.draw.rect(surf, RATING_COLOR[k], (x, y + 24, ww, 16), border_radius=4)
                x += ww
        for i, (k, v) in enumerate(items):
            cx = r.x + 22 + (i % 3) * 176
            cy = y + 56 + (i // 3) * 28
            pygame.draw.circle(surf, RATING_COLOR[k], (cx + 6, cy + 9), 6)
            text(surf, f"{RATING_LABEL[k].capitalize()}: {v}", (cx + 18, cy), 13, TEXT, 2)
        y = r.y + 290
        pygame.draw.line(surf, LINE, (r.x + 22, y), (r.right - 22, y))
        y += 18
        if self.server:
            sv = self.server
            chip(surf, f"+{sv['xp_gain']} XP", (r.x + 22, y), ACCENT, 14, filled=True)
            chip(surf, f"+{sv['points_gain']} điểm xếp hạng", (r.x + 140, y), GOLD, 14, filled=True)
            if sv.get("level_up"):
                text(surf, f"LÊN CẤP {sv['level']}!", (r.x + 22, y + 48), 22, GOLD, 3, shadow=True)
            if sv.get("new_unlocks"):
                text(surf, "THẺ MỚI MỞ KHOÁ", (r.x + 22, y + 88), 11, GOLD, 3)
                for i, cid in enumerate(sv["new_unlocks"][:4]):
                    ui.draw_card(surf, (r.x + 22 + i * 92, y + 108, 84, 60), cid, compact=True)
        elif self.app.user:
            text(surf, "Trận đấu chưa được lưu lên máy chủ.", (r.x + 22, y), 15, ORANGE, 2)
        else:
            text(surf, "Chế độ khách: trận đấu chỉ lưu trong phiên này.", (r.x + 22, y), 15, MUTED)

        # giải thích sau trận
        R = pygame.Rect(624, 30, 616, 660)
        panel(surf, R, (40, 22, 11), radius=18)
        icon(surf, "hint", (R.x + 32, R.y + 30), 22, GOLD)
        text(surf, "GIẢI THÍCH SAU TRẬN", (R.x + 52, R.y + 20), 17, GOLD, 3)
        text(surf, "Lăn chuột để xem thêm", (R.right - 22, R.y + 24), 12, MUTED, right=True)
        decs = s["decisions"]
        if not decs:
            text_box(surf, "Trận này bạn chưa dùng thẻ nào liên quan đến bài toán giữa sân. Hãy thử chọn thẻ phù hợp "
                     "với bài toán để nhận thưởng và Insight!", (R.x + 24, R.y + 70, R.w - 48, 80), 15, MUTED)
        y = R.y + 60
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(R.x, R.y + 52, R.w, R.h - 60))
        for d in decs[self.scroll:]:
            ch = CHALLENGES[d["challenge"]]["title"] if d.get("challenge") else "—"
            lines = ui.wrap(d["explain"], 13, R.w - 76)
            h = 62 + 18 * len(lines)
            if y > R.bottom:
                break
            col = RATING_COLOR[d["rating"]]
            card = pygame.Rect(R.x + 18, y, R.w - 36, h - 10)
            pygame.draw.rect(surf, (32, 17, 8), card, border_radius=12)
            pygame.draw.rect(surf, ui.darken(col, .35), card, 1, border_radius=12)
            pygame.draw.rect(surf, col, (card.x, card.y + 10, 4, card.h - 20), border_radius=2)
            text(surf, f"Lượt {d['turn']}  ·  {CARDS[d['card']]['name']}", (card.x + 18, card.y + 10), 14, TEXT, 3)
            lab = RATING_LABEL[d["rating"]]
            chip(surf, lab, (card.right - ui.text_size(lab, 10, 3)[0] - 30, card.y + 9), col, 10, filled=True)
            text(surf, "Bài toán: " + ch, (card.x + 18, card.y + 32), 12, MUTED)
            yy = card.y + 52
            for ln in lines:
                text(surf, ln, (card.x + 18, yy), 13, (220, 226, 242))
                yy += 18
            y += h
        surf.set_clip(clip)
        for b in self.buttons:
            b.draw(surf)
