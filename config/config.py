import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BotConfig:
    """Advanced configuration management for the music bot"""
    
    def __init__(self):
        # Core Bot Settings
        self.BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
        self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        # Do not raise on import. Defer validation to application startup.
        
        application_id_str = os.getenv("APPLICATION_ID")
        # APPLICATION_ID may be None at import time; convert when present
        self.APPLICATION_ID = int(application_id_str) if application_id_str else None
        self.OWNERS = list(map(int, os.getenv("OWNERS", "").split(","))) if os.getenv("OWNERS") else []
        
        # Lavalink Configuration
        self.LAVALINK_HOST = os.getenv("LAVALINK_HOST", "lavalink.pericsq.ro")
        self.LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", "4499"))
        self.LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "plamea")
        self.LAVALINK_NAME = os.getenv("LAVALINK_NAME", "musik-node")
        self.LAVALINK_SECURE = os.getenv("LAVALINK_SECURE", "false").lower() == "true"
        
        # Music Settings
        self.DEFAULT_VOLUME = int(os.getenv("DEFAULT_VOLUME", "100"))
        self.MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "500"))
        self.TIMEOUT_DURATION = int(os.getenv("TIMEOUT_DURATION", "300"))
        self.AUTO_DISCONNECT_EMPTY = os.getenv("AUTO_DISCONNECT_EMPTY", "true").lower() == "true"
        self.AUTO_DISCONNECT_TIME = int(os.getenv("AUTO_DISCONNECT_TIME", "180"))
        
        # External API Keys
        self.SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
        self.SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN")
        self.LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
        
        # Database Configuration
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///musicbot.db")
        self.DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "10"))
        
        # Web Dashboard
        self.WEB_DASHBOARD_ENABLED = os.getenv("WEB_DASHBOARD_ENABLED", "true").lower() == "true"
        self.WEB_HOST = os.getenv("WEB_HOST", "localhost")
        self.WEB_PORT = int(os.getenv("WEB_PORT", "8080"))
        self.WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "your-secret-key-here")
        
        # Feature Toggles
        self.ENABLE_LYRICS = os.getenv("ENABLE_LYRICS", "true").lower() == "true"
        self.ENABLE_SPOTIFY = os.getenv("ENABLE_SPOTIFY", "true").lower() == "true"
        self.ENABLE_PLAYLISTS = os.getenv("ENABLE_PLAYLISTS", "true").lower() == "true"
        self.ENABLE_STATISTICS = os.getenv("ENABLE_STATISTICS", "true").lower() == "true"
        self.ENABLE_RADIO_MODE = os.getenv("ENABLE_RADIO_MODE", "true").lower() == "true"
        self.ENABLE_DJ_FEATURES = os.getenv("ENABLE_DJ_FEATURES", "true").lower() == "true"
        # Cog selection toggles (avoid duplicate slash command registration)
        self.ENABLE_ADVANCED_MUSIC = os.getenv("ENABLE_ADVANCED_MUSIC", "false").lower() == "true"
        self.ENABLE_VOICE_AND_PLAYLIST = os.getenv("ENABLE_VOICE_AND_PLAYLIST", "false").lower() == "true"
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.getenv("LOG_FILE", "musicbot.log")
        self.LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
        self.LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        
        # Performance Settings
        self.CACHE_SIZE = int(os.getenv("CACHE_SIZE", "1000"))
        self.PRELOAD_TRACKS = int(os.getenv("PRELOAD_TRACKS", "3"))
        self.SEARCH_RESULTS_LIMIT = int(os.getenv("SEARCH_RESULTS_LIMIT", "10"))
        
        # Security Settings
        self.ALLOWED_GUILDS = list(map(int, os.getenv("ALLOWED_GUILDS", "").split(","))) if os.getenv("ALLOWED_GUILDS") else []
        self.BLOCKED_USERS = list(map(int, os.getenv("BLOCKED_USERS", "").split(","))) if os.getenv("BLOCKED_USERS") else []
        self.RATE_LIMIT_COMMANDS = int(os.getenv("RATE_LIMIT_COMMANDS", "10"))
        self.RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
        
        # Audio Quality Settings
        self.AUDIO_QUALITY = os.getenv("AUDIO_QUALITY", "high")  # low, medium, high, lossless
        self.NORMALIZE_VOLUME = os.getenv("NORMALIZE_VOLUME", "true").lower() == "true"
        self.CROSSFADE_DURATION = float(os.getenv("CROSSFADE_DURATION", "3.0"))
        
        # Localization
        self.DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
        self.TIMEZONE = os.getenv("TIMEZONE", "UTC")
        
    def get_lavalink_uri(self) -> str:
        """Get the complete Lavalink URI"""
        protocol = "https" if self.LAVALINK_SECURE else "http"
        return f"{protocol}://{self.LAVALINK_HOST}:{self.LAVALINK_PORT}"
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is bot owner"""
        return user_id in self.OWNERS
    
    def is_guild_allowed(self, guild_id: int) -> bool:
        """Check if guild is allowed to use the bot"""
        return not self.ALLOWED_GUILDS or guild_id in self.ALLOWED_GUILDS
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Check if user is blocked from using the bot"""
        return user_id in self.BLOCKED_USERS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (excluding sensitive data)"""
        return {
            'bot_prefix': self.BOT_PREFIX,
            'max_queue_size': self.MAX_QUEUE_SIZE,
            'default_volume': self.DEFAULT_VOLUME,
            'timeout_duration': self.TIMEOUT_DURATION,
            'features': {
                'lyrics': self.ENABLE_LYRICS,
                'spotify': self.ENABLE_SPOTIFY,
                'playlists': self.ENABLE_PLAYLISTS,
                'statistics': self.ENABLE_STATISTICS,
                'radio_mode': self.ENABLE_RADIO_MODE,
                'dj_features': self.ENABLE_DJ_FEATURES
            },
            'audio_quality': self.AUDIO_QUALITY,
            'normalize_volume': self.NORMALIZE_VOLUME,
            'crossfade_duration': self.CROSSFADE_DURATION
        }

# Create global config instance
config = BotConfig()

# Legacy compatibility - maintain old variable names
BOT_PREFIX = config.BOT_PREFIX
DISCORD_TOKEN = config.DISCORD_TOKEN
APPLICATION_ID = config.APPLICATION_ID
LAVALINK_HOST = config.LAVALINK_HOST
LAVALINK_PORT = config.LAVALINK_PORT
LAVALINK_PASSWORD = config.LAVALINK_PASSWORD
LAVALINK_NAME = config.LAVALINK_NAME
LAVALINK_SECURE = config.LAVALINK_SECURE
DEFAULT_VOLUME = config.DEFAULT_VOLUME
MAX_QUEUE_SIZE = config.MAX_QUEUE_SIZE
TIMEOUT_DURATION = config.TIMEOUT_DURATION
