from pygame.sprite import Sprite
from pygame.color import Color
from pygame.surface import Surface
from pygame.draw import rect as draw_rect
from pygame import Rect


class IntervenableScalarView(Sprite):
    def __init__(
            self,
            width: int,
            min_value: float,
            max_value: float,
            value_width: int = 20,
            height: int = 20,
            nominal_background_color: Color = "darkslategrey",
            intervening_background_color: Color = "brown4",
            nominal_value_color: Color = "white",
            intervening_value_color: Color = "deeppink"
    ):
        self.min_value = min_value
        self.max_value = max_value
        self.nominal_background_color = nominal_background_color
        self.intervening_background_color = intervening_background_color
        self.nominal_value_color = nominal_value_color
        self.intervning_value_color = intervening_value_color

        self.coef = width / (max_value - min_value)
        self.value_width = value_width
        self.half_value_width = value_width / 2

        self.surface = Surface((width, height))
        self.is_intervning = False

    def calc_value_rect(self, value: float) -> Rect:
        return Rect(
            self.coef * (value - self.min_value) - self.half_value_width,
            0,
            self.value_width,
            self.surface.get_height()
        )

    def set_nominal(self, nominal_value: float):
        self.surface.fill(self.nominal_background_color)
        draw_rect(self.surface, self.nominal_value_color, self.calc_value_rect(nominal_value))

    def set_intervening(self, nominal_value: float, intervening_value: float):
        self.surface.fill(self.intervening_background_color)
        draw_rect(self.surface, self.nominal_value_color, self.calc_value_rect(nominal_value))
        draw_rect(self.surface, self.intervning_value_color, self.calc_value_rect(intervening_value))

    def update(self, *args, **kwargs):
        pass


if __name__ == "__main__":
    from pygame import *
    from math import sin

    init()
    screen = display.set_mode((500, 500))

    nominal_view = IntervenableScalarView(width=200, min_value=-1., max_value=1.)
    intervening_view = IntervenableScalarView(width=300, min_value=-1., max_value=1.)

    x = -2.0
    while x <= 2.0:
        nominal_view.set_nominal(x)
        intervening_view.set_intervening(x, sin(x * 3))

        screen.fill("chartreuse")
        screen.blit(nominal_view.surface, (100, 100))
        screen.blit(intervening_view.surface, (50, 200))
        display.flip()

        x += 0.1
        time.wait(100)

    quit()
