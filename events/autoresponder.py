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
from tools.managers.ratelimit import ratelimit

class autoresponder(Cog):
    def __init__(self, bot: Heal):
        self.bot = bot

    @commands.Cog.listener()
    @ratelimit(key="{message.author}", limit=3, duration=10, retry=False)
    async def on_message(self, message: discord.Message) -> Message:
        if message.author.bot or not message.guild:
            return


        data = await self.bot.pool.fetch("SELECT * FROM autoresponder WHERE guild_id = $1", message.guild.id)

        for entry in data:
            trigger = entry["trigger"]
            response = entry["response"]

            
            if message.content.lower().startswith(trigger.lower()):
                processed_message = EmbedBuilder.embed_replacement(message.author, response)
                content, embed, view = await EmbedBuilder.to_object(processed_message)

                if content or embed:
                    await message.channel.send(content=content, embed=embed, view=view)
                else:
                    await message.channel.send(content=processed_message)

async def setup(bot: Heal) -> None:
    await bot.add_cog(autoresponder(bot))
