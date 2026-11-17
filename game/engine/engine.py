"""Rule engine – thuần Python, không phụ thuộc Pygame.

Tính TẤT ĐỊNH (deterministic): cùng seed + cùng bộ bài + cùng chuỗi hành động
→ cùng kết quả. Nhờ đó:
  * Replay chỉ cần lưu (seed, decks, actions) rồi mô phỏng lại.
  * Server xác minh kết quả trận đấu bằng cách chạy lại engine (chống gian lận).

Hành động (action):
  {"t": "play", "i": <chỉ số thẻ trên tay>}
  {"t": "end"}
"""
import random
import copy

from .cards import CARDS
from .challenges import CHALLENGES, rate

START_HP = 30
START_HAND = 4
HAND_LIMIT = 8
MAX_ENERGY = 8
TURN_LIMIT = 40          # tổng số lượt của cả hai người
CHALLENGE_LIFETIME = 3   # số vòng trước khi bài toán hết hạn
OVERFLOW_DEPTH = 6
OVERFLOW_SELF_DMG = 4


class Player:
    def __init__(self, name, deck):
        self.name = name
        self.hp = START_HP
        self.max_hp = START_HP
        self.block = 0
        self.energy = 0
        self.max_energy = 1
        self.deck = list(deck)
        self.hand = []
        self.discard = []
        self.played_stack = []      # LIFO các thẻ đã chơi (dùng cho Undo)
        self.memo = set()           # các loại thẻ đã chơi (dùng cho DP)
        self.scheduled = []         # hàng đợi FIFO sát thương hẹn giờ (Queue)
        self.sorted = 0             # số lượt còn trạng thái "đã sắp xếp"
        self.insight = 0
        self.solved = 0

    def view(self):
        return {
            "name": self.name, "hp": self.hp, "max_hp": self.max_hp, "block": self.block,
            "energy": self.energy, "max_energy": self.max_energy, "hand": list(self.hand),
            "deck": len(self.deck), "discard": len(self.discard), "sorted": self.sorted,
            "scheduled": list(self.scheduled), "memo": len(self.memo),
            "insight": self.insight, "solved": self.solved,
        }


