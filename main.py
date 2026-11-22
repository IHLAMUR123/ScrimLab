#!/usr/bin/env python3
import asyncio
import os

import aiosqlite
import aiohttp
from colorama import Fore, Style, init
from disnake import Intents
from disnake.ext import commands, tasks

from core import config
from core.__credits__ import get_credits_banner, __version__

# Initialize colorama
init(autoreset=True)

# disnake 2.7 calls asyncio.get_event_loop() inside Client.__init__.
# On Python 3.14+ that raises when no loop is set, so create one explicitly.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

TOKEN = config.TOKEN
DB_PATH = os.getenv("DB_PATH", "db/main.sqlite")
PREFIX = os.getenv("PREFIX", "!")


class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = "lol"
        self.role_emojis = dict(config.ROLE_EMOJIS)
        self._db: aiosqlite.Connection | None = None
        self._db_lock = asyncio.Lock()

    # --- database ----------------------------------------------------------
    async def db(self) -> aiosqlite.Connection:
        """Return the shared connection, opening it on first use.

        One connection with WAL avoids the ``database is locked`` errors that
        the old per-query connection produced under load.
        """
        if self._db is None:
            os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
            self._db = await aiosqlite.connect(DB_PATH)
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute("PRAGMA synchronous=NORMAL")
            await self._db.execute("PRAGMA busy_timeout=5000")
            await self._db.execute("PRAGMA foreign_keys=ON")
            await self._db.commit()
        return self._db

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None
        await super().close()

    async def execute(self, query, *values):
        async with self._db_lock:
            db = await self.db()
            await db.execute(query, values)
            await db.commit()

    async def executemany(self, query, values):
        async with self._db_lock:
            db = await self.db()
            await db.executemany(query, values)
            await db.commit()

    async def fetchval(self, query, *values):
        async with self._db_lock:
            db = await self.db()
            async with db.execute(query, values) as cur:
                row = await cur.fetchone()
            return row[0] if row else None

    async def fetchrow(self, query, *values):
        async with self._db_lock:
            db = await self.db()
            async with db.execute(query, values) as cur:
                row = await cur.fetchone()
            return list(row) if row else None

    async def fetchmany(self, query, size, *values):
        async with self._db_lock:
            db = await self.db()
            async with db.execute(query, values) as cur:
                return await cur.fetchmany(size)

    async def fetch(self, query, *values):
        async with self._db_lock:
            db = await self.db()
            async with db.execute(query, values) as cur:
                return await cur.fetchall()

    async def check_testmode(self, guild_id: int) -> bool:
        data = await self.fetchrow(
            "SELECT 1 FROM testmode WHERE guild_id = ?", guild_id
        )
        return data is not None


# Enabling message content intent for the bot to support prefix commands.
intents = Intents.default()
intents.message_content = True
intents.members = True

bot = MyBot(
    intents=intents,
    command_prefix=PREFIX,
    test_guilds=config.sync_guild_ids(),
)
bot.remove_command("help")

async def post_topgg_stats():
    """Post the guild count to top.gg.

    Implemented with a plain HTTP request so the bot does not need topggpy,
    which would pull in discord.py alongside disnake.
    """
    if not config.TOP_GG_TOKEN or bot.user is None:
        return
    payload = {"server_count": len(bot.guilds)}
    if bot.shard_count:
        payload["shard_count"] = bot.shard_count
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://top.gg/api/bots/{bot.user.id}/stats",
                json=payload,
                headers={"Authorization": config.TOP_GG_TOKEN},
                timeout=10,
            ) as response:
                if response.status == 200:
                    print(f"[top.gg] Sunucu sayısı gönderildi: {payload['server_count']}")
                else:
                    print(f"[top.gg] Gönderim başarısız: HTTP {response.status}")
    except Exception as exc:
        print(f"[top.gg] Gönderim hatası: {exc}")


@tasks.loop(minutes=30)
async def topgg_loop():
    await post_topgg_stats()


@topgg_loop.before_loop
async def before_topgg_loop():
    await bot.wait_until_ready()


# Load all cogs
cogs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cogs")
for filename in sorted(os.listdir(cogs_dir)):
    if filename.endswith(".py") and not filename.startswith("__"):
        bot.load_extension(f"cogs.{filename[:-3]}")


@bot.event
async def on_ready():
    print(Fore.CYAN + get_credits_banner() + Style.RESET_ALL)
    print(Fore.GREEN + f"Bot giriş yaptı: {bot.user}" + Style.RESET_ALL)

    # Update check runs once per startup; failures are non-fatal.
    bot.loop.create_task(check_for_updates())

    if config.TOP_GG_TOKEN and not topgg_loop.is_running():
        topgg_loop.start()

    # Base tables. Cogs create their own on load.
    await bot.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            bakiye INTEGER DEFAULT 0
        )
        """
    )
    await bot.execute(
        """
        CREATE TABLE IF NOT EXISTS testmode (
            guild_id INTEGER PRIMARY KEY
        )
        """
    )
    await bot.execute(
        """
        CREATE TABLE IF NOT EXISTS game_substitute_data (
            game_id TEXT,
            user_id INTEGER,
            PRIMARY KEY (game_id, user_id)
        )
        """
    )


async def check_for_updates():
    url = (
        f"https://raw.githubusercontent.com/{config.GITHUB_USER}/"
        f"{config.GITHUB_REPO}/main/version.txt"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return
                remote_version = (await response.text()).strip()
        if remote_version and remote_version != __version__:
            print(Fore.RED + "================================================")
            print(Fore.RED + "🔥 YENİ BİR GÜNCELLEME MEVCUT! 🔥")
            print(Fore.YELLOW + f"  Şu anki Sürüm: {__version__}")
            print(Fore.GREEN + f"  Yeni Sürüm:    {remote_version}")
            print(Fore.RED + "Lütfen GitHub üzerinden güncel versiyonu indirin.")
            print(Fore.RED + "================================================" + Style.RESET_ALL)
        else:
            print(Fore.GREEN + f"[Update Checker] Bot güncel! Sürüm: {__version__}")
    except Exception as exc:  # network errors must never stop the bot
        print(Fore.YELLOW + f"[Update Checker] Güncelleme kontrolü başarısız: {exc}")


if not TOKEN:
    raise SystemExit(
        "TOKEN bulunamadı. .env dosyasına TOKEN=... ekleyin (bkz. .env.example)."
    )

# Run the client
bot.run(TOKEN)
