import discord
from discord.ext import commands
from discord.ui import View, Button
import yt_dlp
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

queue = []
loop_mode = False
volume_level = 0.5
current_query = None


YDL_OPTIONS = {"format": "bestaudio/best", "noplaylist": True}
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}


# ---------------------------------------
# BUTTON CONTROL PANEL
# ---------------------------------------
class MusicButtons(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.secondary)
    async def pause_button(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ Duraklattım.", ephemeral=True)

    @discord.ui.button(label="▶ Resume", style=discord.ButtonStyle.primary)
    async def resume_button(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶ Devam ettirdim.", ephemeral=True)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.success)
    async def skip_button(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        if vc:
            vc.stop()
            await interaction.response.send_message("⏭ Geçtim.", ephemeral=True)

    @discord.ui.button(label="⛔ Stop", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        queue.clear()
        global loop_mode
        loop_mode = False

        if vc:
            vc.stop()
            await vc.disconnect()

        await interaction.response.send_message("🛑 Durdurdum ve çıktım.", ephemeral=True)


# ---------------------------------------
# YOUTUBE SEARCH
# -------------------------
