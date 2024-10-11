import discord
import asyncio
import random
import aiohttp
import uwuipy
import requests

from discord.ext import commands
from discord.ext.commands       import command, group, BucketType, cooldown, has_permissions, hybrid_command, hybrid_group, Cog

from tools.managers.context import Context, Colors
from tools.heal import Heal
from typing import Union
from random import choice
from tools.configuration import api, Emojis

def has_br_role():
    async def predicate(ctx: Context): 
        check = await ctx.bot.pool.fetchrow("SELECT * FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
        if not check: 
            await ctx.warn(f"You do not have a booster role set\nPlease use `{ctx.clean_prefix}br create` to create a booster role") 
        return check is not None
    return commands.check(predicate)

def level2():
    async def predicate(ctx: Context):
        if ctx.guild is not None and ctx.guild.premium_tier >= 2:
            return True
        else:
            await ctx.warn("This guild doesn't have level 2 boosts.")
            return False
    return commands.check(predicate)

def br_enabled():
    async def predicate(ctx: Context):
        check = await ctx.bot.pool.fetchrow("SELECT 1 FROM booster_module WHERE guild_id = $1", ctx.guild.id)
        
        if check:
            return True
        else:
            await ctx.warn("The booster role module is not enabled in this guild.")
            return False

    return commands.check(predicate)

class Boosterrole(commands.Cog):
    def __init__(self, bot: Heal):
        self.bot = bot

    @Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self.bot.pool.execute("DELETE FROM br_award WHERE role_id = $1", role.id)

    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if(
            not before.guild.premium_subscriber_role in before.roles 
            and before.guild.premium_subscriber_role in after.roles
        ):
            if results := await self.bot.pool.fetchrow("SELECT role_id FROM br_award WHERE guild_id = $1", before.guild.id):
                roles = [
                    after.guild.get_role(result["role_id"])
                    for result in results
                    if after.guild.get_role(result["role_id"]).is_assignable()
                ]
                await asyncio.gather(
                    *[
                        after.add_roles(role, reason = "Booster role created")
                        for role in roles
                    ]
                )
            elif(
                before.guild.premium_subscriber_role in before.roles 
                and not after.guild.premium_subscriber_role in after.roles
            ):
                if results := await self.bot.pool.fetchrow("SELECT role_id FROM br_award WHERE guild_id = $1", before.guild.id):
                    roles = [
                        after.guild.get_role(result["role_id"]
                        for result in results 
                        if after.guild.get_role(result["role_id"]).is_assignable()
                        and after.guild.get_role(result["role_id"]) in after.roles
                        )
                    ]

                    await asyncio.gather (
                        *[
                            after.remove_roles(
                                role, reason = "Removed booster role from this member."
                            )
                            for role in roles
                        ]
                    )

    @commands.group(
        name = "boosterrole",
        aliases = ["br"],
        description = "Configure boosterroles in your guild.",
        invoke_without_command = True
    )
    @cooldown(1, 5, commands.BucketType.user)
    async def boosterrole(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @boosterrole.command(
        name = "setup",
        aliases = ["enable"],
        description = "Enable the booster role module in your guild."
    )
    @cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_guild = True)
    async def boosterrole_setup(self, ctx: Context):
        if await self.bot.pool.fetchrow("SELECT * FROM booster_module WHERE guild_id = $1", ctx.guild.id):
            return await ctx.warn("The booster role module is already enabled in this guild.")
        
        premium_role = ctx.guild.premium_subscriber_role
        if premium_role is None:
            premium_role = ctx.guild.default_role

        await self.bot.pool.execute("INSERT INTO booster_module (guild_id, base) VALUES ($1, $2)", ctx.guild.id, premium_role.id)
        return await ctx.approve(f"The booster role module has been enabled.")
    
    @boosterrole.command(
        name = "disable",
        description = "Disable the booster role module in your guild."
    )
    @cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_guild = True)
    async def boosterrole_disable(self, ctx: Context):
        await self.bot.pool.execute("DELETE FROM booster_module WHERE guild_id = $1", ctx.guild.id)
        await self.bot.pool.execute("DELETE FROM booster_roles WHERE guild_id = $1", ctx.guild.id)
        return await ctx.approve(f"Disabled the booster role module.")

    @boosterrole.command(
        name = "base",
        description = "Set the base for the booster role."
    )
    @cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_guild = True)
    async def boosterrole_base(self, ctx: Context, *, role: discord.Role = None):
        check = await self.bot.pool.fetchrow("SELECT base FROM booster_module WHERE guild_id = $1", ctx.guild.id)
        if role is None:
            if check is None:
                return await ctx.warn(f"The booster role base role isn't set.")
            
            await self.bot.pool.execute("UPDATE booster_module SET base = $1 WHERE guild_id = $2", None, ctx.guild.id)
            return await ctx.approve(f"Removed the booster role base.")

        await self.bot.pool.execute("UPDATE booster_module SET base = $1 WHERE guild_id = $2", role.id, ctx.guild.id)
        return await ctx.approve(f"Set the booster role base to: {role.mention}")

    @boosterrole.command(
        name = "create",
        description = "Create your booster role."
    )
    @br_enabled()
    @cooldown(1, 5, commands.BucketType.user)
    async def boosterrole_create(self, ctx: Context, * ,name: str = None):
        if not ctx.author.premium_since:
            return await ctx.warn(f"You need to boost this server in order to use this command.")
        check = await self.bot.pool.fetchrow("SELECT base FROM booster_module WHERE guild_id = $1", ctx.guild.id)

        if not name:
            name = f"{ctx.author.name}'s role"

        if await self.bot.pool.fetchrow("SELECT * FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id):
            return await ctx.warn("You already have a booster role.")
        
        base = ctx.guild.get_role(check)
        role = await ctx.guild.create_role(name=name, reason = f"{ctx.author} created their booster role.")
        await role.edit(position= base.position if base is not None else 1)
        await ctx.author.add_roles(role)
        await self.bot.pool.execute("INSERT INTO booster_roles VALUES ($1,$2,$3)", ctx.guild.id, ctx.author.id, role.id)
        return await ctx.approve("Booster role has been created.")

    @boosterrole.command(
        name = "name",
        description = "Rename your boosterrole."
    )
    @cooldown(1, 5, commands.BucketType.user)
    @has_br_role()
    async def boosterrole_name(self, ctx: Context, *, name: str):

        if len(name) > 32:
            return await ctx.warn("The booster role name can't be more than **32** characters long.")
        
        role = ctx.guild.get_role(
            await self.bot.pool.fetchval("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
        )
        if not role:
            return await ctx.warn(f"You don't have a booster role setup. Use `{ctx.clean_prefix}br create` to create one.")
        
        await role.edit(name=name, reason = f"{ctx.author.name} edited their booster role.")
        return await ctx.approve(f"Renamed your booster role to **{name}**")
    
    @boosterrole.command(
        name = "colour",
        aliases = ["color"],
        description = "Set your booster role's color."
    )
    @cooldown(1, 5, commands.BucketType.user)
    @has_br_role()
    async def boosterrole_colour(self, ctx: Context, *, color: str):
        if color.startswith("#"):
            color = color[1:]

        try:
            discord_color = discord.Color(int(color, 16))
        except ValueError:
            return await ctx.deny("You need to enter a valid hex code. Example: #47C1BC")

        role = ctx.guild.get_role(await self.bot.pool.fetchval("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id))
        if not role:
            return await ctx.warn(f"You don't have a booster role setup. Use `{ctx.clean_prefix}br create` to create one.")
        
        await role.edit(color=discord_color, reason=f"{ctx.author} edited their booster role.")
        return await ctx.send(embed=discord.Embed(description=f"{Emojis.APPROVE} {ctx.author.mention}: Edited the role's color to {color}", color=discord_color))
    
    @boosterrole.command(
        name = "icon",
        description = "Set your booster role icon."
    )
    @cooldown(1, 5, commands.BucketType.user)
    @has_br_role()
    @level2()
    async def boosterrole_icon(self, ctx: Context, *, icon: Union[discord.PartialEmoji, str]):
        role = ctx.guild.get_role(await self.bot.pool.fetchval("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id))
        if not role:
            return await ctx.warn(f"You don't have a booster role setup. Use `{ctx.clean_prefix}br create` to create one.")
        
        await role.edit(display_icon= (await icon.read() if isinstance(icon, discord.PartialEmoji) else icon), reason = f"{ctx.author} edited their booster role")
        return await ctx.approve(f"Booster role icon has been set to {icon.name if isinstance(icon, discord.PartialEmoji) else icon}")
    
    @boosterrole.command(
        name = "delete",
        description = "Delete your booster role."
    )
    @cooldown(1, 5, commands.BucketType.user)
    @has_br_role()
    async def boosterrole_delete(self, ctx: Context):
        role = ctx.guild.get_role(await self.bot.pool.fetchval("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id))
        if not role:
            return await ctx.warn(f"You don't have a booster role setup. Use `{ctx.clean_prefix}br create` to create one.")
        
        await role.delete(reason=f"{ctx.author} deleted their booster role.")
        await self.bot.pool.execute("DELETE FROM booster_roles WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, ctx.author.id)
        return await ctx.approve(f"Your booster role has been deleted.")

async def setup(bot: Heal):
    await bot.add_cog(Boosterrole(bot))
