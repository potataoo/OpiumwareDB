from discord.ext import commands

class NotAPotato(commands.CheckFailure):
    pass

def is_potato():
    async def predicate(ctx):
        is_potato_user = await ctx.bot.database.is_potato(ctx.author.id)
        if not is_potato_user:
            raise NotAPotato("No potato")
        return True
    return commands.check(predicate)

def is_owner_but_better():
    async def predicate(ctx):
        potatao = 1327710660288708661 # that's me!
        if await ctx.bot.is_owner(ctx.author) or ctx.author.id == potatao:
            return True
        raise commands.NotOwner("You aren't an owner... and definitely not a better one.")
    return commands.check(predicate)