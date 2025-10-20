"""
Enhanced Embed System - Beautiful, consistent embeds with rich information, thumbnails, and progress bars
"""

import discord
import wavelink
from typing import Optional, Dict, List, Union
import datetime
import time
import math
from utils.emoji import *

class EnhancedEmbedBuilder:
    """Advanced embed builder with rich features and consistent styling"""
    
    def __init__(self, bot):
        self.bot = bot
        self.default_colors = {
            'primary': discord.Color.blurple(),
            'success': discord.Color.green(),
            'error': discord.Color.red(),
            'warning': discord.Color.orange(),
            'info': discord.Color.blue(),
            'music': discord.Color.purple(),
            'queue': discord.Color.dark_blue(),
            'radio': discord.Color.gold(),
            'premium': discord.Color.from_rgb(255, 115, 250)  # Pink color similar to Nitro pink
        }
    
    def create_base_embed(self, 
                         title: str, 
                         description: str = None, 
                         color: Union[discord.Color, str] = 'primary',
                         timestamp: bool = True,
                         footer_text: str = None) -> discord.Embed:
        """Create a base embed with consistent styling"""
        
        # Handle color parameter
        if isinstance(color, str):
            embed_color = self.default_colors.get(color, self.default_colors['primary'])
        else:
            embed_color = color
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=embed_color
        )
        
        if timestamp:
            embed.timestamp = datetime.datetime.now()
        
        # Enhanced footer with bot info
        if not footer_text:
            current_time = datetime.datetime.now().strftime("%H:%M")
            footer_text = f"Powered by {self.bot.user.name} • {current_time}"
        
        embed.set_footer(
            text=footer_text,
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        return embed
    
    def create_music_embed(self, 
                          track: wavelink.Playable, 
                          title: str = None,
                          requester: discord.Member = None,
                          show_progress: bool = False,
                          player: wavelink.Player = None) -> discord.Embed:
        """Create a beautiful music embed with rich information"""
        
        embed_title = title or f"{NOW_PLAYING} Now Playing"
        embed = self.create_base_embed(embed_title, color='music')
        
        # Main track information
        embed.description = f"[{track.title}]({track.uri})"
        
        # Duration and progress
        duration = str(datetime.timedelta(seconds=int(track.length / 1000)))
        
        if show_progress and player and player.position:
            current_time = int(player.position / 1000)
            current_formatted = str(datetime.timedelta(seconds=current_time))
            progress_bar = self.create_progress_bar(current_time, int(track.length / 1000))
            
            embed.add_field(
                name="⏱️ Progress",
                value=f"`{current_formatted}` {progress_bar} `{duration}`",
                inline=False
            )
        else:
            embed.add_field(name="⏱️ Duration", value=duration, inline=True)
        
        # Track details
        if hasattr(track, 'author') and track.author:
            embed.add_field(name="🎤 Artist", value=track.author, inline=True)
        
        # Source information
        source = self.get_source_info(track.uri)
        embed.add_field(name="🌐 Source", value=source['name'], inline=True)
        
        if requester:
            embed.add_field(name="👤 Requested by", value=requester.mention, inline=True)
        
        # Enhanced thumbnail with high quality
        thumbnail_url = self.get_high_quality_thumbnail(track)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
            
            # Set large image for YouTube tracks
            if "youtube" in str(track.uri):
                embed.set_image(url=thumbnail_url)
        
        # Add source-specific branding
        if source['color']:
            embed.color = source['color']
        
        return embed
    
    def create_queue_embed(self, 
                          queue_data: Dict,
                          player: wavelink.Player = None,
                          guild: discord.Guild = None,
                          show_detailed: bool = True) -> discord.Embed:
        """Create a comprehensive queue embed"""
        
        embed = self.create_base_embed(f"{QUEUE} Music Queue", color='queue')
        
        # Current track section
        if player and player.current:
            current_track = player.current
            current_duration = str(datetime.timedelta(seconds=int(current_track.length / 1000)))
            
            # Progress bar for current track
            progress_info = ""
            if player.position:
                current_time = int(player.position / 1000)
                current_formatted = str(datetime.timedelta(seconds=current_time))
                progress_bar = self.create_progress_bar(current_time, int(current_track.length / 1000))
                progress_info = f"\n`{current_formatted}` {progress_bar} `{current_duration}`"
            
            embed.add_field(
                name="🎵 Now Playing",
                value=f"[{current_track.title}]({current_track.uri}){progress_info}",
                inline=False
            )
            
            # High quality thumbnail
            thumbnail_url = self.get_high_quality_thumbnail(current_track)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
        
        # Queue information
        if queue_data and queue_data.get('tracks'):
            tracks = queue_data['tracks']
            total_duration = queue_data.get('total_duration', 0)
            total_formatted = str(datetime.timedelta(seconds=int(total_duration / 1000)))
            
            # Queue list with enhanced formatting
            queue_text = ""
            for i, track_info in enumerate(tracks[:8], 1):  # Show first 8 tracks
                track = track_info.get('track')
                requester = track_info.get('requester')
                
                if not track:
                    continue
                
                duration = str(datetime.timedelta(seconds=int(getattr(track, 'length', 0) / 1000)))
                requester_name = requester.display_name if requester else "Unknown"
                
                # Add source emoji
                source_emoji = self.get_source_emoji(track.uri)
                
                queue_text += f"`{i:2d}.` {source_emoji} [{track.title[:45]}]({track.uri})\n"
                queue_text += f"      ⏱️ `{duration}` • 👤 {requester_name}\n\n"
            
            remaining = len(tracks) - 8 if len(tracks) > 8 else 0
            if remaining > 0:
                queue_text += f"*... and {remaining} more tracks*\n"
            
            embed.add_field(
                name=f"📋 Up Next • {len(tracks)} tracks • {total_formatted}",
                value=queue_text or "No tracks in queue",
                inline=False
            )
        
        # Queue status and settings
        status_items = []
        
        if queue_data.get('repeat_mode', 'off') != 'off':
            repeat_emoji = "🔂" if queue_data['repeat_mode'] == 'track' else "🔁"
            status_items.append(f"{repeat_emoji} Repeat: {queue_data['repeat_mode'].title()}")
        
        if queue_data.get('shuffle_enabled'):
            status_items.append(f"{SHUFFLE} Shuffle enabled")
        
        if queue_data.get('autoplay_enabled'):
            status_items.append("📻 Radio mode")
        
        if player:
            if player.paused:
                status_items.append(f"{PAUSE} Paused")
            
            volume = int(player.volume * 100)
            if volume != 100:
                volume_emoji = VOLUME_MUTE if volume == 0 else VOLUME_DOWN if volume < 50 else VOLUME_UP
                status_items.append(f"{volume_emoji} Volume: {volume}%")
        
        if status_items:
            embed.add_field(
                name="⚙️ Queue Settings",
                value=" • ".join(status_items),
                inline=False
            )
        
        return embed
    
    def create_error_embed(self, 
                          title: str, 
                          description: str,
                          error_type: str = "general") -> discord.Embed:
        """Create a standardized error embed"""
        
        error_emojis = {
            "permission": "🚫",
            "not_found": "🔍",
            "connection": "🔌",
            "timeout": "⏰",
            "invalid": "❌",
            "general": "⚠️"
        }
        
        emoji = error_emojis.get(error_type, "❌")
        embed = self.create_base_embed(f"{emoji} {title}", description, color='error')
        
        return embed
    
    def create_success_embed(self, 
                           title: str, 
                           description: str) -> discord.Embed:
        """Create a standardized success embed"""
        
        embed = self.create_base_embed(f"✅ {title}", description, color='success')
        return embed
    
    def create_info_embed(self, 
                         title: str, 
                         description: str,
                         info_type: str = "general") -> discord.Embed:
        """Create an informational embed"""
        
        info_emojis = {
            "stats": "📊",
            "help": "❓",
            "settings": "⚙️",
            "update": "🔄",
            "general": "ℹ️"
        }
        
        emoji = info_emojis.get(info_type, "ℹ️")
        embed = self.create_base_embed(f"{emoji} {title}", description, color='info')
        
        return embed
    
    def create_radio_embed(self, 
                          station_info: Dict,
                          status: str = "playing") -> discord.Embed:
        """Create a radio station embed"""
        
        status_emojis = {
            "playing": "📻",
            "loading": "⏳",
            "stopped": "⏹️",
            "error": "❌"
        }
        
        emoji = status_emojis.get(status, "📻")
        embed = self.create_base_embed(f"{emoji} Radio Station", color='radio')
        
        embed.add_field(
            name="🎵 Station",
            value=f"{station_info.get('emoji', '📻')} **{station_info.get('name', 'Unknown')}**",
            inline=True
        )
        
        embed.add_field(
            name="🎧 Genre",
            value=station_info.get('genre', 'Various'),
            inline=True
        )
        
        embed.add_field(
            name="📡 Status",
            value=status.title(),
            inline=True
        )
        
        # Add radio wave animation effect in description
        embed.description = "🌊 **Streaming live 24/7** 🌊"
        
        return embed
    
    def create_progress_bar(self, 
                           current: int, 
                           total: int, 
                           length: int = 12,
                           filled_char: str = "▰",
                           empty_char: str = "▱") -> str:
        """Create a visual progress bar"""
        
        if total <= 0:
            return f"{empty_char * length}"
        
        filled_length = int((current / total) * length)
        filled_length = max(0, min(length, filled_length))
        
        progress = filled_char * filled_length + empty_char * (length - filled_length)
        return progress
    
    def get_high_quality_thumbnail(self, track: wavelink.Playable) -> Optional[str]:
        """Get the highest quality thumbnail available"""
        
        if not track or not track.uri:
            return None
        
        uri = str(track.uri)
        
        # YouTube thumbnail extraction
        if "youtube.com" in uri or "youtu.be" in uri:
            video_id = None
            
            if "youtube.com" in uri:
                if "v=" in uri:
                    video_id = uri.split("v=")[1].split("&")[0]
            elif "youtu.be" in uri:
                video_id = uri.split("/")[-1].split("?")[0]
            
            if video_id:
                # Try different quality options
                quality_options = [
                    f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                    f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                ]
                return quality_options[0]  # Return highest quality
        
        # SoundCloud or other sources
        if hasattr(track, 'artwork_url') and track.artwork_url:
            return track.artwork_url
        
        return None
    
    def get_source_info(self, uri: str) -> Dict:
        """Get source information and branding"""
        
        uri = str(uri).lower()
        
        if "youtube" in uri:
            return {
                'name': 'YouTube',
                'emoji': '📺',
                'color': discord.Color.red()
            }
        elif "soundcloud" in uri:
            return {
                'name': 'SoundCloud',
                'emoji': '☁️',
                'color': discord.Color.orange()
            }
        elif "spotify" in uri:
            return {
                'name': 'Spotify',
                'emoji': '🎵',
                'color': discord.Color.green()
            }
        elif "twitch" in uri:
            return {
                'name': 'Twitch',
                'emoji': '📺',
                'color': discord.Color.purple()
            }
        else:
            return {
                'name': 'Unknown Source',
                'emoji': '🌐',
                'color': None
            }
    
    def get_source_emoji(self, uri: str) -> str:
        """Get emoji for source"""
        return self.get_source_info(uri)['emoji']
    
    def add_field_with_limit(self, 
                            embed: discord.Embed, 
                            name: str, 
                            value: str, 
                            inline: bool = False,
                            max_length: int = 1024) -> discord.Embed:
        """Add field with character limit handling"""
        
        if len(value) > max_length:
            value = value[:max_length-3] + "..."
        
        embed.add_field(name=name, value=value, inline=inline)
        return embed
    
    def create_paginated_embed_list(self, 
                                   items: List,
                                   title: str,
                                   items_per_page: int = 10,
                                   formatter_func = None) -> List[discord.Embed]:
        """Create a list of paginated embeds"""
        
        embeds = []
        total_pages = math.ceil(len(items) / items_per_page)
        
        for page in range(total_pages):
            start_idx = page * items_per_page
            end_idx = min(start_idx + items_per_page, len(items))
            page_items = items[start_idx:end_idx]
            
            embed = self.create_base_embed(f"{title} (Page {page + 1}/{total_pages})")
            
            if formatter_func:
                for item in page_items:
                    formatted = formatter_func(item)
                    embed.add_field(
                        name=formatted['name'],
                        value=formatted['value'],
                        inline=formatted.get('inline', False)
                    )
            else:
                # Default formatting
                item_text = "\n".join([f"{i+1+start_idx}. {item}" for i, item in enumerate(page_items)])
                embed.description = item_text
            
            embeds.append(embed)
        
        return embeds


# Global instance
def get_embed_builder(bot) -> EnhancedEmbedBuilder:
    """Get a global embed builder instance"""
    if not hasattr(bot, '_embed_builder'):
        bot._embed_builder = EnhancedEmbedBuilder(bot)
    return bot._embed_builder


# Convenience functions for quick embed creation
def create_music_embed(bot, track: wavelink.Playable, **kwargs) -> discord.Embed:
    """Quick function to create a music embed"""
    builder = get_embed_builder(bot)
    return builder.create_music_embed(track, **kwargs)

def create_error_embed(bot, title: str, description: str, **kwargs) -> discord.Embed:
    """Quick function to create an error embed"""
    builder = get_embed_builder(bot)
    return builder.create_error_embed(title, description, **kwargs)

def create_success_embed(bot, title: str, description: str) -> discord.Embed:
    """Quick function to create a success embed"""
    builder = get_embed_builder(bot)
    return builder.create_success_embed(title, description)
