import asyncio
from disnake import Color, Embed, ui, ButtonStyle
from disnake.ext.commands import Cog, command, slash_command
from trueskill import Rating, backends, rate

from core.embeds import error, success

class WinButtons(ui.View):
    def __init__(self, bot, game_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.game_id = game_id
        self.blue_votes = []
        self.red_votes = []
    
    async def check_end(self, inter, game_data, *args):
        async def declare_winner(winner):
            display_name = "Kırmızı" if winner.lower() == "red" else "Mavi"
            
            # Mesaj gönderme kontrolü
            try:
                if hasattr(inter, 'send'):
                    await inter.send(f"{display_name} Takım Maçı Kazandı Tebrikler!")
                elif hasattr(inter, 'channel'):
                    await inter.channel.send(f"{display_name} Takım Maçı Kazandı Tebrikler!")
            except:
                pass

            queuechannel = self.bot.get_channel(game_data[6])
            if queuechannel:
                try:
                    msg = await queuechannel.fetch_message(game_data[7])
                    await msg.edit(content=f"{display_name} Takım Maçı Kazandı Tebrikler!", view=None)
                except:
                    pass

            # Kanal ve rol temizliği
            guild = inter.guild if hasattr(inter, 'guild') else self.bot.get_guild(game_data[6])
            if guild:
                for category in guild.categories:
                    if category.name == f"Game: {game_data[0]}":
                        try:
                            await category.delete()
                        except:
                            pass

            # Kanalları sil
            for channel_id in [game_data[1], game_data[2], game_data[3]]:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        await channel.delete()
                    except:
                        pass

            # Rolleri sil
            if guild:
                for role_id in [game_data[4], game_data[5]]:
                    role = guild.get_role(role_id)
                    if role:
                        try:
                            await role.delete()
                        except:
                            pass

            member_data = await self.bot.fetch(
                "SELECT * FROM game_member_data WHERE game_id = ?",
                game_data[0]
            )

            mentions = (
                    f"🔴 **Kırmızı Takım:** "
                    + ", ".join(f"<@{data[0]}>" for data in member_data if data[2] == "red")
                    + "\n🔵 **Mavi Takım**: "
                    + ", ".join(f"<@{data[0]}>" for data in member_data if data[2] == "blue")
            )

            st_pref = await self.bot.fetchrow(
                "SELECT * FROM switch_team_preference WHERE guild_id = ?",
                guild.id if guild else 0
            )
            
            winning_team_str = ""
            losing_team_str = ""
            old_mmr = {}
            new_mmr = {}
            
            # MMR Hesaplama
            if not st_pref:
                winner_team_rating = []
                losing_team_rating = []
                
                for member_entry in member_data:
                    rating = await self.bot.fetchrow(
                        "SELECT * FROM mmr_rating WHERE user_id = ? and guild_id = ? and game = ?",
                        member_entry[0], guild.id if guild else 0, game_data[8]
                    )

                    if not rating:
                        # Eğer rating yoksa varsayılan oluştur
                        if guild:
                            await self.bot.execute(
                                f"INSERT INTO mmr_rating(guild_id, user_id, mu, sigma, counter, game) "
                                f"VALUES($1, $2, $3, $4, $5, $6)",
                                guild.id, member_entry[0], "25.0", "8.33333333333333", 0, game_data[8]
                            )
                            rating = (guild.id, member_entry[0], "25.0", "8.33333333333333", 0, game_data[8])

                    if rating:
                        if member_entry[2] == winner.lower():
                            winner_team_rating.append({
                                "user_id": member_entry[0], 
                                "rating": Rating(mu=float(rating[2]), sigma=float(rating[3]))
                            })
                            winning_team_str += f"• {self.bot.role_emojis.get(member_entry[1], '❓')} <@{member_entry[0]}> \n"
                        else:
                            losing_team_rating.append({
                                "user_id": member_entry[0], 
                                "rating": Rating(mu=float(rating[2]), sigma=float(rating[3]))
                            })
                            losing_team_str += f"• {self.bot.role_emojis.get(member_entry[1], '❓')} <@{member_entry[0]}> \n"

                        old_mmr[str(member_entry[0])] = f"{rating[2]}:{rating[3]}"

                # TrueSkill hesaplama
                if winner_team_rating and losing_team_rating:
                    backends.choose_backend("mpmath")
                    updated_rating = rate(
                        [[x['rating'] for x in winner_team_rating], 
                         [x['rating'] for x in losing_team_rating]],
                        ranks=[0, 1]
                    )

                    # Kazanan takım MMR güncellemesi
                    for i, new_rating in enumerate(updated_rating[0]):
                        counter_row = await self.bot.fetchrow(
                            "SELECT counter FROM mmr_rating WHERE user_id = ? and guild_id = ? and game = ?",
                            winner_team_rating[i]['user_id'], guild.id if guild else 0, game_data[8]
                        )
                        counter = counter_row[0] if counter_row else 0
                        
                        await self.bot.execute(
                            "UPDATE mmr_rating SET mu = $1, sigma = $2, counter = $3 WHERE user_id = $4 and guild_id = $5 and game = $6",
                            str(new_rating.mu), str(new_rating.sigma), counter + 1,
                            winner_team_rating[i]['user_id'], guild.id if guild else 0, game_data[8]
                        )
                        new_mmr[str(winner_team_rating[i]['user_id'])] = f"{new_rating.mu}:{new_rating.sigma}"

                    # Kaybeden takım MMR güncellemesi
                    for i, new_rating in enumerate(updated_rating[1]):
                        counter_row = await self.bot.fetchrow(
                            "SELECT counter FROM mmr_rating WHERE user_id = ? and guild_id = ? and game = ?",
                            losing_team_rating[i]['user_id'], guild.id if guild else 0, game_data[8]
                        )
                        counter = counter_row[0] if counter_row else 0
                        
                        await self.bot.execute(
                            "UPDATE mmr_rating SET mu = $1, sigma = $2, counter = $3 WHERE user_id = $4 and guild_id = $5 and game = $6",
                            str(new_rating.mu), str(new_rating.sigma), counter + 1,
                            losing_team_rating[i]['user_id'], guild.id if guild else 0, game_data[8]
                        )
                        new_mmr[str(losing_team_rating[i]['user_id'])] = f"{new_rating.mu}:{new_rating.sigma}"
            else:
                # SBMM kapalıysa
                for member_entry in member_data:
                    emoji = self.bot.role_emojis.get(member_entry[1], '❓')
                    if member_entry[2] == winner.lower():
                        winning_team_str += f"• {emoji} <@{member_entry[0]}> \n"
                    else:
                        losing_team_str += f"• {emoji} <@{member_entry[0]}> \n"

            # Sonuç Embed'i
            embed = Embed(
                title=f"Oyun Sonlandı!",
                description=f"Maç **{game_data[0]}** sonuçlandı!",
                color=Color.blurple(),
            )
            embed.add_field(name="Kazanan Takım", value=winning_team_str or "N/A")
            embed.add_field(name="Kaybeden Takım", value=losing_team_str or "N/A")

            # Log kanalına gönder
            log_channel_id = await self.bot.fetchrow(
                f"SELECT * FROM winner_log_channel WHERE guild_id = {guild.id if guild else 0} "
                f"and game = '{game_data[8]}'"
            )
            
            if log_channel_id and queuechannel:
                log_channel = self.bot.get_channel(log_channel_id[0])
                if log_channel:
                    try:
                        await log_channel.send(mentions, embed=embed)
                    except:
                        try:
                            await queuechannel.send(
                                embed=error(f"Could not log the game {game_data[0]} in {log_channel.mention}. "
                                          f"Please check my permissions."), 
                                delete_after=120.0
                            )
                        except:
                            pass

            # Veritabanı temizliği
            await self.bot.execute(f"DELETE FROM games WHERE game_id = '{game_data[0]}'")
            await self.bot.execute(f"DELETE FROM game_member_data WHERE game_id = '{game_data[0]}'")
            await self.bot.execute(f"DELETE FROM duo_queue WHERE game_id = '{game_data[0]}'")
            await self.bot.execute(f"DELETE FROM ready_ups WHERE game_id = '{game_data[0]}'")

            # Oyuncu istatistiklerini güncelle
            for member_entry in member_data:
                user_data = await self.bot.fetchrow(
                    f"SELECT * FROM points WHERE user_id = {member_entry[0]} "
                    f"and guild_id = {guild.id if guild else 0} and game = '{game_data[8]}'"
                )

                # MVP oylaması için hazırlık
                existing_voting = await self.bot.fetchrow(
                    f"SELECT * FROM mvp_voting WHERE user_id = {member_entry[0]}"
                )
                if existing_voting:
                    await self.bot.execute(f"DELETE FROM mvp_voting WHERE user_id = {member_entry[0]}")
                    
                await self.bot.execute(
                    f"INSERT INTO mvp_voting(guild_id, user_id, game_id) VALUES($1, $2, $3)",
                    guild.id if guild else 0, member_entry[0], member_entry[3]
                )

                # MVP oylama DM'i gönder
                user = self.bot.get_user(member_entry[0])
                if user:
                    try:
                        red_list = []
                        blue_list = []
                        num = 1
                        
                        for x in member_data:
                            emoji = self.bot.role_emojis.get(x[1], '❓')
                            text = f"**{num}.** {emoji} <@{x[0]}>"
                            
                            if x[2] == "red":
                                red_list.append(text)
                            elif x[2] == "blue":
                                blue_list.append(text)
                            num += 1

                        mvp_embed = Embed(
                            title=":trophy: En iyi oyuncuyu oyla",
                            description="Seçimini Numaralardan Seç (1–10).",
                            color=Color.blurple()
                        )
                        mvp_embed.add_field(
                            name="🔴 Kırmızı Takım", 
                            value="\n".join(red_list) if red_list else "-", 
                            inline=True
                        )
                        mvp_embed.add_field(
                            name="🔵 Mavi Takım", 
                            value="\n".join(blue_list) if blue_list else "-", 
                            inline=True
                        )
                        await user.send(embed=mvp_embed)
                    except:
                        pass

                # MMR verilerini al
                if not st_pref:
                    player_old_mmr = old_mmr.get(str(member_entry[0]), "25.0:8.333")
                    player_new_mmr = new_mmr.get(str(member_entry[0]), "25.0:8.333")
                else:
                    player_old_mmr = "disabled"
                    player_new_mmr = "disabled"

                # Oy bilgisini kaydet
                voted_team = "none"
                if member_entry[0] in self.blue_votes:
                    voted_team = "blue"
                elif member_entry[0] in self.red_votes:
                    voted_team = "red"

                # Maç geçmişine kaydet
                await self.bot.execute(
                    f"INSERT INTO members_history(user_id, game_id, team, result, role, "
                    f"old_mmr, now_mmr, voted_team, game) VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                    member_entry[0], game_data[0], member_entry[2],
                    "won" if member_entry[2] == winner.lower() else "lost",
                    member_entry[1], player_old_mmr, player_new_mmr, voted_team, game_data[8]
                )

                # Kazanma/kaybetme istatistiklerini güncelle
                if member_entry[2] == winner.lower():
                    if user_data:
                        await self.bot.execute(
                            f"UPDATE points SET wins = $1 WHERE user_id = $2 and guild_id = $3 "
                            f"and game = '{game_data[8]}'",
                            user_data[2] + 1, member_entry[0], guild.id if guild else 0
                        )
                    else:
                        await self.bot.execute(
                            "INSERT INTO points(guild_id, user_id, wins, losses, game) "
                            "VALUES($1, $2, $3, $4, $5)",
                            guild.id if guild else 0, member_entry[0], 1, 0, game_data[8]
                        )
                else:
                    if user_data:
                        await self.bot.execute(
                            f"UPDATE points SET losses = $1 WHERE user_id = $2 and guild_id = $3 "
                            f"and game = '{game_data[8]}'",
                            user_data[3] + 1, member_entry[0], guild.id if guild else 0
                        )
                    else:
                        await self.bot.execute(
                            "INSERT INTO points(guild_id, user_id, wins, losses, game) "
                            "VALUES($1, $2, $3, $4, $5)",
                            guild.id if guild else 0, member_entry[0], 0, 1, game_data[8]
                        )

        # Ana kontrol mantığı
        if args:
            if args[0]:
                await declare_winner(args[1])
        elif len(self.red_votes) >= 6:
            await declare_winner("red")
        elif len(self.blue_votes) >= 6:
            await declare_winner("blue")

    async def edit_embed(self, inter):
        value_blue = ""
        value_red = ""
        
        for i, vote in enumerate(self.blue_votes):
            value_blue += f"{i+1}. <@{vote}>\n"
        for i, vote in enumerate(self.red_votes):
            value_red += f"{i+1}. <@{vote}>\n"
        
        try:
            embed = inter.message.embeds[1]
            embed.clear_fields()
            embed.add_field(name="🔵 Mavi Takım Oyları", value=value_blue or "Henüz oy yok")
            embed.add_field(name="🔴 Kırmızı Takım Oyları", value=value_red or "Henüz oy yok")
            await inter.edit_original_message(embeds=[inter.message.embeds[0], embed])
        except:
            pass

    @ui.button(label="Mavi Takım", style=ButtonStyle.blurple, custom_id="win:blue")
    async def first_button(self, button, inter):
        await inter.response.defer()
        
        game_data = await self.bot.fetchrow(f"SELECT * FROM games WHERE game_id = '{self.game_id}'")
        if not game_data:
            return await inter.send(embed=error("Oyun bulunamadı."), ephemeral=True)
            
        if inter.author.id in self.red_votes:
            return await inter.send(embed=error("Zaten Kırmızı Takım'a oy verdiniz."), ephemeral=True)
            
        if inter.author.id not in self.blue_votes:
            self.blue_votes.append(inter.author.id)
            await inter.send(embed=success("Başarıyla Mavi Takım'a oy verdiniz."), ephemeral=True)
        else:
            await inter.send(embed=success("Zaten Mavi Takım'a oy verdiniz."), ephemeral=True)
            
        await self.edit_embed(inter)
        await self.check_end(inter, game_data)
        
    @ui.button(label="Kırmızı Takım", style=ButtonStyle.red, custom_id="win:red")
    async def second_button(self, button, inter):
        await inter.response.defer()
        
        game_data = await self.bot.fetchrow(f"SELECT * FROM games WHERE game_id = '{self.game_id}'")
        if not game_data:
            return await inter.send(embed=error("Oyun bulunamadı."), ephemeral=True)
            
        if inter.author.id in self.blue_votes:
            return await inter.send(embed=error("Zaten Mavi Takım'a oy verdiniz."), ephemeral=True)
            
        if inter.author.id not in self.red_votes:
            self.red_votes.append(inter.author.id)
            await inter.send(embed=success("Başarıyla Kırmızı Takım'a oy verdiniz."), ephemeral=True)
        else:
            await inter.send(embed=success("Zaten Kırmızı Takım'a oy verdiniz."), ephemeral=True)
            
        await self.edit_embed(inter)
        await self.check_end(inter, game_data)


class Win1v1Buttons(ui.View):
    def __init__(self, bot, channel_id, store):
        super().__init__(timeout=None)
        self.bot = bot
        self.channel_id = channel_id
        self.store = store  # {"red": set(), "blue": set()}

    async def _maybe_finish(self, inter):
        red = len(self.store["red"])
        blue = len(self.store["blue"])

        if red >= 2:
            await inter.channel.send(embed=success("Kırmızı kazandı (2 oy)! Kanal kapanıyor..."))
            await asyncio.sleep(2)
            await inter.channel.delete()
        elif blue >= 2:
            await inter.channel.send(embed=success("Mavi kazandı (2 oy)! Kanal kapanıyor..."))
            await asyncio.sleep(2)
            await inter.channel.delete()
    async def _update_embed(self, inter):
        try:
            embed = inter.message.embeds[0]
            embed.clear_fields()
            embed.add_field(
                name="🔴 Kırmızı Oyları",
                value="\n".join(f"<@{uid}>" for uid in self.store["red"]) or "Henüz oy yok",
                inline=True,
            )
            embed.add_field(
                name="🔵 Mavi Oyları",
                value="\n".join(f"<@{uid}>" for uid in self.store["blue"]) or "Henüz oy yok",
                inline=True,
            )
            await inter.edit_original_message(embed=embed)
        except Exception:
            pass

    @ui.button(label="Kırmızı Kazandı", style=ButtonStyle.red, custom_id="1v1win:red")
    async def red_btn(self, button, inter):
        await inter.response.defer(ephemeral=True)
        if inter.author.id in self.store["blue"]:
            return await inter.send(embed=error("Önce Mavi'ye oy verdin."), ephemeral=True)
        self.store["red"].add(inter.author.id)
        await inter.send(embed=success("Oyun Kırmızı için sayıldı."), ephemeral=True)
        await self._update_embed(inter)
        await self._maybe_finish(inter)

    @ui.button(label="Mavi Kazandı", style=ButtonStyle.blurple, custom_id="1v1win:blue")
    async def blue_btn(self, button, inter):
        await inter.response.defer(ephemeral=True)
        if inter.author.id in self.store["red"]:
            return await inter.send(embed=error("Önce Kırmızı'ya oy verdin."), ephemeral=True)
        self.store["blue"].add(inter.author.id)
        await inter.send(embed=success("Oyun Mavi için sayıldı."), ephemeral=True)
        await self._update_embed(inter)
        await self._maybe_finish(inter)


class Win(Cog):
    """
    🏆;Win
    """

    def __init__(self, bot):
        self.bot = bot
        self.active_win_commands = []
        self.win1v1_votes = {}

    def _is_1v1_channel(self, channel):
        name = channel.name.lower()
        cat = channel.category.name.lower() if channel.category else ""
        return "1v1" in name or "1v1" in cat

    async def start_1v1_vote(self, channel):
        if channel.id in self.active_win_commands:
            return await channel.send("Bu kanalda bir kazanma oylaması zaten aktif.")

        self.win1v1_votes[channel.id] = {"red": set(), "blue": set()}
        embed = Embed(
            title="1v1 Kazanan Oylaması",
            description="2 oy alan taraf kazanır. Kanal otomatik kapanır.",
            color=Color.red(),
        )
        embed.add_field(name="🔴 Kırmızı Oyları", value="Henüz oy yok", inline=True)
        embed.add_field(name="🔵 Mavi Oyları", value="Henüz oy yok", inline=True)

        await channel.send(embed=embed, view=Win1v1Buttons(self.bot, channel.id, self.win1v1_votes[channel.id]))
        self.active_win_commands.append(channel.id)

    async def process_win(self, channel, author, bypass=False, bypass_for_team=None):
        game_data = await self.bot.fetchrow(
            f"SELECT * FROM games WHERE lobby_id = {channel.id}"
        )
        
        if not game_data:
            if self._is_1v1_channel(channel):
                return await self.start_1v1_vote(channel)
            return await channel.send("Bu kanal için hiçbir oyun ayrılmadı..")

        if not bypass:
            if channel.id in self.active_win_commands:
                return await channel.send(
                    "Bu kanalda bir kazanma oylaması zaten aktif durumda..", 
                    delete_after=5.0
                )

        member_data = await self.bot.fetch(
            f"SELECT * FROM game_member_data WHERE game_id = '{game_data[0]}'"
        )

        mentions = (
                f"🔴 Kırmızı Takım: "
                + ", ".join(f"<@{data[0]}>" for data in member_data if data[2] == "red")
                + "\n🔵 Mavi Takım: "
                + ", ".join(f"<@{data[0]}>" for data in member_data if data[2] == "blue")
        )

        if (
            not author.id in [member[0] for member in member_data]
            and not author.guild_permissions.administrator
        ):
            return await channel.send(
                "Bu komutu yalnızca oyun üyeleri veya yöneticiler çalıştırabilir."
            )

        if not bypass:
            embed1 = Embed(
                title="Sonuçlar Yanlış Mı İşaretlendi ?", 
                description="Böyle Bir Durumda <#1453371166147477575> Destek Talebi Açınız Yeni Bir Maça Girmeyin !", 
                color=Color.yellow()
            )
            embed2 = Embed(
                title="Kazananı Oyla!", 
                description="Hangi Takım Kazandı?", 
                color=Color.red()
            )
            embed2.add_field(name="🔵 Mavi Takım Oyları", value="Henüz oy yok")
            embed2.add_field(name="🔴 Kırmızı Takım Oyları", value="Henüz oy yok")
            
            await channel.send(
                embeds=[embed1, embed2], 
                view=WinButtons(self.bot, game_data[0])
            )
            await channel.send(mentions)
            self.active_win_commands.append(channel.id)
        else:
            await WinButtons(self.bot, game_data[0]).check_end(
                channel, game_data, bypass, bypass_for_team
            )

    @command()
    async def win(self, ctx):
        await self.process_win(ctx.channel, ctx.author)

    @slash_command(name="win")
    async def win_slash(self, ctx):
        """
        Kazananı belirlemek için oylama başlat.
        """
        await ctx.delete_original_message()
        await self.process_win(ctx.channel, ctx.author)


def setup(bot):
    bot.add_cog(Win(bot))
