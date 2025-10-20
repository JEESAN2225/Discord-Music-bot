"""
Spotify integration for the advanced music bot
Provides playlist imports, track searching, and rich metadata
"""

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import wavelink
import discord
from typing import List, Dict, Optional, Any, Tuple
import logging
import asyncio
import re
from config.config import config

logger = logging.getLogger(__name__)

class SpotifyManager:
    """Manages Spotify API integration"""
    
    def __init__(self):
        self.client_id = config.SPOTIFY_CLIENT_ID
        self.client_secret = config.SPOTIFY_CLIENT_SECRET
        self.spotify = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Spotify client"""
        if not self.client_id or not self.client_secret:
            logger.warning("Spotify credentials not found. Spotify features will be disabled.")
            return
        
        try:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self.spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            logger.info("Spotify client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {e}")
    
    def is_available(self) -> bool:
        """Check if Spotify integration is available"""
        return self.spotify is not None and config.ENABLE_SPOTIFY
    
    def extract_spotify_id(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract Spotify ID and type from URL"""
        patterns = {
            'track': r'spotify:track:([a-zA-Z0-9]+)|open\.spotify\.com/track/([a-zA-Z0-9]+)',
            'playlist': r'spotify:playlist:([a-zA-Z0-9]+)|open\.spotify\.com/playlist/([a-zA-Z0-9]+)',
            'album': r'spotify:album:([a-zA-Z0-9]+)|open\.spotify\.com/album/([a-zA-Z0-9]+)',
            'artist': r'spotify:artist:([a-zA-Z0-9]+)|open\.spotify\.com/artist/([a-zA-Z0-9]+)'
        }
        
        for spotify_type, pattern in patterns.items():
            match = re.search(pattern, url)
            if match:
                spotify_id = match.group(1) or match.group(2)
                return spotify_id, spotify_type
        
        return None, None
    
    async def get_track_info(self, track_id: str) -> Optional[Dict]:
        """Get detailed track information from Spotify"""
        if not self.is_available():
            return None
        
        try:
            track = await asyncio.to_thread(self.spotify.track, track_id)
            
            return {
                'id': track['id'],
                'name': track['name'],
                'artists': [artist['name'] for artist in track['artists']],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'duration_ms': track['duration_ms'],
                'duration': track['duration_ms'] // 1000,
                'popularity': track['popularity'],
                'explicit': track['explicit'],
                'preview_url': track['preview_url'],
                'external_urls': track['external_urls'],
                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'release_date': track['album']['release_date'],
                'spotify_url': track['external_urls']['spotify']
            }
        except Exception as e:
            logger.error(f"Failed to get Spotify track info: {e}")
            return None
    
    async def get_playlist_info(self, playlist_id: str) -> Optional[Dict]:
        """Get playlist information from Spotify"""
        if not self.is_available():
            return None
        
        try:
            playlist = await asyncio.to_thread(self.spotify.playlist, playlist_id)
            
            return {
                'id': playlist['id'],
                'name': playlist['name'],
                'description': playlist['description'],
                'owner': playlist['owner']['display_name'],
                'owner_id': playlist['owner']['id'],
                'track_count': playlist['tracks']['total'],
                'image_url': playlist['images'][0]['url'] if playlist['images'] else None,
                'external_urls': playlist['external_urls'],
                'spotify_url': playlist['external_urls']['spotify'],
                'public': playlist['public'],
                'collaborative': playlist['collaborative']
            }
        except Exception as e:
            logger.error(f"Failed to get Spotify playlist info: {e}")
            return None
    
    async def get_playlist_tracks(self, playlist_id: str, limit: int = 100) -> List[Dict]:
        """Get all tracks from a Spotify playlist"""
        if not self.is_available():
            return []
        
        try:
            tracks = []
            offset = 0
            
            while True:
                batch = await asyncio.to_thread(
                    self.spotify.playlist_tracks,
                    playlist_id,
                    limit=min(limit - len(tracks), 100),
                    offset=offset
                )
                
                for item in batch['items']:
                    if item['track'] and item['track']['id']:
                        track = item['track']
                        tracks.append({
                            'id': track['id'],
                            'name': track['name'],
                            'artists': [artist['name'] for artist in track['artists']],
                            'artist': ', '.join([artist['name'] for artist in track['artists']]),
                            'album': track['album']['name'],
                            'duration_ms': track['duration_ms'],
                            'duration': track['duration_ms'] // 1000,
                            'popularity': track['popularity'],
                            'explicit': track['explicit'],
                            'preview_url': track['preview_url'],
                            'external_urls': track['external_urls'],
                            'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                            'spotify_url': track['external_urls']['spotify'],
                            'search_query': f"{track['name']} {', '.join([artist['name'] for artist in track['artists']])}"
                        })
                
                if len(batch['items']) < 100 or len(tracks) >= limit:
                    break
                
                offset += 100
            
            return tracks
        except Exception as e:
            logger.error(f"Failed to get Spotify playlist tracks: {e}")
            return []
    
    async def get_album_tracks(self, album_id: str) -> List[Dict]:
        """Get all tracks from a Spotify album"""
        if not self.is_available():
            return []
        
        try:
            album = await asyncio.to_thread(self.spotify.album, album_id)
            tracks = []
            
            for track in album['tracks']['items']:
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'album': album['name'],
                    'duration_ms': track['duration_ms'],
                    'duration': track['duration_ms'] // 1000,
                    'explicit': track['explicit'],
                    'preview_url': track['preview_url'],
                    'external_urls': track['external_urls'],
                    'image_url': album['images'][0]['url'] if album['images'] else None,
                    'spotify_url': track['external_urls']['spotify'],
                    'search_query': f"{track['name']} {', '.join([artist['name'] for artist in track['artists']])}"
                })
            
            return tracks
        except Exception as e:
            logger.error(f"Failed to get Spotify album tracks: {e}")
            return []
    
    async def search_tracks(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for tracks on Spotify"""
        if not self.is_available():
            return []
        
        try:
            results = await asyncio.to_thread(
                self.spotify.search,
                query,
                type='track',
                limit=limit
            )
            
            tracks = []
            for track in results['tracks']['items']:
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'album': track['album']['name'],
                    'duration_ms': track['duration_ms'],
                    'duration': track['duration_ms'] // 1000,
                    'popularity': track['popularity'],
                    'explicit': track['explicit'],
                    'preview_url': track['preview_url'],
                    'external_urls': track['external_urls'],
                    'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'spotify_url': track['external_urls']['spotify'],
                    'search_query': f"{track['name']} {', '.join([artist['name'] for artist in track['artists']])}"
                })
            
            return tracks
        except Exception as e:
            logger.error(f"Failed to search Spotify tracks: {e}")
            return []
    
    async def get_artist_top_tracks(self, artist_id: str, country: str = 'US') -> List[Dict]:
        """Get top tracks for an artist"""
        if not self.is_available():
            return []
        
        try:
            results = await asyncio.to_thread(
                self.spotify.artist_top_tracks,
                artist_id,
                country=country
            )
            
            tracks = []
            for track in results['tracks']:
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'album': track['album']['name'],
                    'duration_ms': track['duration_ms'],
                    'duration': track['duration_ms'] // 1000,
                    'popularity': track['popularity'],
                    'explicit': track['explicit'],
                    'preview_url': track['preview_url'],
                    'external_urls': track['external_urls'],
                    'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'spotify_url': track['external_urls']['spotify'],
                    'search_query': f"{track['name']} {', '.join([artist['name'] for artist in track['artists']])}"
                })
            
            return tracks
        except Exception as e:
            logger.error(f"Failed to get artist top tracks: {e}")
            return []
    
    async def get_recommendations(self, seed_tracks: List[str] = None, 
                                seed_artists: List[str] = None,
                                seed_genres: List[str] = None,
                                limit: int = 20, **kwargs) -> List[Dict]:
        """Get track recommendations from Spotify"""
        if not self.is_available():
            return []
        
        try:
            recommendations = await asyncio.to_thread(
                self.spotify.recommendations,
                seed_tracks=seed_tracks,
                seed_artists=seed_artists,
                seed_genres=seed_genres,
                limit=limit,
                **kwargs
            )
            
            tracks = []
            for track in recommendations['tracks']:
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'album': track['album']['name'],
                    'duration_ms': track['duration_ms'],
                    'duration': track['duration_ms'] // 1000,
                    'popularity': track['popularity'],
                    'explicit': track['explicit'],
                    'preview_url': track['preview_url'],
                    'external_urls': track['external_urls'],
                    'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'spotify_url': track['external_urls']['spotify'],
                    'search_query': f"{track['name']} {', '.join([artist['name'] for artist in track['artists']])}"
                })
            
            return tracks
        except Exception as e:
            logger.error(f"Failed to get Spotify recommendations: {e}")
            return []
    
    async def get_available_genres(self) -> List[str]:
        """Get available genre seeds for recommendations"""
        if not self.is_available():
            return []
        
        try:
            genres = await asyncio.to_thread(
                self.spotify.recommendation_genre_seeds
            )
            return genres['genres']
        except Exception as e:
            logger.error(f"Failed to get available genres: {e}")
            return []
    
    async def convert_spotify_tracks_to_wavelink(self, spotify_tracks: List[Dict]) -> List[wavelink.Playable]:
        """Convert Spotify tracks to Wavelink playable tracks by searching"""
        wavelink_tracks = []
        
        for spotify_track in spotify_tracks:
            try:
                search_results = await wavelink.Playable.search(spotify_track['search_query'])
                if search_results:
                    track = search_results[0]
                    # Add Spotify metadata to the track
                    if not hasattr(track, 'spotify_data'):
                        track.spotify_data = spotify_track
                    wavelink_tracks.append(track)
            except Exception as e:
                logger.error(f"Failed to convert Spotify track {spotify_track.get('name', 'Unknown')}: {e}")
                continue
        
        return wavelink_tracks
    
    def create_spotify_embed(self, spotify_data: Dict, embed_type: str = "track") -> discord.Embed:
        """Create a rich embed with Spotify data"""
        if embed_type == "track":
            embed = discord.Embed(
                title=f"🎵 {spotify_data['name']}",
                description=f"by **{spotify_data['artist']}**",
                color=0x1DB954,  # Spotify green
                url=spotify_data['spotify_url']
            )
            
            embed.add_field(name="Album", value=spotify_data['album'], inline=True)
            embed.add_field(
                name="Duration", 
                value=f"{spotify_data['duration'] // 60}:{spotify_data['duration'] % 60:02d}",
                inline=True
            )
            embed.add_field(name="Popularity", value=f"{spotify_data['popularity']}/100", inline=True)
            
            if spotify_data.get('explicit'):
                embed.add_field(name="Content", value="🔞 Explicit", inline=True)
            
            if spotify_data.get('image_url'):
                embed.set_thumbnail(url=spotify_data['image_url'])
            
        elif embed_type == "playlist":
            embed = discord.Embed(
                title=f"📋 {spotify_data['name']}",
                description=spotify_data.get('description', 'No description'),
                color=0x1DB954,
                url=spotify_data['spotify_url']
            )
            
            embed.add_field(name="Owner", value=spotify_data['owner'], inline=True)
            embed.add_field(name="Tracks", value=spotify_data['track_count'], inline=True)
            embed.add_field(
                name="Type", 
                value="Public" if spotify_data['public'] else "Private",
                inline=True
            )
            
            if spotify_data.get('image_url'):
                embed.set_thumbnail(url=spotify_data['image_url'])
        
        embed.set_footer(text="Powered by Spotify", icon_url="https://cdn.iconscout.com/icon/free/png-256/spotify-11-432546.png")
        return embed

# Global Spotify manager instance
spotify_manager = SpotifyManager()

def get_spotify_manager() -> SpotifyManager:
    """Get the global Spotify manager instance"""
    return spotify_manager
