from pygame.sprite import Sprite
from pygame.color import Color
from pygame.font import Font, SysFont, get_fonts
from pygame.surface import Surface
from pygame.draw import rect as draw_rect
from pygame import Rect


class DictViewer(Sprite):
    def __init__(
            self,
            width: int,
            keys: list[str],
            key_width: int = 100,
            height_per_item: int = 25,
            background_color: Color = "darkslategrey",
            key_color: Color = "cyan",
            value_color: Color = "white",
            padding: int = 10,
    ):
        self.keys = keys
        self.key_width = key_width
        self.height_per_item = height_per_item
        self.background_color = background_color
        self.key_color = key_color
        self.value_color = value_color
        self.padding = padding

        self.font = SysFont("couriernew", size=18, bold=True)
        height = height_per_item * len(keys) + padding * 2
        self.surface = Surface((width, height))

        # keysをレンダリング
        self.keys_surface = Surface((key_width, height))
        self.keys_surface.fill(background_color)
        for i, key in enumerate(keys):
            self.keys_surface.blit(
                self.font.render(key, True, key_color),
                (0, height_per_item * i)
            )

    def set_values(self, values: list[str]):
        self.surface.fill(self.background_color)
        for i, value in enumerate(values):
            self.surface.blit(
                self.font.render(value, False, self.value_color),
                (self.key_width + self.padding, self.height_per_item * i + self.padding)
            )
        self.surface.blit(self.keys_surface, (self.padding, self.padding))

    def update(self, *args, **kwargs):
        pass


if __name__ == "__main__":
    from pygame import *
    from math import sin, cos

    init()
    screen = display.set_mode((500, 500))

    view = DictViewer(width=300, keys=["x", "sin x", "cos x", "Feeling"])

    x = -1.0
    while x <= 1.0:
        feeling = "Happy" if sin(10 * x) >= 0 else "Bad"
        view.set_values([
            f"{x:.03f}",
            f"{sin(x):.03f}",
            f"{cos(x):.03f}",
            feeling
        ])

        screen.fill("chartreuse")
        screen.blit(view.surface, (100, 100))
        display.flip()

        x += 0.01
        time.wait(10)

    quit()
