"""
Database models for the advanced music bot
Using SQLite with aiosqlite for async operations
"""

import aiosqlite
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages all database operations for the music bot"""
    
    def __init__(self, db_path: str = "musicbot.db"):
        self.db_path = db_path
        self._connection = None
    
    async def connect(self):
        """Initialize database connection and create tables"""
        self._connection = await aiosqlite.connect(self.db_path)
        await self._create_tables()
        logger.info(f"Connected to database: {self.db_path}")
    
    async def close(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            logger.info("Database connection closed")
    
    async def _create_tables(self):
        """Create all necessary database tables"""
        tables = [
            # Users table
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                discriminator TEXT,
                avatar_url TEXT,
                total_listening_time INTEGER DEFAULT 0,
                tracks_played INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                favorite_genre TEXT,
                preferred_volume INTEGER DEFAULT 100,
                auto_join BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Guilds table
            """
            CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY,
                guild_name TEXT NOT NULL,
                prefix TEXT DEFAULT '!',
                default_volume INTEGER DEFAULT 100,
                auto_disconnect BOOLEAN DEFAULT TRUE,
                auto_disconnect_time INTEGER DEFAULT 180,
                dj_role_id INTEGER,
                music_channel_id INTEGER,
                max_queue_size INTEGER DEFAULT 500,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Playlists table
            """
            CREATE TABLE IF NOT EXISTS playlists (
                playlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                guild_id INTEGER,
                description TEXT,
                is_public BOOLEAN DEFAULT FALSE,
                track_count INTEGER DEFAULT 0,
                total_duration INTEGER DEFAULT 0,
                cover_image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """,
            
            # Playlist tracks table
            """
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                track_title TEXT NOT NULL,
                track_artist TEXT,
                track_uri TEXT NOT NULL,
                track_duration INTEGER,
                track_thumbnail TEXT,
                position INTEGER NOT NULL,
                added_by INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (playlist_id) REFERENCES playlists(playlist_id) ON DELETE CASCADE,
                FOREIGN KEY (added_by) REFERENCES users(user_id)
            )
            """,
            
            # Listening history table
            """
            CREATE TABLE IF NOT EXISTS listening_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                track_title TEXT NOT NULL,
                track_artist TEXT,
                track_uri TEXT NOT NULL,
                track_duration INTEGER,
                listening_time INTEGER,
                completed BOOLEAN DEFAULT FALSE,
                skipped BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
            )
            """,
            
            # Queue history table
            """
            CREATE TABLE IF NOT EXISTS queue_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                track_title TEXT NOT NULL,
                track_artist TEXT,
                track_uri TEXT NOT NULL,
                track_duration INTEGER,
                position INTEGER,
                action TEXT NOT NULL, -- 'added', 'played', 'skipped', 'removed'
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """,
            
            # User preferences table
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                preferred_quality TEXT DEFAULT 'high',
                auto_lyrics BOOLEAN DEFAULT TRUE,
                bass_boost BOOLEAN DEFAULT FALSE,
                nightcore BOOLEAN DEFAULT FALSE,
                eight_d BOOLEAN DEFAULT FALSE,
                notification_settings TEXT DEFAULT '{}',
                theme TEXT DEFAULT 'default',
                language TEXT DEFAULT 'en',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """,
            
            # Statistics table
            """
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                guild_id INTEGER,
                user_id INTEGER,
                stat_type TEXT NOT NULL, -- 'daily_listens', 'command_usage', 'popular_tracks'
                stat_data TEXT NOT NULL, -- JSON data
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """,
            
            # Radio stations table
            """
            CREATE TABLE IF NOT EXISTS radio_stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                genre TEXT NOT NULL,
                description TEXT,
                seed_tracks TEXT NOT NULL, -- JSON array of track URIs
                created_by INTEGER,
                is_public BOOLEAN DEFAULT TRUE,
                play_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(user_id)
            )
            """
        ]
        
        for table_sql in tables:
            await self._connection.execute(table_sql)
        
        await self._connection.commit()
        logger.info("Database tables created/verified successfully")
    
    # User operations
    async def create_or_update_user(self, user_id: int, username: str, 
                                   discriminator: str = None, avatar_url: str = None):
        """Create or update user record"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, discriminator, avatar_url, last_seen)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, discriminator, avatar_url, datetime.now(timezone.utc)))
            await self._connection.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                return dict(zip([col[0] for col in cursor.description], row))
            return None
    
    async def update_user_stats(self, user_id: int, listening_time: int = 0, 
                              tracks_played: int = 0, commands_used: int = 0):
        """Update user statistics"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                UPDATE users SET 
                    total_listening_time = total_listening_time + ?,
                    tracks_played = tracks_played + ?,
                    commands_used = commands_used + ?,
                    last_seen = ?
                WHERE user_id = ?
            """, (listening_time, tracks_played, commands_used, 
                  datetime.now(timezone.utc), user_id))
            await self._connection.commit()
    
    # Guild operations
    async def create_or_update_guild(self, guild_id: int, guild_name: str, **kwargs):
        """Create or update guild record"""
        fields = list(kwargs.keys())
        values = list(kwargs.values())
        
        base_query = """
            INSERT OR REPLACE INTO guilds 
            (guild_id, guild_name, updated_at
        """
        
        if fields:
            base_query += ", " + ", ".join(fields)
        
        base_query += ") VALUES (?, ?, ?"
        base_query += ", ?" * len(fields) + ")"
        
        values = [guild_id, guild_name, datetime.now(timezone.utc)] + values
        
        async with self._connection.cursor() as cursor:
            await cursor.execute(base_query, values)
            await self._connection.commit()
    
    async def get_guild(self, guild_id: int) -> Optional[Dict]:
        """Get guild data"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM guilds WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if row:
                return dict(zip([col[0] for col in cursor.description], row))
            return None
    
    # Playlist operations
    async def create_playlist(self, name: str, user_id: int, guild_id: int = None, 
                            description: str = None, is_public: bool = False) -> int:
        """Create a new playlist"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO playlists 
                (name, user_id, guild_id, description, is_public)
                VALUES (?, ?, ?, ?, ?)
            """, (name, user_id, guild_id, description, is_public))
            await self._connection.commit()
            return cursor.lastrowid
    
    async def get_user_playlists(self, user_id: int, guild_id: int = None) -> List[Dict]:
        """Get all playlists for a user"""
        query = "SELECT * FROM playlists WHERE user_id = ?"
        params = [user_id]
        
        if guild_id:
            query += " AND (guild_id = ? OR guild_id IS NULL)"
            params.append(guild_id)
        
        query += " ORDER BY created_at DESC"
        
        async with self._connection.cursor() as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    
    async def add_track_to_playlist(self, playlist_id: int, track_title: str, 
                                  track_artist: str, track_uri: str, 
                                  track_duration: int, added_by: int,
                                  track_thumbnail: str = None) -> bool:
        """Add a track to a playlist"""
        async with self._connection.cursor() as cursor:
            # Get current track count for position
            await cursor.execute(
                "SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = ?", 
                (playlist_id,)
            )
            position = (await cursor.fetchone())[0] + 1
            
            # Insert track
            await cursor.execute("""
                INSERT INTO playlist_tracks 
                (playlist_id, track_title, track_artist, track_uri, 
                 track_duration, track_thumbnail, position, added_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (playlist_id, track_title, track_artist, track_uri, 
                  track_duration, track_thumbnail, position, added_by))
            
            # Update playlist stats
            await cursor.execute("""
                UPDATE playlists SET 
                    track_count = track_count + 1,
                    total_duration = total_duration + ?,
                    updated_at = ?
                WHERE playlist_id = ?
            """, (track_duration or 0, datetime.now(timezone.utc), playlist_id))
            
            await self._connection.commit()
            return True
    
    async def get_playlist_tracks(self, playlist_id: int) -> List[Dict]:
        """Get all tracks in a playlist"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                SELECT * FROM playlist_tracks 
                WHERE playlist_id = ? 
                ORDER BY position
            """, (playlist_id,))
            rows = await cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    
    # Listening history operations
    async def add_listening_record(self, user_id: int, guild_id: int, 
                                 track_title: str, track_artist: str, 
                                 track_uri: str, track_duration: int,
                                 listening_time: int, completed: bool = False,
                                 skipped: bool = False):
        """Add a listening history record"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO listening_history 
                (user_id, guild_id, track_title, track_artist, track_uri, 
                 track_duration, listening_time, completed, skipped)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, guild_id, track_title, track_artist, track_uri,
                  track_duration, listening_time, completed, skipped))
            await self._connection.commit()
    
    async def get_user_listening_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's listening history"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                SELECT * FROM listening_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    
    async def get_popular_tracks(self, guild_id: int = None, days: int = 7, limit: int = 10) -> List[Dict]:
        """Get most popular tracks"""
        base_query = """
            SELECT track_title, track_artist, track_uri, COUNT(*) as play_count,
                   SUM(listening_time) as total_listening_time
            FROM listening_history 
            WHERE timestamp >= datetime('now', '-{} days')
        """.format(days)
        
        params = []
        if guild_id:
            base_query += " AND guild_id = ?"
            params.append(guild_id)
        
        base_query += " GROUP BY track_uri ORDER BY play_count DESC LIMIT ?"
        params.append(limit)
        
        async with self._connection.cursor() as cursor:
            await cursor.execute(base_query, params)
            rows = await cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    
    # Statistics operations
    async def save_daily_statistics(self, date: str, guild_id: int = None, 
                                  user_id: int = None, stat_type: str = None, 
                                  stat_data: Dict = None):
        """Save daily statistics"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO statistics 
                (date, guild_id, user_id, stat_type, stat_data)
                VALUES (?, ?, ?, ?, ?)
            """, (date, guild_id, user_id, stat_type, json.dumps(stat_data)))
            await self._connection.commit()
    
    async def get_statistics(self, stat_type: str, days: int = 7, 
                           guild_id: int = None, user_id: int = None) -> List[Dict]:
        """Get statistics data"""
        query = """
            SELECT * FROM statistics 
            WHERE stat_type = ? AND date >= date('now', '-{} days')
        """.format(days)
        
        params = [stat_type]
        
        if guild_id:
            query += " AND guild_id = ?"
            params.append(guild_id)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY date DESC"
        
        async with self._connection.cursor() as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    
    # Radio stations operations
    async def create_radio_station(self, name: str, genre: str, seed_tracks: List[str],
                                 description: str = None, created_by: int = None,
                                 is_public: bool = True) -> int:
        """Create a radio station"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO radio_stations 
                (name, genre, description, seed_tracks, created_by, is_public)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, genre, description, json.dumps(seed_tracks), created_by, is_public))
            await self._connection.commit()
            return cursor.lastrowid
    
    async def get_radio_stations(self, genre: str = None) -> List[Dict]:
        """Get radio stations"""
        query = "SELECT * FROM radio_stations WHERE is_public = TRUE"
        params = []
        
        if genre:
            query += " AND genre = ?"
            params.append(genre)
        
        query += " ORDER BY play_count DESC"
        
        async with self._connection.cursor() as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            stations = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
            
            # Parse seed_tracks JSON
            for station in stations:
                station['seed_tracks'] = json.loads(station['seed_tracks'])
            
            return stations
    
    async def increment_radio_play_count(self, station_id: int):
        """Increment radio station play count"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                UPDATE radio_stations 
                SET play_count = play_count + 1 
                WHERE id = ?
            """, (station_id,))
            await self._connection.commit()

# Global database manager instance
db = None

async def initialize_database(db_path: str = "musicbot.db"):
    """Initialize the global database manager"""
    global db
    db = DatabaseManager(db_path)
    await db.connect()
    return db

async def close_database():
    """Close the global database connection"""
    global db
    if db:
        await db.close()
        db = None
