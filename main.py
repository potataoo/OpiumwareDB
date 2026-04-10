#This imports things
import json
import logging
import os
import platform
import random
import sys
import signal
import asyncio

#Even more!
import aiosqlite
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv
from utils.checks import *

from database import DatabaseManager

load_dotenv()

intents = discord.Intents.all()
#I don't think I really even need all of the intents, I just don't want things to break..

#This logs things! Mostly stolen.. (not cool!)
class LoggingFormatter(logging.Formatter):
    # Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("Potataooo")
#logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG) # stuff broke.

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())
# File handler
file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

# Add the handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)


class Potatao(commands.Bot):
    def __init__(self) -> None:
        prefix = os.getenv("PREFIX") or os.getenv("prefix") or "."
        super().__init__(
            command_prefix=commands.when_mentioned_or(prefix),
            intents=intents,
            help_command=None,
        )
        self.logger = logger
        self.database = None
        self.bot_prefix = prefix  # Store the actual prefix used
        self.invite_link = os.getenv("invite") or os.getenv("INVITE")

    # Makes the db work!
    async def init_db(self) -> None:
        async with aiosqlite.connect(
            f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
        ) as db:
            with open(
                f"{os.path.realpath(os.path.dirname(__file__))}/database/schema.sql",
                encoding = "utf-8"
            ) as file:
                await db.executescript(file.read())
            await db.commit()

    # Only runs on startup, makes all of the cogs load up!
    # Cogs = Plugins, I'm too used to ittt
    async def load_cogs(self) -> None:
        for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/plugins"):
            if file.endswith(".py"):
                plugin = file[:-3]
                try:
                    await self.load_extension(f"plugins.{plugin}")
                    self.logger.info(f"Loaded plugin '{plugin}'")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    self.logger.error(
                        f"Failed to load plugin {plugin}\n{exception}"
                    )

    # Goes through this list thingy and picks a random status every minute
    @tasks.loop(minutes=1.0)
    async def status_task(self) -> None:
        statuses = ["Opium Overose", "Skidding more sUNC", "Pasting leaked source", "Running away from bytedancer", "CEO @ Palantir", "Removing rats", " Sponsored by https://claude.ai/"]
        await self.change_presence(activity=discord.Game(random.choice(statuses)))
        # This pretty much broke after discord replaced the "Playing <Status>" thingy with
        # The controller icon thingy so now it's weeeeeird

    # Makes sure the bot works before running the status changer thingy
    @status_task.before_loop
    async def before_status_task(self) -> None:
        await self.wait_until_ready()

    # This thingy runs when the bot fully loads I think
    async def on_ready(self) -> None:
        logger.info("Initialized.") #big word
        embed = discord.Embed(title="Potatao is alive nwooo!",description="All systems operational (very cool)",color=0x57F287,timestamp=discord.utils.utcnow())
        embed.add_field(name="Bot Info",value=f"**Name:** {self.user.name}\n"f"**ID:** {self.user.id}\n"f"**Discriminator:** {self.user.discriminator}",inline=True)  
        embed.add_field(name="Version Info",value=f"**Discord.py:** {discord.__version__}\n"f"**Python:** {platform.python_version()}\n"f"**Prefix:** `{self.bot_prefix}`",inline=True)
        embed.add_field(name="System Info",value=f"**OS:** {platform.system()} {platform.release()}\n"f"**Platform:** {platform.platform()}\n"f"**Architecture:** {platform.machine()}",inline=True)
        embed.add_field(name="Server Stats",value=f"**Guilds:** {len(self.guilds)}\n"f"**Users:** {len(self.users)}\n"f"**Channels:** {sum(len(guild.channels) for guild in self.guilds)}",inline=True)
        embed.add_field(name="Connection",value=f"**Latency:** {round(self.latency * 1000)}ms\n"f"**Intents:** {len([i for i in discord.Intents.all() if getattr(self.intents, i[0])])} enabled",inline=True)
        embed.add_field(name="Loaded Plugins",value=f"**Count:** {len(self.cogs)}\n"f"**Names:** {', '.join(self.cogs.keys())}",inline=False)
        embed.set_footer(text=f"Running on {os.name}")
        #Very pro embed
        reboot_channel_id = await self.database.get_reboot_channel()
        if reboot_channel_id:
            await self.database.clear_reboot_channel()
            try:
                channel = await self.fetch_channel(reboot_channel_id)
                await channel.send(embed=embed)
            except Exception as e:
                self.logger.error(f"Couldn't send reboot message: {e}")
        else:
            default_channel_id = os.getenv("default-channel") or os.getenv("DEFAULT_CHANNEL")
            if default_channel_id:
                try:
                    channel = await self.fetch_channel(int(default_channel_id))
                    await channel.send(embed=embed)
                except Exception as e:
                    self.logger.error(f"Couldn't send startup message: {e}")

    # Runs every time the bot launches
    async def setup_hook(self) -> None:
        self.logger.info(f"That's me!! - {self.user.name}")
        self.logger.info(f"My API is on version: {discord.__version__}")
        self.logger.info(f"My Python version: {platform.python_version()}")
        self.logger.info(
            f"I'm Running on: {platform.system()} {platform.release()} ({os.name})"
        )
        self.logger.info("-------------------") # This line is critical to the bot, without it, performance drops by 50%
        await self.init_db()

        self.database = DatabaseManager(
            connection=await aiosqlite.connect(
                f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
            ) # Not deleting this file would be greatly appreciated
        )    

        await self.load_cogs()
        self.status_task.start()


    # This thingy runs every time the bot reads a message
    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_completion(self, context: Context) -> None:
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        if context.guild is not None:
            self.logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
            )
        else:
            self.logger.info(
                f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
            )

    # Error handler!
    async def on_command_error(self, context: Context, error) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                description=f"**I'm not that fast!** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed, delete_after=5)  # dies after 5 seconds nuuuuu
        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                description="Nuuuuuuuuu!", color=0xE02B2B
            )
            await context.send(embed=embed)
            if context.guild:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot."
                )
            else:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the bot's DMs, but the user is not an owner of the bot."
                )
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="Uuum, you need these thingies: `"
                + ", ".join(error.missing_permissions)
                + "` Or else I don't think I can really help you.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="I think I need these to function: `"
                + ", ".join(error.missing_permissions)
                + "` Someone give me free things!!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Nooooo! Big scary error!",
                # not pro
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, NotAPotato):
            embed = discord.Embed(
                description="Who are youuu",
                color=0xE02B2B
            )
            logger.info(f"{context.author} tried to execute a command but didn't have permission tooo")
            await context.send(embed=embed)
        else:
            raise error # Just prints it to the console if it can't find anything in this list thingy

# Nuuuuu bot is die
def force_shutdown(sig, frame):
    logger.info("Potatao went to eep")
    os._exit(0) # I'm

signal.signal(signal.SIGINT, force_shutdown)

# Runs the bot
async def main():
    async with bot:
        await bot.start(os.getenv("TOKEN")) # Reeeally scary!

bot = Potatao()

if __name__ == "__main__":
    asyncio.run(main())