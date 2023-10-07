import discord
from discord.ext import commands

import yt_dlp as youtube_dl
from Config import token
import functools
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
#Set your Spotify client_id and client_secret
client_id = ''
client_secret = ''

YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'False', 'simulate': 'True', 'key': 'FFmpegExtractAudio','age_limit': 18}

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -af "bass=g=1"'}

queues = {}
#

urls = {'https://youtu.be', 'http://youtube.com',  'https://www.youtube.com/',
        'https://open.spotify.com/track/',
        'https://open.spotify.com/playlist/',
        'https://open.spotify.com/album/'}

playing_message = None


intents = discord.Intents.all()
intents.message_content = True
intents.typing = True
intents.members = True
intents.voice_states = True
bot = commands.Bot(command_prefix='/',  intents=intents)
bot.remove_command('help')

async def play_after_track(guild_id, ctx):
    await check_queue(guild_id, ctx)

async def check_queue(guild_id,ctx):
    global playing_message
    if queues.get(guild_id, []):
        if playing_message:
            try:
                await playing_message.delete()
            except discord.errors.NotFound:
                pass  # Ignore

        voice = bot.get_guild(guild_id).voice_client
        after_func = functools.partial(play_after_track, guild_id, ctx=ctx)
        song = queues[guild_id].pop(0)

        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            if 'https://youtu.be' in song or 'http://youtube.com' in song or 'https://www.youtube.com/' in song:
                info = ydl.extract_info(song, download=False)
                check = True
            elif'https://open.spotify.com/track/' in song:
                artist_name, track_name = readSpotifyURL(song)
                query = f"{artist_name} - {track_name}"
                info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
                check = True
            elif not 'https://' in song or not 'http://' in song:
                     info = ydl.extract_info(f"ytsearch:{song}", download=False)['entries'][0]
                     check = True
            else:
                check = False

            if check == True:
                link = info['url']
                formatted_seconds = f"0{info['duration'] % 60}" if (info['duration'] % 60) < 10 else info['duration'] % 60

                playing_message = await ctx.channel.send(f"```Граю трек: {info['title']} by {info['uploader']}"
                               f" [{info['duration']//60}:{formatted_seconds}]```")
                #Set your path to ffmpeg.exe
                source = discord.FFmpegPCMAudio(executable="C:\\Users\\АРТЕМ\\Desktop\\MusicBot\\ffmpeg\\ffmpeg.exe", source=link,**FFMPEG_OPTIONS)
                voice.play(source, after=lambda x=None: bot.loop.create_task(after_func()))
            else:
                ctx.channel.send("```Не знайдено треку```")
                await check_queue(after_func())


def check_url(url: str):
    for true_url in urls:
        if true_url in url:
            return True
    return False

def initializeSpotify(client_id, client_secret):
    client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    spoti = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    return spoti

def readSpotifyURL(url:str):
    track_info = sp.track(url)
    artist_name = track_info['artists'][0]['name']
    track_name = track_info['name']
    return artist_name, track_name


def readSpotifyContent(url: str):
    # Split the URL to extract the type (playlist or album) and the ID
    parts = url.split('/')
    content_type = parts[-2]  # The second-to-last part indicates type (playlist or album)
    content_id = parts[-1].split('?')[0]

    print(f"Content Type: {content_type}, Content ID: {content_id}")

    track_info_list = []

    if content_type == 'playlist':
        content = sp.playlist_items(content_id)
        for item in content['items']:
            track = item['track']
            artist_name = track['artists'][0]['name']
            track_name = track['name']
            track_info_list.append((artist_name, track_name))
    elif content_type == 'album':
        content = sp.album_tracks(content_id)
        for track in content['items']:
            artist_name = track['artists'][0]['name']
            track_name = track['name']
            track_info_list.append((artist_name, track_name))
    else:
        print("Unsupported content type")

    return track_info_list
@bot.event
async def on_ready():
    global sp
    print(f"Я вернулся из Небытия!")
    sp = initializeSpotify(client_id, client_secret)
    try:
        synced = await bot.tree.sync()
        print(f"Знайдено {len(synced)} команди")
    except Exception as e:
        print(e)

