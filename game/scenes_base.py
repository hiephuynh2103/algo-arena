import asyncio
import pygame

import ui
from ui import W, H, text, panel, Button, BG, MUTED, ACCENT, TEXT, LINE, PANEL2
from net import ApiError
from engine import unlocked_cards, STARTER_DECK


class App:
    def __init__(self, screen):
        from net import Net
        self.screen = screen
        self.net = Net()
        self.user = None            # dict từ /api/me; None khi chơi offline
        self.offline = False
        self.scene = None
        self.running = True
        self.toasts = []
        self.local_matches = []     # trận đấu khi chơi offline
        self.local_puzzles = set()
        self.local_deck = list(STARTER_DECK)
        self._tasks = set()

    # ------------------------------------------------------------ dữ liệu người chơi
    @property
    def unlocked(self):
        if self.user:
            return set(self.user["unlocked"])
        return set(unlocked_cards(1, self.local_puzzles))

    @property
    def deck(self):
        if self.user:
            return list(self.user["active_deck"])
        return list(self.local_deck)

    @property
    def name(self):
        return self.user["username"] if self.user else "Khách"

    # ------------------------------------------------------------ điều hướng & async
    def go(self, scene):
        self.scene = scene
        self.fade = 1.0
        scene.enter()

    def draw_fade(self, surf, dt):
        f = getattr(self, "fade", 0)
        if f > 0:
            s = pygame.Surface((W, H))
            s.fill((10, 5, 2))
            s.set_alpha(int(255 * f))
            surf.blit(s, (0, 0))
            self.fade = max(0.0, f - dt * 4)

    def spawn(self, coro, ok=None, err=None):
        async def run():
            try:
                res = await coro
            except ApiError as e:
                if err:
                    err(e)
                else:
                    self.toast(str(e), ui.RED)
            except Exception as e:  # lỗi bất ngờ: báo nhưng không làm sập game
                if err:
                    err(ApiError(0, str(e)))
                else:
                    self.toast(f"Lỗi: {e}", ui.RED)
            else:
                if ok:
                    ok(res)
        t = asyncio.ensure_future(run())
        self._tasks.add(t)
        t.add_done_callback(self._tasks.discard)

    def toast(self, msg, color=ACCENT, life=2.8):
        self.toasts.append([msg, color, life])
        self.toasts = self.toasts[-3:]

    def draw_toasts(self, surf, dt):
        y = H - 60
        for t in list(self.toasts):
            t[2] -= dt
            if t[2] <= 0:
                self.toasts.remove(t)
                continue
            w = ui.text_size(t[0], 15, 2)[0] + 44
            r = pygame.Rect(W - w - 20, y, w, 42)
            panel(surf, r, (43, 25, 13), accent=t[1], radius=12, width=2)
            pygame.draw.circle(surf, t[1], (r.x + 18, r.centery), 5)
            text(surf, t[0], (r.x + 30, r.centery - 11), 15, TEXT, 2)
            y -= 52


class Scene:
    title = ""

    def __init__(self, app):
        self.app = app
        self.buttons = []
        self.t = 0

    def enter(self):
        pass

    def handle(self, e):
        for b in list(self.buttons):
            if b.handle(e):
                return True
        return False

    def update(self, dt):
        self.t += dt

    def draw_bg(self, surf):
        ui.draw_background(surf, self.t)

    def draw_header(self, surf, back=True):
        if self.title:
            text(surf, self.title, (W // 2, 36), 28, TEXT, 3, center=True, shadow=True)
            tw = ui.text_size(self.title, 28, 3)[0]
            pygame.draw.line(surf, ACCENT, (W // 2 - tw // 2, 58), (W // 2 + tw // 2, 58), 2)

    def draw(self, surf):
        self.draw_bg(surf)
        self.draw_header(surf)
        for b in self.buttons:
            b.draw(surf)


def back_button(app, target_factory, label="Menu"):
    return Button((20, 16, 124, 40), label, lambda: app.go(target_factory()), kind="ghost", size=15, icon_name="back")
