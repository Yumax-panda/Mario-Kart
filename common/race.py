from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from .point import Point

if TYPE_CHECKING:
    from common import Rank, Track


class Race:

    __slots__ = (
        'rank',
        'track'
    )

    def __init__(
        self,
        rank: Rank,
        track: Optional[Track] = None
    ):
        self.rank: Rank = rank
        self.track: Optional[Track] = track


    @property
    def point(self) -> Point:
        return Point.calculate(self.rank)