"""
Radio and Streaming Features - Radio stations, live streams, and advanced features
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import wavelink
from typing import Optional, Dict, List
import datetime
import asyncio
import aiohttp
from utils.emoji import *
from config.config import config
import logging

logger = logging.getLogger(__name__)

class RadioStreaming(commands.Cog):
    """Radio stations, live streams, and streaming features"""
    
    def __init__(self, bot):
        self.bot = bot
        self.radio_stations = {
            'lofi': {
                'name': 'LoFi Hip Hop Radio',
                'url': 'https://www.youtube.com/watch?v=jfKfPfyJRdk',
                'genre': 'Lo-Fi',
                'emoji': '🎵'
            },
            'chill': {
                'name': 'ChillHop Music',
                'url': 'https://www.youtube.com/watch?v=5yx6BWlEVcY',
                'genre': 'Chill',
                'emoji': '😌'
            },
            'jazz': {
                'name': 'Smooth Jazz Radio',
                'url': 'https://www.youtube.com/watch?v=neV3EPgvZ3g',
                'genre': 'Jazz',
                'emoji': '🎺'
            },
            'classical': {
                'name': 'Classical Music',
                'url': 'https://www.youtube.com/watch?v=jgpJVI3tDbY',
                'genre': 'Classical',
                'emoji': '🎼'
            },
            'electronic': {
                'name': 'Electronic Mix',
                'url': 'https://www.youtube.com/watch?v=4xDzrJKXOOY',
                'genre': 'Electronic',
                'emoji': '⚡'
            },
            'synthwave': {
                'name': 'Synthwave Radio',
                'url': 'https://www.youtube.com/watch?v=4xDzrJKXOOY',
                'genre': 'Synthwave',
                'emoji': '🌆'
            },
            'study': {
                'name': 'Study Music',
                'url': 'https://www.youtube.com/watch?v=jfKfPfyJRdk',
                'genre': 'Study',
                'emoji': '📚'
            },
            'gaming': {
                'name': 'Gaming Music Mix',
                'url': 'https://www.youtube.com/watch?v=jIQ6UV2jmPs',
                'genre': 'Gaming',
                'emoji': '🎮'
            },
            'rock': {
                'name': 'Rock Radio',
                'url': 'https://www.youtube.com/watch?v=ZbZSe6N_BXs',
                'genre': 'Rock',
                'emoji': '🎸'
            },
            'pop': {
                'name': 'Pop Hits Radio',
                'url': 'https://www.youtube.com/watch?v=YQHsXMglC9A',
                'genre': 'Pop',
                'emoji': '🎤'
            }
        }
        
        self.activity_monitor = {}  # guild_id -> {'last_activity': timestamp, 'users': set()}
        self.activity_monitor_task.start()
    
    def create_embed(self, title: str, description: str = None, color: discord.Color = None) -> discord.Embed:
        """Create a standardized embed"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or discord.Color.blurple()
        )
        current_time = datetime.datetime.now().strftime("%H:%M")
        embed.set_footer(
            text=f"Powered by {self.bot.user.name} • {current_time}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        return embed
    
    @app_commands.command(name="radio", description="Play a radio station")
    @app_commands.describe(station="Choose a radio station")
    @app_commands.choices(station=[
        app_commands.Choice(name="🎵 LoFi Hip Hop", value="lofi"),
        app_commands.Choice(name="😌 ChillHop Music", value="chill"),
        app_commands.Choice(name="🎺 Smooth Jazz", value="jazz"),
        app_commands.Choice(name="🎼 Classical Music", value="classical"),
        app_commands.Choice(name="⚡ Electronic Mix", value="electronic"),
        app_commands.Choice(name="🌆 Synthwave Radio", value="synthwave"),
        app_commands.Choice(name="📚 Study Music", value="study"),
        app_commands.Choice(name="🎮 Gaming Mix", value="gaming"),
        app_commands.Choice(name="🎸 Rock Radio", value="rock"),
        app_commands.Choice(name="🎤 Pop Hits", value="pop"),
    ])
    async def radio(self, interaction: discord.Interaction, station: str):
        """Play a radio station"""
        if station not in self.radio_stations:
            return await interaction.response.send_message("❌ Invalid radio station!", ephemeral=True)
        
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ You need to be in a voice channel!", ephemeral=True)
        
        await interaction.response.defer()
        
        station_info = self.radio_stations[station]
        
        # Connect to voice if not connected
        player = interaction.guild.voice_client
        if not player:
            player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        
        try:
            # Search for the radio stream
            tracks = await wavelink.Playable.search(station_info['url'])
            if not tracks:
                return await interaction.followup.send("❌ Failed to load radio station!")
            
            track = tracks[0]
            await player.play(track)
            
            # Enable autoplay for continuous radio
            music_cog = self.bot.get_cog('AdvancedMusic')
            if music_cog:
                queue = music_cog.queue_manager.get_queue(interaction.guild.id)
                queue.autoplay_enabled = True
            
            embed = self.create_embed(
                title="📻 Radio Station Playing",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="🎵 Station",
                value=f"{station_info['emoji']} **{station_info['name']}**",
                inline=True
            )
            
            embed.add_field(
                name="🎧 Genre",
                value=station_info['genre'],
                inline=True
            )
            
            embed.add_field(
                name="📻 Mode",
                value="Continuous streaming with autoplay",
                inline=True
            )
            
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/741714070017097779.png")
            
            view = RadioControlView(station)
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Failed to play radio station: {e}")
            await interaction.followup.send("❌ Failed to start radio station!")
    
    @app_commands.command(name="radio_list", description="Show available radio stations")
    async def radio_list(self, interaction: discord.Interaction):
        """Show available radio stations"""
        embed = self.create_embed(
            title="📻 Available Radio Stations",
            description="Choose from our collection of 24/7 radio streams",
            color=discord.Color.blue()
        )
        
        stations_text = ""
        for key, station in self.radio_stations.items():
            stations_text += f"{station['emoji']} **{station['name']}**\n"
            stations_text += f"   Genre: {station['genre']}\n\n"
        
        embed.description += f"\n\n{stations_text}"
        embed.add_field(
            name="🎵 How to use:",
            value="Use `/radio <station>` to start playing any station\nAutoplay will keep the music going continuously!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="stream", description="Play a live stream URL")
    @app_commands.describe(url="Stream URL (YouTube, Twitch, etc.)")
    async def stream(self, interaction: discord.Interaction, url: str):
        """Play a live stream from URL"""
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ You need to be in a voice channel!", ephemeral=True)
        
        await interaction.response.defer()
        
        # Connect to voice if not connected
        player = interaction.guild.voice_client
        if not player:
            player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        
        try:
            tracks = await wavelink.Playable.search(url)
            if not tracks:
                return await interaction.followup.send("❌ Could not load stream from this URL!")
            
            track = tracks[0]
            await player.play(track)
            
            embed = self.create_embed(
                title="📡 Live Stream Playing",
                description=f"[{track.title}]({track.uri})",
                color=discord.Color.red()
            )
            
            embed.add_field(name="🔴 Status", value="Live Streaming", inline=True)
            embed.add_field(name="🌐 Source", value="External Stream", inline=True)
            embed.add_field(name="👤 Requested by", value=interaction.user.mention, inline=True)
            
            if hasattr(track, 'thumbnail'):
                embed.set_thumbnail(url=track.thumbnail)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to play stream: {e}")
            await interaction.followup.send("❌ Failed to play stream! Make sure the URL is valid.")
    
    @app_commands.command(name="activity_monitor", description="Monitor voice channel activity")
    async def activity_monitor_command(self, interaction: discord.Interaction):
        """Show voice channel activity"""
        player = interaction.guild.voice_client
        if not player or not player.channel:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        channel = player.channel
        embed = self.create_embed(
            title="🔊 Voice Activity Monitor",
            description=f"Monitoring activity in {channel.mention}",
            color=discord.Color.green()
        )
        
        # Get member statuses
        members_info = []
        for member in channel.members:
            if member.bot:
                continue
            
            status_emoji = "🎤"  # Default speaking
            if member.voice.self_mute or member.voice.mute:
                status_emoji = "🔇"  # Muted
            elif member.voice.self_deaf or member.voice.deaf:
                status_emoji = "🔇"  # Deafened
            elif member.voice.afk:
                status_emoji = "💤"  # AFK
            
            members_info.append(f"{status_emoji} {member.display_name}")
        
        embed.add_field(
            name=f"👥 Members in Channel ({len(members_info)})",
            value="\n".join(members_info) if members_info else "No active members",
            inline=False
        )
        
        # Channel info
        embed.add_field(
            name="🔊 Channel Info",
            value=f"**Bitrate:** {channel.bitrate // 1000}kbps\n"
                  f"**User Limit:** {channel.user_limit if channel.user_limit else 'Unlimited'}\n"
                  f"**Region:** {channel.rtc_region or 'Automatic'}",
            inline=True
        )
        
        # Player info
        embed.add_field(
            name="🎵 Player Status",
            value=f"**Playing:** {'Yes' if player.current else 'No'}\n"
                  f"**Volume:** {int(player.volume * 100)}%\n"
                  f"**Paused:** {'Yes' if player.paused else 'No'}",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="favorites", description="Manage your favorite stations and tracks")
    async def favorites(self, interaction: discord.Interaction):
        """Manage user favorites"""
        embed = self.create_embed(
            title="⭐ Your Favorites",
            description="Manage your favorite radio stations and tracks",
            color=discord.Color.gold()
        )
        
        # This would typically load from database
        embed.add_field(
            name="📻 Favorite Stations",
            value="• 🎵 LoFi Hip Hop Radio\n• 😌 ChillHop Music\n• 📚 Study Music",
            inline=False
        )
        
        embed.add_field(
            name="🎵 Favorite Tracks",
            value="• Track 1 - Artist 1\n• Track 2 - Artist 2\n• Track 3 - Artist 3",
            inline=False
        )
        
        view = FavoritesView()
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="mood", description="Play music based on your mood")
    @app_commands.describe(mood="Select your current mood")
    @app_commands.choices(mood=[
        app_commands.Choice(name="😊 Happy", value="happy"),
        app_commands.Choice(name="😔 Sad", value="sad"),
        app_commands.Choice(name="😤 Energetic", value="energetic"),
        app_commands.Choice(name="😌 Relaxed", value="relaxed"),
        app_commands.Choice(name="🤔 Focus", value="focus"),
        app_commands.Choice(name="😴 Sleep", value="sleep"),
        app_commands.Choice(name="🎉 Party", value="party"),
        app_commands.Choice(name="💪 Workout", value="workout"),
    ])
    async def mood_music(self, interaction: discord.Interaction, mood: str):
        """Play music based on mood"""
        mood_playlists = {
            'happy': ['pop', 'electronic'],
            'sad': ['lofi', 'classical'],
            'energetic': ['rock', 'electronic'],
            'relaxed': ['chill', 'jazz'],
            'focus': ['study', 'classical'],
            'sleep': ['lofi', 'chill'],
            'party': ['pop', 'electronic'],
            'workout': ['rock', 'electronic']
        }
        
        if mood not in mood_playlists:
            return await interaction.response.send_message("❌ Invalid mood!", ephemeral=True)
        
        stations = mood_playlists[mood]
        selected_station = stations[0]  # Pick first matching station
        
        # Call radio command
        await self.radio(interaction, selected_station)
    
    @tasks.loop(minutes=5)
    async def activity_monitor_task(self):
        """Monitor voice channel activity and auto-disconnect if empty"""
        try:
            for guild in self.bot.guilds:
                voice_client = guild.voice_client
                if not voice_client or not voice_client.channel:
                    continue
                
                # Count non-bot members
                human_members = [m for m in voice_client.channel.members if not m.bot]
                
                if len(human_members) == 0:
                    # Channel is empty, start timeout
                    guild_id = guild.id
                    if guild_id not in self.activity_monitor:
                        self.activity_monitor[guild_id] = {
                            'empty_since': datetime.datetime.now(),
                            'notified': False
                        }
                    
                    empty_time = datetime.datetime.now() - self.activity_monitor[guild_id]['empty_since']
                    
                    # Disconnect after 10 minutes of inactivity
                    if empty_time.total_seconds() > 600:  # 10 minutes
                        await voice_client.disconnect()
                        if guild_id in self.activity_monitor:
                            del self.activity_monitor[guild_id]
                        logger.info(f"Auto-disconnected from {guild.name} due to inactivity")
                else:
                    # Channel has users, reset timer
                    if guild.id in self.activity_monitor:
                        del self.activity_monitor[guild.id]
                        
        except Exception as e:
            logger.error(f"Error in activity monitor: {e}")
    
    @activity_monitor_task.before_loop
    async def before_activity_monitor(self):
        await self.bot.wait_until_ready()


class RadioControlView(discord.ui.View):
    """Control view for radio stations"""
    
    def __init__(self, station: str, *, timeout=300):
        super().__init__(timeout=timeout)
        self.station = station
    
    @discord.ui.button(emoji="⏸️", label="Pause", style=discord.ButtonStyle.secondary)
    async def pause_radio(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        if player.playing:
            await player.pause()
            button.emoji = "▶️"
            button.label = "Resume"
            await interaction.response.send_message("⏸️ **Radio paused**", ephemeral=True)
        else:
            await player.resume()
            button.emoji = "⏸️"
            button.label = "Pause"
            await interaction.response.send_message("▶️ **Radio resumed**", ephemeral=True)
        
        await interaction.edit_original_response(view=self)
    
    @discord.ui.button(emoji="🔀", label="Switch Station", style=discord.ButtonStyle.primary)
    async def switch_station(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = StationSelectView()
        embed = discord.Embed(
            title="📻 Select Radio Station",
            description="Choose a different radio station to play",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(emoji="⭐", label="Favorite", style=discord.ButtonStyle.success)
    async def favorite_station(self, interaction: discord.Interaction, button: discord.ui.Button):
        # This would typically save to database
        await interaction.response.send_message(f"⭐ Added radio station to your favorites!", ephemeral=True)
    
    @discord.ui.button(emoji="🛑", label="Stop Radio", style=discord.ButtonStyle.danger)
    async def stop_radio(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if player:
            await player.disconnect()
        await interaction.response.send_message("🛑 **Radio stopped and disconnected**", ephemeral=True)


class StationSelectView(discord.ui.View):
    """Station selection view"""
    
    def __init__(self, *, timeout=60):
        super().__init__(timeout=timeout)
    
    @discord.ui.select(
        placeholder="Choose a radio station...",
        options=[
            discord.SelectOption(label="LoFi Hip Hop", description="Chill lo-fi beats", emoji="🎵", value="lofi"),
            discord.SelectOption(label="ChillHop Music", description="Relaxing chill music", emoji="😌", value="chill"),
            discord.SelectOption(label="Smooth Jazz", description="Classic jazz radio", emoji="🎺", value="jazz"),
            discord.SelectOption(label="Classical Music", description="Timeless classical pieces", emoji="🎼", value="classical"),
            discord.SelectOption(label="Electronic Mix", description="Electronic dance music", emoji="⚡", value="electronic"),
        ]
    )
    async def station_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        station = select.values[0]
        cog = interaction.client.get_cog('RadioStreaming')
        if cog:
            await cog.radio(interaction, station)


class FavoritesView(discord.ui.View):
    """Favorites management view"""
    
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(emoji="📻", label="Play Favorite Station", style=discord.ButtonStyle.success)
    async def play_favorite_station(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Would typically load user's favorite station from database
        cog = interaction.client.get_cog('RadioStreaming')
        if cog:
            await cog.radio(interaction, "lofi")  # Default favorite
    
    @discord.ui.button(emoji="🎵", label="Play Favorite Track", style=discord.ButtonStyle.primary)
    async def play_favorite_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🎵 Playing your favorite track...", ephemeral=True)
        # Would typically load and play user's favorite track
    
    @discord.ui.button(emoji="➕", label="Add Current", style=discord.ButtonStyle.secondary)
    async def add_current_favorite(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)
        
        # Would typically save current track to user's favorites in database
        await interaction.response.send_message(f"⭐ Added **{player.current.title}** to your favorites!", ephemeral=True)
    
    @discord.ui.button(emoji="🗑️", label="Manage Favorites", style=discord.ButtonStyle.secondary)
    async def manage_favorites(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🗑️ Manage Favorites",
            description="Use the buttons below to remove favorites",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Setup function for Radio Streaming cog"""
    await bot.add_cog(RadioStreaming(bot))
