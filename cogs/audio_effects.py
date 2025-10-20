"""
Advanced Audio Effects - Comprehensive audio control panel with filters, equalizer, and effects
"""

import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from typing import Optional, Dict, List, Tuple
import datetime
import asyncio
from utils.emoji import *
from config.config import config
import logging

logger = logging.getLogger(__name__)

class AudioEffects(commands.Cog):
    """Advanced audio effects and control panel"""
    
    def __init__(self, bot):
        self.bot = bot
        self.effect_presets = {
            'clear': {'name': 'Clear', 'eq': [], 'timescale': None, 'filters': []},
            'bass_boost': {'name': 'Bass Boost', 'eq': [(0, 0.6), (1, 0.7), (2, 0.8), (3, 0.55)], 'timescale': None, 'filters': ['bass']},
            'treble_boost': {'name': 'Treble Boost', 'eq': [(10, 0.5), (11, 0.6), (12, 0.7), (13, 0.8), (14, 0.6)], 'timescale': None, 'filters': ['treble']},
            'nightcore': {'name': 'Nightcore', 'eq': [], 'timescale': {'speed': 1.2, 'pitch': 1.2, 'rate': 1}, 'filters': ['nightcore']},
            'vaporwave': {'name': 'Vaporwave', 'eq': [(0, -0.3), (1, -0.2), (2, 0.1), (3, 0.2), (4, 0.1)], 'timescale': {'speed': 0.8, 'pitch': 0.9, 'rate': 1}, 'filters': ['vaporwave']},
            'pop': {'name': 'Pop', 'eq': [(0, 0.3), (1, 0.2), (2, 0.1), (6, 0.3), (7, 0.4), (8, 0.3)], 'timescale': None, 'filters': ['pop']},
            'rock': {'name': 'Rock', 'eq': [(0, 0.4), (1, 0.3), (2, 0.2), (8, 0.4), (9, 0.5), (10, 0.4)], 'timescale': None, 'filters': ['rock']},
            'classical': {'name': 'Classical', 'eq': [(0, 0.2), (5, 0.3), (6, 0.4), (7, 0.3), (11, 0.2), (12, 0.3)], 'timescale': None, 'filters': ['classical']},
            'jazz': {'name': 'Jazz', 'eq': [(1, 0.2), (4, 0.3), (5, 0.4), (6, 0.3), (9, 0.2)], 'timescale': None, 'filters': ['jazz']},
            'electronic': {'name': 'Electronic', 'eq': [(0, 0.5), (1, 0.3), (7, 0.4), (8, 0.6), (9, 0.5), (10, 0.3)], 'timescale': None, 'filters': ['electronic']},
        }
    
    def create_embed(self, title: str, description: str = None, color: discord.Color = None) -> discord.Embed:
        """Create a standardized embed"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or discord.Color.blurple()
        )
        current_time = datetime.datetime.now().strftime("%H:%M")
        embed.set_footer(
            text=f"Powered by {self.bot.user.name} • {current_time}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        return embed
    
    @app_commands.command(name="effects", description="Open the advanced audio effects control panel")
    async def effects_panel(self, interaction: discord.Interaction):
        """Open the comprehensive audio effects panel"""
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        embed = self.create_embed(
            title="🎛️ Advanced Audio Control Panel",
            description="Select categories below to access different audio effects and controls",
            color=discord.Color.purple()
        )
        
        # Current effects status
        active_effects = []
        if hasattr(player, 'current_effects'):
            active_effects = player.current_effects
        
        embed.add_field(
            name="🎵 Current Track",
            value=f"[{player.current.title}]({player.current.uri})" if player.current else "Nothing playing",
            inline=False
        )
        
        embed.add_field(
            name="🎚️ Active Effects",
            value=", ".join(active_effects) if active_effects else "None",
            inline=True
        )
        
        embed.add_field(
            name="🔊 Volume",
            value=f"{int(player.volume * 100)}%",
            inline=True
        )
        
        view = EffectsMainPanel()
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="preset", description="Apply an audio preset")
    @app_commands.describe(preset="Choose an audio preset")
    @app_commands.choices(preset=[
        app_commands.Choice(name="🔄 Clear (Reset All)", value="clear"),
        app_commands.Choice(name="🎵 Bass Boost", value="bass_boost"),
        app_commands.Choice(name="🎶 Treble Boost", value="treble_boost"),
        app_commands.Choice(name="⚡ Nightcore", value="nightcore"),
        app_commands.Choice(name="🌊 Vaporwave", value="vaporwave"),
        app_commands.Choice(name="🎤 Pop", value="pop"),
        app_commands.Choice(name="🎸 Rock", value="rock"),
        app_commands.Choice(name="🎼 Classical", value="classical"),
        app_commands.Choice(name="🎺 Jazz", value="jazz"),
        app_commands.Choice(name="🔊 Electronic", value="electronic"),
    ])
    async def apply_preset(self, interaction: discord.Interaction, preset: str):
        """Apply an audio preset"""
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        if preset not in self.effect_presets:
            return await interaction.response.send_message("❌ Invalid preset!", ephemeral=True)
        
        preset_data = self.effect_presets[preset]
        filters = player.filters
        
        # Reset all filters first
        filters.reset()
        
        # Apply equalizer
        if preset_data['eq']:
            filters.equalizer.set(bands=preset_data['eq'])
        
        # Apply timescale
        if preset_data['timescale']:
            ts = preset_data['timescale']
            filters.timescale.set(speed=ts['speed'], pitch=ts['pitch'], rate=ts['rate'])
        
        # Apply filters
        await player.set_filters(filters)
        
        # Store current effects
        if not hasattr(player, 'current_effects'):
            player.current_effects = []
        player.current_effects = preset_data['filters']
        
        embed = self.create_embed(
            title="✅ Preset Applied",
            description=f"Applied **{preset_data['name']}** preset",
            color=discord.Color.green()
        )
        
        if preset == 'clear':
            embed.description = "🔄 **All effects cleared**"
            embed.color = discord.Color.orange()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="equalizer", description="Open the equalizer control panel")
    async def equalizer(self, interaction: discord.Interaction):
        """Open the equalizer control panel"""
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        embed = self.create_embed(
            title="🎚️ Equalizer Control",
            description="Adjust frequency bands to customize your audio experience",
            color=discord.Color.blue()
        )
        
        view = EqualizerPanel()
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="speed", description="Adjust playback speed")
    @app_commands.describe(speed="Playback speed multiplier (0.25 - 3.0)")
    async def speed(self, interaction: discord.Interaction, speed: float):
        """Adjust playback speed"""
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        if not 0.25 <= speed <= 3.0:
            return await interaction.response.send_message("❌ Speed must be between 0.25 and 3.0!", ephemeral=True)
        
        filters = player.filters
        filters.timescale.set(speed=speed)
        await player.set_filters(filters)
        
        embed = self.create_embed(
            title="⚡ Speed Adjusted",
            description=f"Set playback speed to **{speed}x**",
            color=discord.Color.yellow()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="pitch", description="Adjust pitch without changing speed")
    @app_commands.describe(pitch="Pitch multiplier (0.25 - 3.0)")
    async def pitch(self, interaction: discord.Interaction, pitch: float):
        """Adjust pitch without changing speed"""
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected to a voice channel!", ephemeral=True)
        
        if not 0.25 <= pitch <= 3.0:
            return await interaction.response.send_message("❌ Pitch must be between 0.25 and 3.0!", ephemeral=True)
        
        filters = player.filters
        current_timescale = filters.timescale.payload
        speed = current_timescale.get('speed', 1.0)
        rate = current_timescale.get('rate', 1.0)
        
        filters.timescale.set(speed=speed, pitch=pitch, rate=rate)
        await player.set_filters(filters)
        
        embed = self.create_embed(
            title="🎵 Pitch Adjusted",
            description=f"Set pitch to **{pitch}x**",
            color=discord.Color.cyan()
        )
        await interaction.response.send_message(embed=embed)


class EffectsMainPanel(discord.ui.View):
    """Main effects control panel with category selection"""
    
    def __init__(self, *, timeout=300):
        super().__init__(timeout=timeout)
    
    @discord.ui.select(
        placeholder="🎛️ Choose an effects category...",
        options=[
            discord.SelectOption(
                label="🎚️ Equalizer",
                description="Adjust frequency bands",
                value="equalizer",
                emoji="🎚️"
            ),
            discord.SelectOption(
                label="🎵 Music Presets",
                description="Genre-based audio presets",
                value="presets",
                emoji="🎵"
            ),
            discord.SelectOption(
                label="⚡ Speed & Pitch",
                description="Tempo and pitch controls",
                value="speed_pitch",
                emoji="⚡"
            ),
            discord.SelectOption(
                label="🌊 Advanced Effects",
                description="Reverb, chorus, distortion",
                value="advanced",
                emoji="🌊"
            ),
            discord.SelectOption(
                label="🔊 Volume Controls",
                description="Volume and dynamics",
                value="volume",
                emoji="🔊"
            ),
        ]
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        category = select.values[0]
        
        if category == "equalizer":
            view = EqualizerPanel()
            embed = discord.Embed(
                title="🎚️ Equalizer Control",
                description="Fine-tune frequency bands to customize your audio",
                color=discord.Color.blue()
            )
        elif category == "presets":
            view = PresetsPanel()
            embed = discord.Embed(
                title="🎵 Audio Presets",
                description="Quick audio presets for different music genres",
                color=discord.Color.green()
            )
        elif category == "speed_pitch":
            view = SpeedPitchPanel()
            embed = discord.Embed(
                title="⚡ Speed & Pitch Control",
                description="Adjust playback speed and pitch independently",
                color=discord.Color.yellow()
            )
        elif category == "advanced":
            view = AdvancedEffectsPanel()
            embed = discord.Embed(
                title="🌊 Advanced Effects",
                description="Professional audio effects and filters",
                color=discord.Color.purple()
            )
        elif category == "volume":
            view = VolumeControlPanel()
            embed = discord.Embed(
                title="🔊 Volume Controls",
                description="Volume, compression, and dynamics control",
                color=discord.Color.orange()
            )
        
        await interaction.response.edit_message(embed=embed, view=view)


class EqualizerPanel(discord.ui.View):
    """Equalizer control panel"""
    
    def __init__(self, *, timeout=300):
        super().__init__(timeout=timeout)
        self.eq_bands = [0] * 15  # 15 band equalizer
    
    @discord.ui.button(label="🎚️ Low Freq +", style=discord.ButtonStyle.secondary)
    async def low_freq_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_eq_band(interaction, [0, 1, 2], 0.1)
    
    @discord.ui.button(label="🎚️ Low Freq -", style=discord.ButtonStyle.secondary)
    async def low_freq_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_eq_band(interaction, [0, 1, 2], -0.1)
    
    @discord.ui.button(label="🎚️ Mid Freq +", style=discord.ButtonStyle.secondary)
    async def mid_freq_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_eq_band(interaction, [5, 6, 7, 8], 0.1)
    
    @discord.ui.button(label="🎚️ Mid Freq -", style=discord.ButtonStyle.secondary)
    async def mid_freq_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_eq_band(interaction, [5, 6, 7, 8], -0.1)
    
    @discord.ui.button(label="🎚️ High Freq +", style=discord.ButtonStyle.secondary)
    async def high_freq_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_eq_band(interaction, [11, 12, 13, 14], 0.1)
    
    @discord.ui.button(label="🎚️ High Freq -", style=discord.ButtonStyle.secondary)
    async def high_freq_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_eq_band(interaction, [11, 12, 13, 14], -0.1)
    
    @discord.ui.button(label="🔄 Reset EQ", style=discord.ButtonStyle.danger, row=1)
    async def reset_eq(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        filters = player.filters
        filters.equalizer.reset()
        await player.set_filters(filters)
        self.eq_bands = [0] * 15
        
        await interaction.response.send_message("🔄 **Equalizer reset**", ephemeral=True)
    
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = EffectsMainPanel()
        embed = discord.Embed(
            title="🎛️ Advanced Audio Control Panel",
            description="Select categories below to access different audio effects and controls",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def adjust_eq_band(self, interaction: discord.Interaction, bands: List[int], adjustment: float):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        # Adjust specified bands
        for band in bands:
            self.eq_bands[band] = max(-0.8, min(0.8, self.eq_bands[band] + adjustment))
        
        # Apply equalizer
        eq_settings = [(i, gain) for i, gain in enumerate(self.eq_bands) if gain != 0]
        filters = player.filters
        if eq_settings:
            filters.equalizer.set(bands=eq_settings)
        else:
            filters.equalizer.reset()
        
        await player.set_filters(filters)
        
        band_names = {0: "Sub Bass", 5: "Mid Range", 11: "High Range"}
        band_name = next((name for b, name in band_names.items() if b in bands), "Frequency")
        direction = "increased" if adjustment > 0 else "decreased"
        
        await interaction.response.send_message(f"🎚️ **{band_name} {direction}**", ephemeral=True)


class PresetsPanel(discord.ui.View):
    """Audio presets panel"""
    
    def __init__(self, *, timeout=300):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="🔄 Clear", style=discord.ButtonStyle.danger, emoji="🔄")
    async def preset_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_preset(interaction, "clear")
    
    @discord.ui.button(label="Bass Boost", style=discord.ButtonStyle.primary, emoji="🎵")
    async def preset_bass(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_preset(interaction, "bass_boost")
    
    @discord.ui.button(label="Treble Boost", style=discord.ButtonStyle.primary, emoji="🎶")
    async def preset_treble(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_preset(interaction, "treble_boost")
    
    @discord.ui.button(label="Nightcore", style=discord.ButtonStyle.secondary, emoji="⚡")
    async def preset_nightcore(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_preset(interaction, "nightcore")
    
    @discord.ui.button(label="Vaporwave", style=discord.ButtonStyle.secondary, emoji="🌊")
    async def preset_vaporwave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_preset(interaction, "vaporwave")
    
    @discord.ui.button(label="Pop", style=discord.ButtonStyle.success, emoji="🎤", row=1)
    async def preset_pop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_preset(interaction, "pop")
    
    @discord.ui.button(label="Rock", style=discord.ButtonStyle.success, emoji="🎸", row=1)
    async def preset_rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_preset(interaction, "rock")
    
    @discord.ui.button(label="Classical", style=discord.ButtonStyle.success, emoji="🎼", row=1)
    async def preset_classical(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_preset(interaction, "classical")
    
    @discord.ui.button(label="Jazz", style=discord.ButtonStyle.success, emoji="🎺", row=1)
    async def preset_jazz(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_preset(interaction, "jazz")
    
    @discord.ui.button(label="Electronic", style=discord.ButtonStyle.success, emoji="🔊", row=1)
    async def preset_electronic(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_preset(interaction, "electronic")
    
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=2)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = EffectsMainPanel()
        embed = discord.Embed(
            title="🎛️ Advanced Audio Control Panel",
            description="Select categories below to access different audio effects and controls",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def apply_preset(self, interaction: discord.Interaction, preset_name: str):
        cog = interaction.client.get_cog('AudioEffects')
        if cog:
            await cog.apply_preset(interaction, preset_name)


class SpeedPitchPanel(discord.ui.View):
    """Speed and pitch control panel"""
    
    def __init__(self, *, timeout=300):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="Speed -", style=discord.ButtonStyle.secondary, emoji="⏪")
    async def speed_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_speed(interaction, -0.1)
    
    @discord.ui.button(label="Speed +", style=discord.ButtonStyle.secondary, emoji="⏩")
    async def speed_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_speed(interaction, 0.1)
    
    @discord.ui.button(label="Pitch -", style=discord.ButtonStyle.secondary, emoji="⬇️")
    async def pitch_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_pitch(interaction, -0.1)
    
    @discord.ui.button(label="Pitch +", style=discord.ButtonStyle.secondary, emoji="⬆️")
    async def pitch_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_pitch(interaction, 0.1)
    
    @discord.ui.button(label="🔄 Reset", style=discord.ButtonStyle.danger, row=1)
    async def reset_timescale(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        filters = player.filters
        filters.timescale.reset()
        await player.set_filters(filters)
        
        await interaction.response.send_message("🔄 **Speed and pitch reset**", ephemeral=True)
    
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = EffectsMainPanel()
        embed = discord.Embed(
            title="🎛️ Advanced Audio Control Panel",
            description="Select categories below to access different audio effects and controls",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def adjust_speed(self, interaction: discord.Interaction, adjustment: float):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        filters = player.filters
        current = filters.timescale.payload
        new_speed = max(0.25, min(3.0, current.get('speed', 1.0) + adjustment))
        
        filters.timescale.set(
            speed=new_speed,
            pitch=current.get('pitch', 1.0),
            rate=current.get('rate', 1.0)
        )
        await player.set_filters(filters)
        
        await interaction.response.send_message(f"⚡ **Speed: {new_speed:.1f}x**", ephemeral=True)
    
    async def adjust_pitch(self, interaction: discord.Interaction, adjustment: float):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        filters = player.filters
        current = filters.timescale.payload
        new_pitch = max(0.25, min(3.0, current.get('pitch', 1.0) + adjustment))
        
        filters.timescale.set(
            speed=current.get('speed', 1.0),
            pitch=new_pitch,
            rate=current.get('rate', 1.0)
        )
        await player.set_filters(filters)
        
        await interaction.response.send_message(f"🎵 **Pitch: {new_pitch:.1f}x**", ephemeral=True)


class AdvancedEffectsPanel(discord.ui.View):
    """Advanced effects panel"""
    
    def __init__(self, *, timeout=300):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="Karaoke", style=discord.ButtonStyle.secondary, emoji="🎤")
    async def toggle_karaoke(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_effect(interaction, 'karaoke', button)
    
    @discord.ui.button(label="8D Audio", style=discord.ButtonStyle.secondary, emoji="🌀")
    async def toggle_8d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_effect(interaction, '8d', button)
    
    @discord.ui.button(label="Tremolo", style=discord.ButtonStyle.secondary, emoji="🌊")
    async def toggle_tremolo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_effect(interaction, 'tremolo', button)
    
    @discord.ui.button(label="Vibrato", style=discord.ButtonStyle.secondary, emoji="〰️")
    async def toggle_vibrato(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_effect(interaction, 'vibrato', button)
    
    @discord.ui.button(label="Distortion", style=discord.ButtonStyle.secondary, emoji="⚡")
    async def toggle_distortion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_effect(interaction, 'distortion', button)
    
    @discord.ui.button(label="🔄 Clear All", style=discord.ButtonStyle.danger, row=1)
    async def clear_effects(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        filters = player.filters
        filters.reset()
        await player.set_filters(filters)
        
        # Reset button styles
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.label != "🔄 Clear All" and item.label != "🔙 Back":
                item.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(content="🔄 **All effects cleared**", view=self)
    
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = EffectsMainPanel()
        embed = discord.Embed(
            title="🎛️ Advanced Audio Control Panel",
            description="Select categories below to access different audio effects and controls",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def toggle_effect(self, interaction: discord.Interaction, effect: str, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        filters = player.filters
        is_active = button.style == discord.ButtonStyle.success
        
        if effect == 'karaoke':
            if is_active:
                filters.karaoke.reset()
                button.style = discord.ButtonStyle.secondary
                status = "disabled"
            else:
                filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220, filter_width=100)
                button.style = discord.ButtonStyle.success
                status = "enabled"
        elif effect == '8d':
            if is_active:
                filters.rotation.reset()
                button.style = discord.ButtonStyle.secondary
                status = "disabled"
            else:
                filters.rotation.set(speed=0.3)
                button.style = discord.ButtonStyle.success
                status = "enabled"
        elif effect == 'tremolo':
            if is_active:
                filters.tremolo.reset()
                button.style = discord.ButtonStyle.secondary
                status = "disabled"
            else:
                filters.tremolo.set(frequency=2.0, depth=0.5)
                button.style = discord.ButtonStyle.success
                status = "enabled"
        elif effect == 'vibrato':
            if is_active:
                filters.vibrato.reset()
                button.style = discord.ButtonStyle.secondary
                status = "disabled"
            else:
                filters.vibrato.set(frequency=2.0, depth=0.5)
                button.style = discord.ButtonStyle.success
                status = "enabled"
        elif effect == 'distortion':
            if is_active:
                filters.distortion.reset()
                button.style = discord.ButtonStyle.secondary
                status = "disabled"
            else:
                filters.distortion.set(sin_offset=60, sin_scale=1.0, cos_offset=60, cos_scale=1.0, tan_offset=60, tan_scale=1.0, offset=0.0, scale=1.0)
                button.style = discord.ButtonStyle.success
                status = "enabled"
        
        await player.set_filters(filters)
        await interaction.response.edit_message(content=f"✨ **{effect.title()} {status}**", view=self)


class VolumeControlPanel(discord.ui.View):
    """Volume and dynamics control panel"""
    
    def __init__(self, *, timeout=300):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="Vol -10%", style=discord.ButtonStyle.secondary, emoji="🔉")
    async def volume_down_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_volume(interaction, -10)
    
    @discord.ui.button(label="Vol -5%", style=discord.ButtonStyle.secondary, emoji="🔉")
    async def volume_down_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_volume(interaction, -5)
    
    @discord.ui.button(label="Vol +5%", style=discord.ButtonStyle.secondary, emoji="🔊")
    async def volume_up_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_volume(interaction, 5)
    
    @discord.ui.button(label="Vol +10%", style=discord.ButtonStyle.secondary, emoji="🔊")
    async def volume_up_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.adjust_volume(interaction, 10)
    
    @discord.ui.button(label="🔇 Mute", style=discord.ButtonStyle.danger, row=1)
    async def mute_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        if not hasattr(player, 'previous_volume'):
            player.previous_volume = player.volume
            await player.set_volume(0)
            button.label = "🔊 Unmute"
            button.style = discord.ButtonStyle.success
            await interaction.response.edit_message(content="🔇 **Muted**", view=self)
        else:
            await player.set_volume(player.previous_volume)
            delattr(player, 'previous_volume')
            button.label = "🔇 Mute"
            button.style = discord.ButtonStyle.danger
            await interaction.response.edit_message(content="🔊 **Unmuted**", view=self)
    
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = EffectsMainPanel()
        embed = discord.Embed(
            title="🎛️ Advanced Audio Control Panel",
            description="Select categories below to access different audio effects and controls",
            color=discord.Color.purple()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def adjust_volume(self, interaction: discord.Interaction, adjustment: int):
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        current_volume = int(player.volume * 100)
        new_volume = max(0, min(200, current_volume + adjustment))
        
        await player.set_volume(new_volume / 100)
        
        await interaction.response.send_message(f"🔊 **Volume: {new_volume}%**", ephemeral=True)


async def setup(bot):
    """Setup function for Audio Effects cog"""
    await bot.add_cog(AudioEffects(bot))
