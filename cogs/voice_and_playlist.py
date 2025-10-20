"""
Voice and Playlist Management - Enhanced join command and playlist features
"""

import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from typing import Optional, List, Dict
import datetime
import json
import asyncio
from utils.emoji import *
from database.models import db
from config.config import config
import logging

logger = logging.getLogger(__name__)

class VoiceAndPlaylist(commands.Cog):
    """Voice connection and playlist management"""
    
    def __init__(self, bot):
        self.bot = bot
    
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
    
    async def ensure_permissions(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> bool:
        """Check bot permissions for voice channel"""
        permissions = channel.permissions_for(interaction.guild.me)
        missing = []
        
        if not permissions.connect:
            missing.append("Connect")
        if not permissions.speak:
            missing.append("Speak")
        if not permissions.use_voice_activation:
            missing.append("Use Voice Activity")
        
        if missing:
            embed = self.create_embed(
                title="❌ Missing Permissions",
                description=f"I need the following permissions in {channel.mention}:\n" + 
                           "\n".join(f"• {perm}" for perm in missing),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        
        return True
    
    @app_commands.command(name="join", description="Join your voice channel or a specific channel")
    @app_commands.describe(channel="Voice channel to join (optional)")
    async def join(self, interaction: discord.Interaction, channel: Optional[discord.VoiceChannel] = None):
        """Enhanced join command with better features"""
        
        # Check if bot is already connected
        if interaction.guild.voice_client:
            current_channel = interaction.guild.voice_client.channel
            
            # If trying to join the same channel
            if channel and current_channel.id == channel.id:
                embed = self.create_embed(
                    title="📍 Already Connected",
                    description=f"I'm already connected to {current_channel.mention}",
                    color=discord.Color.orange()
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # If no channel specified and already connected
            if not channel:
                embed = self.create_embed(
                    title="📍 Currently Connected",
                    description=f"I'm currently connected to {current_channel.mention}\n"
                               f"Use `/join <channel>` to move to a different channel",
                    color=discord.Color.blue()
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Determine target channel
        target_channel = channel
        if not target_channel:
            if not interaction.user.voice:
                embed = self.create_embed(
                    title="❌ No Voice Channel",
                    description="You need to be in a voice channel or specify one to join!",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            target_channel = interaction.user.voice.channel
        
        # Check permissions
        if not await self.ensure_permissions(interaction, target_channel):
            return
        
        # Check channel limits
        if target_channel.user_limit > 0 and len(target_channel.members) >= target_channel.user_limit:
            embed = self.create_embed(
                title="❌ Channel Full",
                description=f"{target_channel.mention} is full ({len(target_channel.members)}/{target_channel.user_limit})",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        try:
            # Connect to voice channel
            if interaction.guild.voice_client:
                # Move to new channel
                await interaction.guild.voice_client.move_to(target_channel)
                action = "Moved to"
                emoji = "🔄"
            else:
                # Connect to channel
                await target_channel.connect(cls=wavelink.Player)
                action = "Joined"
                emoji = JOIN
            
            # Create success embed with channel info
            embed = self.create_embed(
                title=f"{emoji} {action} Voice Channel",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Channel",
                value=f"{target_channel.mention}",
                inline=True
            )
            
            embed.add_field(
                name="Members",
                value=f"{len(target_channel.members)}{f'/{target_channel.user_limit}' if target_channel.user_limit else ''}",
                inline=True
            )
            
            embed.add_field(
                name="Bitrate",
                value=f"{target_channel.bitrate // 1000}kbps",
                inline=True
            )
            
            # Add voice channel activity if available
            if target_channel.members:
                members_list = []
                for member in target_channel.members[:10]:  # Limit to 10 members
                    status = "🔇" if member.voice.self_mute or member.voice.mute else "🎤"
                    if member.voice.self_deaf or member.voice.deaf:
                        status = "🔇"
                    members_list.append(f"{status} {member.display_name}")
                
                if len(target_channel.members) > 10:
                    members_list.append(f"... and {len(target_channel.members) - 10} more")
                
                embed.add_field(
                    name="Connected Members",
                    value="\n".join(members_list) if members_list else "No other members",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
            # Set activity status
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name=f"music in {target_channel.name}"
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to join voice channel: {e}")
            embed = self.create_embed(
                title="❌ Connection Failed",
                description=f"Failed to join {target_channel.mention}: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="leave", description="Leave the current voice channel")
    async def leave(self, interaction: discord.Interaction):
        """Leave the current voice channel"""
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("❌ I'm not connected to any voice channel!", ephemeral=True)
        
        channel_name = interaction.guild.voice_client.channel.name
        await interaction.guild.voice_client.disconnect()
        
        embed = self.create_embed(
            title="👋 Left Voice Channel",
            description=f"Disconnected from **{channel_name}**",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        
        # Reset activity status
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="Advanced Music Bot | /play"
            )
        )
    
    # Playlist Management Commands
    
    @app_commands.command(name="create_playlist", description="Create a new playlist")
    @app_commands.describe(name="Playlist name", description="Playlist description (optional)", public="Make playlist public")
    async def create_playlist(self, interaction: discord.Interaction, name: str, description: str = None, public: bool = False):
        """Create a new playlist"""
        if not db:
            return await interaction.response.send_message("❌ Database not available!", ephemeral=True)
        
        try:
            playlist_id = await db.create_playlist(
                name=name,
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                description=description,
                is_public=public
            )
            
            embed = self.create_embed(
                title="✅ Playlist Created",
                description=f"Created playlist **{name}**",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Name", value=name, inline=True)
            embed.add_field(name="Visibility", value="Public" if public else "Private", inline=True)
            embed.add_field(name="ID", value=str(playlist_id), inline=True)
            
            if description:
                embed.add_field(name="Description", value=description, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to create playlist: {e}")
            await interaction.response.send_message("❌ Failed to create playlist!", ephemeral=True)
    
    @app_commands.command(name="load_playlist", description="Load and play a playlist")
    @app_commands.describe(playlist_id="Playlist ID or name")
    async def load_playlist(self, interaction: discord.Interaction, playlist_id: str):
        """Load and play a playlist"""
        if not db:
            return await interaction.response.send_message("❌ Database not available!", ephemeral=True)
        
        await interaction.response.defer()
        
        try:
            # Try to find playlist by ID or name
            playlist = None
            if playlist_id.isdigit():
                playlist = await db.get_playlist(int(playlist_id))
            else:
                playlists = await db.get_user_playlists(interaction.user.id)
                for p in playlists:
                    if p['name'].lower() == playlist_id.lower():
                        playlist = p
                        break
            
            if not playlist:
                return await interaction.followup.send("❌ Playlist not found!")
            
            # Check permissions
            if playlist['user_id'] != interaction.user.id and not playlist['is_public']:
                return await interaction.followup.send("❌ You don't have permission to load this playlist!")
            
            # Get playlist tracks
            tracks_data = await db.get_playlist_tracks(playlist['id'])
            if not tracks_data:
                return await interaction.followup.send("❌ This playlist is empty!")
            
            # Ensure voice connection
            if not interaction.user.voice:
                return await interaction.followup.send("❌ You need to be in a voice channel!")
            
            player = interaction.guild.voice_client
            if not player:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
            
            # Load tracks
            embed = self.create_embed(
                title="📋 Loading Playlist",
                description=f"Loading **{playlist['name']}** with {len(tracks_data)} tracks...",
                color=discord.Color.blue()
            )
            message = await interaction.followup.send(embed=embed)
            
            loaded_count = 0
            failed_count = 0
            
            for track_data in tracks_data:
                try:
                    # Search for the track
                    search_results = await wavelink.Playable.search(f"{track_data['title']} {track_data['artist']}")
                    if search_results:
                        track = search_results[0]
                        
                        if player.playing:
                            # Add to queue
                            music_cog = self.bot.get_cog('AdvancedMusic')
                            if music_cog:
                                queue = music_cog.queue_manager.get_queue(interaction.guild.id)
                                queue.add(track, interaction.user)
                                loaded_count += 1
                        else:
                            # Play first track
                            await player.play(track)
                            loaded_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to load track {track_data['title']}: {e}")
                    failed_count += 1
            
            # Update embed with results
            embed = self.create_embed(
                title="✅ Playlist Loaded",
                description=f"**{playlist['name']}**",
                color=discord.Color.green()
            )
            
            embed.add_field(name="✅ Loaded", value=str(loaded_count), inline=True)
            embed.add_field(name="❌ Failed", value=str(failed_count), inline=True)
            embed.add_field(name="📊 Total", value=str(len(tracks_data)), inline=True)
            
            if playlist['description']:
                embed.add_field(name="Description", value=playlist['description'], inline=False)
            
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to load playlist: {e}")
            await interaction.followup.send("❌ Failed to load playlist!")
    
    @app_commands.command(name="playlists", description="View your playlists")
    async def playlists(self, interaction: discord.Interaction):
        """View user's playlists"""
        if not db:
            return await interaction.response.send_message("❌ Database not available!", ephemeral=True)
        
        try:
            playlists = await db.get_user_playlists(interaction.user.id)
            if not playlists:
                return await interaction.response.send_message("📋 You don't have any playlists yet!\nUse `/create_playlist` to create one.")
            
            embed = self.create_embed(
                title="📋 Your Playlists",
                color=discord.Color.blue()
            )
            
            for playlist in playlists[:10]:  # Limit to 10 playlists
                track_count = await db.get_playlist_track_count(playlist['id'])
                visibility = "🌍 Public" if playlist['is_public'] else "🔒 Private"
                
                embed.add_field(
                    name=f"{playlist['name']} (ID: {playlist['id']})",
                    value=f"{visibility} • {track_count} tracks\n"
                         f"{playlist['description'] or 'No description'}",
                    inline=False
                )
            
            if len(playlists) > 10:
                embed.set_footer(text=f"Showing 10 of {len(playlists)} playlists")
            
            view = PlaylistManagementView(playlists, interaction.user)
            await interaction.response.send_message(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Failed to get playlists: {e}")
            await interaction.response.send_message("❌ Failed to retrieve playlists!", ephemeral=True)
    
    @app_commands.command(name="save_queue", description="Save current queue as a playlist")
    @app_commands.describe(name="Playlist name", description="Playlist description")
    async def save_queue(self, interaction: discord.Interaction, name: str, description: str = None):
        """Save current queue as a playlist"""
        if not db:
            return await interaction.response.send_message("❌ Database not available!", ephemeral=True)
        
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ No active music session!", ephemeral=True)
        
        music_cog = self.bot.get_cog('AdvancedMusic')
        if not music_cog:
            return await interaction.response.send_message("❌ Music system not available!", ephemeral=True)
        
        queue = music_cog.queue_manager.get_queue(interaction.guild.id)
        
        tracks_to_save = []
        if player.current:
            tracks_to_save.append(player.current)
        
        if queue:
            for track_info in queue._queue:
                tracks_to_save.append(track_info.track)
        
        if not tracks_to_save:
            return await interaction.response.send_message("❌ No tracks to save!", ephemeral=True)
        
        try:
            # Create playlist
            playlist_id = await db.create_playlist(
                name=name,
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                description=description,
                is_public=False
            )
            
            # Add tracks
            saved_count = 0
            for track in tracks_to_save:
                try:
                    await db.add_track_to_playlist(
                        playlist_id=playlist_id,
                        track_title=track.title,
                        track_artist=getattr(track, 'author', ''),
                        track_uri=track.uri,
                        track_duration=getattr(track, 'length', 0),
                        added_by=interaction.user.id
                    )
                    saved_count += 1
                except:
                    pass
            
            embed = self.create_embed(
                title="✅ Queue Saved as Playlist",
                description=f"Saved **{saved_count}** tracks to playlist **{name}**",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Playlist ID", value=str(playlist_id), inline=True)
            embed.add_field(name="Tracks Saved", value=str(saved_count), inline=True)
            
            if description:
                embed.add_field(name="Description", value=description, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to save queue: {e}")
            await interaction.response.send_message("❌ Failed to save queue as playlist!", ephemeral=True)


class PlaylistManagementView(discord.ui.View):
    """View for managing playlists"""
    
    def __init__(self, playlists: List[Dict], user: discord.Member, *, timeout=180):
        super().__init__(timeout=timeout)
        self.playlists = playlists
        self.user = user
        
        # Add select menu for playlist selection
        if playlists:
            options = []
            for playlist in playlists[:25]:  # Discord limit
                options.append(discord.SelectOption(
                    label=playlist['name'][:100],
                    description=f"ID: {playlist['id']} • {playlist['description'] or 'No description'}"[:100],
                    value=str(playlist['id'])
                ))
            
            self.add_item(PlaylistSelectDropdown(options, user))
    
    @discord.ui.button(emoji="🔄", label="Refresh", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ Only the playlist owner can refresh!", ephemeral=True)
        
        # Refresh playlist data
        cog = interaction.client.get_cog('VoiceAndPlaylist')
        if cog:
            await cog.playlists(interaction)


class PlaylistSelectDropdown(discord.ui.Select):
    def __init__(self, options, user):
        super().__init__(placeholder="Select a playlist to load...", options=options)
        self.user = user
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ Only the playlist owner can select playlists!", ephemeral=True)
        
        playlist_id = self.values[0]
        
        # Load the selected playlist
        cog = interaction.client.get_cog('VoiceAndPlaylist')
        if cog:
            await cog.load_playlist(interaction, playlist_id)


async def setup(bot):
    """Setup function for Voice and Playlist cog"""
    await bot.add_cog(VoiceAndPlaylist(bot))
