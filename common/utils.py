from typing import Optional, Any
from datetime import datetime
from zoneinfo import ZoneInfo
import re

_RE = re.compile(r'-?[0-9]+')

def get(l: list[Any], i: int) -> Optional[Any]:
    if len(l) <= i: return None
    return l[i]


def get_integers(text: str) -> list[int]:
    return list(map(int,_RE.findall(text)))


def get_dt(txt: str) -> datetime:
    """change txt into datetime (JST)
    Args:
        txt (str): String with numbers
    Returns:
        datetime: JST datetime (aware)
    """
    now = datetime.now(ZoneInfo('Asia/Tokyo'))
    nums = list(map(int,re.findall(r'[0-9]+',txt)))[:3][::-1]
    return datetime(
        year= get(nums,2) or now.year,
        month= get(nums,1) or now.month,
        day= get(nums,0) or now.day,
        tzinfo=ZoneInfo('Asia/Tokyo')
    )

def get_fc(txt: str) -> Optional[str]:
    d_txt = re.sub(r'\D','',txt)

    if len(d_txt) != 12:
        return None

    return f'{d_txt[:4]}-{d_txt[4:8]}-{d_txt[8:]}'


def get_discord_id(txt: str) -> Optional[int]:
    d_txt = re.sub(r'\D','',txt)

    if len(d_txt) >= 17 and len(d_txt) <=19:
        return int(d_txt)

    return None


def maybe_param(txt: str) -> tuple[Optional[str], Optional[int], Optional[str]]:
    d_id = get_discord_id(txt)
    fc = get_fc(txt)

    if d_id is not None:
        return None, d_id, None

    if fc is not None:
        return None, None, fc

    return txt, None, None