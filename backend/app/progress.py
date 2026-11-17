"""Logic tiến trình (progression) dùng chung: cấp độ, mở khoá thẻ, phần thưởng."""
from engine import unlocked_cards, STARTER_DECK
from engine.ai import DIFFICULTY_POINTS

XP_PER_LEVEL = 100
WIN_XP = {"easy": 30, "normal": 50, "hard": 80}
PUZZLE_XP = 40
TUTORIAL_XP = 15


def level_of(xp: int) -> int:
    return 1 + xp // XP_PER_LEVEL


def user_unlocked(user):
    return unlocked_cards(level_of(user.xp), set(user.puzzles_done or []))


def match_rewards(difficulty, winner, insight, surrender):
    if surrender:
        return 0, 0
    if winner == 0:
        return WIN_XP[difficulty] + 5 * insight, DIFFICULTY_POINTS[difficulty] + insight
    if winner == -1:
        return 15 + 2 * insight, 3
    return 10 + 2 * insight, 0


def user_public(user, active_deck=None):
    lvl = level_of(user.xp)
    played = user.wins + user.losses
    return {
        "id": user.id, "username": user.username, "role": user.role, "is_active": user.is_active,
        "xp": user.xp, "level": lvl, "xp_in_level": user.xp % XP_PER_LEVEL, "xp_per_level": XP_PER_LEVEL,
        "points": user.points, "wins": user.wins, "losses": user.losses,
        "accuracy": round(user.acc_sum / played) if played else 0,
        "puzzles_done": user.puzzles_done or [], "tutorials_done": user.tutorials_done or [],
        "unlocked": user_unlocked(user),
        "active_deck": active_deck.cards if active_deck else list(STARTER_DECK),
        "active_deck_id": active_deck.id if active_deck else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }
