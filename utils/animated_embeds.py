"""
Animated Embeds System - Dynamic embeds with animations, progress bars, and visual effects
"""

import discord
import asyncio
import datetime
import random
import time
from typing import List, Dict, Optional, Any, Callable
from utils.emoji import *

class AnimationFrames:
    """Collection of animation frames for various effects"""
    
    # Loading animations
    LOADING_DOTS = ["⏳", "⌛"]
    LOADING_SPINNER = ["◐", "◓", "◑", "◒"]
    LOADING_BARS = ["▱▱▱▱▱", "▰▱▱▱▱", "▰▰▱▱▱", "▰▰▰▱▱", "▰▰▰▰▱", "▰▰▰▰▰"]
    LOADING_ARROWS = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"]
    LOADING_PULSE = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
    
    # Music visualizer
    MUSIC_BARS = [
        "▁▂▃▄▅▆▇█",
        "▂▃▄▅▆▇█▁",
        "▃▄▅▆▇█▁▂",
        "▄▅▆▇█▁▂▃",
        "▅▆▇█▁▂▃▄",
        "▆▇█▁▂▃▄▅",
        "▇█▁▂▃▄▅▆",
        "█▁▂▃▄▅▆▇"
    ]
    
    # Progress animations
    PROGRESS_FRAMES = [
        "▰▱▱▱▱▱▱▱▱▱",
        "▰▰▱▱▱▱▱▱▱▱",
        "▰▰▰▱▱▱▱▱▱▱",
        "▰▰▰▰▱▱▱▱▱▱",
        "▰▰▰▰▰▱▱▱▱▱",
        "▰▰▰▰▰▰▱▱▱▱",
        "▰▰▰▰▰▰▰▱▱▱",
        "▰▰▰▰▰▰▰▰▱▱",
        "▰▰▰▰▰▰▰▰▰▱",
        "▰▰▰▰▰▰▰▰▰▰"
    ]
    
    # Wave animations
    WAVE_FRAMES = [
        "🌊                    ",
        " 🌊                   ",
        "  🌊                  ",
        "   🌊                 ",
        "    🌊                ",
        "     🌊               ",
        "      🌊              ",
        "       🌊             ",
        "        🌊            ",
        "         🌊           ",
        "          🌊          ",
        "           🌊         ",
        "            🌊        ",
        "             🌊       ",
        "              🌊      ",
        "               🌊     ",
        "                🌊    ",
        "                 🌊   ",
        "                  🌊  ",
        "                   🌊 ",
        "                    🌊"
    ]
    
    # Heart beat animation
    HEARTBEAT_FRAMES = ["💙", "💚", "💛", "🧡", "❤️", "💜"]
    
    # Fire animation
    FIRE_FRAMES = ["🔥", "🔥🔥", "🔥🔥🔥", "🔥🔥", "🔥"]

