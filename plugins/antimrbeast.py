import discord
import logging
import imagehash
import random
import numpy
import asyncio
import aiohttp
import os
import io
import re


from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord import app_commands
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from PIL import Image
from utils.checks import *
from utils import training

# Okay so huge warning, most of this code barely does anythign
# Just does checks, does wtv with hashes and other stuff but really
# it's not that great, most of it relies on Saba's (@1104433284680798248) implementation (Thank you a lot!!) 
# mostly just looks at the user's history and if they haven't sent a message in a few days then randomly
# send images, it's probably a scam, at best this only adds a few failsafes which honestly aren't even that fast
# it's just a slower, worse and honestly just a bad plugin overall, I would just stop using this and 
# make a better, simpler one, but I keep trying on improving it which never really works out
# though I did learn how numpy works a tiny bit so that's probably useful I guess..
# Might even try to add a 10% chance to force staff to give me training data, not like it's going to do much though, but it would
# at least help a bit I guess I keep wanting to cut my wrists up again and again and againg dsiufhgasdkjlfhasdlkjfchhsadkl;
# well I did work on it a bit more, somehow figured out why others can't click buttons to unban themselves through the bot, apparently it's because
# of them not having any mutual servers with the bot because they're bannned so they can't even do anything with it, I wanted to make it some
# small api which would just unban them if they opened a link but I'm too paranoid of it getting abused, everything web related is my weakness
# i feel like it'd just get abused, I actually want to work on some fun commands instead of whatever this may be, I spent days on this and I still
# only have 2 commands which HALF of it is vibecoded because I don't know how to actually train a model properly, I tried doing research but I'm so bad
# none of it really worked and I hate how this project is filled with these try: statements but 90% of the time I don't even get an error in the console
# or for example it just trains a model for 40+ minutes, silently fails and then I had to look for stuff (I never understood what the problem was)


logger = logging.getLogger("Potataooo")

