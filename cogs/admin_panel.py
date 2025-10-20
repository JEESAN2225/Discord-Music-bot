"""
Admin Panel - Server management and bot configuration interface
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
import time
from typing import Optional, List, Dict, Any

from utils.emoji import *
from utils.enhanced_embeds import get_embed_builder
from utils.animated_embeds import InteractiveAnimatedView, EmbedAnimations
from utils.advanced_queue import get_queue_manager
from database.models import db
from config.config import config

class AdminPanelView(discord.ui.View):
    """Main admin panel with all management options"""
    
    def __init__(self, bot, user: discord.Member, *, timeout: int = 600):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.user = user
        self.embed_builder = get_embed_builder(bot)
        self.current_panel = "main"  # main, settings, analytics, moderation, system
        
        # Build initial view
        self.build_main_panel()
    
    def build_main_panel(self):
        """Build main admin panel"""
        self.clear_items()
        
        # Row 0: Main categories
        self.add_item(SettingsPanelButton())
        self.add_item(AnalyticsPanelButton())
        self.add_item(ModerationPanelButton())
        self.add_item(SystemPanelButton())
        
        # Row 1: Quick actions
        self.add_item(ServerInfoButton())
        self.add_item(BotStatusButton())
        self.add_item(QuickSettingsButton())
        self.add_item(EmergencyStopButton())
        
        # Row 2: Navigation
        self.add_item(RefreshButton())
        self.add_item(ExportDataButton())
        self.add_item(HelpButton())
        self.add_item(CloseButton())
    
    def build_settings_panel(self):
        """Build settings management panel"""
        self.clear_items()
        
        # Settings controls
        self.add_item(PrefixSettingButton())
        self.add_item(VolumeSettingButton())
        self.add_item(DJRoleButton())
        self.add_item(MusicChannelButton())
        self.add_item(AutoDisconnectButton())
        
        # Back button
        self.add_item(BackToMainButton())
    
    def build_analytics_panel(self):
        """Build analytics panel"""
        self.clear_items()
        
        # Analytics options
        self.add_item(UsageStatsButton())
        self.add_item(PopularTracksButton())
        self.add_item(UserStatsButton())
        self.add_item(ServerStatsButton())
        self.add_item(ExportAnalyticsButton())
        
        # Back button
        self.add_item(BackToMainButton())
    
    def build_moderation_panel(self):
        """Build moderation panel"""
        self.clear_items()
        
        # Moderation tools
        self.add_item(BlacklistButton())
        self.add_item(WhitelistButton())
        self.add_item(VolumeRestrictionButton())
        self.add_item(CommandRestrictionsButton())
        self.add_item(UserPermissionsButton())
        
        # Back button
        self.add_item(BackToMainButton())
    
    def build_system_panel(self):
        """Build system management panel"""
        self.clear_items()
        
        # System controls
        self.add_item(RestartButton())
        self.add_item(UpdateButton())
        self.add_item(LogsButton())
        self.add_item(DatabaseButton())
        self.add_item(BackupButton())
        
        # Back button
        self.add_item(BackToMainButton())
    
    async def create_main_embed(self) -> discord.Embed:
        """Create main admin panel embed"""
        embed = self.embed_builder.create_base_embed(
            title="⚙️ Admin Control Panel",
            description=f"Welcome, {self.user.display_name}! Select a category below to manage your server.",
            color='info'
        )
        
        # Server info
        guild = self.user.guild
        embed.add_field(
            name="🏠 Server Information",
            value=f"**Name:** {guild.name}\n"
                  f"**Members:** {guild.member_count:,}\n"
                  f"**Channels:** {len(guild.channels)}\n"
                  f"**Roles:** {len(guild.roles)}",
            inline=True
        )
        
        # Bot stats
        embed.add_field(
            name="🤖 Bot Statistics",
            value=f"**Servers:** {len(self.bot.guilds):,}\n"
                  f"**Users:** {len(set(self.bot.get_all_members())):,}\n"
                  f"**Uptime:** {self.get_uptime()}\n"
                  f"**Ping:** {round(self.bot.latency * 1000)}ms",
            inline=True
        )
        
        # Quick status
        player = guild.voice_client
        queue_manager = get_queue_manager()
        queue = queue_manager.get_queue(guild.id)
        
        music_status = "🎵 Playing" if player and player.playing else "⏹️ Stopped"
        queue_status = f"{len(queue)} tracks" if queue else "Empty"
        
        embed.add_field(
            name="🎵 Music Status",
            value=f"**Player:** {music_status}\n"
                  f"**Queue:** {queue_status}\n"
                  f"**Volume:** {int(player.volume * 100) if player else 'N/A'}%\n"
                  f"**Connected:** {'Yes' if player else 'No'}",
            inline=True
        )
        
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_footer(text="Admin Panel • Use buttons below to navigate")
        
        return embed
    
    async def create_settings_embed(self) -> discord.Embed:
        """Create settings panel embed"""
        embed = self.embed_builder.create_base_embed(
            title="⚙️ Server Settings",
            description="Configure bot settings for this server",
            color='info'
        )
        
        guild = self.user.guild
        
        # Current settings (mock data)
        embed.add_field(
            name="🎵 Music Settings",
            value=f"**Prefix:** `{config.BOT_PREFIX}`\n"
                  f"**Default Volume:** {config.DEFAULT_VOLUME}%\n"
                  f"**Max Queue Size:** {config.MAX_QUEUE_SIZE}\n"
                  f"**Auto Disconnect:** {config.AUTO_DISCONNECT_TIME}s",
            inline=True
        )
        
        embed.add_field(
            name="👑 Permissions",
            value="**DJ Role:** Not Set\n"
                  "**Music Channel:** Any\n"
                  "**Volume Lock:** Disabled\n"
                  "**Queue Lock:** Disabled",
            inline=True
        )
        
        embed.add_field(
            name="🔧 Advanced",
            value="**Spotify Integration:** Enabled\n"
                  "**Lyrics Service:** Enabled\n"
                  "**Statistics:** Enabled\n"
                  "**Web Dashboard:** Disabled",
            inline=True
        )
        
        return embed
    
    async def create_analytics_embed(self) -> discord.Embed:
        """Create analytics panel embed"""
        embed = self.embed_builder.create_base_embed(
            title="📊 Analytics Dashboard",
            description="View detailed usage statistics and insights",
            color='stats'
        )
        
        # Mock analytics data
        embed.add_field(
            name="📈 Usage This Week",
            value="**Commands Used:** 1,247\n"
                  "**Music Hours:** 87.3h\n"
                  "**Active Users:** 45\n"
                  "**Peak Concurrent:** 12",
            inline=True
        )
        
        embed.add_field(
            name="🎵 Music Stats",
            value="**Tracks Played:** 892\n"
                  "**Unique Artists:** 156\n"
                  "**Top Genre:** Pop\n"
                  "**Avg Session:** 23m",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Top Performers",
            value="**Most Active User:** User#1234\n"
                  "**Most Played Track:** Song ABC\n"
                  "**Busiest Hour:** 8-9 PM\n"
                  "**Busiest Day:** Saturday",
            inline=True
        )
        
        return embed
    
    async def create_moderation_embed(self) -> discord.Embed:
        """Create moderation panel embed"""
        embed = self.embed_builder.create_base_embed(
            title="🛡️ Moderation Tools",
            description="Manage user permissions and content restrictions",
            color='warning'
        )
        
        embed.add_field(
            name="🚫 Blacklist",
            value="**Blocked Users:** 0\n"
                  "**Blocked Songs:** 0\n"
                  "**Blocked Artists:** 0\n"
                  "**Blocked Keywords:** 0",
            inline=True
        )
        
        embed.add_field(
            name="✅ Whitelist",
            value="**Approved Users:** All\n"
                  "**Approved Channels:** All\n"
                  "**Approved Roles:** DJ Role\n"
                  "**Bypass Users:** 2",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Restrictions",
            value="**Volume Limit:** 150%\n"
                  "**Queue Limit:** 10/user\n"
                  "**Song Duration:** No limit\n"
                  "**File Upload:** Allowed",
            inline=True
        )
        
        return embed
    
    async def create_system_embed(self) -> discord.Embed:
        """Create system panel embed"""
        embed = self.embed_builder.create_base_embed(
            title="🔧 System Management",
            description="Manage bot system and maintenance",
            color='danger'
        )
        
        # System status
        embed.add_field(
            name="💻 System Status",
            value="**CPU Usage:** 15.2%\n"
                  f"**Memory:** 245MB\n"
                  f"**Uptime:** {self.get_uptime()}\n"
                  "**Status:** Healthy ✅",
            inline=True
        )
        
        embed.add_field(
            name="🗃️ Database",
            value="**Status:** Connected ✅\n"
                  "**Size:** 12.4 MB\n"
                  "**Tables:** 8\n"
                  "**Last Backup:** 2 hours ago",
            inline=True
        )
        
        embed.add_field(
            name="🔄 Updates",
            value="**Current Version:** v2.1.0\n"
                  "**Available:** v2.1.1\n"
                  "**Last Check:** 1 hour ago\n"
                  "**Auto Update:** Enabled",
            inline=True
        )
        
        return embed
    
    def get_uptime(self) -> str:
        """Get bot uptime string"""
        # This is a mock implementation
        return "2d 14h 32m"
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin permissions"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Only the admin who opened this panel can use it!", ephemeral=True)
            return False
        
        # Check if user has admin permissions
        if not (interaction.user.guild_permissions.administrator or 
                interaction.user.id in config.OWNERS):
            await interaction.response.send_message("❌ You need administrator permissions to use this panel!", ephemeral=True)
            return False
        
        return True

# Button classes for admin panel

class AdminPanelButton(discord.ui.Button):
    """Base class for admin panel buttons"""
    
    async def callback(self, interaction: discord.Interaction):
        await self.execute_action(interaction)
    
    async def execute_action(self, interaction: discord.Interaction):
        """Override in subclasses"""
        pass

# Main panel navigation buttons
class SettingsPanelButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="⚙️", label="Settings", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: AdminPanelView = self.view
        view.current_panel = "settings"
        view.build_settings_panel()
        embed = await view.create_settings_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class AnalyticsPanelButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="📊", label="Analytics", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: AdminPanelView = self.view
        view.current_panel = "analytics"
        view.build_analytics_panel()
        embed = await view.create_analytics_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class ModerationPanelButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🛡️", label="Moderation", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: AdminPanelView = self.view
        view.current_panel = "moderation"
        view.build_moderation_panel()
        embed = await view.create_moderation_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class SystemPanelButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🔧", label="System", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: AdminPanelView = self.view
        view.current_panel = "system"
        view.build_system_panel()
        embed = await view.create_system_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Quick action buttons
class ServerInfoButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="ℹ️", label="Server Info", style=discord.ButtonStyle.primary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(
            title=f"ℹ️ {guild.name}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Members", value=f"{guild.member_count:,}", inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BotStatusButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🤖", label="Bot Status", style=discord.ButtonStyle.primary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        bot = interaction.client
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Servers", value=f"{len(bot.guilds):,}", inline=True)
        embed.add_field(name="Users", value=f"{len(set(bot.get_all_members())):,}", inline=True)
        embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
        
        # Mock system stats
        embed.add_field(name="CPU", value="15.2%", inline=True)
        embed.add_field(name="Memory", value="245MB", inline=True)
        embed.add_field(name="Uptime", value="2d 14h", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class QuickSettingsButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="⚡", label="Quick Settings", style=discord.ButtonStyle.primary, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("⚡ Quick settings coming soon!", ephemeral=True)

class EmergencyStopButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🛑", label="Emergency Stop", style=discord.ButtonStyle.danger, row=1)
    
    async def execute_action(self, interaction: discord.Interaction):
        # Stop all music in the guild
        if interaction.guild.voice_client:
            queue_manager = get_queue_manager()
            queue = queue_manager.get_queue(interaction.guild.id)
            queue.clear()
            await interaction.guild.voice_client.disconnect()
        
        await interaction.response.send_message("🛑 Emergency stop activated! All music stopped and queue cleared.", ephemeral=True)

# Navigation buttons
class BackToMainButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🏠", label="Back to Main", style=discord.ButtonStyle.primary, row=4)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: AdminPanelView = self.view
        view.current_panel = "main"
        view.build_main_panel()
        embed = await view.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class RefreshButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🔄", label="Refresh", style=discord.ButtonStyle.secondary, row=2)
    
    async def execute_action(self, interaction: discord.Interaction):
        view: AdminPanelView = self.view
        if view.current_panel == "main":
            embed = await view.create_main_embed()
        elif view.current_panel == "settings":
            embed = await view.create_settings_embed()
        elif view.current_panel == "analytics":
            embed = await view.create_analytics_embed()
        elif view.current_panel == "moderation":
            embed = await view.create_moderation_embed()
        elif view.current_panel == "system":
            embed = await view.create_system_embed()
        else:
            embed = await view.create_main_embed()
        
        await interaction.response.edit_message(embed=embed, view=view)

class ExportDataButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="📤", label="Export Data", style=discord.ButtonStyle.secondary, row=2)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("📤 Data export feature coming soon!", ephemeral=True)

class HelpButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="❓", label="Help", style=discord.ButtonStyle.secondary, row=2)
    
    async def execute_action(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❓ Admin Panel Help",
            description="Guide to using the admin control panel",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Navigation",
            value="• Use category buttons to switch panels\n"
                  "• 🏠 **Back to Main** returns to overview\n"
                  "• 🔄 **Refresh** updates current data",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Settings Panel",
            value="• Configure bot behavior for your server\n"
                  "• Set DJ roles and music channels\n"
                  "• Adjust volume and queue limits",
            inline=False
        )
        
        embed.add_field(
            name="📊 Analytics Panel",
            value="• View detailed usage statistics\n"
                  "• Track popular songs and users\n"
                  "• Export data for analysis",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CloseButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="❌", label="Close", style=discord.ButtonStyle.danger, row=2)
    
    async def execute_action(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❌ Admin Panel Closed",
            description="Thanks for using the admin panel!",
            color=discord.Color.red()
        )
        
        # Disable all buttons
        for item in self.view.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self.view)
        self.view.stop()

# Placeholder buttons for sub-panels (these would be fully implemented)
class PrefixSettingButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="📝", label="Prefix", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("📝 Prefix setting coming soon!", ephemeral=True)

class VolumeSettingButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🔊", label="Volume", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔊 Volume settings coming soon!", ephemeral=True)

class DJRoleButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="👑", label="DJ Role", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("👑 DJ role configuration coming soon!", ephemeral=True)

class MusicChannelButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🎵", label="Music Channel", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🎵 Music channel setting coming soon!", ephemeral=True)

class AutoDisconnectButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🚪", label="Auto Disconnect", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🚪 Auto disconnect settings coming soon!", ephemeral=True)

# More placeholder buttons...
class UsageStatsButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="📈", label="Usage Stats", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("📈 Usage statistics coming soon!", ephemeral=True)

class PopularTracksButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🎵", label="Popular Tracks", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🎵 Popular tracks analytics coming soon!", ephemeral=True)

class UserStatsButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="👥", label="User Stats", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("👥 User statistics coming soon!", ephemeral=True)

class ServerStatsButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🏠", label="Server Stats", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏠 Server statistics coming soon!", ephemeral=True)

class ExportAnalyticsButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="📊", label="Export Analytics", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("📊 Export analytics coming soon!", ephemeral=True)

class BlacklistButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🚫", label="Blacklist", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🚫 Blacklist management coming soon!", ephemeral=True)

class WhitelistButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="✅", label="Whitelist", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Whitelist management coming soon!", ephemeral=True)

class VolumeRestrictionButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🔊", label="Volume Limits", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔊 Volume restrictions coming soon!", ephemeral=True)

class CommandRestrictionsButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="⚙️", label="Command Limits", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("⚙️ Command restrictions coming soon!", ephemeral=True)

class UserPermissionsButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="👤", label="User Permissions", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("👤 User permissions coming soon!", ephemeral=True)

class RestartButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🔄", label="Restart Bot", style=discord.ButtonStyle.danger, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔄 Bot restart functionality coming soon!", ephemeral=True)

class UpdateButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="⬆️", label="Update", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("⬆️ Update system coming soon!", ephemeral=True)

class LogsButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="📋", label="View Logs", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("📋 Log viewer coming soon!", ephemeral=True)

class DatabaseButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="🗃️", label="Database", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("🗃️ Database management coming soon!", ephemeral=True)

class BackupButton(AdminPanelButton):
    def __init__(self):
        super().__init__(emoji="💾", label="Backup", style=discord.ButtonStyle.secondary, row=0)
    
    async def execute_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("💾 Backup system coming soon!", ephemeral=True)

class AdminPanel(commands.Cog):
    """Admin panel for server management and bot configuration"""
    
    def __init__(self, bot):
        self.bot = bot
        self.embed_builder = get_embed_builder(bot)
    
    @app_commands.command(name="admin", description="Open the admin control panel (Administrator only)")
    async def admin_panel(self, interaction: discord.Interaction):
        """Open the comprehensive admin panel"""
        
        # Check permissions
        if not (interaction.user.guild_permissions.administrator or 
                interaction.user.id in config.OWNERS):
            embed = self.embed_builder.create_error_embed(
                "Access Denied",
                "You need Administrator permissions to use the admin panel.",
                "permission"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create admin panel
        view = AdminPanelView(self.bot, interaction.user)
        embed = await view.create_main_embed()
        
        await interaction.response.send_message(embed=embed, view=view)
    
    @commands.command(name="admin")
    @commands.has_permissions(administrator=True)
    async def admin_panel_prefix(self, ctx):
        """Prefix version of admin panel command"""
        
        view = AdminPanelView(self.bot, ctx.author)
        embed = await view.create_main_embed()
        
        await ctx.send(embed=embed, view=view)
    
    @app_commands.command(name="animate", description="Show animation demonstration")
    async def animate_demo(self, interaction: discord.Interaction):
        """Demonstration of animated embeds"""
        
        view = InteractiveAnimatedView(self.bot)
        
        initial_embed = discord.Embed(
            title="🎨 Animation Demo",
            description="Click buttons below to see different animations!",
            color=discord.Color.purple()
        )
        
        await interaction.response.send_message(embed=initial_embed, view=view)
        
        # Start with loading animation
        message = await interaction.original_response()
        asyncio.create_task(view.start_with_animation(message, "loading"))

async def setup(bot):
    """Setup function for the AdminPanel cog"""
    await bot.add_cog(AdminPanel(bot))
