"""
Advanced Help System - Interactive categorized help with rich embeds and buttons
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, List, Optional
import datetime
from utils.emoji import *
from utils.enhanced_embeds import get_embed_builder
from config.config import config

class HelpCategory:
    """Represents a help category with commands"""
    
    def __init__(self, name: str, emoji: str, description: str, commands: List[Dict]):
        self.name = name
        self.emoji = emoji
        self.description = description
        self.commands = commands

class HelpView(discord.ui.View):
    """Interactive help view with category buttons"""
    
    def __init__(self, bot, user: discord.Member, *, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.user = user
        self.embed_builder = get_embed_builder(bot)
        
        # Define help categories
        self.categories = {
            "music": HelpCategory(
                name="Music Commands",
                emoji="🎵",
                description="Play, pause, skip and control music",
                commands=[
                    {"name": "/play", "desc": "Play a song from YouTube, Spotify, or URL", "usage": "/play <song name or URL>"},
                    {"name": "/pause", "desc": "Pause the current song", "usage": "/pause"},
                    {"name": "/resume", "desc": "Resume the paused song", "usage": "/resume"},
                    {"name": "/skip", "desc": "Skip the current song", "usage": "/skip"},
                    {"name": "/stop", "desc": "Stop music and clear queue", "usage": "/stop"},
                    {"name": "/queue", "desc": "Show current music queue", "usage": "/queue"},
                    {"name": "/nowplaying", "desc": "Show currently playing song", "usage": "/nowplaying"},
                    {"name": "/shuffle", "desc": "Shuffle the music queue", "usage": "/shuffle"},
                    {"name": "/loop", "desc": "Toggle loop mode (off/track/queue)", "usage": "/loop [mode]"},
                ]
            ),
            "volume": HelpCategory(
                name="Volume & Filters",
                emoji="🔊",
                description="Adjust volume and apply audio effects",
                commands=[
                    {"name": "/volume", "desc": "Set or show volume controls", "usage": "/volume [0-150]"},
                    {"name": "/bassboost", "desc": "Toggle bass boost filter", "usage": "/bassboost"},
                    {"name": "/nightcore", "desc": "Toggle nightcore filter", "usage": "/nightcore"},
                    {"name": "/8d", "desc": "Toggle 8D audio effect", "usage": "/8d"},
                    {"name": "/filters", "desc": "Show all available audio filters", "usage": "/filters"},
                ]
            ),
            "playlist": HelpCategory(
                name="Playlists",
                emoji="📋",
                description="Create and manage your playlists",
                commands=[
                    {"name": "/playlist create", "desc": "Create a new playlist", "usage": "/playlist create <name>"},
                    {"name": "/playlist add", "desc": "Add current song to playlist", "usage": "/playlist add <playlist>"},
                    {"name": "/playlist play", "desc": "Play songs from a playlist", "usage": "/playlist play <name>"},
                    {"name": "/playlist list", "desc": "Show your playlists", "usage": "/playlist list"},
                    {"name": "/playlist delete", "desc": "Delete a playlist", "usage": "/playlist delete <name>"},
                ]
            ),
            "radio": HelpCategory(
                name="Radio & Discovery",
                emoji="📻",
                description="Radio stations and music discovery",
                commands=[
                    {"name": "/radio", "desc": "Browse and play radio stations", "usage": "/radio [genre]"},
                    {"name": "/autoplay", "desc": "Enable automatic song suggestions", "usage": "/autoplay"},
                    {"name": "/discover", "desc": "Discover new music based on your history", "usage": "/discover"},
                    {"name": "/trending", "desc": "Show trending music", "usage": "/trending"},
                ]
            ),
            "lyrics": HelpCategory(
                name="Lyrics & Info",
                emoji="📝",
                description="Get song lyrics and information",
                commands=[
                    {"name": "/lyrics", "desc": "Get lyrics for current or specified song", "usage": "/lyrics [song name]"},
                    {"name": "/songinfo", "desc": "Get detailed information about a song", "usage": "/songinfo"},
                    {"name": "/artist", "desc": "Get information about an artist", "usage": "/artist <name>"},
                    {"name": "/search", "desc": "Search for songs without playing", "usage": "/search <query>"},
                ]
            ),
            "stats": HelpCategory(
                name="Statistics",
                emoji="📊",
                description="View your listening statistics",
                commands=[
                    {"name": "/music-stats", "desc": "View your listening statistics", "usage": "/music-stats [@user]"},
                    {"name": "/leaderboard", "desc": "View server music leaderboard", "usage": "/leaderboard"},
                    {"name": "/history", "desc": "View your listening history", "usage": "/history"},
                    {"name": "/popular", "desc": "View most popular songs in server", "usage": "/popular"},
                ]
            ),
            "admin": HelpCategory(
                name="Admin & Settings",
                emoji="⚙️",
                description="Server administration and bot settings",
                commands=[
                    {"name": "/settings", "desc": "Configure bot settings for server", "usage": "/settings"},
                    {"name": "/prefix", "desc": "Change bot prefix", "usage": "/prefix <new prefix>"},
                    {"name": "/djrole", "desc": "Set DJ role for music controls", "usage": "/djrole <@role>"},
                    {"name": "/musicchannel", "desc": "Set dedicated music channel", "usage": "/musicchannel [#channel]"},
                    {"name": "/blacklist", "desc": "Manage song/user blacklist", "usage": "/blacklist <add/remove> <item>"},
                ]
            )
        }
        
        # Add category buttons
        self.create_category_buttons()
        
        # Set initial category
        self.current_category = "music"
    
    def create_category_buttons(self):
        """Create buttons for each category"""
        row = 0
        col = 0
        
        for key, category in self.categories.items():
            if col >= 4:  # Max 4 buttons per row
                row += 1
                col = 0
            
            button = discord.ui.Button(
                emoji=category.emoji,
                label=category.name.split()[0],  # First word only
                style=discord.ButtonStyle.secondary,
                custom_id=f"help_{key}",
                row=row
            )
            button.callback = self.create_category_callback(key)
            self.add_item(button)
            col += 1
        
        # Add special buttons
        if row < 4:  # Make sure we don't exceed row limit
            row += 1
        
        # Home button
        home_button = discord.ui.Button(
            emoji="🏠",
            label="Overview",
            style=discord.ButtonStyle.primary,
            custom_id="help_home",
            row=row
        )
        home_button.callback = self.show_home
        self.add_item(home_button)
        
        # Close button
        close_button = discord.ui.Button(
            emoji="❌",
            label="Close",
            style=discord.ButtonStyle.danger,
            custom_id="help_close",
            row=row
        )
        close_button.callback = self.close_help
        self.add_item(close_button)
    
    def create_category_callback(self, category_key: str):
        """Create callback function for category button"""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("❌ Only the command user can interact with this help menu!", ephemeral=True)
                return
            
            self.current_category = category_key
            embed = self.create_category_embed(category_key)
            
            # Update button styles
            for item in self.children:
                if hasattr(item, 'custom_id') and item.custom_id == f"help_{category_key}":
                    item.style = discord.ButtonStyle.success
                elif hasattr(item, 'custom_id') and item.custom_id.startswith("help_") and item.custom_id != "help_home" and item.custom_id != "help_close":
                    item.style = discord.ButtonStyle.secondary
            
            await interaction.response.edit_message(embed=embed, view=self)
        
        return callback
    
    async def show_home(self, interaction: discord.Interaction):
        """Show help overview"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Only the command user can interact with this help menu!", ephemeral=True)
            return
        
        embed = self.create_home_embed()
        
        # Reset button styles
        for item in self.children:
            if hasattr(item, 'custom_id') and item.custom_id.startswith("help_") and item.custom_id not in ["help_home", "help_close"]:
                item.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def close_help(self, interaction: discord.Interaction):
        """Close help menu"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Only the command user can interact with this help menu!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Help Menu Closed",
            description="Thanks for using the help system!",
            color=discord.Color.red()
        )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
    
    def create_home_embed(self) -> discord.Embed:
        """Create the main help overview embed"""
        embed = self.embed_builder.create_base_embed(
            title="🎵 Advanced Music Bot - Help Center",
            description="Welcome to the comprehensive help system! Click the buttons below to explore different categories.",
            color='info'
        )
        
        # Bot statistics
        embed.add_field(
            name="📊 Bot Statistics",
            value=f"🏠 Servers: `{len(self.bot.guilds)}`\n"
                  f"👥 Users: `{len(set(self.bot.get_all_members()))}`\n"
                  f"🎵 Commands: `{len(self.bot.commands) + len([cmd for cog in self.bot.cogs.values() for cmd in cog.walk_app_commands()])}`",
            inline=True
        )
        
        # Quick links
        embed.add_field(
            name="🔗 Quick Links",
            value="📝 [Documentation](https://discord.com)\n"
                  "🐛 [Report Bug](https://discord.com)\n"
                  "💡 [Suggestions](https://discord.com)",
            inline=True
        )
        
        # Categories overview
        categories_text = ""
        for key, category in self.categories.items():
            categories_text += f"{category.emoji} **{category.name}**\n{category.description}\n\n"
        
        embed.add_field(
            name="📚 Command Categories",
            value=categories_text[:1024],  # Discord limit
            inline=False
        )
        
        # Tips
        embed.add_field(
            name="💡 Pro Tips",
            value="• Use `/` for slash commands (recommended)\n"
                  f"• Use `{config.BOT_PREFIX}` for prefix commands\n"
                  "• Add the bot to your playlist for 24/7 music\n"
                  "• Use `/settings` to customize the bot per server",
            inline=False
        )
        
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_footer(text="Select a category above to view specific commands", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        return embed
    
    def create_category_embed(self, category_key: str) -> discord.Embed:
        """Create embed for specific category"""
        category = self.categories[category_key]
        
        embed = self.embed_builder.create_base_embed(
            title=f"{category.emoji} {category.name}",
            description=category.description,
            color='info'
        )
        
        # Add commands
        for i, cmd in enumerate(category.commands):
            embed.add_field(
                name=f"{i+1}. {cmd['name']}",
                value=f"**Usage:** `{cmd['usage']}`\n{cmd['desc']}",
                inline=False
            )
        
        embed.set_footer(text=f"Showing {len(category.commands)} commands in this category")
        
        return embed
    
    async def on_timeout(self):
        """Handle view timeout"""
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Don't try to edit if we don't have the original message
        try:
            # This will only work if we have access to the message
            pass
        except:
            pass

class HelpSystem(commands.Cog):
    """Advanced help system with interactive categories"""
    
    def __init__(self, bot):
        self.bot = bot
        self.embed_builder = get_embed_builder(bot)
    
    @app_commands.command(name="help", description="Show interactive help menu with all bot commands")
    @app_commands.describe(command="Get help for a specific command")
    async def help_slash(self, interaction: discord.Interaction, command: Optional[str] = None):
        """Interactive help command with categories"""
        
        if command:
            # Show help for specific command
            embed = await self.get_command_help(command)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Show interactive help menu
            view = HelpView(self.bot, interaction.user)
            embed = view.create_home_embed()
            await interaction.response.send_message(embed=embed, view=view)
    
    @commands.command(name="help")
    async def help_prefix(self, ctx, *, command: Optional[str] = None):
        """Prefix version of help command"""
        
        if command:
            # Show help for specific command
            embed = await self.get_command_help(command)
            await ctx.send(embed=embed)
        else:
            # Show interactive help menu
            view = HelpView(self.bot, ctx.author)
            embed = view.create_home_embed()
            await ctx.send(embed=embed, view=view)
    
    async def get_command_help(self, command_name: str) -> discord.Embed:
        """Get detailed help for a specific command"""
        
        # Search for command
        cmd = self.bot.get_command(command_name)
        app_cmd = None
        
        # Search in slash commands
        for cog in self.bot.cogs.values():
            for app_command in cog.walk_app_commands():
                if app_command.name == command_name:
                    app_cmd = app_command
                    break
            if app_cmd:
                break
        
        if not cmd and not app_cmd:
            embed = self.embed_builder.create_error_embed(
                "Command Not Found",
                f"No command named `{command_name}` was found.",
                "not_found"
            )
            return embed
        
        # Create detailed embed
        target_cmd = app_cmd or cmd
        embed = self.embed_builder.create_base_embed(
            title=f"📖 Command: {target_cmd.name}",
            description=target_cmd.description or "No description provided",
            color='info'
        )
        
        if hasattr(target_cmd, 'usage'):
            embed.add_field(name="📝 Usage", value=f"`{target_cmd.usage}`", inline=False)
        
        if hasattr(target_cmd, 'aliases') and target_cmd.aliases:
            embed.add_field(name="🔗 Aliases", value=", ".join(f"`{alias}`" for alias in target_cmd.aliases), inline=True)
        
        if hasattr(target_cmd, 'parameters') and target_cmd.parameters:
            params = []
            for param in target_cmd.parameters.values():
                if param.description:
                    params.append(f"**{param.name}**: {param.description}")
            
            if params:
                embed.add_field(name="⚙️ Parameters", value="\n".join(params), inline=False)
        
        embed.set_footer(text="Use /help to see all commands")
        
        return embed

async def setup(bot):
    """Setup function for the HelpSystem cog"""
    await bot.add_cog(HelpSystem(bot))
