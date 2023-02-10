from typing import Optional, Union
from discord.ext import commands
from discord import (
    slash_command,
    OptionChoice,
    ApplicationContext,
    ApplicationCommandError,
    Option,
    Member
)
from .errors import *
from . import components
from common import get_integers

ContextLike = Union[ApplicationContext, commands.Context]


class HandsUp(commands.Cog, name='Match'):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = 'Recruitment of Participants'
        self.description_localizations: dict[str, str] = {'ja':'挙手関連'}

    @staticmethod
    def to_hours(text: str) -> list[int]:
        hours = get_integers(text)

        if not hours:
            raise TimeNotSelected

        return hours


    @slash_command(
        name = 'can',
        description = 'Participate in match',
        description_localizations = {'ja': '交流戦の挙手'}
    )
    async def match_can(
        self,
        ctx: ApplicationContext,
        hours: Option(
            str,
            name = 'hours',
            name_localizations = {'ja': '時間'},
            description = 'Time to participate (multiple available)',
            description_localizations = {'ja': '参加する時間(複数可)'},
        ),
        action: Option(
            str,
            name = 'type',
            name_localizations = {'ja': 'タイプ'},
            description = 'Participate or tentatively participate.',
            description_localizations = {'ja': '挙手または仮挙手'},
            choices = [
                OptionChoice(name = 'can', value = 'c', name_localizations = {'ja': '挙手'}),
                OptionChoice(name = 'tentatively', value = 't', name_localizations = {'ja': '仮挙手'})
            ],
            default = 'c'
        ),
        member: Option(
            Member,
            name = 'member',
            name_localizations = {'ja': 'メンバー'},
            description = 'Member to participate',
            description_localizations = {'ja': '参加するメンバー'},
            default = None
        )
        ) -> None:
        await ctx.response.defer()
        member = member or ctx.author
        hours = HandsUp.to_hours(hours)
        flag: bool = action == 't'
        payload = await components.participate(ctx, action, [member], hours)
        await ctx.respond(
            {'ja': f'{member.name}さんが{", ".join([str(h) for h in hours])}へ{"仮" if flag else ""}挙手しました。'}.get(
                ctx.locale, f'{member.name} have {"tentatively " if flag else ""}joined {", ".join([str(h) for h in hours])}.'
            ),
            embed = payload['embed'],
        )

        if payload.get('call'):
            await ctx.respond(payload['call'])
        return


    @slash_command(
        name = 'drop',
        description = 'Cancel participation',
        description_localizations = {'ja': '挙手を取り下げる'}
    )
    async def match_drop(
        self,
        ctx: ApplicationContext,
        hours: Option(
            str,
            name = 'hours',
            name_localizations = {'ja': '時間'},
            description = 'Multiple available',
            description_localizations = {'ja': '挙手を取り下げる時間(複数可)'},
        ),
        member: Option(
            Member,
            name = 'member',
            name_localizations = {'ja': 'メンバー'},
            description = 'Member who cancel his participation',
            description_localizations = {'ja': '挙手を取り下げるメンバー'},
            default = None
        )
    ) -> None:
        await ctx.response.defer()
        hours = HandsUp.to_hours(hours)
        member = member or ctx.author
        e = await components.drop(ctx, [member], hours)
        await ctx.respond(
            {'ja': f'{member.name}さんが{", ".join([str(h) for h in hours])}の挙手を取り下げました。'}.get(
                ctx.locale, f'{member.name} have dropped {", ".join([str(h) for h in hours])}.'
            ),
            embed = e
        )
        return


    @slash_command(
        name = 'out',
        description = 'Delete recruiting',
        description_localizations = {'ja': '募集時間を削除'}
    )
    async def match_out(
        self,
        ctx: ApplicationContext,
        hours: Option(
            str,
            name = 'hours',
            name_localizations = {'ja': '時間'},
            description = 'Multiple available',
            description_localizations = {'ja': '削除する時間(複数可)'},
        )
    ) -> None:
        await ctx.response.defer()
        hours = HandsUp.to_hours(hours)
        await components.out(ctx, hours)
        await ctx.respond(
            {'ja': f'{",".join([str(h) for h in hours])}の募集を削除しました'}.get(
                ctx.locale, f'Deleted `{",".join([str(h) for h in hours])}`'
            )
        )
        return


    @slash_command(
        name = 'clear',
        description = 'Clear war list',
        description_localizations = {'ja': '募集を全てリセット'}
    )
    async def match_clear(self, ctx: ApplicationContext):
        await ctx.response.defer()
        await components.clear(ctx)
        await ctx.respond({'ja': '募集をリセットしました。'}.get(ctx.locale, 'Reset recruiting.'))


    @slash_command(
        name = 'now',
        description = 'Show recruiting state.',
        description_localizations = {'ja': '募集状況を表示'}
    )
    async def match_now(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        await components.now(ctx)
        return


    @commands.command(
        name = 'can',
        aliases = ['c'],
        description = 'Participate in match',
        brief = '交流戦の挙手',
        usage = '!c [@members] <hours>',
        hidden = False
    )
    async def can(
        self,
        ctx: commands.Context,
        members: commands.Greedy[Member] = [],
        *,
        hours: str = ''
    ) -> None:
        hours = HandsUp.to_hours(hours)
        members = members or [ctx.author]
        payload = await components.participate(ctx, 'c', members, hours)
        await ctx.send(
            f'{",".join([m.name for m in members])}さんが{", ".join([str(h) for h in hours])}へ挙手しました。',
            embed = payload['embed'],
        )

        if payload.get('call'):
            await ctx.send(payload['call'])
        return


    @commands.command(
        name = 'tentatively',
        aliases = ['t', 'maybe', 'rc', 'sub'],
        description = 'Tentatively participate in match',
        brief = '交流戦の仮挙手',
        usage = '!t [@members] <hours>',
        hidden = False
    )
    async def tentative(
        self,
        ctx: commands.Context,
        members: commands.Greedy[Member] = [],
        *,
        hours: str = ''
    ) -> None:
        hours = HandsUp.to_hours(hours)
        members = members or [ctx.author]
        payload = await components.participate(ctx, 't', members, hours)
        await ctx.send(
            f'{",".join([m.name for m in members])}さんが{", ".join([str(h) for h in hours])}へ仮挙手しました。',
            embed = payload['embed'],
        )


    @commands.command(
        name = 'drop',
        aliases = ['d', 'dr'],
        description = 'Cancel participation',
        brief = '挙手の取り消し',
        usage = '!d [@members] <hours>',
        hidden = False
    )
    async def drop(
        self,
        ctx: commands.Context,
        members: commands.Greedy[Member] = [],
        *,
        hours: str = ''
    ) -> None:
        hours = HandsUp.to_hours(hours)
        members = members or [ctx.author]
        e = await components.drop(ctx, members, hours)
        await ctx.send(
            f'{",".join([m.name for m in members])}さんが{", ".join([str(h) for h in hours])}の挙手を取り下げました。',
            embed = e,
        )


    @commands.command(
        name = 'now',
        aliases = ['warlist', 'list'],
        description = 'Show recruiting state.',
        brief = '募集状況の表示',
        usage = '!now',
        hidden = False
    )
    async def now(self, ctx: commands.Context) -> None:
        await components.now(ctx)
        return


    @commands.command(
        name = 'out',
        description = 'Delete recruiting',
        brief = '募集時間を削除',
        usage = '!out <hours>',
        hidden = False
    )
    async def out(self, ctx: commands.Context, hours: commands.Greedy[int] = []) -> None:

        if not hours:
            raise TimeNotSelected

        await components.out(ctx, hours)
        await ctx.send(f'{",".join([str(h) for h in hours])}の募集を削除しました')
        return


    @commands.command(
        name = 'clear',
        description = 'Clear war list',
        brief = '募集を全てリセット',
        usage = '!clear',
        hidden = False
    )
    async def clear(self, ctx: commands.Context) -> None:
        await components.clear(ctx)
        await ctx.send('募集をリセットしました。')



    async def cog_command_error(self, ctx: ContextLike, error: ApplicationCommandError) -> None:
        content: Optional[str] = None

        if isinstance(ctx, commands.Context):
            return

        if isinstance(error, TimeNotSelected):
            content = {'ja': '時間が選択されていません。'}.get(ctx.locale, 'Time is not selected.')
        elif isinstance(error, HourNotAddable):
            content = {'ja': '募集できる時間は25個までです。'}.get(ctx.locale, 'The maximum number of times that can be set is 25.')
        elif isinstance(error, NotGathering):
            content = {'ja': '募集している時間はありません。'}.get(ctx.locale, 'There is no recruiting.')

        if content is not None:
            await ctx.respond(content)
            return

        raise error


    @commands.Cog.listener('on_command_error')
    async def error_handler(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ) -> None:
        content: Optional[str] = None

        if isinstance(error, TimeNotSelected):
            content = '時間が選択されていません。\nTime is not selected.'
        elif isinstance(error, HourNotAddable):
            content = '募集できる時間は25個までです。\nThe maximum number of times that can be set is 25.'
        elif isinstance(error, NotGathering):
            content = '募集している時間はありません。\nThere is no recruiting.'

        if content is not None:
            await ctx.send(content, delete_after=10.0)
