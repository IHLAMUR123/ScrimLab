from core import embeds, buttons, selectmenus
from disnake import TextChannel, Embed, Color, OptionChoice, SelectOption
from disnake.ext.commands import Cog, command, slash_command, Param


class ChannelCommands(Cog):
    """
    ⚙️;Channel Setup
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_slash_command_check(self, inter):
        # checks that apply to every command in here

        if inter.author.guild_permissions.administrator:
            return True

        await inter.send(
            embed=embeds.error(
                "You need to have **administrator** permission to run this command."
            )
        )
        return False

    async def cog_check(self, ctx):
        # checks that apply to every command in here

        if ctx.author.guild_permissions.administrator:
            return True

        await ctx.send(
            embed=embeds.error(
                "You need to have **administrator** permission to run this command."
            )
        )
        return False

    @command(aliases=["channel"])
    async def setchannel(self, ctx, channel: TextChannel, game="lol"):
        if game.lower() not in ['lol']:
            return await ctx.send(embed=embeds.error("Oyun sadece 'lol' olabilir."))

        data = await self.bot.fetchrow(
            "SELECT * FROM queuechannels WHERE channel_id = ?",
            channel.id
        )
        if data:
            return await ctx.edit_original_message(
                embed=embeds.error(
                    f"{channel.mention} is already setup as the queue channel."
                )
            )

        if game == 'lol':
            regions =  ["BR", "EUNE", "EUW", "LA", "LAS", "NA", "OCE", "RU", "TR", "JP"]
        else:
            regions = []

        if regions:
            options = []
            for region in regions:
                options.append(SelectOption(label=region, value=region.lower()))
            async def Function(inter, vals, *args):
                view = buttons.ConfirmationButtons(inter.author.id)
                await inter.edit_original_message(
                    embed=Embed(title=":warning: Uyarı", description=f"{channel.mention}kanalındaki mesajlar, kuyruk kanalını temiz tutmak için otomatik olarak silinecektir, devam etmek istiyor musunuz?", color=Color.yellow()),
                    view=view,
                    content=""
                )
                await view.wait()
                if view.value is None:
                    return
                elif view.value:
                    pass
                else:
                    return await inter.edit_original_message(embed=embeds.success("İşlem iptal edildi."))

                await self.bot.execute(
                    "INSERT INTO queuechannels(channel_id, region, game) VALUES($1, $2, $3)", channel.id, vals[0], game
                )

                await inter.edit_original_message(
                    embed=embeds.success(
                        f"{channel.mention} was successfully set as queue channel."
                    )
                )

            await ctx.send(content="Select a region for the queue.", view=selectmenus.SelectMenuDeploy(self.bot, ctx.author.id, options, 1, 1, Function))
        else:
            
            await self.bot.execute(
                "INSERT INTO queuechannels(channel_id, region, game) VALUES($1, $2, $3)", channel.id, "none", game
            )
            await ctx.send(embed=embeds.success(f"{channel.mention} was successfully set as queue channel."))

    @slash_command(name="setchannel")
    async def setchannel_slash(self, ctx, channel: TextChannel, game = Param(default="lol", choices={"League Of Legends": "lol"})):
        """
        Set a channel to be used as the queue.
        """
        await self.setchannel(ctx, channel, game)

    @command()
    async def setregion(self, ctx, queue_channel: TextChannel, region):
        if region.upper() not in [ "BR", "EUNE", "EUW", "LA", "LAS", "NA", "OCE", "RU", "TR", "JP"]:
            return await ctx.send(embed=embeds.error("Lütfen geçerli bir bölge girin."))

        data = await self.bot.fetchrow(f"SELECT * FROM queuechannels WHERE channel_id = ? and game = ?", queue_channel.id, 'lol')
        if not data:
            return await ctx.send(embed=embeds.error(f"{queue_channel.mention} is not a queue channel for league of legends."))
        
        await self.bot.execute("UPDATE queuechannels SET region = ? WHERE channel_id = ?", region, queue_channel.id)
        await ctx.send(embed=embeds.success("Kuyruk kanalının bölgesi başarıyla güncellendi."))

    @slash_command(name="setregion")
    async def setregion_slash(self, ctx, queue_channel: TextChannel, region= Param(choices=[
        OptionChoice("EUW", "euw"),
        OptionChoice("NA", 'na'),
        OptionChoice("BR", 'br'),
        OptionChoice("EUNE", 'eune'),
        OptionChoice("LA", 'la'),
        OptionChoice("LAS", 'las'),
        OptionChoice("OCE", 'oce'),
        OptionChoice("RU", 'ru'),
        OptionChoice("TR", 'tr'),
        OptionChoice("JP", 'jp')]),
        ):
            """
            Update a region for a league of legends queue channel.
            """
            await self.setregion(ctx, queue_channel, region)
            
    @command()
    async def setwinnerlog(self, ctx, channel: TextChannel, game="lol"):
        if game not in ['lol']:
            return await ctx.send(embed=embeds.error("Oyun sadece 'lol' olabilir."))
        data = await self.bot.fetchrow(
            f"SELECT * FROM winner_log_channel WHERE channel_id = {channel.id} and game = '{game}'"
        )
        if data:
            if data[0] == channel.id:
                return await ctx.send(
                    embed=embeds.error(
                        f"{channel.mention} is already setup as the match-history channel for this game."
                    )
                )

        else:
            await self.bot.execute(
                "INSERT INTO winner_log_channel(guild_id, channel_id, game) VALUES($1, $2, $3)",
                ctx.guild.id,
                channel.id,
                game
            )

        await ctx.send(
            embed=embeds.success(
                f"{channel.mention} was successfully set as match-history channel."
            )
        )

    @slash_command(name="setwinnerlog")
    async def setwinnerlog_slash(self, ctx, channel: TextChannel, game=Param(default="lol", choices={"League Of Legends": "lol"})):
        """
        Set a channel to send the game results.
        """
        await self.setwinnerlog(ctx, channel, game)


def setup(bot):
    bot.add_cog(ChannelCommands(bot))
