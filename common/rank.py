from __future__ import annotations
from typing import Optional
import re

_RE = re.compile(r'([0-9]|\-|\ )+')


class Rank:

    __slots__ = (
        'data'
    )

    def __init__(self,data: list[int] = []):
        self.data = sorted(data)

    def __str__(self):
        return ",".join([str(r) for r in self.data])

    @classmethod
    def from_string(cls, text: str) -> Optional[Rank]:
        m = _RE.search(text)

        if m is None:
            return None

        rs = m.group().replace(' ','')
        data: list[int] = []
        prev: Optional[int] = None
        next_list: list[int] = []
        flag: bool = False

        while rs:
            next_list = []

            if rs.startswith('-'):
                flag = True
                rs = rs[1:]

            if data:
                prev = data[-1]
            else:
                prev = 0

            if rs.startswith('10'):
                next_list = [10]
                rs = rs[2:]
            elif rs.startswith('110'):
                next_list = [1,10]
                rs = rs[3:]
            elif rs.startswith('1112'):
                next_list = [11, 12]
                rs = rs[4:]
            elif rs.startswith('111'):
                next_list = [1, 11]
                rs = rs[3:]
            elif rs.startswith('112'):
                next_list = [1, 12]
                rs = rs[3:]
            elif rs.startswith('11'):
                next_list = [11]
                rs = rs[2:]
            elif rs.startswith('12'):
                if data:
                    next_list = [12]
                else:
                    next_list = [1, 2]
                rs = rs[2:]
            elif rs:
                next_list = [int(rs[0])]
                rs = rs[1:]

            if flag:
                if not next_list:
                    next_list = [12]
                next = next_list[0]
                while next - prev > 1:
                    data.append(prev+1)
                    prev += 1
                flag = False

            data += next_list

        ranks = [r for r in sorted(set(data)) if 0 < r < 13]

        if len(ranks) > 6:
            return None

        for k in range(12,0,-1):
            if len(ranks) >= 6:
                return cls(data = ranks)
            if k not in ranks:
                ranks.append(k)


    @staticmethod
    def verify(text: str) -> bool:
        return text.startswith(tuple(['-']+[str(i) for i in range(0,10)]))