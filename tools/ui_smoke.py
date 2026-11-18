"""Chạy game headless, mô phỏng thao tác người dùng qua mọi màn hình và chụp ảnh màn hình."""
import os, sys, asyncio
os.environ["SDL_VIDEODRIVER"] = "dummy"
GAME = os.path.join(os.path.dirname(__file__), "..", "game")
sys.path.insert(0, GAME)
os.chdir(GAME)
import pygame
pygame.init()
import ui
from scenes_base import App
from scenes_menu import BootScene, LoginScene, MenuScene, PlaySetupScene, LeaderboardScene, HistoryScene, open_replay
from scene_battle import BattleScene, ResultScene
from scene_deck import DeckScene
from scenes_learn import PuzzleListScene, TutorialScene, start_puzzle
from engine import choose_action, PUZZLES
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/shots"
os.makedirs(OUT, exist_ok=True)

async def pump(app, sec=0.3, until=None):
    t = 0
    while t < sec or (until and not until()):
        for e in pygame.event.get(): pass
        app.scene.update(1/30); app.scene.draw(app.screen); app.draw_toasts(app.screen, 1/30)
        await asyncio.sleep(0.01); t += 1/30
        if t > 30: raise TimeoutError(type(app.scene).__name__)

def shot(app, name):
    app.scene.draw(app.screen); app.draw_toasts(app.screen, 0)
    pygame.image.save(app.screen, os.path.join(OUT, name + ".png"))

def click(app, pos):
    app.scene.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0,0), buttons=(0,0,0)))
    app.scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))

async def main():
    screen = pygame.display.set_mode((ui.W, ui.H))
    app = App(screen)
    app.net.set_token("")
    app.go(BootScene(app)); await pump(app)
    assert isinstance(app.scene, LoginScene)
    s = app.scene; import random; s.user.value = "sv" + str(random.randint(1000, 9999)); s.pw.value = "matkhau123"
    shot(app, "01_login")
    s.submit("register"); await pump(app, until=lambda: isinstance(app.scene, MenuScene))
    await pump(app, 0.5); shot(app, "02_menu")
    app.go(PlaySetupScene(app)); await pump(app); shot(app, "03_setup")
    app.scene.start("easy"); await pump(app, 1.5)
    b = app.scene; assert isinstance(b, BattleScene)
    # người chơi: mô phỏng bằng AI hard, chụp vài khoảnh khắc
    n = 0
    while not b.g.over and n < 400:
        if b.g.current == 0:
            a = choose_action(b.g, "hard")
            if a["t"] == "play":
                r = b.hand_layout(len(b.g.players[0].hand))[a["i"]][0]
                click(app, r.center)
            else:
                b.end_turn()
            n += 1
            if n in (2, 9): await pump(app, 0.4); shot(app, f"04_battle_{n}")
        await pump(app, 0.2)
    await pump(app, until=lambda: isinstance(app.scene, ResultScene))
    await pump(app, 0.5); shot(app, "05_result")
    assert app.scene.server, "match not saved"
    rec = app.scene.rec
    app.go(DeckScene(app)); await pump(app)
    app.scene.add("dfs"); click(app, (300, 300)); await pump(app); shot(app, "06_deck")
    app.go(PuzzleListScene(app)); await pump(app); shot(app, "07_puzzles")
    start_puzzle(app, PUZZLES[0]); await pump(app, 0.3); app.scene.toggle_hint(); await pump(app); shot(app, "08_puzzle")
    b = app.scene
    hand = b.g.players[0].hand
    click(app, b.hand_layout(len(hand))[hand.index("quick_sort")][0].center); await pump(app, 0.3)
    hand = b.g.players[0].hand
    click(app, b.hand_layout(len(hand))[hand.index("binary_search")][0].center); await pump(app, 2.0)
    shot(app, "09_puzzle_win")
    assert b.overlay and b.overlay[0] == "win"
    await pump(app, 1.0)
    assert "p1" in app.user["puzzles_done"], app.user["puzzles_done"]
    app.go(TutorialScene(app)); await pump(app); app.scene.select(2); app.scene.turn(1); await pump(app); shot(app, "10_tutorial")
    app.go(HistoryScene(app)); await pump(app, until=lambda: app.scene.rows is not None); shot(app, "11_history")
    mid = app.scene.rows[0]["id"]
    open_replay(app, mid); await pump(app, until=lambda: isinstance(app.scene, BattleScene))
    for _ in range(6): app.scene.goto(app.scene.step + 1)
    await pump(app, 0.3); shot(app, "12_replay")
    app.go(LeaderboardScene(app)); await pump(app, until=lambda: app.scene.rows is not None); shot(app, "13_leaderboard")
    # offline mode
    app.net.set_token(""); app.user = None
    app.go(MenuScene(app)); await pump(app); shot(app, "14_menu_offline")
    print("UI smoke OK")

asyncio.run(main())
