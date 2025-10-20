import discord
import datetime

class MusicPlayer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.queue = []
        self.current = None
        self.loop = False
        self.volume = 100
        self.now_playing_message = None

    async def update_now_playing(self):
        if self.now_playing_message:
            try:
                await self.now_playing_message.delete()
            except discord.HTTPException:
                pass

        if not self.current:
            return

        embed = discord.Embed(title="Now Playing 🎵", color=discord.Color.blue())
        embed.add_field(name="Track", value=self.current.title, inline=False)
        embed.add_field(name="Duration", value=str(datetime.timedelta(seconds=self.current.duration)))
        embed.add_field(name="Requested by", value=self.ctx.author.mention)
        embed.add_field(name="URL", value=f"[Click here]({self.current.uri})")
        
        self.now_playing_message = await self.ctx.send(embed=embed) 