import pomice
import random

from typing import Coroutine, Any
from contextlib import suppress
import discord

from discord.ext import commands
from discord import Embed, Message, HTTPException, Member, VoiceState, utils
from discord.ext.commands import Cog, command
from discord import Interaction, ButtonStyle
from discord.ui import View, Button

from tools.managers.context import Context
from tools.heal import Heal
from tools.configuration import Colors


class Player(pomice.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.queue = pomice.Queue()
        self.ctx: Context = None
        self.loop: bool = False
        self.current_track: pomice.Track = None
        self.awaiting = False

    def shuffle(self) -> None:
        return random.shuffle(self.queue)

    async def set_pause(self, pause: bool) -> Coroutine[Any, Any, bool]:
        if pause is True:
            self.awaiting = True
        else:
            if self.awaiting:
                self.awaiting = False

        return await super().set_pause(pause)

    async def do_next(self, track: pomice.Track = None) -> None:
        if not self.loop:
            if not track:
                try:
                    track: pomice.Track = self.queue.get()
                except pomice.QueueEmpty:
                    return await self.kill()

            self.current_track = track

        await self.play(self.current_track)
        await self.context.send(
            embed=Embed(
                color=Colors.BASE_COLOR,
                description=f"<:musicnote:1251992069468065905> {self.context.author.mention}: Now playing [**{track.title}**]({track.uri})",
            )
        )

        if self.awaiting:
            self.awaiting = False

    def set_context(self, ctx: Context):
        self.context = ctx

    async def kill(self) -> Message:
        with suppress((HTTPException), (KeyError)):
            await self.destroy()
            return await self.context.approve(f"Left the voice channel")


class Music(commands.Cog):
    """
    Music commands.
    """

    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🎵"
        self.pomice = pomice.NodePool()

        bot.loop.create_task(self.start_nodes())

    async def start_nodes(self):

        await self.bot.wait_until_ready()

        await self.pomice.create_node(
            bot=self.bot,
            host="127.0.0.1",
            port=2333,
            password="youshallnotpas",
            spotify_client_id="3f6b4c43339342bd83ac665b447da650",
            spotify_client_secret="b1d1c1a22289433186bb0941d02499d2",
            identifier="MAIN",
        )

        #
        print(f"Node is ready!")

    @commands.Cog.listener()
    async def on_pomice_track_end(self, player: Player, track, _):
        await player.do_next()

    @commands.Cog.listener()
    async def on_pomice_track_stuck(self, player: Player, track, _):
        await player.do_next()

    @commands.Cog.listener()
    async def on_pomice_track_exception(self, player: Player, track, _):
        await player.do_next()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        if before.channel:
            if member.guild.me in before.channel.members:
                if len(before.channel.members) == 1:
                    await member.guild.voice_client.disconnect(force=True)

    @commands.hybrid_command(name="stop")
    async def stop(self, ctx: Context):
        """Leaves the voice channel."""
        if ctx.author.voice is None:
            return

        if ctx.voice_client is None:
            return
        else:
            await ctx.voice_client.disconnect()

    @commands.hybrid_command(name="shuffle")
    async def shuffle(self, ctx: Context):
        """Shuffle the queue."""
        player: Player = ctx.voice_client
        player.shuffle()
        await ctx.approve(f"Shuffling the queue")

    @commands.hybrid_command(name="resume", aliases=["res"])
    async def resume(self, ctx: Context):
        """Resume Playback."""

        player: Player = ctx.voice_client
        await player.set_pause(False)
        return await ctx.approve(f"Resumed the song")

    @commands.hybrid_command(name="pause")
    async def pause(self, ctx: Context):
        """Pauses Playback."""
        player: Player = ctx.voice_client
        await player.set_pause(True)
        return await ctx.approve(f"Paused the song")

    @commands.hybrid_command(name="skip")
    async def skip(self, ctx: Context):
        """Skips to the next song in queue."""
        player: Player = ctx.voice_client
        player.loop = False
        player.awaiting = True
        await player.stop()

    @commands.hybrid_command(name="volume")
    async def volume(self, ctx: Context, volume: int):
        """Changes the volume of playback."""
        player: Player = ctx.voice_client
        await player.set_volume(volume=volume)
        await ctx.neutral(f"Volume set to **{volume}**")

    @commands.hybrid_command(name="loop")
    async def loop(self, ctx: Context):
        """Loops Playback."""
        player: Player = ctx.voice_client

        if not player.is_playing:
            return await ctx.warn(f"No track is playing right now")

        if not player.loop:
            player.loop = True
            return await ctx.neutral(
                f"Looping [**{player.current_track.title}**]({player.current_track.uri})"
            )
        else:
            player.loop = False
            return await ctx.neutral(
                f"Removed the loop for [**{player.current_track.title}**]({player.current_track.uri})"
            )

    @commands.hybrid_command(name="play")
    async def play(self, ctx: Context, *, query: str):
        """Plays a song from a query."""
        if not ctx.voice_client:
            player = await ctx.author.voice.channel.connect(cls=Player, self_deaf=True)
        else:
            player: Player = ctx.voice_client

        player.set_context(ctx)
        player.awaiting = True
        try:
            results = await player.get_tracks(query=query, ctx=ctx)
        except Exception as e:
            return await ctx.warn(f"There was an issue fetching that track.")
        if not results:
            await ctx.warn(f"No song found")

        if isinstance(results, pomice.Playlist):
            for track in results.tracks:
                player.queue.put(track)
            track = None
            await ctx.neutral(f"Added **{len(results.tracks)}** songs to the queue")
        else:
            track = results[0]
            if player.is_playing:
                player.queue.put(track)
                await ctx.neutral(
                    f"Added [**{track.title}**]({track.uri}) to the queue"
                )

        if not player.is_playing:
            player.current_track = track
            await player.do_next(track)


async def setup(bot: Heal):
    await bot.add_cog(Music(bot))
