import discord
import os
import sys
import aiohttp

from discord import Message, Embed
from discord.ext import commands
from discord.ext.commands import (
    Cog,
    command,
    hybrid_command,
    hybrid_group,
    is_owner
)
from typing import Union
from discord.ext.tasks import loop
from discord import Member, Guild, Object, User
from asyncio import gather
import traceback

from tools.heal import Heal
from tools.managers.lastfm import FMHandler
from tools.managers.context import Context, Emojis, Colors
from tools.managers.embedBuilder import EmbedBuilder, EmbedScript
from tools.configuration import api

class LastFM(Cog):
    def __init__(self, bot: Heal) -> None:
        self.bot = bot
        self.handler = FMHandler("bc8082588489f949216859abba6e52be")

    async def lastfm_replacement(self, user: str, params: str) -> str: 
        a = await self.handler.get_tracks_recent(user, 1) 
        userinfo = await self.handler.get_user_info(user)
        userpfp = userinfo["user"]["image"][2]["#text"]
        artist = a['recenttracks']['track'][0]['artist']['#text']
        albumplays = await self.handler.get_album_playcount(user, a['recenttracks']['track'][0]) or "N/A"
        artistplays = await self.handler.get_artist_playcount(user, artist) 
        trackplays = await self.handler.get_track_playcount(user, a['recenttracks']['track'][0]) or "N/A"
        album = a["recenttracks"]['track'][0]['album']['#text'].replace(" ", "+") or "N/A"     
        params = params.replace('{track}', a['recenttracks']['track'][0]['name']).replace('{trackurl}', a['recenttracks']['track'][0]['url']).replace('{artist}', a['recenttracks']['track'][0]['artist']['#text']).replace('{artisturl}', f"https://last.fm/music/{artist.replace(' ', '+')}").replace('{trackimage}', str((a['recenttracks']['track'][0])['image'][3]['#text']).replace('{https', "https")).replace('{artistplays}', str(artistplays)).replace('{albumplays}', str(albumplays)).replace('{trackplays}', str(trackplays)).replace('{album}', a['recenttracks']['track'][0]['album']['#text'] or "N/A").replace('{albumurl}', f"https://www.last.fm/music/{artist.replace(' ', '+')}/{album.replace(' ', '+')}" or "https://none.none").replace('{username}', user).replace('{scrobbles}', a['recenttracks']['@attr']['total']).replace('{useravatar}', userpfp)    
        return params


    @hybrid_group(
        name = "lastfm",
        aliases = ["lf", "fm"],
        description = "Interact with LastFM through heal.",
        invoke_without_command = True
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm(self, ctx: Context):
        return await ctx.send_help(ctx.command)
    
    @lastfm.command(
        name = "login",
        aliases = ["link", "set", "connect"],
        description = "Set your LastFM account."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    
    async def lastfm_login(self, ctx: Context, *, lfuser: str = None):
        if lfuser is None:
            return await ctx.send_help(ctx.command)
        
        data = await self.bot.pool.fetchrow("SELECT user_id, lfuser FROM lastfm WHERE lfuser = $1",lfuser)


        if data:
            user_id = data['user_id']
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            return await ctx.deny(f"**{lfuser}** has been registered by {user.mention}")
        
        msg = await ctx.neutral("⚙️ Connecting to LastFM..")
        await self.bot.pool.execute(
            """
            INSERT INTO lastfm (user_id, lfuser)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET lfuser = $2
            """,
            ctx.author.id, lfuser
        )
        embed = Embed(description = f"{Emojis.LASTFM} {ctx.author.mention}: Set your **LastFM** user to **{lfuser}**.", color = Colors.LAST_FM)
        await msg.edit(embed=embed)

    @lastfm.command(
        name = "nowplaying",
        description = "Get your LastFM now playing.",
        aliases = ["np"]
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_nowplaying(self, ctx: Context, *, user: discord.Member= None):
        if user is None:
            user = ctx.author
        await ctx.typing()
        data = await self.bot.pool.fetchrow("SELECT * FROM lastfm WHERE user_id = $1", user.id)
        if not data:
            return await ctx.lastfm(f"**{user.name}** hasn't got their LastFM account linked.")

        lastfm_username = data["lfuser"]

        APIKEY = api.heal
        api_url = "http://localhost:1999/lastfm/recenttracks"

        params = {"username": lastfm_username, "tracks": "1"}
        headers = {"api-key": APIKEY} 

        async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        track = data["tracks"][0]["name"]
                        url = data["tracks"][0]["url"]
                        artist = data["tracks"][0]["artist"]
                        album_art = data["tracks"][0]["image"]
                        album_name = data["tracks"][0]["album"]


                embed = discord.Embed(
                    color=Colors.BASE_COLOR
                )
                embed.add_field(name = "**Track**", value = f"[{track}]({url})", inline  = True)
                embed.add_field(name = "**Artist**", value = f"{artist}", inline = False)
                embed.set_author(name=f"{lastfm_username}")
                if album_art:
                    embed.set_thumbnail(url=album_art)

                embed.set_footer(text=f"Album: {album_name}")
                message = await ctx.send(embed=embed)
                await message.add_reaction("🔥")
                await message.add_reaction("👎")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
      if not message.guild and message.author.bot:
        return

      check = await self.bot.pool.fetchrow("SELECT * FROM lastfm WHERE user_id = $1 AND command = $2", message.author.id, message.content)
      if check:
        ctx = await self.bot.get_context(message)
        return await ctx.invoke(
          self.bot.get_command('fm np')
        )
                

    @command(
        name = "nowplaying",
        aliases = ["np"]
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def nowplaying(self, ctx: Context, *, user: Union[discord.Member, discord.User]= None):
        return await ctx.invoke(self.bot.get_command('lf np'))
    
    @lastfm.command(
        name = "logout",
        aliases = ["remove", "unlink"],
        description = "Unlink your LastFM account from heal."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_logout(self, ctx: Context):
        data = await self.bot.pool.fetchrow("SELECT * FROM lastfm WHERE user_id = $1", ctx.author.id)
        lfuser = data["lfuser"]
        if not lfuser:
            return await ctx.lastfm(f"You do not have a **LastFM** account linked.")
        
        await self.bot.pool.execute("DELETE FROM lastfm WHERE user_id = $1", ctx.author.id)
        return await ctx.lastfm(f"**Unlinked** your LastFM account successfully")
    
    @lastfm.command(
        name = "variables",
        aliases = ["vars"],
        description = "Get a list of LastFM variables to use in you custom embeds."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_variables(self, ctx: Context):
        return await ctx.neutral("{track_name} - Gets the name of the track \n{track_url} - Gets the url of the track\n{album_name} - Gets the name of the album \n{artist_name} - Gets the name of the artist(s) \n{album_art} - Gets the album art.")
    
    @lastfm.group(
        name = "customcommand",
        aliases = ["cc"],
        description = "Configure your custom NowPlaying alias."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_customcommand(self, ctx: Context):
        return await ctx.send_help(ctx.command)
    
    @lastfm_customcommand.command(
        name = "set",
        aliases = ["add"],
        description = "Set your customcommand"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_customcommand_set(self, ctx: Context, *, customcommand: str = None):
        if customcommand is None:
            return await ctx.send_help(ctx.command)
        
        await self.bot.pool.execute("INSERT INTO lastfm (user_id, command) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET command = $2", ctx.author.id , customcommand)
        return await ctx.lastfm(f"Set your **custom command** to **`{customcommand}`**")
    
    @lastfm_customcommand.command(
        name = "remove",
        description = "Remove your LastFM custom command."
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_customcommand_remove(self, ctx: Context):
        data = await self.bot.pool.fetchrow("SELECT * FROM lastfm WHERE user_id = $1", ctx.author.id)
        customcommand = data["command"]

        if not customcommand:
            return await ctx.deny(f"You do not have a **custom command** set.")
        
        await self.bot.pool.execute("UPDATE lastfm SET command = $1 WHERE user_id = $2", None, ctx.author.id)
        return await ctx.lastfm("**Deleted** your LastFM **custom command.**")

    @lastfm.command(
        name = "chart",
        description = "Get your lastfm chart."
    )
    async def lastfm_chart(self, ctx: Context, user: Union[discord.Member, discord.User] = None, size: str = "3x3"):
        APIKEY = api.heal
        api_url = "http://localhost:1999/lastfm/chart"

        if user == None:
            user = ctx.author

        data = await self.bot.pool.fetchrow("SELECT * FROM lastfm WHERE user_id = $1", user.id)
        if not data:
            return await ctx.lastfm(f"**{user.name}** hasn't got their LastFM account linked.")
        lastfmuser = data["lfuser"]

        params = {"username": lastfmuser, "size": size}
        headers = {"api-key": APIKEY} 
        async with ctx.typing():
                    async with aiohttp.ClientSession() as session:
                        async with session.get(api_url, params=params, headers=headers) as response:
                            if response.status == 200:
                                data = await response.json()
                                image = data.get("image_url")
                                embed = discord.Embed(title = f"lastfm chart for {lastfmuser}")
                                embed.set_image(url = image)
                                await ctx.send(embed=embed)


async def setup(bot: Heal):
    await bot.add_cog(LastFM(bot))