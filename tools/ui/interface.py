import discord

from functools import wraps
from typing import Callable
from discord.ui import (
    View,
    Modal,
    TextInput,
    Button,
    button
)

from tools.configuration import Emojis
from tools.heal import Heal
from tools.patches.interaction import PatchedInteraction

def voicemaster_check(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        bot: Heal = args[0].bot
        interaction: PatchedInteraction = args[1]
        
        if bot is None or interaction is None:
            return

        if interaction.user.voice is None:
            return await interaction.warn("You're not in a **voice channel**!")

        if not (voice := await bot.pool.fetchval(
                """
                SELECT owner_id
                FROM voicemaster.channels 
                WHERE channel_id = $1
                """,
                interaction.user.voice.channel.id,
            )
        ):
            return await interaction.warn("This is not a **VoiceMaster** channel.")

        if voice != interaction.user.id:
            return await interaction.warn("You're not the **owner** of this channel.")

        return await func(*args, **kwargs)
    return wrapper

class Interface(View):
    def __init__(self, bot: Heal) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @voicemaster_check
    @button(emoji=Emojis.VOICEMASTER_LOCK, custom_id="VOICEMASTER:LOCK")
    async def lock(self, interaction: PatchedInteraction, button: Button):
        await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, connect = False)
        await interaction.user.voice.channel.set_permissions(interaction.user, connect = True, speak = True)
        return await interaction.approve("Your **channel** has been **locked**")

    @voicemaster_check
    @button(emoji=Emojis.VOICEMASTER_UNLOCK, custom_id="VOICEMASTER:UNLOCK")
    async def unlock(self, interaction: PatchedInteraction, button: Button):
        await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, connect = True)
        return await interaction.approve("Your **channel** has been **unlocked**")

    @voicemaster_check
    @button(emoji=Emojis.VOICEMASTER_GHOST, custom_id="VOICEMASTER:GHOST")
    async def ghost(self, interaction: PatchedInteraction, button: Button):
        await interaction.user.voice.channel.set_permissions(interaction.user, connect = True, speak = True, view_channel = True)
        await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, connect = False, speak = True, view_channel = False)
        return await interaction.approve("Your **channel** is now **hidden**")

    @voicemaster_check
    @button(emoji=Emojis.VOICEMASTER_REVEAL, custom_id="VOICEMASTER:REVEAL")
    async def reveal(self, interaction: PatchedInteraction, button: Button):
        await interaction.user.voice.channel.set_permissions(interaction.user, connect=True, view_channel=True)
        await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, view_channel=True)
        return await interaction.approve("Your **channel** has been **revealed**")

    @button(emoji=Emojis.VOICEMASTER_PERSON, custom_id="VOICEMASTER:CLAIM")
    async def claim(self, interaction: PatchedInteraction, button: Button):
        if not (owner := await self.bot.pool.fetchval(
                """
                SELECT owner_id
                FROM voicemaster.channels
                WHERE channel_id = $1
                """,
                interaction.user.voice.channel.id,
            )
        ):
            return await interaction.approve("This channel isn't a **VoiceMaster** channel.")
        
        if owner in [member.id for member in interaction.user.voice.channel.members]:
            return await interaction.approve("The **channel** owner is already in the **channel**.")
        
        await self.bot.pool.execute(
            """
            UPDATE voicemaster.channels
            SET owner_id = $1
            WHERE channel_id = $2
            """,
            interaction.user.id,
            interaction.user.voice.channel.id,
        )
        return await interaction.approve("You're now the **voice channel** owner.")

    @voicemaster_check
    @button(emoji=Emojis.VOICEMASTER_ADD, custom_id="VOICEMASTER:PERMIT")
    async def permit(self, interaction: PatchedInteraction, button: Button):
        return await interaction.response.send_modal(Permit())

    @voicemaster_check
    @button(emoji=Emojis.VOICEMASTER_MINUS, custom_id="VOICEMASTER:REJECT")
    async def reject(self, interaction: PatchedInteraction, button: Button):
        if len(interaction.user.voice.channel.members) == 1:
            return await interaction.warn("You cannot **disconnect** yourself from the voice channel...")
        
        options = [discord.SelectOption(label=member.name, value=str(member.id)) for member in interaction.user.voice.channel.members if member.id != interaction.user.id]
        selection = discord.ui.Select(placeholder='Voice Members', options=options, custom_id='VM:DISCONNECT:MEMBER')
        
        async def callback(interaction: discord.Interaction):
            member = interaction.guild.get_member(int(interaction.data['values'][0]))
            if member is None: 
                return await interaction.warn("I could not find the **requested member**...")
            await member.move_to(None)
            return await interaction.approve(f"You have **disconnected** {member.mention} from the voice channel")   
        
        selection.callback = callback
        option = discord.ui.View()
        option.add_item(selection)
        return await interaction.response.send_message("Select a member to disconnect", view=option, ephemeral=True)

    @voicemaster_check
    @button(emoji=Emojis.VOICEMASTER_RENAME, custom_id="VOICEMASTER:RENAME")
    async def rename(self, interaction: PatchedInteraction, button: Button):
        return await interaction.response.send_modal(Rename())

    @voicemaster_check
    @button(emoji=Emojis.VOICEMASTER_OWNERSHIP, custom_id="VOICEMASTER:TRANSFER")
    async def transfer(self, interaction: PatchedInteraction, button: Button):
        if len(interaction.user.voice.channel.members) == 1: 
            return await interaction.warn("You cannot **transfer** the voice channel with **only yourself** in it...")
        
        options = [discord.SelectOption(label=member.name, value=str(member.id)) for member in interaction.user.voice.channel.members if member.id != interaction.user.id]
        selection = discord.ui.Select(placeholder='Voice Members', options=options, custom_id='VM:TRANSFER:MEMBER')
        
        async def callback(interaction: PatchedInteraction):
            member = interaction.guild.get_member(int(interaction.data['values'][0]))
            if member is None: return await interaction.warn("I could not find the **requested member**...")
            await self.bot.pool.execute(
                """
                UPDATE voicemaster.channels
                SET owner_id = $1
                WHERE channel_id = $2 AND guild_id = $3
                """,
                member.id,
                interaction.user.voice.channel.id,
                interaction.guild.id
            )
            return await interaction.approve(f"You have **transferred** the voice channel to {member.mention}")
        
        selection.callback = callback
        option = discord.ui.View()
        option.add_item(selection)
        return await interaction.response.send_message("Select a member to transfer the voice channel to", view=option, ephemeral=True)

    @voicemaster_check
    @button(emoji=Emojis.VOICEMASTER_DELETE, custom_id="VOICEMASTER:DELETE")
    async def delete(self, interaction: PatchedInteraction, button: Button):
        await self.bot.pool.execute(
            """
            DELETE FROM voicemaster.channels
            WHERE guild_id = $1
            """,
            interaction.guild.id
        )
        await interaction.user.voice.channel.delete()
        return await interaction.approve("Your **channel** has been **deleted**")

class Rename(Modal, title = 'Rename Channel'):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label='Channel Name', placeholder='e.g. God.exe', custom_id='VM:RENAME:NAME'))
        
    async def on_submit(self, interaction: PatchedInteraction) -> None:
        await interaction.user.voice.channel.edit(name=self.children[0].value)
        return await interaction.approve(f"The **channel** has been **renamed** to `{self.children[0].value}`")

class Permit(Modal, title='Permit Member'):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label='Discord Username or Discord ID', placeholder='e.g. parelite', custom_id='VM:PERMIT:MEMBER'))
        
    async def on_submit(self, interaction: PatchedInteraction) -> None: 
        member = discord.utils.get(interaction.guild.members, name=self.children[0].value) or interaction.guild.get_member(int(self.children[0].value))
        if member is None: 
           return await interaction.warn("I couldn't find the **requested member** in the **guild**.")
        
        return await interaction.approve(f"**{member}** has been **permitted** to the **channel**.")