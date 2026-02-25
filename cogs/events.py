import traceback
from io import StringIO

from core import embeds
from disnake import Color, Embed, File, Game
from disnake.ext import commands, tasks
from disnake.ext.commands import Cog

from cogs.admin import leaderboard_persistent


class Events(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.persistent_lb.start()

    @tasks.loop(seconds=5)
    async def persistent_lb(self):
        await self.bot.wait_until_ready()

        data = await self.bot.fetch("SELECT * FROM persistent_lb")
        for entry in data:
            channel = self.bot.get_channel(entry[1])
            if not channel:
                continue
            msg = self.bot.get_message(entry[2])
            if not msg:
                msg = await channel.fetch_message(entry[2])
                if not msg:
                    continue
            if msg:
                embed = await leaderboard_persistent(self.bot, channel, entry[3])
                await msg.edit(embed=embed)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel):
        deletions = []
        setchannel = await self.bot.fetch("SELECT * FROM queuechannels WHERE channel_id = ?", channel.id)
        if setchannel:
            deletions.append("queuechannels")
        log_channels = await self.bot.fetch("SELECT * FROM winner_log_channel WHERE channel_id = ?", channel.id)
        if log_channels:
            deletions.append("winner_log_channel")
        top_ten = await self.bot.fetch("SELECT * FROM persistent_lb WHERE channel_id = ?", channel.id)
        if top_ten:
            deletions.append("persistent_lb")
        
        for deletion in deletions:
            await self.bot.execute("DELETE FROM " + deletion + " WHERE channel_id = ?", channel.id)

    @Cog.listener()
    async def on_message(self, msg):
        data = await self.bot.fetch("SELECT * FROM queuechannels")
        if not data:
            return

        channels = [channel[0] for channel in data]

        # This is designed to ignore all the messages sent from !start
    async def setuptable(self, bot):

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS queuechannels(
                channel_id INTEGER,
                region TEXT,
                game TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS games(
                game_id TEXT,
                lobby_id INTEGER,
                voice_red_id INTEGER,
                voice_blue_id INTEGER,
                red_role_id INTEGER, 
                blue_role_id INTEGER,
                queuechannel_id INTEGER,
                msg_id INTEGER,
                game TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS game_member_data(
                author_id INTEGER,
                role TEXT,
                team TEXT,
                game_id TEXT,
                queue_id INTEGER,
                channel_id INTEGER
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS points(
                guild_id INTEGER,
                user_id INTEGER,
                wins INTEGER,
                losses INTEGER,
                game TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS members_history(
                user_id INTEGER,
                game_id INTEGER,
                team TEXT,
                result TEXT,
                role TEXT,
                old_mmr TEXT,
                now_mmr TEXT,
                voted_team TEXT,
                game TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS winner_log_channel(
                channel_id INTEGER,
                guild_id INTEGER,
                game TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS game_categories(
                guild_id INTEGER,
                category_id INTEGER,
                game TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS ready_ups(
                game_id TEXT,
                user_id INTEGER
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS persistent_lb(
                guild_id INTEGER,
                channel_id INTEGER,
                msg_id INTEGER,
                game TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS mmr_rating(
                guild_id INTEGER,
                user_id INTEGER,
                mu TEXT,
                sigma TEXT,
                counter INTEGER,
                game TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS mvp_voting(
                guild_id INTEGER,
                user_id INTEGER,
                game_id TEXT,
                time TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS mvp_points(
                guild_id INTEGER,
                user_id INTEGER,
                votes INTEGER,
                game TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS queue_preference(
                guild_id INTEGER,
                preference INTEGER
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS switch_team_preference(
                guild_id INTEGER
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS duo_queue_preference(
                guild_id INTEGER
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_enables(
                guild_id INTEGER,
                command TEXT,
                role_id INTEGER
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS duo_queue(
                guild_id INTEGER,
                user1_id INTEGER, 
                user2_id INTEGER,
                game_id TEXT
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS testmode(
                guild_id INTEGER
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS igns(
                guild_id INTEGER,
                user_id INTEGER,
                game TEXT,
                ign TEXT
            )
            """
        )

        # Kalıcı Takım Sistemi Tabloları
        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS teams(
                team_id TEXT PRIMARY KEY,
                guild_id INTEGER,
                team_name TEXT,
                captain_id INTEGER,
                role_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS team_members(
                team_id TEXT,
                user_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_id, user_id)
            )
            """
        )

        await bot.execute(
            """
            CREATE TABLE IF NOT EXISTS team_stats(
                team_id TEXT PRIMARY KEY,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                elo INTEGER DEFAULT 1000
            )
            """
        )

    @Cog.listener()
    async def on_ready(self):
        print(r"""                  ██████╗░░█████╗░████████╗  ░█████╗░██╗░░██╗████████╗██╗███████╗
                  ██╔══██╗██╔══██╗╚══██╔══╝  ██╔══██╗██║░██╔╝╚══██╔══╝██║██╔════╝              
                  ██╔══██╗██╔══██╗╚══██╔══╝  ██╔══██╗██║░██╔╝╚══██╔══╝██║██╔════╝
                  ██████╦╝██║░░██║░░░██║░░░  ███████║█████═╝░░░░██║░░░██║█████╗░░
                  ██╔══██╗██║░░██║░░░██║░░░  ██╔══██║██╔═██╗░░░░██║░░░██║██╔══╝░░
                  ██████╦╝╚█████╔╝░░░██║░░░  ██║░░██║██║░╚██╗░░░██║░░░██║██║░░░░░
                  ╚═════╝░░╚════╝░░░░╚═╝░░░  ╚═╝░░╚═╝╚═╝░░╚═╝░░░╚═╝░░░╚═╝╚═╝░░░░░""")
        await self.setuptable(self.bot)
        await self.bot.change_presence(activity=Game(name="5v5 Özel Oyunlar Ve Dahası.."))

    @Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
            pass
        elif isinstance(
            error, (commands.MissingRequiredArgument, commands.BadArgument)
        ):
            await ctx.send(embed=embeds.error(str(error)))
        else:
            await self.bot.wait_until_ready()

            if self.bot.user.id == 1452380258933149958:  # Testing bot ID
                channel = self.bot.get_channel(
                    1452690176760479755
                )  # Testing Server Channel
            else:
                channel = self.bot.get_channel(
                    1452690176760479755
                )  # Server Support Channel

            if isinstance(ctx, commands.Context):
                command = ctx.command
            else:
                command = ctx.data.name

            e = Embed(
                title="Exception!",
                description=f"Guild: {ctx.guild.name}\nGuildID: {ctx.guild.id}\nUser: {ctx.author}\nUserID: {ctx.author.id}\n\nError: {error}\nCommand: {command}",
                color=Color.blurple(),
            )
            etype = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(etype, error, trace)
            traceback_text = "".join(lines)

            await channel.send(
                embed=e,
                file=File(filename="traceback.txt", fp=StringIO(f"{traceback_text}\n")),
            )

    @Cog.listener()
    async def on_slash_command_error(self, ctx, error):
        await self.on_command_error(ctx, error)

    @Cog.listener('on_message')
    async def delete_queue_messages(self, msg):
        data = await self.bot.fetch("SELECT * FROM queuechannels")
        if not data:
            return

        channels = [channel[0] for channel in data]

        # This is designed to ignore all the messages sent from !start
        


    @Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot or msg.guild:
            return

        data = await self.bot.fetch("SELECT * FROM mvp_voting")
        for entry in data:
            if msg.author.id == entry[1]:
                if msg.content.isnumeric():
                    if int(msg.content) > 10:
                        return await msg.channel.send(embed=embeds.error("There are only 10 summoners to vote."))
                    all_members = await self.bot.fetch("SELECT * FROM members_history WHERE game_id = ?", entry[2])
                    for i, member in enumerate(all_members):
                        if i+1 == int(msg.content):
                            if member[0] == msg.author.id:
                                return await msg.channel.send(embed=embeds.error("Kendini Oylayamazsın."))
                            mvp_data = await self.bot.fetchrow("SELECT * FROM mvp_points WHERE user_id = ? and game = ?", member[0], member[8])
                            if mvp_data:
                                await self.bot.execute(
                                    "UPDATE mvp_points SET votes = $1 WHERE guild_id = ? and user_id = ? and game = ?",
                                    mvp_data[2] + 1, mvp_data[0], mvp_data[1], member[8]
                                )
                            else:
                                await self.bot.execute(
                                    "INSERT INTO mvp_points(guild_id, user_id, votes, game) VALUES($1, $2, $3, $4)",
                                    entry[0],
                                    member[0],
                                    1,
                                    member[8]
                                )
                            await self.bot.execute(
                                "DELETE FROM mvp_voting WHERE user_id = ? and guild_id = ?",
                                msg.author.id, entry[0]
                            )
                            await msg.channel.send(embed=embeds.success("Oy Kullandığın İçin Teşekkürler."))

    @Cog.listener('on_raw_member_remove')
    async def clear_member_entries(self, payload):
        await self.bot.wait_until_ready()
        data = await self.bot.fetch("SELECT * FROM game_member_data")
        if data:
            for entry in data:
                channel = self.bot.get_channel(entry[5])
                if channel:
                    if channel.guild.id == payload.guild_id:
                        await self.bot.execute("DELETE FROM game_member_data WHERE game_id = ? and author_id = ?", entry[3], payload.user.id)
                        await self.bot.execute("DELETE FROM ready_ups WHERE game_id = ? and user_id = ?", entry[3], payload.user.id)

        
        await self.bot.execute("DELETE FROM igns WHERE guild_id = ? and user_id = ?", payload.guild_id, payload.user.id)
        await self.bot.execute("DELETE FROM mvp_points WHERE guild_id = ? and user_id = ?", payload.guild_id, payload.user.id)
        await self.bot.execute("DELETE FROM points WHERE guild_id = ? and user_id = ?", payload.guild_id, payload.user.id)
        await self.bot.execute("DELETE FROM mmr_rating WHERE guild_id = ? and user_id = ?", payload.guild_id, payload.user.id)


def setup(bot):
    bot.add_cog(Events(bot))
