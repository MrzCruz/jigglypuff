import discord
from discord.ext import commands
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from apikey import BOT_TOKEN
from yt import get_audio_url, get_audio_title
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = commands.Bot(command_prefix='!', intents=intents)
tree = client.tree
client.volume = 0.5  # Default volume (50%)

queues = {}         # {guild_id: [(ctx, url, title), ...]}
current_track = {}  # {guild_id: title}

@client.event
async def on_ready():
    print("Bot is active and online")
    print("------------------------")
    await tree.sync()

@tree.command(name="ping", description="Check if the bot is online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("PONG")

async def play_next(ctx):
    guild_id = ctx.guild.id
    if guild_id in queues and queues[guild_id]:
        next_ctx, url, title = queues[guild_id].pop(0)
        current_track[guild_id] = title

        def after_playing(error):
            fut = asyncio.run_coroutine_threadsafe(play_next(next_ctx), client.loop)
            try:
                fut.result()
            except:
                pass

        voice = next_ctx.voice_client or await next_ctx.author.voice.channel.connect()
        source = FFmpegPCMAudio(url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5')
        source = PCMVolumeTransformer(source, volume=client.volume)
        voice.play(source, after=after_playing)

        await ctx.send(f"🎧 Now playing: **{title}**")
    else:
        current_track.pop(guild_id, None)
        await ctx.send("✅ Queue is empty.")

@tree.command(name="play", description="Play audio from a search query or URL")
async def play(interaction: discord.Interaction, input: str):
    ctx = await commands.Context.from_interaction(interaction)
    if ctx.author.voice:
        await interaction.response.send_message(f"🔍 Searching for **{input}**...")

        audio_url = get_audio_url(input)
        audio_title = get_audio_title(input)
        guild_id = ctx.guild.id

        if guild_id not in queues:
            queues[guild_id] = []

        queues[guild_id].append((ctx, audio_url, audio_title))

        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
            await ctx.send("✅ I joined the voice channel")

        if not ctx.voice_client.is_playing():
            await play_next(ctx)
        else:
            await ctx.send(f"✅ Added to queue: **{audio_title}**")
    else:
        await interaction.followup.send("❌ Please join a voice channel first.")

@tree.command(name="pause", description="Pause the currently playing audio")
async def pause(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    voice = ctx.voice_client
    if voice and voice.is_playing():
        voice.pause()
        await interaction.response.send_message("⏸ Audio paused")
    else:
        await interaction.response.send_message("❌ There is no audio playing")

@tree.command(name="resume", description="Resume paused audio")
async def resume(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    voice = ctx.voice_client
    if voice and voice.is_paused():
        voice.resume()
        await interaction.response.send_message("▶️ Audio resumed")
    else:
        await interaction.response.send_message("❌ There is no paused audio")

# Helper function for leaving voice and clearing queue
async def leave_voice(ctx):
    guild_id = ctx.guild.id
    if ctx.voice_client:
        queues[guild_id] = []
        current_track.pop(guild_id, None)
        await ctx.voice_client.disconnect()
        await ctx.send("👋 I left the voice channel and cleared the queue")
    else:
        await ctx.send("❌ I'm not in a voice channel")

# Old leave command now calls helper
@client.command()
async def leave(ctx):
    await leave_voice(ctx)

# Your slash command stop should look like this:
@tree.command(name="stop", description="Stop audio and leave voice channel")
async def stop(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    voice = ctx.voice_client
    guild_id = ctx.guild.id
    if voice and voice.is_playing():
        queues[guild_id] = []
        voice.stop()
        await ctx.send("⏹ Audio stopped")
        await leave_voice(ctx)
    else:
        await ctx.send("❌ Nothing is playing")

@tree.command(name="skip", description="Skip current playing audio")
async def skip(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    voice = ctx.voice_client
    if voice and voice.is_playing():
        voice.stop()
        await interaction.response.send_message("⏭ Skipping current song...")
    else:
        await interaction.response.send_message("❌ Nothing to skip.")

@tree.command(name="queue", description="Show the current audio queue")
async def queue(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    guild_id = ctx.guild.id
    if guild_id in queues and queues[guild_id]:
        msg = "\n".join([f"{i+1}. {title}" for i, (_, _, title) in enumerate(queues[guild_id])])
        await interaction.response.send_message(f"📜 Current Queue:\n{msg}")
    else:
        await interaction.response.send_message("📭 Queue is empty.")

@tree.command(name="now", description="Show the currently playing audio")
async def now(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    guild_id = ctx.guild.id
    title = current_track.get(guild_id)
    voice = ctx.voice_client
    if voice and voice.is_playing() and title:
        await interaction.response.send_message(f"🎧 Now playing: **{title}**")
    else:
        await interaction.response.send_message("❌ Nothing is playing right now.")

@tree.command(name="volume", description="Set volume (0-100)")
async def volume(interaction: discord.Interaction, vol: int):
    ctx = await commands.Context.from_interaction(interaction)
    if 0 <= vol <= 100:
        client.volume = vol / 100.0
        voice = ctx.voice_client
        if voice and voice.is_playing() and hasattr(voice.source, 'volume'):
            voice.source.volume = client.volume
        await interaction.response.send_message(f"🔊 Volume set to {vol}%")
    else:
        await interaction.response.send_message("❌ Please enter a volume between 0 and 100")

client.run(BOT_TOKEN)