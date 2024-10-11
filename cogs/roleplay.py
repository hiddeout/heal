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

from tools.heal import Heal
from tools.managers.context import Context, Emojis, Colors

class Roleplay(Cog):
    def __init__(self, bot: Heal) -> None:
        self.bot = bot

    @command(
        name = "hug",
        description = "Hugs a user."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hug(self, ctx: Context, *, user: Union[discord.Member, discord.User] = None):
        if user is None:
            return await ctx.deny("You cannot hug yourself, looser.")
        

        url = "https://nekos.best/api/v2/hug"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
                    embed = discord.Embed(description = f"Aww {ctx.author.mention} **hugged** {user.name}", color = Colors.BASE_COLOR)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)

    @command(
        name = "kiss",
        description = "Kisses a user."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def kiss(self, ctx: Context, *, user: Union[discord.Member, discord.User] = None):
        if user is None:
            return await ctx.deny("You cannot kiss yourself, looser.")
        
        url = "https://nekos.best/api/v2/kiss"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
                    embed = discord.Embed(description = f"Aww {ctx.author.mention} **kissed** {user.name}", color = Colors.BASE_COLOR)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)

    @command(
        name = "slap",
        description = "Slaps a user."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def slap(self, ctx: Context, *, user: Union[discord.Member, discord.User] = None):
        if user is None:
            return await ctx.deny("You cannot slap yourself.")
        

        url = "https://nekos.best/api/v2/slap"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
                    embed = discord.Embed(description = f"{ctx.author.mention} **slapped** {user.name}", color = Colors.BASE_COLOR)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)

    @command(
        name = "shoot",
        description = "Shoots a user."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shoot(self, ctx: Context, *, user: Union[discord.Member, discord.User] = None):
        if user is None:
            return await ctx.deny("You cannot shoot yourself.")
        

        url = "https://nekos.best/api/v2/shoot"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
                    embed = discord.Embed(description = f"{ctx.author.mention} **shot** {user.name}", color = Colors.BASE_COLOR)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)
    
    @command(
        name = "stare",
        description = "Stare at a user."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stare(self, ctx: Context, *, user: Union[discord.Member, discord.User] = None):
        if user is None:
            return await ctx.deny("You cannot stare at yourself, looser.")
        

        url = "https://nekos.best/api/v2/stare"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
                    embed = discord.Embed(description = f"{ctx.author.mention} **stares** {user.name}", color = Colors.BASE_COLOR)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)
    
    @command(
        name = "wave",
        description = "Wave at a user."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def wave(self, ctx: Context, *, user: Union[discord.Member, discord.User] = None):
        if user is None:
            return await ctx.deny("You cannot wave to yourself, looser.")
        

        url = "https://nekos.best/api/v2/wave"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
                    embed = discord.Embed(description = f"{ctx.author.mention} **waves to** {user.name}", color = Colors.BASE_COLOR)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)

    @command(
        name = "poke",
        description = "Poke a user."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def poke(self, ctx: Context, *, user: Union[discord.Member, discord.User] = None):
        if user is None:
            return await ctx.deny("You cannot poke yourself, looser.")
        

        url = "https://nekos.best/api/v2/poke"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
                    embed = discord.Embed(description = f"{ctx.author.mention} **poked** {user.name}", color = Colors.BASE_COLOR)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)

    @command(
        name = "wink",
        description = "Wink at a user."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def wink(self, ctx: Context, *, user: Union[discord.Member, discord.User] = None):
        if user is None:
            return await ctx.deny("You cannot wink at yourself, looser.")
        

        url = "https://nekos.best/api/v2/wink"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
                    embed = discord.Embed(description = f"{ctx.author.mention} **winked at** {user.name}", color = Colors.BASE_COLOR)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)

    @command(
        name = "tickle",
        description = "Tickle a user."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tickle(self, ctx: Context, *, user: Union[discord.Member, discord.User] = None):
        if user is None:
            return await ctx.deny("You cannot tickle yourself, looser.")
        

        url = "https://nekos.best/api/v2/tickle"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
                    embed = discord.Embed(description = f"{ctx.author.mention} **tickled** {user.name}", color = Colors.BASE_COLOR)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)

    @command(
        name = "feed",
        description = "Feed a user."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def feed(self, ctx: Context, *, user: Union[discord.Member, discord.User] = None):
        if user is None:
            return await ctx.deny("You cannot feed yourself, looser.")
        

        url = "https://nekos.best/api/v2/feed"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gif_url = data['results'][0]['url']
                    embed = discord.Embed(description = f"{ctx.author.mention} **feeds** {user.name}", color = Colors.BASE_COLOR)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)

async def setup(bot: Heal) -> None:
    await bot.add_cog(Roleplay(bot))