import discord
import logging
import os
import asyncio
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import Context
from datetime import datetime
from collections import deque
from utils.checks import *

# also due for a rewrite, output looks messy but I have no idea how to make it look better
# i will die

class DiscordLogHandler(logging.Handler):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.log_queue = deque(maxlen=100)  # it's not going to fit 100, too lazy to change, I'd rather complain in this comment
        self.last_send = None
        self.batch_task = None
        
    def emit(self, record):
        try:
            log_entry = self.format(record)
            self.log_queue.append({
                'message': log_entry,
                'level': record.levelname,
                'time': datetime.now(),
                'name': record.name
            })
            
            # does the thingy that runs the function in a loop but asyncio
            if self.batch_task is None or self.batch_task.done():
                self.batch_task = asyncio.create_task(self.send_batched_logs())
        except Exception:
            self.handleError(record)
    
    def format_log_line(self, log_msg, level):
        emoji = '📝'  # default thingy if it doesn't match anything below
        
        if 'loaded' in log_msg.lower() or 'ready' in log_msg.lower() or 'connected' in log_msg.lower() or 'initialized' in log_msg.lower() or 'complete' in log_msg.lower():
            emoji = '✅' # yipii
        elif 'loading' in log_msg.lower() or 'starting' in log_msg.lower() or 'connecting' in log_msg.lower():
            emoji = '🔃' # loading stuff
        elif level == 'WARNING':
            emoji = '⚠️' # danger nu
        elif level == 'ERROR':
            emoji = '❌' # bot die
        elif level == 'CRITICAL':
            emoji = '💀' # doubt this ever gets used asw
        elif level == 'DEBUG':
            emoji = '🔍' # doubt this ever gets used
        elif 'executed' in log_msg.lower() or 'command' in log_msg.lower():
            emoji = '⚡' # command executed, 99.5% sure this is broken
        elif 'failed' in log_msg.lower():
            emoji = '❌' # no perms and wtv

            # this did in fact never get used.
        
        # 3 am code ahead
        parts = log_msg.split(' - ', 1)
        if len(parts) == 2:
            # 4 am code ahead
            level_and_name = parts[0].split(': ', 1)
            if len(level_and_name) == 2:
                logger_name = level_and_name[1]
                message = parts[1]
                return f"{emoji} [{logger_name}] -> {message}"
        
        # fallback if my best code ever fails (it never does)
        return f"{emoji} {log_msg}"
    
    async def send_batched_logs(self):
        await asyncio.sleep(5)  # hai, time is here (i keep forgetting)
        
        if not self.log_queue:
            return
            
        channel_id = os.getenv("default-channel") or os.getenv("DEFAULT_CHANNEL")
        if not channel_id:
            return
            
        try:
            channel = await self.bot.fetch_channel(int(channel_id))
            
            # pro
            all_logs = []
            total_logs = len(self.log_queue)
            
            while self.log_queue:
                log = self.log_queue.popleft()
                formatted = self.format_log_line(log['message'], log['level'])
                all_logs.append(formatted)
            
            # if there's any errors it changes the colors to the ones below
            has_error = any('❌' in log or '💀' in log for log in all_logs)
            has_warning = any('⚠️' in log for log in all_logs)
            
            if has_error:
                color = 0xED4245  # reb
            elif has_warning:
                color = 0xFEE75C  # yellooo
            else:
                color = 0x5865F2  # bluuu
            
            # splits the log into smaller parts
            log_text = '\n'.join(all_logs)
            
            # if text is too big, make it smaller!
            if len(log_text) > 4000:
                # even tho i set a limit at the top i still somehow felt the need to add another one here
                display_logs = all_logs[-30:]
                log_text = '\n'.join(display_logs)
                skipped = total_logs - 30
                if skipped > 0:
                    log_text = f"*...{skipped} earlier entries skipped I think*\n\n" + log_text
            
            embed = discord.Embed(
                description=f"```\n{log_text}\n```",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            embed.set_footer(text=f"Collected {total_logs} log entries • That's really pro rite?")
            await channel.send(embed=embed)
                
        except Exception as e:
            print(f"You code is so weird that I can't even log it: {e}")

class DiscordLogging(commands.Cog, name="logging"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.discord_handler = None
        
    async def cog_load(self):
        # Set up Discord logging when cog loads (very important!)
        self.discord_handler = DiscordLogHandler(self.bot)
        self.discord_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '{levelname}: {name} - {message}',
            style='{'
        )
        self.discord_handler.setFormatter(formatter)
        
        # Add handler to the bot's logger (don't ask me wha that means)
        self.bot.logger.addHandler(self.discord_handler)
    
    async def cog_unload(self):
        if self.discord_handler:
            self.bot.logger.removeHandler(self.discord_handler)
            self.bot.logger.info("Discord logging disabled (nuuuu)")

    @commands.hybrid_command(
        name="setlogchannel",
        description="Sets the channel where logs should be sent",
    )
    @app_commands.describe(channel="The channel to send logs to")
    @is_potato()
    async def setlogchannel(self, context: Context, channel: discord.TextChannel) -> None:
        # Updates the environment variable thingy
        os.environ["DEFAULT_CHANNEL"] = str(channel.id)
        
        embed = discord.Embed(
            description=f"Log channel set to {channel.mention}! Logs will go there now yipiiii",
            color=0x57F287
        )
        await context.send(embed=embed)
        self.bot.logger.info(f"Log channel changed to {channel.name} ({channel.id})")

    @commands.hybrid_command(
        name="testlog",
        description="Sends a test log message to check if logging works",
    )
    @is_potato()
    async def testlog(self, context: Context) -> None:
        self.bot.logger.debug("TestLog Command - DEBUG")
        self.bot.logger.info("TestLog Command - INFO")
        self.bot.logger.warning("TestLog Command - WARNING")
        self.bot.logger.error("TestLog Command - ERROR")
        self.bot.logger.critical("TestLog Command - CRITICAL")
        embed = discord.Embed(
            description="Sent test logs. I think",
            color=0xBEBEFE
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="loglevel",
        description="Changes the minimum log level for Discord logging",
    )
    @app_commands.describe(level="The log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    @is_potato()
    async def loglevel(self, context: Context, level: str) -> None:
        level = level.upper()
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        
        if level not in valid_levels:
            embed = discord.Embed(
                description=f"noob, use one of these: {', '.join(valid_levels)}",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        
        if self.discord_handler:
            self.discord_handler.setLevel(getattr(logging, level))
            embed = discord.Embed(
                description=f"Log level set to **{level}**! Very pro rite?",
                color=0x57F287
            )
            await context.send(embed=embed)
            self.bot.logger.info(f"Log level changed to {level}")
        else:
            embed = discord.Embed(
                description="Discord logging isn't enabled... that's weird",
                color=0xE02B2B
            )
            await context.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(DiscordLogging(bot))