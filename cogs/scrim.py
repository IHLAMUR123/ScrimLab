import disnake
from disnake.ext import commands
from disnake import Embed, Color, ButtonStyle, ui, PermissionOverwrite
import random
import string
from datetime import datetime

class ScrimWinButtons(ui.View):
    """Scrim kazanan seçme butonları"""
    def __init__(self, bot, scrim_id, team1_name, team2_name):
        super().__init__(timeout=None)
        self.bot = bot
        self.scrim_id = scrim_id
        self.team1_name = team1_name
        self.team2_name = team2_name
        self.team1_votes = []
        self.team2_votes = []

    @ui.button(label="🏆 Takım 1", style=ButtonStyle.blurple, custom_id="scrim_win:team1")
    async def team1_win(self, button: ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        
        if inter.author.id in self.team2_votes:
            return await inter.send(f"❌ Zaten {self.team2_name} için oy kullandın!", ephemeral=True)
        
        if inter.author.id not in self.team1_votes:
            self.team1_votes.append(inter.author.id)
            await inter.send(f"✅ {self.team1_name} için oy verdin!", ephemeral=True)
        else:
            await inter.send(f"⚠️ Zaten {self.team1_name} için oy kullandın!", ephemeral=True)
        
        await self.update_embed(inter)
        await self.check_winner(inter)

    @ui.button(label="🏆 Takım 2", style=ButtonStyle.red, custom_id="scrim_win:team2")
    async def team2_win(self, button: ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        
        if inter.author.id in self.team1_votes:
            return await inter.send(f"❌ Zaten {self.team1_name} için oy kullandın!", ephemeral=True)
        
        if inter.author.id not in self.team2_votes:
            self.team2_votes.append(inter.author.id)
            await inter.send(f"✅ {self.team2_name} için oy verdin!", ephemeral=True)
        else:
            await inter.send(f"⚠️ Zaten {self.team2_name} için oy kullandın!", ephemeral=True)
        
        await self.update_embed(inter)
        await self.check_winner(inter)

    async def update_embed(self, inter):
        """Oy durumunu güncelle"""
        try:
            embed = inter.message.embeds[0]
            embed.clear_fields()
            
            votes1_str = "\n".join([f"• <@{uid}>" for uid in self.team1_votes]) or "Henüz oy yok"
            votes2_str = "\n".join([f"• <@{uid}>" for uid in self.team2_votes]) or "Henüz oy yok"
            
            embed.add_field(
                name=f"🏆 {self.team1_name} - {len(self.team1_votes)} Oy",
                value=votes1_str,
                inline=True
            )
            embed.add_field(
                name=f"🏆 {self.team2_name} - {len(self.team2_votes)} Oy",
                value=votes2_str,
                inline=True
            )
            
            await inter.edit_original_message(embed=embed)
        except:
            pass

    async def check_winner(self, inter):
        """6 oy alan kazanır"""
        winner_name = None
        winner_team = None
        
        if len(self.team1_votes) >= 6:
            winner_name = self.team1_name
            winner_team = "team1"
        elif len(self.team2_votes) >= 6:
            winner_name = self.team2_name
            winner_team = "team2"
        
        if winner_name:
            await self.declare_winner(inter, winner_name, winner_team)

    async def declare_winner(self, inter, winner_name, winner_team):
        """Kazananı ilan et ve temizlik yap"""
        self.stop()
        
        guild = inter.guild
        
        # Scrim verilerini çek
        game_data = await self.bot.fetchrow(
            "SELECT * FROM scrims WHERE scrim_id = ?",
            self.scrim_id
        )
        
        if not game_data:
            return await inter.send("❌ Scrim verisi bulunamadı!", ephemeral=True)
        
        member_data = await self.bot.fetch(
            "SELECT * FROM scrim_members WHERE scrim_id = ?",
            self.scrim_id
        )
        
        # Kazanan/kaybeden takımları belirle
        winners = []
        losers = []
        
        for member in member_data:
            if member[2] == winner_team:  # team1 veya team2
                winners.append(member[0])  # user_id
            else:
                losers.append(member[0])
        
        # İstatistikleri güncelle
        for uid in winners:
            await self.bot.execute(
                "INSERT INTO scrim_stats(user_id, guild_id, wins, losses) VALUES(?, ?, 1, 0) "
                "ON CONFLICT(user_id, guild_id) DO UPDATE SET wins = wins + 1",
                uid, guild.id
            )
        
        for uid in losers:
            await self.bot.execute(
                "INSERT INTO scrim_stats(user_id, guild_id, wins, losses) VALUES(?, ?, 0, 1) "
                "ON CONFLICT(user_id, guild_id) DO UPDATE SET losses = losses + 1",
                uid, guild.id
            )
        
        # Sonuç embed'i
        winner_mentions = " ".join([f"<@{uid}>" for uid in winners])
        loser_mentions = " ".join([f"<@{uid}>" for uid in losers])
        
        result_embed = Embed(
            title="🏆 SCRIM SONUÇLANDI!",
            description=f"**Kazanan Takım:** {winner_name}",
            color=Color.gold(),
            timestamp=datetime.now()
        )
        
        result_embed.add_field(
            name=f"✅ {winner_name} (Kazanan)",
            value=winner_mentions,
            inline=False
        )
        
        loser_name = self.team1_name if winner_team == "team2" else self.team2_name
        result_embed.add_field(
            name=f"❌ {loser_name} (Kaybeden)",
            value=loser_mentions,
            inline=False
        )
        
        # Log kanalına gönder
        log_channel_id = await self.bot.fetchrow(
            "SELECT channel_id FROM scrim_log_channel WHERE guild_id = ?",
            guild.id
        )
        
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id[0])
            if log_channel:
                try:
                    await log_channel.send(embed=result_embed)
                except:
                    pass
        
        # Orijinal mesajı güncelle
        await inter.edit_original_message(embed=result_embed, view=None)
        
        # Kanalları ve rolleri temizle
        try:
            # Kategoriyi bul ve sil
            for category in guild.categories:
                if category.name == f"🎯 SCRIM: {self.scrim_id}":
                    await category.delete()
            
            # Kanalları sil
            if game_data[2]:  # lobby_id
                lobby = self.bot.get_channel(game_data[2])
                if lobby:
                    await lobby.delete()
            
            if game_data[3]:  # voice1_id
                voice1 = self.bot.get_channel(game_data[3])
                if voice1:
                    await voice1.delete()
            
            if game_data[4]:  # voice2_id
                voice2 = self.bot.get_channel(game_data[4])
                if voice2:
                    await voice2.delete()
            
            # Rolleri sil
            if game_data[5]:  # role1_id
                role1 = guild.get_role(game_data[5])
                if role1:
                    await role1.delete()
            
            if game_data[6]:  # role2_id
                role2 = guild.get_role(game_data[6])
                if role2:
                    await role2.delete()
        except Exception as e:
            print(f"Temizlik hatası: {e}")
        
        # Veritabanından sil
        await self.bot.execute("DELETE FROM scrims WHERE scrim_id = ?", self.scrim_id)
        await self.bot.execute("DELETE FROM scrim_members WHERE scrim_id = ?", self.scrim_id)


class ScrimButtons(ui.View):
    """Takım seçme butonları"""
    def __init__(self, bot, scrim_id, channel, team1_name, team2_name):
        super().__init__(timeout=600)
        self.bot = bot
        self.scrim_id = scrim_id
        self.channel = channel
        self.team1_name = team1_name
        self.team2_name = team2_name
        self.team1_players = []
        self.team2_players = []
        self.max_per_team = 5
        
        # Buton etiketlerini güncelle
        self.children[0].label = f"{team1_name}"
        self.children[1].label = f"{team2_name}"

    @ui.button(label="Takım 1", style=ButtonStyle.blurple, custom_id="scrim:join_team1", emoji="🎮")
    async def join_team1(self, button: ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        
        user_id = inter.author.id
        
        if user_id in self.team2_players:
            return await inter.send(f"❌ Zaten {self.team2_name} takımındasın!", ephemeral=True)
        
        if user_id in self.team1_players:
            return await inter.send(f"⚠️ Zaten {self.team1_name} takımındasın!", ephemeral=True)
        
        if len(self.team1_players) >= self.max_per_team:
            return await inter.send(f"❌ {self.team1_name} dolu! (5/5)", ephemeral=True)
        
        self.team1_players.append(user_id)
        await inter.send(f"✅ {self.team1_name} takımına katıldın! ({len(self.team1_players)}/5)", ephemeral=True)
        
        await self.update_embed(inter)
        
        if len(self.team1_players) == 5 and len(self.team2_players) == 5:
            await self.start_scrim(inter)

    @ui.button(label="Takım 2", style=ButtonStyle.red, custom_id="scrim:join_team2", emoji="🎮")
    async def join_team2(self, button: ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        
        user_id = inter.author.id
        
        if user_id in self.team1_players:
            return await inter.send(f"❌ Zaten {self.team1_name} takımındasın!", ephemeral=True)
        
        if user_id in self.team2_players:
            return await inter.send(f"⚠️ Zaten {self.team2_name} takımındasın!", ephemeral=True)
        
        if len(self.team2_players) >= self.max_per_team:
            return await inter.send(f"❌ {self.team2_name} dolu! (5/5)", ephemeral=True)
        
        self.team2_players.append(user_id)
        await inter.send(f"✅ {self.team2_name} takımına katıldın! ({len(self.team2_players)}/5)", ephemeral=True)
        
        await self.update_embed(inter)
        
        if len(self.team1_players) == 5 and len(self.team2_players) == 5:
            await self.start_scrim(inter)

    @ui.button(label="Takımdan Ayrıl", style=ButtonStyle.grey, custom_id="scrim:leave", emoji="❌")
    async def leave_team(self, button: ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        
        user_id = inter.author.id
        
        if user_id in self.team1_players:
            self.team1_players.remove(user_id)
            await inter.send(f"🚪 {self.team1_name} takımından ayrıldın.", ephemeral=True)
        elif user_id in self.team2_players:
            self.team2_players.remove(user_id)
            await inter.send(f"🚪 {self.team2_name} takımından ayrıldın.", ephemeral=True)
        else:
            return await inter.send("❌ Herhangi bir takımda değilsin!", ephemeral=True)
        
        await self.update_embed(inter)

    @ui.button(label="Zorla Başlat", style=ButtonStyle.green, custom_id="scrim:force", emoji="🚀")
    async def force_start(self, button: ui.Button, inter: disnake.MessageInteraction):
        if not inter.author.guild_permissions.administrator:
            return await inter.send("❌ Sadece adminler zorla başlatabilir!", ephemeral=True)
        
        await inter.response.defer()
        
        if len(self.team1_players) < 2 or len(self.team2_players) < 2:
            return await inter.send("❌ Her takımda en az 2 oyuncu olmalı!", ephemeral=True)
        
        await self.start_scrim(inter, forced=True)

    async def update_embed(self, inter):
        """Embed'i güncelle"""
        embed = inter.message.embeds[0]
        
        team1_str = "\n".join([f"{i+1}. <@{uid}>" for i, uid in enumerate(self.team1_players)]) or "Henüz kimse yok"
        team2_str = "\n".join([f"{i+1}. <@{uid}>" for i, uid in enumerate(self.team2_players)]) or "Henüz kimse yok"
        
        embed.clear_fields()
        embed.add_field(
            name=f"🎮 {self.team1_name} ({len(self.team1_players)}/5)",
            value=team1_str,
            inline=True
        )
        embed.add_field(
            name=f"🎮 {self.team2_name} ({len(self.team2_players)}/5)",
            value=team2_str,
            inline=True
        )
        
        total = len(self.team1_players) + len(self.team2_players)
        status = "✅ Takımlar tamamlandı! Maç başlatılıyor..." if total == 10 else "⏳ Oyuncular bekleniyor..."
        embed.description = f"**Scrim ID:** `{self.scrim_id}`\n**Oyuncular:** {total}/10\n\n{status}"
        
        await inter.edit_original_message(embed=embed)

    async def start_scrim(self, inter, forced=False):
        """Scrim'i başlat"""
        self.stop()
        
        guild = inter.guild
        
        try:
            # Kategori
            category = await guild.create_category(
                name=f"🎯 SCRIM: {self.scrim_id}",
                overwrites={
                    guild.default_role: PermissionOverwrite(view_channel=False),
                    self.bot.user: PermissionOverwrite(
                        view_channel=True,
                        manage_channels=True,
                        manage_roles=True
                    )
                }
            )
            
            # Lobby
            lobby = await category.create_text_channel(f"lobby-{self.scrim_id}")
            
            # Ses kanalları - TAKIM İSİMLERİYLE
            voice1 = await category.create_voice_channel(f"🎮 {self.team1_name}")
            voice2 = await category.create_voice_channel(f"🎮 {self.team2_name}")
            
            # Roller - TAKIM İSİMLERİYLE
            role1 = await guild.create_role(
                name=f"{self.team1_name}",
                color=Color.blue(),
                mentionable=True
            )
            role2 = await guild.create_role(
                name=f"{self.team2_name}",
                color=Color.red(),
                mentionable=True
            )
            
            # Rolleri ver ve izinleri ayarla
            for uid in self.team1_players:
                member = guild.get_member(uid)
                if member:
                    await member.add_roles(role1)
                    await lobby.set_permissions(member, read_messages=True, send_messages=True)
                    await voice1.set_permissions(member, view_channel=True, connect=True)
            
            for uid in self.team2_players:
                member = guild.get_member(uid)
                if member:
                    await member.add_roles(role2)
                    await lobby.set_permissions(member, read_messages=True, send_messages=True)
                    await voice2.set_permissions(member, view_channel=True, connect=True)
            
            # Veritabanına kaydet
            await self.bot.execute(
                "INSERT INTO scrims(scrim_id, guild_id, lobby_id, voice1_id, voice2_id, role1_id, role2_id, team1_name, team2_name, channel_id) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                self.scrim_id, guild.id, lobby.id, voice1.id, voice2.id, 
                role1.id, role2.id, self.team1_name, self.team2_name, self.channel.id
            )
            
            # Oyuncuları kaydet
            for uid in self.team1_players:
                await self.bot.execute(
                    "INSERT INTO scrim_members(scrim_id, user_id, team) VALUES(?, ?, ?)",
                    self.scrim_id, uid, "team1"
                )
            
            for uid in self.team2_players:
                await self.bot.execute(
                    "INSERT INTO scrim_members(scrim_id, user_id, team) VALUES(?, ?, ?)",
                    self.scrim_id, uid, "team2"
                )
            
            # Lobby bilgilendirme
            info_embed = Embed(
                title="🎯 SCRIM BAŞLADI!",
                description=f"**{self.team1_name}** vs **{self.team2_name}**\n\n"
                           f"**Scrim ID:** `{self.scrim_id}`\n\n"
                           f"**Notlar:**\n"
                           f"• Lobi kurucusu ve şifreyi kendiniz belirleyin\n"
                           f"• Roller aralarında anlaşarak seçin\n"
                           f"• Maç bitince `/scrimwin {self.scrim_id}` komutuyla kazananı bildirin",
                color=Color.gold(),
                timestamp=datetime.now()
            )
            
            team1_mentions = " ".join([f"<@{uid}>" for uid in self.team1_players])
            team2_mentions = " ".join([f"<@{uid}>" for uid in self.team2_players])
            
            info_embed.add_field(
                name=f"🎮 {self.team1_name}",
                value=team1_mentions,
                inline=False
            )
            info_embed.add_field(
                name=f"🎮 {self.team2_name}",
                value=team2_mentions,
                inline=False
            )
            
            info_embed.set_footer(text="İyi oyunlar!", icon_url=guild.icon.url if guild.icon else None)
            
            await lobby.send(content=f"{role1.mention} {role2.mention}", embed=info_embed)
            
            # Orijinal mesajı güncelle
            success_embed = Embed(
                title="✅ SCRIM BAŞLATILDI!",
                description=f"**{self.team1_name}** vs **{self.team2_name}**\n\n"
                           f"**Scrim ID:** `{self.scrim_id}`\n\n"
                           f"Lobby: {lobby.mention}\n"
                           f"🎮 {self.team1_name}: {voice1.mention}\n"
                           f"🎮 {self.team2_name}: {voice2.mention}\n\n"
                           f"**Maç bitince:** `/scrimwin {self.scrim_id}`",
                color=Color.green()
            )
            
            await inter.edit_original_message(embed=success_embed, view=None)
            
        except Exception as e:
            await inter.send(f"❌ Hata: {e}", ephemeral=True)
            print(f"Scrim başlatma hatası: {e}")


class Scrim(commands.Cog):
    """
    🎯;Scrim System
    """
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Tabloları oluştur"""
        await self.bot.execute("""
            CREATE TABLE IF NOT EXISTS scrims(
                scrim_id TEXT PRIMARY KEY,
                guild_id INTEGER,
                lobby_id INTEGER,
                voice1_id INTEGER,
                voice2_id INTEGER,
                role1_id INTEGER,
                role2_id INTEGER,
                team1_name TEXT,
                team2_name TEXT,
                channel_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.bot.execute("""
            CREATE TABLE IF NOT EXISTS scrim_members(
                scrim_id TEXT,
                user_id INTEGER,
                team TEXT
            )
        """)
        
        await self.bot.execute("""
            CREATE TABLE IF NOT EXISTS scrim_stats(
                user_id INTEGER,
                guild_id INTEGER,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        
        await self.bot.execute("""
            CREATE TABLE IF NOT EXISTS scrim_log_channel(
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)

    @commands.slash_command(name="scrim")
    async def scrim(self, inter):
        """Scrim (Antrenman Maçı) komutları"""
        pass

    @scrim.sub_command(name="başlat")
    async def scrim_start(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        takım1: str,
        takım2: str,
        açıklama: str = ""
    ):
        """
        5v5 özel scrim başlat. Takım isimleriyle.
        
        Parameters
        ----------
        takım1: Birinci takımın ismi (örn: G2 Esports)
        takım2: İkinci takımın ismi (örn: Fnatic)
        açıklama: Scrim açıklaması (opsiyonel)
        """
        
        # İsim kontrolü
        if len(takım1) > 30 or len(takım2) > 30:
            return await inter.send("❌ Takım isimleri çok uzun! (max 30 karakter)", ephemeral=True)
        
        await inter.response.defer()
        
        scrim_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        embed = Embed(
            title="🎯 ÖZEL SCRIM MAÇI",
            description=f"**Scrim ID:** `{scrim_id}`\n**Oyuncular:** 0/10\n\n"
                       f"⏳ Oyuncular bekleniyor...\n\n"
                       f"{f'**Açıklama:** {açıklama}' if açıklama else ''}",
            color=Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name=f"🎮 {takım1} (0/5)",
            value="Henüz kimse yok",
            inline=True
        )
        embed.add_field(
            name=f"🎮 {takım2} (0/5)",
            value="Henüz kimse yok",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ Nasıl Çalışır?",
            value="• Takımını seç ve katıl\n"
                  "• Her takım 5 kişi olunca otomatik başlar\n"
                  "• Roller aralarında anlaşarak belirlenir\n"
                  "• Maç bitince `/scrimwin` ile kazananı bildirin",
            inline=False
        )
        
        embed.set_footer(
            text=f"Başlatan: {inter.author.display_name}",
            icon_url=inter.author.display_avatar.url
        )
        
        view = ScrimButtons(self.bot, scrim_id, inter.channel, takım1, takım2)
        
        await inter.send(embed=embed, view=view)

    @commands.slash_command(name="scrimwin")
    async def scrim_win(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        scrim_id: str
    ):
        """
        Scrim'in kazananını belirle (oylama ile).
        
        Parameters
        ----------
        scrim_id: Scrim ID'si
        """
        await inter.response.defer(ephemeral=True)
        # Scrim var mı?
        scrim_data = await self.bot.fetchrow(
            f"SELECT * FROM scrims WHERE scrim_id = '{scrim_id}'"
        )
        
        if not scrim_data:
            return await inter.send(f"❌ `{scrim_id}` ID'li scrim bulunamadı!", ephemeral=True)
        
        team1_name = scrim_data[7]
        team2_name = scrim_data[8]
        
        # Oylama embed'i
        embed = Embed(
            title="🏆 KAZANAN TAKIMI OYLA",
            description=f"**Scrim ID:** `{scrim_id}`\n\n"
                       f"**{team1_name}** vs **{team2_name}**\n\n"
                       f"Kazanan takım için oy verin! (6 oy = kazanır)",
            color=Color.gold()
        )
        
        embed.add_field(
            name=f"🏆 {team1_name} - 0 Oy",
            value="Henüz oy yok",
            inline=True
        )
        embed.add_field(
            name=f"🏆 {team2_name} - 0 Oy",
            value="Henüz oy yok",
            inline=True
        )
        
        view = ScrimWinButtons(self.bot, scrim_id, team1_name, team2_name)
        
        # Takım mention'ları
        members = await self.bot.fetch(
            f"SELECT user_id FROM scrim_members WHERE scrim_id = '{scrim_id}'"
        )
        mentions = " ".join([f"<@{m[0]}>" for m in members])
        
        await inter.send(content=mentions, embed=embed, view=view)

    @scrim.sub_command(name="iptal")
    async def scrim_cancel(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        scrim_id: str
    ):
        """
        Devam eden bir scrim'i iptal et.
        
        Parameters
        ----------
        scrim_id: İptal edilecek scrim'in ID'si
        """
        
        if not inter.author.guild_permissions.administrator:
            return await inter.send("❌ Sadece adminler iptal edebilir!", ephemeral=True)
        
        await inter.response.defer()
        
        scrim_data = await self.bot.fetchrow(
            f"SELECT * FROM scrims WHERE scrim_id = '{scrim_id}'"
        )
        
        if not scrim_data:
            return await inter.send(f"❌ Scrim bulunamadı!", ephemeral=True)
        
        guild = inter.guild
        
        try:
            # Temizlik
            for category in guild.categories:
                if category.name == f"🎯 SCRIM: {scrim_id}":
                    await category.delete()
            
            # Kanalları sil
            for channel_id in [scrim_data[2], scrim_data[3], scrim_data[4]]:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.delete()
            
            # Rolleri sil
            for role_id in [scrim_data[5], scrim_data[6]]:
                role = guild.get_role(role_id)
                if role:
                    await role.delete()
            
            # Veritabanından sil
            await self.bot.execute(f"DELETE FROM scrims WHERE scrim_id = '{scrim_id}'")
            await self.bot.execute(f"DELETE FROM scrim_members WHERE scrim_id = '{scrim_id}'")
            
            await inter.send(f"✅ Scrim `{scrim_id}` iptal edildi!")
        
        except Exception as e:
            await inter.send(f"⚠️ Hata: {e}", ephemeral=True)

    @scrim.sub_command(name="liste")
    async def scrim_list(self, inter: disnake.ApplicationCommandInteraction):
        """Devam eden tüm scrim'leri listele"""
        await inter.response.defer(ephemeral=True)
        
        scrims = await self.bot.fetch(
            f"SELECT * FROM scrims WHERE guild_id = {inter.guild.id}"
        )
        
        if not scrims:
            return await inter.send("📭 Şu anda aktif scrim yok.", ephemeral=True)
        
        embed = Embed(
            title="🎯 Aktif Scrim'ler",
            color=Color.blurple()
        )
        
        for scrim in scrims:
            scrim_id = scrim[0]
            team1_name = scrim[7]
            team2_name = scrim[8]
            lobby = self.bot.get_channel(scrim[2])
            
            members = await self.bot.fetch(
                f"SELECT user_id, team FROM scrim_members WHERE scrim_id = '{scrim_id}'"
            )
            
            team1_count = sum(1 for m in members if m[1] == 'team1')
            team2_count = sum(1 for m in members if m[1] == 'team2')
            
            embed.add_field(
                name=f"🎮 {scrim_id}",
                value=f"**{team1_name}** ({team1_count}/5) vs **{team2_name}** ({team2_count}/5)\n"
                      f"Lobby: {lobby.mention if lobby else 'Silinmiş'}",
                inline=False
            )
        
        await inter.send(embed=embed)

    @scrim.sub_command(name="stats")
    async def scrim_stats(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        kullanıcı: disnake.Member = None
    ):
        """
        Scrim istatistiklerini göster
        
        Parameters
        ----------
        kullanıcı: İstatistiği görmek istediğin kişi (opsiyonel)
        """
        await inter.response.defer()
        target = kullanıcı or inter.author
        
        stats = await self.bot.fetchrow(
            "SELECT wins, losses FROM scrim_stats WHERE user_id = ? AND guild_id = ?",
            target.id, inter.guild.id
        )
        
        if not stats:
            return await inter.send(f"📊 {target.mention} henüz scrim oynamamış!", ephemeral=True)
        
        wins = stats[0]
        losses = stats[1]
        total = wins + losses
        winrate = round((wins / total) * 100, 1) if total > 0 else 0
        
        embed = Embed(
            title=f"📊 {target.display_name} - Scrim İstatistikleri",
            color=target.color
        )
        
        embed.add_field(name="🏆 Galibiyet", value=f"{wins}", inline=True)
        embed.add_field(name="❌ Mağlubiyet", value=f"{losses}", inline=True)
        embed.add_field(name="📈 Win Rate", value=f"%{winrate}", inline=True)
        embed.add_field(name="🎮 Toplam Maç", value=f"{total}", inline=True)
        
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await inter.send(embed=embed)

    @scrim.sub_command(name="leaderboard")
    async def scrim_leaderboard(self, inter: disnake.ApplicationCommandInteraction):
        """Scrim liderlik tablosu"""
        await inter.response.defer()
        
        stats = await self.bot.fetch(
            f"SELECT user_id, wins, losses FROM scrim_stats WHERE guild_id = {inter.guild.id} "
            f"ORDER BY wins DESC LIMIT 10"
        )
        
        if not stats:
            return await inter.send("📭 Henüz scrim istatistiği yok!", ephemeral=True)
        
        embed = Embed(
            title="🏆 Scrim Liderlik Tablosu",
            color=Color.gold()
        )
        
        leaderboard_str = ""
        for i, (uid, wins, losses) in enumerate(stats, 1):
            total = wins + losses
            wr = round((wins / total) * 100, 1) if total > 0 else 0
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
            leaderboard_str += f"{medal} <@{uid}> - **{wins}W** {losses}L (%{wr})\n"
        
        embed.description = leaderboard_str
        embed.set_footer(text=f"Toplam {len(stats)} oyuncu")
        
        await inter.send(embed=embed)

    @scrim.sub_command(name="setlog")
    async def scrim_setlog(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        kanal: disnake.TextChannel
    ):
        """
        Scrim sonuçlarının gönderileceği log kanalını ayarla
        
        Parameters
        ----------
        kanal: Log kanalı
        """
        
        if not inter.author.guild_permissions.administrator:
            return await inter.send("❌ Sadece adminler ayarlayabilir!", ephemeral=True)
        
        await inter.response.defer(ephemeral=True)
        
        await self.bot.execute(
            "INSERT INTO scrim_log_channel(guild_id, channel_id) VALUES(?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET channel_id = ?",
            inter.guild.id, kanal.id, kanal.id
        )
        
        await inter.send(f"✅ Scrim log kanalı {kanal.mention} olarak ayarlandı!")


def setup(bot):
    bot.add_cog(Scrim(bot))
