from discord.ext import commands, pages
from discord import Embed, Colour, File

from .errors import *
from common import get_team_name, get_integers
from result import load_file, export_file, EmptyResult, NotAcceptableContent



class Admin(commands.Cog, name='Admin'):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = True


    @commands.is_owner()
    @commands.command(name='user')
    async def user(self, ctx: commands.Context, id: int) -> None:
        user = self.bot.get_user(id)

        if user is None:
            raise NotFound

        e = Embed(
            title = str(user),
            description = f'参加サーバー\n',
            color = Colour.blurple()
        )

        for guild in user.mutual_guilds:
            e.description += f'{guild.name} (`{guild.id}`)\n'

        e.set_author(name = str(user.id), icon_url = user.display_avatar)

        await ctx.author.send(embed = e)


    @commands.is_owner()
    @commands.command(name = 'guild', aliases = ['server'])
    async def guild(self, ctx: commands.Context, id: int) -> None:
        g = self.bot.get_guild(id)

        if g is None:
            raise NotFound

        header = f'メンバー ({len(g.members)})\n'
        p = commands.Paginator(prefix='', suffix='', max_size = 3900)

        for member in g.members:

            if member == g.owner:
                p.add_line(f'__**{str(member)}**__ (`{member.id}`)')
            else:
                p.add_line(f'{str(member)} (`{member.id}`)')

        is_compact: bool = len(p.pages) == 1

        await pages.Paginator(
            pages = [Embed(title = f'{g.name} (`{g.id}`)', color = Colour.blurple(), description = header + page) for page in p.pages],
            show_disabled = not is_compact,
            show_indicator = not is_compact,
            author_check = False
        ).send(ctx, target=ctx.author)


    @commands.is_owner()
    @commands.command(name='users', aliases = ['ul', 'userlist'])
    async def users(self, ctx: commands.Context) -> None:
        p = commands.Paginator(prefix='', suffix='', max_size = 3900)

        for user in self.bot.users:
            p.add_line(f'{str(user)} (`{user.id}`)')

        is_compact: bool = len(p.pages) == 1

        await pages.Paginator(
            pages = [Embed(title = f'ユーザー ({len(self.bot.users)})', color = Colour.blurple(), description =  page) for page in p.pages],
            show_disabled = not is_compact,
            show_indicator = not is_compact,
            author_check = False
        ).send(ctx, target=ctx.author)


    @commands.is_owner()
    @commands.command(name='guilds', aliases=['guildlist', 'serverlist', 'gl', 'sl'])
    async def guilds(self, ctx: commands.Context) -> None:
        p = commands.Paginator(prefix='', suffix='', max_size = 3900)

        for guild in self.bot.guilds:
            p.add_line(f'{guild.name} (`{guild.id}`)')

        is_compact: bool = len(p.pages) == 1

        await pages.Paginator(
            pages = [Embed(title = f'ギルド ({len(self.bot.guilds)})', color = Colour.blurple(), description = page) for page in p.pages],
            show_disabled = not is_compact,
            show_indicator = not is_compact,
            author_check = False
        ).send(ctx, target=ctx.author)


    @commands.is_owner()
    @commands.command(name='mexport')
    async def mexport(self, ctx: commands.Context, id: int) -> None:
        guild = self.bot.get_guild(id)

        if guild is None:
            raise NotFound

        name = get_team_name(id) or guild.name

        try:
            await ctx.author.send(f'{name}の戦績を出力しました。', file= File(export_file(id, name), filename=f'{guild.id}.csv'))
            return
        except EmptyResult:
            await ctx.author.send(f'{name}は戦績を登録していません。', delete_after=10.0)


    @commands.is_owner()
    @commands.command(name='mload')
    async def mload(self, ctx: commands.Context) -> None:

        try:
            guild = self.bot.get_guild(get_integers(ctx.message.attachments[0].filename)[0])
        except:
            raise NotFound

        if not ctx.message.attachments[0].filename.endswith('csv'):
            await ctx.author.send('CSVファイルのみ有効です。', delete_after=10.0)
            return

        await self.mexport(ctx, guild.id)

        try:
            await load_file(guild.id, ctx.message.attachments[0])
            await ctx.author.send(f'{guild.name}の戦績を変更しました。')
        except NotAcceptableContent:
            await ctx.author.send('不正な内容が含まれています。', delete_after=10.0)
            return


    @commands.Cog.listener('on_command_error')
    async def error_handler(self, ctx: commands.Context, error: commands.CommandError) -> None:

        if isinstance(error, NotFound):
            await ctx.author.send('Not found', delete_after=10.0)
            return
