from typing import Optional
from discord.ext import commands
import discord

import logging
import json
import os

from errors import MyError
from team.cog import Lounge
from mogi.cog import Mogi
from utility.cog import Utility
from result.cog import Result
from handsup.cog import HandsUp
from admin.cog import Admin
from team.components import VoteView

import json

config = json.loads(os.environ['CONFIG'])

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class Bot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix = '!',
            intents = intents,
            case_insensitive = True,
            help_command = None
        )
        self.persistent_views_added = False

    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(VoteView())
            self.persistent_views_added = True
        logging.info('Successfully logged in')


    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ) -> None:
        content: Optional[str] = None

        if isinstance(error, MyError):
            return
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.NotOwner):
            content = 'これは管理者専用のコマンドです。\nThis command is only for owner.'
        elif isinstance(error, commands.UserInputError):
            content = f'コマンドの入力が不正です。\nInvalid input.\n`{ctx.command.usage}`'
        elif isinstance(error, commands.BotMissingPermissions):
            content = f'このコマンドを使うにはBotへ以下の権限のください。\n\
                In order to invoke this command, please give me the following permissions\n\
                `{", ".join(error.missing_permissions)}`'
        elif isinstance(error, commands.CheckFailure):
            return

        if content is not None:
            await ctx.send(content, delete_after = 10.0)
            return

        raise error

bot = Bot()

for cog in {
    Lounge,
    Mogi,
    Utility,
    Result,
    HandsUp,
    Admin
}:
    bot.add_cog(cog(bot))


bot.run(config['token'])
