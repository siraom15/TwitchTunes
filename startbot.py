import json
import logging
import os
import sys

from rich.logging import RichHandler
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.pubsub import PubSub
from twitchAPI.twitch import Twitch
from twitchAPI.types import AuthScope

log_level = logging.DEBUG if "dev".lower() in sys.argv else logging.INFO


log = logging.getLogger()


logging.basicConfig(
    level=log_level,
    format="%(name)s - %(message)s",
    datefmt="%X",
    handlers=[RichHandler()],
)

def path_exists(filename):
    return os.path.join(".", f"{filename}")

log.info("\n\nStarting 🎶TwitchTunes")

from pathlib import Path

import dotenv
from twitchio.ext import commands

cwd = Path(__file__).parents[0]
cwd = str(cwd)
import asyncio
import json
import re

import spotipy
from spotipy.oauth2 import SpotifyOAuth

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

with open("config.json") as config_file:
    config = json.load(config_file)

dotenv.load_dotenv()

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=os.environ.get("spotify_client_id"),
        client_secret=os.environ.get("spotify_secret"),
        redirect_uri="http://localhost:8080",
        scope=[
            "user-modify-playback-state",
            "user-read-currently-playing",
            "user-read-playback-state",
            "user-read-recently-played",
        ],
    )
)


def read_json(filename):
    with open(f"{filename}.json") as file:
        data = json.load(file)
    return data


def write_json(data, filename):
    with open(f"{filename}.json", "w") as file:
        json.dump(data, file, indent=4)


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=os.environ.get("TOKEN"),
            client_id=os.environ.get("client_id"),
            nick=config["nickname"],
            prefix=config["prefix"],
            initial_channels=config["channels"],
        )

        self.token = os.environ.get("SPOTIFY_AUTH")
        self.version = "1.4.0"

    async def event_ready(self):
        log.info("\n" * 100)
        log.info(f"TwitchTunes ({self.version}) Ready, logged in as: {self.nick}")

    def is_owner(self, ctx):
        return ctx.author.id == "640348450"

    @commands.command(name="ping", aliases=["ding"])
    async def ping_command(self, ctx):
        await ctx.send(
            f"🎶 TwitchTunes moded by @aommiester ออนไลน์อยู่"
        )

    @commands.command(name="blacklistuser")
    async def blacklist_user(self, ctx, *, user: str):
        user = user.lower()
        if ctx.author.is_mod or self.is_owner(ctx):
            file = read_json("blacklist_user")
            if user not in file["users"]:
                file["users"].append(user)
                write_json(file, "blacklist_user")
                await ctx.send(f"{user} ถูกเพิ่มลงใน blacklist")
            else:
                await ctx.send(f"{user} อยู่ใน blacklist แล้ว")
        else:
            await ctx.send("คุณไม่มีสิทธิ์ในการใช้คำสั่งนี้.")

    @commands.command(name="unblacklistuser")
    async def unblacklist_user(self, ctx, *, user: str):
        user = user.lower()
        if ctx.author.is_mod or self.is_owner(ctx):
            file = read_json("blacklist_user")
            if user in file["users"]:
                file["users"].remove(user)
                write_json(file, "blacklist_user")
                await ctx.send(f"{user} ถูกลบออกจาก blacklist")
            else:
                await ctx.send(f"{user} ไม่อยู่ใน blacklist")
        else:
            await ctx.send("คุณไม่มีสิทธิ์ในการใช้คำสั่งนี้.")

    @commands.command(name="blacklist", aliases=["blacklistsong", "blacklistadd"])
    async def blacklist_command(self, ctx, *, song_uri: str):
        if ctx.author.is_mod or self.is_owner(ctx):
            jscon = read_json("blacklist")

            song_uri = song_uri.replace("spotify:track:", "")

            if song_uri not in jscon["blacklist"]:
                if re.match(URL_REGEX, song_uri):
                    data = sp.track(song_uri)
                    song_uri = data["uri"]
                    song_uri = song_uri.replace("spotify:track:", "")

                track = sp.track(song_uri)

                track_name = track["name"]

                jscon["blacklist"].append(song_uri)

                write_json(jscon, "blacklist")

                await ctx.send(f"เพลง {track_name} ถูกเพิ่มลงใน blacklist")

            else:
                await ctx.send("เพลงนี้อยู่ใน blacklist แล้ว")

        else:
            await ctx.send("คุณไม่มีสิทธิ์ในการใช้คำสั่งนี้.")

    @commands.command(
        name="unblacklist", aliases=["unblacklistsong", "blacklistremove"]
    )
    async def unblacklist_command(self, ctx, *, song_uri: str):
        if ctx.author.is_mod or self.is_owner(ctx):
            jscon = read_json("blacklist")

            song_uri = song_uri.replace("spotify:track:", "")

            if re.match(URL_REGEX, song_uri):
                data = sp.track(song_uri)
                song_uri = data["uri"]
                song_uri = song_uri.replace("spotify:track:", "")

            if song_uri in jscon["blacklist"]:
                jscon["blacklist"].remove(song_uri)
                write_json(jscon, "blacklist")
                await ctx.send("เพลงถูกลบออกจาก blacklist")

            else:
                await ctx.send("เพลงนี้ไม่อยู่ใน blacklist")
        else:
            await ctx.send("คุณไม่มีสิทธิ์ในการใช้คำสั่งนี้.")

    @commands.command(name="np", aliases=["nowplaying", "song"])
    async def np_command(self, ctx):
        data = sp.currently_playing()
        song_artists = data["item"]["artists"]
        song_artists_names = [artist["name"] for artist in song_artists]
        await ctx.send(
            f"🎶กำลังเล่น - {data['item']['name']} - {', '.join(song_artists_names)}"
        )

    @commands.command(
        name="lastsong", aliases=["previoussongs", "last", "previousplayed"]
    )
    async def queue_command(self, ctx):
        queue = sp.current_user_recently_played(limit=10)
        songs = []

        for song in queue["items"]:
            # if the song artists include more than one artist: add all artist names to an artist list variable
            if len(song["track"]["artists"]) > 1:
                artists = [artist["name"] for artist in song["track"]["artists"]]
                song_artists = ", ".join(artists)
            # if the song artists only include one artist: add the artist name to the artist list variable
            else:
                song_artists = song["track"]["artists"][0]["name"]

            songs.append(song["track"]["name"] + " - " + song_artists)

        await ctx.send("กำลังเล่น: " + " | ".join(songs))

    @commands.command(name="songrequest", aliases=["sr", "addsong"])
    async def songrequest_command(self, ctx, *, song: str):
        song_uri = None
        try: 
            if ctx.author.is_mod or self.is_owner(ctx) or ctx.author.is_vip:
                if (
                    song.startswith("spotify:track:")
                    or not song.startswith("spotify:track:")
                    and re.match(URL_REGEX, song)
                ):
                    song_uri = song
                    await self.chat_song_request(ctx, song_uri, song_uri, album=False)

                else:
                    await self.chat_song_request(ctx, song, song_uri, album=False)
            else:
                await ctx.send(f"@{ctx.author.name} คุณต้องเป็น VIP/Mod เพื่อการใช้คำสั่งนี้")
                return
        except:
            await ctx.send(f"⛔หาเพลงไม่เจอ/ยังไม่ได้เปิด spotify client กรุณาลองใหม่อีกครั้ง⛔")

    async def chat_song_request(self, ctx, song, song_uri, album: bool):
        blacklisted_users = read_json("blacklist_user")["users"]
        if ctx.author.name.lower() in blacklisted_users:
            await ctx.send("คุณถูกแบนจากการใช้งานคำสั่งนี้")
        else:
            jscon = read_json("blacklist")

            if song_uri is None:
                data = sp.search(song, limit=1, type="track", market="US")
                song_uri = data["tracks"]["items"][0]["uri"]

            elif re.match(URL_REGEX, song_uri):
                data = sp.track(song_uri)
                song_uri = data["uri"]
                song_uri = song_uri.replace("spotify:track:", "")

            song_id = song_uri.replace("spotify:track:", "")

            if not album:
                data = sp.track(song_id)
                song_name = data["name"]
                song_artists = data["artists"]
                song_artists_names = [artist["name"] for artist in song_artists]
                duration = data["duration_ms"] / 60000

            if song_uri != "not found":
                if song_id in jscon["blacklist"]:
                    await ctx.send("เพลงอยู่ในเบล็คลิสต์ ไม่สามารถเพิ่มเข้าสู่คิวได้")

                elif duration > 17:
                    await ctx.send("เพลงยาวเกิน 17 นาที ไม่สามารถเพิ่มเข้าสู่คิวได้")
                else:
                    sp.add_to_queue(song_uri)
                    await ctx.send(
                        f"@{ctx.author.name} เพิ่ม ({song_name} - {', '.join(song_artists_names)}) เข้าสู่คิวแล้ว"
                    )


