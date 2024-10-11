import discord
import sys
import humanfriendly
import re 
import datetime
from discord import AutoModTrigger, AutoModRuleTriggerType, AutoModRuleAction, AutoModRuleEventType
from tools.managers.context     import Context
from discord.ext.commands       import command, group, BucketType, has_permissions
from tools.configuration        import Emojis, Colors
from tools.paginator            import Paginator
from discord.utils              import format_dt
from discord.ext                import commands
from tools.heal                 import Heal
from tools.managers.embedBuilder import EmbedBuilder, EmbedScript
import asyncio
from typing import Union
from collections import defaultdict
import typing
import json
from humanfriendly import format_timespan
import os

async def send_modlog(bot: Heal, action: str, moderator: discord.Member, vict: Union[discord.Member, discord.User], reason: str):
    settings = await bot.pool.fetchrow("SELECT channel_id FROM modlogs WHERE guild_id = $1", moderator.guild.id)
    
    if settings and "channel_id" in settings:
        res = await bot.pool.fetchrow("SELECT count FROM cases WHERE guild_id = $1", moderator.guild.id)
        if res is None:
            await bot.pool.execute("INSERT INTO cases (guild_id, count) VALUES ($1, $2)", moderator.guild.id, 0)
            casenum = 1 
        else:
            casenum = int(res['count']) + 1
            await bot.pool.execute("UPDATE cases SET count = $1 WHERE guild_id = $2", casenum, moderator.guild.id)
        
        await bot.pool.execute("UPDATE cases SET count = $1 WHERE guild_id = $2", casenum, moderator.guild.id)
        
        embed = discord.Embed(title=f"{action} -> case #{casenum}", color=Colors.BASE_COLOR, timestamp=datetime.datetime.now())
        embed.add_field(name="Moderator:", value=f"{moderator.name} ({moderator.id})", inline = True)
        embed.add_field(name="Victim:", value=f"{vict.name} ({vict.id})", inline = False)
        embed.add_field(name="Reason:", value=f"{reason}", inline = False)
        embed.set_thumbnail(url = moderator.avatar.url)

        try:
            logschan = moderator.guild.get_channel(settings['channel_id'])
            if logschan:
                await logschan.send(embed=embed)
        except:
            pass

