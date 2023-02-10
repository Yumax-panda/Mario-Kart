from __future__ import annotations
from typing import TYPE_CHECKING, Any, Union, Optional

from discord.embeds import Embed, EmptyEmbed
from discord.utils import get
from math import floor
from .api import RANK_DATA, get_rank, get_players, get_team_name

if TYPE_CHECKING:
    from discord.embeds import MaybeEmpty
    from discord import Guild, Role


class LoungeEmbed(Embed):

    def __init__(
        self,
        mmr: Union[int, float],
        title: MaybeEmpty[Any] = EmptyEmbed,
        description: MaybeEmpty[Any] = EmptyEmbed
    ) -> None:
        self.rank: str = get_rank(mmr)
        self.mmr: Union[int, float] = mmr
        super().__init__(
            title = title,
            description = description,
            color = RANK_DATA[self.rank.split(' ')[0]]['color']
        )
        self.set_thumbnail(url = RANK_DATA[self.rank.split(' ')[0]]['url'])



async def mkmg(
    guild: Guild,
    time: Union[str, int, None] = None,
    host: bool = False
    ) -> str:
    header = f'{ f"{time} " if time is not None else ""}' + '交流戦お相手募集します\n'
    header += f'こちら{get_team_name(guild.id) or guild.name}\n'
    body = ('主催持てます\n' if host else '主催持っていただきたいです\n') + 'Sorry, Japanese clan only\n#mkmg'
    role: Optional[Role] = None

    if time is not None:
        role = get(guild.roles, name = str(time))

    if role is None:
        return header + body

    players: list[dict] = await get_players(
        discord_ids = [m.id for m in role.members],
        remove_None = True
    )
    count = 0
    total_mmr = 0

    for player in players:

        try:
            total_mmr += player['mmr']
            count += 1
        except KeyError:
            pass

    if  count == 0:
        return header + body

    header += f'平均MMR {floor(total_mmr/(count*500))*500}程度\n'
    return header + body