@bot.event
async def on_disconnect():
    print(f"Ну почему тут нету ПОМООЩИ?")

@bot.event
async def on_voice_state_update(member, before, after):

    if bot.user in before.channel.members:
        if len(before.channel.members) == 1:
            await before.channel.guild.voice_client.disconnect()

@bot.tree.command(name="play", description="Знайти трек на Youtube, Spotify, або SoundCloud")
async def play(ctx, url: str):

    if (ctx.user.voice):

        if check_url(url) == True:
            await ctx.response.send_message("```Додано до черги.```")
            if ctx.guild.voice_client is None:
                await ctx.user.voice.channel.connect()

            if 'https://open.spotify.com/playlist' in url or 'https://open.spotify.com/album' in url:
                tracks_info = readSpotifyContent(url)
                for artist_name, track_name in tracks_info:
                    song = f"{artist_name} - {track_name}"
                    guild_id = ctx.guild.id
                    if guild_id in queues:
                        queues[guild_id].append(song)
                    else:
                        queues[guild_id] = [song]
            else:
                song = url
                guild_id = ctx.guild.id
                if guild_id in queues:
                    queues[guild_id].append(song)
                else:
                    queues[guild_id] = [song]

            voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

            if len(queues[guild_id]) > 0 and not voice.is_playing():
                await check_queue(guild_id, ctx)

        else:
            await ctx.response.send_message(
                "```Ви ввели невірне посилання на пісню! Приймаються лише посилання на Youtube та Spotify```")
    else:
        await ctx.response.send_message(
            "```Ви не в голосовому каналі, ви повинні зайти в голосовий канал, щоб використати цю команду!```")


@bot.tree.command(description = "Призупинити поточний трек.")
async def pause(ctx):

    voice = discord.utils.get(bot.voice_clients,guild=ctx.guild)
    if voice.is_playing():

        await ctx.response.send_message("```Призупинено.```")
        voice.pause()


    else:
        await ctx.response.send_message("```На даний момент я не граю жодного треку.```")

@bot.tree.command(description = "Артою по Донецьку!")
async def bomb(ctx):
    import random
    await ctx.response.send_message(f"Було обстріляно {random.randint(5,50)} будинків в Донецьку.")

@bot.tree.command(description = "Список команд.")
async def help(ctx):

        emb = discord.Embed(title = 'Навігація по командам')
        emb.add_field(name = f'/play', value='Ввімкнути трек зі Spotify або Youtube')
        emb.add_field(name=f'/skip', value='Пропустити трек')
        emb.add_field(name=f'/stop', value='Зупинити програвання треків та видалення черги')
        emb.add_field(name=f'/pause', value='Призупинити програвання поточного треку')
        emb.add_field(name=f'/resume', value='Відновити програвання поточного треку')
        emb.add_field(name=f'/leave', value='Покинути канал та видалення черги')
        emb.add_field(name=f'/bomb', value='Обстріляти житлові квартали Донецька')

        await ctx.response.send_message(embed=emb)




@bot.tree.command(description = "Відновити відтворення треку.")
async def resume(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        await ctx.response.send_message("```Продовжую.```")
        voice.resume()
    else:
        await ctx.response.send_message("```На даний момент не має призупинених пісень.```")

@bot.tree.command(description = "Зупинити програвання музики та видалити всю чергу.")
async def stop(ctx):

    await ctx.response.send_message("```Зупинено програвання треків.```")
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice:
        voice.stop()
        queues[ctx.guild.id] = []

@bot.tree.command(description = "Покинути канал.")
async def leave(ctx):
    if(ctx.guild.voice_client):
        await ctx.response.send_message("```Я покинув голосовий канал```")
        await ctx.guild.voice_client.disconnect()
    else:
        await ctx.response.send_message("```Я не в голосовому каналі```")

@bot.tree.command(description="Пропустити поточний трек і перейти до наступного")
async def skip(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice and voice.is_playing():
        await ctx.response.send_message("```Поточний трек пропущено.```")
        voice.stop()
    else:
        await ctx.response.send_message("```В даний момент не грає жодний трек або бот не перебуває в голосовому каналі.```")

bot.run(token)
