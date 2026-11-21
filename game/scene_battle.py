import math
import time

import pygame

import ui
from ui import (W, H, text, text_box, panel, bar, chip, icon, Button, Floating, TEXT, MUTED, ACCENT, ACCENT2, GOLD, RED,
                GREEN, ORANGE, BLUE, LINE, PANEL, PANEL2, RATING_COLOR, RATING_LABEL)
from scenes_base import Scene
import board as bd
from engine import CARDS, CHALLENGES, Game, replay, choose_action, card_cost_label
from engine.challenges import best_answer
from engine.engine import CHALLENGE_LIFETIME, HAND_LIMIT

AI_DELAY = 0.9
HAND = pygame.Rect(28, 502, 1004, 194)
OPP_PORTRAIT = pygame.Rect(28, 71, 74, 74)
PLY_PORTRAIT = pygame.Rect(28, 373, 74, 74)
PLAQUE = pygame.Rect(251, 167, 714, 182)
END_BTN = pygame.Rect(1053, 566, 195, 59)
LOG_BOX = pygame.Rect(270, 62, 740, 595)
LOG_CLOSE = pygame.Rect(LOG_BOX.right - 112, LOG_BOX.y + 15, 90, 36)


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
        self.log_open = False
        self.log_offset = self.log_limit = 0
        self.pinned = False
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
        self.stat_values = [self.stats_of(p) for p in game.players]
        self.stat_flash = [[0.0] * 4 for _ in game.players]
        self.wrapped_log = {}
        self.log_source = None
        self.shake = [0.0, 0.0]
        self.play_anim = None
        self.end_hover = False

    def enter(self):
        self.build_buttons()
        if self.mode == "ai":
            self.banner = ["LƯỢT CỦA BẠN", 1.2]
        self.consume_events()

    # ------------------------------------------------------------ nút bấm
    def build_buttons(self):
        B = ui.BookButton
        self.buttons = [B((1134, 13, 116, 36), "Thoát", self.quit, size=14, icon_name="back"),
                        B((827, 13, 143, 36), "Nhật ký", self.toggle_log, size=14, icon_name="book")]
        if self.mode == "ai":
            self.buttons.append(B((982, 13, 139, 36), "Đầu hàng", self.surrender, size=14, icon_name="flag"))
        elif self.mode == "puzzle":
            self.buttons.extend([B((982, 13, 139, 36), "Làm lại", self.restart, size=14, icon_name="replay"),
                                 B((1106, 397, 132, 36), "Gợi ý", self.toggle_hint, size=14, icon_name="hint")])
        else:
            for i, (sym, action) in enumerate([("first", lambda: self.goto(0)), ("prev", lambda: self.goto(self.step - 1)),
                                               ("next", lambda: self.goto(self.step + 1)), ("last", lambda: self.goto(len(self.rd["actions"])))]):
                self.buttons.append(B((1056 + 48 * i, 588, 42, 38), "", action, size=17, icon_name=sym))
            self.buttons.append(B((1056, 639, 186, 42), "Chạy", self.toggle_auto, "primary", 16))

    def toggle_log(self):
        self.log_open = not self.log_open
        self.log_offset = 0
        self.hover = None
        self.pinned = False

    def hand_layout(self, n):
        if not n:
            return []
        gap = 7
        width = min(154, (HAND.w - gap * (n - 1)) // n)
        left = HAND.centerx - (width * n + gap * (n - 1)) // 2
        return [(pygame.Rect(left + i * (width + gap), HAND.y, width, HAND.h), 0) for i in range(n)]

    def hover_rect(self, r):
        expanded = pygame.Rect(0, 0, r.w + 4, 210)
        expanded.midbottom = (r.centerx, r.bottom - 8)
        return expanded.clamp(HAND.inflate(8, 160))

    def pick_hand(self, pos):
        layout = self.hand_layout(len(self.g.players[0].hand))
        if self.hover is not None and self.hover < len(layout) and self.hover_rect(layout[self.hover][0]).collidepoint(pos):
            return self.hover
        for i, (r, _) in enumerate(layout):
            if r.collidepoint(pos):
                return i
        return None

    def handle(self, e):
        if self.overlay and e.type == pygame.MOUSEBUTTONDOWN:
            if self.overlay[0] == "win":
                from scenes_learn import PuzzleListScene
                self.app.go(PuzzleListScene(self.app))
            else:
                self.restart()
            return True
        if self.log_open:
            if e.type == pygame.MOUSEWHEEL:
                self.log_offset = max(0, min(self.log_limit, self.log_offset + e.y * 3))
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.toggle_log()
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and (LOG_CLOSE.collidepoint(e.pos) or not LOG_BOX.collidepoint(e.pos)):
                self.toggle_log()
            return True
        if super().handle(e):
            return True
        if e.type == pygame.MOUSEMOTION:
            if not self.pinned:
                self.hover = self.pick_hand(e.pos)
            self.end_hover = END_BTN.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            i = self.pick_hand(e.pos)
            if e.button == 3 or (getattr(e, "touch", False) and i is not None and (not self.pinned or self.hover != i)):
                self.pinned = i is not None and not (self.pinned and self.hover == i)
                self.hover = i if self.pinned else None
                return True
            self.pinned = False
            if self.mode in ("ai", "puzzle") and END_BTN.collidepoint(e.pos):
                self.hover = None
                self.end_turn()
                return True
            if i is not None and self.my_turn():
                cid = self.g.players[0].hand[i]
                if self.g.can_play(cid):
                    self.g.apply({"t": "play", "i": i})
                    self.consume_events()
                    self.hover = None
                else:
                    self.app.toast("Không đủ năng lượng", ORANGE, 1.5)
                return True
            self.hover = i
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.pinned, self.hover = False, None
            if e.key == pygame.K_SPACE and self.my_turn():
                self.end_turn()
            if self.mode == "replay":
                if e.key == pygame.K_RIGHT:
                    self.goto(self.step + 1)
                elif e.key == pygame.K_LEFT:
                    self.goto(self.step - 1)
        return False

    @staticmethod
    def stats_of(p):
        return (p.hp, p.block, (p.energy, p.max_energy), p.insight)

    def draw_side(self, surf, p, idx, enemy):
        pr = OPP_PORTRAIT if enemy else PLY_PORTRAIT
        offset = round(math.sin(self.t * 55) * self.shake[idx] * 4)
        ui.plate(surf, "master" if enemy else "player", pr.move(offset, 0))
        y = pr.top
        text(surf, "ĐỐI THỦ" if enemy else "NGƯỜI CHƠI", (123, y + 3), 11, ui.STEEL, 3)
        ui.fit_text(surf, p.name, (121, y + 24, 213, 40), 26, ui.CREAM, 3)
        stats = [("HP", f"{round(self.hp_disp[idx])}/{p.max_hp}"), ("Giáp", p.block),
                 ("Năng lượng", f"{p.energy}/{p.max_energy}"), ("Insight", p.insight)]
        for j, (label, value) in enumerate(stats):
            x = 346 + j * 110
            pygame.draw.line(surf, ui.RULE, (x, y + 8), (x, y + 60))
            text(surf, label, (x + 14, y + 5), 13, ui.STEEL, 1)
            color = ui.AMBER if self.stat_flash[idx][j] > 0 else ui.CREAM
            text(surf, value, (x + 14, y + 26), 23, color, 2)
        text(surf, f"Bộ bài {len(p.deck)}    ·    Memo {len(p.memo)}", (803, y + 5), 14, ui.PAPER, 2)
        tags = []
        if p.sorted:
            tags.append(f"Đã sắp xếp {p.sorted}")
        if p.scheduled:
            tags.append("Queue " + " → ".join(map(str, p.scheduled)))
        if tags:
            ui.fit_text(surf, "   ·   ".join(tags), (803, y + 32, 250, 34), 13, ui.AMBER)
        if enemy and not self.puzzle:
            n = len(p.hand)
            text(surf, f"{n} thẻ trên tay", (1247, y + 4), 13, ui.STEEL, 1, right=True)
            for j, cid in enumerate(p.hand):
                r = pygame.Rect(1250 - 23 * (n - j), y + 29, 19, 29)
                pygame.draw.rect(surf, ui.SLATE, r, border_radius=2)
                pygame.draw.rect(surf, ui.SAND, r, 1, border_radius=2)
                if self.mode == "replay":
                    ui.plate(surf, bd.CARD_ART.get(cid, bd.FAMILY_ART[CARDS[cid]["cat"]]), r.inflate(-2, -3))
                else:
                    pygame.draw.polygon(surf, ui.SAND, [(r.centerx,r.y+8),(r.right-4,r.centery),(r.centerx,r.bottom-8),(r.x+4,r.centery)], 1)

    def draw_plaque(self, surf):
        r = PLAQUE
        pygame.draw.rect(surf, ui.INK, r.move(3, 4))
        pygame.draw.rect(surf, ui.PAPER, r)
        pygame.draw.rect(surf, ui.OCHRE, (r.x + 21, r.y, 36, 7))
        x = r.x + 20
        text(surf, "BÀI TOÁN", (x, r.y + 14), 12, ui.OCHRE, 3)
        if not self.g.challenge:
            text(surf, "Đã giải xong bài toán!", (x, r.y + 59), 27, ui.INK, 3)
            return
        ch = CHALLENGES[self.g.challenge]
        if not self.puzzle:
            for i in range(CHALLENGE_LIFETIME):
                pygame.draw.circle(surf, ui.OCHRE if i < CHALLENGE_LIFETIME - self.g.challenge_age else ui.SAND,
                                   (r.right - 46 + 11 * i, r.top + 22), 3)
        ui.fit_text(surf, ch["title"], (x, r.y + 34, r.w - 38, 42), 27, ui.INK, 3)
        text_box(surf, ch["desc"], (x, r.y + 83, r.w - 40, 50), 16, ui.INK)
        rewards = {"dmg": "{} sát thương", "block": "{} giáp", "draw": "rút {} thẻ", "heal": "hồi {} máu"}
        parts = [rewards[k].format(v) for k, v in ch["reward"]] + ["+2 Insight"]
        pygame.draw.line(surf, ui.SAND, (x, r.bottom - 40), (r.right - 20, r.bottom - 40))
        ui.fit_text(surf, "Giải tối ưu   ·   " + "   ·   ".join(parts), (x, r.bottom - 36, r.w - 40, 29), 14, ui.OCHRE)

    def draw_last(self, surf):
        x = 28
        text(surf, "THẺ VỪA CHƠI", (x, 173), 12, ui.STEEL, 3)
        if not self.last:
            ui.plate(surf, "notebook", (x, 204, 91, 91))
            text(surf, "Chưa có thẻ", (x, 308), 14, ui.STEEL)
            return
        cid, who, rating, expl = self.last
        c = CARDS[cid]
        lift = round(12 * max(0, 1 - self.play_anim[3] / .25)) if self.play_anim else 0
        ui.plate(surf, bd.CARD_ART.get(cid, bd.FAMILY_ART[c["cat"]]), (x, 202 - lift, 57, 57))
        text_box(surf, c["name"], (97, 199, 127, 46), 14, ui.CREAM, 2)
        text(surf, "Bạn" if who == 0 else "Đối thủ", (97, 245), 12, ui.STEEL)
        lab = RATING_LABEL.get(rating)
        if lab:
            text(surf, lab, (x, 269), 11, ui.AMBER, 3)
        text_box(surf, expl or c["text"], (x, 290, 207, 68), 12, ui.PAPER, line_gap=0)

    def log_lines(self, width, size):
        revision = (self.g, len(self.g.log))
        if revision != self.log_source:
            self.wrapped_log.clear()
            self.log_source = revision
        if (width, size) in self.wrapped_log:
            return self.wrapped_log[width, size]
        lines = []
        for e in self.g.log:
            fg = ui.AMBER if e["kind"] in ("solve", "trap", "challenge") else ui.PAPER
            for line in ui.wrap(e["text"].strip(), size, width):
                lines.append((line, fg))
        self.wrapped_log[width, size] = lines
        return lines

    def draw_notes(self, surf):
        x = 995
        if self.puzzle:
            text(surf, "GỢI Ý" if self.show_hint else "MỤC TIÊU THỬ THÁCH", (x, 174), 12, ui.AMBER, 3)
            text_box(surf, self.puzzle["hint"] if self.show_hint else self.puzzle["goal"], (x, 206, 246, 92), 15, ui.PAPER)
            return
        text(surf, "NHẬT KÝ TRẬN", (x, 174), 12, ui.STEEL, 3)
        lines = self.log_lines(248, 13)
        for j, (line, fg) in enumerate(lines[-7:]):
            text(surf, line, (x, 207 + 19 * j), 13, fg)

    def draw_log_modal(self, surf):
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((11, 24, 30, 185))
        surf.blit(shade, (0, 0))
        r = LOG_BOX
        pygame.draw.rect(surf, ui.NAVY, r)
        pygame.draw.rect(surf, ui.SAND, r, 1)
        text(surf, f"Nhật ký trận  ·  Lượt {self.g.turn}", (r.x+24, r.y+16), 23, ui.CREAM, 3)
        ui.BookButton(LOG_CLOSE, "Đóng", size=14, icon_name="cross").draw(surf)
        lines = self.log_lines(r.w - 50, 15)
        count = (r.h - 106) // 23
        self.log_limit = max(0, len(lines) - count)
        stop = len(lines) - min(self.log_offset, self.log_limit)
        for j, (line, fg) in enumerate(lines[max(0, stop-count):stop]):
            text(surf, line, (r.x+24, r.y+68+23*j), 15, fg)
        text(surf, "Cuộn để xem lịch sử   ·   Esc để đóng", (r.x+24, r.bottom-30), 13, ui.STEEL)

    def draw_hand(self, surf):
        hand = self.g.players[0].hand
        layout = self.hand_layout(len(hand))
        hint = best_answer(self.g.challenge)[0] if self.show_hint and self.puzzle and self.g.challenge else None
        for i, (cid, (r, _)) in enumerate(zip(hand, layout)):
            if i != self.hover:
                bd.card(surf, r, cid, self.mode == "replay" or (self.my_turn() and self.g.can_play(cid)),
                        badge=("GỢI Ý", ui.AMBER) if cid == hint else None)
        if self.hover is not None and self.hover < len(hand):
            cid = hand[self.hover]
            r = self.hover_rect(layout[self.hover][0])
            bd.card(surf, r, cid, self.mode == "replay" or (self.my_turn() and self.g.can_play(cid)), True,
                    ("GỢI Ý", ui.AMBER) if cid == hint else None)
            bd.detail(surf, cid, (981, 162))

    def draw(self, surf):
        g = self.g
        bd.board(surf)
        ui.plate(surf, "emblem", (27, 11, 40, 40))
        text(surf, "ALGO ARENA", (80, 14), 23, ui.CREAM, 3)
        mode = {"replay": "Replay", "puzzle": "Thử thách", "ai": "Đấu với AI"}[self.mode]
        text(surf, f"{mode}   /   Lượt {g.turn}", (305, 20), 15, ui.STEEL, 2)
        self.draw_side(surf, g.players[1], 1, True)
        self.draw_plaque(surf)
        self.draw_last(surf)
        if self.hover is None or self.hover >= len(g.players[0].hand):
            self.draw_notes(surf)
        self.draw_side(surf, g.players[0], 0, False)
        text(surf, f"TAY BÀI   {len(g.players[0].hand)}/{HAND_LIMIT}", (28, 470), 13, ui.STEEL, 3)
        text(surf, "Rê chuột để xem bài học   ·   Chuột phải để ghim", (HAND.right, 471), 13, ui.STEEL, right=True)
        if self.mode == "replay":
            text(surf, f"Bước {self.step}/{len(self.rd['actions'])}", (1056, 530), 21, ui.CREAM, 2)
            text(surf, "Phím ← → để tua", (1056, 560), 13, ui.STEEL)
        else:
            mine = self.my_turn()
            b = ui.BookButton(END_BTN, "Kết thúc lượt" if mine else "Lượt đối thủ", kind="primary" if mine else "normal", size=18)
            b.hover = mine and self.end_hover
            b.draw(surf)
            hint = "Còn thẻ chơi được" if mine and any(g.can_play(c) for c in g.players[0].hand) else "Phím cách" if mine else "Đang chờ"
            text(surf, hint, (END_BTN.centerx, END_BTN.bottom + 18), 13, ui.STEEL, center=True)
        for button in self.buttons:
            button.draw(surf)
        for f in self.floats:
            f.draw(surf)
        if self.banner:
            text(surf, self.banner[0], (556, 19), 15, ui.AMBER, 3)
        if g.over and self.mode == "replay":
            ui.fit_text(surf, g._result_text(), (525, 8, 286, 48), 18, ui.AMBER)
        self.draw_hand(surf)
        if self.log_open:
            self.draw_log_modal(surf)
        if self.overlay:
            kind, title, body = self.overlay
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((10, 4, 2, 200))
            surf.blit(s, (0, 0))
            col = GREEN if kind == "win" else ORANGE
            r = pygame.Rect(W // 2 - 310, H // 2 - 150, 620, 300)
            pygame.draw.rect(surf, ui.NAVY, r)
            pygame.draw.rect(surf, ui.SAND, r, 1)
            icon(surf, "check" if kind == "win" else "replay", (r.centerx, r.y + 46), 44, col)
            text(surf, title, (r.centerx, r.y + 96), 30, col, 3, center=True)
            text_box(surf, ("Bài học: " if kind == "win" else "Gợi ý: ") + body, (r.x + 44, r.y + 132, r.w - 88, 110), 16)
            text(surf, "Bấm chuột để " + ("quay lại danh sách thử thách" if kind == "win" else "thử lại"),
                 (r.centerx, r.bottom - 30), 13, MUTED, center=True)


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
        self.hover, self.pinned = None, False
        self.play_anim = None
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
                pr = OPP_PORTRAIT if ev["target"] == 1 else PLY_PORTRAIT
                pos = (pr.centerx, pr.centery + 10)
                if ev["amount"]:
                    self.floats.append(Floating(f"-{ev['amount']}", pos, (255, 70, 60), 44, 1.4))
                    self.shake[ev["target"]] = 1.0
                if ev["absorbed"]:
                    self.floats.append(Floating(f"chặn {ev['absorbed']}", (pos[0] + 70, pos[1] + 30), (200, 210, 230), 20))
            elif k == "play":
                rating = ev["rating"]
                self.last = (ev["card"], ev["who"], rating, ev.get("explain", ""))
                self.play_anim = [ev["card"], ev["who"], rating, 0.0]
            elif k == "solve":
                who = self.g.players[ev["who"]].name
                self.app.toast(f"✔ {who} giải bài toán: {CHALLENGES[ev['challenge']]['title']}", GREEN)
            elif k == "turn" and self.mode == "ai" and ev["who"] == 0:
                self.banner = ["LƯỢT CỦA BẠN", 1.0]

    # ------------------------------------------------------------ vòng lặp
    def update(self, dt):
        super().update(dt)
        for i, p in enumerate(self.g.players):
            values = self.stats_of(p)
            self.stat_flash[i] = [0.85 if a != b else max(0, t - dt)
                                  for a, b, t in zip(self.stat_values[i], values, self.stat_flash[i])]
            self.stat_values[i] = values
        self.shake = [max(0.0, s - dt * 3) for s in self.shake]
        if self.play_anim:
            self.play_anim[3] += dt
            if self.play_anim[3] > 1.5:
                self.play_anim = None
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
