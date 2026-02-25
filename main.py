#!/usr/bin/env python3
import os
import topgg

import aiosqlite
from disnake import Intents
from disnake.ext import commands
from dotenv import load_dotenv
import base64
import aiohttp
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Import credits and version
from core.__credits__ import get_credits_banner, __version__, __author__, _verify_integrity

load_dotenv()

TOKEN = os.getenv("TOKEN")
dbl_token = os.getenv("TOP_GG_TOKEN")
PREFIX = "!"


class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not _verify_integrity():
            raise RuntimeError("CRITICAL ERROR: Core system integrity compromised. Do not tamper with core/ files.")
        self.game = "lol"
        self.role_emojis = {
            'top': "<:Top:1454081617382477908>",
            'jungle': "<:Jungle:1454081696327667836>",
            'mid': "<:Mid:1454081643374448836>",
            'support': "<:Support:1454081735087231048>",
            'adc': "<:ADC:1454081581445812244>",
            'flex': "❓"
        }

    async def commit(self):
        async with aiosqlite.connect("db/main.sqlite") as db:
            await db.commit()

    async def execute(self, query, *values):
        async with aiosqlite.connect("db/main.sqlite") as db:
            async with db.cursor() as cur:
                await cur.execute(query, tuple(values))
            await db.commit()

    async def executemany(self, query, values):
        async with aiosqlite.connect("db/main.sqlite") as db:
            async with db.cursor() as cur:
                await cur.executemany(query, values)
            await db.commit()

    async def fetchval(self, query, *values):
        async with aiosqlite.connect("db/main.sqlite") as db:
            async with db.cursor() as cur:
                exe = await cur.execute(query, tuple(values))
                val = await exe.fetchone()
            return val[0] if val else None

    async def fetchrow(self, query, *values):
        async with aiosqlite.connect("db/main.sqlite") as db:
            async with db.cursor() as cur:
                exe = await cur.execute(query, tuple(values))
                row = await exe.fetchmany(size=1)
            if len(row) > 0:
                row = [r for r in row[0]]
            else:
                row = None
            return row

    async def fetchmany(self, query, size, *values):
        async with aiosqlite.connect("db/main.sqlite") as db:
            async with db.cursor() as cur:
                exe = await cur.execute(query, tuple(values))
                many = await exe.fetchmany(size)
            return many

    async def fetch(self, query, *values):
        async with aiosqlite.connect("db/main.sqlite") as db:
            async with db.cursor() as cur:
                exe = await cur.execute(query, tuple(values))
                all = await exe.fetchall()
            return all

    async def check_testmode(self, guild_id):
        data = await self.fetchrow(f"SELECT * FROM testmode WHERE guild_id = {guild_id}")
        if data:
            return True
        return False


# Enabling message content intent for the bot to support prefix commands.
intents = Intents.default()
intents.message_content = True
intents.members = True

bot = MyBot(
    intents=intents, 
    command_prefix=PREFIX, 
    test_guilds=[1458071278689845283] 
)
bot.remove_command("help")
if dbl_token:
    bot.topggpy = topgg.DBLClient(bot, dbl_token, autopost=True)


@bot.event
async def on_autopost_success():
    print(
        f"Posted server count ({bot.topggpy.guild_count}), shard count ({bot.shard_count})"
    )

# Load all cogs
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        bot.load_extension(f"cogs.{filename[:-3]}")
@bot.event
async def on_ready():
    # Print the custom non-deletable banner
    print(Fore.CYAN + get_credits_banner() + Style.RESET_ALL)
    print(Fore.GREEN + f"Bot giriş yaptı: {bot.user}" + Style.RESET_ALL)
    
    # Run update check
    bot.loop.create_task(check_for_updates())
    
    # Bot açıldığında veritabanında gerekli tabloları kontrol eder/oluşturur
    
    # users tablosunu oluştur (eğer yoksa)
    await bot.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            bakiye INTEGER DEFAULT 0
        )
    """)
    
    # Hata aldığın testmode tablosu da eksik olabilir, onu da garantiye alalım:
    await bot.execute("""
        CREATE TABLE IF NOT EXISTS testmode (
            guild_id INTEGER PRIMARY KEY
        )
    """)
    
    # Yedek oyuncu tablosu
    await bot.execute("""
        CREATE TABLE IF NOT EXISTS game_substitute_data (
            game_id TEXT,
            user_id INTEGER,
            PRIMARY KEY (game_id, user_id)
        )
    """)
    
async def check_for_updates():
    # This will check for updates against the GitHub repository
    # Placeholder credentials - will be updated based on user input
    GITHUB_USER = "IHLAMUR123"
    GITHUB_REPO = "ScrimLab"
    
    # Currently pointing to the main branch version.txt
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.txt"
    
    # If the user wishes to use the GitHub API releases instead, we will update the url below:
    # url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
    
    # We will test a simple version.txt fetch for now:
    if GITHUB_REPO != "PLACEHOLDER_REPO":
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        remote_version = (await response.text()).strip()
                        if remote_version != __version__:
                            print(Fore.RED + f"================================================")
                            print(Fore.RED + f"🔥 YENİ BİR GÜNCELLEME MEVCUT! 🔥")
                            print(Fore.YELLOW + f"  Şu anki Sürüm: {__version__}")
                            print(Fore.GREEN + f"  Yeni Sürüm:    {remote_version}")
                            print(Fore.RED + f"Lütfen GitHub üzerinden güncel versiyonu indirin.")
                            print(Fore.RED + f"================================================" + Style.RESET_ALL)
                        else:
                            print(Fore.GREEN + f"[Update Checker] Bot güncel! Sürüm: {__version__}")
        except Exception as e:
            print(Fore.YELLOW + f"[Update Checker] Güncelleme kontrolü başarısız oldu: {e}")

# Run the client
bot.run(TOKEN)
