import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from typing import Optional, List, Dict, Any
import datetime
import random
import time
import math
import asyncio
import json
from utils.emoji import *
from utils.advanced_queue import get_queue_manager, AdvancedQueue
from integrations.spotify import get_spotify_manager
from integrations.lyrics import get_lyrics_manager, LyricsView
from database.models import db
from config.config import config
import logging

def format_time(seconds: int) -> str:
    """Format seconds into HH:MM:SS"""
    return str(datetime.timedelta(seconds=seconds))

def create_progress_bar(current: int, total: int, length: int = 15) -> str:
    """Create a text-based progress bar"""
    filled = int((current / total) * length)
    bar = '▰' * filled + '▱' * (length - filled)
    return bar

def get_random_color() -> discord.Color:
    """Get a random pastel color"""
    return discord.Color.from_hsv(random.random(), 0.3, 1)

class VolumeView(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.button(emoji=VOLUME_DOWN, style=discord.ButtonStyle.secondary)
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        current_volume = int(player.volume * 100)
        new_volume = max(0, current_volume - 10)
        await player.set_volume(new_volume / 100)
        await interaction.response.send_message(f"{VOLUME_DOWN} Volume: {new_volume}%", ephemeral=True)

    @discord.ui.button(emoji=VOLUME_UP, style=discord.ButtonStyle.secondary)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        current_volume = int(player.volume * 100)
        new_volume = min(150, current_volume + 10)
        await player.set_volume(new_volume / 100)
        await interaction.response.send_message(f"{VOLUME_UP} Volume: {new_volume}%", ephemeral=True)

    @discord.ui.button(emoji=VOLUME_MUTE, style=discord.ButtonStyle.secondary)
    async def volume_mute(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        if not hasattr(player, 'previous_volume'):
            player.previous_volume = player.volume
            await player.set_volume(0)
            button.style = discord.ButtonStyle.danger
            await interaction.response.send_message(f"{VOLUME_MUTE} Muted", ephemeral=True)
        else:
            await player.set_volume(player.previous_volume)
            delattr(player, 'previous_volume')
            button.style = discord.ButtonStyle.secondary
            await interaction.response.send_message(f"{VOLUME_UP} Unmuted", ephemeral=True)

class QueueControlView(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.button(emoji=SHUFFLE, style=discord.ButtonStyle.secondary)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.advanced_queue import get_queue_manager
        queue_manager = get_queue_manager()
        queue = queue_manager.get_queue(interaction.guild.id)
        
        if queue.is_empty():
            return await interaction.response.send_message("❌ No songs in queue to shuffle!", ephemeral=True)
        
        queue.shuffle()
        await interaction.response.send_message(f"{SHUFFLE} Queue shuffled!", ephemeral=True)

    @discord.ui.button(emoji=CLEAR, style=discord.ButtonStyle.secondary)
    async def clear_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.advanced_queue import get_queue_manager
        queue_manager = get_queue_manager()
        queue = queue_manager.get_queue(interaction.guild.id)
        
        if queue.is_empty():
            return await interaction.response.send_message("Queue is already empty!", ephemeral=True)
        
        queue_length = len(queue)
        queue.clear()
        await interaction.response.send_message(f"{CLEAR} Cleared {queue_length} tracks from queue!", ephemeral=True)

    @discord.ui.button(emoji=LOOP_QUEUE, style=discord.ButtonStyle.secondary)
    async def loop_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.advanced_queue import get_queue_manager
        queue_manager = get_queue_manager()
        queue = queue_manager.get_queue(interaction.guild.id)
        
        repeat_mode = queue.toggle_repeat()
        status = f"{repeat_mode} mode"
        button.style = discord.ButtonStyle.success if repeat_mode != "off" else discord.ButtonStyle.secondary
        await interaction.response.send_message(f"{LOOP_QUEUE} Repeat {status}", ephemeral=True)

class FilterView(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.button(emoji=NIGHTCORE, style=discord.ButtonStyle.secondary)
    async def nightcore(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        filters = player.filters
        if not hasattr(player, 'nightcore'):
            player.nightcore = False
        
        player.nightcore = not player.nightcore
        if player.nightcore:
            filters.timescale.set(speed=1.2, pitch=1.2, rate=1)
            button.style = discord.ButtonStyle.success
        else:
            filters.timescale.reset()
            button.style = discord.ButtonStyle.secondary
        
        await player.set_filters(filters)
        status = "enabled" if player.nightcore else "disabled"
        await interaction.response.send_message(f"{NIGHTCORE} Nightcore filter {status}", ephemeral=True)

    @discord.ui.button(emoji=BASS_BOOST, style=discord.ButtonStyle.secondary)
    async def bass_boost(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        filters = player.filters
        if not hasattr(player, 'bass_boost'):
            player.bass_boost = False
        
        player.bass_boost = not player.bass_boost
        if player.bass_boost:
            filters.equalizer.set(bands=[(0, 0.6), (1, 0.7), (2, 0.8), (3, 0.55)])
            button.style = discord.ButtonStyle.success
        else:
            filters.equalizer.reset()
            button.style = discord.ButtonStyle.secondary
        
        await player.set_filters(filters)
        status = "enabled" if player.bass_boost else "disabled"
        await interaction.response.send_message(f"{BASS_BOOST} Bass boost {status}", ephemeral=True)

    @discord.ui.button(emoji=EIGHT_D, style=discord.ButtonStyle.secondary)
    async def eight_d(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        filters = player.filters
        if not hasattr(player, 'eight_d'):
            player.eight_d = False
        
        player.eight_d = not player.eight_d
        if player.eight_d:
            filters.rotation.set(speed=0.3)
            button.style = discord.ButtonStyle.success
        else:
            filters.rotation.reset()
            button.style = discord.ButtonStyle.secondary
        
        await player.set_filters(filters)
        status = "enabled" if player.eight_d else "disabled"
        await interaction.response.send_message(f"{EIGHT_D} 8D audio {status}", ephemeral=True)

class MusicControlView(discord.ui.View):
    def __init__(self, *, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.button(emoji=PREVIOUS, style=discord.ButtonStyle.secondary, row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player or not hasattr(player, 'previous_track'):
            return await interaction.response.send_message("❌ No previous track available!", ephemeral=True)
        
        await player.play(player.previous_track)
        await interaction.response.send_message(f"{PREVIOUS} Playing previous track", ephemeral=True)

    @discord.ui.button(emoji=PLAY_PAUSE, style=discord.ButtonStyle.secondary, row=0)
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not playing anything!", ephemeral=True)
        
        if player.playing:
            await player.pause()
            button.style = discord.ButtonStyle.success
            await interaction.response.send_message(f"{PAUSE} Paused", ephemeral=True)
        else:
            await player.resume()
            button.style = discord.ButtonStyle.secondary
            await interaction.response.send_message(f"{PLAY} Resumed", ephemeral=True)

    @discord.ui.button(emoji=SKIP, style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player or not player.playing:
            return await interaction.response.send_message("❌ Nothing to skip!", ephemeral=True)
        
        await player.stop()
        await interaction.response.send_message(f"{SKIP} Skipped", ephemeral=True)

    @discord.ui.button(emoji=LOOP, style=discord.ButtonStyle.secondary, row=0)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not hasattr(interaction.guild, "music_loop"):
            interaction.guild.music_loop = False
        
        interaction.guild.music_loop = not interaction.guild.music_loop
        status = "enabled" if interaction.guild.music_loop else "disabled"
        button.style = discord.ButtonStyle.success if interaction.guild.music_loop else discord.ButtonStyle.secondary
        await interaction.response.send_message(f"{LOOP} Loop {status}", ephemeral=True)

    @discord.ui.button(emoji=STOP, style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not playing anything!", ephemeral=True)
        
        await player.disconnect()
        await interaction.response.send_message(f"{STOP} Stopped and cleared queue", ephemeral=True)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue_manager = get_queue_manager()
        self.start_times = {}
        super().__init__()

    def create_embed(self, title: str, description: str = None) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=get_random_color()
        )
        current_time = datetime.datetime.now().strftime("%H:%M")
        embed.set_footer(
            text=f"Powered by {self.bot.user.name} • today {current_time}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        return embed

    def get_youtube_thumbnail(self, track: wavelink.Playable) -> str:
        """Get high quality YouTube thumbnail if available"""
        if "youtube" in track.uri:
            if "youtube.com" in track.uri:
                video_id = track.uri.split("v=")[-1].split("&")[0]
            elif "youtu.be" in track.uri:
                video_id = track.uri.split("/")[-1].split("?")[0]
            else:
                return track.artwork_url if hasattr(track, 'artwork_url') else None
                
            return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        return track.artwork_url if hasattr(track, 'artwork_url') else None

    def create_now_playing_embed(self, track: wavelink.Playable, requester: discord.Member = None) -> discord.Embed:
        embed = self.create_embed(f"{NOW_PLAYING} Now Playing")
        
        embed.description = f"[{track.title}]({track.uri})"
        
        duration = str(datetime.timedelta(seconds=int(track.length / 1000)))
        if track.uri in self.start_times:
            current_time = time.time() - self.start_times[track.uri]
            progress = create_progress_bar(current_time, track.length / 1000)
            timestamp = str(datetime.timedelta(seconds=int(current_time)))
            embed.add_field(
                name="Progress",
                value=f"`{timestamp} {progress} {duration}`",
                inline=False
            )
        
        if hasattr(track, 'author'):
            embed.add_field(name="Artist", value=track.author, inline=True)
        embed.add_field(name="Duration", value=duration, inline=True)
        
        source = "YouTube" if "youtube" in track.uri else "SoundCloud" if "soundcloud" in track.uri else "Unknown"
        embed.add_field(name="Source", value=source, inline=True)
        
        if requester:
            embed.add_field(name="Requested by", value=requester.mention, inline=True)
        
        thumbnail_url = self.get_youtube_thumbnail(track)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
            if "youtube" in track.uri:
                embed.set_image(url=thumbnail_url)
        
        return embed

    def create_queue_embed(self, player: wavelink.Player, guild: discord.Guild) -> discord.Embed:
        embed = self.create_embed(f"{QUEUE} Music Queue")
        queue = self.queue_manager.get_queue(guild.id)
        
        if player.current:
            current_duration = str(datetime.timedelta(seconds=int(player.current.length / 1000)))
            embed.add_field(
                name="Now Playing",
                value=f"[{player.current.title}]({player.current.uri})\n`Duration: {current_duration}`",
                inline=False
            )
            
            thumbnail_url = self.get_youtube_thumbnail(player.current)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
        
        if not queue.is_empty():
            queue_stats = queue.get_queue_stats()
            total_duration = queue_stats['total_duration']
            queue_duration = str(datetime.timedelta(seconds=int(total_duration / 1000)))
            
            queue_list = []
            for i in range(min(10, len(queue))):
                track_info = queue.peek(i)
                if track_info:
                    track = track_info.track
                    duration = str(datetime.timedelta(seconds=int(track.length / 1000)))
                    requester_name = track_info.requester.display_name if track_info.requester else "Unknown"
                    queue_list.append(
                        f"`{i+1}.` [{track.title}]({track.uri})\n┗ `{duration}` • {requester_name}"
                    )
            
            queue_text = "\n".join(queue_list)
            remaining = len(queue) - 10 if len(queue) > 10 else 0
            
            if remaining > 0:
                queue_text += f"\n\n*And {remaining} more tracks...*"
            
            embed.add_field(
                name=f"Up Next • {len(queue)} tracks • Total Duration: {queue_duration}",
                value=queue_text or "No tracks in queue",
                inline=False
            )
        
        status = []
        if queue.repeat_mode != "off":
            repeat_emoji = "🔂" if queue.repeat_mode == "track" else "🔁"
            status.append(f"{repeat_emoji} Repeat: {queue.repeat_mode}")
        if queue.shuffle_enabled:
            status.append(f"{SHUFFLE} Shuffle")
        if player.paused:
            status.append(f"{PAUSE} Paused")
        if int(player.volume * 100) != 100:
            status.append(f"{VOLUME_UP} Volume: {int(player.volume * 100)}%")
        
        if status:
            embed.add_field(name="Player Status", value=" | ".join(status), inline=False)
        
        return embed

    async def ensure_voice_client(self, interaction: discord.Interaction) -> Optional[wavelink.Player]:
        """Ensure we have a valid voice client and user is in a voice channel"""
        if not interaction.guild:
            if not interaction.response.is_done():
                await interaction.response.send_message("This command can only be used in servers!", ephemeral=True)
            return None
            
        if not getattr(interaction.user, 'voice', None):
            if not interaction.response.is_done():
                await interaction.response.send_message("You need to be in a voice channel!", ephemeral=True)
            return None

        player = interaction.guild.voice_client
        if not player:
            try:
                # Check if there are any connected Lavalink nodes
                from utils.lavalink_helper import is_lavalink_available
                if not is_lavalink_available():
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "❌ No Lavalink nodes available. Music features are currently disabled.\n"
                            "Please contact the bot administrator.", 
                            ephemeral=True
                        )
                    return None
                    
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
                # Advanced queue is managed separately by queue_manager
            except Exception as e:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"Failed to join voice channel: {str(e)}", ephemeral=True)
                return None
        
        return player

    @app_commands.command(name="join", description="Join your voice channel")
    async def join(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            return await interaction.response.send_message("I'm already in a voice channel!", ephemeral=True)
            
        player = await self.ensure_voice_client(interaction)
        if player:
            await interaction.response.send_message(f"{JOIN} Joined {interaction.user.voice.channel.mention} 🎵")

    @app_commands.command(name="play", description="Play a song")
    @app_commands.describe(query="The song name or URL to play")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        player = await self.ensure_voice_client(interaction)
        if not player:
            return
            
        queue = self.queue_manager.get_queue(interaction.guild.id)
        
        try:
            tracks = await wavelink.Playable.search(query)
            if not tracks:
                return await interaction.followup.send(f"No results found for: {query}", ephemeral=True)
                
            track = tracks[0]
            
            if player.playing or player.paused:
                success = queue.add(track, interaction.user)
                if not success:
                    return await interaction.followup.send("Queue is full! Please wait for some tracks to finish.", ephemeral=True)
                    
                embed = discord.Embed(
                    title=f"{QUEUE_ADD} Added to Queue",
                    description=f"[{track.title}]({track.uri})",
                    color=get_random_color()
                )
                embed.add_field(name="Duration", value=format_time(int(track.length / 1000)))
                embed.add_field(name="Position in Queue", value=f"#{len(queue)}")
                
                if hasattr(track, 'author') and track.author:
                    embed.add_field(name="Artist", value=track.author, inline=True)
                    
                thumbnail_url = self.get_youtube_thumbnail(track)
                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)
                    
                return await interaction.followup.send(embed=embed)
            
            await player.play(track)
            self.start_times[track.uri] = time.time()
            
            embed = self.create_now_playing_embed(track, interaction.user)
            view = MusicControlView()
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="stop", description="Stop the music and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("I'm not playing anything!", ephemeral=True)
            
        queue = self.queue_manager.get_queue(interaction.guild.id)
        queue.clear()
        
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(f"{STOP} Stopped and cleared queue ⏹")

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client or not interaction.guild.voice_client.playing:
            return await interaction.response.send_message("Nothing to skip!", ephemeral=True)
            
        await interaction.guild.voice_client.stop()
        await interaction.response.send_message(f"{SKIP} Skipped ⏩")

    @app_commands.command(name="queue", description="Show queue controls and current queue")
    async def queue_view(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("No active music player!", ephemeral=True)
            
        embed = self.create_queue_embed(interaction.guild.voice_client, interaction.guild)
        view = QueueControlView()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="filters", description="Show audio filter controls")
    async def filters(self, interaction: discord.Interaction):
        await interaction.response.send_message("Audio Filters:", view=FilterView(), ephemeral=True)

    @app_commands.command(name="volume", description="Adjust or show volume controls")
    @app_commands.describe(level="Volume level (0-150)")
    async def volume(self, interaction: discord.Interaction, level: Optional[int] = None):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("No active music player!", ephemeral=True)
            
        if level is None:
            await interaction.response.send_message("Volume Controls:", view=VolumeView(), ephemeral=True)
        else:
            if not 0 <= level <= 150:
                return await interaction.response.send_message("Volume must be between 0 and 150!", ephemeral=True)
            
            await interaction.guild.voice_client.set_volume(level / 100)
            await interaction.response.send_message(
                f"{VOLUME_UP} Volume set to: [{create_progress_bar(level, 150)}] {level}%"
            )

    @app_commands.command(name="pause", description="Pause the current song")
    async def pause(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client or not interaction.guild.voice_client.playing:
            return await interaction.response.send_message("Nothing is playing!", ephemeral=True)
            
        await interaction.guild.voice_client.pause()
        await interaction.response.send_message(f"{PAUSE} Paused ⏸")

    @app_commands.command(name="resume", description="Resume the paused song")
    async def resume(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client or interaction.guild.voice_client.playing:
            return await interaction.response.send_message("Nothing is paused!", ephemeral=True)
            
        await interaction.guild.voice_client.resume()
        await interaction.response.send_message(f"{PLAY} Resumed ▶")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        """Handle track end event"""
        player = payload.player
        if payload.reason == "FINISHED":
            queue = self.queue_manager.get_queue(player.guild.id)
            
            # Handle repeat modes
            if queue.repeat_mode == "track" and payload.track:
                await player.play(payload.track)
                return
            
            # Get next track from advanced queue
            if not queue.is_empty():
                next_track_info = queue.get()
                if next_track_info:
                    await player.play(next_track_info.track)
                    self.start_times[next_track_info.track.uri] = time.time()
            elif queue.repeat_mode == "queue":
                # TODO: Implement queue repeat logic
                pass

async def setup(bot):
    """Setup function for the Music cog"""
    await bot.add_cog(Music(bot))