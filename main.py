#!/usr/bin/env python3
"""
Advanced Discord Music Bot
Main entry point for the bot application.

Developer: <@997351056600219740>

Features:
- Advanced queue management with persistence
- Spotify integration for playlists and albums
- Lyrics integration with Genius API
- Audio effects and filters
- DJ moderation features
- Statistics and analytics
- Web dashboard (optional)
"""

import os
import sys
import asyncio
import logging
import signal
import traceback
from typing import Optional, List, Dict, Any

import discord
from discord.ext import commands
import wavelink
from aiohttp import web

# Import configuration
from config.config import config

# Import database
from database.models import db, initialize_database

# Import utilities
from utils.logging_system import setup_logging
from utils.advanced_queue import get_queue_manager

# Import integrations
from integrations.spotify import get_spotify_manager
from integrations.lyrics import get_lyrics_manager

# Setup logging with fallback
try:
    logger = setup_logging()
    if logger is None:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('musicbot')
except Exception as e:
    # Fallback to basic logging
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('musicbot')
    logger.warning(f"Advanced logging setup failed, using basic logging: {e}")

# Safe logging functions to prevent NoneType errors
def safe_log_info(message: str):
    """Safely log info message"""
    if logger:
        logger.info(message)
    else:
        print(f"INFO: {message}")
        
def safe_log_error(message: str):
    """Safely log error message"""
    if logger:
        logger.error(message)
    else:
        print(f"ERROR: {message}")
        
def safe_log_warning(message: str):
    """Safely log warning message"""
    if logger:
        logger.warning(message)
    else:
        print(f"WARNING: {message}")

