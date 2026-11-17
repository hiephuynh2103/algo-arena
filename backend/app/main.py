import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "game"))   # dùng chung rule engine với game

from fastapi import FastAPI                          # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles          # noqa: E402
from sqlalchemy import select                        # noqa: E402

from .db import init_db, SessionLocal, User, Deck    # noqa: E402
from .security import hash_password                  # noqa: E402
from .routes_game import router as game_router       # noqa: E402
from .routes_admin import router as admin_router     # noqa: E402
from engine import STARTER_DECK                      # noqa: E402

PORTAL = ROOT / "backend" / "portal"
GAME_BUILD = Path(os.getenv("GAME_BUILD_DIR", ROOT / "game" / "build" / "web"))


def seed_admin():
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)):
            return
        u = User(username=username, password_hash=hash_password(password), role="admin",
                 puzzles_done=[], tutorials_done=[])
        db.add(u)
        db.flush()
        db.add(Deck(user_id=u.id, name="Bộ khởi đầu", cards=list(STARTER_DECK), is_active=True))
        db.commit()


@asynccontextmanager
async def lifespan(app):
    init_db()
    seed_admin()
    yield


app = FastAPI(title="Algo Arena API", version="1.0.0", lifespan=lifespan,
              description="Backend cho game card battle học thuật toán: auth, deck, replay, leaderboard, analytics.")
app.include_router(game_router)
app.include_router(admin_router)


@app.get("/healthz")
def health():
    return {"ok": True, "game_built": (GAME_BUILD / "index.html").exists()}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(PORTAL / "index.html")


@app.get("/admin", include_in_schema=False)
def admin_page():
    return FileResponse(PORTAL / "admin.html")


app.mount("/static", StaticFiles(directory=PORTAL / "static"), name="static")

if (GAME_BUILD / "index.html").exists():
    app.mount("/play", StaticFiles(directory=GAME_BUILD, html=True), name="play")
else:
    @app.get("/play", include_in_schema=False)
    @app.get("/play/", include_in_schema=False)
    def play_missing():
        return HTMLResponse("<h2>Game chưa được build.</h2><p>Chạy: <code>python -m pygbag --build game</code></p>",
                            status_code=503)
