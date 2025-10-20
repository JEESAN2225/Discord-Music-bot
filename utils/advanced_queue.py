"""
Advanced queue system for the music bot
Enhanced queue with history, autoplay suggestions, queue persistence, and smart shuffling
"""

import discord
import wavelink
import asyncio
import random
import time
from typing import List, Dict, Optional, Any, Tuple, Set
from collections import deque
from datetime import datetime, timezone
import json
import logging
from config.config import config

logger = logging.getLogger(__name__)

class TrackInfo:
    """Enhanced track information container"""
    
    def __init__(self, track: wavelink.Playable, requester: discord.Member = None, 
                 added_at: datetime = None, priority: int = 0, **metadata):
        self.track = track
        self.requester = requester
        self.added_at = added_at or datetime.now(timezone.utc)
        self.priority = priority  # Higher priority = plays earlier
        self.metadata = metadata
        
        # Track statistics
        self.play_count = 0
        self.skip_count = 0
        self.last_played = None
        self.total_listening_time = 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'uri': self.track.uri,
            'title': self.track.title,
            'author': getattr(self.track, 'author', ''),
            'length': getattr(self.track, 'length', 0),
            'requester_id': self.requester.id if self.requester else None,
            'added_at': self.added_at.isoformat(),
            'priority': self.priority,
            'metadata': self.metadata,
            'play_count': self.play_count,
            'skip_count': self.skip_count,
            'total_listening_time': self.total_listening_time
        }
    
    @classmethod
    async def from_dict(cls, data: Dict[str, Any], guild: discord.Guild = None):
        """Create TrackInfo from dictionary"""
        try:
            # Search for the track
            tracks = await wavelink.Playable.search(data['uri'])
            if not tracks:
                return None
            
            track = tracks[0]
            requester = None
            
            if data.get('requester_id') and guild:
                requester = guild.get_member(data['requester_id'])
            
            track_info = cls(
                track=track,
                requester=requester,
                added_at=datetime.fromisoformat(data['added_at']),
                priority=data.get('priority', 0),
                **data.get('metadata', {})
            )
            
            # Restore statistics
            track_info.play_count = data.get('play_count', 0)
            track_info.skip_count = data.get('skip_count', 0)
            track_info.total_listening_time = data.get('total_listening_time', 0)
            
            return track_info
        except Exception as e:
            logger.error(f"Failed to create TrackInfo from dict: {e}")
            return None

