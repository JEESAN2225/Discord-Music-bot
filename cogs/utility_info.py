"""
Utility and Information Commands - Bot info, stats, help, invite, and more
"""

import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from typing import Optional, Dict, List
import datetime
import time
import psutil
import platform
import asyncio
from utils.emoji import *
from config.config import config
import logging

logger = logging.getLogger(__name__)

class UtilityInfo(commands.Cog):
    """Utility and information commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
    
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
    
    def get_uptime(self) -> str:
        """Get bot uptime as formatted string"""
        uptime_seconds = int(time.time() - self.start_time)
        return str(datetime.timedelta(seconds=uptime_seconds))
    
    def get_system_info(self) -> Dict:
        """Get system information"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            # Use current working directory for Windows compatibility
            disk = psutil.disk_usage('.')
            
            return {
                'cpu': f"{cpu_percent:.1f}%",
                'memory': f"{memory.percent:.1f}%",
                'disk': f"{disk.percent:.1f}%",
                'memory_used': f"{memory.used // (1024**3):.1f}GB",
                'memory_total': f"{memory.total // (1024**3):.1f}GB"
            }
        except:
            return {
                'cpu': 'N/A',
                'memory': 'N/A',
                'disk': 'N/A',
                'memory_used': 'N/A',
                'memory_total': 'N/A'
            }
    
    @app_commands.command(name="botinfo", description="Show detailed bot information")
    async def botinfo(self, interaction: discord.Interaction):
        """Show detailed bot information"""
        embed = self.create_embed(
            title="🤖 Bot Information",
            color=discord.Color.blue()
        )
        
        # Bot stats
        guild_count = len(self.bot.guilds)
        user_count = sum(guild.member_count for guild in self.bot.guilds)
        voice_connections = len([vc for vc in self.bot.voice_clients if vc.is_connected()])
        
        embed.add_field(
            name="📊 Statistics",
            value=f"**Servers:** {guild_count:,}\n"
                  f"**Users:** {user_count:,}\n"
                  f"**Voice Connections:** {voice_connections}",
            inline=True
        )
        
        # System info
        sys_info = self.get_system_info()
        embed.add_field(
            name="⚙️ System",
            value=f"**CPU:** {sys_info['cpu']}\n"
                  f"**Memory:** {sys_info['memory']} ({sys_info['memory_used']}/{sys_info['memory_total']})\n"
                  f"**Platform:** {platform.system()}",
            inline=True
        )
        
        # Bot info
        embed.add_field(
            name="🔧 Bot Details",
            value=f"**Uptime:** {self.get_uptime()}\n"
                  f"**Ping:** {round(self.bot.latency * 1000)}ms\n"
                  f"**Version:** discord.py {discord.__version__}",
            inline=True
        )
        
        # Features
        embed.add_field(
            name="✨ Features",
            value="🎵 **Music Streaming**\n"
                  "📋 **Playlist Management**\n"
                  "🎧 **DJ Controls**\n"
                  "🔍 **Lyrics Search**\n"
                  "📊 **Advanced Queue**\n"
                  "🎛️ **Audio Effects**\n"
                  "📻 **Autoplay Mode**\n"
                  "🗳️ **Vote Skip System**",
            inline=False
        )
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        view = BotInfoView()
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="stats", description="Show server and bot statistics")
    async def stats(self, interaction: discord.Interaction):
        """Show server and bot statistics"""
        embed = self.create_embed(
            title="📊 Statistics",
            color=discord.Color.green()
        )
        
        # Server stats
        guild = interaction.guild
        embed.add_field(
            name="🏠 Server Info",
            value=f"**Name:** {guild.name}\n"
                  f"**Members:** {guild.member_count:,}\n"
                  f"**Created:** <t:{int(guild.created_at.timestamp())}:R>",
            inline=True
        )
        
        # Voice stats
        voice_client = guild.voice_client
        if voice_client and voice_client.channel:
            embed.add_field(
                name="🔊 Voice Status",
                value=f"**Channel:** {voice_client.channel.name}\n"
                      f"**Connected:** {len(voice_client.channel.members)} members\n"
                      f"**Playing:** {'Yes' if voice_client.current else 'No'}",
                inline=True
            )
        else:
            embed.add_field(
                name="🔊 Voice Status",
                value="Not connected to voice",
                inline=True
            )
        
        # Queue stats
        music_cog = self.bot.get_cog('AdvancedMusic')
        if music_cog:
            queue = music_cog.queue_manager.get_queue(guild.id)
            if queue:
                queue_stats = queue.get_queue_stats()
                embed.add_field(
                    name="📋 Queue Stats",
                    value=f"**Tracks:** {queue_stats['track_count']}\n"
                          f"**Duration:** {str(datetime.timedelta(seconds=int(queue_stats['total_duration'] / 1000)))}\n"
                          f"**Repeat:** {queue.repeat_mode.title()}",
                    inline=True
                )
        
        # System resources
        sys_info = self.get_system_info()
        embed.add_field(
            name="⚡ Performance",
            value=f"**CPU Usage:** {sys_info['cpu']}\n"
                  f"**Memory:** {sys_info['memory']}\n"
                  f"**Latency:** {round(self.bot.latency * 1000)}ms",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="ping", description="Check bot latency and response time")
    async def ping(self, interaction: discord.Interaction):
        """Check bot latency and response time"""
        # Measure response time
        start = time.time()
        
        embed = self.create_embed(
            title="🏓 Pong!",
            color=discord.Color.yellow()
        )
        
        # API Latency
        api_latency = round(self.bot.latency * 1000)
        
        await interaction.response.send_message(embed=embed)
        
        # Response time
        end = time.time()
        response_time = round((end - start) * 1000)
        
        # Update embed with all latency info
        embed.add_field(name="📡 API Latency", value=f"{api_latency}ms", inline=True)
        embed.add_field(name="⚡ Response Time", value=f"{response_time}ms", inline=True)
        
        # Latency rating
        if api_latency < 100:
            rating = "🟢 Excellent"
        elif api_latency < 200:
            rating = "🟡 Good"
        elif api_latency < 500:
            rating = "🟠 Fair"
        else:
            rating = "🔴 Poor"
        
        embed.add_field(name="📊 Rating", value=rating, inline=True)
        
        await interaction.edit_original_response(embed=embed)
    
    @app_commands.command(name="invite", description="Get bot invite link and support information")
    async def invite(self, interaction: discord.Interaction):
        """Get bot invite link and support information"""
        embed = self.create_embed(
            title="🔗 Invite Bot",
            description="Thank you for using Advanced Music Bot!",
            color=discord.Color.blurple()
        )
        
        # Bot permissions needed
        permissions = discord.Permissions(
            connect=True,
            speak=True,
            use_voice_activation=True,
            send_messages=True,
            embed_links=True,
            read_message_history=True,
            manage_messages=True
        )
        
        invite_url = discord.utils.oauth_url(
            client_id=self.bot.user.id,
            permissions=permissions,
            scopes=['bot', 'applications.commands']
        )
        
        embed.add_field(
            name="📋 Required Permissions",
            value="• Connect to Voice Channels\n"
                  "• Speak in Voice Channels\n" 
                  "• Send Messages\n"
                  "• Embed Links\n"
                  "• Manage Messages\n"
                  "• Application Commands",
            inline=True
        )
        
        embed.add_field(
            name="✨ What you get:",
            value="🎵 High-quality music streaming\n"
                  "📋 Advanced playlist system\n"
                  "🎧 DJ controls and voting\n"
                  "🔍 Lyrics and track info\n"
                  "🎛️ Audio effects and filters\n"
                  "📊 Queue management\n"
                  "🤖 24/7 uptime",
            inline=True
        )
        
        view = InviteView(invite_url)
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="support", description="Get support and contact information")
    async def support(self, interaction: discord.Interaction):
        """Get support and contact information"""
        embed = self.create_embed(
            title="🆘 Support Center",
            description="Need help with the bot? Here are your options:",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="📖 Documentation",
            value="• Use `/help` for command list\n"
                  "• Check command descriptions\n"
                  "• Try `/botinfo` for bot stats",
            inline=False
        )
        
        embed.add_field(
            name="🐛 Common Issues",
            value="• **Bot not responding:** Check permissions\n"
                  "• **No audio:** Verify voice channel connection\n"
                  "• **Commands not working:** Try rejoining voice channel\n"
                  "• **Poor audio quality:** Check your internet connection",
            inline=False
        )
        
        embed.add_field(
            name="💡 Tips",
            value="• Use DJ roles for better control\n"
                  "• Try different audio sources\n"
                  "• Use autoplay for continuous music\n"
                  "• Save your favorite queues as playlists",
            inline=False
        )
        
        view = SupportView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="uptime", description="Show bot uptime and status")
    async def uptime(self, interaction: discord.Interaction):
        """Show bot uptime and status"""
        embed = self.create_embed(
            title="⏰ Bot Uptime",
            color=discord.Color.green()
        )
        
        uptime = self.get_uptime()
        embed.add_field(
            name="🕐 Current Uptime",
            value=f"**{uptime}**",
            inline=False
        )
        
        # Start time
        start_timestamp = int(self.start_time)
        embed.add_field(
            name="🚀 Started",
            value=f"<t:{start_timestamp}:F>\n<t:{start_timestamp}:R>",
            inline=True
        )
        
        # Status indicators
        embed.add_field(
            name="📊 Status",
            value=f"🟢 **Online**\n"
                  f"🔊 **Voice:** {len([vc for vc in self.bot.voice_clients if vc.is_connected()])} connections\n"
                  f"🏠 **Servers:** {len(self.bot.guilds)}",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)


