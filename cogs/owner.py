import discord
import os
import sys
import aiohttp

from discord import Message, Embed
from discord.ext import commands
from discord.ext.commands import (
    Cog,
    command,
    hybrid_command,
    is_owner
)
from typing import Union
from discord.ext.tasks import loop
from discord import Member, Guild, Object, User
from asyncio import gather
import traceback
import secrets
import config
import subprocess
import asyncio
import requests

from tools.heal import Heal
from tools.managers.context import Context, Emojis, Colors

class Owner(Cog):
    def __init__(self, bot: Heal) -> None:
        self.bot = bot

    @hybrid_command(
        name = "activity",
        aliases = ["status"],
        description = "Change the bots activity status."
    )
    @is_owner()
    
    async def activity(self, ctx: Context, *, activity: str):
        activity = discord.CustomActivity(name=activity)
        await self.bot.change_presence(activity=activity)
        await ctx.approve(f"**Activity** has been set to - `{activity}`")

    @hybrid_command(
        name = "say",
        aliases = ["repeat", "rp"],
        description = "Make the bot repeat the text"
    )
    @is_owner()
    async def say(self, ctx, *, msg: str):
        await ctx.message.delete()
        await ctx.send(msg)


    @commands.group(
        name = "system",
        aliases = ["sys"],
        description = "System commands.",
        invoke_without_command = True
    )
    @is_owner()
    async def system(self, ctx: Context):
        return await ctx.send_help(ctx.command.qualified_name)
    
    @system.command(
        name = "restart",
        aliases = ["rs", "reboot"],
        description = "restarts the bot."
    )
    @is_owner()
    async def system_restart(self, ctx: Context):
        await ctx.approve(f"Restarting bot...")
        os.system("pm2 restart 0")


    @system.command(
        name = "pfp",
        aliases = ["av", "changeav"]
    )
    @is_owner()
    async def system_avatar(self, ctx: Context, *, image: str= None):

        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        elif image:
            image_url = image
        else:
            return await ctx.warn(f"Please provide an image URL or upload an image.")

        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    return await ctx.deny(f"Failed to fetch the image.")
                data = await resp.read()

        try:
            await self.bot.user.edit(avatar=data)
            await ctx.approve(f"Changed my **pfp** successfully!")
        except discord.HTTPException as e:
            await ctx.deny(f"Failed to change profile picture: {e}")

    @system.command(
        name = "banner",
        aliases = ["bnr", "changebanner"]
    )
    @is_owner()
    async def system_banner(self, ctx: Context, *, image: str= None):

        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        elif image:
            image_url = image
        else:
            return await ctx.warn(f"Please provide an image URL or upload an image.")

        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    return await ctx.deny(f"Failed to fetch the image.")
                data = await resp.read()

        try:
            await self.bot.user.edit(banner=data)
            await ctx.approve(f"Changed my **banner** successfully!")
        except discord.HTTPException as e:
            await ctx.deny(f"Failed to change profile picture: {e}")


    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: Context):

        await ctx.message.add_reaction("⌛")
        await self.bot.tree.sync()
        await ctx.message.clear_reactions()
        return await ctx.message.add_reaction("✅")
    
    @commands.command(
        name = "unblacklist",
        aliases =["unbl"],
        description = "Unblacklist a user."
    )
    @commands.is_owner()
    async def unblacklist(self, ctx: Context, *, user: Union[discord.User, discord.Member]):

        await self.bot.pool.execute(
            """
            DELETE FROM blacklist 
            WHERE user_id = $1
            """,
            user.id
        )

        return await ctx.approve(f"**Unblacklisted** {user.name}")

    @commands.command(
        name = "blacklist",
        aliases =["bl"],
        description = "Blacklist a user."
    )
    @commands.is_owner()
    async def blacklist(self, ctx: Context, *, user: Union[discord.User, discord.Member]):

        await self.bot.pool.execute(
            """
            INSERT INTO blacklist (user_id)
            VALUES ($1)
            ON CONFLICT (user_id)
            DO NOTHING
            """,
            user.id
        )

        return await ctx.approve(f"**Blacklisted** {user.name}")

    @command(
        name = "blacklistguild",
        description = "Blacklists a guild."
    )
    @commands.is_owner()
    async def blacklistguild(self, ctx: Context, *, guildid: int):
        if not guildid:
            await ctx.warn("Guild not found.")
            return

        check = await self.bot.pool.fetchrow("SELECT 1 FROM blacklistguild WHERE guild_id = $1", guildid)
        if check:
            await self.bot.pool.execute("DELETE FROM blacklistguild WHERE guild_id = $1", guildid)
            await ctx.approve(f"Guild {guildid} has been removed from the blacklist.")
        else:
            await self.bot.pool.execute("INSERT INTO blacklistguild (guild_id) VALUES ($1)", guildid)
            await ctx.approve(f"Guild {guildid} has been added to the blacklist.")

    @command(
        name = "upload"
    )
    @commands.is_owner()
    async def upload(self, ctx, attachment: discord.Attachment):
        file_bytes = await attachment.read()
        url = "https://catbox.moe/user/api.php"
        payload = {
            'reqtype': 'fileupload'
        }
        files = {
            'fileToUpload': (attachment.filename, file_bytes)
        }

        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field('reqtype', 'fileupload')
            form.add_field('fileToUpload', file_bytes, filename=attachment.filename)
            
            async with session.post(url, data=form) as response:
                if response.status == 200:
                    response_text = await response.text()
                    await ctx.send(f"File uploaded successfully: {response_text}")
                else:
                    await ctx.send(f"Failed to upload the file. Status Code: {response.status}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        check = await self.bot.pool.fetchrow("SELECT 1 FROM blacklistguild WHERE guild_id = $1", guild.id)

        if check:
            await guild.leave()
            owner = await self.bot.fetch_user(187747524646404105)
            await owner.send(f"Left a blacklisted guild: {guild}")
        else:
            print(f"Joined guild: {guild.id}")

    @commands.command()
    @commands.is_owner()
    async def gi(self, ctx, identifier: str):
        guild = None

        if identifier.isdigit():
            guild = self.bot.get_guild(int(identifier))
        else:
            guild = discord.utils.get(self.bot.guilds, name=identifier)

        if guild:
            invite = await ctx.send(f"guild > {guild.name}, inv > {await self.generate_invite(guild)}")
        else:
            await ctx.send(f"not in the guild, no perms or wrong id. {identifier}")

    async def generate_invite(self, guild):
        invite = await guild.text_channels[0].create_invite()
        return invite.url

    @commands.command(name="leaveguild", description="Force the bot to leave a guild by its ID.", permission = "Owner")
    @commands.is_owner() 
    async def leaveguild(self, ctx: Context, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild:
            await guild.leave()
            await ctx.approve(f"Successfully left the guild: {guild.name} (ID: {guild.id})")
        else:
            await ctx.warn(f"Guild with ID {guild_id} not found.")

    @commands.command(
        name = "globalban",
        aliases = ["gban"],
        description = "Global bans a user."
    )
    @commands.is_owner()
    async def globalban(self, ctx: Context, *, user: discord.User):
        if user.id in self.bot.owner_ids:
            return await ctx.deny("You can't global ban a bot owner.")
        if user.id == self.bot.user.id:
            return await ctx.deny(f"Bro tried global banning me from {len(self.bot.guilds)} 💀")

        check = await self.bot.pool.fetchrow(
            "SELECT * FROM globalban WHERE user_id = $1", user.id
        )
        if check:
            await self.bot.pool.execute("DELETE FROM globalban WHERE user_id = $1", user.id)
            return await ctx.approve("{user.mention} was succesfully globally unbanned")

        mutual_guilds = len(user.mutual_guilds)
        tasks = [
            g.ban(user, reason=f"Globally banned by bot owner: {ctx.author.name}")
            for g in user.mutual_guilds
            if g.me.guild_permissions.ban_members
            and g.me.top_role > g.get_member(user.id).top_role
            and g.owner_id != user.id
        ]
        await asyncio.gather(*tasks)
        await self.bot.pool.execute("INSERT INTO globalban VALUES ($1)", user.id)
        return await ctx.approve(f"{user.mention} was succesfully global banned in {len(tasks)}/{mutual_guilds} servers")

    @command(
        name = "whitelist",
        aliases = ["wl", "auth"],
        description = "Authorize a guild."
    )
    @is_owner()
    async def whitelist(self, ctx: Context, *, guild: Union[discord.Guild, int]):
        if isinstance(guild, discord.Guild):
            guild_id = guild.id
        elif isinstance(guild, int):
            guild_id = guild
        else:
            await ctx.warn("Please provide a valid guild ID or mention a guild.")
            return

        try:
            await self.bot.pool.execute(
                "INSERT INTO authed (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING;",
                guild_id
            )
            await ctx.approve(f"Guild **{guild_id}** has been authorized successfully.")
        except Exception as e:
            await ctx.deny(f"An error occurred while authorizing the guild: {e}")
            raise e

    @commands.group(
        name = "premium",
        description = "Gives / revokes a users premium.",
        invoke_without_command = True
    )
    @is_owner()
    async def premium(self, ctx: Context):
        return await ctx.send_help(ctx.command)
    
    @premium.command(
        name = "add",
        aliases = ["give"],
        description = "Give a user premium."
    )
    @is_owner()
    async def premium_give(self, ctx: Context, *, user: Union[discord.Member, discord.User]= None):
        if user is None:
            return await ctx.warn(f"User cannot be none.")
        
        await self.bot.pool.execute("INSERT INTO premium (user_id) VALUES ($1)", user.id)
        return await ctx.approve(f"**{user.name}** has been **granted** premium.")
    
    @premium.command(
        name = "remove",
        aliases = ["take", "revoke"],
        description = "Revokes a user premium."
    )
    @is_owner()
    async def premium_revoke(self, ctx: Context, *, user: Union[discord.Member, discord.User]= None):
        if user is None:
            return await ctx.warn(f"User cannot be none.")
        
        await self.bot.pool.execute("DELETE FROM premium WHERE user_id = $1", user.id)
        return await ctx.approve(f"**{user.name}'s** premium has been **revoked**.")

    @commands.group(invoke_without_command=True, name="api")
    async def api(self, ctx:Context):
        await ctx.send_help(ctx.command)

    @api.command(name="add", brief="bot owner", usage="[user] [role]\n[master] [bot_developer] [premium] [pro] [basic]", description="add an api key")
    @commands.is_owner()
    async def apikey_add(self, ctx: Context, user: discord.User, role: str):
        key = secrets.token_urlsafe(32)  
        url = "http://66.23.207.37:1337/"

        check = await self.bot.pool.fetchrow("SELECT * FROM api_key WHERE user_id = $1", user.id)
        if check is not None:
            return await ctx.send(f"The user **{user.name}** already has a **valid** API key.")

        embed = discord.Embed(description=f"Your API key for {url} is listed above.", color=Colors.BASE_COLOR)

        await self.bot.pool.execute("INSERT INTO api_key (key, user_id, role) VALUES ($1, $2, $3)", key, user.id, role)
        await ctx.approve(f"I have **successfully** added the API key **{key}** to {user.mention}.")
        await user.send(f"{key}", embed=embed)

    @command(
        name = "push",
        description = "Push to the github repo."
    )
    @commands.is_owner()
    async def push(self, ctx: Context):
        try:
            # Execute the shell command
            result = subprocess.run(
                ['git', 'add', '*'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            commit_result = subprocess.run(
                ['git', 'commit', '-m', 'lol'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            push_result = subprocess.run(
                ['git', 'push'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            await ctx.approve(f"```{result.stdout}{commit_result.stdout}{push_result.stdout}```")

        except subprocess.CalledProcessError as e:
            await ctx.warn(f"An error occurred:\n```{e.stderr}```")

    @hybrid_command()
    async def shards(self, ctx: Context):
        """
        Check status of each bot shard
        """

        embed = Embed(
            color=Colors.BASE_COLOR, title=f"Total shards ({self.bot.shard_count})"
        )

        for shard in self.bot.shards:
            guilds = [g for g in self.bot.guilds if g.shard_id == shard]
            users = sum([g.member_count for g in guilds])
            embed.add_field(
                name=f"Shard {shard}",
                value=f"**ping**: {round(self.bot.shards.get(shard).latency * 1000)}ms\n**guilds**: {len(guilds)}\n**users**: {users:,}",
                inline=False,
            )

        await ctx.send(embed=embed)

async def setup(bot: Heal) -> None:
    await bot.add_cog(Owner(bot))
