"""
DJ and Moderation Commands - Vote skip, DJ roles, queue limits, and moderation features
"""

import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from typing import Optional, List, Dict, Set
import datetime
import asyncio
from utils.emoji import *
from utils.advanced_queue import get_queue_manager
from config.config import config
import logging

logger = logging.getLogger(__name__)

class DJModeration(commands.Cog):
    """DJ and moderation commands for music control"""
    
    def __init__(self, bot):
        self.bot = bot
        self.queue_manager = get_queue_manager()
        self.vote_skips: Dict[int, Set[int]] = {}  # guild_id -> set of user_ids who voted
        self.banned_tracks: Dict[int, List[str]] = {}  # guild_id -> list of banned URIs
        self.queue_limits: Dict[int, Dict[int, int]] = {}  # guild_id -> user_id -> track_count
        self.dj_roles: Dict[int, List[int]] = {}  # guild_id -> list of role_ids
    
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
    
    def is_dj(self, member: discord.Member) -> bool:
        """Check if member has DJ permissions"""
        # Bot owner is always DJ
        if member.id in getattr(config, 'OWNERS', []):
            return True
        
        # Administrator permission
        if member.guild_permissions.administrator:
            return True
        
        # Check DJ roles
        guild_dj_roles = self.dj_roles.get(member.guild.id, [])
        for role in member.roles:
            if role.id in guild_dj_roles:
                return True
        
        # If alone in voice channel
        if member.voice and len([m for m in member.voice.channel.members if not m.bot]) == 1:
            return True
        
        return False
    
    def get_vote_threshold(self, guild: discord.Guild) -> int:
        """Calculate vote threshold for skip votes"""
        voice_client = guild.voice_client
        if not voice_client:
            return 1
        
        # Count non-bot members in voice channel
        members_count = len([m for m in voice_client.channel.members if not m.bot])
        if members_count <= 2:
            return 1
        elif members_count <= 4:
            return 2
        else:
            return max(2, members_count // 2)
    
    @app_commands.command(name="voteskip", description="Vote to skip the current track")
    async def voteskip(self, interaction: discord.Interaction):
        """Vote to skip the current track"""
        player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)
        
        # Check if user is in voice channel
        if not interaction.user.voice or interaction.user.voice.channel != player.channel:
            return await interaction.response.send_message("❌ You need to be in the same voice channel!", ephemeral=True)
        
        # DJ can force skip
        if self.is_dj(interaction.user):
            await player.stop()
            embed = self.create_embed(
                title="⏭️ DJ Skip",
                description=f"**{interaction.user.display_name}** (DJ) skipped [{player.current.title}]({player.current.uri})",
                color=discord.Color.gold()
            )
            return await interaction.response.send_message(embed=embed)
        
        # Initialize vote skip for this guild
        if interaction.guild.id not in self.vote_skips:
            self.vote_skips[interaction.guild.id] = set()
        
        # Check if user already voted
        if interaction.user.id in self.vote_skips[interaction.guild.id]:
            return await interaction.response.send_message("❌ You already voted to skip this track!", ephemeral=True)
        
        # Add vote
        self.vote_skips[interaction.guild.id].add(interaction.user.id)
        
        # Calculate threshold
        threshold = self.get_vote_threshold(interaction.guild)
        current_votes = len(self.vote_skips[interaction.guild.id])
        
        embed = self.create_embed(
            title="🗳️ Vote Skip",
            color=discord.Color.orange()
        )
        
        if current_votes >= threshold:
            # Skip the track
            await player.stop()
            embed.title = "⏭️ Track Skipped"
            embed.description = f"Skipped [{player.current.title}]({player.current.uri}) with **{current_votes}** votes"
            embed.color = discord.Color.green()
            
            # Clear votes
            self.vote_skips[interaction.guild.id].clear()
        else:
            embed.description = f"Vote to skip [{player.current.title}]({player.current.uri})\n"
            embed.description += f"**{current_votes}/{threshold}** votes needed"
            embed.add_field(
                name="Voters",
                value=", ".join([f"<@{uid}>" for uid in self.vote_skips[interaction.guild.id]]),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="forceskip", description="Force skip the current track (DJ only)")
    async def forceskip(self, interaction: discord.Interaction):
        """Force skip the current track (DJ only)"""
        if not self.is_dj(interaction.user):
            return await interaction.response.send_message("❌ You need DJ permissions to force skip!", ephemeral=True)
        
        player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing is currently playing!", ephemeral=True)
        
        track_title = player.current.title
        await player.stop()
        
        # Clear any ongoing votes
        if interaction.guild.id in self.vote_skips:
            self.vote_skips[interaction.guild.id].clear()
        
        embed = self.create_embed(
            title="⏭️ Force Skipped",
            description=f"**{interaction.user.display_name}** force skipped **{track_title}**",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="set_dj_role", description="Set DJ role for the server (Admin only)")
    @app_commands.describe(role="Role to grant DJ permissions")
    async def set_dj_role(self, interaction: discord.Interaction, role: discord.Role):
        """Set DJ role for the server"""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ You need administrator permissions!", ephemeral=True)
        
        if interaction.guild.id not in self.dj_roles:
            self.dj_roles[interaction.guild.id] = []
        
        if role.id in self.dj_roles[interaction.guild.id]:
            return await interaction.response.send_message(f"❌ {role.mention} is already a DJ role!", ephemeral=True)
        
        self.dj_roles[interaction.guild.id].append(role.id)
        
        embed = self.create_embed(
            title="✅ DJ Role Added",
            description=f"Added {role.mention} as a DJ role\nMembers with this role can now control music without voting",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remove_dj_role", description="Remove DJ role from the server (Admin only)")
    @app_commands.describe(role="Role to remove DJ permissions from")
    async def remove_dj_role(self, interaction: discord.Interaction, role: discord.Role):
        """Remove DJ role from the server"""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ You need administrator permissions!", ephemeral=True)
        
        if interaction.guild.id not in self.dj_roles or role.id not in self.dj_roles[interaction.guild.id]:
            return await interaction.response.send_message(f"❌ {role.mention} is not a DJ role!", ephemeral=True)
        
        self.dj_roles[interaction.guild.id].remove(role.id)
        
        embed = self.create_embed(
            title="❌ DJ Role Removed",
            description=f"Removed {role.mention} from DJ roles",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="dj_roles", description="View current DJ roles")
    async def dj_roles(self, interaction: discord.Interaction):
        """View current DJ roles"""
        guild_dj_roles = self.dj_roles.get(interaction.guild.id, [])
        
        embed = self.create_embed(
            title="🎧 DJ Roles",
            color=discord.Color.blue()
        )
        
        if not guild_dj_roles:
            embed.description = "No DJ roles set for this server"
        else:
            role_mentions = []
            for role_id in guild_dj_roles:
                role = interaction.guild.get_role(role_id)
                if role:
                    role_mentions.append(role.mention)
            
            embed.description = "\\n".join(role_mentions) if role_mentions else "No valid DJ roles found"
        
        embed.add_field(
            name="DJ Permissions Include:",
            value="• Force skip tracks\\n• No queue limits\\n• Access to all music controls\\n• Bypass voting requirements",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="ban_track", description="Ban a track from being played (DJ only)")
    @app_commands.describe(track_url="URL of the track to ban")
    async def ban_track(self, interaction: discord.Interaction, track_url: str):
        """Ban a track from being played"""
        if not self.is_dj(interaction.user):
            return await interaction.response.send_message("❌ You need DJ permissions to ban tracks!", ephemeral=True)
        
        if interaction.guild.id not in self.banned_tracks:
            self.banned_tracks[interaction.guild.id] = []
        
        if track_url in self.banned_tracks[interaction.guild.id]:
            return await interaction.response.send_message("❌ This track is already banned!", ephemeral=True)
        
        self.banned_tracks[interaction.guild.id].append(track_url)
        
        # Try to get track info
        try:
            tracks = await wavelink.Playable.search(track_url)
            track_name = tracks[0].title if tracks else "Unknown Track"
        except:
            track_name = "Unknown Track"
        
        embed = self.create_embed(
            title="🚫 Track Banned",
            description=f"Banned **{track_name}** from being played in this server",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="unban_track", description="Unban a track (DJ only)")
    @app_commands.describe(track_url="URL of the track to unban")
    async def unban_track(self, interaction: discord.Interaction, track_url: str):
        """Unban a track"""
        if not self.is_dj(interaction.user):
            return await interaction.response.send_message("❌ You need DJ permissions to unban tracks!", ephemeral=True)
        
        if interaction.guild.id not in self.banned_tracks or track_url not in self.banned_tracks[interaction.guild.id]:
            return await interaction.response.send_message("❌ This track is not banned!", ephemeral=True)
        
        self.banned_tracks[interaction.guild.id].remove(track_url)
        
        embed = self.create_embed(
            title="✅ Track Unbanned",
            description=f"Unbanned the track - it can now be played again",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="banned_tracks", description="View banned tracks")
    async def banned_tracks_list(self, interaction: discord.Interaction):
        """View banned tracks"""
        guild_banned = self.banned_tracks.get(interaction.guild.id, [])
        
        embed = self.create_embed(
            title="🚫 Banned Tracks",
            color=discord.Color.red()
        )
        
        if not guild_banned:
            embed.description = "No tracks are currently banned in this server"
        else:
            # Get track names for first 10 banned tracks
            track_list = []
            for i, track_url in enumerate(guild_banned[:10], 1):
                try:
                    tracks = await wavelink.Playable.search(track_url)
                    track_name = tracks[0].title if tracks else "Unknown Track"
                    track_list.append(f"`{i}.` {track_name}")
                except:
                    track_list.append(f"`{i}.` Unknown Track")
            
            embed.description = "\\n".join(track_list)
            
            if len(guild_banned) > 10:
                embed.set_footer(text=f"Showing 10 of {len(guild_banned)} banned tracks")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="queue_limit", description="Set queue limit per user (DJ only)")
    @app_commands.describe(limit="Maximum tracks per user (0 for unlimited)")
    async def queue_limit(self, interaction: discord.Interaction, limit: int):
        """Set queue limit per user"""
        if not self.is_dj(interaction.user):
            return await interaction.response.send_message("❌ You need DJ permissions to set queue limits!", ephemeral=True)
        
        if limit < 0:
            return await interaction.response.send_message("❌ Limit cannot be negative!", ephemeral=True)
        
        if interaction.guild.id not in self.queue_limits:
            self.queue_limits[interaction.guild.id] = {}
        
        # Store the limit (0 means unlimited)
        for user_id in self.queue_limits[interaction.guild.id]:
            self.queue_limits[interaction.guild.id][user_id] = 0  # Reset counts
        
        embed = self.create_embed(
            title="📊 Queue Limit Set",
            description=f"Set queue limit to **{'unlimited' if limit == 0 else f'{limit} tracks'}** per user",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="clear_user_queue", description="Clear a user's tracks from queue (DJ only)")
    @app_commands.describe(user="User whose tracks to remove")
    async def clear_user_queue(self, interaction: discord.Interaction, user: discord.Member):
        """Clear a user's tracks from the queue"""
        if not self.is_dj(interaction.user):
            return await interaction.response.send_message("❌ You need DJ permissions to clear user queues!", ephemeral=True)
        
        queue = self.queue_manager.get_queue(interaction.guild.id)
        if not queue:
            return await interaction.response.send_message("❌ Queue is empty!", ephemeral=True)
        
        removed_count = queue.remove_user_tracks(user.id)
        
        embed = self.create_embed(
            title="🗑️ User Queue Cleared",
            description=f"Removed **{removed_count}** tracks from {user.mention}'s queue",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="move_to_top", description="Move a track to the top of queue (DJ only)")
    @app_commands.describe(position="Position of track to move to top")
    async def move_to_top(self, interaction: discord.Interaction, position: int):
        """Move a track to the top of the queue"""
        if not self.is_dj(interaction.user):
            return await interaction.response.send_message("❌ You need DJ permissions to reorder the queue!", ephemeral=True)
        
        queue = self.queue_manager.get_queue(interaction.guild.id)
        if not queue or len(queue) == 0:
            return await interaction.response.send_message("❌ Queue is empty!", ephemeral=True)
        
        if position < 1 or position > len(queue):
            return await interaction.response.send_message(f"❌ Position must be between 1 and {len(queue)}", ephemeral=True)
        
        success, track_title = queue.move_to_top(position - 1)  # Convert to 0-based
        if success:
            embed = self.create_embed(
                title="⬆️ Moved to Top",
                description=f"Moved **{track_title}** to the top of the queue",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to move track!", ephemeral=True)
    
    async def check_track_banned(self, guild_id: int, track_uri: str) -> bool:
        """Check if a track is banned"""
        guild_banned = self.banned_tracks.get(guild_id, [])
        return track_uri in guild_banned
    
    async def check_user_queue_limit(self, guild_id: int, user_id: int, limit: int = 0) -> bool:
        """Check if user has exceeded their queue limit"""
        if limit == 0:  # Unlimited
            return True
        
        if guild_id not in self.queue_limits:
            self.queue_limits[guild_id] = {}
        
        current_count = self.queue_limits[guild_id].get(user_id, 0)
        return current_count < limit
    
    async def increment_user_queue_count(self, guild_id: int, user_id: int):
        """Increment user's queue count"""
        if guild_id not in self.queue_limits:
            self.queue_limits[guild_id] = {}
        
        self.queue_limits[guild_id][user_id] = self.queue_limits[guild_id].get(user_id, 0) + 1
    
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload):
        """Clear vote skips when track ends"""
        # Check if player has valid guild reference
        if not payload.player or not payload.player.guild:
            return
            
        if payload.player.guild.id in self.vote_skips:
            self.vote_skips[payload.player.guild.id].clear()


class VoteSkipView(discord.ui.View):
    """View for vote skip interface"""
    
    def __init__(self, guild_id: int, track_title: str, *, timeout=60):
        super().__init__(timeout=timeout)
        self.guild_id = guild_id
        self.track_title = track_title
    
    @discord.ui.button(emoji="⏭️", label="Vote Skip", style=discord.ButtonStyle.secondary)
    async def vote_skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        dj_cog = interaction.client.get_cog('DJModeration')
        if dj_cog:
            await dj_cog.voteskip(interaction)


async def setup(bot):
    """Setup function for DJ Moderation cog"""
    await bot.add_cog(DJModeration(bot))
