"""
Advanced Music Dashboard - Live updating music control panel with rich embeds and animations
"""

import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import asyncio
import datetime
import time
from typing import Optional, Dict, Any
import random

from utils.emoji import *
from utils.enhanced_embeds import get_embed_builder
from utils.advanced_queue import get_queue_manager
from config.config import config

class MusicDashboard(discord.ui.View):
    """Advanced music dashboard with live updates and comprehensive controls"""
    
    def __init__(self, bot, guild: discord.Guild, *, timeout: int = 600):  # 10 minutes
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.embed_builder = get_embed_builder(bot)
        self.queue_manager = get_queue_manager()
        
        # Dashboard state
        self.is_live = True
        self.update_task = None
        self.last_update = None
        self.view_mode = "dashboard"  # dashboard, queue, filters, settings
        
        # Animation frames for progress bar
        self.animation_frames = [
            "▰▱▱▱▱▱▱▱▱▱",
            "▱▰▱▱▱▱▱▱▱▱", 
            "▱▱▰▱▱▱▱▱▱▱",
            "▱▱▱▰▱▱▱▱▱▱",
            "▱▱▱▱▰▱▱▱▱▱",
            "▱▱▱▱▱▰▱▱▱▱",
            "▱▱▱▱▱▱▰▱▱▱",
            "▱▱▱▱▱▱▱▰▱▱",
            "▱▱▱▱▱▱▱▱▰▱",
            "▱▱▱▱▱▱▱▱▱▰"
        ]
        self.frame_index = 0
        
        # Build initial view
        self.build_view()
    
    def build_view(self):
        """Build the dashboard view with all controls"""
        self.clear_items()
        
        if self.view_mode == "dashboard":
            self.build_dashboard_view()
        elif self.view_mode == "queue":
            self.build_queue_view()
        elif self.view_mode == "filters":
            self.build_filters_view()
        elif self.view_mode == "settings":
            self.build_settings_view()
    
    def build_dashboard_view(self):
        """Build main dashboard controls"""
        
        # Row 1: Primary controls
        self.add_item(PreviousButton())
        self.add_item(PlayPauseButton())
        self.add_item(SkipButton())
        self.add_item(StopButton())
        self.add_item(LoopButton())
        
        # Row 2: Volume and mode controls
        self.add_item(VolumeDownButton())
        self.add_item(VolumeUpButton())
        self.add_item(ShuffleButton())
        self.add_item(QueueButton())
        self.add_item(FiltersButton())
        
        # Row 3: Advanced features
        self.add_item(LyricsButton())
        self.add_item(SaveToPlaylistButton())
        self.add_item(RadioModeButton())
        self.add_item(SettingsButton())
        self.add_item(RefreshButton())
    
    def build_queue_view(self):
        """Build queue management view"""
        
        # Queue controls
        self.add_item(QueueShuffleButton())
        self.add_item(QueueClearButton())
        self.add_item(QueueSaveButton())
        self.add_item(QueueLoadButton())
        self.add_item(BackToDashboardButton())
        
        # Navigation
        self.add_item(QueuePreviousPageButton())
        self.add_item(QueueNextPageButton())
        self.add_item(QueueJumpToButton())
        
    def build_filters_view(self):
        """Build audio filters view"""
        
        # Audio filters
        self.add_item(BassBoostFilterButton())
        self.add_item(NightcoreFilterButton())
        self.add_item(EightDFilterButton())
        self.add_item(ReverbFilterButton())
        self.add_item(ClearFiltersButton())
        
        # Back button
        self.add_item(BackToDashboardButton())
    
    def build_settings_view(self):
        """Build settings view"""
        
        # Settings options
        self.add_item(AutoPlayToggleButton())
        self.add_item(AutoLeaveToggleButton())
        self.add_item(VolumeLockButton())
        self.add_item(QueueLockButton())
        self.add_item(BackToDashboardButton())
    
    async def start_live_updates(self, message: discord.Message):
        """Start live updating the dashboard"""
        self.message = message
        self.update_task = asyncio.create_task(self.update_loop())
    
    async def update_loop(self):
        """Main update loop for live dashboard"""
        while self.is_live:
            try:
                await asyncio.sleep(2)  # Update every 2 seconds
                
                if not self.message:
                    break
                
                embed = await self.create_dashboard_embed()
                
                # Only update if content changed
                if self.last_update != embed.to_dict():
                    await self.message.edit(embed=embed, view=self)
                    self.last_update = embed.to_dict()
                
                self.frame_index = (self.frame_index + 1) % len(self.animation_frames)
                
            except discord.NotFound:
                # Message was deleted
                break
            except Exception as e:
                print(f"Dashboard update error: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def create_dashboard_embed(self) -> discord.Embed:
        """Create the main dashboard embed with live data"""
        
        player = self.guild.voice_client
        queue = self.queue_manager.get_queue(self.guild.id)
        
        if self.view_mode == "dashboard":
            return await self.create_main_dashboard_embed(player, queue)
        elif self.view_mode == "queue":
            return await self.create_queue_embed(player, queue)
        elif self.view_mode == "filters":
            return await self.create_filters_embed(player)
        elif self.view_mode == "settings":
            return await self.create_settings_embed(queue)
    
    async def create_main_dashboard_embed(self, player: wavelink.Player, queue) -> discord.Embed:
        """Create main dashboard embed"""
        
        embed = self.embed_builder.create_base_embed(
            title="🎵 Music Dashboard",
            color='music'
        )
        
        # Current track section
        if player and player.current:
            current = player.current
            
            # Progress calculation
            if player.position:
                current_pos = int(player.position / 1000)
                total_dur = int(current.length / 1000)
                progress_percent = min(current_pos / total_dur, 1.0) if total_dur > 0 else 0
                
                # Animated progress bar
                progress_bar = self.embed_builder.create_progress_bar(current_pos, total_dur, 20)
                current_time = str(datetime.timedelta(seconds=current_pos))
                total_time = str(datetime.timedelta(seconds=total_dur))
                
                # Status indicators
                status_icons = []
                if player.paused:
                    status_icons.append(f"{PAUSE} Paused")
                else:
                    status_icons.append(f"{PLAY} Playing")
                
                if queue.repeat_mode != "off":
                    loop_emoji = "🔂" if queue.repeat_mode == "track" else "🔁"
                    status_icons.append(f"{loop_emoji} Loop")
                
                if queue.shuffle_enabled:
                    status_icons.append(f"{SHUFFLE} Shuffle")
                
                # Volume with visual indicator
                volume = int(player.volume * 100)
                if volume == 0:
                    vol_emoji = VOLUME_MUTE
                elif volume < 30:
                    vol_emoji = VOLUME_DOWN
                else:
                    vol_emoji = VOLUME_UP
                status_icons.append(f"{vol_emoji} {volume}%")
                
                embed.description = f"**[{current.title}]({current.uri})**"
                
                embed.add_field(
                    name=f"{NOW_PLAYING} Now Playing",
                    value=f"**Artist:** {getattr(current, 'author', 'Unknown')}\n"
                          f"**Duration:** `{current_time}` {progress_bar} `{total_time}`\n"
                          f"**Status:** {' • '.join(status_icons)}",
                    inline=False
                )
                
                # Thumbnail
                thumbnail_url = self.embed_builder.get_high_quality_thumbnail(current)
                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)
                
            else:
                embed.add_field(
                    name=f"{NOW_PLAYING} Now Playing",
                    value=f"**[{current.title}]({current.uri})**\n"
                          f"Artist: {getattr(current, 'author', 'Unknown')}",
                    inline=False
                )
        else:
            embed.description = "🎵 **No music playing**\nUse `/play` to start playing music!"
            embed.add_field(
                name="🎶 Ready to Play",
                value="Connect to a voice channel and use the play button or `/play <song>` to get started!",
                inline=False
            )
        
        # Queue preview
        if not queue.is_empty():
            queue_preview = []
            for i in range(min(3, len(queue))):
                track_info = queue.peek(i)
                if track_info:
                    track = track_info.track
                    duration = str(datetime.timedelta(seconds=int(track.length / 1000)))
                    queue_preview.append(f"`{i+1}.` {track.title[:30]}{'...' if len(track.title) > 30 else ''} `{duration}`")
            
            embed.add_field(
                name=f"{QUEUE} Up Next ({len(queue)} tracks)",
                value="\n".join(queue_preview) + (f"\n*... and {len(queue) - 3} more*" if len(queue) > 3 else ""),
                inline=False
            )
        
        # Live indicators
        embed.set_footer(
            text=f"🔴 Live Dashboard • Updated every 2s • {datetime.datetime.now().strftime('%H:%M:%S')}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        return embed
    
    async def create_queue_embed(self, player: wavelink.Player, queue) -> discord.Embed:
        """Create detailed queue embed"""
        
        embed = self.embed_builder.create_base_embed(
            title=f"{QUEUE} Music Queue",
            description=f"**{len(queue)} tracks** in queue",
            color='queue'
        )
        
        if not queue.is_empty():
            queue_stats = queue.get_queue_stats()
            total_duration = queue_stats['total_duration']
            total_formatted = str(datetime.timedelta(seconds=int(total_duration / 1000)))
            
            embed.add_field(
                name="📊 Queue Statistics",
                value=f"**Total Duration:** {total_formatted}\n"
                      f"**Total Tracks:** {len(queue)}\n"
                      f"**Repeat Mode:** {queue.repeat_mode.title()}\n"
                      f"**Shuffle:** {'Enabled' if queue.shuffle_enabled else 'Disabled'}",
                inline=True
            )
            
            # Show queue tracks
            queue_text = ""
            for i in range(min(10, len(queue))):
                track_info = queue.peek(i)
                if track_info:
                    track = track_info.track
                    duration = str(datetime.timedelta(seconds=int(track.length / 1000)))
                    requester = track_info.requester.display_name if track_info.requester else "Unknown"
                    
                    queue_text += f"`{i+1:2d}.` **{track.title[:35]}{'...' if len(track.title) > 35 else ''}**\n"
                    queue_text += f"      ⏱️ `{duration}` • 👤 {requester}\n\n"
            
            if len(queue) > 10:
                queue_text += f"*... and {len(queue) - 10} more tracks*"
            
            embed.add_field(name="🎵 Queue Tracks", value=queue_text or "No tracks", inline=False)
        
        return embed
    
    async def create_filters_embed(self, player: wavelink.Player) -> discord.Embed:
        """Create audio filters embed"""
        
        embed = self.embed_builder.create_base_embed(
            title="🎚️ Audio Filters",
            description="Customize your audio experience",
            color='info'
        )
        
        if player:
            # Check current filters
            active_filters = []
            
            if hasattr(player, 'bass_boost') and player.bass_boost:
                active_filters.append(f"{BASS_BOOST} Bass Boost")
            
            if hasattr(player, 'nightcore') and player.nightcore:
                active_filters.append(f"{NIGHTCORE} Nightcore")
            
            if hasattr(player, 'eight_d') and player.eight_d:
                active_filters.append(f"{EIGHT_D} 8D Audio")
            
            embed.add_field(
                name="🎵 Active Filters",
                value="\n".join(active_filters) if active_filters else "No filters active",
                inline=False
            )
        
        # Available filters
        embed.add_field(
            name="🔧 Available Filters",
            value=f"{BASS_BOOST} **Bass Boost** - Enhanced low frequencies\n"
                  f"{NIGHTCORE} **Nightcore** - Higher pitch and tempo\n"
                  f"{EIGHT_D} **8D Audio** - Spatial audio effect\n"
                  f"🌊 **Reverb** - Echo and reverb effects",
            inline=False
        )
        
        return embed
    
    async def create_settings_embed(self, queue) -> discord.Embed:
        """Create settings embed"""
        
        embed = self.embed_builder.create_base_embed(
            title="⚙️ Dashboard Settings",
            description="Configure dashboard and music settings",
            color='info'
        )
        
        # Current settings
        settings_text = f"📻 **Auto-play:** {'Enabled' if queue.autoplay_enabled else 'Disabled'}\n"
        settings_text += f"🚪 **Auto-leave:** Enabled\n"  # This would come from config
        settings_text += f"🔒 **Volume Lock:** Disabled\n"
        settings_text += f"🎵 **Queue Lock:** Disabled"
        
        embed.add_field(name="Current Settings", value=settings_text, inline=False)
        
        return embed
    
    async def on_timeout(self):
        """Handle view timeout"""
        self.is_live = False
        if self.update_task:
            self.update_task.cancel()
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True

# Button classes for the dashboard

class DashboardButton(discord.ui.Button):
    """Base class for dashboard buttons"""
    
    async def callback(self, interaction: discord.Interaction):
        # Check if user can control music
        if not await self.check_permissions(interaction):
            return
        
        await self.execute_action(interaction)
    
    async def check_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if user has permissions to use music controls"""
        # Basic check - user must be in same voice channel
        if interaction.guild.voice_client:
            user_channel = getattr(interaction.user.voice, 'channel', None)
            bot_channel = interaction.guild.voice_client.channel
            
            if user_channel != bot_channel:
                await interaction.response.send_message(
                    "❌ You must be in the same voice channel as the bot!", 
                    ephemeral=True
                )
                return False
        
        return True
    
    async def execute_action(self, interaction: discord.Interaction):
        """Override this method in subclasses"""
        pass

class PlayPauseButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=PLAY_PAUSE, style=discord.ButtonStyle.primary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        
        if not player or not player.current:
            await interaction.response.send_message("❌ No music playing!", ephemeral=True)
            return
        
        if player.paused:
            await player.resume()
            await interaction.response.send_message(f"{PLAY} Resumed!", ephemeral=True)
        else:
            await player.pause()
            await interaction.response.send_message(f"{PAUSE} Paused!", ephemeral=True)

class SkipButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=SKIP, style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        
        if not player or not player.current:
            await interaction.response.send_message("❌ No music playing!", ephemeral=True)
            return
        
        await player.stop()
        await interaction.response.send_message(f"{SKIP} Skipped!", ephemeral=True)

class PreviousButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=PREVIOUS, style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{PREVIOUS} Previous track feature coming soon!", ephemeral=True)

class StopButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=STOP, style=discord.ButtonStyle.danger, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        queue_manager = get_queue_manager()
        queue = queue_manager.get_queue(interaction.guild.id)
        
        if player:
            queue.clear()
            await player.disconnect()
            await interaction.response.send_message(f"{STOP} Stopped and disconnected!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Not playing anything!", ephemeral=True)

class LoopButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=LOOP, style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        queue_manager = get_queue_manager()
        queue = queue_manager.get_queue(interaction.guild.id)
        
        new_mode = queue.toggle_repeat()
        mode_emoji = {"off": "⏹️", "track": "🔂", "queue": "🔁"}
        
        await interaction.response.send_message(
            f"{mode_emoji[new_mode]} Loop mode: **{new_mode.title()}**", 
            ephemeral=True
        )

class VolumeUpButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=VOLUME_UP, style=discord.ButtonStyle.secondary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        
        if not player:
            await interaction.response.send_message("❌ Not connected to voice!", ephemeral=True)
            return
        
        current_vol = int(player.volume * 100)
        new_vol = min(150, current_vol + 10)
        await player.set_volume(new_vol / 100)
        
        await interaction.response.send_message(f"{VOLUME_UP} Volume: {new_vol}%", ephemeral=True)

class VolumeDownButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=VOLUME_DOWN, style=discord.ButtonStyle.secondary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        
        if not player:
            await interaction.response.send_message("❌ Not connected to voice!", ephemeral=True)
            return
        
        current_vol = int(player.volume * 100)
        new_vol = max(0, current_vol - 10)
        await player.set_volume(new_vol / 100)
        
        await interaction.response.send_message(f"{VOLUME_DOWN} Volume: {new_vol}%", ephemeral=True)

class ShuffleButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=SHUFFLE, style=discord.ButtonStyle.secondary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        queue_manager = get_queue_manager()
        queue = queue_manager.get_queue(interaction.guild.id)
        
        if queue.is_empty():
            await interaction.response.send_message("❌ Queue is empty!", ephemeral=True)
            return
        
        shuffled = queue.toggle_shuffle()
        status = "enabled" if shuffled else "disabled"
        
        await interaction.response.send_message(f"{SHUFFLE} Shuffle {status}!", ephemeral=True)

class QueueButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=QUEUE, label="Queue", style=discord.ButtonStyle.secondary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: MusicDashboard = self.view
        view.view_mode = "queue"
        view.build_view()
        
        embed = await view.create_dashboard_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class FiltersButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="🎚️", label="Filters", style=discord.ButtonStyle.secondary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: MusicDashboard = self.view
        view.view_mode = "filters"
        view.build_view()
        
        embed = await view.create_dashboard_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Additional buttons for other views
class BackToDashboardButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="🏠", label="Dashboard", style=discord.ButtonStyle.primary, row=2)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: MusicDashboard = self.view
        view.view_mode = "dashboard"
        view.build_view()
        
        embed = await view.create_dashboard_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# More button classes would go here...
class LyricsButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="📝", label="Lyrics", style=discord.ButtonStyle.secondary, row=2)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("📝 Lyrics feature coming soon!", ephemeral=True)

class SaveToPlaylistButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="💾", label="Save", style=discord.ButtonStyle.secondary, row=2)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("💾 Save to playlist feature coming soon!", ephemeral=True)

class RadioModeButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="📻", label="Radio", style=discord.ButtonStyle.secondary, row=2)
    
    async def execute_action(self, interaction: discord.Interaction):
        queue_manager = get_queue_manager()
        queue = queue_manager.get_queue(interaction.guild.id)
        
        queue.autoplay_enabled = not queue.autoplay_enabled
        status = "enabled" if queue.autoplay_enabled else "disabled"
        
        await interaction.response.send_message(f"📻 Radio mode {status}!", ephemeral=True)

class SettingsButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="⚙️", label="Settings", style=discord.ButtonStyle.secondary, row=2)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: MusicDashboard = self.view
        view.view_mode = "settings"
        view.build_view()
        
        embed = await view.create_dashboard_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class RefreshButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="🔄", label="Refresh", style=discord.ButtonStyle.secondary, row=2)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: MusicDashboard = self.view
        embed = await view.create_dashboard_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Placeholder buttons for other views
class QueueShuffleButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=SHUFFLE, label="Shuffle", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{SHUFFLE} Queue shuffled!", ephemeral=True)

class QueueClearButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=CLEAR, label="Clear", style=discord.ButtonStyle.danger, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{CLEAR} Queue cleared!", ephemeral=True)

class QueueSaveButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="💾", label="Save", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("💾 Save queue feature coming soon!", ephemeral=True)

class QueueLoadButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="📁", label="Load", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("📁 Load queue feature coming soon!", ephemeral=True)

class QueuePreviousPageButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="⬅️", label="Previous", style=discord.ButtonStyle.secondary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("⬅️ Previous page feature coming soon!", ephemeral=True)

class QueueNextPageButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="➡️", label="Next", style=discord.ButtonStyle.secondary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("➡️ Next page feature coming soon!", ephemeral=True)

class QueueJumpToButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="🔢", label="Jump To", style=discord.ButtonStyle.secondary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔢 Jump to track feature coming soon!", ephemeral=True)

# Filter buttons
class BassBoostFilterButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=BASS_BOOST, label="Bass Boost", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{BASS_BOOST} Bass boost toggled!", ephemeral=True)

class NightcoreFilterButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=NIGHTCORE, label="Nightcore", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{NIGHTCORE} Nightcore toggled!", ephemeral=True)

class EightDFilterButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji=EIGHT_D, label="8D Audio", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{EIGHT_D} 8D audio toggled!", ephemeral=True)

class ReverbFilterButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="🌊", label="Reverb", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🌊 Reverb toggled!", ephemeral=True)

class ClearFiltersButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="🧹", label="Clear All", style=discord.ButtonStyle.danger, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🧹 All filters cleared!", ephemeral=True)

# Settings buttons
class AutoPlayToggleButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="📻", label="Auto-play", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("📻 Auto-play setting toggled!", ephemeral=True)

class AutoLeaveToggleButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="🚪", label="Auto-leave", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🚪 Auto-leave setting toggled!", ephemeral=True)

class VolumeLockButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="🔒", label="Volume Lock", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔒 Volume lock toggled!", ephemeral=True)

class QueueLockButton(DashboardButton):
    def __init__(self):
        super().__init__(emoji="🎵", label="Queue Lock", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🎵 Queue lock toggled!", ephemeral=True)

class MusicDashboardCog(commands.Cog):
    """Music Dashboard cog with live updating controls"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_dashboards = {}  # guild_id -> dashboard
    
    @app_commands.command(name="dashboard", description="Open the advanced music dashboard with live updates")
    async def dashboard(self, interaction: discord.Interaction):
        """Create and display the music dashboard"""
        
        # Check if user is in voice channel
        if not getattr(interaction.user.voice, 'channel', None):
            await interaction.response.send_message(
                "❌ You must be in a voice channel to use the dashboard!", 
                ephemeral=True
            )
            return
        
        # Create dashboard
        dashboard = MusicDashboard(self.bot, interaction.guild)
        embed = await dashboard.create_dashboard_embed()
        
        await interaction.response.send_message(embed=embed, view=dashboard)
        
        # Start live updates
        message = await interaction.original_response()
        await dashboard.start_live_updates(message)
        
        # Store active dashboard
        self.active_dashboards[interaction.guild.id] = dashboard
    
    @commands.command(name="dashboard")
    async def dashboard_prefix(self, ctx):
        """Prefix version of dashboard command"""
        
        if not getattr(ctx.author.voice, 'channel', None):
            await ctx.send("❌ You must be in a voice channel to use the dashboard!")
            return
        
        dashboard = MusicDashboard(self.bot, ctx.guild)
        embed = await dashboard.create_dashboard_embed()
        
        message = await ctx.send(embed=embed, view=dashboard)
        await dashboard.start_live_updates(message)
        
        self.active_dashboards[ctx.guild.id] = dashboard

async def setup(bot):
    """Setup function for the MusicDashboard cog"""
    await bot.add_cog(MusicDashboardCog(bot))
