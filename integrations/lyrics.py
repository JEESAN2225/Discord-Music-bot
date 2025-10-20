"""
Lyrics integration for the advanced music bot
Fetches and displays song lyrics using Genius API
"""

import lyricsgenius
import discord
import re
import asyncio
from typing import Optional, Dict, List
import logging
from config.config import config

logger = logging.getLogger(__name__)

class LyricsManager:
    """Manages lyrics fetching and display"""
    
    def __init__(self):
        self.genius_token = config.GENIUS_API_TOKEN
        self.genius = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Genius client"""
        if not self.genius_token:
            logger.warning("Genius API token not found. Lyrics features will be disabled.")
            return
        
        try:
            self.genius = lyricsgenius.Genius(
                self.genius_token,
                skip_non_songs=True,
                excluded_terms=["(Remix)", "(Live)"],
                remove_section_headers=True,
                timeout=15,
                sleep_time=0.5
            )
            logger.info("Genius client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Genius client: {e}")
    
    def is_available(self) -> bool:
        """Check if lyrics integration is available"""
        return self.genius is not None and config.ENABLE_LYRICS
    
    async def search_song_lyrics(self, title: str, artist: str = None) -> Optional[Dict]:
        """Search for song lyrics on Genius"""
        if not self.is_available():
            return None
        
        try:
            # Clean up the search query
            search_query = self._clean_search_query(title, artist)
            
            # Search for the song
            song = await asyncio.to_thread(self.genius.search_song, search_query)
            
            if not song:
                return None
            
            # Extract and clean lyrics
            lyrics = self._clean_lyrics(song.lyrics)
            
            return {
                'title': song.title,
                'artist': song.artist,
                'album': getattr(song, 'album', None),
                'lyrics': lyrics,
                'url': song.url,
                'thumbnail': song.song_art_image_thumbnail_url,
                'genius_id': song.id,
                'release_date': getattr(song, 'release_date_for_display', None),
                'pageviews': getattr(song, 'stats', {}).get('pageviews', 0),
                'genius_data': {
                    'primary_artist': song.primary_artist.name if song.primary_artist else artist,
                    'featured_artists': [artist.name for artist in song.featured_artists] if hasattr(song, 'featured_artists') else [],
                    'producer_artists': [artist.name for artist in song.producer_artists] if hasattr(song, 'producer_artists') else [],
                    'writer_artists': [artist.name for artist in song.writer_artists] if hasattr(song, 'writer_artists') else []
                }
            }
        except Exception as e:
            logger.error(f"Failed to fetch lyrics for '{title}' by '{artist}': {e}")
            return None
    
    async def get_song_by_id(self, genius_id: int) -> Optional[Dict]:
        """Get song info by Genius ID"""
        if not self.is_available():
            return None
        
        try:
            song = await asyncio.to_thread(self.genius.song, genius_id)
            
            if not song:
                return None
            
            lyrics = self._clean_lyrics(song.lyrics)
            
            return {
                'title': song.title,
                'artist': song.artist,
                'lyrics': lyrics,
                'url': song.url,
                'thumbnail': song.song_art_image_thumbnail_url,
                'genius_id': song.id,
                'pageviews': getattr(song, 'stats', {}).get('pageviews', 0)
            }
        except Exception as e:
            logger.error(f"Failed to fetch song with ID {genius_id}: {e}")
            return None
    
    def _clean_search_query(self, title: str, artist: str = None) -> str:
        """Clean up search query for better results"""
        # Remove common suffixes and prefixes that might interfere with search
        cleanup_patterns = [
            r'\(.*?\)',  # Remove parentheses content
            r'\[.*?\]',  # Remove brackets content
            r'\s*-\s*.*$',  # Remove everything after dash
            r'\s*(feat|ft|featuring)\.?\s+.*$',  # Remove featuring information
            r'\s*(remix|mix|edit|version).*$',  # Remove remix/version info
            r'\s*(official|music|video|audio).*$',  # Remove official/video tags
            r'\s*\d{4}.*$',  # Remove year at the end
            r'[^\w\s]',  # Remove special characters except spaces
        ]
        
        cleaned_title = title
        for pattern in cleanup_patterns:
            cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE)
        
        cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
        
        if artist:
            cleaned_artist = re.sub(r'[^\w\s]', '', artist)
            cleaned_artist = re.sub(r'\s+', ' ', cleaned_artist).strip()
            return f"{cleaned_title} {cleaned_artist}"
        
        return cleaned_title
    
    def _clean_lyrics(self, raw_lyrics: str) -> str:
        """Clean up the lyrics text"""
        if not raw_lyrics:
            return "No lyrics available"
        
        # Remove Genius metadata
        lyrics = re.sub(r'^.*?Lyrics', '', raw_lyrics, flags=re.DOTALL)
        lyrics = re.sub(r'\d+Embed$', '', lyrics)
        
        # Remove excessive whitespace
        lyrics = re.sub(r'\n\s*\n\s*\n', '\n\n', lyrics)
        lyrics = re.sub(r'^\s+|\s+$', '', lyrics, flags=re.MULTILINE)
        
        # Remove empty lines at start/end
        lyrics = lyrics.strip()
        
        return lyrics if lyrics else "No lyrics available"
    
    def create_lyrics_embed(self, lyrics_data: Dict, page: int = 1, 
                           max_length: int = 4000) -> List[discord.Embed]:
        """Create embed(s) for displaying lyrics"""
        embeds = []
        lyrics = lyrics_data['lyrics']
        
        if not lyrics or lyrics == "No lyrics available":
            embed = discord.Embed(
                title="❌ No Lyrics Found",
                description=f"Sorry, I couldn't find lyrics for **{lyrics_data.get('title', 'Unknown')}**",
                color=discord.Color.red()
            )
            return [embed]
        
        # Split lyrics into chunks that fit Discord's embed limits
        chunks = self._split_lyrics(lyrics, max_length)
        
        for i, chunk in enumerate(chunks, 1):
            embed = discord.Embed(
                title=f"🎵 {lyrics_data['title']}" + (f" (Page {i}/{len(chunks)})" if len(chunks) > 1 else ""),
                description=f"**{lyrics_data['artist']}**",
                color=0xFFFF00,  # Genius yellow
                url=lyrics_data.get('url', '')
            )
            
            embed.add_field(
                name="Lyrics",
                value=f"```{chunk}```" if len(chunk) < 1000 else chunk,
                inline=False
            )
            
            if i == 1:  # Only add metadata to first page
                if lyrics_data.get('album'):
                    embed.add_field(name="Album", value=lyrics_data['album'], inline=True)
                
                if lyrics_data.get('release_date'):
                    embed.add_field(name="Release Date", value=lyrics_data['release_date'], inline=True)
                
                if lyrics_data.get('pageviews'):
                    embed.add_field(name="Views on Genius", value=f"{lyrics_data['pageviews']:,}", inline=True)
                
                # Add artist information
                genius_data = lyrics_data.get('genius_data', {})
                if genius_data.get('featured_artists'):
                    embed.add_field(
                        name="Featured Artists",
                        value=", ".join(genius_data['featured_artists']),
                        inline=False
                    )
                
                if genius_data.get('producer_artists'):
                    embed.add_field(
                        name="Producers",
                        value=", ".join(genius_data['producer_artists']),
                        inline=False
                    )
            
            if lyrics_data.get('thumbnail'):
                embed.set_thumbnail(url=lyrics_data['thumbnail'])
            
            embed.set_footer(
                text=f"Powered by Genius • Page {i}/{len(chunks)}" if len(chunks) > 1 else "Powered by Genius",
                icon_url="https://genius.com/static/images/apple-touch-icon.png"
            )
            
            embeds.append(embed)
        
        return embeds
    
    def _split_lyrics(self, lyrics: str, max_length: int) -> List[str]:
        """Split lyrics into chunks that fit Discord embeds"""
        if len(lyrics) <= max_length:
            return [lyrics]
        
        chunks = []
        current_chunk = ""
        lines = lyrics.split('\n')
        
        for line in lines:
            # If adding this line would exceed the limit
            if len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = line + '\n'
                else:
                    # Line itself is too long, split it
                    while len(line) > max_length:
                        chunks.append(line[:max_length])
                        line = line[max_length:]
                    current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def search_artist_songs(self, artist_name: str, limit: int = 10) -> List[Dict]:
        """Search for songs by an artist"""
        if not self.is_available():
            return []
        
        try:
            artist = await asyncio.to_thread(self.genius.search_artist, artist_name, max_songs=limit)
            
            if not artist:
                return []
            
            songs = []
            for song in artist.songs:
                songs.append({
                    'title': song.title,
                    'artist': song.artist,
                    'url': song.url,
                    'genius_id': song.id,
                    'thumbnail': song.song_art_image_thumbnail_url,
                    'pageviews': getattr(song, 'stats', {}).get('pageviews', 0)
                })
            
            return songs
        except Exception as e:
            logger.error(f"Failed to search artist songs for '{artist_name}': {e}")
            return []
    
    def create_search_results_embed(self, songs: List[Dict], artist_name: str) -> discord.Embed:
        """Create embed for artist song search results"""
        embed = discord.Embed(
            title=f"🎤 Songs by {artist_name}",
            color=0xFFFF00,
            description=f"Found {len(songs)} songs"
        )
        
        songs_text = ""
        for i, song in enumerate(songs[:10], 1):  # Limit to 10 songs to fit in embed
            pageviews = f"{song['pageviews']:,}" if song['pageviews'] else "N/A"
            songs_text += f"`{i}.` [{song['title']}]({song['url']}) - {pageviews} views\n"
        
        embed.add_field(name="Popular Songs", value=songs_text or "No songs found", inline=False)
        embed.set_footer(text="Powered by Genius", icon_url="https://genius.com/static/images/apple-touch-icon.png")
        
        return embed

class LyricsView(discord.ui.View):
    """Discord UI View for lyrics pagination"""
    
    def __init__(self, lyrics_embeds: List[discord.Embed], *, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.lyrics_embeds = lyrics_embeds
        self.current_page = 0
        
        # Disable buttons if only one page
        if len(lyrics_embeds) <= 1:
            self.previous_page.disabled = True
            self.next_page.disabled = True
    
    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page - 1) % len(self.lyrics_embeds)
        await interaction.response.edit_message(embed=self.lyrics_embeds[self.current_page], view=self)
    
    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = (self.current_page + 1) % len(self.lyrics_embeds)
        await interaction.response.edit_message(embed=self.lyrics_embeds[self.current_page], view=self)
    
    @discord.ui.button(emoji="🔗", style=discord.ButtonStyle.secondary, label="Open on Genius")
    async def open_genius(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.lyrics_embeds[0]  # First embed always has the URL
        if embed.url:
            await interaction.response.send_message(f"🔗 Open on Genius: {embed.url}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No Genius URL available", ephemeral=True)

# Global lyrics manager instance
lyrics_manager = LyricsManager()

def get_lyrics_manager() -> LyricsManager:
    """Get the global lyrics manager instance"""
    return lyrics_manager
