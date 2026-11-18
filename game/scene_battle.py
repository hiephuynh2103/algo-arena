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
from engine.engine import CHALLENGE_LIFETIME

AI_DELAY = 0.9
CARD_W, CARD_H = 124, 176          # thẻ trên tay
HOVER_W, HOVER_H = 168, 238        # thẻ phóng to khi rê chuột
HAND_Y = 574

OPP_PORTRAIT = pygame.Rect(584, 58, 112, 132)
PLY_PORTRAIT = pygame.Rect(584, 404, 112, 132)
PLAQUE = pygame.Rect(400, 214, 480, 168)
LAST_RECT = pygame.Rect(126, 150, 250, 340)
LOG_RECT = pygame.Rect(908, 150, 250, 180)
END_BTN = pygame.Rect(936, 346, 216, 62)
OPP_MANA = pygame.Rect(968, 14, 292, 36)
PLY_MANA = pygame.Rect(968, 670, 292, 36)


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
        self.buttons = []
        if self.mode == "ai":
            self.buttons.append(Button((138, 670, 128, 36), "Đầu hàng", self.surrender, "danger", 13, icon_name="flag"))
        elif self.mode == "puzzle":
            self.buttons += [Button((936, 420, 104, 40), "Gợi ý", self.toggle_hint, "gold", 14, icon_name="hint"),
                             Button((1048, 420, 104, 40), "Làm lại", self.restart, size=14, icon_name="replay")]
        else:
            x, y = 916, 344
            self.buttons += [
                Button((x, y, 46, 46), "", lambda: self.goto(0), icon_name="first"),
                Button((x + 52, y, 46, 46), "", lambda: self.goto(self.step - 1), icon_name="prev"),
                Button((x + 104, y, 74, 46), "Chạy", self.toggle_auto, "primary", 14),
                Button((x + 184, y, 46, 46), "", lambda: self.goto(self.step + 1), icon_name="next"),
                Button((x + 236, y, 46, 46), "", lambda: self.goto(len(self.rd["actions"])), icon_name="last"),
            ]
        self.buttons.append(Button((20, 670, 110, 36), "Thoát", self.quit, "ghost", 13, icon_name="back"))

    # ------------------------------------------------------------ tay bài hình quạt
    def hand_layout(self, n):
        """Trả về [(rect_gốc, góc_xoay)] cho từng thẻ trên tay."""
        if n == 0:
            return []
        mid = (n - 1) / 2
        step = min(86, 600 / max(1, n))
        out = []
        for i in range(n):
            d = i - mid
            cx = W // 2 + d * step
            y = HAND_Y + int(d * d * 4)
            out.append((pygame.Rect(int(cx - CARD_W / 2), y, CARD_W, CARD_H), -d * 5.5))
        return out

    def hover_rect(self, r):
        hr = pygame.Rect(0, 0, HOVER_W, HOVER_H)
        hr.midbottom = (min(max(r.centerx, HOVER_W // 2 + 10), W - HOVER_W // 2 - 10), H - 4)
        return hr

    def pick_hand(self, pos):
        lay = self.hand_layout(len(self.g.players[0].hand))
        if self.hover is not None and self.hover < len(lay) and self.hover_rect(lay[self.hover][0]).collidepoint(pos):
            return self.hover
        for i in range(len(lay) - 1, -1, -1):
            if lay[i][0].collidepoint(pos):
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
        if super().handle(e):
            return True
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.pick_hand(e.pos)
            self.end_hover = END_BTN.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.mode in ("ai", "puzzle") and END_BTN.collidepoint(e.pos):
                self.end_turn()
                return True
            if self.my_turn():
                i = self.pick_hand(e.pos)
                if i is not None:
                    cid = self.g.players[0].hand[i]
                    if self.g.can_play(cid):
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
    def draw_side(self, surf, p, idx, enemy):
        pr = OPP_PORTRAIT if enemy else PLY_PORTRAIT
        active = self.g.current == idx and not self.g.over and self.mode != "replay"
        glow = ((255, 120, 90) if enemy else (120, 230, 140)) if active else None
        kind = "ai" if enemy else "me"
        bd.draw_portrait(surf, pr, kind, (p.name[:1] or "?").upper(), glow, self.shake[idx], self.t)
        # tên trên dải ruy băng
        rib = pygame.Rect(0, 0, max(120, ui.text_size(p.name, 13, 3)[0] + 34), 24)
        rib.midtop = (pr.centerx, pr.bottom + 6) if not enemy else (pr.centerx, pr.y - 30)
        pygame.draw.rect(surf, (40, 20, 10), rib.move(2, 3), border_radius=12)
        surf.blit(ui.vgradient(rib.w, rib.h, (150, 40, 44, 255), (96, 22, 26, 255), 12), rib)
        pygame.draw.rect(surf, bd.GOLD_A, rib, 2, border_radius=12)
        text(surf, p.name, rib.center, 13, (255, 240, 220), 3, center=True)
        # máu + giáp
        bd.health_drop(surf, (pr.right - 6, pr.bottom - 22), round(self.hp_disp[idx]), p.max_hp)
        if p.block:
            bd.armor_shield(surf, (pr.right - 6, pr.bottom - 70), p.block)
        # Insight (vòng tròn bên phải, như "kỹ năng anh hùng")
        bd.round_gem(surf, (pr.right + 62, pr.centery + 10), 26, (60, 170, 90), p.insight, "Insight")
        # trạng thái bên trái chân dung
        tags = []
        if p.sorted > 0:
            tags.append((f"ĐÃ SẮP XẾP · {p.sorted}", (52, 225, 196)))
        if p.scheduled:
            tags.append(("QUEUE " + " → ".join(str(v) for v in p.scheduled), GOLD))
        tags.append((f"MEMO {len(p.memo)}", (196, 181, 253)))
        tags.append((f"BỘ BÀI {len(p.deck)}", (230, 210, 180)))
        y = pr.y + 18
        for lab, c in tags:
            w = ui.text_size(lab, 11, 3)[0] + 20
            r = pygame.Rect(pr.x - 30 - w, y, w, 24)
            pygame.draw.rect(surf, (40, 22, 12), r.move(1, 2), border_radius=12)
            pygame.draw.rect(surf, (70, 40, 22), r, border_radius=12)
            pygame.draw.rect(surf, c, r, 1, border_radius=12)
            text(surf, lab, r.center, 11, c, 3, center=True)
            y += 30
        # thanh năng lượng
        bd.mana_bar(surf, OPP_MANA if enemy else PLY_MANA, p.energy, p.max_energy)

    def draw_plaque(self, surf):
        g = self.g
        r = PLAQUE
        bd.scroll_plaque(surf, r)
        ink, ink2 = (74, 40, 14), (110, 72, 34)
        text(surf, "BÀI TOÁN", (r.centerx, r.y + 16), 12, (150, 40, 44), 3, center=True)
        if g.challenge:
            ch = CHALLENGES[g.challenge]
            if not self.puzzle:
                left = CHALLENGE_LIFETIME - g.challenge_age
                for k in range(CHALLENGE_LIFETIME):
                    pygame.draw.circle(surf, (190, 60, 50) if k < left else (200, 170, 130), (r.right - 26 - k * 14, r.y + 18), 5)
            tl = ui.wrap(ch["title"], 20, r.w - 50, 3)[:2]
            y = r.y + 34
            for ln in tl:
                text(surf, ln, (r.centerx, y + 12), 20, ink, 3, center=True)
                y += 26
            for ln in ui.wrap(ch["desc"], 13, r.w - 60)[:3]:
                text(surf, ln, (r.centerx, y + 12), 13, ink2, 1, center=True)
                y += 18
            parts = [{"dmg": f"{v[1]} sát thương", "heal": f"hồi {v[1]} máu", "draw": f"rút {v[1]} thẻ",
                      "block": f"{v[1]} giáp"}[v[0]] for v in ch["reward"]]
            text(surf, "Giải tối ưu: " + " · ".join(parts) + " · +2 Insight", (r.centerx, r.bottom - 18), 12, (40, 110, 50), 3, center=True)
        else:
            icon(surf, "check", (r.centerx, r.centery - 10), 40, (40, 130, 60))
            text(surf, "Đã giải xong bài toán!", (r.centerx, r.centery + 28), 18, ink, 3, center=True)

    def draw_last_played(self, surf):
        r = LAST_RECT
        text(surf, "VỪA CHƠI", (r.centerx, r.y), 12, (110, 60, 30), 3, center=True)
        if not self.last:
            pygame.draw.rect(surf, (160, 104, 72), (r.centerx - 62, r.y + 16, 124, 172), 2, border_radius=12)
            text(surf, "—", (r.centerx, r.y + 100), 20, (120, 74, 44), center=True)
            return
        cid, who, rating, expl = self.last
        badge = (RATING_LABEL[rating], RATING_COLOR[rating]) if RATING_LABEL.get(rating) else None
        ui.draw_card(surf, (r.centerx - 62, r.y + 16, 124, 174), cid, compact=True, badge=badge)
        lab = "Bạn" if who == 0 else "Đối thủ"
        text(surf, lab, (r.centerx, r.y + 202), 11, (90, 50, 22), 3, center=True)
        if expl:
            box = pygame.Rect(r.x, r.y + 218, r.w, 112)
            pygame.draw.rect(surf, (60, 32, 18), box.move(2, 3), border_radius=10)
            surf.blit(ui.vgradient(box.w, box.h, (250, 232, 196, 255), (226, 198, 150, 255), 10), box)
            pygame.draw.rect(surf, RATING_COLOR.get(rating, (150, 104, 54)), box, 2, border_radius=10)
            text_box(surf, expl, (box.x + 10, box.y + 8, box.w - 20, box.h - 12), 11, (70, 40, 16))

    def draw_log(self, surf):
        r = LOG_RECT
        pygame.draw.rect(surf, (40, 22, 12), r.move(2, 3), border_radius=12)
        surf.blit(ui.vgradient(r.w, r.h, (70, 42, 24, 235), (50, 28, 16, 235), 12), r)
        pygame.draw.rect(surf, (180, 136, 80), r, 1, border_radius=12)
        text(surf, f"NHẬT KÝ  ·  LƯỢT {self.g.turn}", (r.x + 12, r.y + 8), 11, (240, 200, 130), 3)
        colors = {"trap": (255, 120, 110), "solve": (130, 230, 140), "challenge": (255, 214, 120), "play": (250, 240, 220),
                  "end": (255, 214, 120), "turn": (180, 150, 120), "effect": (214, 190, 156), "warn": (255, 170, 90), "sys": (240, 200, 130)}
        y = r.bottom - 18
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(r.x, r.y + 26, r.w, r.h - 30))
        for entry in reversed(self.g.log[-40:]):
            col = colors.get(entry["kind"], (250, 240, 220))
            if entry["kind"] == "play":
                col = (150, 230, 255) if entry["who"] == 0 else (255, 160, 150)
            lines = ui.wrap(entry["text"].strip(), 11, r.w - 24, 2 if entry["kind"] == "play" else 0)
            for ln in reversed(lines):
                text(surf, ln, (r.x + 12, y), 11, col, 2 if entry["kind"] == "play" else 0)
                y -= 15
            if y < r.y + 26:
                break
        surf.set_clip(clip)

    def draw_opp_hand(self, surf):
        ai = self.g.players[1]
        n = len(ai.hand)
        if self.puzzle or n == 0:
            return
        mid = (n - 1) / 2
        for i in range(n):
            d = i - mid
            x = W // 2 + int(d * 36) - 24
            y = -50 + int(abs(d) * 3)
            if self.mode == "replay":
                cid = ai.hand[i]
                cc = ui.CAT_COLOR[CARDS[cid]["cat"]]
                r = pygame.Rect(x, y + 6, 48, 66)
                surf.blit(ui.vgradient(48, 66, (*ui.lighten(cc, .1), 255), (*ui.darken(cc, .5), 255), 7), r)
                pygame.draw.rect(surf, bd.GOLD_A, r, 1, border_radius=7)
                ui._cat_icon(surf, CARDS[cid]["cat"], (r.centerx, r.bottom - 22), 24, (255, 255, 255))
            else:
                ui.draw_card_back(surf, (x, y, 48, 70))

    def draw_hand(self, surf):
        g = self.g
        hand = g.players[0].hand
        lay = self.hand_layout(len(hand))
        hint = None
        if self.show_hint and self.puzzle and g.challenge:
            hint, _ = best_answer(g.challenge)
        for i, (cid, (r, ang)) in enumerate(zip(hand, lay)):
            if i == self.hover:
                continue
            playable = (self.my_turn() and g.can_play(cid)) or self.mode == "replay"
            badge = ("GỢI Ý", GOLD) if cid == hint else None

            def build(cid=cid, playable=playable, badge=badge):
                s = pygame.Surface((CARD_W + 44, CARD_H + 44), pygame.SRCALPHA)
                ui.draw_card(s, (22, 22, CARD_W, CARD_H), cid, playable=playable, badge=badge)
                if playable and self.mode != "replay":
                    pygame.draw.rect(s, (120, 255, 140), (22, 22, CARD_W, CARD_H), 2, border_radius=14)
                return s
            img = bd.fan_card(build, cid, ang, (playable, bool(badge), self.mode == "replay"))
            surf.blit(img, img.get_rect(center=r.center))
        if self.hover is not None and self.hover < len(hand):
            cid = hand[self.hover]
            r = lay[self.hover][0]
            hr = self.hover_rect(r)
            playable = self.my_turn() and g.can_play(cid)
            ui.draw_card(surf, hr, cid, playable=playable or self.mode == "replay",
                         highlight=playable, badge=("GỢI Ý", GOLD) if cid == hint else None)
            # bài học bên cạnh thẻ phóng to
            side = hr.right + 14 if hr.centerx < W // 2 + 200 else hr.x - 334
            ui.draw_card_detail(surf, (side, hr.y + 20), cid)

    def draw(self, surf):
        g = self.g
        me, ai = g.players
        bd.draw_board(surf)
        self.draw_opp_hand(surf)
        self.draw_plaque(surf)
        self.draw_last_played(surf)
        if self.mode == "replay":
            self.draw_log(surf)
        else:
            self.draw_log(surf)
        self.draw_side(surf, ai, 1, True)
        self.draw_side(surf, me, 0, False)

        # nút kết thúc lượt (hoặc thông tin replay)
        if self.mode in ("ai", "puzzle"):
            mine = self.my_turn()
            can_any = mine and any(g.can_play(c) for c in me.hand)
            label = "KẾT THÚC LƯỢT" if mine else "LƯỢT ĐỐI THỦ"
            sub = None if (not mine or not can_any) else "còn thẻ chơi được"
            bd.end_turn_button(surf, END_BTN, mine, self.end_hover, self.t, label, sub)
        else:
            text(surf, f"Bước {self.step}/{len(self.rd['actions'])}", (1038, 404), 14, (250, 236, 210), 3, center=True, shadow=True)
            text(surf, "Phím ← → để tua", (1038, 424), 11, (220, 196, 160), 2, center=True)
        if self.puzzle:
            pz = pygame.Rect(20, 14, 360, 84)
            hint = self.show_hint
            panel(surf, pz, (60, 34, 18), accent=GOLD, radius=12)
            icon(surf, "hint" if hint else "puzzle", (pz.x + 20, pz.y + 20), 16, GOLD)
            text(surf, "GỢI Ý" if hint else "MỤC TIÊU THỬ THÁCH", (pz.x + 36, pz.y + 11), 11, GOLD, 3)
            text_box(surf, self.puzzle["hint"] if hint else self.puzzle["goal"], (pz.x + 14, pz.y + 34, pz.w - 26, 46), 12)

        for b in self.buttons:
            b.draw(surf)
        self.draw_hand(surf)

        # hoạt ảnh thẻ vừa chơi bay ra giữa bàn
        if self.play_anim:
            cid, who, rating, t = self.play_anim
            k = min(1.0, t / 0.18)
            a = 1.0 if t < 1.0 else max(0.0, 1 - (t - 1.0) / 0.5)
            sc = 0.7 + 0.3 * k
            w, h = int(170 * sc), int(240 * sc)
            cy = 280 + (60 if who == 0 else -40) * (1 - k)
            s = pygame.Surface((w + 40, h + 40), pygame.SRCALPHA)
            badge = (RATING_LABEL[rating], RATING_COLOR[rating]) if RATING_LABEL.get(rating) else None
            ui.draw_card(s, (20, 20, w, h), cid, badge=badge, highlight=rating == "optimal")
            s.set_alpha(int(255 * a))
            surf.blit(s, s.get_rect(center=(W // 2, int(cy))))
            if rating in ("optimal", "acceptable", "trap", "failed") and a > 0:
                lab = RATING_LABEL[rating] + "!"
                img = ui.render(lab, 30, RATING_COLOR[rating], 3).copy()
                img.set_alpha(int(255 * a))
                out = ui.render(lab, 30, (0, 0, 0), 3).copy()
                out.set_alpha(int(200 * a))
                rr = img.get_rect(center=(W // 2, int(cy) + h // 2 + 26))
                for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                    surf.blit(out, rr.move(dx, dy))
                surf.blit(img, rr)

        for f in self.floats:
            f.draw(surf)
        if self.banner:
            a = min(1.0, self.banner[1] * 3)
            band = pygame.Surface((W, 110), pygame.SRCALPHA)
            for yy in range(110):
                al = int(220 * a * (1 - abs(yy - 55) / 55) ** .6)
                pygame.draw.line(band, (30, 14, 6, al), (0, yy), (W, yy))
            surf.blit(band, (0, H // 2 - 110))
            col = (120, 230, 140) if "BẠN" in self.banner[0] else GOLD
            pygame.draw.line(surf, col, (W // 2 - 260, H // 2 - 88), (W // 2 + 260, H // 2 - 88), 2)
            pygame.draw.line(surf, col, (W // 2 - 260, H // 2 - 22), (W // 2 + 260, H // 2 - 22), 2)
            text(surf, self.banner[0], (W // 2, H // 2 - 55), 40, col, 3, center=True, shadow=True)
        if g.over and self.mode == "replay":
            text(surf, g._result_text(), (W // 2, H // 2 - 55), 32, GOLD, 3, center=True, shadow=True)
        if self.overlay:
            kind, title, body = self.overlay
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((10, 4, 2, 200))
            surf.blit(s, (0, 0))
            col = GREEN if kind == "win" else ORANGE
            r = pygame.Rect(W // 2 - 310, H // 2 - 150, 620, 300)
            surf.blit(ui.glow(r.w, r.h, col, 18, 24, 140), (r.x - 24, r.y - 24))
            panel(surf, r, (60, 34, 18), accent=col, radius=18, width=2)
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
        self.dt = dt
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