class Game:
    def __init__(self, seed, deck0, deck1, names=("Bạn", "Máy"), puzzle=None):
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.players = [Player(names[0], deck0), Player(names[1], deck1)]
        self.current = 0
        self.turn = 0
        self.winner = None          # 0, 1, -1 (hoà) hoặc None
        self.over = False
        self.log = []               # dòng log hiển thị
        self.events = []            # sự kiện cho UI (hiệu ứng)
        self.decisions = []         # phục vụ giải thích sau trận
        self.actions = []
        self.challenge = None
        self.challenge_age = 0
        self.puzzle = puzzle
        self.played_this_turn = []

        if puzzle:
            self._setup_puzzle(puzzle)
            return

        pool = set(deck0) | set(deck1)
        self.challenge_pool = sorted(
            cid for cid, ch in CHALLENGES.items()
            if any(c in pool for c in ch["optimal"]) or any(c in pool for c in ch["acceptable"])
        ) or sorted(CHALLENGES)
        for p in self.players:
            self.rng.shuffle(p.deck)
        for _ in range(START_HAND):
            self._draw(self.players[0])
        for _ in range(START_HAND):
            self._draw(self.players[1])
        self._new_challenge()
        self._start_turn()

    # ------------------------------------------------------------ puzzle
    def _setup_puzzle(self, pz):
        p, o = self.players
        p.hand = list(pz["hand"])
        p.deck = list(pz.get("deck", []))
        p.energy = p.max_energy = pz["energy"]
        p.sorted = pz.get("sorted", 0)
        p.hp = pz.get("hp", START_HP)
        p.memo = set(pz.get("memo", []))
        o.hp = pz["enemy_hp"]
        o.max_hp = max(o.hp, START_HP)
        o.block = pz.get("enemy_block", 0)
        o.deck = []
        self.challenge_pool = [pz["challenge"]] if pz.get("challenge") else []
        self.challenge = pz.get("challenge")
        self.turn = 1
        self._log(f"Thử thách: {pz['title']}", "sys")

    # ------------------------------------------------------------ helpers
    @property
    def me(self):
        return self.players[self.current]

    @property
    def opp(self):
        return self.players[1 - self.current]

    def _log(self, text, kind="info", who=None):
        self.log.append({"turn": self.turn, "who": self.current if who is None else who,
                         "text": text, "kind": kind})

    def _event(self, kind, **kw):
        kw["kind"] = kind
        kw["who"] = kw.get("who", self.current)
        self.events.append(kw)

    def _draw(self, p, n=1):
        for _ in range(n):
            if not p.deck:
                if not p.discard:
                    return
                p.deck = p.discard
                p.discard = []
                p.played_stack = []
                self.rng.shuffle(p.deck)
            card = p.deck.pop()
            if len(p.hand) >= HAND_LIMIT:
                p.discard.append(card)
                self._log(f"{p.name}: tay đầy, thẻ {CARDS[card]['name']} bị loại", "warn",
                          who=self.players.index(p))
            else:
                p.hand.append(card)

    def _new_challenge(self):
        options = [c for c in self.challenge_pool if c != self.challenge] or self.challenge_pool
        if not options:
            self.challenge = None
            return
        self.challenge = self.rng.choice(options)
        self.challenge_age = 0
        self._log(f"Bài toán mới: {CHALLENGES[self.challenge]['title']}", "challenge")
        self._event("challenge", challenge=self.challenge)

    def _damage(self, target_idx, amount, source=""):
        if amount <= 0:
            return 0
        t = self.players[target_idx]
        absorbed = min(t.block, amount)
        t.block -= absorbed
        real = amount - absorbed
        t.hp -= real
        self._event("damage", target=target_idx, amount=real, absorbed=absorbed, source=source)
        return real

    def _check_over(self):
        if self.over:
            return True
        dead = [i for i, p in enumerate(self.players) if p.hp <= 0]
        if dead:
            self.over = True
            if len(dead) == 2:
                self.winner = -1
            else:
                self.winner = 1 - dead[0]
            self._log(self._result_text(), "end")
            return True
        return False

    def _result_text(self):
        if self.winner == -1:
            return "Kết quả: HOÀ"
        return f"{self.players[self.winner].name} chiến thắng!"

    # ------------------------------------------------------------ turns
    def _start_turn(self):
        self.turn += 1
        p = self.me
        p.max_energy = min(MAX_ENERGY, p.max_energy + 1)
        p.energy = p.max_energy
        p.block = 0
        self.played_this_turn = []
        if p.sorted > 0:
            p.sorted -= 1
        if p.scheduled:
            amt = p.scheduled.pop(0)  # FIFO
            dealt = self._damage(1 - self.current, amt, "queue")
            self._log(f"{p.name}: Queue dequeue → {dealt} sát thương", "effect")
        if self.turn > 1:           # người đi trước không rút ở lượt đầu (cân bằng)
            self._draw(p)
        self._event("turn", turn=self.turn)
        self._check_over()

    def legal_actions(self):
        if self.over:
            return []
        acts = []
        p = self.me
        for i, cid in enumerate(p.hand):
            if self.can_play(cid):
                acts.append({"t": "play", "i": i})
        acts.append({"t": "end"})
        return acts

    def can_play(self, cid, p=None):
        p = p or self.me
        cost = CARDS[cid]["cost"]
        return (p.energy >= 1) if cost < 0 else (p.energy >= cost)

    def apply(self, action):
        if self.over:
            raise ValueError("Trận đấu đã kết thúc")
        t = action.get("t")
        if t == "play":
            i = action.get("i")
            if not isinstance(i, int) or i < 0 or i >= len(self.me.hand):
                raise ValueError("Chỉ số thẻ không hợp lệ")
            cid = self.me.hand[i]
            if not self.can_play(cid):
                raise ValueError("Không đủ năng lượng")
            self.actions.append({"t": "play", "i": i})
            self._play(i)
        elif t == "end":
            self.actions.append({"t": "end"})
            self._end_turn()
        else:
            raise ValueError("Hành động không hợp lệ")

    def _end_turn(self):
        p = self.me
        self._check_missed()
        self._log(f"{p.name} kết thúc lượt", "turn")
        if self.puzzle:
            # Thử thách chỉ có 1 lượt: kết thúc lượt mà đối thủ chưa gục là thất bại
            self.over = True
            self.winner = 0 if self.players[1].hp <= 0 else 1
            return
        if self.current == 1:
            self.challenge_age += 1
            if self.challenge and self.challenge_age >= CHALLENGE_LIFETIME:
                self._log(f"Bài toán \"{CHALLENGES[self.challenge]['title']}\" hết hạn", "challenge")
                self._new_challenge()
        if self.turn >= TURN_LIMIT:
            self.over = True
            a, b = self.players
            self.winner = 0 if a.hp > b.hp else 1 if b.hp > a.hp else -1
            self._log("Hết giới hạn lượt. " + self._result_text(), "end")
            return
        self.current = 1 - self.current
        self._start_turn()

    def _check_missed(self):
        """Ghi nhận cơ hội bỏ lỡ: còn thẻ tối ưu đủ năng lượng mà không dùng."""
        if not self.challenge:
            return
        p = self.me
        for cid in set(p.hand):
            r, why = rate(self.challenge, cid)
            if r == "optimal" and self.can_play(cid):
                if CARDS[cid]["effects"][0][0] == "need_sorted" and p.sorted <= 0:
                    continue
                self.decisions.append({
                    "turn": self.turn, "who": self.current, "card": cid,
                    "challenge": self.challenge, "rating": "missed",
                    "explain": f"Bạn có {CARDS[cid]['name']} và đủ năng lượng nhưng không dùng. {why}",
                })
                break

    # ------------------------------------------------------------ play card
    def _play(self, i):
        p = self.me
        cid = p.hand.pop(i)
        card = CARDS[cid]
        cost = card["cost"]
        x = p.energy if cost < 0 else 0
        p.energy -= x if cost < 0 else cost

        rating, why = rate(self.challenge, cid) if self.challenge else ("neutral", "")
        scale = 0.5 if rating == "trap" else 1.0
        self._log(f"{p.name} dùng {card['name']}", "play")
        self._event("play", card=cid, rating=rating, explain="")
        play_ev = self.events[-1]

        ok = self._run_effects(card["effects"], scale, cid, x)

        p.discard.append(cid)
        if cid != "undo":
            p.played_stack.append(cid)
        p.memo.add(cid)
        self.played_this_turn.append(cid)

        if self.challenge and rating != "neutral":
            if not ok and rating in ("optimal", "acceptable"):
                rating = "failed"
                why = ("Đúng thuật toán nhưng chưa thoả tiền điều kiện (dữ liệu chưa sắp xếp). "
                       "Hãy dùng một thẻ Sắp xếp trước.")
            self.decisions.append({"turn": self.turn, "who": self.current, "card": cid,
                                   "challenge": self.challenge, "rating": rating, "explain": why})
            play_ev["rating"], play_ev["explain"] = rating, why
            if rating == "trap":
                self._log(f"⚠ Lựa chọn sai cho bài toán: hiệu ứng giảm một nửa. {why}", "trap")
            elif rating in ("optimal", "acceptable"):
                self._solve(rating, why)
        elif not ok:
            self.decisions.append({"turn": self.turn, "who": self.current, "card": cid,
                                   "challenge": self.challenge, "rating": "failed",
                                   "explain": "Tiền điều kiện chưa thoả: dữ liệu chưa được sắp xếp."})
            play_ev["rating"], play_ev["explain"] = "failed", self.decisions[-1]["explain"]
        self._check_over()

    def _solve(self, rating, why):
        p = self.me
        ch = CHALLENGES[self.challenge]
        half = rating == "acceptable"
        p.insight += 1 if half else 2
        p.solved += 1
        tag = "chưa tối ưu" if half else "TỐI ƯU"
        self._log(f"✔ {p.name} giải \"{ch['title']}\" ({tag})", "solve")
        self._event("solve", challenge=self.challenge, rating=rating)
        self._run_effects(ch["reward"], 0.5 if half else 1.0, "reward", 0)
        if not self.puzzle:
            self._new_challenge()
        else:
            self.challenge = None

    def _run_effects(self, effects, scale, source, x):
        p = self.me
        me_idx = self.current
        ok = True

        def sc(n):
            return int(n * scale) if scale != 1.0 else n

        for eff in effects:
            op = eff[0]
            if op == "dmg":
                d = self._damage(1 - me_idx, sc(eff[1]), source)
                self._log(f"  → {d} sát thương", "effect")
            elif op == "block":
                p.block += sc(eff[1])
                self._log(f"  → +{sc(eff[1])} giáp", "effect")
            elif op == "heal":
                h = min(sc(eff[1]), p.max_hp - p.hp)
                p.hp += h
                self._log(f"  → hồi {h} máu", "effect")
            elif op == "draw":
                n = eff[1] if scale >= 1 else max(0, eff[1] // 2)
                self._draw(p, n)
                if n:
                    self._log(f"  → rút {n} thẻ", "effect")
            elif op == "sort":
                p.sorted = max(p.sorted, eff[1])
                self._log("  → dữ liệu ĐÃ SẮP XẾP", "effect")
            elif op == "unsort_opp":
                self.opp.sorted = 0
                self._log("  → dữ liệu đối thủ bị xáo trộn", "effect")
            elif op == "schedule":
                vals = [sc(v) for v in eff[1]]
                p.scheduled.extend(vals)
                self._log(f"  → enqueue {vals}", "effect")
            elif op == "need_sorted":
                if p.sorted > 0:
                    self._run_effects(eff[1], scale, source, x)
                else:
                    if eff[2]:
                        self._run_effects(eff[2], scale, source, x)
                    else:
                        self._log("  ✖ Thất bại: dữ liệu CHƯA sắp xếp!", "trap")
                    ok = False
            elif op == "tutor":
                found = None
                if self.challenge:
                    opts = list(CHALLENGES[self.challenge]["optimal"])
                    for k in range(len(p.deck) - 1, -1, -1):
                        if p.deck[k] in opts:
                            found = p.deck.pop(k)
                            break
                if found and len(p.hand) < HAND_LIMIT:
                    p.hand.append(found)
                    self._log(f"  → tra cứu O(1): lấy {CARDS[found]['name']}", "effect")
                else:
                    if found:
                        p.deck.append(found)
                    self._draw(p, 1)
                    self._log("  → không tìm thấy thẻ tối ưu, rút 1 thẻ", "effect")
            elif op == "heapdmg":
                mx = max([max(CARDS[c]["cost"], 0) for c in p.hand] or [0])
                d = self._damage(1 - me_idx, sc(eff[1] + mx), source)
                self._log(f"  → lấy max = {mx}: {d} sát thương", "effect")
            elif op == "memodmg":
                bonus = min(len(p.memo - {"dp"}), eff[2])
                d = self._damage(1 - me_idx, sc(eff[1] + bonus), source)
                self._log(f"  → tra bảng memo ({bonus} kết quả con): {d} sát thương", "effect")
            elif op == "recursion":
                if x >= OVERFLOW_DEPTH:
                    self._damage(me_idx, OVERFLOW_SELF_DMG, "overflow")
                    self._log(f"  ✖ STACK OVERFLOW ở độ sâu {x}! Bạn nhận {OVERFLOW_SELF_DMG} sát thương", "trap")
                    ok = False
                else:
                    d = self._damage(1 - me_idx, sc(2 * x), source)
                    self._log(f"  → đệ quy độ sâu {x}: {d} sát thương", "effect")
            elif op == "undo":
                if p.played_stack:
                    last = p.played_stack.pop()
                    # rút bản sao cuối cùng của thẻ đó khỏi chồng bài đã dùng
                    for k in range(len(p.discard) - 1, -1, -1):
                        if p.discard[k] == last:
                            p.discard.pop(k)
                            break
                    if len(p.hand) < HAND_LIMIT:
                        p.hand.append(last)
                        self._log(f"  → pop: {CARDS[last]['name']} trở về tay", "effect")
                    else:
                        p.discard.append(last)
                else:
                    self._log("  → ngăn xếp rỗng, không có gì để hoàn tác", "effect")
        return ok

    # ------------------------------------------------------------ summary
    def view(self):
        return {
            "turn": self.turn, "current": self.current, "challenge": self.challenge,
            "challenge_age": self.challenge_age, "over": self.over, "winner": self.winner,
            "players": [p.view() for p in self.players],
        }

    def summary(self, who=0):
        mine = [d for d in self.decisions if d["who"] == who]
        cnt = {k: 0 for k in ("optimal", "acceptable", "trap", "missed", "failed")}
        for d in mine:
            cnt[d["rating"]] = cnt.get(d["rating"], 0) + 1
        total = cnt["optimal"] + cnt["acceptable"] + cnt["trap"] + cnt["missed"] + cnt["failed"]
        good = cnt["optimal"] + 0.5 * cnt["acceptable"]
        acc = round(100 * good / total) if total else 0
        p = self.players[who]
        return {
            "winner": self.winner, "turns": self.turn, "accuracy": acc, "counts": cnt,
            "insight": p.insight, "solved": p.solved, "hp": p.hp,
            "enemy_hp": self.players[1 - who].hp, "decisions": mine,
        }

    def clone(self):
        g = copy.copy(self)
        g.rng = random.Random()
        g.rng.setstate(self.rng.getstate())
        g.players = [copy.deepcopy(p) for p in self.players]
        g.log = []
        g.events = []
        g.decisions = []
        g.actions = []
        g.played_this_turn = list(self.played_this_turn)
        return g


def replay(seed, deck0, deck1, actions, names=("Bạn", "Máy"), upto=None, puzzle=None):
    """Mô phỏng lại một trận từ seed + hành động. upto: số hành động áp dụng."""
    g = Game(seed, deck0, deck1, names=names, puzzle=puzzle)
    n = len(actions) if upto is None else min(upto, len(actions))
    for a in actions[:n]:
        g.apply(a)
    return g
