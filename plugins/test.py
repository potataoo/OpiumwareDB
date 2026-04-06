from discord.ext import commands
from discord.ext.commands import Context
from utils.checks import *

class Test(commands.Cog, name="testing"):
    def __init__(self, bot) -> None:
        self.bot = bot

    # This cog is just a template.. doesn't do much..
    @commands.hybrid_command(
        name="testcommand",
        description="I've no idea why I have this plugin loaded..",
    )
    async def testcommand(self, context: Context) -> None:
        pass
        # DIE DIE DIE DIE DIE DIE DIE DIE


async def setup(bot) -> None:
    await bot.add_cog(Test(bot))
