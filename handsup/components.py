from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union, Literal
from discord.ext.commands import Context
from discord import (
    ApplicationContext,
    Embed,
    Colour
)
from discord.utils import get

import asyncio

from .errors import *
from common.api import get_guild_info, MY_ID, post_guild_info

ContextLike = Union[ApplicationContext, Context]

if TYPE_CHECKING:
    from discord import (
        Member,
        Guild,
        Role,
        Message,
        WebhookMessage,
        TextChannel
    )
    MessageLike = Union[Message, WebhookMessage]


def verify(message: MessageLike) -> bool:
    try:
        if (
            message.author.id == MY_ID
            and '6v6 War List' in message.embeds[0].title
        ):
            try:
                return message.embeds[0].author.name != 'アーカイブ'
            except:
                return True
    except:
        return False


async def get_lineup(channel: TextChannel) -> Optional[MessageLike]:

    async for message in channel.history(limit=20, oldest_first=False):

        if verify(message):
            return message

    return None


async def set_hours(
    guild: Guild,
    hours: list[Union[str, int]],
    members: list[Member]
    ) -> None:
    roles: list[Role] = []

    for hour in hours:
        role: Optional[Role] = get(guild.roles, name=str(hour))

        if role is None:
            role = await guild.create_role(name=str(hour), mentionable=True)

        roles.append(role)

    await asyncio.gather(*[asyncio.create_task(member.add_roles(*roles)) for member in members])


async def drop_hours(
    guild: Guild,
    hours: list[Union[str, int]],
    members: list[Member]
    ) -> None:
    roles: list[Role] = []

    for hour in hours:
        role: Optional[Role] = get(guild.roles, name=str(hour))

        if role is None:
            continue

        roles.append(role)

    await asyncio.gather(*[asyncio.create_task(member.remove_roles(*roles)) for member in members])


async def clear_hours(
    guild: Guild,
    hours: list[Union[str, int]],
) -> None:
    for hour in hours:
        role: Optional[Role] = get(guild.roles, name=str(hour))

        if role is not None:
            await role.delete()
    return


def create_lineup(recruit: dict[str, list[int]]) -> Embed:

    if not recruit:
        raise NotGathering

    if len(recruit.keys()) >= 26:
        raise HourNotAddable

    e = Embed(
        title = '**6v6 War List**',
        color = Colour.blue()
    )

    for hour in sorted(int(h) for h in recruit.keys()):
        is_empty: bool = len(recruit[str(hour)]['c'] + recruit[str(hour)]['t']) == 0

        if is_empty:
            e.add_field(name=f'{hour}@6', value='> なし', inline=False)
            continue
        else:
            c = [f'<@{id}>' for id in recruit[str(hour)]['c']]
            t = [f'<@{id}>' for id in recruit[str(hour)]['t']]
            e.add_field(
                name = f'{hour}@{6-len(c)}' + (f'({len(t)})' if t else ''),
                value = f'> {",".join(c)}' + (f'({",".join(t)})' if t else ''),
                inline = False
            )
    return e


async def participate(
    ctx: ContextLike,
    action: Literal['c', 't'],
    members: list[Member],
    hours: list[Union[int, str]]
) -> dict[str, Union[str, Embed]]:
    payload: dict[str, Union[str, Embed]] = {}
    x, y = 'c', 't'

    if action == 't':
        x, y = 't', 'c'

    info = get_guild_info(ctx.guild.id)
    recruit = info['recruit'].copy()
    ids: list[int] = [m.id for m in members]
    filled_hours:list[str] = []

    for hour in sorted(map(str, hours), key=lambda x: int(x)):
        recruit_hour = recruit.get(hour)

        if recruit_hour is None:
            recruit[hour] = {x: ids.copy(), y: []}
        else:
            recruit_hour[x] = list(set(recruit_hour[x])|set(ids))
            recruit_hour[y] = list(set(recruit_hour[y])-set(ids))

        if len(recruit[hour]['c']) >=6 and action=='c':
            filled_hours.append(hour)

    info['recruit'] = recruit.copy()
    payload['embed'] = create_lineup(recruit)
    await set_hours(ctx.guild, hours, members)
    post_guild_info(ctx.guild.id, info)

    if filled_hours:
        call_ids: set[int] = set([])

        for hour in filled_hours:
            call_ids = call_ids | set(recruit[hour]['c'])

        members = [ctx.guild.get_member(id) for id in list(call_ids) if ctx.guild.get_member(id) is not None]
        payload['call'] = f"**{', '.join(filled_hours)}**{', '.join([member.mention for member in members])}"

    msg = await get_lineup(ctx.channel)

    if msg is not None:
        await msg.delete()

    return payload


async def drop(
    ctx: ContextLike,
    members: list[Member],
    hours: list[Union[int, str]]
) -> Embed:
    guild = ctx.guild
    info = get_guild_info(guild.id)
    recruit = info['recruit']
    recruit_hours = recruit.keys()
    member_ids = [m.id for m in members]

    for hour in hours:

        if str(hour) not in recruit_hours:
            continue

        recruit[str(hour)]['c'] = [i for i in recruit[str(hour)]['c'] if i not in member_ids]
        recruit[str(hour)]['t'] = [i for i in recruit[str(hour)]['c'] if i not in member_ids]

    post_guild_info(guild.id, info)
    await drop_hours(guild, hours, members)
    msg = await get_lineup(ctx.channel)

    if msg is not None:
        await msg.delete()

    return create_lineup(recruit)



async def clear(ctx: ContextLike) -> None:
    guild = ctx.guild
    info = get_guild_info(guild.id)
    await clear_hours(guild, info['recruit'].keys())
    info['recruit'] = {}
    post_guild_info(guild.id, info)
    msg = await get_lineup(ctx.channel)

    if msg is not None:
        e = msg.embeds[0].copy()
        e.set_author(name='アーカイブ')
        e.color = Colour.yellow()
        await msg.edit(embed=e)

    return


async def now(ctx: ContextLike) -> None:
    guild = ctx.guild
    e = create_lineup(get_guild_info(guild.id)['recruit'])
    msg = await get_lineup(ctx.channel)

    if isinstance(ctx, ApplicationContext):
        await ctx.respond(embed = e)
    elif isinstance(ctx, Context):
        await ctx.send(embed=e)

    if msg is not None:
        await msg.delete()

    return


async def out(ctx: ContextLike, hours: Union[int, str]) -> None:
    info = get_guild_info(ctx.guild.id)
    recruit = info['recruit']

    for hour in hours:

        try:
            recruit.pop(str(hour))
        except KeyError:
            pass

    await clear_hours(ctx.guild, hours)
    post_guild_info(ctx.guild.id, info)
    return