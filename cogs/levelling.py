import discord
import sys
import humanfriendly
import re 
import datetime

from tools.managers.context     import Context
from discord.ext.commands       import command, group, BucketType, has_permissions
from tools.configuration        import Emojis, Colors
from tools.paginator            import Paginator
from discord.utils              import format_dt
from discord.ext                import commands
from tools.heal                 import Heal
import asyncio
from typing import Union
from collections import defaultdict
import typing
import json
from humanfriendly import format_timespan
import os
from tools.managers.ratelimit import ratelimit

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def calculate_level(self, message_count):
        level = 1
        while message_count >= (5 * (level ** 2) + 50 * level + 100):
            message_count -= (5 * (level ** 2) + 50 * level + 100)
            level += 1
        next_level_req = (5 * (level ** 2) + 50 * level + 100) - message_count
        return level, next_level_req

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_settings = await self.bot.pool.fetchrow(
            "SELECT leveling_enabled FROM guild_settings WHERE guild_id = $1",
            message.guild.id
        )
        
        if not guild_settings or not guild_settings['leveling_enabled']:
            return

        user_id = message.author.id

        user_data = await self.bot.pool.fetchrow(
            "SELECT * FROM levels WHERE user_id = $1",
            user_id
        )

        if user_data:
            new_message_count = user_data['message_count'] + 1
            await self.bot.pool.execute(
                "UPDATE levels SET message_count = $1 WHERE user_id = $2",
                new_message_count, user_id
            )
        else:
            new_message_count = 1
            await self.bot.pool.execute(
                "INSERT INTO levels (user_id, message_count, level) VALUES ($1, $2, $3)",
                user_id, new_message_count, 1
            )

        new_level, _ = self.calculate_level(new_message_count)

        if new_level > (user_data['level'] if user_data else 1):
            await self.bot.pool.execute(
                "UPDATE levels SET level = $1 WHERE user_id = $2",
                new_level, user_id
            )
            embed = discord.Embed(
                description=f"Congratulations {message.author.mention}, you have reached level {new_level}!",
                color=Colors.BASE_COLOR
            )
            await message.reply(embed=embed)

    @commands.command(name="levels", description="Displays the global leaderboard for levels.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leaderboard(self, ctx: Context):
        top_users = await self.bot.pool.fetch(
            "SELECT * FROM levels ORDER BY level DESC, message_count DESC LIMIT 10"
        )

        leaderboard = []
        for user_data in top_users:
            user = await self.bot.fetch_user(user_data["user_id"])
            leaderboard.append((user.display_name, user_data["level"], user_data["message_count"]))

        if leaderboard:
            leaderboard_message = "Top 10 Users\n"
            for rank, (name, level, message_count) in enumerate(leaderboard, start=1):
                leaderboard_message += f"{rank}. {name} - Level {level} with {message_count} messages\n"
            await ctx.neutral(leaderboard_message)
        else:
            await ctx.deny("There is no one on the leaderboard.")

    @commands.group(
        name="levelling",
        aliases=["level"],
        invoke_without_command=True
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def levelling(self, ctx: Context):
        """Show level information for a user or self."""
        member = ctx.message.mentions[0] if ctx.message.mentions else ctx.author

        user_data = await self.bot.pool.fetchrow(
            "SELECT * FROM levels WHERE user_id = $1",
            member.id
        )

        if user_data:
            level, next_level_req = self.calculate_level(user_data['message_count'])
            embed = discord.Embed(description=f"{member} is at level {level}.", color=Colors.BASE_COLOR)
            await ctx.send(embed=embed)
        else:
            await ctx.deny(f"{member.display_name} has no messages recorded.")

    @levelling.command(
        name="enable",
        description="Enable leveling in your guild."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def enable_leveling(self, ctx: Context):
        await self.bot.pool.execute(
            """
            INSERT INTO guild_settings (guild_id, leveling_enabled)
            VALUES ($1, TRUE)
            ON CONFLICT (guild_id)
            DO UPDATE SET leveling_enabled = TRUE
            """,
            ctx.guild.id
        )
        await ctx.approve(f"Leveling has been enabled successfully.")

    @levelling.command(
        name="disable",
        description="Disable leveling in your guild."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def disable_leveling(self, ctx: Context):
        await self.bot.pool.execute(
            """
            INSERT INTO guild_settings (guild_id, leveling_enabled)
            VALUES ($1, TRUE)
            ON CONFLICT (guild_id)
            DO UPDATE SET leveling_enabled = False
            """,
            ctx.guild.id
        )
        await ctx.approve(f"Leveling has been disabled successfully.")

async def setup(bot):
    await bot.add_cog(Leveling(bot))
