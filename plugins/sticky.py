import discord
import logging
import datetime

from datetime import datetime, timezone
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from utils.checks import *

logger = logging.getLogger("Potataooo")

class Sticky(commands.Cog, name="sticky"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.nothanks: set[int] = set() # what
        # why is this a : instead of a = whar

    async def makethereallyproembed(self, channel: discord.TextChannel, message: str, set_by: int | str, set_at: str | None) -> discord.Embed:
        embed = discord.Embed(
            title="📌 Pinned Message",
            description=message,
            color=0xFFC5D3,
        )
        displayname = str(set_by)
        avatarthing = None

        try:
            member = channel.guild.get_member(int(set_by))
            if member:
                displayname = member.display_name
                avatarthing = member.display_avatar.url
            else:
                whatdidiget = await self.bot.fetch_user(int(set_by))
                displayname = whatdidiget.name
                avatarthing = whatdidiget.display_avatar.url
        except Exception:
            pass

        if set_at:
            try:
                whatisthetime = datetime.strptime(set_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                whatisthetimebutastring = whatisthetime.strftime("%b %d, %Y at %I:%M %p UTC")
            except Exception:
                whatisthetimebutastring = ""
        else:
            whatisthetimebutastring = ""

        embed.set_footer(
            text=f"Pinned by {displayname} · {whatisthetimebutastring}" if whatisthetimebutastring else f"Pinned by {displayname}",
            icon_url=avatarthing or discord.Embed.Empty
        )

        return embed

    @commands.hybrid_group(
        name="sticky",
        description="bleh it's all the message pinning stuff",
        invoke_without_command=True
    )
    @commands.has_permissions(manage_messages=True)
    async def sticky(self, context: Context) -> None:
        embed = discord.Embed(
            title="Hi this is the sticky thingy",
            description=f"""
            this is how u use it:
            `{self.bot.bot_prefix}sticky set <message>` - Sets the message thingy obviouslyy
            `{self.bot.bot_prefix}sticky remove` - removes it ig
            `{self.bot.bot_prefix}sticky info` - what
            """,
            color=0x9CD3F0,
        )
        await context.send(embed=embed)

    @sticky.command(
        name="set",
        description="Adds a sticky message thingy but u need the um manage messages permission thing"
    )
    @app_commands.describe(message="The message thingy which will be put in the channel's bottom I guess")
    @commands.has_permissions(manage_messages=True)
    async def sticky_set(self, context: Context, *, message: str) -> None:
        if not context.guild:
            await context.send("This thingy only works in servers i think because nooo")
            return
        
        old_messageee = await self.bot.database.get_sticky_data(context.channel.id)
        if old_messageee and old_messageee["last_message_id"]:
            try:
                oldthing = await context.channel.fetch_message(old_messageee["last_message_id"])
                await oldthing.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

        embed = await self.makethereallyproembed(channel=context.channel, message=message, set_by=context.author.id, set_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        whatdidisend = await context.channel.send(embed=embed)

        await self.bot.database.set_sticky_message(channel_id=context.channel.id, message=message, set_by=context.author.id, last_message_id=whatdidisend.id)
        logger.info(f"Woah I set a sticky message thingy in #{context.channel.name} ({context.channel.id}) and it was made by {context.author} ({context.author.id}) in {context.guild.name} and I think I had no errors")

        ididit = discord.Embed(
            description = "You set a sticky thingy woah",
            color = 0xFFC5D3
        )
        await context.send(embed=ididit)

    @sticky.command(
        name="remove",
        description="Removes the sticky message thingy from the channel forevaaaaaa",
    )
    @commands.has_permissions(manage_messages=True)
    async def sticky_remove(self, context: Context) -> None:
        if not context.guild:
            await context.send("This thingy only works in servers i think because nooo")
            return
        
        old_messageee = await self.bot.database.get_sticky_data(context.channel.id)
        if not old_messageee:
            await context.send("i don't know of anythign which i could remove")
            return
        
        if old_messageee["last_message_id"]:
            try:
                oldthing = await context.channel.fetch_message(old_messageee["last_message_id"])
                await oldthing.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

        await self.bot.database.remove_sticky_message(context.channel.id)
        logger.info(f"The sticky thingy was removed from #{context.channel.name} ({context.channel.id}) and it was by {context.author} ({context.author.id})")

        ididit = discord.Embed(
            description = "i think u deleted the sticky message thing",
            color = 0xFFC5D3
        )
        await context.send(embed=ididit)

    @sticky.command(
        name="info",
        description="this is so uselesssss",
    )
    async def sticky_info(self, context: Context) -> None:
        if not context.guild:
            await context.send("This thingy only works in servers i think because nooo")
            return
        
        datastuff = await self.bot.database.get_sticky_data(context.channel.id)
        if not datastuff:
            await context.send("I don't think there's much of anything stuck here for now whar")
            return
        
        embed = await self.makethereallyproembed(channel=context.channel, message=datastuff["message"], set_by=datastuff["set_by"], set_at=datastuff["set_at"])
        embed.set_author(name="📌 Bleeeh")
        await context.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.channel.id in self.nothanks:
            return
        
        datastuff = await self.bot.database.get_sticky_data(message.channel.id)
        if not datastuff:
            return
        
        if datastuff["last_message_id"]:
            try:
                lastthingy = await message.channel.fetch_message(datastuff["last_message_id"])
                howoldisthisthing = (discord.utils.utcnow() - lastthingy.created_at).total_seconds()
                if howoldisthisthing < 60: # not so sure if this would make it so it never even runs but wtv
                    return
            except (discord.NotFound, discord.Forbidden):
                pass

        self.nothanks.add(message.channel.id)
        try:
            if datastuff["last_message_id"]:
                try:
                    oldthingy = await message.channel.fetch_message(datastuff["last_message_id"])
                    await oldthingy.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass

            embed = await self.makethereallyproembed(channel=message.channel, message=datastuff["message"], set_by=datastuff["set_by"], set_at=datastuff["set_at"])
            imadethis = await message.channel.send(embed=embed)

            await self.bot.database.update_sticky_last_message(message.channel.id, imadethis.id)
        except discord.Forbidden:
            logger.warning(f"I don't think I have permissions to do hatever in #{message.channel.name} ({message.channel.id}) I don't knwo why")
        except Exception as e:
            logger.error(f"bleh i died and got this when trying to do stuff in {message.channel.id} because of {e}")
        finally: # SINCE WHEN IS THSI A THIGN
            self.nothanks.discard(message.channel.id)

        

async def setup(bot) -> None:
    await bot.add_cog(Sticky(bot))
