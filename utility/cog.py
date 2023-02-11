from typing import Optional
from discord import (
    ApplicationContext,
    SlashCommand,
    slash_command,
    Option,
    Embed,
    Colour,
    Message
)
from discord.ext import commands, pages
import asyncio
import re

from common import get_lounger, LoungeEmbed, mkmg, maybe_param, get_player
from .errors import *

MKC_URL = 'https://www.mariokartcentral.com/mkc/registry/players/'


class Utility(commands.Cog, name='Utility'):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = 'Utilities'
        self.description_localizations: dict[str, str] = {'ja':'ユーティリティ'}


    @slash_command(
        name = 'help',
        description = 'Show command help',
        description_localizations = {'ja':'コマンドの使い方'}
    )
    async def help(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        embeds: list[Embed] = []
        is_ja: bool = ctx.locale == 'ja'

        for _, cog in self.bot.cogs.items():

            if cog.hide:
                continue

            e = Embed(
                title = cog.description_localizations.get(ctx.locale, cog.description),
                color = Colour.yellow()
            )
            e.set_footer(text = '<必須> [任意]' if is_ja else '<Required> [Optional]')

            for command in cog.walk_commands():

                if isinstance(command, SlashCommand):
                    usage = command.description_localizations
                    if usage is not None:
                        usage = usage.get(ctx.locale, command.description)
                    e.add_field(
                        name = f'/{command.qualified_name}',
                        value = '> '+ usage or command.description,
                        inline = False
                    )
                elif isinstance(command, commands.Command):

                    if command.hidden:
                        continue

                    e.add_field(
                        name = command.usage,
                        value = '> ' + command.brief if is_ja else command.description,
                        inline = False
                    )


            embeds.append(e)

        await pages.Paginator(pages=embeds, author_check=False).respond(ctx.interaction)
        return

    @slash_command(
        name = 'who',
        description = 'Search Lounge name',
        description_localizations = {'ja': 'ラウンジ名を検索'}
    )
    async def who(
        self,
        ctx: ApplicationContext,
        input_str: Option(
            str,
            name = 'name',
            name_localizations = {'ja': '名前'},
            description = 'Switch FC, Discord ID, server nick-name and Lounge name are available.',
            description_localizations = {'ja': 'フレコ、Discord ID、ニックネーム、ラウンジ名で検索可能'}
        )
    ) -> None:
        await ctx.response.defer()
        name, discord_id, fc = maybe_param(input_str)

        member = ctx.guild.get_member_named(input_str)

        try:
            discord_id = discord_id or member.id
        except:
            pass

        if discord_id is not None:
            name, fc = None, None

        player = await get_player(
            name = name,
            discord_id = discord_id,
            fc = fc
        )

        if player is None:
            await ctx.respond({'ja': 'プレイヤーが見つかりませんでした。'}.get(ctx.locale, 'Not found.'))
            return

        msg = f"[{player['name']}](https://www.mk8dx-lounge.com/PlayerDetails/{player['id']})"

        try:
            user = self.bot.get_user(int(discord_id or player.get('discordId')))
            if user is not None:
                msg += f'   ({str(user)})'
        except:
            pass

        await ctx.respond(msg)
        return



    @commands.command(
        name = 'm',
        aliases = ['mkmg'],
        description = 'Create #mkmg template for twitter',
        brief = 'mkmgの外交文を作成',
        usage = '!m [hour] [host -> h]',
        hidden = False
    )
    async def mkmg_template(self, ctx: commands.Context, time: Optional[int] = None, host: str = ''):
        await ctx.send(await mkmg(ctx.guild, time = time, host = host.lower() == 'h'))



    @staticmethod
    async def from_fc(text: str, sort_values: Optional[bool] = None) -> Embed:
        _RE = re.compile(r'[0-9]{4}\-[0-9]{4}\-[0-9]{4}')
        inputs: list[str] = _RE.findall(text)
        dummy = inputs.copy()
        tasks = [asyncio.create_task(get_lounger(fc = fc)) for fc in inputs]
        players: list[Optional[dict]] = await asyncio.gather(*tasks, return_exceptions = False)

        count: int = 0
        total_mmr: int = 0
        content: str = ''

        if sort_values is not None:
            lineup: list[dict] = sorted(
                [p for p in players if p is not None and not p.get('isHidden')],
                reverse = bool(sort_values),
                key = lambda p: p['mmr']
            )
        else:
            lineup: list[dict] = [p for p in players]

        for i, player in enumerate(lineup):

            if player is not None:

                if player.get('isHidden'):
                    continue

                count += 1
                content += f'{str(count).rjust(3)}: [{player["name"]}]({MKC_URL}{player["registryId"]}) (MMR: {player["mmr"]})\n'
                total_mmr += player["mmr"]
                dummy.remove(player['switchFc'])
            else:
                content +=f"N/A ({inputs[i]})\n"
                dummy.remove(inputs[i])

        if count == 0:
            raise PlayerNotFound

        for fc in dummy:
            content +=f"N/A ({fc})\n"

        e = LoungeEmbed(
            mmr = total_mmr/count,
            title = f'Average MMR: {total_mmr/count:.1f}',
        )
        e.description = content + f'\n**Rank** {e.rank}'
        return e



    @commands.Cog.listener('on_message')
    async def fm_message(self, message: Message) -> None:
        payload: dict = {}

        if message.author.bot:
            return

        try:
            if message.content.lower().startswith('!fml'):
                payload['embed'] = await Utility.from_fc(message.content, False)

            elif message.content.lower().startswith('!fmh'):
                payload['embed'] = await Utility.from_fc(message.content, True)

            elif message.content.lower().startswith('!fm'):
                payload['embed'] = await Utility.from_fc(message.content, None)
        except PlayerNotFound:
            payload['content'] = 'プレイヤーが見つかりません。\nPlayer not found.'
            payload['delete_after'] = 10.0

        if payload:
            await message.channel.send(**payload)
