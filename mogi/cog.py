from typing import Optional
from discord.ext import commands
from discord import (
    SlashCommandGroup,
    ApplicationContext,
    ApplicationCommandError,
    Option,
    Role,
    Message,
    Attachment,
    message_command
)

from .components import MogiMessage
from .errors import *
from .status import Status

from common import (
    get_team_name,
    post_results,
    Lang,
    Point,
    Race,
    Rank,
    Track
)


class Mogi(commands.Cog, name='Mogi'):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = 'About Sokuji'
        self.description_localizations: dict[str, str] = {'ja':'即時関連'}

    mogi = SlashCommandGroup(name='mogi')
    race = mogi.create_subgroup(name='race')
    penalty = mogi.create_subgroup(name='penalty')
    image = mogi.create_subgroup(name='image')


    @message_command(name = 'Register Result')
    async def register_result(
        self,
        ctx: ApplicationContext,
        message: Message
    ) -> None:
        await ctx.response.defer()
        MogiMessage.verify(message, raise_exceptions=True)
        msg = MogiMessage.convert(message)
        post_results(
            guild_id = ctx.guild_id,
            point = msg.total,
            enemy = msg.tags[-1],
            dt = msg.message.created_at
        )
        txt = f'**{msg.tags[0]}**  `{msg.total}` **{msg.tags[1]}**'
        await ctx.respond({'ja': f'戦績を登録しました\n{txt}'}.get(msg.lang.value, f'Registered result\n{txt}'))


    @mogi.command(
        name = 'start',
        description = 'Start Mogi',
        description_localizations = {'ja':'即時集計の開始'}
    )
    async def mogi_start(
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
            description = 'Member role',
            description_localizations = {'ja':'参加メンバーのロール'},
            default = None
        )
        ) -> None:
        await ctx.response.defer()
        members = set()
        if role is not None:
            members = set(role.members)
        name = get_team_name(ctx.guild_id) or ctx.guild.name
        await MogiMessage(
            tags = [name,enemy],
            members = members,
            lang = {'ja':Lang.JA}.get(ctx.locale, Lang.EN)
        ).send(ctx, {'ja':'即時を開始します。'}.get(ctx.locale, 'Started Mogi.'))
        return


    @mogi.command(
        name = 'language',
        description = 'Change language',
        description_localizations = {'ja':'即時の言語を変更'}
    )
    async def mogi_language(
        self,
        ctx: ApplicationContext,
        locale: Option(
            str,
            name = 'language',
            name_localizations = {'ja':'言語'},
            description = 'Change language',
            description_localizations = {'ja':'変更したい言語'},
            choices = ['English', '日本語'],
            required = True
        )
    ) -> None:
        flag = locale == '日本語'
        await ctx.response.defer()
        msg, _ = await MogiMessage.get(ctx.channel, True)
        msg.lang = Lang.JA if flag else Lang.EN
        await msg.refresh()
        await ctx.respond('日本語へ変更しました。' if flag else 'Changed to English.')
        return


    @mogi.command(
        name = 'edit',
        description = 'Edit mogi setting',
        description_localizations = {'ja': '即時の設定を変更'}
    )
    async def mogi_edit(
        self,
        ctx: ApplicationContext,
        enemy: Option(
            str,
            name = 'enemy',
            name_localizations = {'ja':'チーム名'},
            description = 'enemy name',
            description_localizations = {'ja':'相手チームの名前'},
            default = None
        ),
        role: Option(
            Role,
            name = 'role',
            name_localizations = {'ja':'ロール'},
            description = 'Member role',
            description_localizations = {'ja':'参加メンバーのロール'},
            default = None
        )
    ) -> None:
        msg, _ = await MogiMessage.get(ctx.channel)
        if enemy is not None:
            msg.tags[1] = enemy
        if role is not None:
            msg.members = set(role.members)
        await msg.refresh()
        await ctx.respond({'ja':'即時を編集しました。'}.get(msg.lang.value, 'Edited mogi.'))


    @mogi.command(
        name = 'end',
        description = 'End mogi.',
        description_localizations = {'ja':'即時を終了'}
    )
    async def mogi_end(self, ctx: ApplicationContext):
        await ctx.response.defer()
        msg, _ = await MogiMessage.get(ctx.channel)
        msg.status = Status.ARCHIVE
        await msg.refresh()
        await ctx.respond({'ja':'即時を終了しました。'}.get(msg.lang.value, 'Finished mogi.'))


    @mogi.command(
        name = 'resume',
        description = 'Resume mogi.',
        description_localizations = {'ja':'即時を再開'}
    )
    async def mogi_resume(self, ctx: ApplicationContext):
        await ctx.response.defer()
        msg, _ = await MogiMessage.get(ctx.channel, True)
        if len(msg.races) == 12:
            msg.status = Status.FINISHED
        else:
            msg.status = Status.ONGOING
        await msg.refresh()
        await ctx.respond({'ja':'即時を再開しました。'}.get(msg.lang.value, 'Resumed mogi.'))


    @race.command(
        name='add',
        description = 'Add race.',
        description_localizations = {'ja':'即時にレースを追加'}
    )
    async def mogi_race_add(
        self,
        ctx: ApplicationContext,
        rank: Option(
            str,
            name = 'rank',
            name_localizations = {'ja':'順位'}
        ),
        track: Option(
            str,
            name = 'track',
            name_localizations = {'ja':'コース名'},
            default = '',
            required = False
        )
    ) -> None:
        await ctx.response.defer()
        msg, _ = await MogiMessage.get(ctx.channel)
        rank = Rank.from_string(rank)

        if rank is None:
            raise InvalidRankInput

        msg.add_race(Race(rank, Track.get_track(track or '')))
        await msg.send(ctx, {'ja':'レースを追加しました。'}.get(msg.lang.value, 'Added race.'))
        return


    @race.command(
        name = 'back',
        description = 'back to previous race',
        description_localizations = {'ja':'レースを一つ戻す'}
    )
    async def mogi_race_back(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        msg, _ = await MogiMessage.get(ctx.channel)
        msg.back()
        await msg.refresh()
        await ctx.respond({'ja':'1レース戻しました。'}.get(msg.lang.value, 'Backed to previous race'))
        return


    @race.command(
        name = 'edit',
        description = 'Edit race',
        description_localizations = {'ja':'レースの編集'}
    )
    async def mogi_race_edit(
        self,
        ctx: ApplicationContext,
        number: Option(
            int,
            name = 'number',
            name_localizations = {'ja':'レース番号'},
            description = 'Race number',
            description_localizations = {'ja':'編集するレース番号'},
            min_value = 1,
            max_value = 12,
            default = 0
        ),
        rank: Option(
            str,
            name = 'rank',
            name_localizations = {'ja':'順位'},
            default = ''
        ),
        track: Option(
            str,
            name = 'track',
            name_localizations = {'ja':'コース名'},
            default = '',
        )
    ) -> None:
        await ctx.response.defer()
        index: int = number -1
        msg, _  = await MogiMessage.get(ctx.channel)

        try:
            prev_race = msg.races[index]
            prev_rank = prev_race.rank
            prev_track = prev_race.track
            msg.races[index] = Race(
                rank = Rank.from_string(rank) or prev_rank,
                track = Track.get_track(track) or prev_track,
            )
        except IndexError:
            raise OutOfRange

        await msg.refresh()
        await ctx.respond({'ja':'レースを編集しました。'}.get(msg.lang.value, 'Edited race.'))



    @penalty.command(
        name = 'add',
        description = 'Add penalty or repick.',
        description_localizations = {'ja':'ペナルティを追加'}
    )
    async def mogi_penalty_add(
        self,
        ctx: ApplicationContext,
        reason: Option(
            str,
            name = 'reason',
            name_localizations = {'ja':'種類'},
            choices = ['Repick', 'Penalty'],
            default = 'Repick'
        ),
        tag: Option(
            str,
            name ='tag',
            name_localizations = {'ja':'チーム名'},
            default = None
            ),
        amount: Option(
            int,
            name = 'amount',
            name_localizations = {'ja':'ポイント'},
            description = 'Penalty point',
            description_localizations = {'ja':'ペナルティのポイント'},
            default = -15
        )
    ) -> None:
        await ctx.response.defer()
        msg, _ = await MogiMessage.get(ctx.channel)
        p = Point(amount, 0)

        if tag is not None:
            if tag == msg.tags[0]:
                p = Point(amount, 0)
            elif tag == msg.tags[1]:
                p = Point(0, amount)
            else:
                raise InvalidTag

        if reason == 'Repick':
            msg.repick = msg.repick + p
        else:
            msg.penalty = msg.penalty + p

        await msg.refresh()
        await ctx.respond({'ja':'ペナルティを追加しました。'}.get(msg.lang.value, 'Added penalty.'))
        return


    @penalty.command(
        name = 'clear',
        description = 'Clear penalty.',
        description_localizations = {'ja':'ペナルティを削除'}
    )
    async def mogi_penalty_clear(
        self,
        ctx: ApplicationContext,
        reason: Option(
            name = 'reason',
            name_localizations = {'ja':'種類'},
            choices = ['Repick','Penalty'],
            default = None
        )
    ) -> None:
        await ctx.response.defer()
        msg, _ = await MogiMessage.get(ctx.channel)

        if reason != 'Repick':
            msg.penalty = Point(0,0)
        if reason != 'Penalty':
            msg.repick = Point(0,0)

        await msg.refresh()
        await ctx.respond({'ja':'ペナルティを削除しました。'}.get(msg.lang.value, 'Cleared penalty.'))


    @image.command(
        name = 'set',
        description = 'Set result image',
        description_localizations = {'ja':'リザルト画像を登録'}
    )
    async def mogi_image_set(
        self,
        ctx: ApplicationContext,
        file: Option(
            Attachment,
            name = 'image',
            name_localizations = {'ja':'集計画像'},
            description = 'Result image',
            description_localizations = {'ja':'登録する集計画像'}
        )
    ) -> None:
        await ctx.response.defer()

        if not file.filename.endswith(('.jpg', '.jpeg','png')):
            raise InvalidFile

        msg, _ = await MogiMessage.get(ctx.channel, True)
        embed = msg.embed.copy()
        embed.set_image(url=f'attachment://{file.filename}')
        f = await file.to_file()
        await msg.message.edit(embed=embed, file=f)
        await ctx.respond({'ja':'画像を添付しました。'}.get(msg.lang.value, 'Attached result image.'))


    @image.command(
        name = 'remove',
        description = 'Remove result image',
        description_localizations = {'ja':'リザルト画像を削除'}
    )
    async def mogi_image_remove(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        msg, _ = await MogiMessage.get(ctx.channel, True)
        e = msg.message.embeds[0].copy()
        e.remove_image()
        await msg.message.edit(embed=e, attachments = [])
        await ctx.respond({'ja':'画像を削除しました。'}.get(msg.lang.value, 'Removed result image.'))


    @commands.Cog.listener('on_message')
    async def on_mogi_message(self, message: Message):

        if message.author.bot:
            return

        try:
            msg, track = await MogiMessage.get(message.channel)
            if message.content == 'back':
                msg.back()
                await msg.send(message.channel)
                return
            if Rank.verify(message.content):
                rank = Rank.from_string(message.content)
                if rank is None:
                    return
                msg.add_race(Race(rank, track))
                await msg.send(message.channel)
                return
        except (MogiNotFound, NotAddable, NotBackable, MogiArchived):
            return


    async def cog_command_error(self, ctx: ApplicationContext, error: ApplicationCommandError) -> None:
        content: Optional[str] = None

        if isinstance(error, MogiNotFound):
            content = {'ja':'実施している即時が見つかりません。'}.get(ctx.locale, 'Mogi not Found.')
        elif isinstance(error, InvalidMessage):
            content = {'ja':'メッセージが不正です。'}.get(ctx.locale, 'Invalid Message.')
        elif isinstance(error, InvalidRankInput):
            content = {'ja':'順位の入力が不正です。'}.get(ctx.locale, 'Invalid rank input.')
        elif isinstance(error, NotBackable):
            content = {'ja':'レースを戻すことができません。'}.get(ctx.locale, 'You cannot back race anymore.')
        elif isinstance(error, NotAddable):
            content = {'ja':'既に12レース終了しています。'}.get(ctx.locale, 'This mogi has already finished.')
        elif isinstance(error, MogiArchived):
            content = {'ja':'この即時は既に終了しています。'}.get(ctx.locale, 'This mogi has already finished.')
        elif isinstance(error, InvalidTag):
            content = {'ja':'タグの名前が不正です。'}.get(ctx.locale,'Invalid tag name.')
        elif isinstance(error, OutOfRange):
            content = {'ja':'存在しないレース番号です。'}.get(ctx.locale,'Invalid race number.')
        elif isinstance(error, InvalidFile):
            content = {'ja':'ファイル拡張子は`.jpeg, .jpg, .png`のみです。'}.get(ctx.locale,'Only `.jpeg, .jpg, .png` are available.')

        if content is not None:
            await ctx.respond(content, ephemeral = True)
            return

        raise error
