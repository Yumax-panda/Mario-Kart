from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union
from datetime import datetime, timedelta
from io import BytesIO
from discord import (
    Embed,
    Colour,
    Interaction,
    ApplicationContext,
    File
)
from discord.ext.commands import Context
from discord.abc import Messageable
import aiohttp

from common import (
    get_integers,
    Lang,
    Point,
    Race,
    Rank,
    Track,
    BOT_IDS,
    MY_ID
)

from .status import Status
from .errors import *

if TYPE_CHECKING:
    from discord import (
        Message,
        WebhookMessage,
        InteractionMessage,
        Member,
        User
    )
    MessageLike = Union[Message, WebhookMessage, InteractionMessage]
    MemberLike = Union[Member, User]
    ContextLike = Union[ApplicationContext, Context, Messageable]

class MogiMessage:

    __slots__ = (
        'tags',
        'races',
        'members',
        'penalty',
        'repick',
        'message',
        'lang',
        'status',
    )

    def __init__(
        self,
        tags: list[str],
        races: list[Race] = [],
        members: set[MemberLike] = set(),
        penalty: Optional[Point] = None,
        repick: Optional[Point] = None,
        message: Optional[MessageLike] = None,
        lang: Optional[Lang] = None,
        status: Optional[Status] = None
    ) -> None:
        self.tags: list[str] = tags
        self.races: list[Race] = races
        self.members: set[MemberLike] = members
        self.penalty: Point = penalty or Point(0,0)
        self.repick: Point = repick or Point(0,0)
        self.message: Optional[MessageLike] = message
        self.lang: Lang = lang or Lang.EN
        self.status: Status = status or Status.ONGOING

    @property
    def total(self) -> Point:
        al, en = 0, 0
        for race in self.races:
            al += race.point.ally
            en += race.point.enemy
        return Point(al, en) + self.penalty + self.repick


    @property
    def embed(self) -> Embed:
        title = '即時集計 ' if self.lang == Lang.JA else 'Sokuji '
        title += f'6v6\n{self.tags[0]} - {self.tags[1]}'
        e = Embed(
            title = title,
            description = f'`{self.total.to_string()} @{12-len(self.races)}`',
            color = Colour.blurple()
        )

        for i,race in enumerate(self.races):
            txt = f'{i+1} '
            if race.track is not None:
                txt += '- '+ (race.track.nick_ja if self.lang == Lang.JA else race.track.nick_en)
            e.add_field(
                name = txt,
                value = f'`{race.point.to_string()}`|`{race.rank}`',
                inline = False
            )

        if self.penalty:
            e.add_field(name = 'Penalty', value = f'`{self.penalty}`',inline = False)

        if self.repick:
            e.add_field(name = 'Repick', value = f'`{self.repick}`', inline = False)

        if self.members:
            e.add_field(name = 'Members', value = f'> {", ".join([m.mention for m in self.members])}')

        if self.status != Status.ONGOING:
            e.set_author(name = f'{self.status.en if self.lang == Lang.EN else self.status.ja}')

        return e


    @staticmethod
    def verify(message: MessageLike, raise_exceptions: bool = False) -> bool:
        try:
            if (message.embeds[0].title.startswith(('Sokuji','即時集計'))
                and message.author.id in BOT_IDS):
                return True
        except:
            pass
        if raise_exceptions:
            raise InvalidMessage
        return False


    @staticmethod
    def convert(message: MessageLike) -> MogiMessage:
        embed = message.embeds[0].copy()
        lang = Lang.JA if '即時集計' in embed.title else Lang.EN
        tags = embed.title.split('\n', maxsplit=1)[-1].split(' - ')
        races: list[Race] = []
        penalty = Point(0,0)
        repick = Point(0,0)
        members: set[MemberLike] = set()
        status: Status = Status.ONGOING

        if embed.author is not None:
            status = Status.from_string(embed.author.name)

        for field in embed.fields:
            if 'Penalty' in field.name:
                p = get_integers(field.value)
                penalty = penalty + Point(p[0],p[1])
            elif 'Repick' in field.name:
                r = get_integers(field.value)
                repick = repick + Point(r[0],r[1])
            elif 'Members' in field.name:
                temp: list[Optional[MemberLike]] = [message.guild.get_member(id) for id in get_integers(field.value)]
                members = {m for m in temp if m is not None}
            else:
                rank = Rank(get_integers(field.value)[-6:])
                track: Optional[Track] = None
                if '-' in field.name:
                    txt = field.name
                    track = Track.get_track(txt[txt.find('-')+2:])
                races.append(Race(rank, track))

        if status == Status.FINISHED and len(races) != 12:
            status = Status.ONGOING

        return MogiMessage(
            tags = [tags[0],tags[-1]],
            races = races,
            members = members,
            penalty = penalty,
            repick = repick,
            message = message,
            lang = lang,
            status = status
        )


    def add_race(self, race: Race) -> None:
        if self.status == Status.FINISHED:
            raise NotAddable
        if self.status == Status.ARCHIVE:
            raise MogiArchived

        self.races.append(race)

        if len(self.races) == 12:
            self.status = Status.FINISHED

        return


    def back(self) -> Race:
        if len(self.races) == 0:
            raise NotBackable

        if self.status == Status.ARCHIVE:
            raise MogiArchived

        self.status = Status.ONGOING
        return self.races.pop()


    async def send(
        self,
        context: ContextLike,
        content: Optional[str] = None
        ) -> None:
        old_msg = self.message
        params = {}
        e = self.embed.copy()

        if old_msg is not None:

            try:
                url = old_msg.embeds[0]._image['url']
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            pass
                        buffer = BytesIO()
                        buffer.write(await response.read())
                        buffer.seek(0)
                        params['file'] = File(buffer, filename = 'image.png')
                        e.set_image(url=f'attachment://image.png')

            except (KeyError, AttributeError):
                pass

        params['embed'] = e

        if content is not None:
            params['content'] = content

        if isinstance(context, Context):
            self.message = await context.send(**params)
        elif isinstance(context, ApplicationContext):
            msg = await context.respond(**params)
            if isinstance(msg, Interaction):
                self.message = msg.message
            else:
                self.message = msg
        elif isinstance(context, Messageable):
            self.message = await context.send(**params)

        if old_msg is not None and old_msg.author.id == MY_ID:
            await old_msg.delete()


    async def refresh(self, content: Optional[str] = None) -> None:
        params = {'content': content, 'attachments':[]}
        e = self.embed.copy()

        try:
            url = self.message.embeds[0]._image['url']
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        buffer = BytesIO()
                        buffer.write(await response.read())
                        buffer.seek(0)
                        params['file'] = File(buffer, filename = 'image.png')
                        e.set_image(url=f'attachment://image.png')

        except (KeyError, AttributeError):
            pass

        params['embed'] = e

        if self.message is not None and self.message.author.id == MY_ID:
            await self.message.edit(**params)
            return
        raise MogiNotFound


    @staticmethod
    async def get(
        messageable: Messageable,
        include_archive: bool= False
        ) -> tuple[MogiMessage, Optional[Track]]:
        track: Optional[Track] = None

        async for message in messageable.history(
            after = datetime.now() - timedelta(hours=1),
            oldest_first = False
        ):
            if track is None:
                track = Track.get_track(message.content)
            if MogiMessage.verify(message):
                msg = MogiMessage.convert(message)
                if msg.status == Status.ARCHIVE:
                    if include_archive:
                        return msg, track
                    else:
                        raise MogiArchived
                return msg, track
        raise MogiNotFound