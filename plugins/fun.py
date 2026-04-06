import random

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import Context
from utils.checks import *

# 90% sure this was pasted, I was lazy


class Choice(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.value = None

    @discord.ui.button(label="Heads", style=discord.ButtonStyle.blurple)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.value = "heads"
        self.stop()

    @discord.ui.button(label="Tails", style=discord.ButtonStyle.blurple)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.value = "tails"
        self.stop()


class RockPaperScissors(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(
                label="Scissors", description="You choose scissors.", emoji="✂"
            ),
            discord.SelectOption(
                label="Rock", description="You choose rock.", emoji="🪨"
            ),
            discord.SelectOption(
                label="Paper", description="You choose paper.", emoji="🧻"
            ),
        ]
        super().__init__(
            placeholder="Choose...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        choices = {
            "rock": 0,
            "paper": 1,
            "scissors": 2,
        }
        user_choice = self.values[0].lower()
        user_choice_index = choices[user_choice]

        bot_choice = random.choice(list(choices.keys()))
        bot_choice_index = choices[bot_choice]

        result_embed = discord.Embed(color=0xBEBEFE)
        result_embed.set_author(
            name=interaction.user.name, icon_url=interaction.user.display_avatar.url
        )

        winner = (3 + user_choice_index - bot_choice_index) % 3
        if winner == 0:
            result_embed.description = f"**draw (you still lose tho)**\nyou lost because i said so, we both picked {bot_choice}."
            result_embed.colour = 0xF59E42
        elif winner == 1:
            result_embed.description = f"**omg omgomgomgomg pro**\nI think I lost to your {user_choice} with my {bot_choice}."
            result_embed.colour = 0x57F287
        else:
            result_embed.description = f"**Nooooooooob!**\nShame on you for picking {user_choice} against my {bot_choice}."
            result_embed.colour = 0xE02B2B

        await interaction.response.edit_message(
            embed=result_embed, content=None, view=None
        )


class RockPaperScissorsView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(RockPaperScissors())


class Fun(commands.Cog, name="fun"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="coinflip", description="Worse version of gambling"
    )
    @cooldown("user", 5)
    async def coinflip(self, context: Context) -> None:
        buttons = Choice()
        embed = discord.Embed(description=f"\"This is just a shittier version of my coinflipping bot\"\n-Unarming", color=0xBEBEFE)
        message = await context.send(embed=embed, view=buttons)
        await buttons.wait()  # We wait for the user to click a button.
        result = random.choice(["heads", "tails"])
        if buttons.value == result:
            embed = discord.Embed(
                description=f"omg pro  it was `{result}`!!",
                color=0xBEBEFE,
            )
        else:
            embed = discord.Embed(
                description=f"noob, it's not `{buttons.value}`, it's `{result}`, let's all point fingers and laugh",
                color=0xE02B2B,
            )
        await message.edit(embed=embed, view=None, content=None)

    @commands.hybrid_command(
        name="rps", description="Play the rock paper scissors game against the bot."
    )
    @cooldown("user", 5)
    async def rock_paper_scissors(self, context: Context) -> None:
        view = RockPaperScissorsView()
        await context.send("If the buttons below actually show up I'll be impressed, now go pick!!", view=view)


async def setup(bot) -> None:
    await bot.add_cog(Fun(bot))
