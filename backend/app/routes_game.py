from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from engine import (CARDS, CHALLENGES, PUZZLES, TUTORIALS, STARTER_DECK, CATEGORY_LABEL,
                    DECK_SIZE, MAX_COPIES, validate_deck, replay, ai_deck)
from engine.puzzles import PUZZLE_BY_ID
from engine.tutorials import TUTORIAL_BY_ID

from .db import get_db, User, Deck, Match, Event, now
from .security import (current_user, hash_password, verify_password, create_token, USERNAME_RE)
from .progress import (user_public, user_unlocked, level_of, match_rewards, PUZZLE_XP, TUTORIAL_XP)

router = APIRouter(prefix="/api")
MAX_ACTIONS = 1500


# ------------------------------------------------------------------ Auth
class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)


def _active_deck(db, user):
    return db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.is_active.is_(True)))


@router.post("/auth/register")
def register(body: Credentials, db: Session = Depends(get_db)):
    if not USERNAME_RE.match(body.username):
        raise HTTPException(400, "Tên đăng nhập 3–32 ký tự, chỉ gồm chữ, số, '_' và '.'")
    if db.scalar(select(User).where(func.lower(User.username) == body.username.lower())):
        raise HTTPException(409, "Tên đăng nhập đã tồn tại")
    user = User(username=body.username, password_hash=hash_password(body.password),
                puzzles_done=[], tutorials_done=[], last_login=now())
    db.add(user)
    db.flush()
    db.add(Deck(user_id=user.id, name="Bộ khởi đầu", cards=list(STARTER_DECK), is_active=True))
    db.add(Event(user_id=user.id, type="register", data={}))
    db.commit()
    return {"token": create_token(user), "user": user_public(user, _active_deck(db, user))}


@router.post("/auth/login")
def login(body: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.username) == body.username.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu")
    if not user.is_active:
        raise HTTPException(403, "Tài khoản đã bị khoá. Liên hệ quản trị viên.")
    user.last_login = now()
    db.add(Event(user_id=user.id, type="login", data={}))
    db.commit()
    return {"token": create_token(user), "user": user_public(user, _active_deck(db, user))}


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


@router.post("/auth/password")
def change_password(body: PasswordChange, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "Mật khẩu cũ không đúng")
    user.password_hash = hash_password(body.new_password)
    db.merge(user)
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_public(user, _active_deck(db, user))


# ------------------------------------------------------------------ Catalog
@router.get("/catalog")
def catalog():
    return {
        "cards": {k: {kk: vv for kk, vv in v.items() if kk != "effects"} for k, v in CARDS.items()},
        "categories": CATEGORY_LABEL,
        "challenges": {k: {"title": v["title"], "desc": v["desc"]} for k, v in CHALLENGES.items()},
        "puzzles": [{k: p[k] for k in ("id", "title", "topic", "goal", "unlocks")} for p in PUZZLES],
        "tutorials": [{"id": t["id"], "title": t["title"], "puzzle": t["puzzle"]} for t in TUTORIALS],
        "deck_size": DECK_SIZE, "max_copies": MAX_COPIES,
    }


