import discord

from typing import List

from discord import Message, Embed
from discord.ext.commands import Context, Group

from tools.configuration import Colors, Emojis
from tools.paginator import Paginator

class Context(Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def approve(self, message: str, **kwargs) -> Message:
        return await self.send(
            embed=Embed(
                color = Colors.APPROVE,
                description = f'{Emojis.APPROVE} {self.author.mention}: {message}'
            ),
            **kwargs
        )
    
    async def warn(self, message: str, **kwargs) -> Message:
        return await self.send(
            embed=Embed(
                color = Colors.WARN,
                description = f'{Emojis.WARN} {self.author.mention}: {message}'
            ),
            **kwargs
        )
    
    async def deny(self, message: str, **kwargs) -> Message:
        return await self.send(
            embed=Embed(
                color = Colors.DENY,
                description = f'{Emojis.DENY} {self.author.mention}: {message}'
            ),
            **kwargs
        )
    
    async def lastfm(self, message: str, **kwargs) -> Message:
        return await self.send(
            embed=Embed(
                color = Colors.LAST_FM,
                description = f'{Emojis.LASTFM} {self.author.mention}: {message}'
            ),
            **kwargs
        )
    
    async def paginate(self, embeds: List[discord.Embed], **kwargs) -> Message:
        return await self.send(
            embed = embeds[0],
            view  = Paginator(self, embeds),
            **kwargs
        )

    async def neutral(self, message: str, **kwargs) -> Message:
        return await self.send(
            embed=Embed(
                color = Colors.BASE_COLOR,
                description = f'{message}'
            ),
            **kwargs
        )