class AnimatedEmbed:
    """Animated embed with dynamic content updates"""
    
    def __init__(self, bot, message: discord.Message = None):
        self.bot = bot
        self.message = message
        self.is_animating = False
        self.animation_task = None
        self.frame_index = 0
        self.animation_speed = 1.0  # seconds between frames
        self.callbacks = []
        
    async def start_animation(self, animation_func: Callable, duration: float = 30.0):
        """Start an animation that runs for a specific duration"""
        if self.is_animating:
            await self.stop_animation()
        
        self.is_animating = True
        self.frame_index = 0
        
        try:
            self.animation_task = asyncio.create_task(
                self._animation_loop(animation_func, duration)
            )
            await self.animation_task
        except asyncio.CancelledError:
            pass
        finally:
            self.is_animating = False
    
    async def _animation_loop(self, animation_func: Callable, duration: float):
        """Main animation loop"""
        start_time = time.time()
        
        while time.time() - start_time < duration and self.is_animating:
            try:
                if self.message:
                    embed = await animation_func(self.frame_index)
                    await self.message.edit(embed=embed)
                    
                    # Execute callbacks
                    for callback in self.callbacks:
                        await callback(self.frame_index)
                
                self.frame_index += 1
                await asyncio.sleep(self.animation_speed)
                
            except discord.NotFound:
                # Message was deleted
                break
            except Exception as e:
                print(f"Animation error: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    async def stop_animation(self):
        """Stop the current animation"""
        self.is_animating = False
        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass
    
    def add_callback(self, callback: Callable):
        """Add a callback function to execute during animation"""
        self.callbacks.append(callback)

class ProgressBarGenerator:
    """Generate various types of progress bars"""
    
    @staticmethod
    def create_basic_progress(current: float, total: float, length: int = 10, 
                            filled: str = "▰", empty: str = "▱") -> str:
        """Create basic progress bar"""
        if total <= 0:
            return empty * length
        
        filled_length = int((current / total) * length)
        filled_length = max(0, min(length, filled_length))
        
        return filled * filled_length + empty * (length - filled_length)
    
    @staticmethod
    def create_animated_progress(current: float, total: float, frame: int, 
                               length: int = 10) -> str:
        """Create animated progress bar with moving elements"""
        if total <= 0:
            return "▱" * length
        
        filled_length = int((current / total) * length)
        filled_length = max(0, min(length, filled_length))
        
        # Create base progress
        bar = ["▰"] * filled_length + ["▱"] * (length - filled_length)
        
        # Add animation effect at the progress point
        if filled_length < length and filled_length > 0:
            animation_chars = ["▰", "▬", "▰", "▱"]
            bar[filled_length] = animation_chars[frame % len(animation_chars)]
        
        return "".join(bar)
    
    @staticmethod
    def create_gradient_progress(current: float, total: float, length: int = 10) -> str:
        """Create gradient-style progress bar"""
        if total <= 0:
            return "▱" * length
        
        progress = current / total
        filled_length = int(progress * length)
        
        # Gradient characters from empty to full
        gradient = ["▱", "▒", "▓", "█"]
        bar = []
        
        for i in range(length):
            if i < filled_length:
                bar.append("█")
            elif i == filled_length and progress * length % 1 > 0:
                # Partial fill at current position
                partial_index = int((progress * length % 1) * len(gradient))
                bar.append(gradient[min(partial_index, len(gradient) - 1)])
            else:
                bar.append("▱")
        
        return "".join(bar)
    
    @staticmethod
    def create_wave_progress(current: float, total: float, frame: int, 
                           length: int = 10) -> str:
        """Create wave-style animated progress bar"""
        if total <= 0:
            return "▱" * length
        
        progress = current / total
        filled_length = int(progress * length)
        
        # Wave pattern
        wave_chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        bar = []
        
        for i in range(length):
            if i < filled_length:
                # Create wave effect
                wave_height = int(4 + 3 * math.sin((i + frame * 0.5) * 0.5))
                wave_height = max(0, min(len(wave_chars) - 1, wave_height))
                bar.append(wave_chars[wave_height])
            else:
                bar.append("▱")
        
        return "".join(bar)

class EmbedAnimations:
    """Collection of predefined embed animations"""
    
    @staticmethod
    async def loading_animation(frame: int) -> discord.Embed:
        """Loading animation embed"""
        spinner = AnimationFrames.LOADING_SPINNER[frame % len(AnimationFrames.LOADING_SPINNER)]
        dots = "." * ((frame % 4) + 1)
        
        embed = discord.Embed(
            title=f"{spinner} Loading",
            description=f"Please wait{dots}",
            color=discord.Color.blue()
        )
        
        # Add loading bar
        progress = (frame % 20) / 20
        progress_bar = ProgressBarGenerator.create_animated_progress(progress, 1.0, frame)
        embed.add_field(name="Progress", value=f"`{progress_bar}`", inline=False)
        
        return embed
    
    @staticmethod
    async def music_visualizer(frame: int, track_title: str = "Unknown Track") -> discord.Embed:
        """Music visualizer animation"""
        visualizer = AnimationFrames.MUSIC_BARS[frame % len(AnimationFrames.MUSIC_BARS)]
        
        embed = discord.Embed(
            title=f"🎵 Now Playing",
            description=f"**{track_title}**",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🎵 Visualizer",
            value=f"`{visualizer}`",
            inline=False
        )
        
        # Add animated status
        status_emojis = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
        status = status_emojis[frame % len(status_emojis)]
        embed.add_field(name="Status", value=f"{status} Live", inline=True)
        
        return embed
    
    @staticmethod
    async def download_progress(frame: int, current: int, total: int, 
                              filename: str = "track.mp3") -> discord.Embed:
        """Download progress animation"""
        embed = discord.Embed(
            title="📥 Downloading",
            description=f"**{filename}**",
            color=discord.Color.green()
        )
        
        if total > 0:
            progress = current / total
            progress_bar = ProgressBarGenerator.create_gradient_progress(current, total, 15)
            percentage = int(progress * 100)
            
            embed.add_field(
                name="📊 Progress",
                value=f"`{progress_bar}` {percentage}%\n"
                      f"{current}/{total} MB",
                inline=False
            )
            
            # Add download speed simulation
            speed = random.uniform(1.5, 3.2)
            embed.add_field(name="🚀 Speed", value=f"{speed:.1f} MB/s", inline=True)
            
            # ETA calculation
            if progress > 0:
                eta = (total - current) / (speed * 1024 * 1024)  # Rough estimate
                eta_str = str(datetime.timedelta(seconds=int(eta)))
                embed.add_field(name="⏱️ ETA", value=eta_str, inline=True)
        
        return embed
    
    @staticmethod
    async def heartbeat_animation(frame: int) -> discord.Embed:
        """Heartbeat animation for bot status"""
        heart = AnimationFrames.HEARTBEAT_FRAMES[frame % len(AnimationFrames.HEARTBEAT_FRAMES)]
        
        # Simulate heartbeat rhythm
        if frame % 8 in [0, 2]:  # Double beat
            heart = "❤️💓"
        
        embed = discord.Embed(
            title=f"{heart} Bot Status",
            description="System is healthy and running smoothly",
            color=discord.Color.red()
        )
        
        # Add animated stats
        uptime = datetime.datetime.now().strftime("%H:%M:%S")
        embed.add_field(name="⏰ Uptime", value=uptime, inline=True)
        
        # Simulated load
        load = 15 + random.randint(-5, 5)
        embed.add_field(name="📊 CPU", value=f"{load}%", inline=True)
        
        # Memory usage
        memory = 245 + random.randint(-10, 10)
        embed.add_field(name="🧠 Memory", value=f"{memory}MB", inline=True)
        
        return embed
    
    @staticmethod
    async def wave_animation(frame: int) -> discord.Embed:
        """Wave animation embed"""
        wave = AnimationFrames.WAVE_FRAMES[frame % len(AnimationFrames.WAVE_FRAMES)]
        
        embed = discord.Embed(
            title="🌊 Radio Waves",
            description="Broadcasting live music",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📡 Signal",
            value=f"`{wave}`",
            inline=False
        )
        
        # Add frequency info
        frequency = 105.5 + random.uniform(-2.0, 2.0)
        embed.add_field(name="📻 Frequency", value=f"{frequency:.1f} FM", inline=True)
        
        return embed

class InteractiveAnimatedView(discord.ui.View):
    """Interactive view with animated elements"""
    
    def __init__(self, bot, *, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.animated_embed = None
        self.current_animation = None
        
    async def start_with_animation(self, message: discord.Message, animation_type: str = "loading"):
        """Start the view with an animation"""
        self.animated_embed = AnimatedEmbed(self.bot, message)
        
        if animation_type == "loading":
            await self.animated_embed.start_animation(EmbedAnimations.loading_animation, 10.0)
        elif animation_type == "music":
            animation_func = lambda frame: EmbedAnimations.music_visualizer(frame, "Demo Track")
            await self.animated_embed.start_animation(animation_func, 15.0)
        elif animation_type == "heartbeat":
            await self.animated_embed.start_animation(EmbedAnimations.heartbeat_animation, 20.0)
        elif animation_type == "wave":
            await self.animated_embed.start_animation(EmbedAnimations.wave_animation, 12.0)
    
    @discord.ui.button(emoji="🔄", label="Restart Animation", style=discord.ButtonStyle.secondary)
    async def restart_animation(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.animated_embed:
            await self.animated_embed.stop_animation()
            await self.start_with_animation(interaction.message, "loading")
        
        await interaction.response.send_message("🔄 Animation restarted!", ephemeral=True)
    
    @discord.ui.button(emoji="⏹️", label="Stop Animation", style=discord.ButtonStyle.danger)
    async def stop_animation(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.animated_embed:
            await self.animated_embed.stop_animation()
            
            # Show final static embed
            final_embed = discord.Embed(
                title="⏹️ Animation Stopped",
                description="Animation has been stopped",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=final_embed, view=self)
        else:
            await interaction.response.send_message("❌ No animation running!", ephemeral=True)
    
    @discord.ui.button(emoji="🎵", label="Music Visualizer", style=discord.ButtonStyle.primary)
    async def music_visualizer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.animated_embed:
            await self.animated_embed.stop_animation()
            animation_func = lambda frame: EmbedAnimations.music_visualizer(frame, "Animated Track")
            await self.animated_embed.start_animation(animation_func, 15.0)
        
        await interaction.response.send_message("🎵 Music visualizer started!", ephemeral=True)
    
    @discord.ui.button(emoji="❤️", label="Heartbeat", style=discord.ButtonStyle.secondary)
    async def heartbeat(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.animated_embed:
            await self.animated_embed.stop_animation()
            await self.animated_embed.start_animation(EmbedAnimations.heartbeat_animation, 20.0)
        
        await interaction.response.send_message("❤️ Heartbeat animation started!", ephemeral=True)
    
    @discord.ui.button(emoji="🌊", label="Waves", style=discord.ButtonStyle.secondary)
    async def wave_animation(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.animated_embed:
            await self.animated_embed.stop_animation()
            await self.animated_embed.start_animation(EmbedAnimations.wave_animation, 12.0)
        
        await interaction.response.send_message("🌊 Wave animation started!", ephemeral=True)

# Utility functions for easy integration

async def create_loading_embed(bot, channel: discord.TextChannel, duration: float = 5.0) -> discord.Message:
    """Create a loading embed with animation"""
    initial_embed = discord.Embed(
        title="⏳ Loading...",
        description="Please wait",
        color=discord.Color.blue()
    )
    
    message = await channel.send(embed=initial_embed)
    animated_embed = AnimatedEmbed(bot, message)
    
    # Start animation in background
    asyncio.create_task(
        animated_embed.start_animation(EmbedAnimations.loading_animation, duration)
    )
    
    return message

async def create_progress_embed(bot, channel: discord.TextChannel, 
                              total_items: int, item_name: str = "items") -> tuple:
    """Create a progress tracking embed"""
    initial_embed = discord.Embed(
        title="📊 Processing",
        description=f"Processing {total_items} {item_name}...",
        color=discord.Color.green()
    )
    
    message = await channel.send(embed=initial_embed)
    
    async def update_progress(current: int):
        """Update progress embed"""
        progress_bar = ProgressBarGenerator.create_gradient_progress(current, total_items, 15)
        percentage = int((current / total_items) * 100) if total_items > 0 else 0
        
        embed = discord.Embed(
            title="📊 Processing",
            description=f"Processing {total_items} {item_name}...",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Progress",
            value=f"`{progress_bar}` {percentage}%\n{current}/{total_items} {item_name}",
            inline=False
        )
        
        try:
            await message.edit(embed=embed)
        except discord.NotFound:
            pass  # Message was deleted
    
    return message, update_progress

# Import math for wave calculations
import math
