"""
Advanced logging system for the music bot
Comprehensive error handling, detailed logging, and user-friendly error messages
"""

import logging
import logging.handlers
import sys
import traceback
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import discord
from discord.ext import commands
from config.config import config
import functools

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

class ColoredFormatter(logging.Formatter):
    """Colored console logging formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        record.name = f"\033[94m{record.name}{self.RESET}"  # Blue
        return super().format(record)

class DatabaseLogHandler(logging.Handler):
    """Custom log handler that saves logs to database"""
    
    def __init__(self):
        super().__init__()
        self.buffer = []
        self.buffer_size = 100
    
    def emit(self, record):
        """Emit a log record to the database buffer"""
        try:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created),
                'level': record.levelname,
                'module': record.name,
                'message': record.getMessage(),
                'function': record.funcName,
                'line': record.lineno
            }
            
            if record.exc_info:
                log_entry['exception'] = self.format_exception(record.exc_info)
            
            self.buffer.append(log_entry)
            
            # Flush buffer when it reaches the limit
            if len(self.buffer) >= self.buffer_size:
                asyncio.create_task(self.flush_to_database())
                
        except Exception:
            self.handleError(record)
    
    def format_exception(self, exc_info):
        """Format exception information"""
        return ''.join(traceback.format_exception(*exc_info))
    
    async def flush_to_database(self):
        """Flush log buffer to database"""
        if not self.buffer:
            return
        
        try:
            from database.models import db
            if db:
                for entry in self.buffer:
                    await db.save_daily_statistics(
                        date=entry['timestamp'].date().isoformat(),
                        stat_type='log_entry',
                        stat_data=entry
                    )
                self.buffer.clear()
        except Exception as e:
            print(f"Failed to flush logs to database: {e}")

def setup_logging():
    """Setup the comprehensive logging system"""
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=f"logs/{config.LOG_FILE}",
            maxBytes=config.LOG_MAX_SIZE,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        # If file logging fails, continue with console only
        console_handler.stream.write(f"Warning: Could not setup file logging: {e}\n")
    
    # Database handler for important logs
    try:
        db_handler = DatabaseLogHandler()
        db_handler.setLevel(logging.WARNING)
        root_logger.addHandler(db_handler)
    except Exception:
        # Continue without database logging if it fails
        pass
    
    # Setup specific loggers
    setup_discord_logging()
    setup_wavelink_logging()
    
    # Get a logger for the main module
    main_logger = logging.getLogger('musicbot')
    main_logger.info("Logging system initialized successfully")
    
    return main_logger

def setup_discord_logging():
    """Setup Discord.py specific logging"""
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
    
    # Separate file for Discord logs
    discord_handler = logging.handlers.RotatingFileHandler(
        filename='logs/discord.log',
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=3,
        encoding='utf-8'
    )
    discord_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    discord_handler.setFormatter(discord_formatter)
    discord_logger.addHandler(discord_handler)

def setup_wavelink_logging():
    """Setup Wavelink specific logging"""
    wavelink_logger = logging.getLogger('wavelink')
    wavelink_logger.setLevel(logging.INFO)
    
    # Separate file for Wavelink logs
    wavelink_handler = logging.handlers.RotatingFileHandler(
        filename='logs/wavelink.log',
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=3,
        encoding='utf-8'
    )
    wavelink_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    wavelink_handler.setFormatter(wavelink_formatter)
    wavelink_logger.addHandler(wavelink_handler)

class ErrorHandler:
    """Advanced error handling with user-friendly messages"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('error_handler')
        self.error_messages = self._load_error_messages()
        self.error_counts = {}
    
    def _load_error_messages(self) -> Dict[str, str]:
        """Load user-friendly error messages"""
        return {
            'MissingPermissions': "❌ I don't have the required permissions to perform this action.",
            'BotMissingPermissions': "❌ I'm missing permissions. Please check my role permissions.",
            'CommandOnCooldown': "⏰ This command is on cooldown. Try again in {retry_after:.1f} seconds.",
            'NoPrivateMessage': "❌ This command cannot be used in private messages.",
            'NotOwner': "❌ This command is restricted to bot owners only.",
            'CheckFailure': "❌ You don't have permission to use this command.",
            'CommandInvokeError': "❌ An error occurred while executing the command.",
            'ArgumentParsingError': "❌ Invalid arguments provided. Please check the command usage.",
            'BadArgument': "❌ Invalid argument provided. Please check the command usage.",
            'MissingRequiredArgument': "❌ Missing required argument. Please check the command usage.",
            'TooManyArguments': "❌ Too many arguments provided. Please check the command usage.",
            'UserInputError': "❌ Invalid input provided. Please check your input and try again.",
            'NoVoiceChannel': "❌ You need to be in a voice channel to use this command.",
            'AlreadyConnected': "❌ I'm already connected to a voice channel.",
            'NotConnected': "❌ I'm not connected to any voice channel.",
            'VoiceConnectionError': "❌ Failed to connect to voice channel. Please try again.",
            'QueueEmpty': "❌ The music queue is empty.",
            'QueueFull': "❌ The music queue is full. Please wait for some tracks to finish.",
            'TrackNotFound': "❌ No tracks found for your search query.",
            'PlaylistNotFound': "❌ Playlist not found or is private.",
            'SpotifyError': "❌ Spotify integration error. Please try again later.",
            'LyricsNotFound': "❌ No lyrics found for this track.",
            'DatabaseError': "❌ Database error occurred. Please contact support if this persists.",
            'APIError': "❌ External service error. Please try again later.",
            'RateLimited': "⏰ You're being rate limited. Please slow down and try again later.",
        }
    
    async def handle_error(self, ctx_or_interaction, error: Exception, 
                          send_to_user: bool = True) -> Optional[str]:
        """Handle errors with appropriate logging and user feedback"""
        error_type = type(error).__name__
        error_id = f"{error_type}_{datetime.now().timestamp()}"
        
        # Log the error
        self.logger.error(
            f"Error {error_id}: {error_type} - {str(error)}",
            exc_info=error,
            extra={
                'error_id': error_id,
                'user_id': getattr(ctx_or_interaction.user, 'id', None),
                'guild_id': getattr(ctx_or_interaction.guild, 'id', None),
                'command': getattr(ctx_or_interaction, 'command', None)
            }
        )
        
        # Count errors for monitoring
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Get user-friendly message
        user_message = self._get_user_friendly_message(error)
        
        # Send to user if requested
        if send_to_user and user_message:
            try:
                if isinstance(ctx_or_interaction, discord.Interaction):
                    if ctx_or_interaction.response.is_done():
                        await ctx_or_interaction.followup.send(user_message, ephemeral=True)
                    else:
                        await ctx_or_interaction.response.send_message(user_message, ephemeral=True)
                else:
                    await ctx_or_interaction.send(user_message)
            except Exception as send_error:
                self.logger.error(f"Failed to send error message: {send_error}")
        
        return error_id
    
    def _get_user_friendly_message(self, error: Exception) -> str:
        """Get a user-friendly error message"""
        error_type = type(error).__name__
        
        # Check for specific error types
        if error_type in self.error_messages:
            message = self.error_messages[error_type]
            
            # Format message with error attributes
            if hasattr(error, 'retry_after'):
                message = message.format(retry_after=error.retry_after)
            
            return message
        
        # Generic fallback message
        return "❌ An unexpected error occurred. Please try again or contact support if this persists."
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        return self.error_counts.copy()

