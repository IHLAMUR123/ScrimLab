import sqlite3
from disnake.ext import commands

class Database(commands.Cog):
    def __init__(self, bot, path="main.sqlite"):
        self.bot = bot
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.init_tables()

    def init_tables(self):
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tournament_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            active INTEGER,
            round INTEGER
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tournament_players (
            player_id TEXT PRIMARY KEY,
            nick TEXT,
            discord_id INTEGER,
            source TEXT,
            eliminated INTEGER
        )
        """)

        self.conn.commit()

    def execute(self, q, params=()):
        cur = self.conn.cursor()
        cur.execute(q, params)
        self.conn.commit()
        return cur

    def fetchone(self, q, params=()):
        return self.execute(q, params).fetchone()

    def fetchall(self, q, params=()):
        return self.execute(q, params).fetchall()

def setup(bot):
    bot.add_cog(Database(bot))
