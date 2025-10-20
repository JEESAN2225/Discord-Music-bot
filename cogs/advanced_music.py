"""
Advanced Music Cog - Complete feature-rich music bot
Includes Spotify integration, lyrics, advanced queue, playlists, and more
"""

import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from typing import Optional, List, Dict, Any, Union
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

logger = logging.getLogger(__name__)

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

class AdvancedMusicControlView(discord.ui.View):
    """Enhanced music control panel with all features"""
    
    def __init__(self, *, timeout=None):
        super().__init__(timeout=timeout)
        self.queue_manager = get_queue_manager()
        self.spotify = get_spotify_manager()
        self.lyrics = get_lyrics_manager()
    
    @discord.ui.button(emoji=PREVIOUS, style=discord.ButtonStyle.secondary, row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        queue = self.queue_manager.get_queue(interaction.guild_id)
        history = queue.get_history(1)
        
        if not history:
            return await interaction.response.send_message("❌ No previous track available!", ephemeral=True)
        
        # Add current track back to queue at front
        if player.current:
            queue.add_next(player.current, interaction.user)
        
        # Play previous track
        prev_track = history[-1].track
        await player.play(prev_track)
        await interaction.response.send_message(f"{PREVIOUS} Playing previous track: **{prev_track.title}**", ephemeral=True)
    
    @discord.ui.button(emoji=PLAY_PAUSE, style=discord.ButtonStyle.primary, row=0)
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not playing anything!", ephemeral=True)
        
        if player.playing:
            await player.pause()
            button.emoji = PLAY
            button.style = discord.ButtonStyle.success
            await interaction.response.send_message(f"{PAUSE} Paused", ephemeral=True)
        else:
            await player.resume()
            button.emoji = PLAY_PAUSE
            button.style = discord.ButtonStyle.primary
            await interaction.response.send_message(f"{PLAY} Resumed", ephemeral=True)
    
    @discord.ui.button(emoji=SKIP, style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player or not player.playing:
            return await interaction.response.send_message("❌ Nothing to skip!", ephemeral=True)
        
        track_title = player.current.title if player.current else "Unknown"
        await player.stop()
        await interaction.response.send_message(f"{SKIP} Skipped: **{track_title}**", ephemeral=True)
    
    @discord.ui.button(emoji=LOOP, style=discord.ButtonStyle.secondary, row=0)
    async def toggle_repeat(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue = self.queue_manager.get_queue(interaction.guild_id)
        new_mode = queue.toggle_repeat()
        
        mode_emojis = {"off": "❌", "track": "🔂", "queue": "🔁"}
        button.emoji = mode_emojis.get(new_mode, LOOP)
        button.style = discord.ButtonStyle.success if new_mode != "off" else discord.ButtonStyle.secondary
        
        await interaction.response.send_message(f"{button.emoji} Repeat mode: **{new_mode.title()}**", ephemeral=True)
    
    @discord.ui.button(emoji=STOP, style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not playing anything!", ephemeral=True)
        
        queue = self.queue_manager.get_queue(interaction.guild_id)
        queue.clear()
        await player.disconnect()
        await interaction.response.send_message(f"{STOP} Stopped and disconnected", ephemeral=True)
    
    # Row 1 - Advanced Controls
    @discord.ui.button(emoji=SHUFFLE, style=discord.ButtonStyle.secondary, row=1)
    async def toggle_shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue = self.queue_manager.get_queue(interaction.guild_id)
        is_shuffled = queue.toggle_shuffle()
        
        button.style = discord.ButtonStyle.success if is_shuffled else discord.ButtonStyle.secondary
        status = "enabled" if is_shuffled else "disabled"
        await interaction.response.send_message(f"{SHUFFLE} Shuffle {status}", ephemeral=True)
    
    @discord.ui.button(emoji="🎵", label="Lyrics", style=discord.ButtonStyle.secondary, row=1)
    async def show_lyrics(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.followup.send("❌ No track is currently playing!", ephemeral=True)
        
        track = player.current
        lyrics_data = await self.lyrics.search_song_lyrics(track.title, getattr(track, 'author', None))
        
        if not lyrics_data:
            return await interaction.followup.send(f"❌ No lyrics found for **{track.title}**", ephemeral=True)
        
        embeds = self.lyrics.create_lyrics_embed(lyrics_data)
        view = LyricsView(embeds)
        await interaction.followup.send(embed=embeds[0], view=view, ephemeral=True)
    
    @discord.ui.button(emoji="📊", label="Queue", style=discord.ButtonStyle.secondary, row=1)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        music_cog = interaction.client.get_cog('AdvancedMusic')
        if music_cog:
            embed = await music_cog.create_queue_embed(interaction.guild_id, interaction.guild.voice_client)
            view = QueueControlView(interaction.guild_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(emoji="🎛️", label="Effects", style=discord.ButtonStyle.secondary, row=1)
    async def audio_effects(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdvancedFilterView()
        await interaction.response.send_message("🎛️ **Audio Effects Panel**", view=view, ephemeral=True)
    
    @discord.ui.button(emoji="📻", label="Radio", style=discord.ButtonStyle.secondary, row=1)
    async def radio_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue = self.queue_manager.get_queue(interaction.guild_id)
        queue.autoplay_enabled = not queue.autoplay_enabled
        
        button.style = discord.ButtonStyle.success if queue.autoplay_enabled else discord.ButtonStyle.secondary
        status = "enabled" if queue.autoplay_enabled else "disabled"
        await interaction.response.send_message(f"📻 Radio mode {status}", ephemeral=True)

class QueueControlView(discord.ui.View):
    """Queue management controls"""
    
    def __init__(self, guild_id: int, *, timeout=180):
        super().__init__(timeout=timeout)
        self.guild_id = guild_id
        self.queue_manager = get_queue_manager()
    
    @discord.ui.button(emoji=SHUFFLE, label="Shuffle", style=discord.ButtonStyle.secondary)
    async def shuffle_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue = self.queue_manager.get_queue(self.guild_id)
        if not queue:
            return await interaction.response.send_message("❌ Queue is empty!", ephemeral=True)
        
        queue.shuffle()
        await interaction.response.send_message(f"{SHUFFLE} Queue shuffled!", ephemeral=True)
    
    @discord.ui.button(emoji=CLEAR, label="Clear", style=discord.ButtonStyle.danger)
    async def clear_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue = self.queue_manager.get_queue(self.guild_id)
        if not queue:
            return await interaction.response.send_message("❌ Queue is already empty!", ephemeral=True)
        
        count = len(queue)
        queue.clear()
        await interaction.response.send_message(f"{CLEAR} Cleared {count} tracks from queue!", ephemeral=True)
    
    @discord.ui.button(emoji="💾", label="Save as Playlist", style=discord.ButtonStyle.success)
    async def save_as_playlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SavePlaylistModal(self.guild_id)
        await interaction.response.send_modal(modal)

class AdvancedFilterView(discord.ui.View):
    """Advanced audio effects and filters"""
    
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(emoji=NIGHTCORE, label="Nightcore", style=discord.ButtonStyle.secondary, row=0)
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
        await interaction.response.send_message(f"{NIGHTCORE} Nightcore {status}", ephemeral=True)
    
    @discord.ui.button(emoji=BASS_BOOST, label="Bass Boost", style=discord.ButtonStyle.secondary, row=0)
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
    
    @discord.ui.button(emoji=EIGHT_D, label="8D Audio", style=discord.ButtonStyle.secondary, row=0)
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
    
    @discord.ui.button(emoji="🎤", label="Karaoke", style=discord.ButtonStyle.secondary, row=1)
    async def karaoke(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        filters = player.filters
        if not hasattr(player, 'karaoke'):
            player.karaoke = False
        
        player.karaoke = not player.karaoke
        if player.karaoke:
            filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220, filter_width=100)
            button.style = discord.ButtonStyle.success
        else:
            filters.karaoke.reset()
            button.style = discord.ButtonStyle.secondary
        
        await player.set_filters(filters)
        status = "enabled" if player.karaoke else "disabled"
        await interaction.response.send_message(f"🎤 Karaoke mode {status}", ephemeral=True)
    
    @discord.ui.button(emoji="🌊", label="Vaporwave", style=discord.ButtonStyle.secondary, row=1)
    async def vaporwave(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        filters = player.filters
        if not hasattr(player, 'vaporwave'):
            player.vaporwave = False
        
        player.vaporwave = not player.vaporwave
        if player.vaporwave:
            filters.timescale.set(speed=0.8, pitch=0.9, rate=1)
            filters.equalizer.set(bands=[(0, -0.3), (1, -0.2), (2, 0.1), (3, 0.2), (4, 0.1)])
            button.style = discord.ButtonStyle.success
        else:
            filters.timescale.reset()
            filters.equalizer.reset()
            button.style = discord.ButtonStyle.secondary
        
        await player.set_filters(filters)
        status = "enabled" if player.vaporwave else "disabled"
        await interaction.response.send_message(f"🌊 Vaporwave {status}", ephemeral=True)

class SavePlaylistModal(discord.ui.Modal):
    """Modal for saving queue as playlist"""
    
    def __init__(self, guild_id: int):
        super().__init__(title="Save Queue as Playlist")
        self.guild_id = guild_id
        self.queue_manager = get_queue_manager()
    
    name = discord.ui.TextInput(
        label="Playlist Name",
        placeholder="Enter playlist name...",
        required=True,
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label="Description (Optional)",
        placeholder="Enter playlist description...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        queue = self.queue_manager.get_queue(self.guild_id)
        if not queue:
            return await interaction.followup.send("❌ Queue is empty!", ephemeral=True)
        
        if not db:
            return await interaction.followup.send("❌ Database not available!", ephemeral=True)
        
        try:
            # Create playlist in database
            playlist_id = await db.create_playlist(
                name=str(self.name.value),
                user_id=interaction.user.id,
                guild_id=self.guild_id,
                description=str(self.description.value) if self.description.value else None,
                is_public=False
            )
            
            # Add tracks to playlist
            tracks_added = 0
            for track_info in queue._queue:
                await db.add_track_to_playlist(
                    playlist_id=playlist_id,
                    track_title=track_info.track.title,
                    track_artist=getattr(track_info.track, 'author', ''),
                    track_uri=track_info.track.uri,
                    track_duration=getattr(track_info.track, 'length', 0),
                    added_by=interaction.user.id
                )
                tracks_added += 1
            
            embed = discord.Embed(
                title="✅ Playlist Saved",
                description=f"**{self.name.value}** has been saved with {tracks_added} tracks!",
                color=discord.Color.green()
            )
            
            if self.description.value:
                embed.add_field(name="Description", value=self.description.value, inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Failed to save playlist: {e}")
            await interaction.followup.send("❌ Failed to save playlist!", ephemeral=True)

class SearchView(discord.ui.View):
    """Search results view with multiple options"""
    
    def __init__(self, results: List[wavelink.Playable], interaction_user: discord.Member, *, timeout=60):
        self.results = results[:10]  # Limit to 10 results
        self.interaction_user = interaction_user
        self.queue_manager = get_queue_manager()
        
        super().__init__(timeout=timeout)
        
        # Create options for the select menu
        options = [
            discord.SelectOption(
                label=f"{i+1}. {track.title[:80]}"[:100],
                description=f"by {getattr(track, 'author', 'Unknown')[:50]}"[:100],
                value=str(i)
            ) for i, track in enumerate(self.results)
        ]
        
        # Add the select menu with options
        self.add_item(TrackSelectMenu(options, self.results, self.interaction_user))

class TrackSelectMenu(discord.ui.Select):
    def __init__(self, options, results, interaction_user):
        super().__init__(placeholder="Choose a track to play...", min_values=1, max_values=1, options=options)
        self.results = results
        self.interaction_user = interaction_user
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.interaction_user:
            return await interaction.response.send_message("❌ Only the command user can select tracks!", ephemeral=True)
        
        selected_index = int(self.values[0])
        selected_track = self.results[selected_index]
        
        # Play the selected track
        music_cog = interaction.client.get_cog('AdvancedMusic')
        if music_cog:
            await music_cog.play_track(interaction, selected_track, from_search=True)

class AdvancedMusic(commands.Cog):
    """Advanced Music Cog with full feature set"""
    
    def __init__(self, bot):
        self.bot = bot
        self.queue_manager = get_queue_manager()
        self.spotify = get_spotify_manager()
        self.lyrics = get_lyrics_manager()
        self.start_times = {}
    
    async def cog_load(self):
        """Load queues when cog loads"""
        await self.queue_manager.load_all_queues(self.bot)
        self.queue_manager.start_persistence_task()
        logger.info("Advanced Music Cog loaded successfully")
    
    async def cog_unload(self):
        """Save queues when cog unloads"""
        await self.queue_manager.save_all_queues()
        self.queue_manager.stop_persistence_task()
        logger.info("Advanced Music Cog unloaded, queues saved")
    
    def create_embed(self, title: str, description: str = None) -> discord.Embed:
        """Create a standardized embed"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=get_random_color()
        )
        current_time = datetime.datetime.now().strftime("%H:%M")
        embed.set_footer(
            text=f"Powered by {self.bot.user.name} • {current_time}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        return embed
    
    def get_youtube_thumbnail(self, track: wavelink.Playable) -> str:
        """Get high quality YouTube thumbnail"""
        if "youtube" in str(track.uri):
            if "youtube.com" in str(track.uri):
                video_id = str(track.uri).split("v=")[-1].split("&")[0]
            elif "youtu.be" in str(track.uri):
                video_id = str(track.uri).split("/")[-1].split("?")[0]
            else:
                return None
            return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        return None
    
    async def create_now_playing_embed(self, track: wavelink.Playable, requester: discord.Member = None) -> discord.Embed:
        """Create now playing embed with enhanced information"""
        embed = self.create_embed(f"{NOW_PLAYING} Now Playing")
        
        embed.description = f"[{track.title}]({track.uri})"
        
        duration = str(datetime.timedelta(seconds=int(track.length / 1000)))
        
        if hasattr(track, 'author') and track.author:
            embed.add_field(name="Artist", value=track.author, inline=True)
        embed.add_field(name="Duration", value=duration, inline=True)
        
        source = "YouTube" if "youtube" in str(track.uri) else "SoundCloud" if "soundcloud" in str(track.uri) else "Unknown"
        embed.add_field(name="Source", value=source, inline=True)
        
        if requester:
            embed.add_field(name="Requested by", value=requester.mention, inline=True)
        
        # Add Spotify data if available
        if hasattr(track, 'spotify_data'):
            spotify_data = track.spotify_data
            embed.add_field(name="Album", value=spotify_data.get('album', 'Unknown'), inline=True)
            embed.add_field(name="Popularity", value=f"{spotify_data.get('popularity', 0)}/100", inline=True)
        
        thumbnail_url = self.get_youtube_thumbnail(track)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
            if "youtube" in str(track.uri):
                embed.set_image(url=thumbnail_url)
        
        return embed
    
    async def create_queue_embed(self, guild_id: int, player: wavelink.Player = None) -> discord.Embed:
        """Create enhanced queue embed"""
        queue = self.queue_manager.get_queue(guild_id)
        embed = self.create_embed(f"{QUEUE} Music Queue")
        
        if player and player.current:
            current_duration = str(datetime.timedelta(seconds=int(player.current.length / 1000)))
            embed.add_field(
                name="Now Playing",
                value=f"[{player.current.title}]({player.current.uri})\\n`Duration: {current_duration}`",
                inline=False
            )
            
            thumbnail_url = self.get_youtube_thumbnail(player.current)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
        
        if queue:
            queue_stats = queue.get_queue_stats()
            total_duration = str(datetime.timedelta(seconds=int(queue_stats['total_duration'] / 1000)))
            
            queue_list = []
            for i, track_info in enumerate(queue._queue[:10], 1):
                duration = str(datetime.timedelta(seconds=int(getattr(track_info.track, 'length', 0) / 1000)))
                requester = track_info.requester.display_name if track_info.requester else "Unknown"
                queue_list.append(
                    f"`{i}.` [{track_info.track.title}]({track_info.track.uri})\\n"
                    f"┗ `{duration}` • Requested by {requester}"
                )
            
            queue_text = "\\n".join(queue_list)
            remaining = len(queue) - 10 if len(queue) > 10 else 0
            
            if remaining > 0:
                queue_text += f"\\n\\n*And {remaining} more tracks...*"
            
            embed.add_field(
                name=f"Up Next • {len(queue)} tracks • Total: {total_duration}",
                value=queue_text or "No tracks in queue",
                inline=False
            )
        
        # Queue status
        status = []
        if queue.repeat_mode != "off":
            status.append(f"{LOOP} Repeat: {queue.repeat_mode}")
        if queue.shuffle_enabled:
            status.append(f"{SHUFFLE} Shuffle enabled")
        if queue.autoplay_enabled:
            status.append("📻 Radio mode enabled")
        if player and player.paused:
            status.append(f"{PAUSE} Paused")
        
        if status:
            embed.add_field(name="Status", value=" | ".join(status), inline=False)
        
        return embed
    
    async def ensure_voice_client(self, interaction: discord.Interaction) -> Optional[wavelink.Player]:
        """Enhanced voice client management"""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers!", ephemeral=True)
            return None
        
        if not getattr(interaction.user, 'voice', None):
            await interaction.response.send_message("You need to be in a voice channel!", ephemeral=True)
            return None
        
        player = interaction.guild.voice_client
        if not player:
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
                # Initialize advanced queue for this guild
                queue = self.queue_manager.get_queue(interaction.guild.id)
                logger.info(f"Connected to voice channel in guild {interaction.guild.id}")
            except Exception as e:
                await interaction.response.send_message(f"Failed to join voice channel: {str(e)}", ephemeral=True)
                return None
        
        return player
    
    async def play_track(self, interaction: discord.Interaction, track: wavelink.Playable, 
                        from_search: bool = False):
        """Enhanced track playing with queue management"""
        player = await self.ensure_voice_client(interaction)
        if not player:
            return
        
        queue = self.queue_manager.get_queue(interaction.guild.id)
        
        if player.playing:
            # Add to queue
            success = queue.add(track, interaction.user)
            if not success:
                return await interaction.followup.send("❌ Queue is full!", ephemeral=True)
            
            embed = discord.Embed(
                title=f"{QUEUE_ADD} Added to Queue",
                description=f"[{track.title}]({track.uri})",
                color=get_random_color()
            )
            embed.add_field(name="Duration", value=format_time(int(track.length / 1000)))
            embed.add_field(name="Position", value=f"#{len(queue)}")
            
            if from_search:
                await interaction.edit_original_response(embed=embed, view=None)
            else:
                await interaction.followup.send(embed=embed)
        else:
            # Play immediately
            await player.play(track)
            self.start_times[track.uri] = time.time()
            
            # Update database
            if db:
                try:
                    await db.create_or_update_user(
                        user_id=interaction.user.id,
                        username=interaction.user.name,
                        discriminator=str(interaction.user.discriminator),
                        avatar_url=str(interaction.user.avatar.url) if interaction.user.avatar else None
                    )
                    await db.update_user_stats(interaction.user.id, commands_used=1)
                except Exception as e:
                    logger.error(f"Failed to update user stats: {e}")
            
            embed = await self.create_now_playing_embed(track, interaction.user)
            view = AdvancedMusicControlView()
            
            if from_search:
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await interaction.followup.send(embed=embed, view=view)
    
    # Command implementations
    @app_commands.command(name="play", description="Play a song from various sources")
    @app_commands.describe(query="Song name, URL, or Spotify link")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        # Check if it's a Spotify URL
        if "spotify.com" in query or "spotify:" in query:
            if not self.spotify.is_available():
                return await interaction.followup.send("❌ Spotify integration is not available!", ephemeral=True)
            
            spotify_id, spotify_type = self.spotify.extract_spotify_id(query)
            if not spotify_id:
                return await interaction.followup.send("❌ Invalid Spotify URL!", ephemeral=True)
            
            if spotify_type == "track":
                # Single track
                spotify_data = await self.spotify.get_track_info(spotify_id)
                if not spotify_data:
                    return await interaction.followup.send("❌ Failed to get Spotify track info!", ephemeral=True)
                
                # Search for the track on available sources
                search_results = await wavelink.Playable.search(spotify_data['search_query'])
                if not search_results:
                    return await interaction.followup.send(f"❌ No results found for: {spotify_data['search_query']}", ephemeral=True)
                
                track = search_results[0]
                track.spotify_data = spotify_data  # Attach Spotify metadata
                await self.play_track(interaction, track)
                
            elif spotify_type == "playlist":
                # Playlist import
                await self.import_spotify_playlist(interaction, spotify_id)
                
            elif spotify_type == "album":
                # Album import
                await self.import_spotify_album(interaction, spotify_id)
                
        else:
            # Regular search
            try:
                tracks = await wavelink.Playable.search(query)
                if not tracks:
                    return await interaction.followup.send(f"❌ No results found for: {query}", ephemeral=True)
                
                if len(tracks) == 1:
                    # Single result, play directly
                    await self.play_track(interaction, tracks[0])
                else:
                    # Multiple results, show selection
                    embed = discord.Embed(
                        title="🔍 Search Results",
                        description=f"Found {len(tracks)} results for **{query}**",
                        color=get_random_color()
                    )
                    
                    view = SearchView(tracks, interaction.user)
                    await interaction.followup.send(embed=embed, view=view)
                    
            except Exception as e:
                logger.error(f"Search error: {e}")
                await interaction.followup.send("❌ An error occurred while searching!", ephemeral=True)
    
    async def import_spotify_playlist(self, interaction: discord.Interaction, playlist_id: str):
        """Import a Spotify playlist"""
        playlist_info = await self.spotify.get_playlist_info(playlist_id)
        if not playlist_info:
            return await interaction.followup.send("❌ Failed to get playlist info!", ephemeral=True)
        
        embed = discord.Embed(
            title="📋 Importing Spotify Playlist",
            description=f"**{playlist_info['name']}** by {playlist_info['owner']}\\n"
                       f"Processing {playlist_info['track_count']} tracks...",
            color=0x1DB954
        )
        message = await interaction.followup.send(embed=embed)
        
        # Get playlist tracks
        spotify_tracks = await self.spotify.get_playlist_tracks(playlist_id, limit=50)  # Limit for performance
        
        player = await self.ensure_voice_client(interaction)
        if not player:
            return
        
        queue = self.queue_manager.get_queue(interaction.guild.id)
        added_count = 0
        failed_count = 0
        
        for spotify_track in spotify_tracks:
            try:
                # Search for each track
                search_results = await wavelink.Playable.search(spotify_track['search_query'])
                if search_results:
                    track = search_results[0]
                    track.spotify_data = spotify_track
                    
                    if player.playing:
                        success = queue.add(track, interaction.user)
                        if success:
                            added_count += 1
                        else:
                            break  # Queue is full
                    else:
                        # Play first track immediately
                        await player.play(track)
                        added_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to import track {spotify_track['name']}: {e}")
                failed_count += 1
        
        # Update the embed with results
        embed = discord.Embed(
            title="✅ Playlist Import Complete",
            description=f"**{playlist_info['name']}**\\n"
                       f"✅ Added: {added_count} tracks\\n"
                       f"❌ Failed: {failed_count} tracks",
            color=discord.Color.green()
        )
        
        if playlist_info.get('image_url'):
            embed.set_thumbnail(url=playlist_info['image_url'])
        
        view = AdvancedMusicControlView() if added_count > 0 else None
        await message.edit(embed=embed, view=view)
    
    async def import_spotify_album(self, interaction: discord.Interaction, album_id: str):
        """Import a Spotify album"""
        spotify_tracks = await self.spotify.get_album_tracks(album_id)
        if not spotify_tracks:
            return await interaction.followup.send("❌ Failed to get album tracks!", ephemeral=True)
        
        album_name = spotify_tracks[0]['album'] if spotify_tracks else "Unknown Album"
        
        embed = discord.Embed(
            title="💿 Importing Spotify Album",
            description=f"**{album_name}**\\nProcessing {len(spotify_tracks)} tracks...",
            color=0x1DB954
        )
        message = await interaction.followup.send(embed=embed)
        
        player = await self.ensure_voice_client(interaction)
        if not player:
            return
        
        queue = self.queue_manager.get_queue(interaction.guild.id)
        added_count = 0
        failed_count = 0
        
        for spotify_track in spotify_tracks:
            try:
                search_results = await wavelink.Playable.search(spotify_track['search_query'])
                if search_results:
                    track = search_results[0]
                    track.spotify_data = spotify_track
                    
                    if player.playing:
                        success = queue.add(track, interaction.user)
                        if success:
                            added_count += 1
                        else:
                            break
                    else:
                        await player.play(track)
                        added_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to import album track: {e}")
                failed_count += 1
        
        embed = discord.Embed(
            title="✅ Album Import Complete",
            description=f"**{album_name}**\\n"
                       f"✅ Added: {added_count} tracks\\n"
                       f"❌ Failed: {failed_count} tracks",
            color=discord.Color.green()
        )
        
        view = AdvancedMusicControlView() if added_count > 0 else None
        await message.edit(embed=embed, view=view)
    
    @app_commands.command(name="advanced_queue", description="Show the current queue with advanced controls")
    async def queue_command(self, interaction: discord.Interaction):
        embed = await self.create_queue_embed(interaction.guild_id, interaction.guild.voice_client)
        view = QueueControlView(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="nowplaying", description="Show currently playing track")
    async def nowplaying(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)
        
        embed = await self.create_now_playing_embed(player.current)
        view = AdvancedMusicControlView()
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="lyrics", description="Get lyrics for the current track or search")
    @app_commands.describe(query="Song name to search for (optional)")
    async def lyrics_command(self, interaction: discord.Interaction, query: str = None):
        await interaction.response.defer()
        
        if not self.lyrics.is_available():
            return await interaction.followup.send("❌ Lyrics feature is not available!", ephemeral=True)
        
        if query:
            # Search for specific song
            lyrics_data = await self.lyrics.search_song_lyrics(query)
        else:
            # Get lyrics for current track
            player = interaction.guild.voice_client
            if not player or not player.current:
                return await interaction.followup.send("❌ No track is playing and no search query provided!", ephemeral=True)
            
            track = player.current
            lyrics_data = await self.lyrics.search_song_lyrics(track.title, getattr(track, 'author', None))
        
        if not lyrics_data:
            search_term = query or (player.current.title if player and player.current else "Unknown")
            return await interaction.followup.send(f"❌ No lyrics found for **{search_term}**", ephemeral=True)
        
        embeds = self.lyrics.create_lyrics_embed(lyrics_data)
        view = LyricsView(embeds)
        await interaction.followup.send(embed=embeds[0], view=view)
    
    @app_commands.command(name="skip", description="Skip the current track")
    async def skip(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not player or not player.playing:
            return await interaction.response.send_message("❌ Nothing to skip!", ephemeral=True)
        
        track_title = player.current.title if player.current else "Unknown"
        await player.stop()
        await interaction.response.send_message(f"{SKIP} Skipped: **{track_title}**")
    
    @app_commands.command(name="stop", description="Stop playback and clear queue")
    async def stop(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        queue = self.queue_manager.get_queue(interaction.guild.id)
        queue.clear()
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(f"{STOP} Stopped and disconnected")
    
    @app_commands.command(name="volume", description="Set the playback volume")
    @app_commands.describe(level="Volume level (0-200)")
    async def volume(self, interaction: discord.Interaction, level: int):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        if not 0 <= level <= 200:
            return await interaction.response.send_message("❌ Volume must be between 0 and 200!", ephemeral=True)
        
        await player.set_volume(level / 100)
        await interaction.response.send_message(
            f"{VOLUME_UP} Volume set to: [{create_progress_bar(level, 200)}] {level}%"
        )
    
    # Event handlers
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Enhanced track end handling with autoplay and repeat"""
        player = payload.player
        
        # Check if player has valid guild reference
        if not player or not player.guild:
            logger.warning("Track end event received but player has no guild reference")
            return
            
        queue = self.queue_manager.get_queue(player.guild.id)
        
        # Record listening statistics
        if payload.track and db:
            try:
                listening_time = int(payload.track.length / 1000)
                if payload.track.uri in self.start_times:
                    actual_time = int(time.time() - self.start_times[payload.track.uri])
                    listening_time = min(listening_time, actual_time)
                    del self.start_times[payload.track.uri]
                
                completed = payload.reason == "FINISHED"
                skipped = payload.reason == "STOPPED"
                
                # This would need the user who requested the track
                # For now, we'll skip individual track recording
                pass
            except Exception as e:
                logger.error(f"Failed to record listening stats: {e}")
        
        # Handle repeat modes
        if queue.repeat_mode == "track" and payload.track:
            await player.play(payload.track)
            return
        
        # Get next track from queue
        next_track_info = None
        if queue.repeat_mode == "queue" and not queue and payload.track:
            # Re-add the track to queue for queue repeat
            queue.add(payload.track)
        
        if queue:
            next_track_info = queue.get()
        
        if next_track_info:
            await player.play(next_track_info.track)
            self.start_times[next_track_info.track.uri] = time.time()
        elif queue.autoplay_enabled:
            # Generate autoplay suggestions
            suggestions = await queue.generate_autoplay_suggestions(payload.track, limit=1)
            if suggestions:
                await player.play(suggestions[0])
                self.start_times[suggestions[0].uri] = time.time()
            else:
                # No autoplay available, disconnect after timeout
                await asyncio.sleep(180)  # 3 minutes
                if not player.playing:
                    await player.disconnect()
    
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        """Track start event handling"""
        self.start_times[payload.track.uri] = time.time()
        logger.debug(f"Track started: {payload.track.title}")

async def setup(bot):
    """Setup function for the Advanced Music cog"""
    await bot.add_cog(AdvancedMusic(bot))
