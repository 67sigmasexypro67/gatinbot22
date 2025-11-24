import discord
from discord.ext import commands
from discord.ui import View, Button
import yt_dlp
import asyncio
import os

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


# ------------------------- BUTTON PANEL -------------------------
class MusicButtons(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.secondary)
    async def pause_btn(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ Duraklattım.", ephemeral=True)

    @discord.ui.button(label="▶ Resume", style=discord.ButtonStyle.primary)
    async def resume_btn(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶ Devam ettirdim.", ephemeral=True)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.success)
    async def skip_btn(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        if vc:
            vc.stop()
            await interaction.response.send_message("⏭ Geçtim!", ephemeral=True)

    @discord.ui.button(label="⛔ Stop", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, button: Button):
        vc = self.ctx.voice_client
        global loop_mode
        queue.clear()
        loop_mode = False

        if vc:
            vc.stop()
            await vc.disconnect()

        await interaction.response.send_message("🛑 Durdurdum ve çıktım.", ephemeral=True)


# ------------------------- YOUTUBE SEARCH -------------------------
def yt_search(query):
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        return info["entries"][0]["webpage_url"]


# ------------------------- PLAY MUSIC -------------------------
async def play_music(ctx, query):
    global current_query, volume_level

    vc = ctx.voice_client
    current_query = query

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(query, download=False)
        url = info["url"]
        title = info["title"]

    audio = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS),
        volume=volume_level
    )

    vc.play(audio, after=lambda e: asyncio.run_coroutine_threadsafe(after_song(ctx), bot.loop))

    await ctx.send(f"🎶 Çalıyorum: **{title}**", view=MusicButtons(ctx))


# ------------------------- AFTER SONG -------------------------
async def after_song(ctx):
    vc = ctx.voice_client
    global loop_mode, current_query

    if loop_mode and current_query:
        await play_music(ctx, current_query)
        return

    if queue:
        next_song = queue.pop(0)
        await play_music(ctx, next_song)
    else:
        await asyncio.sleep(10)
        if vc and not vc.is_playing():
            await vc.disconnect()


# ------------------------- COMMANDS -------------------------
@bot.command()
async def play(ctx, *, query):
    if ctx.author.voice is None:
        return await ctx.send("Sesli kanala gir reis.")

    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()

    vc = ctx.voice_client

    if not query.startswith("http"):
        query = yt_search(query)

    if vc.is_playing():
        queue.append(query)
        return await ctx.send("🎧 Şarkı sıraya eklendi.")

    await play_music(ctx, query)


@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc:
        vc.stop()
        await ctx.send("⏭ Şarkıyı geçtim.")


@bot.command()
async def stop(ctx):
    vc = ctx.voice_client
    global loop_mode
    queue.clear()
    loop_mode = False

    if vc:
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
        return await ctx.send("🎶 Sıra boş reis.")

    msg = "\n".join([f"{i+1}. {song}" for i, song in enumerate(queue)])
    await ctx.send(f"🎶 **Sıradaki şarkılar:**\n{msg}")


bot.run(os.getenv("TOKEN"))
