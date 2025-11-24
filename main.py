import discord
from discord.ext import commands
from discord.ui import View, Button
import yt_dlp
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# QUEUE
queue = []
loop_mode = False
volume_level = 0.5
current_title = ""


# SPOTIFY API
SPOTIFY_CLIENT_ID = "SPOTIFY_CLIENT_ID_HERE"
SPOTIFY_CLIENT_SECRET = "SPOTIFY_CLIENT_SECRET_HERE"

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

YDL_OPTIONS = {"format": "bestaudio/best", "noplaylist": True}
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}


# ---------------------------------------------------------
# BUTTON PANEL
# ---------------------------------------------------------
class MusicButtons(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ Duraklattım.", ephemeral=True)

    @discord.ui.button(label="▶ Resume", style=discord.ButtonStyle.primary)
    async def resume(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        if vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶ Devam!", ephemeral=True)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.success)
    async def skip(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        if vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭ Geçtim!", ephemeral=True)

    @discord.ui.button(label="⛔ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        queue.clear()
        global loop_mode
        loop_mode = False

        if vc:
            vc.stop()
            await vc.disconnect()

        await interaction.response.send_message("🛑 Durdurdum ve çıktım.", ephemeral=True)


# ---------------------------------------------------------
# SPOTIFY → YOUTUBE ARAMA
# ---------------------------------------------------------
def spotify_to_youtube(query):
    search_opts = {"format": "bestaudio", "noplaylist": True}
    with yt_dlp.YoutubeDL(search_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        return info["entries"][0]["webpage_url"]


# ---------------------------------------------------------
# MÜZİK ÇALMA
# ---------------------------------------------------------
async def play_music(ctx, url):
    global current_title, volume_level

    vc = ctx.voice_client

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
        music_url = info["url"]
        current_title = info["title"]

    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(music_url, **FFMPEG_OPTIONS),
        volume=volume_level
    )

    vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(after_song(ctx), bot.loop))

    panel = MusicButtons(ctx)
    await ctx.send(f"🎶 **{current_title}** çalıyor.", view=panel)


# ---------------------------------------------------------
# ŞARKI BİTİNCE OLAN
# ---------------------------------------------------------
async def after_song(ctx):
    vc = ctx.voice_client
    global loop_mode

    if loop_mode:  # aynı şarkıyı tekrar çal
        await play_music(ctx, current_title)
        return

    if queue:
        next_url = queue.pop(0)
        await play_music(ctx, next_url)
    else:
        await asyncio.sleep(10)
        if vc and not vc.is_playing():
            await vc.disconnect()


# ---------------------------------------------------------
# KOMUTLAR
# ---------------------------------------------------------

@bot.command()
async def play(ctx, link):
    if ctx.author.voice is None:
        return await ctx.send("Sesli kanala girmen lazım reis.")

    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()

    vc = ctx.voice_client

    # SPOTIFY LINKI
    if "spotify.com" in link:
        if "track" in link:
            track = sp.track(link)
            name = track["name"]
            artist = track["artists"][0]["name"]
            yt = spotify_to_youtube(f"{name} {artist}")
            link = yt

        elif "playlist" in link:
            playlist = sp.playlist_tracks(link)["items"]
            for item in playlist:
                t = item["track"]["name"]
                a = item["track"]["artists"][0]["name"]
                yt = spotify_to_youtube(f"{t} {a}")
                queue.append(yt)

            return await ctx.send("🎧 Spotify playlist sıraya eklendi reis.")

        elif "album" in link:
            album = sp.album_tracks(link)["items"]
            for item in album:
                t = item["name"]
                a = item["artists"][0]["name"]
                yt = spotify_to_youtube(f"{t} {a}")
                queue.append(yt)

            return await ctx.send("🎧 Spotify albüm sıraya eklendi.")

    # YOUTUBE
    if vc.is_playing():
        queue.append(link)
        return await ctx.send("🎶 Çalıyor, sıraya ekledim.")

    await play_music(ctx, link)


@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc.is_playing():
        vc.stop()
        await ctx.send("⏭ Geçtim.")


@bot.command()
async def stop(ctx):
    vc = ctx.voice_client
    queue.clear()
    global loop_mode
    loop_mode = False
    vc.stop()
    await vc.disconnect()
    await ctx.send("🛑 Durdurdum.")


@bot.command()
async def loop(ctx):
    global loop_mode
    loop_mode = not loop_mode
    await ctx.send(f"🔁 Loop modu: **{'AÇIK' if loop_mode else 'KAPALI'}**")


@bot.command()
async def volume(ctx, level: int):
    global volume_level
    volume_level = level / 100
    await ctx.send(f"🔊 Ses seviyesi: %{level}")


@bot.command()
async def queue_list(ctx):
    if not queue:
        return await ctx.send("Sırada bir şey yok reis.")

    msg = "\n".join([f"{i+1}. {x}" for i, x in enumerate(queue)])
    await ctx.send(f"🎧 **Sıra:**\n{msg}")


bot.run("DISCORD_BOT_TOKEN_HERE")
