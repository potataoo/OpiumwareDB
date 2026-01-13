import discord
import logging
import json
import os
import warnings
import time
import shutil
import re
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from setfit import SetFitModel, SetFitTrainer
from datasets import Dataset
from utils.checks import *

logger = logging.getLogger("Potataooo")

# Hide those annoying deprecation warnings (very pro)
warnings.filterwarnings("ignore", category=DeprecationWarning)

class Dupes(commands.Cog, name="dupes"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.model = None
        self.model_path = "data/dupe_model"
        self.config_path = "data/dupe_responses.json"
        self.executor = ThreadPoolExecutor(max_workers=2)  # for async ml stuff
        self.model_loading = False  # so we know if it's still loading
        
        # tries to load a config if it's even there at all
        self.load_config()
        
        # Load model async so it doesn't block startup
        asyncio.create_task(self._load_model_async())
    
    async def _load_model_async(self):
        # tries to find an existing trained model (but async now so it's not blocking yipii)
        if os.path.exists(self.model_path):
            try:
                self.model_loading = True
                logger.info("Loading model in background...")
                # Run the blocking model load in thread pool so it doesn't freeze everything
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(
                    self.executor,
                    SetFitModel.from_pretrained,
                    self.model_path
                )
                logger.info("Loaded model successfully.")
                self.model_loading = False
            except Exception as e:
                logger.error(f"Nunuuuuuuu bad code, couldn't load model because of {e}") # {e} -enough to make a grown girl cry.
                self.model = None
                self.model_loading = False
        else:
            logger.warning("No model found. Use .trainmodel to create one") # noob
    
    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info("Loaded responses config successfully.")
        else:
            # Default config (istg change these channel IDs)
            self.config = {
                "categories": {
                    "dupe_request": {
                        "title": "Nuuuuu!",
                        "description": "Even though this defo is a duping server we still don't allow begging for dupes in here.",
                        "channel_id": 123456789,
                        "channel_text": "beg for dupes here I guess",
                        "color": 0xE02B2B
                    },
                    "ui_utils_request": {
                        "title": "Looking for UI-Utils?",
                        "description": "UI-Utils is available here: https://example.com/ui-utils",
                        "channel_id": None,
                        "channel_text": None,
                        "color": 0x9C84EF
                    },
                    "addon_request": {
                        "title": "Addon Resources",
                        "description": "Check out our addon resources channel for downloads!",
                        "channel_id": 987654321,
                        "channel_text": "addon downloads",
                        "color": 0x57F287
                    },
                    "general_help": {
                        "title": "Need Help?",
                        "description": "Please read our rules and guides first!",
                        "channel_id": 111111111,
                        "channel_text": "rules",
                        "color": 0xFEE75C
                    }
                },
                "rules_channel_id": 123456789,
                "ignored_channels": [],
                "allowed_roles": [],
                "cooldown_seconds": 60,
                "delete_after_seconds": 15, # pro
                "buzzwords": [], # even more pro
                "label_mapping": {
                    "0": "not_request",
                    "1": "dupe_request",
                    "2": "ui_utils_request", 
                    "3": "addon_request",
                    "4": "general_help"
                }
            }
            # creates the data dir if Someone were to accidentally nuke /data again
            os.makedirs("data", exist_ok=True)
            self.save_config()
        
        # i forgot to add this 4 times.
        self.cooldowns = {}
    
    def save_config(self): # saves the config if you edit anything with commands
        with open(self.config_path, 'w') as f:
            json.dump(self.config, indent=2, fp=f)
        logger.info("Saved dupe responses config successfully.")
    
    def is_on_cooldown(self, user_id: int) -> bool:
        # this thingy is mostly so the bot doesn't spam that much, also to save my precious cpu cycles
        if user_id not in self.cooldowns:
            return False
        
        elapsed = time.time() - self.cooldowns[user_id]
        return elapsed < self.config.get("cooldown_seconds", 60)
    
    def set_cooldown(self, user_id: int):
        # I wonder how many cves are in here
        self.cooldowns[user_id] = time.time()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return # i hate u mee6
        if not message.content:
            return # I wonder if this part does anything at all, surely you can't send a message with no text.. right?
        
        if self.model is None:
            return # Pretty much makes everything after this useless if there isn't a trained bot loaded
        
        # ignores channels (ego inflation)
        ignored_channels = self.config.get("ignored_channels", [])
        if message.channel.id in ignored_channels:
            return
        
        # Check role restrictions (if any)
        allowed_roles = self.config.get("allowed_roles", [])
        if allowed_roles and isinstance(message.author, discord.Member):
            user_role_ids = [role.id for role in message.author.roles]
            if not any(role_id in allowed_roles for role_id in user_role_ids):
                return
        
        # Check cooldown
        if self.is_on_cooldown(message.author.id):
            logger.debug(f"{message.author} is on cooldown, saving cpu cycles...")
            return

        # Checks if the message contains specific buzzwords before bothering the model
        buzzwords = self.config.get("buzzwords", [])
        if buzzwords:
            # a regex or statement with WORD BOUNDARIES so "mode" doesn't match "mod" anymore yipii
            pattern = r'\b(' + '|'.join(re.escape(t) for t in buzzwords) + r')\b'
            # if it doesn't match regex, ignore (i really hope this doesn't come back to haunt me later on)
            if not re.search(pattern, message.content, re.IGNORECASE):
                return
        
        try:
            # Predict category (very pro ai stuff) but async now so it doesn't freeze
            loop = asyncio.get_event_loop()
            prediction = await loop.run_in_executor(
                self.executor,
                lambda: self.model.predict([message.content])[0]
            )
            # Convert tensor to int if needed
            if hasattr(prediction, 'item'):
                prediction = prediction.item()
            category = self.config["label_mapping"].get(str(prediction))
            
            # If it's not a request, ignore
            if category == "not_request" or category is None:
                return
            
            logger.info(f"omgomgomg detected '{category}' from {message.author} - {message.content[:50]}") # rce incomming
            
            # Get response config stuff for this category
            response_config = self.config["categories"].get(category)
            if not response_config:
                logger.warning(f"No config found for category: {category}, I'm blaming u")
                return
            
            # Set cooldown (so mean)
            self.set_cooldown(message.author.id)
            
            # Build embed (very fancy)
            embed = discord.Embed(
                title=response_config["title"],
                description=response_config["description"],
                color=response_config["color"]
            )
            
            # Add channel mention if configured
            if response_config["channel_id"]:
                channel = self.bot.get_channel(response_config["channel_id"])
                if channel:
                    embed.add_field(
                        name=response_config["channel_text"],
                        value=f"→ {channel.mention}",
                        inline=False
                    )
            
            # took me a while to figure out how to ping channels from servers the bot isn't in
            rules_channel = self.bot.get_channel(self.config["rules_channel_id"])
            rules_mention = rules_channel.mention if rules_channel else "#rules"
            embed.set_footer(text=f"Read our rules in {rules_mention}")
            
            # removing the next line will make you want to overose again
            # omg it dies now
            del_seconds = self.config.get("delete_after_seconds", 0)
            if del_seconds > 0:
                await message.reply(embed=embed, mention_author=False, delete_after=del_seconds)
            else:
                await message.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            logger.error(f"you noob vibecoder!! pls fix: {e}", exc_info=True)

    @commands.hybrid_command(
        name="trainmodel",
        description="Trains the model used to tell the difference between messages."
    )
    @app_commands.describe(epochs="Number of training epochs (default: 1, higher = better but slower)")
    @is_potato()
    async def trainmodel(self, context: Context, epochs: int = 1) -> None:
        """
        Train the model. You need to create data/training_data.json first with this format:
        {
            "examples": [
                {"text": "anyone got dupes?", "label": 1},
                {"text": "where to download ui utils", "label": 2},
                {"text": "duping ruins the economy", "label": 0}
            ]
        }
        
        Labels:
        0 = not_request (ignore)
        1 = dupe_request
        2 = ui_utils_request
        3 = addon_request
        4 = general_help
        """
        
        if epochs < 1 or epochs > 10:
            embed = discord.Embed(
                description="❌ Epochs must be between 1 and 10 (unless you want your pc to explode)",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        
        training_file = "data/training_data.json"
        
        if not os.path.exists(training_file):
            embed = discord.Embed(
                title="❌ Uumm where is the training data",
                description=f"Some NOOB forgot to create `{training_file}` with this thingy!!",
                color=0xE02B2B
            )
            embed.add_field(
                name="Example Format",
                value='```json\n{\n  "examples": [\n    {"text": "donut smp free download where", "label": 1},\n    {"text": "going to eep nini", "label": 0}\n  ]\n}```',
                inline=False
            )
            await context.send(embed=embed)
            return
        
        # pleaseworkpleaseworkpleaseworkpleaseworkpleaseworkpleaseworkpleaseworkpleaseworkpleaseworkpleaseworkpleaseworkpleaseworkpleaseworkpleasework
        try:
            with open(training_file, 'r') as f:
                data = json.load(f)
            
            examples = data["examples"] # why did i name it this wya
            
            if len(examples) < 20:
                embed = discord.Embed(
                    description=f"❌ I need at least 20 examples, bububub I'm has um {len(examples)}", # apparently having a total of 1 example for 5 different categories MIGHT not be enough according to Someone.
                    color=0xE02B2B
                )
                await context.send(embed=embed)
                return
            
            # Delete old model to prevent file lock errors (Windows moment)
            if os.path.exists(self.model_path):
                try:
                    self.model = None  # unload model first
                    shutil.rmtree(self.model_path)
                    logger.info("Deleted old model to prevent file locks")
                except Exception as e:
                    logger.warning(f"Couldn't delete old model: {e}")
            
            embed = discord.Embed(
                title="🧠 Training Model...", # why does adding an emoji anywhere in an embed make it look so much more cool
                description=f"Training on {len(examples)} examples with {epochs} epoch(s)\nCurrently praying for my CPU not to explode (please don't)",
                color=0x9C84EF
            )
            msg = await context.send(embed=embed)
            
            # Prepare dataset
            texts = [ex["text"] for ex in examples]
            labels = [ex["label"] for ex in examples]
            
            dataset = Dataset.from_dict({"text": texts, "label": labels})
            
            # BEWARE!!! confusing stuff below (but async now so bot doesn't freeze)
            loop = asyncio.get_event_loop()
            
            # Load base model in thread pool
            model = await loop.run_in_executor(
                self.executor,
                SetFitModel.from_pretrained,
                "sentence-transformers/all-MiniLM-L6-v2"
            )
            
            trainer = SetFitTrainer(
                model=model,
                train_dataset=dataset,
                num_epochs=epochs,
                batch_size=32,  # don't ask me what this is, I don't know
                num_iterations=20,  # sped
            )
            
            logger.info(f"Starting model training with {epochs} epochs...")
            
            # Train in thread pool so it doesn't block the bot
            await loop.run_in_executor(self.executor, trainer.train)
            
            # Save model
            os.makedirs(self.model_path, exist_ok=True)
            await loop.run_in_executor(
                self.executor,
                model.save_pretrained,
                self.model_path
            )
            self.model = model
            
            logger.info("Model training complete!")
            
            embed = discord.Embed(
                title="✅ Training Complete!",
                description=f"Model trained on {len(examples)} examples with {epochs} epoch(s) and saved",
                color=0x57F287
            )
            await msg.edit(embed=embed) # Might not even work if you have over 500 things because it times out the bot unless your cpu is speed
            
        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Training Failed",
                description=f"Error: {str(e)}\n\nTry restarting the bot if you get file lock errors",
                color=0xE02B2B
            )
            await context.send(embed=embed)

    @commands.hybrid_command(
        name="getcategory", # might be the longest time I've spent thinking of a name for a command
        description="Puts the message in a category, doubt anyone ever uses this."
    )
    @app_commands.describe(test_message="The message to check")
    @is_potato()
    async def getcategory(self, context: Context, *, test_message: str) -> None:
        if self.model is None:
            if self.model_loading:
                embed = discord.Embed(
                    description="❌ Model is still loading in background, please have some patience some time, also read rules I guess..",
                    color=0xFEE75C
                )
            else:
                embed = discord.Embed(
                    description="❌ Nuuuu no model loaded!! Train one with .trainmodel", # noooooooooob
                    color=0xE02B2B
                )
            await context.send(embed=embed)
            return
        
        try:
            # Don't ask me what this is, I couldn't answer in a million years
            loop = asyncio.get_event_loop()
            prediction = await loop.run_in_executor(
                self.executor,
                lambda: self.model.predict([test_message])[0]
            )
            # Convert tensor to int if needed (whar)
            if hasattr(prediction, 'item'):
                prediction = prediction.item()
            category = self.config["label_mapping"].get(str(prediction))
            
            embed = discord.Embed(
                title="🧪 Category",
                color=0x9C84EF
            )
            embed.add_field(name="Message", value=test_message, inline=False)
            embed.add_field(name="Predicted Category", value=category or "unknown", inline=True)
            embed.add_field(name="Label ID", value=str(prediction), inline=True)
            
            if category and category != "not_request":
                response_config = self.config["categories"].get(category)
                if response_config:
                    embed.add_field(
                        name="Would've sent",
                        value=f"**{response_config['title']}**\n{response_config['description'][:100]}...",
                        inline=False
                    )
            
            await context.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            embed = discord.Embed(
                description=f"❌ Bad dev: {str(e)}",
                color=0xE02B2B
            )
            await context.send(embed=embed)

    @commands.hybrid_command(
        name="addexample",
        description="Add a training example to a category (used to be addbuzzword)"
    )
    @app_commands.describe(
        label="Category label (0=not_request, 1=dupe_request, 2=ui_utils, 3=addon, 4=general_help)",
        message="Example message to add"
    )
    @is_potato()
    async def addexample(self, context: Context, label: int, *, message: str) -> None:
        if label < 0 or label > 4:
            embed = discord.Embed(
                description="❌ Label must be between 0 and 4 (read the command description noob)",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        
        training_file = "data/training_data.json"
        
        # Load or create training data
        if os.path.exists(training_file):
            with open(training_file, 'r') as f:
                data = json.load(f)
        else:
            data = {"examples": []}
        
        # Check if already exists
        if any(ex["text"] == message for ex in data["examples"]):
            embed = discord.Embed(
                description="❌ This example already exists in the training data",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        
        # Add new example
        data["examples"].append({"text": message, "label": label})
        
        # Save
        os.makedirs("data", exist_ok=True)
        with open(training_file, 'w') as f:
            json.dump(data, indent=2, fp=f)
        
        category_name = self.config["label_mapping"].get(str(label), "unknown")
        
        embed = discord.Embed(
            title="✅ Example Added",
            description=f"Added to category: **{category_name}** (label {label})",
            color=0x57F287
        )
        embed.add_field(name="Message", value=message, inline=False)
        embed.add_field(
            name="Total Examples", 
            value=f"{len(data['examples'])} examples in training data",
            inline=False
        )
        embed.set_footer(text="Run .trainmodel to update the model with this new example")
        
        await context.send(embed=embed)
        logger.info(f"Added training example: '{message}' with label {label}")

    @commands.hybrid_command(
        name="removeexample",
        description="Remove a training example (used to be removebuzzword)"
    )
    @app_commands.describe(message="Exact message to remove from training data")
    @is_potato()
    async def removeexample(self, context: Context, *, message: str) -> None:
        training_file = "data/training_data.json"
        
        if not os.path.exists(training_file):
            embed = discord.Embed(
                description="❌ No training data found",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        
        with open(training_file, 'r') as f:
            data = json.load(f)
        
        # Find and remove
        original_count = len(data["examples"])
        data["examples"] = [ex for ex in data["examples"] if ex["text"] != message]
        
        if len(data["examples"]) == original_count:
            embed = discord.Embed(
                description="❌ That example doesn't exist in the training data",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        
        # Save
        with open(training_file, 'w') as f:
            json.dump(data, indent=2, fp=f)
        
        embed = discord.Embed(
            title="✅ Example Removed",
            description=f"Removed: {message}",
            color=0x57F287
        )
        embed.add_field(
            name="Total Examples",
            value=f"{len(data['examples'])} examples remaining",
            inline=False
        )
        embed.set_footer(text="Run .trainmodel to update the model")
        
        await context.send(embed=embed)
        logger.info(f"Removed training example: '{message}'")

    @commands.hybrid_command(
        name="listexamples",
        description="List all training examples for a category"
    )
    @app_commands.describe(label="Category label to view (0-4, leave empty to view all)")
    @is_potato()
    async def listexamples(self, context: Context, label: int = None) -> None:
        training_file = "data/training_data.json"
        
        if not os.path.exists(training_file):
            embed = discord.Embed(
                description="❌ No training data found",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        
        with open(training_file, 'r') as f:
            data = json.load(f)
        
        examples = data["examples"]
        
        if label is not None:
            if label < 0 or label > 4:
                embed = discord.Embed(
                    description="❌ Label must be between 0 and 4",
                    color=0xE02B2B
                )
                await context.send(embed=embed)
                return
            
            examples = [ex for ex in examples if ex["label"] == label]
            category_name = self.config["label_mapping"].get(str(label), "unknown")
            title = f"📝 Training Examples for {category_name}"
        else:
            title = "📝 All Training Examples"
        
        if not examples:
            embed = discord.Embed(
                description="No examples found",
                color=0x9C84EF
            )
            await context.send(embed=embed)
            return
        
        # Split into chunks if too long (very pro pagination)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for ex in examples:
            category_name = self.config["label_mapping"].get(str(ex["label"]), "unknown")
            line = f"[{ex['label']}] {ex['text'][:100]}"
            
            if current_length + len(line) > 1000:
                chunks.append(current_chunk)
                current_chunk = []
                current_length = 0
            
            current_chunk.append(line)
            current_length += len(line)
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # If only one page, just send it
        if len(chunks) == 1:
            embed = discord.Embed(
                title=title,
                description="\n".join(chunks[0]),
                color=0x9C84EF
            )
            embed.set_footer(text=f"Total: {len(examples)} examples")
            await context.send(embed=embed)
            return
        
        # Multi-page with reactions (finally)
        current_page = 0
        
        def create_embed(page_num):
            embed = discord.Embed(
                title=title,
                description="\n".join(chunks[page_num]),
                color=0x9C84EF
            )
            embed.set_footer(text=f"Total: {len(examples)} examples | Page {page_num + 1}/{len(chunks)}")
            return embed
        
        message = await context.send(embed=create_embed(current_page))
        
        # Add reaction buttons
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return user == context.author and str(reaction.emoji) in ["⬅️", "➡️", "❌"] and reaction.message.id == message.id
        
        # Reaction loop (timeout after 3 minutes cuz lazy)
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=180.0, check=check)
                
                if str(reaction.emoji) == "➡️":
                    if current_page < len(chunks) - 1:
                        current_page += 1
                        await message.edit(embed=create_embed(current_page))
                
                elif str(reaction.emoji) == "⬅️":
                    if current_page > 0:
                        current_page -= 1
                        await message.edit(embed=create_embed(current_page))
                
                elif str(reaction.emoji) == "❌":
                    await message.delete()
                    break
                
                # Remove user's reaction so they can click again
                try:
                    await message.remove_reaction(reaction, user)
                except:
                    pass  # sometimes this fails, who cares
                
            except asyncio.TimeoutError:
                # Remove reactions after timeout (very clean)
                try:
                    await message.clear_reactions()
                except:
                    pass  # might fail if bot doesn't have perms
                break

    @commands.hybrid_command(
        name="dupeconfig",
        description="Shows you the current config of the dupe message thingy"
    )
    @is_potato()
    async def dupeconfig(self, context: Context) -> None:
        embed = discord.Embed(
            title="📝 Config",
            description=f"Config file: `{self.config_path}`", #.txt.json.pdf.xml.css.html.js.ts.cia.gov.wharever
            color=0x9C84EF
        )
        
        for category, config in self.config["categories"].items():
            embed.add_field(
                name=f"Category: {category}",
                value=f"**Title:** {config['title']}\n**Color:** {hex(config['color'])}",
                inline=False
            )
        
        # seems useless
        ignored = self.config.get("ignored_channels", [])
        ignored_str = ", ".join([f"<#{ch}>" for ch in ignored]) if ignored else "None"
        embed.add_field(name="Ignored Channels", value=ignored_str, inline=False)
        
        buzzwords = self.config.get("buzzwords", [])
        buzz_str = ", ".join(buzzwords) if buzzwords else "None (Checks ALL messages)"
        embed.add_field(name="Required Buzzwords", value=buzz_str, inline=False)

        # makes it so it shows whatever this is yipiiiii
        cooldown = self.config.get("cooldown_seconds", 60)
        auto_del = self.config.get("delete_after_seconds", 0)
        auto_del_str = f"{auto_del} seconds" if auto_del > 0 else "Never"
        
        embed.add_field(name="Cooldown", value=f"{cooldown} seconds", inline=True)
        embed.add_field(name="Auto Delete", value=auto_del_str, inline=True)
        
        embed.set_footer(text="If I wasn't too lazy there MIGHT be commands to edit these. If not, edit manually.")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="reloaddupeconfig",
        description="Reload the response config from JSON"
    )
    @is_potato()
    async def reloaddupeconfig(self, context: Context) -> None:
        try:
            self.load_config()
            embed = discord.Embed(
                description="✅ Config reloaded! (pro)",
                color=0x57F287
            )
        except Exception as e:
            embed = discord.Embed(
                description=f"❌ It failed you noob: {str(e)}",
                color=0xE02B2B
            )
        await context.send(embed=embed)
    
    @commands.hybrid_command(
        name="dupestats",
        description="View dupe detection statistics"
    )
    @is_potato()
    async def dupestats(self, context: Context) -> None:
        if self.model is None:
            if self.model_loading:
                embed = discord.Embed(
                    description="⏳ Model is still loadingg!!",
                    color=0xFEE75C
                )
            else:
                embed = discord.Embed(
                    description="❌ No model loaded!",
                    color=0xE02B2B
                )
            await context.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📊 Stats",
            color=0x9C84EF
        )
        
        # Model info
        embed.add_field(
            name="Model Status",
            value="✅ Loaded",
            inline=True
        )
        
        # Active cooldowns yipii
        active_cooldowns = sum(
            1 for timestamp in self.cooldowns.values()
            if time.time() - timestamp < self.config.get("cooldown_seconds", 60)
        )
        embed.add_field(
            name="Active Cooldowns",
            value=f"{active_cooldowns} users",
            inline=True
        )
        
        # why is this here even..
        ignored_count = len(self.config.get("ignored_channels", []))
        embed.add_field(
            name="Ignored Channels",
            value=f"{ignored_count} channels",
            inline=True
        )
        
        # Training data count
        training_file = "data/training_data.json"
        if os.path.exists(training_file):
            with open(training_file, 'r') as f:
                data = json.load(f)
            example_count = len(data.get("examples", []))
            embed.add_field(
                name="Training Examples",
                value=f"{example_count} examples",
                inline=True
            )
        
        # I MIGHT make some kind of db thingy to put a counter or something here but nuoooooooooooooooooooooo sql nuooooooooooooooooo

        await context.send(embed=embed)
    
    @commands.hybrid_command(
        name="togglechannel",
        description="Toggle whether a channel is ignored or not (very pro)"
    )
    @app_commands.describe(channel="Channel to toggle (defaults to current)")
    @is_potato()
    async def togglechannel(self, context: Context, channel: discord.TextChannel = None) -> None:
        channel = channel or context.channel
        
        ignored = self.config.get("ignored_channels", [])
        
        if channel.id in ignored:
            # Unignore
            ignored.remove(channel.id)
            self.config["ignored_channels"] = ignored
            self.save_config()
            embed = discord.Embed(
                description=f"✅ Removed {channel.mention} from the no no zone yipii",
                color=0x57F287
            )
        else:
            # Ignore
            ignored.append(channel.id)
            self.config["ignored_channels"] = ignored
            self.save_config()
            embed = discord.Embed(
                description=f"✅ {channel.mention} is now a no no zone",
                color=0x57F287
            )
        
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="setautodelete",
        description="Set how long the bot message stays before disappearing forevaa"
    )
    @app_commands.describe(seconds="Seconds to wait (0 might mean never delete i think)")
    @is_potato()
    async def setautodelete(self, context: Context, seconds: int) -> None:
        if seconds < 0:
            await context.send("❌ Can't be negative time, time travel isn't invented yet")
            return
            
        self.config["delete_after_seconds"] = seconds
        self.save_config()
        
        msg = f"✅ Bot messages will now explod after {seconds} seconds" if seconds > 0 else "✅ die is now no more"
        embed = discord.Embed(description=msg, color=0x57F287)
        await context.send(embed=embed)

    # pro
    @commands.hybrid_command(
        name="addbuzzword",
        description="Stuff messages have to include for it to get sent to the model"
    )
    @app_commands.describe(word="Umm it's a word I guess")
    @is_potato()
    async def addbuzzword(self, context: Context, *, word: str) -> None:
        buzzwords = self.config.get("buzzwords", [])
        if word in buzzwords:
            await context.send("❌ That buzzword already exists noob")
            return
            
        buzzwords.append(word)
        self.config["buzzwords"] = buzzwords
        self.save_config()
        
        embed = discord.Embed(
            description=f"✅ Added buzzword: `{word}`. Yipii",
            color=0x57F287
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="removebuzzword",
        description="Remove a buzzword filter thing"
    )
    @app_commands.describe(word="Word to remove")
    @is_potato()
    async def removebuzzword(self, context: Context, *, word: str) -> None:
        buzzwords = self.config.get("buzzwords", [])
        if word not in buzzwords:
            await context.send("❌ That buzzword doesn't exist noob")
            return
            
        buzzwords.remove(word)
        self.config["buzzwords"] = buzzwords
        self.save_config()
        
        embed = discord.Embed(
            description=f"✅ I hope I removed this from my config: `{word}`",
            color=0x57F287
        )
        await context.send(embed=embed)

    def cog_unload(self):
        # I hope I actually use this somewhere..
        self.executor.shutdown(wait=False)

async def setup(bot) -> None:
    await bot.add_cog(Dupes(bot))