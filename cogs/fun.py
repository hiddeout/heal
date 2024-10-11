import discord
import asyncio
import random
import aiohttp
import uwuipy
import requests

from discord.ext import commands
from discord.ext.commands import (
    command,
    group,
    BucketType,
    cooldown,
    has_permissions,
    hybrid_command,
    hybrid_group,
)

from tools.managers.context import Context, Colors
from tools.heal import Heal
from typing import Union
from random import choice
from tools.configuration import api


class Fun(commands.Cog):
    """
    Commands for when you're bored
    """

    def __init__(self, bot: Heal):
        self.bot = bot
        self.MatchStart = {}
        self.lifes = {}
        self.valid_flavors = [
            "Strawberry",
            "Mango",
            "Blue Raspberry",
            "Pineapple",
            "Grape",
            "Watermelon",
            "Lime",
            "Melon",
            "Apple",
            "Blueberry",
            "Tropical",
        ]

    async def get_string(self):
        lis = await self.get_words()
        word = random.choice(lis)
        return word[:3].lower()

    async def get_words(self):
        async with aiohttp.ClientSession() as cs:
            async with cs.get("https://www.mit.edu/~ecprice/wordlist.100000") as r:
                byte = await r.read()
                data = str(byte, "utf-8")
                return data.splitlines()

    @command(name="blacktea", description="Play a game of blacktea.")
    @cooldown(1, 5, commands.BucketType.user)
    async def blacktea(self, ctx: Context):
        try:
            if self.MatchStart[ctx.guild.id] is True:
                return await ctx.deny(
                    "somebody in this server is already playing blacktea",
                    mention_author=False,
                )
        except KeyError:
            pass

        self.MatchStart[ctx.guild.id] = True
        embed = discord.Embed(
            color=Colors.BASE_COLOR,
            title="BlackTea Matchmaking",
            description=f"⏰ Waiting for players to join. To join react with 🍵.\nThe game will begin in **10 seconds**",
        )
        embed.add_field(
            name="goal",
            value="You have **10 seconds** to say a word containing the given group of **3 letters.**\nIf failed to do so, you will lose a life. Each player has **2 lifes**",
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        mes = await ctx.send(embed=embed)
        await mes.add_reaction("🍵")
        await asyncio.sleep(10)
        me = await ctx.channel.fetch_message(mes.id)
        players = [user.id async for user in me.reactions[0].users()]
        players.remove(self.bot.user.id)

        if len(players) < 2:
            self.MatchStart[ctx.guild.id] = False
            return await ctx.neutral(
                "😦 {}, not enough players joined to start blacktea".format(
                    ctx.author.mention
                ),
                allowed_mentions=discord.AllowedMentions(users=True),
            )

        while len(players) > 1:
            for player in players:
                strin = await self.get_string()
                embed = discord.Embed(
                    description=f"⏰ <@{player}>, type a word containing **{strin.upper()}** in **10 seconds**",
                    color=Colors.BASE_COLOR,
                )
                await ctx.send(embed=embed, content=f"<@{player}>")

                def is_correct(msg):
                    return msg.author.id == player

                try:
                    message = await self.bot.wait_for(
                        "message", timeout=10, check=is_correct
                    )
                except asyncio.TimeoutError:
                    try:
                        self.lifes[player] = self.lifes[player] + 1
                        if self.lifes[player] == 3:
                            await ctx.neutral(
                                f" <@{player}>, you're eliminated ☠️",
                                allowed_mentions=discord.AllowedMentions(users=True),
                            )
                            self.lifes[player] = 0
                            players.remove(player)
                            continue
                    except KeyError:
                        self.lifes[player] = 0
                    await ctx.neutral(
                        f"💥 <@{player}>, you didn't reply on time! **{2-self.lifes[player]}** lifes remaining",
                        allowed_mentions=discord.AllowedMentions(users=True),
                    )
                    continue
                if (
                    not strin.lower() in message.content.lower()
                    or not message.content.lower() in await self.get_words()
                ):
                    try:
                        self.lifes[player] = self.lifes[player] + 1
                        if self.lifes[player] == 3:
                            await ctx.send(
                                f" <@{player}>, you're eliminated ☠️",
                                allowed_mentions=discord.AllowedMentions(users=True),
                            )
                            self.lifes[player] = 0
                            players.remove(player)
                            continue
                    except KeyError:
                        self.lifes[player] = 0
                    await ctx.neutral(
                        f"💥 <@{player}>, incorrect word! **{2-self.lifes[player]}** lifes remaining",
                        allowed_mentions=discord.AllowedMentions(users=True),
                    )
                else:
                    await message.add_reaction("✅")

        await ctx.neutral(
            f"👑 <@{players[0]}> won the game!",
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        self.lifes[players[0]] = 0
        self.MatchStart[ctx.guild.id] = False

    @hybrid_command(name="howgay", aliases=["gayrate", "gay"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def howgay(self, ctx: Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        min = 0
        max = 100
        value = random.randint(min, max)

        await ctx.neutral(f":rainbow_flag: {member.mention} is **{value}%** gay.")

    @hybrid_command(name="howlesbian", aliases=["lesbianrate", "lesbian"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def howlesbian(self, ctx: Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        min = 0
        max = 100
        value = random.randint(min, max)

        await ctx.neutral(
            f"<:lesbian:1271068282652463144> {member.mention} is **{value}%** lesbian."
        )

    @commands.command(name="bible", aliases=["verse"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def bible(self, ctx: Context):
        try:
            response = requests.get(
                "https://labs.bible.org/api/?passage=random&type=json"
            )

            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    verse_text = data[0]["text"]

                    if (
                        "bookname" in data[0]
                        and "chapter" in data[0]
                        and "verse" in data[0]
                    ):
                        book = data[0]["bookname"]
                        chapter = data[0]["chapter"]
                        verse = data[0]["verse"]
                        verse_info = f"{book} {chapter}:{verse}"
                    else:
                        verse_info = "Unknown"

                    embed = discord.Embed(
                        description=verse_text, color=Colors.BASE_COLOR
                    )
                    embed.set_author(
                        name=verse_info,
                        icon_url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR1j_wSogE8gfO35iYFAe-Dpa_qsjNjnpusiQ&s",
                    )
                    return await ctx.send(embed=embed)
                else:
                    await ctx.warn("No data found or empty response.")
            else:
                await ctx.deny("Failed to fetch data from the API.")
        except Exception as e:
            await ctx.warn(f"An error occurred: {e}")

    @hybrid_group(
        name="vape",
        aliases=["juul"],
        description="Vape commands.",
        invoke_without_command=True,
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def vape(self, ctx: Context):

        data = await self.bot.pool.fetchrow(
            "SELECT * FROM vape WHERE user_id = $1", ctx.author.id
        )

        if data is None:
            return await ctx.warn(
                f"You don't have a **vape**. Use `{ctx.clean_prefix}vape flavor <flavor>` to get a vape."
            )

        flavor = data["flavor"]
        embed = discord.Embed(
            description=f"<:juul:1271087027278053407> You have a **{flavor}** vape.",
            color=Colors.BASE_COLOR,
        )
        return await ctx.send(embed=embed)

    @vape.command(
        name="flavors", aliases=["flavours"], description="See a list of vape flavors."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def vape_flavors(self, ctx: Context):

        embed = discord.Embed(
            title="Available vape flavors",
            description="> Strawberry \n> Mango \n> Blue Raspberry \n> Pineapple \n> Grape \n> Watermelon \n> Lime \n> Melon \n> Apple \n> Blueberry \n> Tropical",
            color=Colors.BASE_COLOR,
        )
        return await ctx.reply(embed=embed)

    @vape.command(name="hit", aliases=["smoke"], description="Hit your vape.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def vape_hit(self, ctx: Context):

        data = await self.bot.pool.fetchrow(
            "SELECT * FROM vape WHERE user_id = $1", ctx.author.id
        )
        hits = data["hits"] or 0
        flavor = data["flavor"]

        if data is None:
            return await ctx.deny(
                f"You don't have a **vape**. Use `{ctx.clean_prefix}vape flavor <flavor> to get a vape."
            )

        if data:

            hits += 1
            await self.bot.pool.execute(
                """
                INSERT INTO vape (user_id, hits)
                VALUES ($1, $2)
                ON CONFLICT (user_id)
                DO UPDATE SET hits = $2
                """,
                ctx.author.id,
                hits,
            )
            embed1 = discord.Embed(
                description=f"<:juul:1271087027278053407> **Hitting your vape..**",
                color=Colors.BASE_COLOR,
            )

            msg = await ctx.send(embed=embed1)

            await asyncio.sleep(1)

            embed = discord.Embed(
                description=f"<:juul:1271087027278053407> Hit your **{flavor}** vape. You now have **{hits}** hits.",
                color=Colors.BASE_COLOR,
            )
            await msg.edit(embed=embed)

    @vape.command(
        name="flavor", aliases=["flavour", "set"], description="Set your vape flavor"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def vape_flavor(self, ctx: Context, *, flavor: str = None):
        if flavor is None:
            return await ctx.warn(f"A flavor is needed.")

        flavor = flavor.title()
        if flavor not in self.valid_flavors:
            return await ctx.deny(
                f"Invalid flavor. Use `{ctx.prefix}vape flavors` to see the list of available flavors."
            )

        await self.bot.pool.execute(
            """
            INSERT INTO vape (user_id, flavor)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET flavor = $2
            """,
            ctx.author.id,
            flavor,
        )
        return await ctx.approve(f"Your vape flavor has been set to **{flavor}**.")

    @hybrid_command(name="uwuify", aliases=["uwu"], description="Uwuify a message.")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def uwuify(self, ctx: Context, *, message: str = None):
        if message is None:
            return await ctx.send_help(ctx.command)

        try:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(
                    "https://api.fulcrum.lol/uwu",
                    params={"message": message},
                    headers={"Authorization": api.luma},
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        uwuified_message = data.get("message")
                        if uwuified_message:
                            await ctx.message.delete()
                            await ctx.send(uwuified_message)
                        else:
                            await ctx.send("Failed to retrieve the uwuified message.")
                    else:
                        await ctx.send(
                            f"API request failed with status code: {r.status}"
                        )
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @hybrid_command(name="8ball", description="Ask 8ball a question.")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def eightball(self, ctx: Context, *, question: str):
        responses = [
            "It is certain",
            "Reply hazy, try again",
            "Don't count on it",
            "It is decidedly so",
            "Ask again later",
            "My reply is no",
            "Without a doubt",
            "Better not tell you now",
            "My sources say no",
            "Yes definitely",
            "Cannot predict now",
            "Outlook not so good",
            "You may rely on it",
            "Concentrate and ask again",
            "Very doubtful",
            "As I see it, yes",
            "Most likely",
            "Outlook good",
            "Yes",
            "Signs point to yes",
        ]
        embed = discord.Embed(
            title=f"{question}",
            description=f"{choice(responses)}",
            color=Colors.BASE_COLOR,
        )
        embed.set_author(name=f"{ctx.author}", icon_url=ctx.author.avatar.url)
        return await ctx.reply(embed=embed)


async def setup(bot: Heal):
    return await bot.add_cog(Fun(bot))
