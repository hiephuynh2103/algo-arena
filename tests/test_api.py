from fastapi.testclient import TestClient
from app.main import app
from engine import Game, choose_action, ai_deck, STARTER_DECK
from engine.puzzles import PUZZLE_BY_ID

def client():
    return TestClient(app)

def auth(c, u="alice", p="secret12", register=True):
    r = c.post("/api/auth/register" if register else "/api/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}

def play_full(seed, deck, diff):
    g = Game(seed, deck, ai_deck(diff, seed))
    while not g.over:
        g.apply(choose_action(g, "hard" if g.current == 0 else diff))
    return g

def test_flow():
    with client() as c:
        h = auth(c)
        assert c.post("/api/auth/register", json={"username": "alice", "password": "secret12"}).status_code == 409
        assert c.post("/api/auth/login", json={"username": "alice", "password": "wrong!!"}).status_code == 401
        assert c.get("/api/me").status_code == 401
        me = c.get("/api/me", headers=h).json()
        assert me["level"] == 1 and "dp" not in me["unlocked"]
        # deck chưa mở khoá bị từ chối
        bad = STARTER_DECK[:-1] + ["dp"]
        assert c.post("/api/decks", json={"name": "x", "cards": bad}, headers=h).status_code == 400
        # trận đấu được xác minh lại trên server
        g = play_full(123, STARTER_DECK, "easy")
        body = {"difficulty": "easy", "seed": 123, "player_deck": STARTER_DECK, "actions": g.actions}
        r = c.post("/api/matches", json=body, headers=h)
        assert r.status_code == 200, r.text
        res = r.json()
        assert res["winner"] == g.winner and res["summary"]["accuracy"] == g.summary(0)["accuracy"]
        assert c.post("/api/matches", json=body, headers=h).status_code == 409   # không gửi lại seed cũ
        tampered = dict(body, seed=124, actions=g.actions[:3])
        assert c.post("/api/matches", json=tampered, headers=h).status_code == 400
        mid = res["match_id"]
        rep = c.get(f"/api/matches/{mid}", headers=h).json()
        assert rep["actions"] == g.actions and rep["ai_deck"] == ai_deck("easy", 123)
        # puzzle: lời giải sai bị từ chối, đúng thì mở khoá thẻ
        assert c.post("/api/puzzles/p1/complete", json={"actions": [{"t": "end"}]}, headers=h).status_code == 400
        sol = [{"t": "play", "i": 3}, {"t": "play", "i": 1}]
        r = c.post("/api/puzzles/p1/complete", json={"actions": sol}, headers=h).json()
        assert r["first_time"] and "binary_search" in r["new_unlocks"]
        deck = ["binary_search", "binary_search", "quick_sort", "quick_sort"] + STARTER_DECK[:8]
        r = c.post("/api/decks", json={"name": "Sort+Search", "cards": deck}, headers=h)
        assert r.status_code == 200 and r.json()["is_active"]
        assert c.get("/api/me", headers=h).json()["active_deck"] == deck
        assert c.post("/api/tutorials/t1/complete", headers=h).json()["first_time"]
        lb = c.get("/api/leaderboard").json()
        assert lb[0]["username"] == "alice"
        assert c.get("/api/admin/stats", headers=h).status_code == 403

def test_admin():
    with client() as c:
        ha = auth(c, "admin", "admin123", register=False)
        hb = auth(c, "bob", "secret12")
        st = c.get("/api/admin/stats", headers=ha).json()
        assert st["total_users"] >= 2 and len(st["cards"]) == 24
        users = c.get("/api/admin/users?q=bob", headers=ha).json()
        bid = users[0]["id"]
        assert c.patch(f"/api/admin/users/{bid}", json={"is_active": False}, headers=ha).status_code == 200
        assert c.get("/api/me", headers=hb).status_code == 403
        assert c.post("/api/auth/login", json={"username": "bob", "password": "secret12"}).status_code == 403
        assert c.patch(f"/api/admin/users/{bid}", json={"is_active": True, "new_password": "newpass1"}, headers=ha).status_code == 200
        auth(c, "bob", "newpass1", register=False)
        me_id = c.get("/api/me", headers=ha).json()["id"]
        assert c.patch(f"/api/admin/users/{me_id}", json={"role": "player"}, headers=ha).status_code == 400
        assert c.delete(f"/api/admin/users/{bid}", headers=ha).status_code == 200
        assert c.get("/", ).status_code == 200 and c.get("/admin").status_code == 200
