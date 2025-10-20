"""
Enhanced Music Commands - Additional features for the music bot
Includes searchmusic, seek, replay, remove, move, jump, and more commands
"""

import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from typing import Optional, List, Union
import datetime
import asyncio
import re
from utils.emoji import *
from utils.advanced_queue import get_queue_manager
from config.config import config
import logging

logger = logging.getLogger(__name__)

class EnhancedCommands(commands.Cog):
    """Enhanced music commands for better control"""
    
    def __init__(self, bot):
        self.bot = bot
        self.queue_manager = get_queue_manager()
    
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
    
    @app_commands.command(name="searchmusic", description="Search for music and choose what to play")
    @app_commands.describe(query="Search query for music")
    async def search(self, interaction: discord.Interaction, query: str):
        """Enhanced search command with multiple results"""
        await interaction.response.defer()
        
        try:
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
            if not tracks:
                return await interaction.followup.send(f"❌ No results found for: **{query}**")
            
            # Create search results embed
            embed = self.create_embed(
                title="🔍 Search Results",
                description=f"Found **{len(tracks)}** results for: `{query}`",
                color=discord.Color.blue()
            )
            
            # Add first 10 results
            results_text = ""
            for i, track in enumerate(tracks[:10], 1):
                duration = str(datetime.timedelta(seconds=int(track.length / 1000)))
                results_text += f"`{i}.` [{track.title[:50]}]({track.uri})\n"
                results_text += f"    🎤 {getattr(track, 'author', 'Unknown')[:30]} • ⏱️ {duration}\n\n"
            
            embed.description += f"\n\n{results_text}"
            
            # Create view for selection
            view = SearchResultView(tracks[:10], interaction.user)
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await interaction.followup.send("❌ An error occurred while searching!")
    
    @app_commands.command(name="seek", description="Seek to a specific position in the current track")
    @app_commands.describe(position="Position to seek to (e.g., 1:30, 90, 2m30s)")
    async def seek(self, interaction: discord.Interaction, position: str):
        """Seek to a specific position in the current track"""
        player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)
        
        # Parse position
        try:
            seconds = self.parse_time(position)
            if seconds < 0 or seconds > (player.current.length / 1000):
                return await interaction.response.send_message(
                    f"❌ Position must be between 0 and {datetime.timedelta(seconds=int(player.current.length / 1000))}",
                    ephemeral=True
                )
            
            await player.seek(seconds * 1000)  # Wavelink uses milliseconds
            
            embed = self.create_embed(
                title="⏩ Seeked",
                description=f"Seeked to **{datetime.timedelta(seconds=seconds)}** in [{player.current.title}]({player.current.uri})",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
        except ValueError as e:
            await interaction.response.send_message(f"❌ Invalid time format: {e}", ephemeral=True)
    
    @app_commands.command(name="fastforward", description="Fast forward the current track")
    @app_commands.describe(seconds="Seconds to fast forward (default: 10)")
    async def fastforward(self, interaction: discord.Interaction, seconds: int = 10):
        """Fast forward the current track"""
        player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)
        
        current_pos = player.position
        new_pos = min(current_pos + (seconds * 1000), player.current.length)
        
        await player.seek(new_pos)
        
        embed = self.create_embed(
            title="⏩ Fast Forwarded",
            description=f"Fast forwarded **{seconds}** seconds",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="rewind", description="Rewind the current track")
    @app_commands.describe(seconds="Seconds to rewind (default: 10)")
    async def rewind(self, interaction: discord.Interaction, seconds: int = 10):
        """Rewind the current track"""
        player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)
        
        current_pos = player.position
        new_pos = max(current_pos - (seconds * 1000), 0)
        
        await player.seek(new_pos)
        
        embed = self.create_embed(
            title="⏪ Rewound",
            description=f"Rewound **{seconds}** seconds",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="replay", description="Replay the current track from the beginning")
    async def replay(self, interaction: discord.Interaction):
        """Replay the current track from the beginning"""
        player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)
        
        await player.seek(0)
        
        embed = self.create_embed(
            title="🔄 Replaying",
            description=f"Replaying [{player.current.title}]({player.current.uri}) from the beginning",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remove", description="Remove a track from the queue")
    @app_commands.describe(position="Position of track to remove (1-based)")
    async def remove(self, interaction: discord.Interaction, position: int):
        """Remove a track from the queue"""
        queue = self.queue_manager.get_queue(interaction.guild.id)
        if not queue or len(queue) == 0:
            return await interaction.response.send_message("❌ Queue is empty!", ephemeral=True)
        
        if position < 1 or position > len(queue):
            return await interaction.response.send_message(
                f"❌ Position must be between 1 and {len(queue)}", ephemeral=True
            )
        
        removed_track = queue.remove_at_position(position - 1)  # Convert to 0-based
        if removed_track:
            embed = self.create_embed(
                title="🗑️ Track Removed",
                description=f"Removed **{removed_track.title}** from position #{position}",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to remove track!", ephemeral=True)
    
    @app_commands.command(name="move", description="Move a track to a different position in the queue")
    @app_commands.describe(from_pos="Current position of track", to_pos="New position for track")
    async def move(self, interaction: discord.Interaction, from_pos: int, to_pos: int):
        """Move a track to a different position"""
        queue = self.queue_manager.get_queue(interaction.guild.id)
        if not queue or len(queue) == 0:
            return await interaction.response.send_message("❌ Queue is empty!", ephemeral=True)
        
        if from_pos < 1 or from_pos > len(queue) or to_pos < 1 or to_pos > len(queue):
            return await interaction.response.send_message(
                f"❌ Positions must be between 1 and {len(queue)}", ephemeral=True
            )
        
        success = queue.move_track(from_pos - 1, to_pos - 1)  # Convert to 0-based
        if success:
            embed = self.create_embed(
                title="📍 Track Moved",
                description=f"Moved track from position #{from_pos} to #{to_pos}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to move track!", ephemeral=True)
    
    @app_commands.command(name="jump", description="Jump to a specific track in the queue")
    @app_commands.describe(position="Position of track to jump to")
    async def jump(self, interaction: discord.Interaction, position: int):
        """Jump to a specific track in the queue"""
        player = interaction.guild.voice_client
        queue = self.queue_manager.get_queue(interaction.guild.id)
        
        if not player:
            return await interaction.response.send_message("❌ Not connected to voice!", ephemeral=True)
        
        if not queue or len(queue) == 0:
            return await interaction.response.send_message("❌ Queue is empty!", ephemeral=True)
        
        if position < 1 or position > len(queue):
            return await interaction.response.send_message(
                f"❌ Position must be between 1 and {len(queue)}", ephemeral=True
            )
        
        # Skip to the desired position
        for _ in range(position - 1):
            queue.get()
        
        next_track = queue.get()
        if next_track:
            await player.play(next_track.track)
            
            embed = self.create_embed(
                title="⏭️ Jumped to Track",
                description=f"Now playing [{next_track.track.title}]({next_track.track.uri})",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="clear_range", description="Clear a range of tracks from the queue")
    @app_commands.describe(start="Start position", end="End position")
    async def clear_range(self, interaction: discord.Interaction, start: int, end: int):
        """Clear a range of tracks from the queue"""
        queue = self.queue_manager.get_queue(interaction.guild.id)
        if not queue or len(queue) == 0:
            return await interaction.response.send_message("❌ Queue is empty!", ephemeral=True)
        
        if start < 1 or end > len(queue) or start > end:
            return await interaction.response.send_message(
                f"❌ Invalid range! Must be between 1 and {len(queue)}", ephemeral=True
            )
        
        removed_count = queue.clear_range(start - 1, end - 1)  # Convert to 0-based
        
        embed = self.create_embed(
            title="🗑️ Range Cleared",
            description=f"Removed **{removed_count}** tracks from positions {start}-{end}",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="autoplay", description="Toggle autoplay mode")
    async def autoplay(self, interaction: discord.Interaction):
        """Toggle autoplay mode"""
        queue = self.queue_manager.get_queue(interaction.guild.id)
        queue.autoplay_enabled = not queue.autoplay_enabled
        
        status = "enabled" if queue.autoplay_enabled else "disabled"
        emoji = "📻" if queue.autoplay_enabled else "📵"
        color = discord.Color.green() if queue.autoplay_enabled else discord.Color.red()
        
        embed = self.create_embed(
            title=f"{emoji} Autoplay {status.title()}",
            description=f"Autoplay is now **{status}**\n"
                       f"{'The bot will automatically play similar songs when the queue is empty' if queue.autoplay_enabled else 'The bot will stop when the queue is empty'}",
            color=color
        )
        await interaction.response.send_message(embed=embed)
    
    def parse_time(self, time_str: str) -> int:
        """Parse time string to seconds"""
        time_str = time_str.strip().lower()
        
        # Handle different formats: 1:30, 90, 2m30s, etc.
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                minutes, seconds = parts
                return int(minutes) * 60 + int(seconds)
            elif len(parts) == 3:
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        
        # Handle 1m30s format
        total_seconds = 0
        time_units = re.findall(r'(\d+)([hms]?)', time_str)
        
        for value, unit in time_units:
            value = int(value)
            if unit == 'h':
                total_seconds += value * 3600
            elif unit == 'm':
                total_seconds += value * 60
            elif unit == 's':
                total_seconds += value
            else:
                # No unit specified, assume seconds
                total_seconds += value
        
        return total_seconds


class SearchResultView(discord.ui.View):
    """View for search results with pagination"""
    
    def __init__(self, tracks: List[wavelink.Playable], user: discord.Member, *, timeout=60):
        super().__init__(timeout=timeout)
        self.tracks = tracks
        self.user = user
        self.current_page = 0
        self.per_page = 5
        
        # Add select menu
        options = []
        for i, track in enumerate(tracks[:10], 1):
            duration = str(datetime.timedelta(seconds=int(track.length / 1000)))
            options.append(discord.SelectOption(
                label=f"{i}. {track.title[:80]}"[:100],
                description=f"by {getattr(track, 'author', 'Unknown')[:30]} • {duration}"[:100],
                value=str(i-1)
            ))
        
        if options:
            self.add_item(TrackSelectDropdown(options, tracks, user))
    
    @discord.ui.button(emoji="▶️", label="Play All", style=discord.ButtonStyle.success)
    async def play_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ Only the search user can use this!", ephemeral=True)
        
        music_cog = interaction.client.get_cog('AdvancedMusic')
        if not music_cog:
            return await interaction.response.send_message("❌ Music system not available!", ephemeral=True)
        
        await interaction.response.defer()
        
        # Add all tracks to queue
        added = 0
        for track in self.tracks:
            try:
                await music_cog.play_track(interaction, track, from_search=True)
                added += 1
                if added >= 10:  # Limit to prevent spam
                    break
            except:
                break
        
        embed = discord.Embed(
            title="✅ Tracks Added",
            description=f"Added **{added}** tracks to the queue",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=None)


class TrackSelectDropdown(discord.ui.Select):
    def __init__(self, options, tracks, user):
        super().__init__(placeholder="Choose a track to play...", options=options)
        self.tracks = tracks
        self.user = user
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ Only the search user can select tracks!", ephemeral=True)
        
        selected_index = int(self.values[0])
        selected_track = self.tracks[selected_index]
        
        music_cog = interaction.client.get_cog('AdvancedMusic')
        if music_cog:
            await music_cog.play_track(interaction, selected_track, from_search=True)
        else:
            await interaction.response.send_message("❌ Music system not available!", ephemeral=True)


async def setup(bot):
    """Setup function for Enhanced Commands cog"""
    await bot.add_cog(EnhancedCommands(bot))