class BotInfoView(discord.ui.View):
    """View for bot info with additional actions"""
    
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(emoji="🔗", label="Invite Bot", style=discord.ButtonStyle.secondary)
    async def invite_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get proper invite URL
        permissions = discord.Permissions(
            connect=True, speak=True, send_messages=True, 
            embed_links=True, manage_messages=True
        )
        invite_url = discord.utils.oauth_url(
            client_id=interaction.client.user.id,
            permissions=permissions,
            scopes=['bot', 'applications.commands']
        )
        await interaction.response.send_message(f"🔗 **Invite me to your server:**\n{invite_url}", ephemeral=True)
    
    @discord.ui.button(emoji="📊", label="System Stats", style=discord.ButtonStyle.secondary)
    async def system_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        sys_info = UtilityInfo.get_system_info(self)
        
        embed = discord.Embed(
            title="⚙️ System Information",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="💻 System",
            value=f"**OS:** {platform.system()} {platform.release()}\n"
                  f"**Architecture:** {platform.machine()}\n"
                  f"**Python:** {platform.python_version()}",
            inline=True
        )
        
        embed.add_field(
            name="📈 Resources",
            value=f"**CPU:** {sys_info['cpu']}\n"
                  f"**Memory:** {sys_info['memory_used']} / {sys_info['memory_total']}\n"
                  f"**Memory Usage:** {sys_info['memory']}",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class HelpView(discord.ui.View):
    """Interactive help system with categories"""
    
    def __init__(self, *, timeout=300):
        super().__init__(timeout=timeout)
        self.current_category = "music"
    
    def create_help_embed(self, category: str) -> discord.Embed:
        """Create help embed for specific category"""
        embed = discord.Embed(color=discord.Color.purple())
        
        if category == "music":
            embed.title = "🎵 Music Commands"
            embed.description = "Basic music playback and control commands"
            embed.add_field(
                name="Essential Commands",
                value="`/play` - Play a song or add to queue\n"
                      "`/search` - Search and select from results\n"
                      "`/pause` - Pause current track\n"
                      "`/resume` - Resume paused track\n"
                      "`/skip` - Skip current track\n"
                      "`/stop` - Stop and clear queue\n"
                      "`/nowplaying` - Show current track\n"
                      "`/queue` - Show current queue",
                inline=False
            )
            
        elif category == "advanced":
            embed.title = "⚡ Advanced Commands"
            embed.description = "Advanced music control and queue management"
            embed.add_field(
                name="Queue Control",
                value="`/seek <time>` - Seek to position\n"
                      "`/fastforward <seconds>` - Skip forward\n"
                      "`/rewind <seconds>` - Skip backward\n"
                      "`/replay` - Restart current track\n"
                      "`/remove <position>` - Remove track from queue\n"
                      "`/move <from> <to>` - Move track position\n"
                      "`/jump <position>` - Jump to track in queue\n"
                      "`/clear_range <start> <end>` - Clear track range",
                inline=False
            )
            
        elif category == "playlists":
            embed.title = "📋 Playlist Commands"
            embed.description = "Create and manage your playlists"
            embed.add_field(
                name="Playlist Management",
                value="`/create_playlist <name>` - Create new playlist\n"
                      "`/load_playlist <id/name>` - Load and play playlist\n"
                      "`/playlists` - View your playlists\n"
                      "`/save_queue <name>` - Save current queue as playlist",
                inline=False
            )
            
        elif category == "dj":
            embed.title = "🎧 DJ Commands"
            embed.description = "DJ and moderation features"
            embed.add_field(
                name="DJ Controls",
                value="`/voteskip` - Vote to skip current track\n"
                      "`/forceskip` - Force skip (DJ only)\n"
                      "`/set_dj_role <role>` - Set DJ role (Admin)\n"
                      "`/ban_track <url>` - Ban a track (DJ)\n"
                      "`/queue_limit <limit>` - Set user queue limits (DJ)\n"
                      "`/clear_user_queue <user>` - Clear user's tracks (DJ)",
                inline=False
            )
            
        elif category == "voice":
            embed.title = "🔊 Voice Commands"
            embed.description = "Voice connection and audio controls"
            embed.add_field(
                name="Voice & Audio",
                value="`/join [channel]` - Join voice channel\n"
                      "`/leave` - Leave voice channel\n"
                      "`/volume <level>` - Set volume (0-200)\n"
                      "`/autoplay` - Toggle autoplay mode\n"
                      "`/lyrics [query]` - Get lyrics for track",
                inline=False
            )
            
        elif category == "info":
            embed.title = "ℹ️ Information Commands"
            embed.description = "Bot information and utility commands"
            embed.add_field(
                name="Utility",
                value="`/botinfo` - Show bot information\n"
                      "`/stats` - Show server statistics\n"
                      "`/ping` - Check bot latency\n"
                      "`/uptime` - Show bot uptime\n"
                      "`/invite` - Get bot invite link\n"
                      "`/support` - Get help and support",
                inline=False
            )
        
        return embed
    
    @discord.ui.select(
        placeholder="Choose a command category...",
        options=[
            discord.SelectOption(label="🎵 Music Commands", value="music", description="Basic playback controls"),
            discord.SelectOption(label="⚡ Advanced Commands", value="advanced", description="Queue management and seeking"),
            discord.SelectOption(label="📋 Playlist Commands", value="playlists", description="Playlist creation and management"),
            discord.SelectOption(label="🎧 DJ Commands", value="dj", description="DJ controls and moderation"),
            discord.SelectOption(label="🔊 Voice Commands", value="voice", description="Voice and audio controls"),
            discord.SelectOption(label="ℹ️ Info Commands", value="info", description="Bot information and utilities"),
        ]
    )
    async def help_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.current_category = select.values[0]
        embed = self.create_help_embed(self.current_category)
        await interaction.response.edit_message(embed=embed, view=self)


class InviteView(discord.ui.View):
    """View for invite command with links"""
    
    def __init__(self, invite_url: str, *, timeout=180):
        super().__init__(timeout=timeout)
        # Create a proper link button
        button = discord.ui.Button(label="🔗 Invite Bot", style=discord.ButtonStyle.link, url=invite_url)
        self.add_item(button)


class SupportView(discord.ui.View):
    """View for support command with help options"""
    
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(emoji="❓", label="Show Commands", style=discord.ButtonStyle.secondary)
    async def show_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('UtilityInfo')
        if cog:
            await cog.help_command(interaction)
    
    @discord.ui.button(emoji="🏓", label="Test Connection", style=discord.ButtonStyle.secondary)
    async def test_connection(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('UtilityInfo')
        if cog:
            await cog.ping(interaction)


async def setup(bot):
    """Setup function for Utility Info cog"""
    await bot.add_cog(UtilityInfo(bot))