class AdvancedQueue:
    """Advanced queue with enhanced features"""
    
    def __init__(self, guild_id: int, max_size: int = None):
        self.guild_id = guild_id
        self.max_size = max_size or config.MAX_QUEUE_SIZE
        
        # Queue containers
        self._queue: List[TrackInfo] = []
        self._history: deque = deque(maxlen=100)  # Last 100 played tracks
        self._favorites: Set[str] = set()  # Track URIs marked as favorites
        
        # Queue modes
        self.shuffle_enabled = False
        self.repeat_mode = "off"  # "off", "track", "queue"
        self.autoplay_enabled = False
        
        # Smart features
        self._autoplay_seeds: List[str] = []  # Track URIs used for recommendations
        self._user_preferences: Dict[int, Dict] = {}  # User listening preferences
        self._genre_weights: Dict[str, float] = {}  # Genre preference weights
        
        # Statistics
        self.total_tracks_added = 0
        self.total_tracks_played = 0
        self.created_at = datetime.now(timezone.utc)
        
    def __len__(self) -> int:
        return len(self._queue)
    
    def __bool__(self) -> bool:
        return bool(self._queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return len(self._queue) == 0
    
    def is_full(self) -> bool:
        """Check if queue is at capacity"""
        return len(self._queue) >= self.max_size
    
    def add(self, track: wavelink.Playable, requester: discord.Member = None, 
            priority: int = 0, **metadata) -> bool:
        """Add a track to the queue"""
        if self.is_full():
            return False
        
        track_info = TrackInfo(track, requester, priority=priority, **metadata)
        
        if priority > 0:
            # Insert based on priority
            inserted = False
            for i, existing_track in enumerate(self._queue):
                if existing_track.priority < priority:
                    self._queue.insert(i, track_info)
                    inserted = True
                    break
            
            if not inserted:
                self._queue.append(track_info)
        else:
            self._queue.append(track_info)
        
        self.total_tracks_added += 1
        self._update_user_preferences(requester, track)
        return True
    
    def add_next(self, track: wavelink.Playable, requester: discord.Member = None, **metadata) -> bool:
        """Add track to play next (highest priority)"""
        return self.add(track, requester, priority=999, **metadata)
    
    def get(self) -> Optional[TrackInfo]:
        """Get next track from queue"""
        if self.is_empty():
            return None
        
        if self.shuffle_enabled and len(self._queue) > 1:
            # Smart shuffle - avoid recently played tracks
            available_tracks = [
                (i, track) for i, track in enumerate(self._queue)
                if not self._was_recently_played(track.track.uri)
            ]
            
            if available_tracks:
                index, track_info = random.choice(available_tracks)
                self._queue.pop(index)
            else:
                # All tracks were recently played, fall back to random
                index = random.randint(0, len(self._queue) - 1)
                track_info = self._queue.pop(index)
        else:
            track_info = self._queue.pop(0)
        
        # Update statistics
        track_info.play_count += 1
        track_info.last_played = datetime.now(timezone.utc)
        self.total_tracks_played += 1
        
        # Add to history
        self._history.append(track_info)
        
        return track_info
    
    def peek(self, index: int = 0) -> Optional[TrackInfo]:
        """Peek at track without removing it"""
        try:
            return self._queue[index]
        except IndexError:
            return None
    
    def remove(self, index: int) -> Optional[TrackInfo]:
        """Remove track at specific index"""
        try:
            return self._queue.pop(index)
        except IndexError:
            return None
    
    def remove_by_uri(self, uri: str) -> bool:
        """Remove first occurrence of track by URI"""
        for i, track_info in enumerate(self._queue):
            if track_info.track.uri == uri:
                self._queue.pop(i)
                return True
        return False
    
    def clear(self):
        """Clear all tracks from queue"""
        self._queue.clear()
    
    def move(self, from_index: int, to_index: int) -> bool:
        """Move track from one position to another"""
        try:
            track_info = self._queue.pop(from_index)
            self._queue.insert(to_index, track_info)
            return True
        except IndexError:
            return False
    
    def shuffle(self):
        """Shuffle the current queue"""
        if len(self._queue) > 1:
            # Smart shuffle - ensure good distribution
            high_priority = [t for t in self._queue if t.priority > 0]
            normal_tracks = [t for t in self._queue if t.priority <= 0]
            
            random.shuffle(normal_tracks)
            
            # Combine with high priority tracks at the beginning
            self._queue = high_priority + normal_tracks
            self.shuffle_enabled = True
    
    def toggle_shuffle(self) -> bool:
        """Toggle shuffle mode"""
        self.shuffle_enabled = not self.shuffle_enabled
        if self.shuffle_enabled:
            self.shuffle()
        return self.shuffle_enabled
    
    def set_repeat_mode(self, mode: str) -> str:
        """Set repeat mode: 'off', 'track', 'queue'"""
        if mode in ['off', 'track', 'queue']:
            self.repeat_mode = mode
        return self.repeat_mode
    
    def toggle_repeat(self) -> str:
        """Cycle through repeat modes"""
        modes = ['off', 'track', 'queue']
        current_index = modes.index(self.repeat_mode)
        next_index = (current_index + 1) % len(modes)
        self.repeat_mode = modes[next_index]
        return self.repeat_mode
    
    def get_history(self, limit: int = 10) -> List[TrackInfo]:
        """Get recently played tracks"""
        return list(self._history)[-limit:]
    
    def add_to_favorites(self, uri: str):
        """Mark track as favorite"""
        self._favorites.add(uri)
    
    def remove_from_favorites(self, uri: str):
        """Remove track from favorites"""
        self._favorites.discard(uri)
    
    def is_favorite(self, uri: str) -> bool:
        """Check if track is in favorites"""
        return uri in self._favorites
    
    def get_favorites(self) -> List[str]:
        """Get all favorite track URIs"""
        return list(self._favorites)
    
    def _update_user_preferences(self, user: discord.Member, track: wavelink.Playable):
        """Update user listening preferences"""
        if not user:
            return
        
        user_id = user.id
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {
                'genres': {},
                'artists': {},
                'track_count': 0
            }
        
        prefs = self._user_preferences[user_id]
        prefs['track_count'] += 1
        
        # Update artist preferences
        if hasattr(track, 'author') and track.author:
            artist = track.author.lower()
            prefs['artists'][artist] = prefs['artists'].get(artist, 0) + 1
    
    def _was_recently_played(self, uri: str, recent_count: int = 3) -> bool:
        """Check if track was played recently"""
        recent_uris = [track_info.track.uri for track_info in list(self._history)[-recent_count:]]
        return uri in recent_uris
    
    async def generate_autoplay_suggestions(self, current_track: wavelink.Playable = None, 
                                          limit: int = 5) -> List[wavelink.Playable]:
        """Generate autoplay suggestions based on listening history"""
        if not self.autoplay_enabled:
            return []
        
        try:
            # Use Spotify integration for recommendations if available
            from integrations.spotify import get_spotify_manager
            spotify = get_spotify_manager()
            
            if spotify.is_available() and current_track:
                # Try to get Spotify recommendations
                recommendations = await spotify.get_recommendations(
                    seed_tracks=[current_track.uri] if hasattr(current_track, 'spotify_data') else None,
                    limit=limit
                )
                
                if recommendations:
                    return await spotify.convert_spotify_tracks_to_wavelink(recommendations)
            
            # Fallback: use similar tracks from history
            return await self._get_similar_tracks_from_history(current_track, limit)
            
        except Exception as e:
            logger.error(f"Failed to generate autoplay suggestions: {e}")
            return []
    
    async def _get_similar_tracks_from_history(self, current_track: wavelink.Playable, 
                                             limit: int) -> List[wavelink.Playable]:
        """Get similar tracks from listening history"""
        suggestions = []
        
        if not self._history:
            return suggestions
        
        # Find tracks by same artist
        if hasattr(current_track, 'author') and current_track.author:
            current_artist = current_track.author.lower()
            
            for track_info in self._history:
                if (hasattr(track_info.track, 'author') and 
                    track_info.track.author and
                    track_info.track.author.lower() == current_artist and
                    track_info.track.uri != current_track.uri):
                    
                    if len(suggestions) < limit:
                        suggestions.append(track_info.track)
        
        # Fill remaining slots with popular tracks from history
        popular_tracks = sorted(
            self._history, 
            key=lambda x: x.play_count, 
            reverse=True
        )
        
        for track_info in popular_tracks:
            if (len(suggestions) < limit and 
                track_info.track not in suggestions and
                track_info.track.uri != current_track.uri):
                suggestions.append(track_info.track)
        
        return suggestions
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        if not self._queue:
            return {
                'total_tracks': 0,
                'total_duration': 0,
                'average_duration': 0,
                'requesters': {},
                'genres': {},
                'most_requested_artist': None
            }
        
        total_duration = sum(
            getattr(track_info.track, 'length', 0) for track_info in self._queue
        )
        
        requesters = {}
        artists = {}
        
        for track_info in self._queue:
            # Count requesters
            if track_info.requester:
                requester_name = track_info.requester.display_name
                requesters[requester_name] = requesters.get(requester_name, 0) + 1
            
            # Count artists
            if hasattr(track_info.track, 'author') and track_info.track.author:
                artist = track_info.track.author
                artists[artist] = artists.get(artist, 0) + 1
        
        most_requested_artist = max(artists.items(), key=lambda x: x[1])[0] if artists else None
        
        return {
            'total_tracks': len(self._queue),
            'total_duration': total_duration,
            'average_duration': total_duration // len(self._queue) if self._queue else 0,
            'requesters': requesters,
            'artists': artists,
            'most_requested_artist': most_requested_artist
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert queue to dictionary for persistence"""
        return {
            'guild_id': self.guild_id,
            'queue': [track_info.to_dict() for track_info in self._queue],
            'history': [track_info.to_dict() for track_info in list(self._history)[-20:]],  # Last 20
            'favorites': list(self._favorites),
            'shuffle_enabled': self.shuffle_enabled,
            'repeat_mode': self.repeat_mode,
            'autoplay_enabled': self.autoplay_enabled,
            'user_preferences': self._user_preferences,
            'total_tracks_added': self.total_tracks_added,
            'total_tracks_played': self.total_tracks_played,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    async def from_dict(cls, data: Dict[str, Any], guild: discord.Guild):
        """Create AdvancedQueue from dictionary"""
        queue = cls(data['guild_id'], config.MAX_QUEUE_SIZE)
        
        # Restore settings
        queue.shuffle_enabled = data.get('shuffle_enabled', False)
        queue.repeat_mode = data.get('repeat_mode', 'off')
        queue.autoplay_enabled = data.get('autoplay_enabled', False)
        queue.total_tracks_added = data.get('total_tracks_added', 0)
        queue.total_tracks_played = data.get('total_tracks_played', 0)
        
        if data.get('created_at'):
            queue.created_at = datetime.fromisoformat(data['created_at'])
        
        # Restore favorites
        queue._favorites = set(data.get('favorites', []))
        
        # Restore user preferences
        queue._user_preferences = data.get('user_preferences', {})
        
        # Restore queue tracks
        for track_data in data.get('queue', []):
            track_info = await TrackInfo.from_dict(track_data, guild)
            if track_info:
                queue._queue.append(track_info)
        
        # Restore history
        for track_data in data.get('history', []):
            track_info = await TrackInfo.from_dict(track_data, guild)
            if track_info:
                queue._history.append(track_info)
        
        return queue

class QueueManager:
    """Manages queues for all guilds with persistence"""
    
    def __init__(self):
        self.queues: Dict[int, AdvancedQueue] = {}
        self.persistence_enabled = True
        self.save_interval = 300  # Save every 5 minutes
        self._save_task = None
    
    def get_queue(self, guild_id: int) -> AdvancedQueue:
        """Get or create queue for guild"""
        if guild_id not in self.queues:
            self.queues[guild_id] = AdvancedQueue(guild_id)
        return self.queues[guild_id]
    
    def remove_queue(self, guild_id: int) -> bool:
        """Remove queue for guild"""
        if guild_id in self.queues:
            del self.queues[guild_id]
            return True
        return False
    
    async def save_all_queues(self):
        """Save all queues to database"""
        if not self.persistence_enabled:
            return
        
        try:
            from database.models import db
            
            if not db:
                return
            
            for guild_id, queue in self.queues.items():
                queue_data = queue.to_dict()
                await db.save_daily_statistics(
                    date=datetime.now(timezone.utc).date().isoformat(),
                    guild_id=guild_id,
                    stat_type='queue_state',
                    stat_data=queue_data
                )
            
            logger.info(f"Saved {len(self.queues)} queues to database")
        except Exception as e:
            logger.error(f"Failed to save queues: {e}")
    
    async def load_all_queues(self, bot):
        """Load all queues from database"""
        if not self.persistence_enabled:
            return
        
        try:
            from database.models import db
            
            if not db:
                return
            
            # Get recent queue states for all guilds
            stats = await db.get_statistics('queue_state', days=1)
            
            for stat in stats:
                guild_id = stat['guild_id']
                if guild_id:
                    guild = bot.get_guild(guild_id)
                    if guild:
                        try:
                            queue_data = json.loads(stat['stat_data'])
                            restored_queue = await AdvancedQueue.from_dict(queue_data, guild)
                            self.queues[guild_id] = restored_queue
                            logger.info(f"Restored queue for guild {guild_id} with {len(restored_queue)} tracks")
                        except Exception as e:
                            logger.error(f"Failed to restore queue for guild {guild_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to load queues: {e}")
    
    async def cleanup_guild_data(self, guild_id: int):
        """Clean up guild data when bot leaves a guild"""
        if guild_id in self.queues:
            del self.queues[guild_id]
            logger.info(f"Cleaned up queue data for guild {guild_id}")
    
    def start_persistence_task(self):
        """Start the automatic queue saving task"""
        if self._save_task is None or self._save_task.done():
            self._save_task = asyncio.create_task(self._periodic_save())
    
    def stop_persistence_task(self):
        """Stop the automatic queue saving task"""
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
    
    async def _periodic_save(self):
        """Periodically save queues"""
        while True:
            try:
                await asyncio.sleep(self.save_interval)
                await self.save_all_queues()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic save: {e}")

# Global queue manager instance
queue_manager = QueueManager()

def get_queue_manager() -> QueueManager:
    """Get the global queue manager instance"""
    return queue_manager
