import discord
import logging
import os
import asyncio
from discord.ext import commands
from datetime import datetime
from collections import deque

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
            emoji = '⚡' # command executed
        elif 'failed' in log_msg.lower():
            emoji = '❌' # no perms and wtv
        
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

async def setup(bot) -> None:
    await bot.add_cog(DiscordLogging(bot))