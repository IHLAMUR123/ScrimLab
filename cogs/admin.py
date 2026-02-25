from disnake import Color, Embed, Member, OptionChoice, Role, TextChannel, PermissionOverwrite, SelectOption
from disnake.ext.commands import Cog, Context, Param, group, slash_command
import disnake

from trueskill import Rating, backends, rate
from cogs.win import Win
from core.embeds import error, success
from core.buttons import ConfirmationButtons, LinkButton
from core.selectmenus import SelectMenuDeploy
from core.match import start_queue

async def leaderboard_persistent(bot, channel, game):
    user_data = await bot.fetch(
        """SELECT *, (points.wins + 0.0) / (MAX(points.wins + points.losses, 1.0) + 0.0) AS percentage 
           FROM points WHERE guild_id = ? and game = ?""",
        channel.guild.id, game
    )
    if user_data:
        user_data = sorted(list(user_data), key=lambda x: x[4], reverse=True)
        user_data = sorted(list(user_data), key=lambda x: x[2], reverse=True)
        # user_data = sorted(list(user_data), key=lambda x: float(x[2]) - (2 * float(x[3])), reverse=True)

    embed = Embed(title=f"🏆 Sıralama", color=Color.yellow())
    if channel.guild.icon:
        embed.set_thumbnail(url=channel.guild.icon.url)

    async def add_field(data) -> None:
        user_history = await bot.fetch(
            "SELECT role FROM members_history WHERE user_id = ? and game = ?",
            data[1], game
        )
        if user_history and game != 'other':
            if game == 'lol':
                roles_players = {
                    'top': 0,
                    'jungle': 0,
                    'mid': 0,
                    'support': 0,
                    'adc': 0
                }

            for history in user_history:
                if history[0]:
                    roles_players[history[0]] += 1
            
            most_played_role = max(roles_players, key = lambda x: roles_players[x])
            if not roles_players[most_played_role]:
                most_played_role = "<:fill:1066868480537800714>"
            else:
                most_played_role = bot.role_emojis[most_played_role]
        else:
            most_played_role = "<:fill:1066868480537800714>"

        st_pref = await bot.fetchrow(
            "SELECT * FROM switch_team_preference WHERE guild_id = ?",
            channel.guild.id
        )
        if not st_pref:
            mmr_data = await bot.fetchrow(
                "SELECT * FROM mmr_rating WHERE user_id = ? and guild_id = ? and game = ?",
                data[1], channel.guild.id, game
            )
            if mmr_data:
                skill = float(mmr_data[2]) - (2 * float(mmr_data[3]))
                if mmr_data[4] >= 10:
                    display_mmr = f"{int(skill*100)}"
                else:
                    display_mmr = f"{mmr_data[4]}/10GP"
            else:
                display_mmr = f"0/10GP"
        else:
            display_mmr = ""

        if i+1 == 1:
            name = "🥇"
        elif i+1 == 2:
            name = "🥈"
        elif i+1 == 3:
            name = "🥉"
        else:
            name = f"#{i+1}"
        
        member = channel.guild.get_member(data[1])
        if member:
            member_name = member.name
        else:
            member_name = "Unknown Member"

        embed.add_field(
            name=name,
            value=f"{most_played_role} `{member_name}   {display_mmr} {data[2]}W {data[3]}L {round(data[5]*100)}% WR`",
            inline=False,
        )

    if not user_data:
        embed.description = "Henüz Yeteri Kadar Veri Yok"
    for i, data in enumerate(user_data):

        if i <= 9:
            await add_field(data)

    return embed

