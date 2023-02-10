from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .rank import Rank


class Point:

    __slots__ = (
        'ally',
        'enemy'
    )

    def __init__(self, ally: int, enemy: int):
        self.ally = ally
        self.enemy = enemy

    def __add__(self, other: Point) -> Point:
        return Point(self.ally+other.ally, self.enemy+other.enemy)

    def __str__(self):
        return f'{self.ally} : {self.enemy}'

    def __bool__(self):
        return not (self.ally == 0 and self.enemy == 0)

    def to_string(self) -> str:
        sign = '+' if self.ally - self.enemy >= 0 else ''
        return f'{self.ally} : {self.enemy}({sign}{self.ally-self.enemy})'

    @classmethod
    def calculate(cls, rank: Rank) -> Point:
        p = [15,12,10,9,8,7,6,5,4,3,2,1]
        ally = sum([p[i-1] for i in rank.data])
        return cls(ally, 82-ally)