"""AI đối thủ với 3 mức độ.

- easy  : chọn ngẫu nhiên trong các thẻ chơi được.
- normal: tham lam 1 bước – thử từng thẻ trên bản sao trạng thái, chọn thẻ làm hàm đánh giá tăng nhiều nhất.
- hard  : tìm kiếm theo chiều sâu (DFS) các chuỗi tối đa 3 thẻ trong lượt, có cắt tỉa theo beam.
"""
import random

from .cards import CARDS

AI_DECKS = {
    "easy": [
        ["linear_search", "linear_search", "stack", "stack", "queue", "queue",
         "greedy", "greedy", "bfs", "dfs", "hash_table", "bubble_sort"],
    ],
    "normal": [
        ["greedy", "greedy", "bfs", "bfs", "dfs", "queue", "stack", "stack",
         "quick_sort", "binary_search", "dijkstra", "hash_table"],
        ["linear_search", "greedy", "stack", "undo", "undo", "queue", "queue",
         "bfs", "dfs", "dijkstra", "hash_table", "union_find"],
    ],
    "hard": [
        ["greedy", "greedy", "quick_sort", "binary_search", "binary_search", "dp", "dp",
         "dijkstra", "bellman_ford", "heap", "stack", "hash_table"],
        ["merge_sort", "quick_sort", "binary_search", "binary_search", "two_pointers", "heap",
         "dp", "dijkstra", "kruskal", "union_find", "stack", "greedy"],
    ],
}

DIFFICULTY_POINTS = {"easy": 10, "normal": 20, "hard": 35}


def ai_deck(difficulty, seed):
    decks = AI_DECKS.get(difficulty, AI_DECKS["normal"])
    return list(random.Random(seed * 7 + 13).choice(decks))


def evaluate(g, me):
    if g.over:
        if g.winner == me:
            return 10_000 - g.turn
        if g.winner == -1:
            return 0
        return -10_000
    a, b = g.players[me], g.players[1 - me]
    score = 0.0
    score += 4.0 * (b.max_hp - b.hp)
    score -= 3.0 * (a.max_hp - a.hp)
    score += 1.2 * a.block
    score += 1.5 * a.insight
    score += 0.8 * len(a.hand)
    score += 1.5 * sum(a.scheduled)
    score += 1.0 * min(a.sorted, 1) * sum(1 for c in a.hand if c in ("binary_search", "two_pointers"))
    score += 0.4 * len(a.memo)
    return score


def _plays(g):
    seen = set()
    res = []
    for a in g.legal_actions():
        if a["t"] != "play":
            continue
        cid = g.me.hand[a["i"]]
        if cid in seen:         # thẻ trùng tên cho kết quả như nhau
            continue
        seen.add(cid)
        res.append(a)
    return res


def _search(g, me, depth, beam):
    best = evaluate(g, me)
    if depth == 0 or g.over or g.current != me:
        return best
    cands = []
    for a in _plays(g):
        c = g.clone()
        c.apply(a)
        cands.append((evaluate(c, me), c))
    cands.sort(key=lambda x: -x[0])
    for _, c in cands[:beam]:
        best = max(best, _search(c, me, depth - 1, beam))
    return best


def choose_action(g, difficulty="normal", rng=None):
    me = g.current
    rng = rng or random.Random(g.seed + g.turn * 101 + len(g.actions))
    plays = _plays(g)
    if not plays:
        return {"t": "end"}

    if difficulty == "easy":
        if rng.random() < 0.25:
            return {"t": "end"}
        return rng.choice(plays)

    base = evaluate(g, me)
    scored = []
    for a in plays:
        c = g.clone()
        c.apply(a)
        if difficulty == "hard":
            s = _search(c, me, 2, 4)
        else:
            s = evaluate(c, me)
        scored.append((s, a))
    scored.sort(key=lambda x: -x[0])
    best_s, best_a = scored[0]
    # Thêm chút nhiễu cho mức normal để không quá máy móc
    if difficulty == "normal" and len(scored) > 1 and rng.random() < 0.15:
        best_s, best_a = scored[1]
    if best_s <= base + 0.01:
        return {"t": "end"}
    return best_a


def describe_ai(difficulty):
    return {"easy": "Dễ – chơi ngẫu nhiên",
            "normal": "Thường – tham lam 1 bước",
            "hard": "Khó – tìm kiếm DFS 3 bước"}[difficulty]


def card_value(cid):
    return CARDS[cid]["cost"]
