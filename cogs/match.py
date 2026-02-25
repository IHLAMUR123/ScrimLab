from disnake import Color, Embed
from disnake.ext.commands import Cog, slash_command

from core.match import start_queue
from core.embeds import error

class Match(Cog):
    """
    ⚔️;Matchmaking
    """

    def __init__(self, bot):
        self.bot = bot

    async def send_new_queues(self):
        await self.bot.wait_until_ready()
        channels = await self.bot.fetch("SELECT * FROM queuechannels")
        for data in channels:
            channel = self.bot.get_channel(data[0])
            if channel:
                try:
                    await channel.send(
                        embed=Embed(
                            title=":warning: Uyarı",
                            description="Bot Güncellenmiştir\n"
                                        "Bu Mesajdan Önceki Sıralar Çalışmayacaktır.",
                            color=Color.yellow()
                        )
                    )
                    await start_queue(self.bot, channel, data[2])
                except:
                    import traceback
                    print(traceback.format_exc())

    @Cog.listener()
    async def on_ready(self):
        await self.send_new_queues()

    @slash_command(name="başlat")
    async def start_slash(self, ctx):
        """
        İnhouse Sırası Başlat.
        """
        game_check = await self.bot.fetchrow("SELECT * FROM queuechannels WHERE channel_id = ?", ctx.channel.id)
        if not game_check:
            return await ctx.send(embed=error("Bu kanal bir sıra kanalı değildir."))
        try:
            await ctx.send("Oyun Başladı!")
        except:
            pass
        await start_queue(self.bot, ctx.channel, game_check[2], ctx.author)

def setup(bot):
    bot.add_cog(Match(bot))
