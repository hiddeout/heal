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
import random
import string

class Starboard(Cog):
    def __init__(self, bot: Heal):
        self.bot = bot
        self.user_reactions = {} 
        self.skull_messages = {} 
    
    @group(
        name = "starboard",
        aliases = ["skullboard", "clownboard"],
        description = "Showcase messages in your guild.",
        invoke_without_command = True
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def starboard(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @starboard.command(
        name = "channel",
        aliases = ["chan"],
        description = "Set the starboard channel."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_channels = True)
    async def starboard_channel(self, ctx: Context, *, channel: discord.TextChannel):
        await self.bot.pool.execute("INSERT INTO starboard (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2", ctx.guild.id, channel.id)
        return await ctx.approve(f"Set the **starboard channel** to: {channel.mention}.")
    
    @starboard.command(
        name = "emoji",
        description = "Set the starboard emoji, if not 🌟 will be used."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_channels = True)
    async def starboard_emoji(self, ctx: Context, *, emoji: str):
        try:
            await self.bot.pool.execute("INSERT INTO starboard (guild_id, emoji) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET emoji = $2", ctx.guild.id, emoji)
            return await ctx.approve(f"Set the **starboard emoji** to {emoji}.")
        except Exception as E:
            return await ctx.warn(f"Oopsies! An error occured: **{E}**")
    
    @starboard.command(
        name = "threshold",
        description = "Set the starboard threshold."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_channels = True)
    async def starboard_threshold(self, ctx: Context, *, threshold: int):
        await self.bot.pool.execute("INSERT INTO starboard (guild_id, threshold) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET threshold = $2", ctx.guild.id, threshold)
        return await ctx.approve(f"Set the **starboard threshold** to: {threshold}")
    
    async def get_starboard_config(self, guild_id):
        """Fetch starboard configuration from the database."""
        query = """
        SELECT channel_id, emoji, threshold
        FROM starboard
        WHERE guild_id = $1;
        """
        row = await self.bot.pool.fetchrow(query, guild_id)
        if row:
            channel_id = row['channel_id']
            emoji = row['emoji'] if row['emoji'] else '🌟'  
            threshold = row['threshold']
            return channel_id, emoji, threshold
        return None

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        guild_id = reaction.message.guild.id
        config = await self.get_starboard_config(guild_id)

        if not config:
            return  

        channel_id, emoji, threshold = config

        if str(reaction.emoji) != emoji:
            return 

        message_id = reaction.message.id
        user_id = user.id


        if message_id in self.user_reactions:
            if user_id in self.user_reactions[message_id]:
                return
        else:
            self.user_reactions[message_id] = set()


        self.user_reactions[message_id].add(user_id)

        channel = self.bot.get_channel(channel_id)

        if channel is None:
            return  

        skull_reactions = len(self.user_reactions[message_id])

        if skull_reactions >= threshold:
            embed = discord.Embed(
                title='',
                description=f'{reaction.message.clean_content}',
                color=Colors.BASE_COLOR
            )
            embed.add_field(
                name=f'#{reaction.message.channel}', 
                value=f"**[Jump to message]({reaction.message.jump_url})**",
                inline=False
            )
            embed.set_author(name = f"{reaction.message.author}", icon_url= reaction.message.author.avatar.url)
            if reaction.message.attachments:
                    embed.set_image(url=reaction.message.attachments[0].url)

            try:
                if message_id in self.skull_messages:
                    sent_message = self.skull_messages[message_id]
                    await sent_message.edit(content=f"#{skull_reactions} {emoji}", embed=embed)
                else:
                    sent_message = await channel.send(content=f"#{skull_reactions} {emoji}", embed=embed)
                    self.skull_messages[message_id] = sent_message
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass


async def setup(bot: Heal):
    await bot.add_cog(Starboard(bot))