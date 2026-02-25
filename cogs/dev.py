from core.embeds import error, success
from disnake import Game
from disnake.ext.commands import Cog, group, slash_command


class Dev(Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.devs = [655498457083150342]

    async def cog_check(self, ctx) -> bool:
        if not ctx.author.id in self.devs:
            await ctx.send(embed=error("Bu komutu kullanamazsınız."))
            return False
        return True

    async def cog_slash_command_check(self, inter) -> bool:
        if not inter.author.id in self.devs:
            await inter.send(embed=error("Bu komutu kullanamazsınız."))
            return False
        return True

    @group()
    async def dev(self, ctx):
        pass

    @slash_command(name="dev", guild_ids=[1458071278689845283])
    async def dev_slash(self, ctx):
        pass

    @dev_slash.sub_command(name="durum")
    async def dev_status(self, ctx, status):
        """
        Botun durumunu değiştirir.
        """

        await self.bot.change_presence(activity=Game(name=status))
        await ctx.send(embed=success("Durum başarıyla değiştirildi."))

    @dev.command()
    async def status(self, ctx, status):
        await self.dev_status(ctx, status)


def setup(bot):
    bot.add_cog(Dev(bot))
