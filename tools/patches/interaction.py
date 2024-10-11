import discord
from discord.interactions import Interaction

from tools.configuration import Colors, Emojis

class PatchedInteraction(Interaction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    async def embed(self, message: str, emoji: str='', delete_after: float=None):
        return await self.response.send_message(embed=discord.Embed(description=f'{emoji} {self.user.mention}: {message}', color=Colors.BASE_COLOR), delete_after=delete_after, ephemeral=True)
    
    async def deny(self, message: str) -> discord.message:
        return await self.response.send_message(embed=discord.Embed(description=f'{Emojis.DENY} {self.user.mention}: {message}', color=Colors.BASE_COLOR), ephemeral=True)
    
    async def warn(self, message: str) -> discord.message:
        return await self.response.send_message(embed=discord.Embed(description=f'{Emojis.WARN} {self.user.mention}: {message}', color=Colors.BASE_COLOR), ephemeral=True)
    
    async def approve(self, message: str, url: str=None) -> discord.Message:
        if url is None: return await self.response.send_message(embed=discord.Embed(description=f'{Emojis.APPROVE} {self.user.mention}: {message}', color=Colors.BASE_COLOR), ephemeral=True)
        return await self.response.send_message(embed=discord.Embed(description=f'{Emojis.APPROVE} {self.user.mention}: {message}', color=Colors.BASE_COLOR).set_image(url=url), ephemeral=True)
    
    
Interaction.warn = PatchedInteraction.warn
Interaction.embed = PatchedInteraction.embed
Interaction.deny = PatchedInteraction.deny
Interaction.approve = PatchedInteraction.approve