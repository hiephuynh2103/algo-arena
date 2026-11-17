import random
from engine import Game, replay, PUZZLES, CARDS, CHALLENGES, choose_action, ai_deck, validate_deck, STARTER_DECK
from engine.challenges import rate

def run(seed, d0, d1, a="normal", b="normal"):
    g = Game(seed, d0, d1)
    while not g.over:
        g.apply(choose_action(g, a if g.current == 0 else b))
    return g

def test_challenges_reference_existing_cards():
    for cid, ch in CHALLENGES.items():
        assert ch["optimal"], cid
        for k in ("optimal", "acceptable", "traps"):
            for card in ch[k]:
                assert card in CARDS, (cid, card)

def test_deterministic_replay():
    for s in range(15):
        d0, d1 = ai_deck("hard", s), ai_deck("normal", s + 1)
        g = run(s, d0, d1, "hard", "normal")
        r = replay(s, d0, d1, g.actions)
        assert r.over and r.winner == g.winner and r.turn == g.turn
        assert [p.hp for p in r.players] == [p.hp for p in g.players]

def test_tampered_replay_rejected():
    g = Game(1, STARTER_DECK, STARTER_DECK)
    try:
        replay(1, STARTER_DECK, STARTER_DECK, [{"t": "play", "i": 99}])
        assert False
    except ValueError:
        pass

def test_binary_search_needs_sorted():
    pz = {"title": "t", "hand": ["binary_search"], "energy": 3, "enemy_hp": 30, "challenge": None}
    g = Game(0, [], [], puzzle=pz); g.apply({"t": "play", "i": 0})
    assert g.players[1].hp == 30
    pz2 = dict(pz, sorted=2); g = Game(0, [], [], puzzle=pz2); g.apply({"t": "play", "i": 0})
    assert g.players[1].hp == 25

def test_trap_halves_effect_and_optimal_solves():
    pz = {"title": "t", "hand": ["greedy", "dp"], "energy": 5, "enemy_hp": 30, "challenge": "knapsack"}
    g = Game(0, [], [], puzzle=pz); g.apply({"t": "play", "i": 0})
    assert g.players[1].hp == 29 and g.decisions[-1]["rating"] == "trap"
    g.apply({"t": "play", "i": 0})
    assert g.decisions[-1]["rating"] == "optimal" and g.players[0].insight == 2

def test_recursion_overflow():
    pz = {"title": "t", "hand": ["recursion"], "energy": 6, "enemy_hp": 30, "challenge": None}
    g = Game(0, [], [], puzzle=pz); g.apply({"t": "play", "i": 0})
    assert g.players[0].hp == 26 and g.players[1].hp == 30

def test_undo_is_lifo():
    pz = {"title": "t", "hand": ["greedy", "bfs", "undo"], "energy": 5, "enemy_hp": 30, "challenge": None}
    g = Game(0, [], [], puzzle=pz)
    g.apply({"t": "play", "i": 0}); g.apply({"t": "play", "i": 0}); g.apply({"t": "play", "i": 0})
    assert g.players[0].hand == ["bfs"]

def test_queue_fifo_schedule():
    g = Game(3, ["queue"] * 2 + ["stack"] * 10, ["stack"] * 12)
    p = g.players[0]
    p.hand = ["queue"]; p.energy = 5; g.challenge = None
    g.apply({"t": "play", "i": 0})
    assert p.scheduled == [2, 2]
    g.apply({"t": "end"}); g.apply({"t": "end"})
    assert p.scheduled == [2]

def test_puzzles_solvable_and_not_trivial():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    from simulate import solve_puzzle
    for pz in PUZZLES:
        w, t, ex = solve_puzzle(pz)
        assert w >= 1, pz["id"]
        assert w / t < 0.5, pz["id"]

def test_ai_strength_order():
    wins = 0
    for s in range(20):
        g = run(s, ai_deck("normal", s), ai_deck("normal", s + 5), "hard", "easy")
        wins += g.winner == 0
    assert wins >= 16

def test_validate_deck():
    assert validate_deck(STARTER_DECK)[0]
    assert not validate_deck(STARTER_DECK[:-1])[0]
    assert not validate_deck(["greedy"] * 12)[0]
    assert not validate_deck(STARTER_DECK[:-1] + ["dp"], set(STARTER_DECK))[0]

def test_rate():
    assert rate("knapsack", "greedy")[0] == "trap"
    assert rate("knapsack", "dp")[0] == "optimal"
    assert rate("gps", "bellman_ford")[0] == "acceptable"
    assert rate("gps", "stack")[0] == "neutral"
