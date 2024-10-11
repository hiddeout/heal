import discord

from discord import Message
from discord.ext import commands
from discord.ext.commands import (
    Cog,
    hybrid_group,
    group
)
from tools.heal import Heal
from tools.managers.context import Context
from tools.configuration import Colors, Emojis
from typing import Union
import asyncio
from tools.managers.embedBuilder import EmbedBuilder, EmbedScript
import logging

class autorole(Cog):
    def __init__(self, bot: Heal):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data =await self.bot.pool.fetchrow("SELECT role_id FROM autorole WHERE guild_id = $1", member.guild.id)

        if data:
            role = member.guild.get_role(data["role_id"])
            if role in member.roles:
                pass
            else:
                await member.add_roles(role)

        else:
            pass

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        command_name = ctx.command.name

        if command_name == "topcmds":
            return

        row = await self.bot.pool.fetchrow('SELECT usage_count FROM topcmds WHERE command_name = $1', command_name)
        
        if row is None:
            await self.bot.pool.execute('INSERT INTO topcmds (command_name, usage_count) VALUES ($1, $2)', command_name, 1)
        else:
            await self.bot.pool.execute('UPDATE topcmds SET usage_count = usage_count + 1 WHERE command_name = $1', command_name)

async def setup(bot: Heal) -> None:
    await bot.add_cog(autorole(bot))