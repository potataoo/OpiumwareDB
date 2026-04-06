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
        potatao = 1327710660288708661 # that's me! might actually need to remove this later on or add this to some env
        if await ctx.bot.is_owner(ctx.author) or ctx.author.id == potatao:
            return True
        raise commands.NotOwner("You aren't an owner... and definitely not a better one.")
    return commands.check(predicate)

# Pro cooldown thing I'll probably forget to ever use
def cooldown(bucket_type: str, seconds: int, rate: int = 1):
    # Some examples for myself so I won't forget
    # bucket_type: "user", "guild", "channel", "everyone", or "role"
    # seconds: how long the cooldown lasts
    # rate: how many uses before cooldown kicks in (default 1)
    # @cooldown("user", 10)  # 10 second cooldown per user
    # @cooldown("everyone", 30, rate=3)  # everyone gets 3 uses per 30 seconds
    bucket_map = {
        "user": commands.BucketType.user,
        "guild": commands.BucketType.guild,
        "channel": commands.BucketType.channel,
        "everyone": commands.BucketType.default,
        "role": commands.BucketType.role,
        "member": commands.BucketType.member,
        "category": commands.BucketType.category
    }
    
    bucket = bucket_map.get(bucket_type.lower(), commands.BucketType.user)
    
    async def predicate(ctx):
        # Check if user is a potato
        is_potato_user = await ctx.bot.database.is_potato(ctx.author.id)
        
        if is_potato_user:
            # Potatoes bypass cooldown yipii
            return True
        
        # if not potato, then cooldown
        cooldown_instance = commands.Cooldown(rate, seconds)
        bucket_key = bucket.get_key(ctx)
        
        # whar
        if not hasattr(ctx.command, '_cooldown_mapping'):
            ctx.command._cooldown_mapping = {}
        
        # cooldown thingy check
        if bucket_key in ctx.command._cooldown_mapping:
            retry_after = ctx.command._cooldown_mapping[bucket_key].update_rate_limit()
            if retry_after:
                raise commands.CommandOnCooldown(cooldown_instance, retry_after, bucket)
        else:
            ctx.command._cooldown_mapping[bucket_key] = cooldown_instance
            ctx.command._cooldown_mapping[bucket_key].update_rate_limit()
        
        return True
    
    return commands.check(predicate)