class Moderation(commands.Cog):
    """
    Moderation commands.
    """
    def __init__(self, bot: Heal) -> None:
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)
        self.role_lock = defaultdict(asyncio.Lock)


    @command(
        name = "lock",
        usage = "lock #channel"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_channels = True)
    async def lock(self, ctx: Context, *, channel: discord.TextChannel = None):

        if channel is None:
            channel = ctx.channel

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.approve('Channel has been locked.')

    @command(
        name = "unlock",
        usage = "unlock #channel"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_channels = True)
    async def unlock(self, ctx: Context, *, channel: discord.TextChannel = None):

        if channel is None:
            channel = ctx.channel

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.approve('Channel has been unlocked.')

    @command(
        name = "kick",
        aliases = ["getout", "bye"]
    )
    @commands.cooldown(1, 5, BucketType.user)
    @has_permissions(moderate_members=True)
    async def kick(self, ctx: Context, user: Union[discord.Member, discord.User], *, reason: str = "no reason"):
        reason += f' | executed by {ctx.author}'
        await ctx.typing()

        if isinstance(user, discord.Member):
            if user == ctx.guild.owner:
                return await ctx.warn(f"You're unable to kick the **server owner**.")
            if user == ctx.author:
                return await ctx.warn(f"You're unable to kick **yourself**.")
            if ctx.author.top_role.position <= user.top_role.position:
                return await ctx.warn(f"You're unable to kick a user with a **higher role** than **yourself**.")

        await user.kick(reason=reason)

        data = await self.bot.pool.fetchrow("SELECT * FROM invoke WHERE guild_id = $1 AND type = $2", ctx.guild.id, "kick")

        if data and "message" in data:
            message = data["message"]
            processed_message = EmbedBuilder.embed_replacement(user, message)
            content, embed, view = await EmbedBuilder.to_object(processed_message)

            if content or embed:
                await ctx.channel.send(content=content, embed=embed, view=view)
            else:
                await ctx.channel.send(content=processed_message)
        
        if data is None:
            await ctx.approve(f'Successfully kicked {user.mention} for {reason.split(" |")[0]}')

        await send_modlog(self.bot, "kick", ctx.author, user, reason)
        
    @command(
        name = "ban",
        aliases = ["fuckoff", "banish"]
    )
    @commands.cooldown(1, 5, BucketType.user)
    @has_permissions(ban_members=True)
    async def ban(self, ctx: Context, user: Union[discord.Member, discord.User], *, reason: str = "no reason"):
        
        reason += f' | executed by {ctx.author}'
        await ctx.typing()

        if isinstance(user, discord.Member):
            if user == ctx.guild.owner:
                return await ctx.warn(f"You're unable to ban the **server owner**.")
            if user == ctx.author:
                return await ctx.warn(f"You're unable to ban **yourself**.")
            if ctx.author.top_role.position <= user.top_role.position:
                return await ctx.warn(f"You're unable to ban a user with a **higher role** than **yourself**.")
                
        await ctx.guild.ban(user, reason=reason)

        data = await self.bot.pool.fetchrow("SELECT * FROM invoke WHERE guild_id = $1 AND type = $2", ctx.guild.id, "ban")

        if data and data["message"]:
            message = data["message"]
            processed_message = EmbedBuilder.embed_replacement(user, message)
            content, embed, view = await EmbedBuilder.to_object(processed_message)

            if content or embed:
                await ctx.channel.send(content=content, embed=embed, view=view)
            else:
                await ctx.channel.send(content=processed_message)
        
        if data is None:
            await ctx.approve(f'Successfully banned {user.mention} for {reason.split(" |")[0]}')
        
        await send_modlog(self.bot, "ban", ctx.author, user, reason)
    
        
    @commands.command(name='mute', description='mute a user in your server', brief='-mute <user> <time> <reason>')
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def mute(self, ctx: Context, user: discord.Member, time: str="60s", *, reason: str = "No reason provided"):
        
        if user.id == self.bot.user.id:
            return await ctx.deny("I cannot **mute** myself.")

        if user.id == ctx.author.id:
            return await ctx.deny("You cannot **mute** yourself.")


        member = ctx.guild.get_member(user.id)
        if member:

            if ctx.author.id != ctx.guild.owner_id:
                if member.top_role.position >= ctx.guild.me.top_role.position:
                    return await ctx.warn("You cannot **mute** a member with a higher role than me.")
                if member.top_role.position >= ctx.author.top_role.position:
                    return await ctx.warn("You cannot **mute** a member with a higher role than you.")
        else:
            pass
        
        time = humanfriendly.parse_timespan(time)

        await user.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=time), reason=reason)

        data = await self.bot.pool.fetchrow("SELECT * FROM invoke WHERE guild_id = $1 AND type = $2", ctx.guild.id, "mute")

        if data and data["message"]:
            message = data["message"]
            processed_message = EmbedBuilder.embed_replacement(user, message)
            content, embed, view = await EmbedBuilder.to_object(processed_message)

            if content or embed:
                await ctx.channel.send(content=content, embed=embed, view=view)
            else:
                await ctx.channel.send(content=processed_message)
        if data is None:
            await ctx.approve(f'Muted **{user}** for `{humanfriendly.format_timespan(time)}` - **{reason}**')

        await send_modlog(self.bot, "mute", ctx.author, user, reason)

    
    @commands.command(name='unmute', description='ummute a user in your server', brief='-ummute <user> <reason>')
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def unmute(self, ctx: Context, user: discord.Member, *, reason: str = "No reason provided"):
        
        if user.id == self.bot.user.id:
            return await ctx.deny("I cannot **unmute** myself.")

        if user.id == ctx.author.id:
            return await ctx.deny("You cannot **unmute** yourself.")


        member = ctx.guild.get_member(user.id)
        if member:

            if ctx.author.id != ctx.guild.owner_id:
                if member.top_role.position >= ctx.guild.me.top_role.position:
                    return await ctx.warn("You cannot **unmute** a member with a higher role than me.")
                if member.top_role.position >= ctx.author.top_role.position:
                    return await ctx.warn("You cannot **unmute** a member with a higher role than you.")
        else:
            pass
        

        await user.timeout(None, reason=reason)

        data = await self.bot.pool.fetchrow("SELECT * FROM invoke WHERE guild_id = $1 AND type = $2", ctx.guild.id, "unmute")

        if data and data["message"]:
            message = data["message"]
            processed_message = EmbedBuilder.embed_replacement(user, message)
            content, embed, view = await EmbedBuilder.to_object(processed_message)

            if content or embed:
                await ctx.channel.send(content=content, embed=embed, view=view)
            else:
                await ctx.channel.send(content=processed_message)
        if data is None:
            await ctx.approve(f"**Unmuted {user}**")
        await send_modlog(self.bot, "unmute", ctx.author, user, reason)
    
    @commands.command(
    name="forcenickname",
    aliases=["fn"],
    description="force a nickname upon a user."
    )
    @commands.has_permissions(moderate_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def forcenickname(self, ctx: Context, user: discord.Member, *, name: str = None):
        if name is None:
            check = await self.bot.pool.fetchrow(
                "SELECT name FROM forcenick WHERE guild_id = $1 AND user_id = $2",
                ctx.guild.id, user.id
            )
            if check and check["name"]:
                await self.bot.pool.execute(
                    "DELETE FROM forcenick WHERE guild_id = $1 AND user_id = $2",
                    ctx.guild.id, user.id
                )
                await user.edit(nick=None)
                return await ctx.approve(f"Removed the **forced nickname** from {user.mention}!")
            else:
                return await ctx.deny(f"No forced nickname found for {user.mention}.")
        else:
            check = await self.bot.pool.fetchrow("SELECT * FROM forcenick WHERE user_id = $1 AND guild_id = $2", user.id, ctx.guild.id)               
            if check is None: 
                await self.bot.pool.execute("INSERT INTO forcenick VALUES ($1,$2,$3)", ctx.guild.id, user.id, name)
            else: 
                await self.bot.pool.execute("UPDATE forcenick SET name = $1 WHERE user_id = $2 AND guild_id = $3", name, user.id, ctx.guild.id)  
            await user.edit(nick=name)
            await send_modlog(self.bot, "force nickname", ctx.author, user, reason = "Forced nickname.")
            return await ctx.approve(f"Forced **{user.name}'s** nickname to be **`{name}`**!")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
      if str(before.nick) != str(after.nick): 
        check = await self.bot.pool.fetchrow("SELECT name FROM forcenick WHERE user_id = $1 AND guild_id = $2", before.id, before.guild.id)   
        if check: 
            return await before.edit(nick=check['name'])

    @commands.command(
        name = "purge",
        description = "Purge messages."
    )
    @commands.has_permissions(manage_messages = True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def purge(self, ctx: Context, *, amount: int):
        await ctx.message.delete()
        await ctx.channel.purge(limit=amount)
        await send_modlog(self.bot, "purge", ctx.author, vict= ctx.author ,reason = "purged")
        purgemsg = await ctx.approve(f"**Successfully** purged {amount} messages.")
        await asyncio.sleep(2)
        await purgemsg.delete()

    @group(
        name = "role",
        description = "Add / remove a role from a user.",
        aliases = ["r"],
        invoke_without_command=True
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx: Context, member: discord.Member, *, role: Union[discord.Role, str]):

        if isinstance(role, str):
            role = ctx.guild.get_role(role)
        
        if role is None:
            return await ctx.warn('please provide a **valid** role.')

        if role in member.roles:
            await member.remove_roles(role)
            await ctx.approve(f"Removed {role.mention} from {member.name}")
            await send_modlog(self.bot, "role removed", ctx.author, member, reason = "role removed.")
        else:
            await member.add_roles(role)
            await send_modlog(self.bot, "role added", ctx.author, member, reason = "role added.")
            await ctx.approve(f"Added {role.mention} to {member.name}")


    @role.command(name="create", description="Create a new role in the server.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    async def role_create(self, ctx: Context, *, name: str):
        role = await ctx.guild.create_role(name=name)
        await ctx.approve(f"Created new role: {role.mention}")

    @role.command(name="delete", description="Delete an existing role from the server.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    async def role_delete(self, ctx: Context, *, role: Union[discord.Role, str]):
        if isinstance(role, str):
            role = discord.utils.get(ctx.guild.roles, name=role)

        if role is None:
            return await ctx.warn('Please provide a **valid** role to delete.')

        await role.delete()
        await ctx.approve(f"Deleted role: **{role.name}**")

    @role.command(name="rename", description="Rename an existing role in the server.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_roles=True)
    async def role_rename(self, ctx: Context, role: Union[discord.Role, str], *, name: str):
        if isinstance(role, str):
            role = discord.utils.get(ctx.guild.roles, name=role)

        if role is None:
            return await ctx.warn('Please provide a **valid** role to rename.')

        old_name = role.name
        await role.edit(name=name)
        await ctx.approve(f"Renamed role **{old_name}** to **{name}**")




    @commands.command(description="Adds an emoji to your server", usage="steal [emoji] <name>", aliases = ["steal"])
    @commands.has_permissions(manage_expressions = True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def addemoji(self, ctx: Context, emoji: Union[discord.Emoji, discord.PartialEmoji] = None, *, name: str=None):
        if not emoji:
            return await ctx.send_help(ctx.command)
        if not name: 
            name = emoji.name
            emoji = await ctx.guild.create_custom_emoji(image= await emoji.read(), name=name)
            return await ctx.approve(f"added {emoji} as `{name}`")

    @commands.command(
        name = "pin",
        description = "Pins the message you reply to."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_messages = True)
    async def pin(self, ctx: Context, *, link: str = None):
        message = None

        if ctx.message.reference:
            message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        elif link:
            pattern = re.compile(r'https://discord.com/channels/(\d+)/(\d+)/(\d+)')
            match = pattern.match(link)
            if match:
                guild_id, channel_id, message_id = map(int, match.groups())
                if guild_id == ctx.guild.id:
                    channel = ctx.guild.get_channel(channel_id)
                    if channel:
                        message = await channel.fetch_message(message_id)

        if message:
            try:
                await message.pin()
            except discord.Forbidden:
                await ctx.warn("I do not have permission to pin messages.")
            except discord.HTTPException as e:
                await ctx.warn(f"Failed to pin the message: {e}")
        else:
            return await ctx.send_help(ctx.command)
        
    @command(
        name = "roleall",
        description = "Gives a role to all users."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_roles = True)
    async def roleall(self, ctx: Context, *, role: discord.Role = None):
        """
        add a role to all members
        """
        if role is None:
            return await ctx.send_help(ctx.command)
        async with self.role_lock[ctx.guild.id]:
            tasks = [
                m.add_roles(role, reason=f"Role all invoked by {ctx.author}")
                for m in ctx.guild.members
                if not role in m.roles
            ]

            if len(tasks) == 0:
                return await ctx.warn(f"Everyone has this role")

            mes = await ctx.neutral(
                f"Giving {role.mention} to **{len(tasks)}** members. This may take around **{format_timespan(0.3*len(tasks))}**"
            )

            await asyncio.gather(*tasks)
            return await mes.edit(
                embed=discord.Embed(
                    color= Colors.BASE_COLOR,
                    description=f"Added {role.mention} to **{len(tasks)}** members",
                )
            )

    @commands.command(
        name="nuke",
        description="Nukes a channel."
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nuke(self, ctx: Context, *, channel: discord.TextChannel = None):
        """
        Clone a channel and delete the original one.
        """
        if channel is None:
            channel = ctx.channel

        embed = discord.Embed(description = f"{Emojis.WARN} {ctx.author.mention}: Are you sure you want to nuke this channel?", color = Colors.WARN)

        view = Confirm(ctx, channel)
        await ctx.send(embed=embed, view=view)
        await send_modlog(self.bot, "channel nuked", ctx.author, channel, reason = "Channel nuked.")

    @command(
        name = "imute",
        aliases = ["imgmute", "imagemute"],
        description = "Remove image permissions from a user in a channel."
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def imute(self, ctx: Context, member: discord.Member, channel : discord.TextChannel=None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(member)
        overwrite.attach_files = False
        overwrite.embed_links = False
        await channel.set_permissions(member, overwrite=overwrite)
        await send_modlog(self.bot, "image mute", ctx.author, member, reason = "image muted user.")
        await ctx.approve(f"Removed media permissions from **{member.mention}** in {channel.mention}.")
    
    @command(
        name = "iunmute",
        aliases = ["imgunmute", "imageunmute"],
        description = "Restore someones image permissions in a channel."
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def iunmute(self, ctx: Context, member: discord.Member, channel : discord.TextChannel=None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(member)
        overwrite.attach_files = True
        overwrite.embed_links = True
        await channel.set_permissions(member, overwrite=overwrite)
        await send_modlog(self.bot, "image unmute", ctx.author, member, reason = "restored users image perms")
        await ctx.approve(f"Restored media permissions to **{member.mention}** in {channel.mention}.")

    @commands.group(
        name = "thread",
        aliases = ["thr"],
        description = "Thread settings.",
        invoke_without_command = True
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_threads = True)
    async def thread(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @thread.command(
        name = "rename",
        aliases = ["name"],
        description = "Renames a thread."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_threads = True)
    async def thread_rename(self, ctx: Context, thread: typing.Optional[discord.Thread], *, name: str = None):
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            if isinstance(ctx.channel, discord.TextChannel):
                return await ctx.deny(f"This channel is not a **thread**.")
        await thread.edit(name=name, reason=f"{ctx.author} renamed the thread.")
        await ctx.approve(f'Renamed the **thread** to **`{name}`**')
    
    @thread.command(
        name = "delete",
        aliases = ["remove"],
        description = "Deletes a thread."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_threads = True)
    async def thread_delete(self, ctx: Context, *, thread: typing.Optional[discord.Thread] = None):
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            if isinstance(ctx.channel, discord.TextChannel):
                return await ctx.deny(f"This channel is not a **thread**.")
        await thread.delete()

    @thread.command(
        name = "lock",
        aliases = ["close"],
        description = "Lock a thread."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_threads = True)
    async def thread_lock(self, ctx: Context, *, thread: typing.Optional[discord.Thread] = None):
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            if isinstance(ctx.channel, discord.TextChannel):
                return await ctx.deny(f"This channel is not a **thread**.")
        await thread.edit(locked=True, reason=f"Locked by {ctx.author}")
        await ctx.approve(f"The **thread** has been **locked**.")

    @thread.command(
        name = "unlock",
        aliases = ["open"],
        description = "Unlocks a thread."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_threads = True)
    async def thread_unlock(self, ctx: Context, *, thread: typing.Optional[discord.Thread] = None):
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            if isinstance(ctx.channel, discord.TextChannel):
                return await ctx.deny(f"This channel is not a **thread**.")
        await thread.edit(locked=False, reason=f"Unlocked by {ctx.author}")
        await ctx.approve(f"The **thread** has been **unlocked**.")

    @command(
        name = "disablecommand",
        aliases = ["disablecmd"],
        description = "Disables a command."
    )
    @has_permissions(administrator = True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def disablecommand(self, ctx: Context, *, command: str):
        cmd = self.bot.get_command(command)
    
        if not cmd:
            return await ctx.warn(f"Command **`{command}`** is not found.")

        if cmd.name in ["ping", "help", "uptime", "disablecommand", "disablecmd", "enablecommand", "enablecmd"]:
            return await ctx.deny(f"You cannot **disable** `{cmd.name}`.")
        
        check = await self.bot.pool.fetchrow("SELECT * FROM disablecommand WHERE command = $1 AND guild_id = $2", cmd.name, ctx.guild.id)
        if check:
            return await ctx.warn(f"This command is already **disabled**.")

        await self.bot.pool.execute("INSERT INTO disablecommand (guild_id, command) VALUES ($1, $2)", ctx.guild.id, cmd.name)
        await ctx.approve(f"**Disabled** the command `{cmd.name}`.")

    @command(
        name = "enablecommand",
        aliases = ["enablecmd"],
        description = "Enable a command."
    )
    @has_permissions(administrator = True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def enablecommand(self, ctx: Context, *, command: str):
        cmd = self.bot.get_command(command)
    
        if not cmd:
            return await ctx.warn(f"Command **`{command}`** is not found.")
        
        check = await self.bot.pool.fetchrow("SELECT * FROM disablecommand WHERE command = $1 AND guild_id = $2::bigint", cmd.name, ctx.guild.id)

        if check:
            await self.bot.pool.execute("DELETE FROM disablecommand WHERE command = $1 AND guild_id = $2::bigint", cmd.name, ctx.guild.id)
            return await ctx.approve(f"**Enabled** the command `{cmd.name}`")
        else:
            return await ctx.warn(f"Command **`{cmd.name}`** is not disabled.")

    @command(
        name = "unban",
        description = "Unbans a user."
    )
    @has_permissions(ban_members = True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unban(self, ctx: Context, *, user: discord.User):
        await ctx.guild.unban(user)
        data = await self.bot.pool.fetchrow("SELECT * FROM invoke WHERE guild_id = $1 AND type = $2", ctx.guild.id, "unban")

        if data and data["message"]:
            message = data["message"]
            processed_message = EmbedBuilder.embed_replacement(user, message)
            content, embed, view = await EmbedBuilder.to_object(processed_message)

            if content or embed:
                await ctx.channel.send(content=content, embed=embed, view=view)
            else:
                await ctx.channel.send(content=processed_message)
        if data is None:
            return await ctx.approve(f'Unbanned {user.mention}')
        await send_modlog(self.bot, "unban", ctx.author, user, reason = "unbanned user.")


class Confirm(discord.ui.View):
    def __init__(self, ctx: Context, channel: discord.TextChannel):
        super().__init__(timeout=60)  # 60 seconds timeout
        self.ctx = ctx
        self.channel = channel
        self.value = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You cannot confirm this action.", ephemeral=True)
            return

        # Clone the channel
        nukedchannel = await self.channel.clone()

        await nukedchannel.edit(
            position=self.channel.position,
            topic=self.channel.topic,
            overwrites=self.channel.overwrites
        )

        # Update database references
        q = [
            "UPDATE voicemaster.configuration SET channel_id = $1 WHERE channel_id = $2",
            "UPDATE welcome SET channel_id = $1 WHERE channel_id = $2",
            "UPDATE boostmessage SET channel_id = $1 WHERE channel_id = $2",
            "UPDATE starboard SET channel_id = $1 WHERE channel_id = $2",
            "UPDATE vanityroles SET channel_id = $1 WHERE channel_id = $2",
            "UPDATE joinping SET channel_id = $1 WHERE channel_id = $2",
            "UPDATE modlogs SET channel_id = $1 WHERE channel_id = $2"
        ]
        for query in q:
            await self.ctx.bot.pool.execute(query, nukedchannel.id, self.channel.id)

        # Delete the original channel
        await self.channel.delete()

        # Send nuked confirmation
        embed = discord.Embed(description="", color=Colors.BASE_COLOR)
        embed.set_image(url = self.ctx.bot.user.avatar.url)
        embed.set_footer(text=f"Nuked by {self.ctx.author}", icon_url=self.ctx.author.avatar.url)
        await nukedchannel.send(embed=embed)

        # Respond to the interaction to confirm action
        await interaction.response.send_message("Channel nuked!", ephemeral=True)

        # Disable the buttons after the action
        self.disable_all_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You cannot cancel this action.", ephemeral=True)
            return

        # Respond to the interaction and delete the confirmation message
        await interaction.response.send_message("Nuke cancelled.", ephemeral=True)
        await interaction.message.delete()

        # Disable the buttons after the action
        self.disable_all_items()



async def setup(bot: Heal):
    await bot.add_cog(Moderation(bot))
