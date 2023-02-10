from typing import Optional
from discord.ext import commands
from discord import (
    Option,
    ApplicationContext,
    ApplicationCommandError,
    SlashCommandGroup,
    File,
    Attachment
)
from discord.utils import format_dt

from .errors import *
from .components import ResultPaginator
from . import components
from common.plotting import result_graph as plot_result
from common.api import get_team_name




class Result(commands.Cog, name = 'Result'):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = 'Manage Results'
        self.description_localizations: dict[str, str] = {'ja':'戦績管理'}


    result = SlashCommandGroup(name = 'result')
    data = result.create_subgroup(name = 'data')


    @result.command(
        name = 'list',
        description = 'Show all results',
        description_localizations = {'ja': '戦績を全て表示'}
    )
    async def result_list(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        await components.show_all(ctx.guild_id).respond(ctx.interaction)


    @result.command(
        name = 'search',
        description = 'Search results by team name',
        description_localizations = {'ja': 'チーム名で対戦履歴を検索'}
    )
    async def result_search(
        self,
        ctx: ApplicationContext,
        name: Option(
            str,
            name = 'enemy',
            name_localizations = {'ja': '相手チーム名'},
            description = 'Enemy team name',
            description_localizations = {'ja': '検索するチーム名'}
        )
    ) -> None:
        await ctx.response.defer()
        page = components.search_results(ctx.guild_id, name)

        if isinstance(page, ResultPaginator):
            await page.respond(ctx.interaction)
            return
        else:
            if page:
                await ctx.respond(
                    {'ja': '戦績が見つかりませんでした。\n類似した名前: '}.get(
                        ctx.locale, 'Result not found.\nSimilar name:  ') + ', '.join(page)
                )
                return

        raise EmptyResult


    @result.command(
        name = 'graph',
        description = 'Show result graph',
        description_localizations = {'ja': '戦績グラフを表示'}
    )
    async def result_graph(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        buffer = plot_result(components.get(ctx.guild_id))
        await ctx.respond(file = File(buffer, 'results.png'))


    @result.command(
        name = 'register',
        description = 'Register result',
        description_localizations = {'ja': '戦績を登録'}
    )
    async def result_register(
        self,
        ctx: ApplicationContext,
        name: Option(
            str,
            name = 'enemy',
            name_localizations = {'ja': 'チーム名'},
            description = 'Enemy name',
            description_localizations = {'ja': '相手チームの名前'}
        ),
        scores: Option(
            str,
            name = 'scores',
            name_localizations = {'ja': '得点'},
            description = 'TeamScore (EnemyScore)',
            description_localizations = {'ja': '自チームの得点  (相手の得点)'}
        ),
        date: Option(
            str,
            name = 'date',
            name_localizations = {'ja': '日にち'},
            description = '(year) (month) day',
            description_localizations = {'ja': '(年) (月) 日'},
            default = ''
        )
    ) -> None:
        await ctx.response.defer()
        data = components.register(ctx.guild_id, name, scores, date)
        msg = f'{data["point"].to_string()}  vs. **{name}** {format_dt(data["dt"], style = "F")}'
        await ctx.respond(
            {'ja': '戦績を登録しました。\n'}.get(
                ctx.locale, 'Successfully sent result.\n') + msg
        )
        return


    @result.command(
        name = 'delete',
        description = 'Delete results.',
        description_localizations = {'ja': '戦績を削除'},
    )
    async def result_delete(
        self,
        ctx: ApplicationContext,
        id: Option(
            str,
            name = 'id',
            description = 'ID (multiple available)',
            description_localizations = {'ja': '削除する戦績のID (複数可)'},
            default = '-1'
        )
    ) -> None:
        await ctx.response.defer()
        await components.delete(ctx.guild_id, id, ctx.locale).respond(ctx.interaction)


    @result.command(
        name = 'edit',
        description = 'Edit result',
        description_localizations = {'ja': '戦績を編集'}
    )
    async def result_edit(
        self,
        ctx: ApplicationContext,
        id: Option(
            int,
            name = 'id',
            description = 'Result ID',
            description_localizations = {'ja': '編集する戦績のID'},
            min_value = 0
        ),
        enemy: Option(
            str,
            name = 'enemy',
            name_localizations = {'ja': 'チーム名'},
            description = 'Enemy name',
            description_localizations = {'ja': '相手チームの名前'},
            default = None
        ),
        scores: Option(
            str,
            name = 'scores',
            name_localizations = {'ja': '得点'},
            description = 'TeamScore (EnemyScore)',
            description_localizations = {'ja': '自チームの得点  (相手の得点)'},
            default = None
        ),
        date: Option(
            str,
            name = 'date',
            name_localizations = {'ja': '日にち'},
            description = '(year) (month) day',
            description_localizations = {'ja': '(年) (月) 日'},
            default = None
        )
    ) -> None:
        await ctx.response.defer()
        data = components.edit(ctx.guild_id, id, enemy, scores, date)
        msg = f'`{id}` {data["point"].to_string()}  vs. **{data["enemy"]}** {format_dt(data["dt"], style = "F")}'
        await ctx.respond(
            {'ja': '戦績を編集しました。\n'}.get(
                ctx.locale, 'Successfully edited result.\n') + msg
        )
        return


    @data.command(
        name = 'export',
        description = 'Export result data',
        description_localizations = {'ja': '保存された戦績ファイルを出力'}
    )
    async def result_data_export(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        buffer = components.export_file(
            guild_id = ctx.guild_id,
            name = get_team_name(ctx.guild_id) or ctx.guild.name
        )
        await ctx.respond(
            {'ja':'ファイルを送信しました。'}.get(ctx.locale, 'Sent result file.'),
            file = File(buffer, 'result.csv')
        )
        return


    @data.command(
        name = 'load',
        description = 'Load result file and override',
        description_localizations = {'ja': '戦績ファイルを読み込んで上書き'}
    )
    async def result_data_load(
        self,
        ctx: ApplicationContext,
        file: Option(
            Attachment,
            name = 'csv',
            name_localizations = {'ja': 'csvファイル'},
            description = 'File to load',
            description_localizations = {'ja': '戦績が書き込まれたファイル'}
        )
    ) -> None:
        await ctx.response.defer()

        if not file.filename.endswith('.csv'):
            raise NotCSVFile

        await components.load_file(ctx.guild_id, file)
        await ctx.respond({'ja':'戦績ファイルを読み込みました。'}.get(ctx.locale, 'Loaded result file.'))
        return






    async def cog_command_error(self, ctx: ApplicationContext, error: ApplicationCommandError) -> None:
        content: Optional[str] = None

        if isinstance(error, EmptyResult):
            content = {'ja':'戦績が見つかりません。'}.get(ctx.locale, 'Result not Found.')
        elif isinstance(error, InvalidScoreInput):
            content = {'ja':'得点の入力が不正です。\n`自チーム (敵チーム 任意)`'}.get(ctx.locale, 'Invalid scores input\n `score (enemy_score; optional)`')
        elif isinstance(error, InvalidIdInput):
            content = {'ja':'IDの入力が不正です。'}.get(ctx.locale, 'Invalid ID input.')
        elif isinstance(error, IdOutOfRange):
            content = {'ja':'存在しないIDが含まれています。'}.get(ctx.locale, 'This ID does not exist.')
        elif isinstance(error, NotCSVFile):
            content = {'ja':'CSVファイルのみが有効です。'}.get(ctx.locale, 'Only CSV file is available.')
        elif isinstance(error, NotAcceptableContent):
            content = {'ja':'ファイルの内容が不正です。'}.get(ctx.locale, 'Not acceptable content.')

        if content is not None:
            await ctx.respond(content, ephemeral = True)
            return

        raise error