class MusicBot(commands.Bot):
    """Advanced Discord Music Bot with comprehensive features"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        intents.guild_messages = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.BOT_PREFIX),
            intents=intents,
            application_id=config.APPLICATION_ID,
            help_command=None,  # We'll create a custom help command
            case_insensitive=True,
            strip_after_prefix=True
        )
        
        # Bot state
        self.startup_complete = False
        self.web_app = None
        
        # Managers
        self.queue_manager = None
        self.spotify_manager = None
        self.lyrics_manager = None
    
    async def setup_hook(self):
        """Initial setup when bot starts"""
        safe_log_info("🚀 Starting Advanced Discord Music Bot...")
        
        # Initialize database
        try:
            await initialize_database()
            safe_log_info("✅ Database initialized successfully")
        except Exception as e:
            safe_log_error(f"❌ Failed to initialize database: {e}")
            safe_log_warning("Continuing without database - some features may be limited")
        
        # Initialize managers
        try:
            self.queue_manager = get_queue_manager()
            safe_log_info("✅ Queue manager initialized")
            
            if config.ENABLE_SPOTIFY and config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET:
                self.spotify_manager = get_spotify_manager()
                safe_log_info("✅ Spotify integration enabled")
            
            if config.ENABLE_LYRICS and config.GENIUS_API_TOKEN:
                self.lyrics_manager = get_lyrics_manager()
                safe_log_info("✅ Lyrics integration enabled")
        except Exception as e:
            safe_log_error(f"❌ Failed to initialize managers: {e}")
            raise
        
        # Setup Lavalink with fallback support
        try:
            from utils.lavalink_helper import connect_lavalink
            success = await connect_lavalink(self)
            if success:
                safe_log_info("✅ Lavalink connection established")
            else:
                safe_log_warning("Bot will continue without Lavalink - music features will be limited")
        except Exception as e:
            safe_log_error(f"❌ Failed to setup Lavalink: {e}")
            safe_log_warning("Bot will continue without Lavalink - music features will be limited")
        
        # Load cogs
        await self.load_cogs()
        
        # Setup web dashboard if enabled
        if config.WEB_DASHBOARD_ENABLED:
            await self.setup_web_dashboard()
        
        safe_log_info("🎵 Bot setup complete!")
    
    async def load_cogs(self):
        """Load all bot cogs"""
        # Base music cog selection (avoid duplicate slash commands)
        cog_files = []
        if config.ENABLE_ADVANCED_MUSIC:
            cog_files.append('cogs.advanced_music')
        else:
            cog_files.append('cogs.music')

        # Optional, may overlap with base music cog - disabled by default
        if config.ENABLE_VOICE_AND_PLAYLIST:
            cog_files.append('cogs.voice_and_playlist')

        # Other non-conflicting cogs
        cog_files += [
            'cogs.enhanced_commands',
            'cogs.utility_info',
            'cogs.audio_effects',
            'cogs.radio_streaming',
            'cogs.help_system',
            'cogs.music_dashboard',
            'cogs.advanced_commands',
            'cogs.admin_panel',
        ]
        
        # Load optional cogs based on configuration
        if config.ENABLE_DJ_FEATURES:
            cog_files.append('cogs.dj_moderation')
        
        for cog in cog_files:
            try:
                await self.load_extension(cog)
                safe_log_info(f"✅ Loaded cog: {cog}")
            except Exception as e:
                safe_log_error(f"❌ Failed to load cog {cog}: {e}")
                traceback.print_exception(type(e), e, e.__traceback__)
    
    async def setup_web_dashboard(self):
        """Setup optional web dashboard"""
        try:
            from web.dashboard import create_web_app
            self.web_app = create_web_app(self)
            
            runner = web.AppRunner(self.web_app)
            await runner.setup()
            site = web.TCPSite(runner, config.WEB_HOST, config.WEB_PORT)
            await site.start()
            
            safe_log_info(f"🌐 Web dashboard running on http://{config.WEB_HOST}:{config.WEB_PORT}")
        except ImportError:
            safe_log_warning("⚠️ Web dashboard module not found, skipping...")
        except Exception as e:
            safe_log_error(f"❌ Failed to start web dashboard: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        safe_log_info(f"🤖 Bot is ready! Logged in as {self.user}")
        safe_log_info(f"📊 Connected to {len(self.guilds)} guilds")
        safe_log_info(f"👥 Serving {len(set(self.get_all_members()))} users")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            safe_log_info(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            safe_log_error(f"❌ Failed to sync commands: {e}")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="JEESAN"
        )
        await self.change_presence(activity=activity, status=discord.Status.dnd)
        
        self.startup_complete = True
        safe_log_info("🎵 Bot is fully operational!")
    
    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a guild"""
        safe_log_info(f"🆕 Joined guild: {guild.name} (ID: {guild.id})")
        
        # Check if guild is allowed
        if not config.is_guild_allowed(guild.id):
            safe_log_warning(f"⚠️ Guild {guild.name} is not in allowed list, leaving...")
            await guild.leave()
            return
        
        # Send welcome message
        try:
            # Find a suitable channel to send welcome message
            channel = None
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break
            
            if channel:
                embed = discord.Embed(
                    title="🎵 Thanks for adding me!",
                    description=f"I'm an advanced music bot with tons of features!\n"
                               f"Use `{config.BOT_PREFIX}help` to get started.",
                    color=discord.Color.blurple()
                )
                embed.add_field(
                    name="🎶 Quick Start",
                    value=f"• `{config.BOT_PREFIX}play <song>` - Play music\n"
                          f"• `/play` - Use slash commands\n"
                          f"• `{config.BOT_PREFIX}help` - Show all commands",
                    inline=False
                )
                await channel.send(embed=embed)
        except Exception as e:
            safe_log_error(f"Failed to send welcome message: {e}")
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when bot leaves a guild"""
        safe_log_info(f"📤 Left guild: {guild.name} (ID: {guild.id})")
        
        # Cleanup guild data
        try:
            if self.queue_manager:
                await self.queue_manager.cleanup_guild_data(guild.id)
        except Exception as e:
            safe_log_error(f"Failed to cleanup guild data: {e}")
    
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Global error handler"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument provided")
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command")
            return
        
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions to execute this command")
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Command is on cooldown. Try again in {error.retry_after:.2f} seconds")
            return
        
        # Log unexpected errors
        safe_log_error(f"Command error in {ctx.command}: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)
        
        # Send generic error message
        await ctx.send("❌ An unexpected error occurred. Please try again later.")
    
    async def close(self):
        """Clean shutdown"""
        safe_log_info("🔄 Shutting down bot...")
        
        # Disconnect from all voice channels
        for guild in self.guilds:
            if guild.voice_client:
                await guild.voice_client.disconnect(force=True)
        
        # Close database connections
        if db:
            await db.close()
        
        # Close web app if running
        if self.web_app:
            await self.web_app.cleanup()
        
        await super().close()
        safe_log_info("✅ Bot shutdown complete")

def setup_signal_handlers(bot: MusicBot):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        safe_log_info(f"Received signal {signum}, initiating graceful shutdown...")
        try:
            asyncio.create_task(bot.close())
        except Exception as e:
            print(f"Error during signal handling: {e}")
    
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    except Exception as e:
        safe_log_warning(f"Could not setup signal handlers: {e}")

async def main():
    """Main entry point"""
    # Validate configuration
    try:
        if not config.DISCORD_TOKEN:
            safe_log_error("❌ DISCORD_TOKEN not found in environment variables")
            safe_log_error("Please create a .env file with your Discord bot token")
            return 1
        
        if not config.APPLICATION_ID:
            safe_log_error("❌ APPLICATION_ID not found in environment variables")
            safe_log_error("Please add your Discord application ID to the .env file")
            return 1
    except Exception as e:
        safe_log_error(f"❌ Configuration error: {e}")
        return 1
    
    # Create bot instance
    bot = MusicBot()
    
    # Setup signal handlers
    setup_signal_handlers(bot)
    
    # Start bot
    try:
        await bot.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        safe_log_info("🛑 Received keyboard interrupt, shutting down...")
    except Exception as e:
        safe_log_error(f"❌ Critical error: {e}")
        traceback.print_exception(type(e), e, e.__traceback__)
        return 1
    finally:
        if not bot.is_closed():
            await bot.close()
    
    return 0

if __name__ == "__main__":
    try:
        # Check Python version
        if sys.version_info < (3, 8):
            print("❌ Python 3.8 or higher is required")
            sys.exit(1)
        
        # Run the bot
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exception(type(e), e, e.__traceback__)
        sys.exit(1)
