from typing import TypeVar
from abc import ABC, abstractmethod

T = TypeVar("T")


class KeepoutArea(ABC):
    @abstractmethod
    def check(self, x: T, y: T) -> T:
        """
        立ち入り禁止に入っていたら負を，それ以外では正を出力するように．
        与えられるx,yはスカラ（float），ベクトル（ndarray），行列（ndarray）の可能性がある．
        """
        pass


class CircleKeepoutArea(KeepoutArea):
    def __init__(self, x: float, y: float, radius: float):
        self.x = x
        self.y = y
        self.radius_2 = radius ** 2

    def check(self, x: T, y: T) -> T:
        to_margin_2 = (self.x - x) ** 2 + (self.y - y) ** 2 - self.radius_2
        return to_margin_2
