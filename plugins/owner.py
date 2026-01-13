import discord
import logging
import subprocess
import os
import sys

from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from utils.checks import is_potato, is_owner_but_better

logger = logging.getLogger("Potataooo")

class Owner(commands.Cog, name="owner"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.command(
        name="sync",
        description="Synchonizes the slash commands.",
    )
    @app_commands.describe(scope="This is the scope thingy. Can be `global` or `guild`")
    @is_potato()
    async def sync(self, context: Context, scope: str) -> None:
        #Makes slash commands work
        if scope == "global":
            await context.bot.tree.sync()
            embed = discord.Embed(
                description="Slash commands have been updated globally yipiiiie",
                color=0xBEBEFE,
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.copy_global_to(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="I'm pretty sure I updated the slash commands so they work in this server",
                color=0xBEBEFE,
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="noob, you have to say either global or guild!!", color=0xE02B2B
        )
        await context.send(embed=embed)

    @commands.command(
        name="unsync",
        description="Unsynchonizes the slash commands. Why would you ever want thi",
    )
    @app_commands.describe(
        scope="This is the scope thingy. Can be `global`, `current_guild` or `guild`"
    )
    @is_potato()
    async def unsync(self, context: Context, scope: str) -> None:
        if scope == "global": #Unloads slash commands??
            context.bot.tree.clear_commands(guild=None)
            await context.bot.tree.sync()
            embed = discord.Embed(
                description="Slash commands have been globally unsynchronized. Why would you ever wanr this?",
                color=0xBEBEFE,
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.clear_commands(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="Okay fine, Slash commands have been unsynchronized in this guild.",
                color=0xBEBEFE,
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="The scope must be `global` or `guild`.", color=0xE02B2B
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="load",
        description="Load a plugin.",
    )
    @app_commands.describe(plugin="The name of the cog to load")
    @is_potato()
    async def load(self, context: Context, plugin: str) -> None:
        try:
            await self.bot.load_extension(f"plugins.{plugin}")
        except Exception:
            embed = discord.Embed(
                description=f"You broke the `{plugin}` plugins.\nPlease do check the console for errors tho", color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"Successfully loaded the `{plugin}` plugins.", color=0xBEBEFE
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="unload",
        description="Unloads a plugin.",
    )
    @app_commands.describe(plugin="The name of the plugin to unload")
    @is_potato()
    async def unload(self, context: Context, plugin: str) -> None:
        try:
            await self.bot.unload_extension(f"plugins.{plugin}")
        except Exception:
            embed = discord.Embed(
                description=f"You broke the `{plugin}` plugin.\nPlease do check the console for errors tho", color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"Successfully unloaded the `{plugin}` plugin.", color=0xBEBEFE
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="reload",
        description="Reloads a plugin.",
    )
    @app_commands.describe(plugin="The name of the plugin to reload")
    @is_potato()
    async def reload(self, context: Context, plugin: str) -> None:
        try:
            await self.bot.reload_extension(f"plugins.{plugin}")
        except Exception:
            embed = discord.Embed(
                description=f"You broke the `{plugin}` plugin.\nPlease do check the console for errors tho", color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"Successfully reloaded the `{plugin}` plugin.", color=0xBEBEFE
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="say",
        description="The bot will say anything you want.",
    )
    @app_commands.describe(message="The message that should be repeated by the bot")
    @is_potato()
    async def say(self, context: Context, *, message: str) -> None:
        await context.send(message) #pro

    @commands.hybrid_command(
        name="embed",
        description="Same as the say command but in an embed"
    )
    @app_commands.describe(message="The message that should be repeated by the bot")
    @is_potato()
    async def embed(self, context: Context, *, message: str) -> None:
        embed = discord.Embed(description=message, color=0xBEBEFE)
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="reboot",
        description="Replaces the bot process with a new one!",
    )
    @is_potato()
    async def reboot(self, context: Context) -> None:
        embed = discord.Embed(
            description="Rebooting... See you in a bit! (◕‿◕)ﻭ",
            color=0x9C84EF
        )
        await context.send(embed=embed)
        logger.info("Rebooting...")
        await self.bot.database.set_reboot_channel(context.channel.id)
        
        # This gets the path to main.py, very pro
        main_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")
        subprocess.Popen([sys.executable, main_path])
        
        logger.info("Bot is die now..")
        os._exit(0)

    @commands.hybrid_command(
        name="die",
        description="Kills the bot completely.",
    )
    #@commands.is_owner()
    @is_owner_but_better()
    async def die(self, context: Context) -> None:
        embed = discord.Embed(
            description="Goodbye~ (╥﹏╥)",
            color=0xE02B2B
        )
        await context.send(embed=embed)
        logger.info("Bot is die forever")
        await self.bot.close()
        os._exit(0)


    @commands.hybrid_command(
        name="addpotato",
        description="Adds a user to the potato list!",
    )
    @app_commands.describe(user="The user to add")
    #@commands.is_owner()
    @is_owner_but_better()
    async def addpotato(self, context: Context, user: discord.User) -> None:
        await self.bot.database.add_potato(user.id)
        embed = discord.Embed(
            description=f"{user.mention} is now a potatooo!",
            color=0x57F287
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="removepotato",
        description="Removes a user from the potato list.",
    )
    @app_commands.describe(user="The user to remove")
    #@commands.is_owner()
    @is_owner_but_better()
    async def removepotato(self, context: Context, user: discord.User) -> None:
        await self.bot.database.remove_potato(user.id)
        embed = discord.Embed(
            description=f"{user.mention} is a no name now.",
            color=0xE02B2B
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="potatoes",
        description="Lists all potato users!",
    )
    async def potatoes(self, context: Context) -> None:
        potato_ids = await self.bot.database.get_all_potatoes()
        if not potato_ids:
            embed = discord.Embed(
                description="Database is empty, I think you broke somethingg",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        
        potato_list = []
        for i, user_id in enumerate(potato_ids, start=1):
            user = await self.bot.fetch_user(user_id)
            # Use display_name if you want their nickname in the server
            member = context.guild.get_member(user.id)
            name = member.display_name if member else user.name
            potato_list.append(f"{i}. {name} | `{user.id}`")

        embed = discord.Embed(
            title="Potatoooooo",
            description="\n".join(potato_list),
            color=0x57F287
        )
        await context.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(Owner(bot))
