from typing import Optional
from discord.ext import commands
from discord import (
    SlashCommandGroup,
    ApplicationContext,
    ApplicationCommandError,
    Option,
    OptionChoice,
    Role,
    Embed
)
import discord
import pandas as pd
from datetime import timedelta

from .errors import PlayerNotFound
from .components import VoteMessage

from common import (
    LoungeEmbed,
    get_players,
    get_team_name,
    set_team_name,
    get_dt,
    mkmg
)



MKC_URL = 'https://www.mariokartcentral.com/mkc/registry/players/'
LOUNGE_WEB = 'https://www.mk8dx-lounge.com/PlayerDetails/'


class Lounge(commands.Cog, name='Team'):

    def __init__(self,bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = 'Manage team info'
        self.description_localizations: dict[str, str] = {'ja':'チーム関連'}

    team = SlashCommandGroup(name='team')
    name = team.create_subgroup(name='name')


    @staticmethod
    async def get_players(role: Role) -> list[dict]:
        players = await get_players(
            discord_ids = [m.id for m in role.members],
            remove_None = True
        )
        if len(players) == 0:
            raise PlayerNotFound
        return pd.DataFrame(players).drop_duplicates(subset='name').to_dict('records')


    @discord.slash_command(
        name='vote',
        description='Start voting',
        description_localizations = {'ja':'参加アンケートを開始'}
    )
    async def start_voting(
        self,
        ctx: ApplicationContext,
        enemy: Option(
            str,
            name = 'enemy',
            name_localizations = {'ja':'チーム名'},
            description = 'enemy name',
            description_localizations = {'ja':'相手チームの名前'}
        ),
        role: Option(
            Role,
            name = 'role',
            name_localizations = {'ja':'ロール'},
            description = 'target',
            description_localizations = {'ja':'アンケートの対象'}
        ),
        hour: Option(
            int,
            min_value = 0,
            name = 'hour',
            name_localizations = {'ja':'時間'},
            description = 'hour',
            description_localizations = {'ja':'試合をする時間'}
            ),
        date: Option(
            str,
            name = 'date',
            name_localizations = {'ja':'日にち'},
            description = 'date',
            description_localizations = {'ja':'試合の日にち'},
            default = ''
        )
        ) -> None:
        await VoteMessage.start(
            ctx.interaction,
            enemy = enemy,
            role = role,
            dt = get_dt(date) + timedelta(hours=hour),
            lang = ctx.interaction.locale
        )


    @team.command(
        name = 'mmr',
        description = 'Average MMR',
        description_localizations = {'ja':'チームの平均MMRを計算'}
    )
    async def team_mmr(
        self,
        ctx: ApplicationContext,
        role: Option(
            Role,
            name = 'role',
            name_localizations = {'ja':'ロール'}
            )
    ) -> None:
        await ctx.response.defer()
        df = pd.DataFrame(await Lounge.get_players(role)).sort_values('mmr', ascending=False)
        average = df['mmr'].mean()

        e = LoungeEmbed(
            mmr = average,
            title = f'Team MMR: {average:.1f}'
        )
        txt = f'**Role**  {role.mention}\n\n'

        for i, player in enumerate(df.to_dict('records')):
            txt += f'{str(i+1).rjust(3)}: [{player["name"]}]({LOUNGE_WEB+str(player["id"])}) (MMR: {player["mmr"]})\n'

        txt += f'\n**Rank**  {e.rank}'
        e.description = txt
        await ctx.respond(embed= e)


    @team.command(
        name = 'mkc',
        description ='Show mkc website url',
        description_localizations ={'ja':'MKCサイトのリンク'}
    )
    async def team_mkc(
        self,
        ctx: ApplicationContext,
        role: Option(
            Role,
            name = 'role',
            name_localizations = {'ja':'ロール'}
        )
    ) -> None:
        await ctx.response.defer()
        players = await Lounge.get_players(role)
        e = Embed(title = 'MKC Registry', color = ctx.author.color)
        txt = f'**Role**  {role.mention}\n\n'

        for player in players:
            fc = player.get("switchFc")
            txt += f'[{player["name"]}]({MKC_URL}{player["registryId"]}) {"("+fc+")" if fc is not None else ""}\n'

        e.description = txt
        await ctx.respond(embed = e)
        return


    @team.command(
        name= 'mkmg',
        description = 'Create #mkmg template for twitter',
        description_localizations = {'ja': 'mkmgの外交文を作成'}
    )
    async def team_mkmg(
        self,
        ctx: ApplicationContext,
        time: Option(
            int,
            name = 'hour',
            name_localizations = {'ja': '時間'},
            description = 'Opening hour of match',
            description_localizations = {'ja': '交流戦の時間'},
            min_value = 0,
            default = None
        ),
        host: Option(
            str,
            name = 'host',
            name_localizations = {'ja': '主催'},
            description = 'Whether or not host',
            description_localizations = {'ja': '主催を持てるかどうか'},
            choices = [
                OptionChoice(name= 'Yes', name_localizations = {'ja': '可能'}, value = 'h'),
                OptionChoice(name= 'No', name_localizations = {'ja': '不可'}, value = '')
            ],
            default = ''
        )
    ):
        await ctx.response.defer()
        await ctx.respond(await mkmg(ctx.guild, time, host=='h'))


    @name.command(
        name = 'set',
        description = 'Set team name',
        description_localizations = {'ja':'チーム名を登録'}
    )
    async def team_name_set(
        self,
        ctx: ApplicationContext,
        name: Option(
            str,
            name = 'name',
            name_localizations = {'ja':'チーム名'},
            required = True
        )
    ) -> None:
        await ctx.response.defer()
        set_team_name(ctx.guild_id,name)
        await ctx.respond({'ja':f'チーム名を登録しました  **{name}**'}.get(ctx.locale, f'Set team name **{name}**'))
        return


    @name.command(
        name = 'reset',
        description = 'Reset team name',
        description_localizations = {'ja':'チーム名をリセット'}
    )
    async def team_name_reset(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        set_team_name(ctx.guild_id,ctx.guild.name)
        await ctx.respond({'ja':f'{ctx.guild.name}へリセットしました。'}.get(ctx.locale, f'Reset team name to default {ctx.guild.name}'))
        return


    @name.command(
        name = 'show',
        description = 'Show team name',
        description_localizations = {'ja': '登録されているチーム名を表示'}
    )
    async def team_name_show(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        await ctx.respond(get_team_name(ctx.guild_id or ctx.guild.name))



    async def cog_command_error(self, ctx: ApplicationContext, error: ApplicationCommandError) -> None:
        content: Optional[str] = None

        if isinstance(error, PlayerNotFound):
            content = {'ja':'プレイヤーが見つかりません。'}.get(ctx.locale, 'Player not found.')

        if content is not None:
            await ctx.respond(content, ephemeral = True)
            return

        raise error
