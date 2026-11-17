"""Algo Arena – Game Card Battle học Thuật toán.

Chạy desktop :  python main.py            (cần backend ở http://127.0.0.1:8000 hoặc chơi offline)
Build web    :  python -m pygbag --build game   (tạo game/build/web để FastAPI phục vụ ở /play)
"""
import asyncio
import sys

import pygame

pygame.init()

import ui                                  # noqa: E402
from scenes_base import App                # noqa: E402
from scenes_menu import BootScene          # noqa: E402


async def main():
    screen = pygame.display.set_mode((ui.W, ui.H))
    pygame.display.set_caption("Algo Arena – Card Battle học Thuật toán")
    clock = pygame.time.Clock()
    app = App(screen)
    app.go(BootScene(app))
    while app.running:
        dt = min(clock.tick(60) / 1000.0, 0.1)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                app.running = False
            else:
                app.scene.handle(e)
        app.scene.update(dt)
        app.scene.draw(screen)
        app.draw_fade(screen, dt)
        app.draw_toasts(screen, dt)
        pygame.display.flip()
        await asyncio.sleep(0)       # bắt buộc với pygbag: nhường quyền cho trình duyệt
    pygame.quit()
    if sys.platform != "emscripten":
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