def song_request(data, song, song_uri, album: bool):
    jscon = read_json("blacklist")
    if song_uri is None:
        data = sp.search(song, limit=1, type="track", market="US")
        song_uri = data["tracks"]["items"][0]["uri"]
    elif re.match(URL_REGEX, song_uri):
        data = sp.track(song_uri)
        song_uri = data["uri"]
        song_uri = song_uri.replace("spotify:track:", "")
    song_id = song_uri.replace("spotify:track:", "")
    if not album:
        data = sp.track(song_id)
        duration = data["duration_ms"] / 60000
    if song_uri != "not found":
        if song_id in jscon["blacklist"] or duration > 17:
            return
        else:
            sp.add_to_queue(song_uri)


def callback_channel_points(uuid, data: dict) -> None:
    if (
        data["data"]["redemption"]["reward"]["title"].lower()
        != os.environ.get("channel_points_reward").lower()
    ):
        return

    log.debug(data)

    song: str = data["data"]["redemption"]["user_input"]
    ctx = None
    blacklisted_users = read_json("blacklist_user")["users"]
    if data["data"]["redemption"]["user"]["login"] in blacklisted_users:
        return
    if (
        song.startswith("spotify:track:")
        or not song.startswith("spotify:track:")
        and re.match(URL_REGEX, song)
    ):
        song_uri = song
        song_request(ctx, song_uri, song_uri, album=False)
    else:
        song_request(ctx, song, song_uri=None, album=False)


if os.environ.get("channel_points_reward"):
    channel_points_reward = os.environ.get("channel_points_reward")
    twitch = Twitch(os.environ.get("client_id"), os.environ.get("client_secret"))
    twitch.authenticate_app([])
    target_scope: list = [AuthScope.CHANNEL_READ_REDEMPTIONS]
    auth = UserAuthenticator(twitch, target_scope, force_verify=False)
    token, refresh_token = auth.authenticate()
    # add User authentication
    twitch.set_user_authentication(token, target_scope, refresh_token)

    user_id: str = twitch.get_users(logins=config["channels"])["data"][0]["id"]

    pubsub = PubSub(twitch)
    uuid = pubsub.listen_channel_points(user_id, callback_channel_points)
    pubsub.start()

bot = Bot()
bot.run()