class Admin(Cog):
    """
    🤖;Admin
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        if ctx.author.guild_permissions.administrator:
            return True
        
        if ctx.command.qualified_name in ['admin', 'admin reset']:
            return True

        author_role_ids = [r.id for r in ctx.author.roles]
        admin_enable = await self.bot.fetch(
            "SELECT * FROM admin_enables WHERE guild_id = ? and command = ?",
            ctx.guild.id, ctx.command.qualified_name
        )
        for data in admin_enable:
            if data[2] in author_role_ids:
                return True
        
        await ctx.send(
            embed=error("Bu komutu kullanmak için **yönetici** izinlerine ihtiyacınız var.")
        )
        return False

    async def cog_slash_command_check(self, inter) -> bool:
        if inter.author.guild_permissions.administrator:
            return True

        if inter.application_command.qualified_name in ['admin', 'admin reset']:
            return True

        author_role_ids = [r.id for r in inter.author.roles]
        admin_enable = await self.bot.fetch(
            "SELECT * FROM admin_enables WHERE guild_id = ? and command = ?",
            inter.guild.id, inter.application_command.qualified_name
        )
        for data in admin_enable:
            if data[2] in author_role_ids:
                return True

        await inter.send(
            embed=error("Bu komutu kullanmak için **yönetici** izinlerine ihtiyacınız var.")
        )
        return False

    @group()
    async def admin(self, ctx):
        pass

    @admin.command()
    async def user_dequeue(self, ctx, member: Member):
        member_data = await self.bot.fetch(
            "SELECT * FROM game_member_data WHERE author_id = ?", member.id
        )
        for entry in member_data:
            game_data = await self.bot.fetchrow(
                "SELECT * FROM games WHERE game_id = ? ", entry[3]
            )
            if not game_data:
                await self.bot.execute(
                    "DELETE FROM game_member_data WHERE author_id = ? ", member.id
                )
                await self.bot.execute(
                    "DELETE FROM ready_ups WHERE game_id = ?",
                    entry[3]
                )

        await ctx.send(embed=success(f"{member.mention} was removed from all active queues. They may still show up in queue embed."))

    @admin.command()
    async def winner(self, ctx, role: Role):
        role_name = role.name
        game_id = role_name.replace("Kırmızı Takım: ", "").replace("Mavi Takım: ", "")
        game_data = await self.bot.fetchrow(
            "SELECT * FROM games WHERE game_id = ?",
            game_id
        )

        if game_data:
            if "Kırmızı Takım" in role_name:
                team = "red"
            else:
                team = "blue"

            await ctx.send(embed=success(f"**{game_id}** Kodlu maç sonuçlandı."))

            channel = self.bot.get_channel(game_data[1])
            await Win.process_win(self, channel, ctx.author, True, team)

        else:
            await ctx.send(embed=error("Oyun bulunamadı."))

    @admin.command()
    async def change_winner(self, ctx, game_id: str, team: str):
        if team.lower() not in ["red", "blue"]:
            await ctx.send(embed=error("Geçersiz ekip girişi alındı."))
            return

        member_data = await self.bot.fetch(
            "SELECT * FROM members_history WHERE game_id = ?",
            game_id
        )
        if not member_data:
            return await ctx.send(embed=error(f"Game **{game_id}** was not found."))

        for member in member_data:
            if member[3] == "won":
                if member[2] == team.lower():
                    return await ctx.send(
                        embed=error(f"{team.capitalize()} is already the winner.")
                    )

        wrong_voters = []
        winner_rating = []
        loser_rating = []
        for member_entry in member_data:
            user_data = await self.bot.fetchrow(
                "SELECT * FROM points WHERE user_id = ? and guild_id = ? and game = ?",
                member_entry[0], ctx.guild.id, member_entry[8]
            )

            if member_entry[7] != "none":
                if member_entry[7] != team.lower():
                    wrong_voters.append(member_entry[0])
            
            rating = Rating(mu=float(member_entry[5].split(':')[0]), sigma=float(member_entry[5].split(':')[1]))

            if member_entry[2] == team.lower():
                await self.bot.execute(
                    "UPDATE members_history SET result = $1 WHERE user_id = ? and game_id = ?",
                    "won", member_entry[0], game_id
                )

                await self.bot.execute(
                    "UPDATE points SET wins = $1, losses = $2 WHERE user_id = $3 and guild_id = $4 and game = $5",
                    user_data[2] + 1, user_data[3] - 1, member_entry[0], ctx.guild.id, member_entry[8]
                )

                winner_rating.append(
                    {"user_id": member_entry[0], "rating": rating}
                )
            else:
                await self.bot.execute(
                    "UPDATE members_history SET result = $1 WHERE user_id = ? and game_id = ?",
                    "lost", member_entry[0], game_id
                )

                await self.bot.execute(
                    "UPDATE points SET wins = $1, losses = $2 WHERE user_id = $3 and guild_id = $4 and game = $5",
                    user_data[2] - 1, user_data[3] + 1, member_entry[0], ctx.guild.id, member_entry[8]
                )

                loser_rating.append(
                    {"user_id": member_entry[0], "rating": rating}
                )
            
        backends.choose_backend("mpmath")
            
        updated_rating = rate(
            [[x['rating'] for x in winner_rating], [x['rating'] for x in loser_rating]],
            ranks=[0, 1]
        )
        
        for i, new_rating in enumerate(updated_rating[0]):
            counter = await self.bot.fetchrow(
                "SELECT counter FROM mmr_rating WHERE user_id = ? and guild_id = ? and game = ?",
                winner_rating[i]['user_id'], ctx.guild.id, member_entry[8]
            )
            await self.bot.execute(
                "UPDATE mmr_rating SET mu = $1, sigma = $2, counter = $3 WHERE user_id = ? and guild_id = ? and game = ?",
                str(new_rating.mu), str(new_rating.sigma), counter[0] + 1, winner_rating[i]['user_id'], ctx.guild.id, member_entry[8]
            )
            await self.bot.execute(
                "UPDATE members_history SET now_mmr = $1 WHERE user_id = ? and game_id = ?",
                f"{str(new_rating.mu)}:{str(new_rating.sigma)}", winner_rating[i]['user_id'], game_id
            )

        for i, new_rating in enumerate(updated_rating[1]):
            counter = await self.bot.fetchrow(
                "SELECT counter FROM mmr_rating WHERE user_id = ? and guild_id = ? and game = ?",
                loser_rating[i]['user_id'], ctx.guild.id, member_entry[8]
            )
            await self.bot.execute(
                "UPDATE mmr_rating SET mu = $1, sigma = $2, counter = $3 WHERE user_id = ? and guild_id = ? and game = ?",
                str(new_rating.mu), str(new_rating.sigma), counter[0] + 1, loser_rating[i]['user_id'], ctx.guild.id, member_entry[8]
            )
            await self.bot.execute(
                "UPDATE members_history SET now_mmr = $1 WHERE user_id = ? and game_id = ?",
                f"{str(new_rating.mu)}:{str(new_rating.sigma)}", loser_rating[i]['user_id'], game_id
            )

        if wrong_voters:
            wrong_voters_embed = Embed(
                title="Wrong Voters",
                description="These player(s) purposely voted for the wrong winning team.\n" + "\n".join(f"{i+1}. <@{x}>" for i, x in enumerate(wrong_voters)),
                color=Color.yellow()
            )
        
            await ctx.send(embeds=[success("Oyunun kazananı değiştirildi."), wrong_voters_embed])
        else:
            await ctx.send(embed=success("Oyunun kazananı değiştirildi."))
        
        log_channel_id = await self.bot.fetchrow(
            "SELECT * FROM winner_log_channel WHERE guild_id = ? and game = ?",
            ctx.guild.id, member_entry[8]
        )
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id[0])
            if log_channel:
                mentions = (
                    f"🔴 Kırmızı Takım: "
                    + ", ".join(f"<@{data[0]}>" for data in member_data if data[2] == "red")
                    + "\n🔵 Mavi Takım: "
                    + ", ".join(
                        f"<@{data[0]}>" for data in member_data if data[2] == "blue"
                    )
                )

                embed = Embed(
                    title=f"Game results changed!",
                    description=f"Game **{game_id}**'s results were changed!\n\nResult: **{team.capitalize()} team Won!**",
                    color=Color.blurple(),
                )
                await log_channel.send(mentions, embed=embed)

    @admin.command()
    async def void(self, ctx, game_id):
        game_data = await self.bot.fetchrow(
            "SELECT * FROM games WHERE game_id = ?",
            game_id
        )
        if not game_data:
            return await ctx.send(embed=error("Oyun bulunamadı."))
        
        await self.bot.execute("DELETE FROM games WHERE game_id = ?", game_id)
        await self.bot.execute("DELETE FROM game_member_data WHERE game_id = ?", game_id)
        await self.bot.execute("DELETE FROM ready_ups WHERE game_id = ?", game_id)

        try:
            for category in ctx.guild.categories:
                if category.name == f"Maç: {game_data[0]}":
                    await category.delete()

            red_channel = self.bot.get_channel(game_data[2])
            await red_channel.delete()

            blue_channel = self.bot.get_channel(game_data[3])
            await blue_channel.delete()

            red_role = ctx.guild.get_role(game_data[4])
            await red_role.delete()

            blue_role = ctx.guild.get_role(game_data[5])
            await blue_role.delete()

            lobby = self.bot.get_channel(game_data[1])
            await lobby.delete()
        except:
            await ctx.send(embed=error("Oyun kanalları ve rolleri silinemiyor. Lütfen bunları manuel olarak kaldırın."))

        await ctx.send(embed=success(f"All records for Game **{game_id}** were deleted."))

    @admin.command()
    async def cancel(self, ctx, member: Member):
        member_data = await self.bot.fetchrow(
            "SELECT * FROM game_member_data WHERE author_id = ?",
            member.id
        )
        if member_data:
            game_id = member_data[3]
            game_data = await self.bot.fetchrow(
                "SELECT * FROM games WHERE game_id = ?",
                game_id
            )

            for category in ctx.guild.categories:
                if category.name == f"Maç: {game_data[0]}":
                    await category.delete()

            red_channel = self.bot.get_channel(game_data[2])
            await red_channel.delete()

            blue_channel = self.bot.get_channel(game_data[3])
            await blue_channel.delete()

            red_role = ctx.guild.get_role(game_data[4])
            await red_role.delete()

            blue_role = ctx.guild.get_role(game_data[5])
            await blue_role.delete()

            lobby = self.bot.get_channel(game_data[1])
            await lobby.delete()

            await self.bot.execute("DELETE FROM games WHERE game_id = ?", game_id)
            await self.bot.execute(
                "DELETE FROM game_member_data WHERE game_id = ?",
                game_id
            )

            await ctx.send(
                embed=success(f"Game **{game_id}** was successfully cancelled.")
            )

        else:
            await ctx.send(
                embed=error(f"{member.mention} oyundaki biri değil.")
            )

    @admin.group()
    async def reset(self, ctx):
        pass
    
    @reset.command(aliases=['lb'])
    async def leaderboard(self, ctx):
        data = await self.bot.fetch("SELECT * FROM points WHERE guild_id = ?", ctx.guild.id)
        if not data:
            return await ctx.send(embed=error("Silinecek kayıt yok"))
        
        view = ConfirmationButtons(ctx.author.id)
        await ctx.send(
            "This will reset all member's wins, losses, MMR and MVP votes back to 0. Are you sure?",
            view=view
        )
        await view.wait()
        if view.value:
            await self.bot.execute("UPDATE mvp_points SET votes = 0 WHERE guild_id = ?", ctx.guild.id)
            await self.bot.execute("UPDATE points SET wins = 0, losses = 0 WHERE guild_id = ?", ctx.guild.id)
            await self.bot.execute("UPDATE mmr_rating SET counter = 0, mu = 25.0, sigma = 8.33333333333333 WHERE guild_id = ?", ctx.guild.id)
            await ctx.send(embed=success("Tüm galibiyetleri, mmr ve mvp oylarını başarıyla sıfırlayın"))
        else:
            await ctx.send(embed=success("İşlem iptal edildi."))
    
    @reset.command()
    async def queue(self, ctx, game_id):
        game_data = await self.bot.fetchrow(
            "SELECT * FROM games WHERE game_id = ?",
            game_id
        )
        if game_data:
            return await ctx.send(embed=error("Devam eden bir oyunu sıfırlayamazsınız.Devam eden bir oyunu iptal etmek için lütfen `/admin cancel [üye]` komutunu kullanın"))

        member_data = await self.bot.fetchrow(
            "SELECT * FROM game_member_data WHERE game_id = ?", game_id
        )
        if member_data:
            await self.bot.execute(
                "DELETE FROM game_member_data WHERE game_id = ? ", game_id
            )
            await ctx.send(embed=success(f"Game **{game_id}** queue was refreshed."))
        else:
            await ctx.send(embed=error(f"Game **{game_id}** was not found."))
    
    @reset.command()
    async def user(self, ctx, member: Member):
        data = await self.bot.fetch(
            "SELECT * FROM points WHERE guild_id = ? and user_id = ?",
            ctx.guild.id, member.id
        )
        if not data:
            return await ctx.send(embed=error("Silinecek kayıt yok"))
        
        view = ConfirmationButtons(ctx.author.id)
        await ctx.send(
            f"This will reset all {member.display_name}'s wins, losses, MMR and MVP votes back to 0. Are you sure?",
            view=view
        )
        await view.wait()
        if view.value:
            await self.bot.execute("UPDATE mvp_points SET votes = 0 WHERE guild_id = ? and user_id = ?", ctx.guild.id, member.id)
            await self.bot.execute("UPDATE points SET wins = 0, losses = 0 WHERE guild_id = ? and user_id = ?", ctx.guild.id, member.id)
            await self.bot.execute("UPDATE mmr_rating SET counter = 0, mu = 25.0, sigma = 8.33333333333333 WHERE guild_id = ? and user_id = ?", ctx.guild.id, member.id)
            await ctx.send(embed=success(f"Successfully reset all wins, mmr and mvp votes of {member.display_name}"))
        else:
            await ctx.send(embed=success("İşlem iptal edildi."))

    # SLASH COMMANDS

    @slash_command(name="yönetici")
    async def admin_slash(self, ctx):
        pass
    
    @admin_slash.sub_command(name="ver")
    async def grant(
        self,
        ctx, 
        role: Role, 
        command = Param(
            choices=[
                OptionChoice('sıralama sıfırla', 'admin reset leaderboard'),
                OptionChoice('kullanıcı sırası sil', 'user_dequeue'),
                OptionChoice('sıra sıfırla', 'admin reset queue'),
                OptionChoice('kazanan değiştir', 'admin change_winner'),
                OptionChoice('kazanan belirle', 'admin winner'),
                OptionChoice('oyun iptal', 'admin cancel'),
                OptionChoice('oyun sil', 'admin void'),
                OptionChoice('sbmm', 'admin sbmm'),
                OptionChoice('üst on', 'admin top_ten'),
                OptionChoice('sıra tercihi', 'admin queue_preference'),
            ]
        ), 
    ):
        """
        Bir rolün belirli bir yönetici komutunu çalıştırmasına izin verin..
        """
        data = await self.bot.fetchrow(
            "SELECT * FROM admin_enables WHERE guild_id = ? and role_id = ? and command = ?",
            ctx.guild.id, role.id, command
        )
        if data:
            return await ctx.send(
                embed=error(f"{role.mention} zaten erişime sahip.")
            )
        
        await ctx.response.defer(ephemeral=True)
        await self.bot.execute(
            "INSERT INTO admin_enables(guild_id, command, role_id) VALUES(?,?,?)",
            ctx.guild.id,
            command,
            role.id
        )
        await ctx.send(embed=success(f"Command enabled for {role.mention} successfully."))
    
    @admin_slash.sub_command(name="kaldır")
    async def revoke(
        self,
        ctx, 
        role: Role, 
        command = Param(
            choices=[
                OptionChoice('sıralama sıfırla', 'admin reset leaderboard'),
                OptionChoice('kullanıcı sırası sil', 'user_dequeue'),
                OptionChoice('sıra sıfırla', 'admin reset queue'),
                OptionChoice('kazanan değiştir', 'admin change_winner'),
                OptionChoice('kazanan belirle', 'admin winner'),
                OptionChoice('oyun iptal', 'admin cancel'),
                OptionChoice('oyun sil', 'admin void'),
                OptionChoice('sbmm', 'admin sbmm'),
                OptionChoice('üst on', 'admin top_ten'),
                OptionChoice('sıra tercihi', 'admin queue_preference'),
            ]
        ), 
    ):
        """
        Bir rolün belirli bir yönetici komutunu çalıştırmasına izin verme.
        """
        data = await self.bot.fetchrow(
            "SELECT * FROM admin_enables WHERE guild_id = ? and role_id = ? and command = ?",
            ctx.guild.id, role.id, command
        )
        if not data:
            return await ctx.send(
                embed=error(f"{role.mention} already does not have access to the command.")
            )
        
        await ctx.response.defer(ephemeral=True)
        await self.bot.execute(
            "DELETE FROM admin_enables WHERE guild_id = ? and command = ? and role_id = ?",
            ctx.guild.id, command, role.id
        )
        await ctx.send(embed=success(f"Command disabled for {role.mention} successfully."))

    @admin_slash.sub_command(name="sıradansil")
    async def user_dequeue_slash(self, ctx, member: Member):
        """
        Oyuncuyu Sıradan Sil ve Embedi Yenile.
        """
        await ctx.response.defer()
        await self.user_dequeue(ctx, member)

    @admin_slash.sub_command(name="sıra_tercihi")
    async def queue_preference(self, ctx, preference = Param(choices=[OptionChoice("Multi Queue", "1"), OptionChoice("Single Queue", "2")])):
        """
        Oyuncuların aynı anda birden fazla sırada yer alıp alamayacağına karar verin.
        """
        await ctx.response.defer(ephemeral=True)
        preference_data = await self.bot.fetchrow(
            "SELECT * FROM queue_preference WHERE guild_id = ?",
            ctx.guild.id
        )
        if preference_data:
            await self.bot.execute("UPDATE queue_preference SET preference = $1 WHERE guild_id = $2", int(preference), ctx.guild.id)
        else:
            await self.bot.execute(
                "INSERT INTO queue_preference(guild_id, preference) VALUES($1, $2)",
                ctx.guild.id,
                int(preference)
            )
        
        await ctx.send(embed=success("Tercih başarıyla güncellendi."))

    @admin_slash.sub_command(name="kazananı_değiştir")
    async def change_winner_slash(
        self,
        ctx,
        game_id,
        team=Param(choices=[OptionChoice("red", "red"), OptionChoice("blue", "blue")]),
    ):
        """
        Bir oyunun kazananını değiştir.
        """
        await ctx.response.defer()
        await self.change_winner(ctx, game_id, team)

    @admin_slash.sub_command(name="kazanan_belirle")
    async def winner_slash(self, ctx, role: Role):
        """
        Bir oyunun kazananını belirle. Oyuncu seçimine gerek kalmadan oyunu bitirir.
        """
        await ctx.response.defer()
        await self.winner(ctx, role)

    @admin_slash.sub_command(name="iptal")
    async def cancel_slash(self, ctx, member: Member):
        """
        Birinin aktif oyununu iptal et.
        """
        await ctx.response.defer()
        await self.cancel(ctx, member)

    @admin_slash.sub_command(name="top_on")
    async def leaderboard_persistent_slash(self, ctx, channel: TextChannel, game = Param(default="lol", choices={"League Of Legends": "lol"})):
        """
        Sabit bir kanalda kalıcı liderlik tablosu oluşturun.
        """
        await ctx.response.defer()
        embed = await leaderboard_persistent(self.bot, channel, game)
        msg = await channel.send(embed=embed)
        if not msg:
            return await ctx.send(embed=error("Liderlik tablosunda görüntülenecek kayıt yok, önce bir maç oynamayı deneyin."))
        data = await self.bot.fetchrow(
            "SELECT * FROM persistent_lb WHERE guild_id = ? and game = ?",
            ctx.guild.id, game
        )
        if data:
            await self.bot.execute(
                "UPDATE persistent_lb SET channel_id = $1, msg_id = $2 WHERE guild_id = $3 and game = $4",
                channel.id,
                msg.id,
                ctx.guild.id,
                game
            )
        else:
            await self.bot.execute(
                "INSERT INTO persistent_lb(guild_id, channel_id, msg_id, game) VALUES($1, $2, $3, $4)",
                ctx.guild.id,
                channel.id, 
                msg.id,
                game
            )
        
        await ctx.send(embed=success("Kalıcı skor tablosu başarıyla etkinleştirildi."))

    
    @admin_slash.sub_command(name="sil")
    async def void_slash(self, ctx, game_id):
        """
        Bir maçın tüm kayıtlarını sil.
        """
        await ctx.response.defer()
        await self.void(ctx, game_id)

    @admin_slash.sub_command(name="sbmm")
    async def sbmm(self, ctx, preference = Param(
        choices=[
            OptionChoice('Enabled', '1'),
            OptionChoice('Disabled', '0')
        ]
    )):
        """
        SkillBased eşleştirmeyi Etkinleştir/Devre Dışı Bırak.
        """
        if int(preference):
            await self.bot.execute("DELETE FROM switch_team_preference WHERE guild_id = ?", ctx.guild.id)
            
        else:
            await self.bot.execute(
                "INSERT INTO switch_team_preference(guild_id) VALUES($1)",
                ctx.guild.id
            )

        await ctx.send(embed=success(f"Skillbase eşleştirmesi başarıyla değiştirildi."))

    @admin_slash.sub_command()
    async def duo_queue(self, ctx, preference = Param(
        choices=[
            OptionChoice('Enabled', '1'),
            OptionChoice('Disabled', '0')
        ]
    )):
        """
        Duo Queue sistemini Etkinleştir/Devre Dışı Bırak.
        """
        sbmm = await self.bot.fetchrow(
            "SELECT * FROM switch_team_preference WHERE guild_id = ?",
            ctx.guild.id
        )
        if sbmm:
            return await ctx.send(embed=error("Lütfen Duo'ya sbmm'yi etkinleştirin.`/admin sbmm Enable`"))
        if int(preference):
            await self.bot.execute(
                "INSERT INTO duo_queue_preference(guild_id) VALUES($1)",
                ctx.guild.id
            )
            
        else:
            await self.bot.execute("DELETE FROM duo_queue_preference WHERE guild_id = ?", ctx.guild.id)
            
        await ctx.send(embed=success(f"Duo Queue tercihi başarıyla değiştirildi."))

    @admin_slash.sub_command()
    async def test_mode(self, ctx, condition: bool):
        """
        Test Modu Kapa/Aç.
        """
        data = await self.bot.fetchrow(
            "SELECT * FROM testmode WHERE guild_id = ?",
            ctx.guild.id
        )
        if data and condition:
            return await ctx.send(embed=success("Test modu zaten etkin."))
        
        if not data and not condition:
            return await ctx.send(embed=success("Test modu zaten devre dışı."))
        
        if condition:
            await self.bot.execute("INSERT INTO testmode(guild_id) VALUES(?)", ctx.guild.id)
            await ctx.send(embed=success("Test modu başarıyla etkinleştirildi."))
        else:
            await self.bot.execute("DELETE FROM testmode WHERE guild_id = ?", ctx.guild.id)
            await ctx.send(embed=success("Test modu başarıyla devre dışı bırakıldı."))

    @admin_slash.sub_command()
    async def setup(self, ctx, game=Param(default="lol", choices={"League Of Legends": "lol"})):
        """
        Scrimlabi ayarlama.
        """
        await ctx.response.defer()
        if game == 'lol':
            regions =  ["BR", "EUNE", "EUW", "LA", "LAS", "NA", "OCE", "RU", "TR", "JP"]
        else:
            regions = []
        
        async def process_setup(region):
            mutual_overwrites = {
                    ctx.guild.default_role: PermissionOverwrite(
                        send_messages=False
                    ),
                    self.bot.user: PermissionOverwrite(
                        send_messages=True, manage_channels=True
                    ),
                }
            if game == "lol":
                display_game = "League Of Legends"
            else:
                display_game = "Other"
            category = await ctx.guild.create_category(name=f"InHouse - {display_game}", overwrites=mutual_overwrites)
            queue = await category.create_text_channel(name="queue")
            match_history = await category.create_text_channel(name="match-history")
            top_ten = await category.create_text_channel(name="top-10")
            await self.bot.execute(
                "INSERT INTO queuechannels(channel_id, region, game) VALUES($1, $2, $3)", queue.id, region, game
            )
            winnerlog = await self.bot.fetchrow(
                "SELECT * FROM winner_log_channel WHERE guild_id = ? and game = ?",
                ctx.guild.id, game
            )
            if winnerlog:
                await self.bot.execute(
                    "UPDATE winner_log_channel SET channel_id = ? WHERE guild_id = ? and game = ?",
                    match_history.id, ctx.guild.id, game
                )
            else:
                await self.bot.execute(
                    "INSERT INTO winner_log_channel(guild_id, channel_id, game) VALUES($1, $2, $3)",
                    ctx.guild.id,
                    match_history.id,
                    game
                )
            embed = await leaderboard_persistent(self.bot, top_ten, game)
            msg = await top_ten.send(embed=embed)
            data = await self.bot.fetchrow(
                "SELECT * FROM persistent_lb WHERE guild_id = ? and game = ?",
                ctx.guild.id, game
            )
            if data:
                await self.bot.execute(
                    "UPDATE persistent_lb SET channel_id = $1, msg_id = $2 WHERE guild_id = $3 and game = $4",
                    top_ten.id,
                    msg.id,
                    ctx.guild.id,
                    game
                )
            else:
                await self.bot.execute(
                    "INSERT INTO persistent_lb(guild_id, channel_id, msg_id, game) VALUES($1, $2, $3, $4)",
                    ctx.guild.id,
                    top_ten.id, 
                    msg.id,
                    game
                )
            await start_queue(self.bot, queue, game)
            embed = Embed(
                description="Maç Geçmişi Burada Gösterilir.",
                color=Color.red()
            )
            await match_history.send(embed=embed)
            overwrites = {
                ctx.guild.default_role: PermissionOverwrite(
                    send_messages=False
                ),
                self.bot.user: PermissionOverwrite(
                    send_messages=True, manage_channels=True
                ),
            }
            
            category = await ctx.guild.create_category(name=f"Ongoing {game} Games", overwrites=overwrites)
            cate_data = await self.bot.fetchrow(
                "SELECT * FROM game_categories WHERE guild_id = ? and game = ?",
                ctx.guild.id, game
            )
            if cate_data:
                await self.bot.execute(
                    "UPDATE game_categories SET category_id = ? WHERE guild_id = ? and game = ?",
                    category.id, ctx.guild.id, game
                )
            else:
                await self.bot.execute(
                    "INSERT INTO game_categories(guild_id, category_id, game) VALUES(?,?,?)",
                    ctx.guild.id, category.id, game
                )
            
            info_channel = await category.create_text_channel("Information")

            embed = embed = Embed(title="InHouse Aktif Oyunlar", description=f"Devam eden tüm {display_game} oyunları bu kategori altında yer alacaktır. İstediğiniz gibi yerini değiştirebilir veya adını değiştirebilirsiniz.", color=Color.red())

            embed.set_image(url="https://cdn.discordapp.com/attachments/1452690176760479755/1453400151426072671/mundo-league.gif?ex=694d4fde&is=694bfe5e&hm=bb72132be5373691a7d68cf812fb1a451d886cd4777a2225e4cc5bc911b63568&")
            view = LinkButton({"Düzenle": "https://example.com"})
            await info_channel.send(embed=embed, view=view)

            await ctx.send(embed=success("Kurulum başarıyla tamamlandı.Varsa lütfen önceki 'eşleşme geçmişi', 'top_10' ve 'bilgi' metin kanallarını silin.Bunlar artık devre dışıdır."))
        if regions:
            options = []
            for region in regions:
                options.append(SelectOption(label=region, value=region.lower()))

            async def Function(inter, vals, *args):
                await process_setup(vals[0])

            await ctx.send(content="Sıra İçin Bölge Seç", view=SelectMenuDeploy(self.bot, ctx.author.id, options, 1, 1, Function))
        else:
            await process_setup("none")

    @admin_slash.sub_command(name="setup_1v1")
    async def setup_1v1(self, ctx):
        """
        1v1 özel sırası için ayrı bir kanal kurar (top-10'a dokunmaz).
        """
        await ctx.response.defer()
        mutual_overwrites = {
            ctx.guild.default_role: PermissionOverwrite(send_messages=False),
            self.bot.user: PermissionOverwrite(send_messages=True, manage_channels=True),
        }
        category = await ctx.guild.create_category(name="InHouse - 1v1", overwrites=mutual_overwrites)
        queue = await category.create_text_channel(name="1v1-queue")

        # 1v1 sırası: region boş, game = '1v1'
        await self.bot.execute(
            "INSERT INTO queuechannels(channel_id, region, game) VALUES($1, $2, $3)",
            queue.id,
            "",
            "1v1",
        )

        await ctx.send(
            embed=success(
                f"{queue.mention} kanalı 1v1 sırası olarak ayarlandı. "
                f"Bu mod, mevcut top-10 veya puan sistemini etkilemez."
            )
        )

    @admin_slash.sub_command()
    async def reset_db(self, ctx, user_id):
        """
        Bir kullanıcının sıralama tablolarındaki kayıtlarını kaldırın.
        """
        try:
            await self.bot.execute("DELETE FROM points WHERE user_id = ? and guild_id = ?", user_id, ctx.guild.id)
            await self.bot.execute("DELETE FROM mvp_points WHERE user_id = ? and guild_id = ?", user_id, ctx.guild.id)
            await self.bot.execute("DELETE FROM mmr_rating WHERE user_id = ? and guild_id = ?", user_id, ctx.guild.id)
            await ctx.send(embed=success("Verilen kimlikle ilişkili girişler başarıyla silindi."))
        except:
            await ctx.send(embed=error("Bir hata oluştu.Lütfen kullanıcı kimliğini tekrar kontrol edin."))

    @admin_slash.sub_command()
    async def update_ign(self, ctx, ign, member: Member, game=Param(default="lol", choices={"League Of Legends": "lol"})):
        """
        Oyuncunun Oyun İçi Adını (IGN) güncelleyin.
        """
        data = await self.bot.fetchrow(
            "SELECT * FROM igns WHERE game = ? and user_id = ? and guild_id = ?",
            game, member.id, ctx.guild.id
        )
        if data:
            await self.bot.execute(
                "UPDATE igns SET ign = ? WHERE guild_id = ? and user_id = ? and game = ?",
                ign, ctx.guild.id, member.id, game
            )
        else:
            await self.bot.execute(
                "INSERT INTO igns(guild_id, user_id, game, ign) VALUES(?,?,?,?)",
                ctx.guild.id, member.id, game, ign
            )
        await ctx.send(embed=success("IGN başarıyla güncellendi."))

    @admin_slash.sub_command_group(name="reset")
    async def reset_slash(self, ctx):
        pass
    
    @reset_slash.sub_command(name="leaderboard")
    async def leaderboard_slash(self, ctx):
        """
        Sunucunuzdaki tüm galibiyet, mağlubiyet, MMR ve MVP oylarını sıfırlayın.
        """
        await self.leaderboard(ctx)

    @reset_slash.sub_command(name="queue")
    async def queue_slash(self, ctx, game_id: str):
        """
        Sıradaki herkesi çıkarın. Embedi yenilemek için sıraya tekrar katılın
        """
        await self.queue(ctx, game_id)

    @reset_slash.sub_command(name="user")
    async def user_slash(self, ctx, member: Member):
        """
        Üyenin galibiyet, mağlubiyet, MMR ve MVP oylarını sıfırlayın.
        """
        await self.user(ctx, member)

    @admin_slash.sub_command(name="mac_bildirim")
    async def mac_bildirim_slash(self, ctx, saat: str, draft_turu: str, ekstra_mesaj: str = ""):
        """
        @maç bilgi rolüne sahip olanlara DM'den maç bildirimi gönder.
        """
        match_info_role = disnake.utils.get(ctx.guild.roles, name="maç bilgi")
        if not match_info_role:
            await ctx.send(embed=error("@maç bilgi rolü bulunamadı."), ephemeral=True)
            return

        await ctx.response.defer(ephemeral=True)
        import random
        colors = [Color.red(), Color.blue(), Color.green(), Color.purple(), Color.orange(), Color.teal()]
        embed_color = random.choice(colors)

        # Rastgele gif seç
        gifs = [
            "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3eDQ3dGJraDB6YWVkMXByM2luajFkZmlycndxYjliOGdoMmo3aTh2aiZlcD12MV9naWZzX3JlbGF0ZWQmY3Q9Zw/2Zx7vPlybLbpe/giphy.gif",
            "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExNXZ3aDk4NmdqejY3ejNsMHN0YmFubGNxNDZ1YjE3aWRkZHp2bno1YyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/1lD9aC19nGv33NKCjF/giphy.gif",  # League temalı başka gif
            "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExcjYyb2VtdjB4aGUzZTVwcHIzZmFuZHpnZWFzYmVuNDRtbGpiaGl4ciZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/26gYOdBrT3MKcTj3O/giphy.gif",
            "https://media.giphy.com/media/5GTaXWH5axV8lofbxM/giphy.gif",
            "https://media1.tenor.com/m/kl12XsiWYWwAAAAd/ding-ding-ding-alistar.gif",
            "https://media.tenor.com/8RXJiR609CMAAAAj/alistar-league-of-legends.gif",
            "https://media1.tenor.com/m/daCGy4UTOboAAAAd/lol-league-of-legends.gif",
            "https://media.tenor.com/JtPir03G7REAAAAi/zed-happy.gif",
            "https://media.tenor.com/gkYZNAaA_LUAAAAi/sfreaking-yasuo.gif",
            "https://giphy.com/gifs/leagueoflegends-league-of-legends-5JUdtqgoeh2BoCALiV"   # League animasyonu
        ]
        selected_gif = random.choice(gifs)

        embed = Embed(
            title="⚔️ **MAÇ BİLDİRİMİ** ⚔️",
            description=f"**{ctx.guild.name}** sunucusunda yeni bir maç var!\n\n{ekstra_mesaj}",
            color=embed_color
        )
        embed.add_field(name="🕒 **Saat**", value=f"**{saat}**", inline=True)
        embed.add_field(name="📋 **Draft Türü**", value=f"**{draft_turu}**", inline=True)
        embed.add_field(name="🎮 **Sunucu**", value=f"**{ctx.guild.name}**", inline=True)
        embed.set_image(url=selected_gif)
        embed.set_footer(text="Hazır olun, eğlence başlıyor! 🎉")

        sent_count = 0
        for member in ctx.guild.members:
            if match_info_role in member.roles:
                # Her üye için ayrı embed, ayrı renk ve gif
                embed_color = random.choice(colors)
                selected_gif = random.choice(gifs)
                embed = Embed(
                    title="⚔️ **MAÇ BİLDİRİMİ** ⚔️",
                    description=f"**{ctx.guild.name}** sunucusunda yeni bir maç var!\n\n{ekstra_mesaj}",
                    color=embed_color
                )
                embed.add_field(name="🕒 **Saat**", value=f"**{saat}**", inline=True)
                embed.add_field(name="📋 **Draft Türü**", value=f"**{draft_turu}**", inline=True)
                embed.add_field(name="🎮 **Sunucu**", value=f"**{ctx.guild.name}**", inline=True)
                embed.set_image(url=selected_gif)
                embed.set_footer(text="Hazır olun, eğlence başlıyor! 🎉")
                try:
                    await member.send(embed=embed)
                    sent_count += 1
                except:
                    pass  # DM gönderilemezse geç

                    pass  # DM gönderilemezse geç
 
        await ctx.edit_original_message(embed=success(f"{sent_count} üyeye maç bildirimi gönderildi!"))

    @admin_slash.sub_command(name="rolvermebaslat")
    async def rolvermebaslat_slash(self, ctx):
        """
        Rol verme embed'ini başlat.
        """
        from cogs.role_selection import RoleSelectionView  # Import et
        embed = Embed(
            title="Rol Seçimi",
            description="**Butonlardan Kendinizle ilgili rolleri seçiniz. Eğer Maçlar hakkında bilgi almak istiyorsanız @maç bilgi rolünü alabilirsiniz.**",
            color=Color.blue()
        )
        view = RoleSelectionView(self.bot)
        await ctx.send(embed=embed, view=view)

def setup(bot):
    bot.add_cog(Admin(bot))
