"""Công cụ kiểm tra: (1) giải vét cạn các thử thách, (2) mô phỏng AI vs AI để cân bằng thẻ."""
import sys, os, itertools, collections, random, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
from engine import Game, PUZZLES, choose_action, ai_deck, CARDS
from engine.puzzles import PUZZLE_BY_ID

def solve_puzzle(pz):
    """Đếm số chuỗi hành động thắng / tổng số chuỗi (DFS)."""
    wins, total, example = 0, 0, None
    def dfs(g, path):
        nonlocal wins, total, example
        if g.over:
            total += 1
            if g.winner == 0:
                wins += 1
                example = example or path
            return
        for a in g.legal_actions():
            c = g.clone(); c.puzzle = g.puzzle
            c.apply(a)
            names = path + ([g.me.hand[a["i"]]] if a["t"] == "play" else ["END"])
            dfs(c, names)
    dfs(Game(0, [], [], puzzle=pz), [])
    return wins, total, example

def play_match(seed, d0, d1, diff0, diff1):
    g = Game(seed, d0, d1, names=("A", "B"))
    guard = 0
    while not g.over and guard < 2000:
        diff = diff0 if g.current == 0 else diff1
        g.apply(choose_action(g, diff)); guard += 1
    return g

if __name__ == "__main__":
    for pz in PUZZLES:
        w, t, ex = solve_puzzle(pz)
        print(f"{pz['id']}: {w}/{t} chuỗi thắng  ví dụ: {ex}")
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    res = collections.Counter(); card_win = collections.Counter(); card_n = collections.Counter()
    turns = []
    for diff_a, diff_b in [("hard","easy"),("hard","normal"),("normal","easy"),("normal","normal")]:
        wins = collections.Counter()
        for s in range(n):
            d0 = ai_deck(diff_a, s); d1 = ai_deck(diff_b, s+999)
            g = play_match(s, d0, d1, diff_a, diff_b)
            wins[g.winner] += 1; turns.append(g.turn)
            for p_i, deck in enumerate((d0, d1)):
                for c in set(deck):
                    card_n[c] += 1; card_win[c] += (g.winner == p_i)
        print(f"{diff_a} vs {diff_b}: {dict(wins)}")
    print("số lượt TB:", sum(turns)/len(turns))
    print("Tỉ lệ thắng khi có thẻ trong bộ bài:")
    for c in sorted(card_n, key=lambda c: -card_win[c]/card_n[c]):
        print(f"  {c:15s} {100*card_win[c]/card_n[c]:5.1f}%  (n={card_n[c]})")

def balance_random_decks(n=400, diff="normal"):
    """Bộ bài ngẫu nhiên, cùng mức AI → tỉ lệ thắng theo thẻ ít bị nhiễu bởi bộ bài cố định."""
    rng = random.Random(42)
    ids = list(CARDS)
    win = collections.Counter(); cnt = collections.Counter(); first = collections.Counter()
    for s in range(n):
        decks = []
        for _ in range(2):
            d = []
            while len(d) < 12:
                c = rng.choice(ids)
                if d.count(c) < 2: d.append(c)
            decks.append(d)
        g = play_match(s, decks[0], decks[1], diff, diff)
        first[g.winner] += 1
        for i, d in enumerate(decks):
            for c in set(d):
                cnt[c] += 1; win[c] += g.winner == i
    return first, {c: round(100*win[c]/cnt[c],1) for c in cnt}
