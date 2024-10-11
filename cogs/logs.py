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

class Logs(commands.Cog):
    def __init__(self, bot: Heal) -> None:
        self.bot = bot

    @group(
        name = "logs",
        aliases = ["logging", "log"],
        description = "Configure logs for your server.",
        invoke_without_command = True
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator = True)
    async def logs(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @logs.command(
        name = "joins",
        aliases = ["on_join", "join"],
        description = "Setup join logs."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator = True)
    async def logs_joins(self, ctx: Context, *, channel: discord.TextChannel = None):
        if channel is None:
            return await ctx.send_help(ctx.command)
        
        data = await self.bot.pool.fetchrow("SELECT joinlogschannel FROM logging WHERE guild_id = $1", ctx.guild.id)
        if data and data.get("joinlogschannel"):
            if data["joinlogschannel"] == channel.id:
                await self.bot.pool.execute("DELETE FROM logging WHERE guild_id = $1", ctx.guild.id)
                return await ctx.approve("Join logs have been disabled.")
        
        await self.bot.pool.execute("INSERT INTO logging (guild_id, joinlogschannel) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET joinlogschannel = $2", ctx.guild.id, channel.id)
        return await ctx.approve(f"Join logs will now be sent to {channel.mention}.")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        res = await self.bot.pool.fetchrow("SELECT * from logging WHERE guild_id = $1", member.guild.id)

        if res:
            channel_id = res["joinlogschannel"]
            channel = member.guild.get_channel(channel_id)
            if channel:
                embed = discord.Embed(title = "Member Joined", description =f"{member.mention} joined. \nCreated: {format_dt(member.created_at, style='f')}", color = Colors.BASE_COLOR)
                embed.set_thumbnail(url = member.avatar.url)
                await channel.send(embed=embed)

    @logs.command(
        name = "leave",
        aliases = ["on_leave"],
        description = "Setup leave logs"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator = True)
    async def logs_leave(self, ctx: Context, *, channel: discord.TextChannel):
        if channel is None:
            return await ctx.send_help(ctx.command)
        
        data = await self.bot.pool.fetchrow("SELECT leavelogschannel FROM logging WHERE guild_id = $1", ctx.guild.id)
        if data and data.get("leavelogschannel"):
            if data["leavelogschannel"] == channel.id:
                await self.bot.pool.execute("DELETE FROM logging WHERE guild_id = $1", ctx.guild.id)
                return await ctx.approve("Leave logs have been disabled.")
        
        await self.bot.pool.execute("INSERT INTO logging (guild_id, leavelogschannel) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET leavelogschannel = $2", ctx.guild.id, channel.id)
        return await ctx.approve(f"Leave logs will now be sent to {channel.mention}.")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        res = await self.bot.pool.fetchrow("SELECT * from logging WHERE guild_id = $1", member.guild.id)

        if res:
            channel_id = res["leavelogschannel"]
            channel = member.guild.get_channel(channel_id)
            if channel:
                embed = discord.Embed(title = "Member Left", description =f"{member.mention} left. \nCreated: {format_dt(member.created_at, style='f')}", color = Colors.BASE_COLOR)
                embed.set_thumbnail(url = member.avatar.url)
                await channel.send(embed=embed)

    @logs.command(
        name = "message",
        aliases = ["messages"],
        description = "Setup message logs"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator = True)
    async def logs_message(self, ctx: Context, *, channel: discord.TextChannel):
        if channel is None:
            return await ctx.send_help(ctx.command)
        
        data = await self.bot.pool.fetchrow("SELECT messagelogschannel FROM logging WHERE guild_id = $1", ctx.guild.id)
        if data and data.get("messagelogschannel"):
            if data["messagelogschannel"] == channel.id:
                await self.bot.pool.execute("DELETE FROM logging WHERE guild_id = $1", ctx.guild.id)
                return await ctx.approve("Message logs have been disabled.")
        
        await self.bot.pool.execute("INSERT INTO logging (guild_id, messagelogschannel) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET messagelogschannel = $2", ctx.guild.id, channel.id)
        return await ctx.approve(f"Message logs will now be sent to {channel.mention}.")

    @commands.Cog.listener()
    @ratelimit(key="{message.guild}", limit=3, duration=10, retry=False)
    async def on_message_delete(self, message: discord.Message):
        res = await self.bot.pool.fetchrow("SELECT * from logging WHERE guild_id = $1", message.guild.id)
        if res:
            channel_id = res["messagelogschannel"]  
            channel = message.guild.get_channel(channel_id)
            if channel:
                embed = discord.Embed(title = f"", description = message.content, color = Colors.BASE_COLOR)
                embed.set_author(name = F"{message.author.name} deleted a message in #{message.channel}.", icon_url = message.author.avatar.url)
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content == after.content:
            return
        res = await self.bot.pool.fetchrow("SELECT * from logging WHERE guild_id = $1", before.guild.id)
        if res:
            channel_id = res["messagelogschannel"]  
            channel = before.guild.get_channel(channel_id)
            if channel:
                embed = discord.Embed(description = "", color = Colors.BASE_COLOR)
                embed.set_author(name = f"{before.author.name} edited a message in #{before.channel}", icon_url = before.author.avatar.url)
                embed.add_field(name="Before", value=before.content, inline=False)
                embed.add_field(name="After", value=after.content, inline=False)
                await channel.send(embed=embed)

    @logs.command(
        name = "voice",
        aliases = ["vc"],
        description = "Setup voice logs"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator = True)
    async def logs_voice(self, ctx: Context, *, channel: discord.TextChannel = None):
        if channel is None:
            return await ctx.send_help(ctx.command)
        
        data = await self.bot.pool.fetchrow("SELECT * FROM logging WHERE guild_id = $1", ctx.guild.id)
        if data and data.get("voicelogschannel"):
            if data["voicelogschannel"] == channel.id:
                await self.bot.pool.execute("DELETE FROM logging WHERE guild_id = $1", ctx.guild.id)
                return await ctx.approve("Voice chat logs have been disabled.")
        
        await self.bot.pool.execute("INSERT INTO logging (guild_id, voicelogschannel) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET voicelogschannel = $2", ctx.guild.id, channel.id)
        return await ctx.approve(f"Voice chat logs will now be sent to {channel.mention}.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        res = await self.bot.pool.fetchrow("SELECT * from logging WHERE guild_id = $1", member.guild.id)

        if res:
            channel_id = res["voicelogschannel"]  
            channel = member.guild.get_channel(channel_id)

            if channel:
                embed = None

                if before.channel is None and after.channel is not None:
                    embed = discord.Embed(
                        description=f"{member.mention} **connected to** {after.channel.mention}",
                        color=Colors.BASE_COLOR
                    )
                    embed.set_author(name = f"{member.name} connected to a voice channel.", icon_url = member.avatar.url)

                elif before.channel is not None and after.channel is None:
                    embed = discord.Embed(
                        description=f"{member.mention} **disconnected from** {before.channel.mention}",
                        color=Colors.BASE_COLOR
                    )
                    embed.set_author(name = f"{member.name} disconnected from a voice channel.", icon_url = member.avatar.url)

                elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
                    embed = discord.Embed(
                        description=f"{member.mention} **moved from** {before.channel.mention} **to** {after.channel.mention}",
                        color=Colors.BASE_COLOR
                    )
                    embed.set_author(name = f"{member.name} moved voice channels.", icon_url = member.avatar.url)

                if not before.self_mute and after.self_mute:
                    embed = discord.Embed(
                        description=f"{member.mention} **muted themselves** in {after.channel.mention}",
                        color=Colors.WARN
                    )
                    embed.set_author(name = f"{member.name} was muted.", icon_url = member.avatar.url)
                elif before.self_mute and not after.self_mute:
                    embed = discord.Embed(
                        description=f"{member.mention} **unmuted themselves** in {after.channel.mention}",
                        color=Colors.APPROVE
                    )
                    embed.set_author(name = f"{member.name} was unmuted.", icon_url = member.avatar.url)


                if not before.self_deaf and after.self_deaf:
                    embed = discord.Embed(
                        description=f"{member.mention} **deafened themselves** in {after.channel.mention}",
                        color=Colors.WARN
                    )
                    embed.set_author(name = f"{member.name} was deafend.", icon_url = member.avatar.url)
                elif before.self_deaf and not after.self_deaf:
                    embed = discord.Embed(
                        description=f"{member.mention} **undeafened themselves** in {after.channel.mention}",
                        color=Colors.APPROVE
                    )
                    embed.set_author(name = f"{member.name} was undeafend.", icon_url = member.avatar.url)

                if embed:
                    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                    await channel.send(embed=embed)

    @logs.command(
        name="list",
        aliases = ["settings"],
        description="List all logging settings and their current status."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def logs_list(self, ctx: Context):
        data = await self.bot.pool.fetchrow("SELECT * FROM logging WHERE guild_id = $1", ctx.guild.id)
        
        join_channel = None
        leave_channel = None
        message_channel = None
        voice_channel = None

        if data:
            join_channel = data.get("joinlogschannel")
            leave_channel = data.get("leavelogschannel")
            message_channel = data.get("messagelogschannel")
            voice_channel = data.get("voicelogschannel")

        embed = discord.Embed(title="Logging Settings", color=Colors.BASE_COLOR)

        embed.add_field(
            name="Joins",
            value=f"{Emojis.APPROVE} {ctx.guild.get_channel(join_channel).mention}" if join_channel else f"{Emojis.DENY} Joins",
            inline=False
        )

        embed.add_field(
            name="Leaves",
            value=f"{Emojis.APPROVE} {ctx.guild.get_channel(leave_channel).mention}" if leave_channel else f"{Emojis.DENY} Leaves",
            inline=False
        )

        embed.add_field(
            name="Messages",
            value=f"{Emojis.APPROVE} {ctx.guild.get_channel(message_channel).mention}" if message_channel else f"{Emojis.DENY} Messages",
            inline=False
        )

        embed.add_field(
            name="Voice",
            value=f"{Emojis.APPROVE} {ctx.guild.get_channel(voice_channel).mention}" if voice_channel else f"{Emojis.DENY} Voice",
            inline=False
        )

        await ctx.send(embed=embed)


async def setup(bot: Heal):
    await bot.add_cog(Logs(bot))