def log_function_call(func):
    """Decorator to log function calls"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args[:2]} kwargs={list(kwargs.keys())}")
        
        try:
            start_time = datetime.now()
            result = await func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.debug(f"Function {func.__name__} completed in {duration:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Function {func.__name__} failed: {str(e)}", exc_info=True)
            raise
    
    return wrapper

def log_command_usage(func):
    """Decorator to log command usage"""
    @functools.wraps(func)
    async def wrapper(self, ctx_or_interaction, *args, **kwargs):
        logger = logging.getLogger('command_usage')
        
        user_info = f"{ctx_or_interaction.user.name}#{ctx_or_interaction.user.discriminator} ({ctx_or_interaction.user.id})"
        guild_info = f"{ctx_or_interaction.guild.name} ({ctx_or_interaction.guild.id})" if ctx_or_interaction.guild else "DM"
        command_name = func.__name__
        
        logger.info(f"Command '{command_name}' used by {user_info} in {guild_info}")
        
        try:
            return await func(self, ctx_or_interaction, *args, **kwargs)
        except Exception as e:
            logger.error(f"Command '{command_name}' failed for {user_info}: {str(e)}")
            raise
    
    return wrapper

class PerformanceMonitor:
    """Monitor bot performance and resource usage"""
    
    def __init__(self):
        self.logger = logging.getLogger('performance')
        self.metrics = {
            'commands_executed': 0,
            'errors_occurred': 0,
            'tracks_played': 0,
            'guilds_joined': 0,
            'guilds_left': 0
        }
        self.start_time = datetime.now()
    
    def increment_metric(self, metric: str, value: int = 1):
        """Increment a performance metric"""
        if metric in self.metrics:
            self.metrics[metric] += value
            self.logger.debug(f"Metric '{metric}' incremented to {self.metrics[metric]}")
    
    def get_uptime(self) -> str:
        """Get bot uptime as formatted string"""
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        try:
            import psutil
            process = psutil.Process()
            
            return {
                'uptime': self.get_uptime(),
                'metrics': self.metrics.copy(),
                'memory_usage': f"{process.memory_info().rss / 1024 / 1024:.1f} MB",
                'cpu_usage': f"{process.cpu_percent():.1f}%",
                'threads': process.num_threads()
            }
        except ImportError:
            return {
                'uptime': self.get_uptime(),
                'metrics': self.metrics.copy(),
                'memory_usage': 'N/A (psutil not installed)',
                'cpu_usage': 'N/A (psutil not installed)',
                'threads': 'N/A (psutil not installed)'
            }

# Global instances
error_handler = None
performance_monitor = PerformanceMonitor()

def initialize_error_handling(bot):
    """Initialize error handling system"""
    global error_handler
    error_handler = ErrorHandler(bot)
    
    @bot.event
    async def on_application_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Handle slash command errors"""
        await error_handler.handle_error(interaction, error)
        performance_monitor.increment_metric('errors_occurred')
    
    @bot.event
    async def on_command_error(ctx, error):
        """Handle prefix command errors"""
        await error_handler.handle_error(ctx, error)
        performance_monitor.increment_metric('errors_occurred')
    
    logging.info("Error handling system initialized")

def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module"""
    return logging.getLogger(name)

# Initialize logging on import
setup_logging()
