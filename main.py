#!/usr/bin/env python3
import asyncio
import os

import aiosqlite
import aiohttp
from colorama import Fore, Style, init
from disnake import Intents
from disnake.ext import commands
from dotenv import load_dotenv

from core import config
from core.__credits__ import get_credits_banner, __version__

# Initialize colorama
init(autoreset=True)

load_dotenv()

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

if config.TOP_GG_TOKEN:
    import topgg

    bot.topggpy = topgg.DBLClient(bot, config.TOP_GG_TOKEN, autopost=True)

    @bot.event
    async def on_autopost_success():
        print(
            f"Posted server count ({bot.topggpy.guild_count}), "
            f"shard count ({bot.shard_count})"
        )


# Load all cogs
for filename in sorted(os.listdir(os.path.join(os.path.dirname(__file__), "cogs"))):
    if filename.endswith(".py"):
        bot.load_extension(f"cogs.{filename[:-3]}")


@bot.event
async def on_ready():
    print(Fore.CYAN + get_credits_banner() + Style.RESET_ALL)
    print(Fore.GREEN + f"Bot giriş yaptı: {bot.user}" + Style.RESET_ALL)

    # Update check runs once per startup; failures are non-fatal.
    bot.loop.create_task(check_for_updates())

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