# ------------------------------------------------------------------ Decks
class DeckBody(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    cards: list[str]
    activate: bool = True


def _deck_out(d):
    return {"id": d.id, "name": d.name, "cards": d.cards, "is_active": d.is_active,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None}


@router.get("/decks")
def list_decks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    decks = db.scalars(select(Deck).where(Deck.user_id == user.id).order_by(Deck.id)).all()
    return [_deck_out(d) for d in decks]


def _activate(db, user, deck):
    for d in db.scalars(select(Deck).where(Deck.user_id == user.id)).all():
        d.is_active = d.id == deck.id


@router.post("/decks")
def create_deck(body: DeckBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ok, msg = validate_deck(body.cards, set(user_unlocked(user)))
    if not ok:
        raise HTTPException(400, msg)
    if db.scalar(select(func.count(Deck.id)).where(Deck.user_id == user.id)) >= 10:
        raise HTTPException(400, "Tối đa 10 bộ bài")
    d = Deck(user_id=user.id, name=body.name, cards=body.cards)
    db.add(d)
    db.flush()
    if body.activate:
        _activate(db, user, d)
    db.add(Event(user_id=user.id, type="deck_saved", data={"cards": body.cards}))
    db.commit()
    return _deck_out(d)


def _own_deck(db, user, deck_id):
    d = db.get(Deck, deck_id)
    if not d or d.user_id != user.id:
        raise HTTPException(404, "Không tìm thấy bộ bài")
    return d


@router.put("/decks/{deck_id}")
def update_deck(deck_id: int, body: DeckBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _own_deck(db, user, deck_id)
    ok, msg = validate_deck(body.cards, set(user_unlocked(user)))
    if not ok:
        raise HTTPException(400, msg)
    d.name, d.cards = body.name, list(body.cards)
    if body.activate:
        _activate(db, user, d)
    db.add(Event(user_id=user.id, type="deck_saved", data={"cards": body.cards}))
    db.commit()
    return _deck_out(d)


@router.post("/decks/{deck_id}/activate")
def activate_deck(deck_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _own_deck(db, user, deck_id)
    _activate(db, user, d)
    db.commit()
    return _deck_out(d)


@router.delete("/decks/{deck_id}")
def delete_deck(deck_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _own_deck(db, user, deck_id)
    if d.is_active:
        raise HTTPException(400, "Không thể xoá bộ bài đang dùng")
    db.delete(d)
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ Matches
class MatchBody(BaseModel):
    difficulty: str
    seed: int = Field(ge=0, le=2_000_000_000)
    player_deck: list[str]
    actions: list[dict]
    surrender: bool = False
    duration_sec: int = 0


@router.post("/matches")
def submit_match(body: MatchBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Server KHÔNG tin kết quả từ client: chạy lại engine từ seed + hành động để xác minh."""
    if body.difficulty not in ("easy", "normal", "hard"):
        raise HTTPException(400, "Độ khó không hợp lệ")
    ok, msg = validate_deck(body.player_deck, set(user_unlocked(user)))
    if not ok:
        raise HTTPException(400, msg)
    if len(body.actions) > MAX_ACTIONS:
        raise HTTPException(400, "Quá nhiều hành động")
    deck_ai = ai_deck(body.difficulty, body.seed)
    try:
        g = replay(body.seed, body.player_deck, deck_ai, body.actions, names=(user.username, "AI"))
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(400, f"Replay không hợp lệ: {e}")
    if not g.over and not body.surrender:
        raise HTTPException(400, "Trận đấu chưa kết thúc")
    winner = g.winner if g.over else 1
    s = g.summary(0)
    xp, pts = match_rewards(body.difficulty, winner, s["insight"], body.surrender and not g.over)
    old_level = level_of(user.xp)
    old_unlocked = set(user_unlocked(user))

    m = Match(user_id=user.id, difficulty=body.difficulty, seed=body.seed, player_deck=body.player_deck,
              ai_deck=deck_ai, actions=body.actions, winner=winner, surrender=body.surrender and not g.over,
              turns=g.turn, accuracy=s["accuracy"], insight=s["insight"], xp_gain=xp, points_gain=pts,
              duration_sec=max(0, min(body.duration_sec, 7200)),
              summary={"counts": s["counts"], "decisions": g.decisions, "solved": s["solved"],
                       "hp": s["hp"], "enemy_hp": s["enemy_hp"]})
    db.add(m)
    user.xp += xp
    user.points += pts
    if winner == 0:
        user.wins += 1
    else:
        user.losses += 1
    user.acc_sum += s["accuracy"]
    db.merge(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Trận đấu với seed này đã được ghi nhận")
    new_unlocked = sorted(set(user_unlocked(user)) - old_unlocked)
    return {"match_id": m.id, "winner": winner, "summary": s, "xp_gain": xp, "points_gain": pts,
            "level_up": level_of(user.xp) > old_level, "level": level_of(user.xp),
            "new_unlocks": new_unlocked, "user": user_public(user, _active_deck(db, user))}


def _match_out(m, username=None, full=False):
    out = {"id": m.id, "difficulty": m.difficulty, "winner": m.winner, "turns": m.turns,
           "accuracy": m.accuracy, "insight": m.insight, "xp_gain": m.xp_gain,
           "points_gain": m.points_gain, "surrender": m.surrender,
           "created_at": m.created_at.isoformat() if m.created_at else None}
    if username:
        out["username"] = username
    if full:
        out.update({"seed": m.seed, "player_deck": m.player_deck, "ai_deck": m.ai_deck,
                    "actions": m.actions, "summary": m.summary})
    return out


@router.get("/matches/mine")
def my_matches(limit: int = 30, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ms = db.scalars(select(Match).where(Match.user_id == user.id)
                    .order_by(Match.id.desc()).limit(min(limit, 100))).all()
    return [_match_out(m) for m in ms]


@router.get("/matches/{match_id}")
def get_match(match_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = db.get(Match, match_id)
    if not m:
        raise HTTPException(404, "Không tìm thấy trận đấu")
    owner = db.get(User, m.user_id)
    return _match_out(m, owner.username if owner else "?", full=True)


# ------------------------------------------------------------------ Puzzles & tutorials
class PuzzleBody(BaseModel):
    actions: list[dict]


@router.post("/puzzles/{pid}/complete")
def complete_puzzle(pid: str, body: PuzzleBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    pz = PUZZLE_BY_ID.get(pid)
    if not pz:
        raise HTTPException(404, "Không có thử thách này")
    try:
        g = replay(0, [], [], body.actions[:50], puzzle=pz)
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(400, f"Lời giải không hợp lệ: {e}")
    if not (g.over and g.winner == 0):
        raise HTTPException(400, "Lời giải chưa hạ được đối thủ")
    done = list(user.puzzles_done or [])
    first = pid not in done
    old = set(user_unlocked(user))
    if first:
        done.append(pid)
        user.puzzles_done = done
        user.xp += PUZZLE_XP
    db.merge(user)
    db.add(Event(user_id=user.id, type="puzzle_complete", data={"puzzle": pid, "first": first}))
    db.commit()
    return {"first_time": first, "xp_gain": PUZZLE_XP if first else 0,
            "new_unlocks": sorted(set(user_unlocked(user)) - old),
            "user": user_public(user, _active_deck(db, user))}


@router.post("/tutorials/{tid}/complete")
def complete_tutorial(tid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if tid not in TUTORIAL_BY_ID:
        raise HTTPException(404, "Không có bài hướng dẫn này")
    done = list(user.tutorials_done or [])
    first = tid not in done
    if first:
        done.append(tid)
        user.tutorials_done = done
        user.xp += TUTORIAL_XP
    db.merge(user)
    db.add(Event(user_id=user.id, type="tutorial_complete", data={"tutorial": tid}))
    db.commit()
    return {"first_time": first, "user": user_public(user, _active_deck(db, user))}


# ------------------------------------------------------------------ Leaderboard & analytics
@router.get("/leaderboard")
def leaderboard(limit: int = 20, db: Session = Depends(get_db)):
    users = db.scalars(select(User).where(User.is_active.is_(True), User.role == "player")
                       .order_by(User.points.desc(), User.wins.desc(), User.id).limit(min(limit, 100))).all()
    out = []
    for rank, u in enumerate(users, 1):
        played = u.wins + u.losses
        out.append({"rank": rank, "username": u.username, "level": level_of(u.xp), "points": u.points,
                    "wins": u.wins, "losses": u.losses,
                    "accuracy": round(u.acc_sum / played) if played else 0})
    return out


class EventBody(BaseModel):
    type: str = Field(min_length=1, max_length=40)
    data: dict = {}


@router.post("/events")
def log_event(body: EventBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.add(Event(user_id=user.id, type=body.type, data=body.data))
    db.commit()
    return {"ok": True}


def card_and_challenge_stats(db):
    """Thống kê cân bằng: lượt chơi theo đánh giá + tỉ lệ thắng khi thẻ có trong bộ bài."""
    plays = Counter()
    rating = {}
    ch_solved = Counter()
    ch_seen = Counter()
    in_deck = Counter()
    in_deck_win = Counter()
    for m in db.scalars(select(Match).order_by(Match.id.desc()).limit(2000)).all():
        for cid in set(m.player_deck):
            in_deck[cid] += 1
            in_deck_win[cid] += m.winner == 0
        for d in (m.summary or {}).get("decisions", []):
            if d.get("who") != 0:
                continue
            plays[d["card"]] += 1
            rating.setdefault(d["card"], Counter())[d["rating"]] += 1
            ch_seen[d["challenge"]] += 1
            if d["rating"] in ("optimal", "acceptable"):
                ch_solved[d["challenge"]] += 1
    cards = []
    for cid, c in CARDS.items():
        r = rating.get(cid, Counter())
        cards.append({"id": cid, "name": c["name"], "decisions": plays[cid], "optimal": r["optimal"],
                      "acceptable": r["acceptable"], "trap": r["trap"], "missed": r["missed"],
                      "in_decks": in_deck[cid],
                      "win_rate": round(100 * in_deck_win[cid] / in_deck[cid]) if in_deck[cid] else None})
    challenges = [{"id": k, "title": v["title"], "attempts": ch_seen[k], "solved": ch_solved[k]}
                  for k, v in CHALLENGES.items()]
    return cards, challenges
