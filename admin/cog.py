from discord.ext import commands, pages
from discord import Embed, Colour
from .errors import *



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


    @commands.Cog.listener('on_command_error')
    async def error_handler(self, ctx: commands.Context, error: commands.CommandError) -> None:

        if isinstance(error, NotFound):
            await ctx.send('Not found', delete_after=10.0)
            return