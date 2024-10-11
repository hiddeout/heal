import importlib
import jishaku
import logging
import asyncpg
import asyncio
import aiohttp
import discord
import secrets
import string
import glob
import json
import sys
import os
import re
import datetime
import time
import discord_ios
import socket
import pathlib

from asyncpg import Pool
from typing import Dict, Set
from collections import defaultdict

from tools.managers.help import HealHelp
from tools.managers.cache import Cache
from tools.managers.context import Context
from tools.managers.lastfm import FMHandler
from tools.configuration import Colors, Emojis
from discord.ext import commands
from discord import Message, Embed

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


intents = discord.Intents.all()

OWNER_IDS = 1, 2  # replace


class Heal(commands.AutoShardedBot):
    def __init__(self):
        self.cache = Cache()
        self.errors = Dict[str, commands.CommandError]
        self._uptime = time.time()

        super().__init__(
            command_prefix=",",
            help_command=HealHelp(),
            intents=intents,
            activity=discord.CustomActivity(
                name=f"placeholder"
            ),  # edit with your own status
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=True, roles=False, replied_user=False
            ),
            case_insensitive=True,
            owner_ids=OWNER_IDS,  # can switch to just 1 id
        )

        self.message_cache = defaultdict(list)
        self.cache_expiry_seconds = 30
        self.add_check(self.disabled_command)

    async def load_modules(self, directory: str) -> None:
        for module in glob.glob(f"{directory}/**/*.py", recursive=True):
            if module.endswith("__init__.py"):
                continue
            try:
                await self.load_extension(module.replace("/", ".").replace(".py", ""))
                log.info(f"Loaded module: {module}")
            except commands.ExtensionFailed:
                log.warning(f"Extension failed to load: {module}")
            except Exception as e:
                log.error(f"Error loading module {module}: {e}")

    async def load_patches(self) -> None:
        for module in glob.glob("tools/patches/**/*.py", recursive=True):
            if module.endswith("__init__.py"):
                continue

            module_name = (
                module.replace(os.path.sep, ".").replace("/", ".").replace(".py", "")
            )

            try:
                importlib.import_module(module_name)
                print(f"Patched: {module}")
            except ModuleNotFoundError as e:
                print(f"Error importing {module_name}: {e}")

    async def _load_database(self) -> Pool:
        try:
            pool = await asyncpg.create_pool(
                **{
                    var: os.environ[
                        f"DATABASE_{var.upper()}" if var != "database" else "DATABASE"
                    ]
                    for var in ["database", "user", "password", "host"]
                },
                max_size=30,
                min_size=10,
            )
            log.info("Database connection established")

            with open("tools/schema/schema.sql", "r") as file:
                schema = file.read()
                if schema.strip():  # Check if schema is not empty
                    await pool.execute(schema)
                    log.info("Database schema loaded")
                else:
                    log.warning("Database schema file is empty")
                file.close()

            return pool
        except Exception as e:
            log.error(f"Error loading database: {e}")
            raise e

    async def get_prefix(self, message: Message) -> tuple:
        """
        Get the command prefixes for a message, considering both self-prefix and guild prefix.
        """
        if message.guild is None:
            return

        guild_prefix = await self.cache.get(f"prefix-{message.guild.id}")
        if guild_prefix is None:
            guild_prefix = (
                await self.pool.fetchval(
                    "SELECT prefix FROM guilds WHERE guild_id = $1", message.guild.id
                )
                or ";"
            )
            await self.cache.set(f"prefix-{message.guild.id}", guild_prefix)

        self_prefix = await self.cache.get(f"selfprefix-{message.author.id}")
        if self_prefix is None:
            self_prefix = await self.pool.fetchval(
                "SELECT prefix FROM selfprefix WHERE user_id = $1", message.author.id
            )
            if self_prefix:
                await self.cache.set(f"selfprefix-{message.author.id}", self_prefix)

        return (self_prefix or guild_prefix, guild_prefix)

    async def on_ready(self) -> None:
        log.info(
            f"Logged in as {self.user.name}#{self.user.discriminator} ({self.user.id})"
        )
        log.info(f"Connected to {len(self.guilds)} guilds")
        log.info(f"Connected to {len(self.users)} users")

        #  await self.cogs["Music"].start_nodes()  # do this urself
        log.info("Lavalink Nodes Loaded.")

    async def setup_hook(self) -> None:
        self.pool = await self._load_database()
        self.session = aiohttp.ClientSession()
        await self.load_modules("cogs")
        await self.load_modules("events")
        await self.load_extension("jishaku")

        from tools.ui import Interface

        self.add_view(Interface(self))

        return await super().setup_hook()

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        self._connection.http.connector = aiohttp.TCPConnector(
            limit=0, family=socket.AF_INET, local_addr=("0", 0)  # REPLACE
        )
        return await super().start(token, reconnect=reconnect)

    async def get_context(self, message: Message, *, cls=Context):
        return await super().get_context(message, cls=cls)

    def humanize_number(self, number: int) -> str:
        suffixes = ["", "k", "m", "b", "t"]
        magnitude = min(len(suffixes) - 1, (len(str(abs(number))) - 1) // 3)
        formatted_number = (
            "{:.1f}".format(number / 10 ** (3 * magnitude)).rstrip("0").rstrip(".")
        )
        return "{}{}".format(formatted_number, suffixes[magnitude])

    def humanize_time(self, start_time: float) -> str:
        uptime_seconds = abs(time.time() - start_time)
        intervals = (
            ("year", 31556952),
            ("month", 2629746),
            ("day", 86400),
            ("hour", 3600),
            ("minute", 60),
            ("second", 1),
        )

        result = []
        for name, count in intervals:
            value = uptime_seconds // count
            if value:
                uptime_seconds -= value * count
                result.append(f"{int(value)} {name}{'s' if value > 1 else ''}")

        return ", ".join(result)

    @property
    def uptime(self) -> str:
        return self.humanize_time(self._uptime)

    @property
    def linecount(self) -> int:
        return sum(
            [
                len(f.open("r").readlines())
                for f in [
                    f
                    for f in pathlib.Path("/root/HEAL/").glob("**/*.py")
                    if f.is_file()
                ]
            ]
        )

    async def on_command_error(
        self, ctx: Context, exception: commands.CommandError
    ) -> None:
        if type(exception) in [
            commands.CommandNotFound,
            commands.NotOwner,
            commands.CheckFailure,
        ]:
            return
        elif isinstance(exception, commands.BadColourArgument):
            return await ctx.warn(f"I was **unable** to find that **color**.")
        elif isinstance(exception, commands.RoleNotFound):
            return await ctx.warn(
                f"I was unable to find the role **{exception.argument}**."
            )
        elif isinstance(exception, commands.ChannelNotFound):
            return await ctx.warn(
                f"I was unable to find the channel **{exception.argument}**"
            )
        elif isinstance(exception, commands.ThreadNotFound):
            return await ctx.warn(
                f"I was unable to find the thread **{exception.argument}**"
            )
        elif isinstance(exception, commands.BadUnionArgument):
            if (
                discord.Emoji in exception.converters
                or discord.PartialEmoji in exception.converters
            ):
                return await ctx.warn(f"Invalid **emoji** provided.")
            elif (
                discord.User in exception.converters
                or discord.Member in exception.converters
            ):
                return await ctx.warn(
                    f"I was unable to find that **member** or the provided **ID** is invalid."
                )
            return await ctx.warn(
                f"Could not convert **{exception.param.name}** to **{exception.converters}**"
            )
        elif isinstance(exception, commands.CommandInvokeError):
            if isinstance(exception.original, ValueError):
                return await ctx.warn(exception.original)
            elif isinstance(exception.original, discord.HTTPException):
                return await ctx.warn(f"**Invalid code**\n```{exception.original}```")
            elif isinstance(exception.original, aiohttp.ClientConnectorError):
                return await ctx.warn(
                    f"**Failed** to connect to the **URL** - Possibly invalid."
                )
            elif isinstance(exception.original, aiohttp.ClientResponseError):
                if exception.original.status == 522:
                    return await ctx.warn(
                        f"**Timed out** while requesting data - probably the API's fault"
                    )
                return await ctx.warn(
                    f"**API** returned a **{exception.original.status}** status - try again later."
                )
            elif isinstance(exception.original, discord.Forbidden):
                return await ctx.warn(
                    f"I'm **missing** permission: `{exception.original.missing_perms[0]}`"
                )
            elif isinstance(exception.original, discord.NotFound):
                return await ctx.warn(f"**Not found** - the **ID** is invalid")
            elif isinstance(exception.original, aiohttp.ContentTypeError):
                return await ctx.warn(
                    f"**Invalid content** - the **API** returned an unexpected response"
                )
            elif isinstance(exception.original, aiohttp.InvalidURL):
                return await ctx.warn(f"The provided **url** is invalid")
            elif isinstance(exception.original, asyncpg.StringDataRightTruncationError):
                return await ctx.warn(
                    f"**Data** is too **long** - try again with a shorter message"
                )
            return await ctx.warn(exception.original)
        elif isinstance(exception, commands.UserNotFound):
            return await ctx.warn(
                "I was unable to find that **member** or the **ID** is invalid"
            )
        elif isinstance(exception, commands.MemberNotFound):
            return await ctx.warn(
                f"I was unable to find a member with the name: **{exception.argument}**"
            )
        elif isinstance(exception, commands.MissingPermissions):
            return await ctx.warn(
                f"You're **missing** permission: `{exception.missing_permissions[0]}`"
            )
        elif isinstance(exception, commands.BotMissingPermissions):
            return await ctx.warn(
                f"I'm **missing** permission: `{exception.missing_permissions[0]}`"
            )
        elif isinstance(exception, commands.GuildNotFound):
            return await ctx.warn(
                f"I was unable to find that **server** or the **ID** is invalid"
            )
        elif isinstance(exception, commands.BadInviteArgument):
            return await ctx.warn(f"Invalid **invite code** given")
        elif isinstance(exception, commands.UserInputError):
            return await ctx.warn(f"**Invalid Input Given**: \n`{exception}`")
        elif isinstance(exception, commands.CommandOnCooldown):
            return await ctx.neutral(
                f"Please wait **{exception.retry_after:.2f} seconds** before using this command again."
            )
        if isinstance(exception, commands.errors.NotOwner):
            return await ctx.deny(f"You are not an owner of {self.user.mention}.")

        code = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(13)
        )
        self.errors[code] = exception
        return await ctx.warn(
            message=f"Error occurred whilst performing command **{ctx.command.qualified_name}**. Use the given error code to report it to the developers in the [support server](https://discord.gg/tCZDT7YdUF)",
            content=f"`{code}`",
        )

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        check = await self.pool.fetchrow(
            "SELECT * FROM blacklist WHERE user_id = $1", message.author.id
        )
        if check:
            return

        prefix = await self.get_prefix(message)
        if not message.content.startswith(tuple(prefix)):
            return

        now = time.time()
        author_id = message.author.id

        self.message_cache[author_id] = [
            timestamp
            for timestamp in self.message_cache[author_id]
            if now - timestamp < self.cache_expiry_seconds
        ]

        if len(self.message_cache[author_id]) >= 10:
            await self.pool.execute("INSERT INTO blacklist VALUES ($1)", author_id)
            await message.channel.send(
                embed=discord.Embed(
                    color=Colors.BASE_COLOR,
                    description=f"> {message.author.mention}: You are now **blacklisted**, join the support [server]() for support.",
                )
            )
        else:
            self.message_cache[author_id].append(now)
            await self.process_commands(message)

    async def disabled_command(self, ctx: Context) -> bool:
        if ctx.guild is None:
            return True
        cmd = self.get_command(ctx.invoked_with)
        if not cmd:
            return True

        check = await self.pool.fetchrow(
            "SELECT * FROM disablecommand WHERE command = $1 AND guild_id = $2",
            cmd.name,
            ctx.guild.id,
        )

        if check:
            await ctx.warn(f"The command **{cmd.name}** is **disabled** in this guild")

        return check is None
