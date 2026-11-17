from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from .db import get_db, User, Match, Event, Deck, now
from .security import require_admin, hash_password
from .progress import user_public
from .routes_game import card_and_challenge_stats

router = APIRouter(prefix="/api/admin")


@router.get("/users")
def list_users(q: str = "", admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = select(User).order_by(User.id)
    if q:
        stmt = stmt.where(User.username.ilike(f"%{q}%"))
    return [user_public(u) for u in db.scalars(stmt.limit(500)).all()]


class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    new_password: str | None = Field(default=None, min_length=6, max_length=128)


@router.patch("/users/{uid}")
def patch_user(uid: int, body: UserPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Không tìm thấy người dùng")
    if u.id == admin.id and (body.role == "player" or body.is_active is False):
        raise HTTPException(400, "Không thể tự hạ quyền hoặc tự khoá tài khoản của mình")
    if body.role is not None:
        if body.role not in ("player", "admin"):
            raise HTTPException(400, "Vai trò không hợp lệ")
        u.role = body.role
    if body.is_active is not None:
        u.is_active = body.is_active
    if body.new_password:
        u.password_hash = hash_password(body.new_password)
    db.add(Event(user_id=admin.id, type="admin_update_user",
                 data={"target": uid, "role": body.role, "is_active": body.is_active,
                       "reset_password": bool(body.new_password)}))
    db.commit()
    return user_public(u)


@router.delete("/users/{uid}")
def delete_user(uid: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Không tìm thấy người dùng")
    if u.id == admin.id:
        raise HTTPException(400, "Không thể tự xoá tài khoản của mình")
    for model in (Match, Deck):
        for row in db.scalars(select(model).where(model.user_id == uid)).all():
            db.delete(row)
    db.delete(u)
    db.add(Event(user_id=admin.id, type="admin_delete_user", data={"target": uid}))
    db.commit()
    return {"ok": True}


@router.get("/stats")
def stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    total_users = db.scalar(select(func.count(User.id)))
    total_matches = db.scalar(select(func.count(Match.id)))
    since = now() - timedelta(days=7)
    active_7d = db.scalar(select(func.count(func.distinct(Event.user_id))).where(Event.created_at >= since))

    by_diff = {}
    for diff in ("easy", "normal", "hard"):
        n = db.scalar(select(func.count(Match.id)).where(Match.difficulty == diff))
        w = db.scalar(select(func.count(Match.id)).where(Match.difficulty == diff, Match.winner == 0))
        acc = db.scalar(select(func.avg(Match.accuracy)).where(Match.difficulty == diff))
        by_diff[diff] = {"matches": n, "win_rate": round(100 * w / n) if n else None,
                         "avg_accuracy": round(acc) if acc is not None else None}

    days = []
    start = (now() - timedelta(days=13)).date()
    recent = db.scalars(select(Match).where(Match.created_at >= now() - timedelta(days=14))).all()
    per_day = Counter(m.created_at.date().isoformat() for m in recent if m.created_at)
    for i in range(14):
        d = (start + timedelta(days=i)).isoformat()
        days.append({"date": d, "matches": per_day.get(d, 0)})

    events = dict(db.execute(select(Event.type, func.count(Event.id)).group_by(Event.type)).all())
    avg_turns = db.scalar(select(func.avg(Match.turns)))
    avg_dur = db.scalar(select(func.avg(Match.duration_sec)))
    cards, challenges = card_and_challenge_stats(db)
    return {"total_users": total_users, "total_matches": total_matches, "active_7d": active_7d,
            "avg_turns": round(avg_turns, 1) if avg_turns else 0,
            "avg_duration_sec": round(avg_dur) if avg_dur else 0,
            "by_difficulty": by_diff, "matches_per_day": days, "events": events,
            "cards": cards, "challenges": challenges}


@router.get("/matches")
def recent_matches(limit: int = 50, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Match, User.username).join(User, User.id == Match.user_id)
                      .order_by(Match.id.desc()).limit(min(limit, 200))).all()
    return [{"id": m.id, "username": name, "difficulty": m.difficulty, "winner": m.winner,
             "turns": m.turns, "accuracy": m.accuracy, "points_gain": m.points_gain,
             "created_at": m.created_at.isoformat() if m.created_at else None} for m, name in rows]