class UnbanMePleaseThanks(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        logger.error(f"something broke in the unban button and I have absolutely no idea why: {error}", exc_info=error) # no idea why this works
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("Something went wrong.. please contact a staff member!", ephemeral=True)
            else:
                await interaction.followup.send("Something went wrong but worse.. please contact a staff member!", ephemeral=True)
        except Exception:
            pass


    @discord.ui.button(
        label="I've secured my account",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="unbanmepleasethanksbutitsabuttonactuallyno"
    )
    async def confirm_safe(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        try: # trytrytrytrytrytrytrytrytrytrytrytrytrytry
            cog = interaction.client.get_cog("antimrbeast")
            if not cog:
                await interaction.followup.send("Feature seems to be disabled for some reason (broken?) Please contact a staff member thankuu!", ephemeral=True)
                return

            guild_id = await cog.bot.database.get_compromised_guild(interaction.user.id)
            if not guild_id:
                await interaction.followup.send("I don't think ur banned from the server for being compromised I donm't knwooosdfjhksdh", ephemeral=True)
                return

            guild = cog.bot.get_guild(guild_id)
            if not guild:
                await interaction.followup.send("Some random meanie decided it was a good idea to kick me from the serverrrr, can't unban u sorryy", ephemeral=True)
                return
        
            try:
                banthingy = await guild.fetch_ban(interaction.user)
                if not banthingy or not banthingy.reason or not banthingy.reason.startswith("Compromised"):
                    await interaction.followup.send("uuum no thanku", ephemeral=True)
                    return
            except discord.NotFound:
                await cog.bot.database.remove_compromised_account(interaction.user.id)
                await interaction.followup.send("i don't think ur banned but girl whatever I don't knwo", ephemeral=True)
                return

            try:
                await guild.unban(interaction.user, reason="Not compromised anymore apparently")
            except Exception as e:
                logger.error(f"u broke somethingsjdkhfsdkjf I don't know how to unban {interaction.user.id} because of {e}")
                await interaction.followup.send("I couldn't manage to unban you for some reason.. canu please dm a staff member or something", ephemeral=True)
                return
        
            # so many triessdkjfhgsdjfkhd

            await cog.bot.database.remove_compromised_account(interaction.user.id)

            discordinvite = os.getenv("invite")
            await interaction.followup.send(f"Your account has been unblocked! Please join our server back [here]({discordinvite})")

            button.disabled = True
            button.label = "Unbanned"
            await interaction.message.edit(view=self)

            logger.info(f"{interaction.user.id} was unbanned because they're safe nooow yipiiiehfkijsdh")
        except Exception as e:
            logger.error(f"something broke in the unban and I have no idea what or why {e}", exc_info=e)
            try:
                await interaction.followup.send("Something went reeeeeally wreong canu please contact a staff member?", ephemeral=True)
            except Exception:
                pass # I love how many exceptions there are everywhere yet a lot of this is still broken

class YesItsAScamOrActuallyNoItsNotIDontKnow(discord.ui.View):
    def __init__(self, cog, user_id: int, guild_id: int, image_hashes: list[dict], image_file_names: list[str]):
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id
        self.guild_id = guild_id
        self.image_hashes = image_hashes
        self.image_file_names = image_file_names

    def isitastaff(self, interaction: discord.Interaction) -> bool:
        staffroleid = int(os.getenv("staff-role") or 0)
        if not staffroleid:
            return True # I guess anyone is staff if it's not defined, not like this part really matters tho
        return any(role.id == staffroleid for role in getattr(interaction.user, "roles", [])) # whar

    @discord.ui.button(
        label = "Ban",
        emoji = "<:KirbyStar:1393463086802796644>",
        style = discord.ButtonStyle.danger,
    )
    async def itsascam(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.isitastaff(interaction): # Just realised how messed up this codebase is but I'm too lazy to move stuff to utils/checks.py since its old and I'm lazyyyyy
            await interaction.response.send_message("No thanks I don't even knwo who u are tho", ephemeral=True)
            return
        await interaction.response.defer()

        try:
            for hashthingy in self.image_hashes:
                for algo, hashthingybutdifferent in hashthingy.items():
                    await self.cog.bot.database.add_scam_hash(algo, hashthingybutdifferent)
                    self.cog.known_hashes[algo].add(imagehash.hex_to_hash(hashthingybutdifferent))
        except Exception as e:
            logger.error(f"noob u broke something because I don't know how to save a hash {e}")

        for filename in self.image_file_names:
            training.move_image(filename, "pending", "positive")
        try:
            await self.cog.bot.database.update_training_images_label(self.image_file_names, "positive", str(interaction.user.id))
        except Exception as e:
            logger.error(f"Okay so I don't know how to make it move the image and do the label tyhing because of {e}")

        try:
            guild = self.cog.bot.get_guild(self.guild_id)
            if guild:
                banthisguy = guild.get_member(self.user_id) or discord.Object(id=self.user_id) # not sure which one works
                await self.cog.bot.database.add_compromised_account(self.user_id, self.guild_id)
                if isinstance(banthisguy, discord.Member):
                    await self.cog.tellthatnoobthattheydownloadedabitcoinminer(banthisguy, guild.name)
                #await guild.ban(banthisguy, reason=f"Compromised Account - Confirmed by {interaction.user.display_name}", delete_message_seconds=60)
                await guild.ban(banthisguy, reason=f"Compromised Account - Confirmed by {interaction.user.display_name}", delete_message_days=0)
        except Exception as e:
            logger.error(f"Yet another error noob so um fix this, this time it has to do with the mods not being able to ban a user or wtv {e}")

        self.cog.howmanytimesdidiconfirmthis += 1
        if self.cog.howmanytimesdidiconfirmthis % 12 == 0: # it's confusing, just retrains stuff I guess, not that this explaains it any better
            asyncio.create_task(self.cog.retrainbutcool())

        embed = interaction.message.embeds[0]
        embed.color = 0xFF2B2B
        embed.title = "<:KirbyStar:1393463086802796644> User Banned."
        embed.set_author(name=f"Confirmed by {interaction.user}")
        for something in self.children:
            something.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        logger.info(f"Scam confirmed by {interaction.user} ({interaction.user.id}) so he banned {self.user_id} i think and I saved some images to the DB")

    @discord.ui.button(
        label = "Keep",
        emoji = "<:thumbs:1454731387256180795>",
        style = discord.ButtonStyle.success
    )
    async def nopnotscam(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.isitastaff(interaction): # guess whewre it pasted this from (20 lines above or something)
            await interaction.response.send_message("No thanks I don't even knwo who u are tho", ephemeral=True)
            return
        await interaction.response.defer()

        for filename in self.image_file_names:
            training.move_image(filename, "pending", "negative")
        try:
            await self.cog.bot.database.update_training_images_label(self.image_file_names, "negative", str(interaction.user.id))
        except Exception as e:
            logger.error(f"Girl whatever I'm sick of these exceptions {e}")

        self.cog.howmanytimesdidiconfirmthis += 1
        if self.cog.howmanytimesdidiconfirmthis % 12 == 0: # it's confusing, just retrains stuff I guess, not that this explaains it any better
            asyncio.create_task(self.cog.retrainbutcool())


        embed = interaction.message.embeds[0]
        embed.color = 0x80FF80
        embed.title = "<:thumbs:1454731387256180795> User has been spared!"
        embed.set_footer(text=f"{interaction.user} can vouch.")
        for something in self.children:
            something.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        logger.info(f"False positive I guess or something well I guess the {interaction.user} thingy ({interaction.user.id}) thought that {self.user_id} was safe")

class AntiMrBeast(commands.Cog, name="antimrbeast"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.last_seen: dict[int, datetime] = {} # why woudl this EVER be a dictionary :sob:
        self.known_hashes: dict[str, set] = {
            "phash": set(),
            "dhash": set(),
            "ahash": set(),
            "chash": set(),
        }
        self.model_session = None
        self.model_version = 0
        self.howmanytimesdidiconfirmthis = 0
        self.recent_hashes: dict[str, tuple[datetime, int]] = {}
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="antimrbeast") # EXECUTOR OMG OMGOMGOMGODFNMGKDFNGKDFJNG AAAAASJFHSDJFLKHB
        self.semaphore = asyncio.Semaphore(4) # all this does is just set limits and add more workers or wtv so it uses ur pc more

    async def cog_load(self):
        self.bot.add_view(UnbanMePleaseThanks())

        training.makesurethedirsarereal()
        await self.loadscamhashesfromyourwhatever()
        woah = asyncio.get_event_loop()
        self.model_session = await woah.run_in_executor(None, training.loadsomemodel)
        if self.model_session:
            self.model_version = training.newestmodelversion()
        self.cleaneverything.start()
        positives, negatives = training.whatdoihave()
        
        logger.info(f"Okay so I have v{self.model_version} of the model and it is {'ready' if self.model_session else 'BROKENSKDFJHSDF'}! I also have {positives} positive and {negatives} images that I know of")

    async def cog_unload(self): # not sure if it's really ever going to be unloaded tho
        self.cleaneverything.cancel()
        self.executor.shutdown(wait=False)

    @tasks.loop(hours=1)
    async def cleaneverything(self):
        now = discord.utils.utcnow()
        self.recent_hashes = { # what am i reading I did NOT write this what what is this
            something: hash for something, hash in self.recent_hashes.items()
            if (now - hash[0]).total_seconds() < 60
        }

        try:
            oldstuff = await self.bot.database.get_expired_pending_images(7)
            for filename in oldstuff:
                training.delete_image(filename, "pending")
                await self.bot.database.delete_training_image(filename)
            if oldstuff:
                logger.info(f"I deleted {len(oldstuff)} old stuff because it was old and um u took too long")
        except Exception as e:
            logger.error(f"Cleanup thingy blew up {e}")

    async def loadscamhashesfromyourwhatever(self):
        try:
            hashthings = await self.bot.database.get_all_scam_hashes()
            for algo, hash in hashthings:
                if algo in self.known_hashes and algo != "chash": # thanks sql or something, the db broke because color hashes can't just work for some rteason i hateu
                    self.known_hashes[algo].add(imagehash.hex_to_hash(hash)) # top tier grade military technology encryption
        except Exception as e:
            logger.error(f"ur db broke again nooob bleh {e}")

    async def retrainbutcool(self):
        positives, negatives = training.whatdoihave()

        if positives + negatives < 128:
            logger.info(f"Okii so um I was going to retrain the model thingy thing but I only have {positives + negatives}/128 examples so no thanku")
            return
        logger.info(f"Decided it was a good idea to start training myself yet again because I have {positives + negatives} examples (Pro - {positives}, Noob - {negatives})")
        try:
            woah = asyncio.get_event_loop()
            result = await woah.run_in_executor(self.executor, training.train_model)
            newmodelbecause = await woah.run_in_executor(None, training.loadsomemodel, result['version'])
            if newmodelbecause:
                self.model_session = newmodelbecause
                self.model_version = result["version"]
                await self.bot.database.add_model_version(result['version'], result['accuracy'], result['train_n'], result['n'], result['positives'], result['negatives'], "auto")
                logger.info(f"Wooooooooahh I upgraded to v{result['version']} noow! And apparently my accuracy is {result['accuracy']} but I took {result['elapsed']:.2f} seconds")
        except Exception as e:
            logger.error(f"okay so u don't know how to make it automatically do stuff noob {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        author = message.author
        now = discord.utils.utcnow()

        # free pass because staff is cool
        if any(role.id == int(os.getenv("staff-role") or 0) for role in getattr(author, "roles", [])):
            self.last_seen[author.id] = now
            return
                
        last_seen = self.last_seen.get(author.id)

        if last_seen is None:
            last_seen = await self.getlastseenfrommessagehistoryorsomething(message)

        self.last_seen[author.id] = now # no idea why this is like that too lazy to fix or remove

        if last_seen is None:
            return
        
        daysbutpro = (now - last_seen).days
        if daysbutpro < 0: # don't forget to change me later on or I'd get almost everyone banned okay thasnks (0 for testing and the 3 was saba's reomcendadsrf)
            return
        
        image_count = sum(1 for attachment in message.attachments if attachment.content_type and attachment.content_type.startswith("image/"))

        if image_count < 2:
            return

        async with self.semaphore:
            await self.scanthisnoobsmessage(message, image_count, daysbutpro)

    async def scanthisnoobsmessage(self, message: discord.Message, image_count: int, daysbutpro: int):
        images = [attachments for attachments in message.attachments if attachments.content_type and attachments.content_type.startswith("image/")]

        imagedata: list[tuple[str,bytes]] = [] # thanks github
        # async with aiohttp.ClientSession() as session: # nvm no thanks github it broke everything
        #     for attachment in images:
        #         try:
        #             async with session.get(attachment.url, timeout=aiohttp.ClientTimeout(total=6)) as resp: # thanks github again
        #                 if resp.status == 200:
        #                     imagedata.append((attachment.filename, await resp.read()))
        #         except Exception:
        #             pass
        for attachment in images:
            try:
                data = await attachment.read()
                imagedata.append((attachment.filename, data))
            except Exception:
                pass

        if not imagedata:
            logger.warning(f"I was going to scan this guy's images {message.author.id} but I don't um they just what they disappeared")
            return
    
        loop = asyncio.get_event_loop()
        hashes: list[dict] = [] # WHY DOES IT HJAVE TO HAVE A : DFKJLHSDFLDESFJH
        hashfound = False
        isitinmultiplechannels = False
        now = discord.utils.utcnow()
        whatdoesthemodelthink: list[float] = []

        for something, data in imagedata:
            try:
                hashthing = await loop.run_in_executor(self.executor, self.thinkofahash, data)
                if hashthing is None:
                    hashes.append({})
                    continue
                
                hashthingies = {}
                for algo, hash in hashthing.items():
                    if hash is None:
                        continue
                    hashthingy = str(hash)
                    hashthingies[algo] = hashthingy

                    grokisthisreal = self.recent_hashes.get(hashthingy)
                    if grokisthisreal and (now - grokisthisreal[0]).total_seconds() <= 5 and grokisthisreal[1] != message.channel.id:
                        isitinmultiplechannels = True

                    self.recent_hashes[hashthingy] = (now, message.channel.id)

                    hashthrestholds = {"phash": 10, "dhash": 10, "ahash": 10, "chash": 3}
                    if any(abs(hash - iknowthis) <= hashthrestholds.get(algo, 10) for iknowthis in self.known_hashes[algo]):
                        hashfound = True

                hashes.append(hashthingies)
            except Exception:
                hashes.append({})

        if self.model_session and not hashfound and not isitinmultiplechannels:
            for something, data in imagedata:
                try:
                    think = await loop.run_in_executor(self.executor, training.predict, self.model_session, data)
                    whatdoesthemodelthink.append(think)
                except Exception:
                    pass

        howconfidentcanibe = max(whatdoesthemodelthink) if whatdoesthemodelthink else None

        if isitinmultiplechannels:
            await self.banthisnoob(message, f"Compromised Account - {daysbutpro}d inactive, sent same images in multiple channels in like 5 seconds", imagedata, hashes)
        elif hashfound and random.random() > 0.10:
            await self.banthisnoob(message, f"Compromised Account - {daysbutpro}d inactive, image matched a known hash in the DB", imagedata, hashes)
        elif howconfidentcanibe is not None and howconfidentcanibe >= 0.85 and random.random() > 0.10:
            await self.banthisnoob(message, f"Compromised Account - {daysbutpro}d inactive - {howconfidentcanibe:.0%} Confidence.", imagedata, hashes)
        elif hashfound or (howconfidentcanibe is not None and howconfidentcanibe >= 0.15) or self.model_session is None:
            await self.sendtomods(message, hashes, image_count, daysbutpro, imagedata, howconfidentcanibe)

    def thinkofahash(self, imagebytes: bytes) -> dict | None:
        try:
            image = Image.open(io.BytesIO(imagebytes)).convert("RGB")
            return {
                "phash": imagehash.phash(image),
                "dhash": imagehash.dhash(image),
                "ahash": imagehash.average_hash(image),
                "chash": imagehash.colorhash(image, binbits=3)
            }
        except Exception:
            return None

    async def sendtomods(self, message: discord.Message, hashes: list[dict], image_count: int, daysbutpro: int, imagedata: list, confidence: float | None): # what even is a tuple
        defaultchannel = os.getenv("antimrbeastchannel")
        if not defaultchannel:
            return
        
        try:
            channel = await self.bot.fetch_channel(int(defaultchannel))
        except Exception:
            logger.error("I don't knwo but the mrbeast channel is die or something")
            return
        
        try:
            await message.delete()
        except Exception:
            pass
    
        filenames: list[str] = []
        for file, (filename, data) in enumerate(imagedata):
            iknowthis = training.save_image(data, "pending")
            if iknowthis:
                filenames.append(iknowthis)
                hashthings = hashes[file] if file < len(hashes) else {}
                try:
                    await self.bot.database.add_training_image(iknowthis, "pending", hashthings.get("phash"), hashthings.get("dhash"), hashthings.get("ahash"), hashthings.get("chash"), confidence)
                except Exception as e:
                    logger.error(f"I don't knmow hwo to ad that training image to the DB because of {e}")

        confidencebutpro = f"{confidence:.0%}" if confidence is not None else "I don't know"
        howmanyhashes = sum(len(hashthings) for hashthings in hashes)

        embed = discord.Embed(
            title = "Okii so I think this is some compromised account",
            description=(
                f"So this guy {message.author.mention} came back after **{daysbutpro}** days of pure silence and\n"
                f"Immediately decided that it was a good idea to send **{image_count}** images\n\n"
                f"So i think my confidence is `{confidencebutpro}` and\n"
                "None of this really matched the hashes I made so um canu solve this captcha for me thanks okiiii\n"
                "I also deleted that message if that matters"
            ),
            color = 0xEEEE55,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="User", value=f"{message.author}\n`{message.author.id}`", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Hashes", value=f"I thought of {howmanyhashes} of them", inline=True)
        embed.set_footer(text="Help meeeeeeeeeeeeee")
        files = [discord.File(io.BytesIO(data), filename=filename) for filename, data in imagedata]
        view = YesItsAScamOrActuallyNoItsNotIDontKnow(self, message.author.id, message.guild.id, hashes, filenames)
        try:
            await channel.send(embed=embed, files=files or None, view=view) # truly magnificent
        except Exception as e:
            logger.error(f"i don't know how to send messagews because of {e}")
        logger.info(f"This might just be some compromised account and I sent it to the mod queue I think so um he is {message.author} ({message.author.id}), {image_count} images, {confidencebutpro} confidence.")

    async def banthisnoob(self, message: discord.Message, reason: str, imagedata: list = None, hashes: list = None):
        try:
            await message.delete()
        except Exception:
            pass # I'm honestly so so so so SO SO SOIASFJHGSBDFKJ SO sick of these try: and except Exception thingies I will cry

        try:
            await self.bot.database.add_compromised_account(message.author.id, message.guild.id)
            await self.tellthatnoobthattheydownloadedabitcoinminer(message.author, message.guild.name)
            #await message.guild.ban(message.author, reason=reason, delete_message_seconds=60)
            await message.guild.ban(message.author, reason=reason, delete_message_days=0)
            logger.info(f"Banned some random mrbeast probably I think I don't knwoo {message.author} ({message.author.id}) because they um {reason}")
        except Exception as e:
            logger.error(f"I don't know how to ban them because of {e} so umm yea they'll stay but they are {message.author} ({message.author.id})")
            return
        
        self.last_seen.pop(message.author.id, None)
        logger.warning(f"Managed to ban some random account yippiee! {message.author} ({message.author.id}) in #{message.channel.name} for {reason}")

    async def getlastseenfrommessagehistoryorsomething(self, message: discord.Message) -> datetime | None:
        try:
            async for msg in message.channel.history(limit=10, before=message.created_at):
                if msg.author.id == message.author.id:
                    logger.debug(f"Managed to find some messages from {message.author.id} in the search thingy")
                    return msg.created_at
        except Exception as e:
            logger.error(f"I didn't know how how to search for messages")
            return None

    async def tellthatnoobthattheydownloadedabitcoinminer(self, user: discord.User, guild_name: str):
        embed = discord.Embed(
            title = ":warning: Account Compromised?",
            description=(
                f"Okay so um hii {user.display_name}..\n\n"
                "I'll probably just get straight to the point and tell you that your account might be compromised.\n"
                "If you're **100%** sure that you and your system is safe, then please read what's below.\n\n"
                "I've seen you send something which looked like scam images and I just don't want that in our server.\n"
                f"That's why I've banned you from **{guild_name}**, but for now I need you to do this:\n"
                "1. Change ALL of your passwords for ALL of your accounts (Takes a day, saves your life)\n"
                "2. Reset your system, malware tends to stay on it even after your accounts get stolen.\n"
                "3. Please never trust random links/scripts/applications sent by people you don't trust.\n"
                "4. And as always, take everything on the internet with a pinch of salt.\n\n"
                f"That being said, you can unban yourself from {guild_name} by clicking the button below."
            ),
            color=0xFFC5D3
        )
        try:
            await user.send(embed=embed, view=UnbanMePleaseThanks())
        except discord.Forbidden:
            logger.info(f"Well um.. Not much of anything we could do about that.. {user.display_name} has their DMs closed so I couldn't send them their only change to get unbanned nooo")

    @commands.hybrid_command(
        name="adddata",
        description="Add some training data for the model thing"
    )
    @app_commands.describe(label="Positive (It's a scam) and Negative (It's normal)")
    @is_potato()
    async def adddata(self, context: Context, label: str) -> None:
        label = label.lower().strip()
        if label not in ("positive", "negative"):
            embed = discord.Embed(title="Noob..", description="It can either be `Positive` (It's a scam) or `Negative` (It's normal) stupi", color=0xE02B2B)
            await context.send(embed=embed)
            return
        
        images: list[str] = [
            attachment.url for attachment in context.message.attachments
            if attachment.content_type and attachment.content_type.startswith("image/")
        ]
        images += re.findall(r"https?://\S+", context.message.content)

        if not images:
            embed = discord.Embed(title="Bleeeeeh", description="I can't see any imagessasfkjsdh at least upload them in the message I guess", color=0xE02B2B)
            await context.send(embed=embed)
            return
        
        howmanydoiknow = 0
        what = asyncio.get_event_loop()

        async with aiohttp.ClientSession() as session:
            for url in images:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status != 200:
                            continue
                        whatever = response.content_type or ""
                        if "image" not in whatever and not url.lower().endswith((".png", ".jpg", ".jpeg", ".webp")): # 90% sure it's useless and that discord.py has a weird way of doing it beter
                            continue
                        data = await response.read()
                except Exception:
                    continue

                filename = training.save_image(data, label)
                if not filename:
                    continue

                hashotherthing = await what.run_in_executor(self.executor, self.thinkofahash, data)
                phash = str(hashotherthing["phash"]) if hashotherthing else None
                dhash = str(hashotherthing["dhash"]) if hashotherthing else None
                ahash = str(hashotherthing["ahash"]) if hashotherthing else None
                chash = str(hashotherthing["chash"]) if hashotherthing else None
                try:
                    await self.bot.database.add_training_image(filename, label, phash, dhash, ahash, chash, None)
                except Exception as e:
                    logger.error(f"dsfkjlhnsbdlfkjshgfkjldsjbhf db broken db broken db broken nooooo {e}")
                howmanydoiknow += 1

        positives, negatives = training.whatdoihave()
        total = positives + negatives
        howmanydoineed = max(0, 128 - total)

        embed = discord.Embed(
            title="Woah new images thanks",
            description=(
                f"I think I saved **{howmanydoiknow}** images as **{label}** training data yippii\n\n"
                f"**{positives}** positive / **{negatives}** negative\n"
                + (f"\n\nI still need **{howmanydoineed}** examples before I can leanr because otherwise I' stupid" # messiest thing ever
                if howmanydoineed > 0 else
                    "\n\n**Ready to train!** Canu type in the `trainmodel` command thanks") # doesn't even exist as of writing this noo
            ),
            color=0xFFC5D3
            )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="trainmodel",
        description="no more mrbeast in ur server"
    )
    @is_potato()
    async def trainmodel(self, context: Context) -> None:
        positives, negatives = training.whatdoihave()
        total = positives + negatives

        if total < 128:
            await context.send(f"nooo i don't have enough data i'll probably do random stuff because I need at least 128 files worth of sorted data but I only have {total} dataaajhfghsd")
            return
        
        embed = discord.Embed(
            title="Learning stuff",
            description=f"Okii so I know **{positives}** positives and {negatives} negatives ",
            color=0xFFC5D3,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="What am I doing", value="figuring stuff out wait", inline=False)
        whatamidoing = await context.send(embed=embed)

        woah = asyncio.get_event_loop()

        def dotheupdatethingbutitsinafunctionbecausegithubtoldmeto(epoch, howmanyepochs, loss, trainingaccuracy, accuracy, howmuchtimepassed, eta):
            async def dotheupdatething():
                try:
                    embed = discord.Embed(
                        title="Learning stuff",
                        color=0xFFC5D3,
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(name="How much did I do", value=f"{epoch}/{howmanyepochs} epochs", inline=False)
                    embed.add_field(name="What did I lose", value=f"{loss:.2f}", inline=True) # having to use a whole f string is cruel just because I want that :.2f
                    embed.add_field(name="some random training accuracy", value=f"{trainingaccuracy:.2f}", inline=True)
                    embed.add_field(name="some random other accuracy", value=f"{accuracy:.2f}", inline=True)
                    embed.add_field(name="how long am i taking", value=f"{howmuchtimepassed} seconds i think", inline=True)
                    embed.add_field(name="ETA", value=f"{eta} seconds i think", inline=True)
                    await whatamidoing.edit(embed=embed)
                except Exception:
                    pass
            asyncio.run_coroutine_threadsafe(dotheupdatething(), woah)

        try:
            result = await woah.run_in_executor(self.executor, lambda: training.train_model(dotheupdatethingbutitsinafunctionbecausegithubtoldmeto))
        except Exception as e:
            await whatamidoing.edit(content="i broke")
            logger.error(f"training blew up {e}")
            return
        
        promodel = await woah.run_in_executor(None, training.loadsomemodel, result["version"])
        if promodel:
            self.model_session = promodel
            self.model_version = result["version"]
        try:
            await self.bot.database.add_model_version(result["version"], result["accuracy"], result["train_n"], result["n"], result["positives"], result["negatives"], str(context.author.id))
            # I hate how I vibecoded this tiny thing and now all of the variable names are inconsistent so like I can't even tell if I should've used val_n or n for example i hate itt
            # these lines are also so long and annoyinbfdjksbf
            # managed to fix it up a little bit yippii
        except Exception as e:
            logger.error(f"u broke this 50 times already istg {e}")

        embed = discord.Embed(
            title=f"oki so i finished model v{result["version"]}",
            color = 0xFFC5D3,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Accuracy", value=f"{result["accuracy"]:.1%}", inline=True)
        embed.add_field(name="Examples", value=f"{result["train_n"]}", inline=True)
        embed.add_field(name="Other thing", value=f"{result["n"]} examples", inline=True)
        embed.add_field(name="What do I know", value=f"{result["positives"]} positive / {result["negatives"]} negative / {(result["positives"] + result["negatives"])} total", inline=True)
        embed.add_field(name="Time thing", value=f"{result["elapsed"]}", inline=True)
        await whatamidoing.edit(embed=embed)
        logger.info(f"i trained some model and it probably works, it's v{result["version"]} and {context.author} trained it")



async def setup(bot) -> None:
    await bot.add_cog(AntiMrBeast(bot))
