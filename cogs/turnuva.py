import os
import io
import random
import math
from uuid import uuid4

import disnake
from disnake.ext import commands
from disnake import Embed, Color, File, ui, ButtonStyle
from PIL import Image, ImageDraw, ImageFont

from core.embeds import error, success

# =====================
# BRACKET IMAGE GENERATOR (YAN YANA OYUNCULAR, BÜYÜK GÖRSEL)
# =====================
class BracketImageGenerator:
    def __init__(self, width: int = None):
        # Varsayılan genişlik daha büyük tutularak embed önizlemesinin küçük görünmesi azaltılır.
        self.width = width or int(os.getenv("BRACKET_WIDTH", "1800"))
        self.height = 1200
        self.bg_color = (28, 30, 38)
        self.box_color = (44, 48, 64)
        self.line_color = (90, 95, 110)
        self.text_color = (235, 238, 240)
        self.winner_color = (0, 215, 120)
        self.pending_color = (255, 160, 60)

    def truncate_text(self, text: str, max_len: int = 36) -> str:
        if not text:
            return ""
        if len(text) <= max_len:
            return text
        return text[: max_len - 2] + ".."

    def create_bracket_image(self, matches_data, tournament_name: str, round_name: str):
        """
        matches_data: [
            { 'p1_name': 'Player1', 'p2_name': 'Player2', 'winner': 'Player1' or None, 'match_id': 'abc123' }
        ]
        Layout: her maç kutusunda oyuncu1 SOLDA, oyuncu2 SAĞDA (yan yana).
        Döner: BytesIO (PNG)
        """
        match_count = max(1, len(matches_data))
        # maç başına yüksekliği arttır, toplam yükseklik dinamik
        self.height = max(900, match_count * 140 + 260)

        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        # Font yükleme (fallback ile)
        try:
            title_font = ImageFont.truetype("arial.ttf", 48)
            round_font = ImageFont.truetype("arial.ttf", 28)
            name_font = ImageFont.truetype("arial.ttf", 26)
            small_font = ImageFont.truetype("arial.ttf", 18)
        except Exception:
            title_font = ImageFont.load_default()
            round_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Başlık ve round
        draw.text((self.width // 2, 48), f"{tournament_name}", fill=self.winner_color, font=title_font, anchor="mm")
        draw.text((self.width // 2, 110), f"{round_name}", fill=self.text_color, font=round_font, anchor="mm")

        # Maç kutuları
        start_y = 160
        box_width = int(self.width * 0.8)
        box_height = 120
        spacing = 24
        x_pos = (self.width - box_width) // 2

        # iç bölmeler: sol ve sağ için x'ler
        left_x = x_pos + 30
        right_x = x_pos + box_width - 30

        for i, match in enumerate(matches_data):
            y_pos = start_y + i * (box_height + spacing)
            # ana kutu
            draw.rounded_rectangle(
                [(x_pos, y_pos), (x_pos + box_width, y_pos + box_height)],
                radius=14,
                fill=self.box_color,
                outline=self.line_color,
                width=2,
            )

            # maç numarası ve id
            draw.text((x_pos + 18, y_pos + 12), f"Maç #{i+1}", fill=self.pending_color, font=small_font)
            draw.text((x_pos + box_width - 240, y_pos + 12), f"ID: {match['match_id'][:12]}", fill=(170, 170, 180), font=small_font)

            # sol oyuncu (solda hizalanmış)
            p1_name = self.truncate_text(match.get("p1_name", "???"), 36)
            p1_color = self.winner_color if match.get("winner") and match.get("winner") == match.get("p1_name") else self.text_color
            # anchor "lm" (left-middle) yerine default kullan; pillow default anchor farklılıkları olabileceğinden x,y hesapla
            draw.text((left_x, y_pos + 36), f"{p1_name}", fill=p1_color, font=name_font)

            # sağ oyuncu (sağa yasla)
            p2_name = self.truncate_text(match.get("p2_name", "BYE"), 36)
            p2_color = self.winner_color if match.get("winner") and match.get("winner") == match.get("p2_name") else self.text_color
            # sağa yaslamak için text width ölç, sonra çiz
            try:
                p2_text = f"{p2_name}"
                w2, _ = draw.textsize(p2_text, font=name_font)
                draw.text((right_x - w2 + 10, y_pos + 36), p2_text, fill=p2_color, font=name_font)
            except Exception:
                draw.text((right_x - 320, y_pos + 36), p2_name, fill=p2_color, font=name_font)

            # VS ortada
            draw.text((x_pos + box_width // 2, y_pos + box_height // 2 - 6), "VS", fill=(200, 200, 200), font=small_font, anchor="mm")

            # küçük kupa ikonları (kazananı vurgula)
            if match.get("winner") == match.get("p1_name"):
                draw.text((left_x + 420, y_pos + 36), "", font=name_font)
            if match.get("winner") == match.get("p2_name"):
                draw.text((right_x - 420, y_pos + 36), "", font=name_font)

            # durum (alt ortada)
            if match.get("winner"):
                status = f"✅ Kazanan: {self.truncate_text(match.get('winner'), 28)}"
                status_color = self.winner_color
            else:
                status = "Beklemede..."
                status_color = self.pending_color
            draw.text((x_pos + box_width // 2, y_pos + box_height - 14), status, fill=status_color, font=small_font, anchor="mm")

        # footer
        footer = "Scrimlab Turnuva Sistemi — /turnuva ver.0.01"
        draw.text((self.width // 2, self.height - 28), footer, fill=(140, 140, 150), font=small_font, anchor="mm")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf


# =====================
# TOURNAMENT MANAGER (DB + LOGIC)
# =====================
class TournamentManager:
    def __init__(self, bot):
        self.bot = bot
        self.img_generator = BracketImageGenerator(width=int(os.getenv("BRACKET_WIDTH", "1800")))

    async def create_tournament(self, guild_id: int, name: str, max_players: int, admin_id: int):
        if max_players not in [2, 4, 8, 16, 32, 64]:
            return None
        tournament_id = str(uuid4())[:8]
        join_code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=6))
        await self.bot.execute(
            """INSERT INTO tournaments(tournament_id, guild_id, name, max_players, join_code, status, current_round, admin_id)
               VALUES(?,?,?,?,?,?,?,?)""",
            tournament_id,
            guild_id,
            name,
            max_players,
            join_code,
            "registration",
            0,
            admin_id,
        )
        return {"tournament_id": tournament_id, "join_code": join_code}

    async def get_tournament(self, tournament_id: str):
        return await self.bot.fetchrow("SELECT * FROM tournaments WHERE tournament_id = ?", tournament_id)

    async def get_active_tournament(self, guild_id: int):
        return await self.bot.fetchrow(
            "SELECT * FROM tournaments WHERE guild_id = ? AND status != 'finished' ORDER BY created_at DESC LIMIT 1", guild_id
        )

    async def add_player(self, tournament_id: str, player_name: str, discord_id: int = None):
        tournament = await self.get_tournament(tournament_id)
        if not tournament:
            return {"success": False, "error": "Turnuva bulunamadı"}
        if tournament[5] != "registration":
            return {"success": False, "error": "Kayıt dönemi bitti"}
        current_players = await self.bot.fetch("SELECT * FROM tournament_players WHERE tournament_id = ?", tournament_id)
        if len(current_players) >= tournament[3]:
            return {"success": False, "error": "Turnuva dolu"}
        existing = await self.bot.fetchrow(
            "SELECT * FROM tournament_players WHERE tournament_id = ? AND (LOWER(player_name) = LOWER(?) OR discord_id = ?)",
            tournament_id,
            player_name,
            discord_id,
        )
        if existing:
            return {"success": False, "error": "Bu isimle/kullanıcıyla zaten kayıtlısın"}
        player_id = str(uuid4())[:8]
        await self.bot.execute(
            """INSERT INTO tournament_players(player_id, tournament_id, player_name, discord_id, eliminated, current_round)
               VALUES(?,?,?,?,?,?)""",
            player_id,
            tournament_id,
            player_name,
            discord_id,
            0,
            0,
        )
        return {"success": True, "player_id": player_id}

    async def start_tournament(self, tournament_id: str):
        tournament = await self.get_tournament(tournament_id)
        if not tournament:
            return {"success": False, "error": "Turnuva bulunamadı"}
        players = await self.bot.fetch("SELECT * FROM tournament_players WHERE tournament_id = ? AND eliminated = 0", tournament_id)
        if len(players) < 2:
            return {"success": False, "error": "En az 2 oyuncu gerekli"}
        players = list(players)
        random.shuffle(players)
        round_num = 1
        matches_created = 0
        for i in range(0, len(players), 2):
            if i + 1 < len(players):
                match_id = str(uuid4())[:8]
                await self.bot.execute(
                    """INSERT INTO tournament_matches(match_id, tournament_id, round, player1_id, player2_id, status)
                       VALUES(?,?,?,?,?,?)""",
                    match_id,
                    tournament_id,
                    round_num,
                    players[i][0],
                    players[i + 1][0],
                    "pending",
                )
                matches_created += 1
        await self.bot.execute("UPDATE tournaments SET status = ?, current_round = ? WHERE tournament_id = ?", "active", round_num, tournament_id)
        return {"success": True, "matches": matches_created, "round": round_num}

    async def set_winner(self, match_id: str, winner_player_id: str):
        match = await self.bot.fetchrow("SELECT * FROM tournament_matches WHERE match_id = ?", match_id)
        if not match:
            return {"success": False, "error": "Maç bulunamadı"}
        if match[6] == "completed":
            return {"success": False, "error": "Bu maç zaten tamamlandı"}
        tournament = await self.get_tournament(match[1])

        # güncelle
        await self.bot.execute("UPDATE tournament_matches SET winner_id = ?, status = ? WHERE match_id = ?", winner_player_id, "completed", match_id)
        loser_id = match[3] if winner_player_id == match[4] else match[4]
        await self.bot.execute("UPDATE tournament_players SET eliminated = 1 WHERE player_id = ?", loser_id)

        winner = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE player_id = ?", winner_player_id)
        # kazanana DM gönder
        if winner and winner[3]:
            try:
                user = await self.bot.fetch_user(winner[3])
                if user:
                    next_round = match[2] + 1
                    dm_embed = Embed(title="🎉 Tebrik Ederiz!", color=Color.green())
                    dm_embed.description = f"**{tournament[2]}** turnuvasında maçınızı kazandınız!!\n\n**Tur {match[2]}** → **Tur {next_round}**"
                    dm_embed.add_field(name="Oyuncu Adınız", value=winner[2], inline=True)
                    dm_embed.add_field(name="Maç ID", value=match_id, inline=True)
                    await user.send(embed=dm_embed)
            except Exception:
                pass

        # round tamamlandıysa bir sonraki roundu oluştur
        pending_matches = await self.bot.fetch(
            "SELECT * FROM tournament_matches WHERE tournament_id = ? AND round = ? AND status = 'pending'", match[1], match[2]
        )
        if not pending_matches:
            await self._create_next_round(match[1], match[2])

        return {"success": True, "winner_name": winner[2] if winner else "Unknown"}

    async def _create_next_round(self, tournament_id: str, completed_round: int):
        winner_ids = await self.bot.fetch(
            """SELECT DISTINCT winner_id FROM tournament_matches
               WHERE tournament_id = ? AND round = ? AND status = 'completed' AND winner_id IS NOT NULL""",
            tournament_id,
            completed_round,
        )
        winners = []
        seen_ids = set()
        for row in winner_ids:
            wid = row[0]
            if wid and wid not in seen_ids:
                player = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE player_id = ? AND eliminated = 0", wid)
                if player:
                    winners.append(player)
                seen_ids.add(wid)

        if len(winners) <= 1:
            await self.bot.execute("UPDATE tournaments SET status = ? WHERE tournament_id = ?", "finished", tournament_id)
            if winners:
                await self.bot.execute("UPDATE tournaments SET champion_id = ? WHERE tournament_id = ?", winners[0][0], tournament_id)
            return

        next_round = completed_round + 1
        matches_created = 0
        random.shuffle(winners)
        for i in range(0, len(winners), 2):
            if i + 1 < len(winners):
                match_id = str(uuid4())[:8]
                await self.bot.execute(
                    """INSERT INTO tournament_matches(match_id, tournament_id, round, player1_id, player2_id, status)
                       VALUES(?,?,?,?,?,?)""",
                    match_id,
                    tournament_id,
                    next_round,
                    winners[i][0],
                    winners[i + 1][0],
                    "pending",
                )
                matches_created += 1
        await self.bot.execute("UPDATE tournaments SET current_round = ? WHERE tournament_id = ?", next_round, tournament_id)

    async def generate_bracket_image(self, tournament_id: str):
        tournament = await self.get_tournament(tournament_id)
        if not tournament or tournament[5] == "registration":
            return None
        current_round = tournament[6]
        matches = await self.bot.fetch(
            "SELECT * FROM tournament_matches WHERE tournament_id = ? AND round = ? ORDER BY created_at", tournament_id, current_round
        )
        if not matches:
            return None

        matches_data = []
        for match in matches:
            p1 = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE player_id = ?", match[3])
            p2 = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE player_id = ?", match[4]) if match[4] else None
            winner_name = None
            if match[6] == "completed" and match[5]:
                winner = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE player_id = ?", match[5])
                winner_name = winner[2] if winner else None
            matches_data.append({"p1_name": p1[2] if p1 else "???", "p2_name": p2[2] if p2 else "BYE", "winner": winner_name, "match_id": match[0]})

        total_rounds = int(math.log2(tournament[3])) if tournament[3] > 0 else 1
        # Round adı: final/yarı/çeyrek vs
        if current_round == total_rounds:
            round_name = "FİNAL"
        elif current_round == total_rounds - 1:
            round_name = "YARI FİNAL"
        elif current_round == total_rounds - 2:
            round_name = "ÇEYREK FİNAL"
        else:
            round_name = f"Tur {current_round}"

        img_bytes = self.img_generator.create_bracket_image(matches_data, tournament[2], round_name)
        return img_bytes

    async def generate_ascii_bracket(self, tournament_id: str):
        tournament = await self.get_tournament(tournament_id)
        if not tournament or tournament[5] == "registration":
            return None
        current_round = tournament[6]
        matches = await self.bot.fetch("SELECT * FROM tournament_matches WHERE tournament_id = ? AND round = ?", tournament_id, current_round)
        if not matches:
            return "Henüz maç yok."

        total_rounds = int(math.log2(tournament[3])) if tournament[3] > 0 else 1
        if current_round == total_rounds:
            round_name = "Final"
        elif current_round == total_rounds - 1:
            round_name = "Yarı Final"
        elif current_round == total_rounds - 2:
            round_name = "Çeyrek Final"
        else:
            round_name = f"Round {current_round}"

        bracket = "╔═══════════════════════════════════════╗\n"
        bracket += f"║ {tournament[2][:35]:^35} ║\n"
        bracket += f"║ {round_name:^35} ║\n"
        bracket += "╠═══════════════════════════════════════╣\n"

        for idx, match in enumerate(matches, 1):
            p1 = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE player_id = ?", match[3])
            p2 = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE player_id = ?", match[4]) if match[4] else None
            p1_name = (p1[2][:15] if len(p1[2]) > 15 else p1[2]) if p1 else "???"
            p2_name = (p2[2][:15] if len(p2[2]) > 15 else p2[2]) if p2 else "BYE"

            if match[6] == "completed":
                winner = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE player_id = ?", match[5]) if match[5] else None
                winner_name = (winner[2][:15] if len(winner[2]) > 15 else winner[2]) if winner else "???"
                bracket += f"║ Maç {idx:02d} ║\n"
                bracket += f"║ ┌─ {p1_name:15} {'🏆' if match[5] == match[3] else ' '} ║\n"
                bracket += "║ │ ║\n"
                bracket += f"║ └─ {p2_name:15} {'🏆' if match[5] == match[4] else ' '} ║\n"
                bracket += f"║ Kazanan: {winner_name:15} ║\n"
            else:
                bracket += f"║ Maç {idx:02d} (ID: {match[0][:8]:8}) ║\n"
                bracket += f"║ ┌─ {p1_name:15} ║\n"
                bracket += "║ │ ║\n"
                bracket += f"║ └─ {p2_name:15} ║\n"
                bracket += "║ Bekleniyor... ║\n"

            if idx < len(matches):
                bracket += "╟───────────────────────────────────────╢\n"

        bracket += "╚═══════════════════════════════════════╝"
        return bracket

    def _get_round_name(self, round_num: int, total_rounds: int):
        remaining = total_rounds - round_num
        if remaining == 0:
            return "Final"
        elif remaining == 1:
            return "Yarı Final"
        elif remaining == 2:
            return "Çeyrek Final"
        else:
            return f"Round {round_num}"


# =====================
# WINNER SELECTION VIEW (BUTONLU) - butonlara sadece komutu çağıran admin veya başka adminler basabilir
# =====================
class WinnerSelectView(ui.View):
    def __init__(self, bot, match_id: str, p1_id: str, p1_name: str, p2_id: str, p2_name: str, tournament_manager: TournamentManager, allowed_user_id: int = None):
        super().__init__(timeout=300)
        self.bot = bot
        self.match_id = match_id
        self.tournament_manager = tournament_manager
        self.allowed_user_id = allowed_user_id

        # Player1 button
        self.player1_btn = ui.Button(label=f"🏆 {p1_name[:30]}", style=ButtonStyle.primary, custom_id=f"win1_{match_id}")
        self.player1_btn.callback = self._make_callback(p1_id, p1_name)
        self.add_item(self.player1_btn)

        # Player2 button (rakip varsa)
        if p2_id:
            self.player2_btn = ui.Button(label=f"🏆 {p2_name[:30]}", style=ButtonStyle.primary, custom_id=f"win2_{match_id}")
            self.player2_btn.callback = self._make_callback(p2_id, p2_name)
            self.add_item(self.player2_btn)

        # İptal butonu
        self.cancel_btn = ui.Button(label="❌ İptal", style=ButtonStyle.danger, custom_id=f"cancel_{match_id}")
        self.cancel_btn.callback = self.cancel_selection
        self.add_item(self.cancel_btn)

    def _is_allowed(self, inter: disnake.MessageInteraction) -> bool:
        # ya komutu çağıran kişi ya da admin olmalı
        if self.allowed_user_id and inter.author.id == self.allowed_user_id:
            return True
        if getattr(inter.author, "guild_permissions", None) and inter.author.guild_permissions.administrator:
            return True
        return False

    def _make_callback(self, winner_id: str, winner_name: str):
        async def callback(inter: disnake.MessageInteraction):
            # izin kontrolü
            if not self._is_allowed(inter):
                return await inter.response.send_message("Bu işlemi gerçekleştirmek için yetkiniz yok.", ephemeral=True)

            await inter.response.defer()
            result = await self.tournament_manager.set_winner(self.match_id, winner_id)
            if not result["success"]:
                return await inter.edit_original_message(embed=Embed(title="❌ Hata", description=result["error"], color=Color.red()), view=None)

            # Orijinal butonlu mesajı güncelle: butonları kaldır + kazanan bilgisi göster
            success_embed = Embed(title="🏆 Kazanan Belirlendi!", description=f"**{winner_name}** maçı kazandı!", color=0x00FF88)
            try:
                await inter.edit_original_message(embed=success_embed, view=None)
            except Exception:
                pass

            # Güncel bracket görselini büyük olarak kanala at
            match = await self.bot.fetchrow("SELECT * FROM tournament_matches WHERE match_id = ?", self.match_id)
            if match:
                img_bytes = await self.tournament_manager.generate_bracket_image(match[1])
                if img_bytes:
                    file = File(img_bytes, filename="bracket.png")
                    try:
                        await inter.channel.send(file=file)
                    except Exception:
                        pass

        return callback

    async def cancel_selection(self, inter: disnake.MessageInteraction):
        if not self._is_allowed(inter):
            return await inter.response.send_message("Bu işlemi gerçekleştirmek için yetkiniz yok.", ephemeral=True)
        await inter.response.defer()
        cancel_embed = Embed(title="❌ İptal Edildi", description="Kazanan seçimi iptal edildi.", color=Color.red())
        await inter.edit_original_message(embed=cancel_embed, view=None)


# =====================
# COG (Discord komutları - tam fonksiyonel)
# =====================
class Turnuva(commands.Cog):
    """🏆 Tournament management"""

    def __init__(self, bot):
        self.bot = bot
        self.manager = TournamentManager(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        await self._create_tables()

    async def _create_tables(self):
        # create tables if not exists
        await self.bot.execute(
            """CREATE TABLE IF NOT EXISTS tournaments (
                tournament_id TEXT PRIMARY KEY,
                guild_id INTEGER,
                name TEXT,
                max_players INTEGER,
                join_code TEXT,
                status TEXT,
                current_round INTEGER,
                admin_id INTEGER,
                champion_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await self.bot.execute(
            """CREATE TABLE IF NOT EXISTS tournament_players (
                player_id TEXT PRIMARY KEY,
                tournament_id TEXT,
                player_name TEXT,
                discord_id INTEGER,
                eliminated INTEGER DEFAULT 0,
                current_round INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await self.bot.execute(
            """CREATE TABLE IF NOT EXISTS tournament_matches (
                match_id TEXT PRIMARY KEY,
                tournament_id TEXT,
                round INTEGER,
                player1_id TEXT,
                player2_id TEXT,
                winner_id TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )

    @commands.slash_command(name="turnuva")
    async def tournament_group(self, inter):
        """Turnuva yönetim komutları"""
        pass

    @tournament_group.sub_command(name="oluştur")
    async def create(self, inter: disnake.ApplicationCommandInteraction, isim: str, max_oyuncu: int = commands.Param(choices=[2, 4, 8, 16, 32, 64])):
        """Yeni bir turnuva oluştur (Sadece adminler)"""
        if not inter.author.guild_permissions.administrator:
            return await inter.send(embed=error("Bu komutu sadece adminler kullanabilir."), ephemeral=True)

        await inter.response.defer()
        active = await self.manager.get_active_tournament(inter.guild.id)
        if active:
            return await inter.send(embed=error(f"Zaten aktif bir turnuva var: **{active[2]}**"), ephemeral=True)

        result = await self.manager.create_tournament(inter.guild.id, isim, max_oyuncu, inter.author.id)
        if not result:
            return await inter.send(embed=error("Turnuva oluşturulamadı."), ephemeral=True)

        embed = Embed(color=0x5865F2)
        embed.set_author(name="🏆 TURNUVA OLUŞTURULDU!", icon_url=inter.guild.icon.url if inter.guild.icon else None)
        embed.description = f"### {isim}\nDurum: Kayıt Açık\nMax Oyuncu: {max_oyuncu}"
        embed.add_field(name="📋 Turnuva Bilgileri", value=f"ID: {result['tournament_id']}\nKod: {result['join_code']}", inline=False)
        embed.add_field(name="💡 Nasıl Katılınır?", value=f"Discord: /turnuva katıl {result['join_code']}\nDiscord'suz: /turnuva kayıt {result['join_code']} İsim#Tag", inline=False)
        embed.set_footer(text=f"Oluşturan: {inter.author.display_name}")
        embed.timestamp = disnake.utils.utcnow()
        await inter.send(embed=embed)

    @tournament_group.sub_command(name="katıl")
    async def join(self, inter: disnake.ApplicationCommandInteraction, kod: str):
        """Discord hesabınla turnuvaya katıl"""
        await inter.response.defer(ephemeral=True)
        tournament = await self.bot.fetchrow("SELECT * FROM tournaments WHERE UPPER(join_code) = UPPER(?) AND guild_id = ?", kod, inter.guild.id)
        if not tournament:
            return await inter.send(embed=error("Geçersiz turnuva kodu."), ephemeral=True)

        ign_data = await self.bot.fetchrow("SELECT ign FROM igns WHERE user_id = ? AND guild_id = ? AND game = 'lol'", inter.author.id, inter.guild.id)
        player_name = ign_data[0] if ign_data else inter.author.display_name

        result = await self.manager.add_player(tournament[0], player_name, inter.author.id)
        if not result["success"]:
            return await inter.send(embed=error(result["error"]), ephemeral=True)

        current_players = await self.bot.fetch("SELECT * FROM tournament_players WHERE tournament_id = ?", tournament[0])
        embed = Embed(color=0x00FF88)
        embed.set_author(name="✅ Turnuvaya Katıldınız!", icon_url=inter.author.display_avatar.url if inter.author.display_avatar else None)
        embed.description = f"### 🏆 {tournament[2]}\n{player_name}"
        embed.add_field(name="📊 Durum", value=f"Kayıtlı: {len(current_players)}/{tournament[3]}\nDoluluk: {int((len(current_players)/tournament[3])*100)}%")
        embed.timestamp = disnake.utils.utcnow()
        await inter.send(embed=embed, ephemeral=True)

    @tournament_group.sub_command(name="kayıt")
    async def register(self, inter: disnake.ApplicationCommandInteraction, kod: str, isim: str):
        """İsim#etiket ile turnuvaya katıl (Discord hesabı olmayan için)"""
        if not inter.author.guild_permissions.administrator:
            return await inter.send(embed=error("Bu komutu sadece adminler kullanabilir."), ephemeral=True)

        await inter.response.defer(ephemeral=True)
        tournament = await self.bot.fetchrow("SELECT * FROM tournaments WHERE UPPER(join_code) = UPPER(?) AND guild_id = ?", kod, inter.guild.id)
        if not tournament:
            return await inter.send(embed=error("Geçersiz turnuva kodu."), ephemeral=True)

        result = await self.manager.add_player(tournament[0], isim, None)
        if not result["success"]:
            return await inter.send(embed=error(result["error"]), ephemeral=True)

        current_players = await self.bot.fetch("SELECT * FROM tournament_players WHERE tournament_id = ?", tournament[0])
        embed = Embed(color=0x00FF88)
        embed.set_author(name="✅ Oyuncu Eklendi!")
        embed.description = f"**{isim}** turnuvaya eklendi.\nKayıtlı: {len(current_players)}/{tournament[3]}"
        await inter.send(embed=embed)

    @tournament_group.sub_command(name="başlat")
    async def start(self, inter: disnake.ApplicationCommandInteraction):
        """Turnuvayı başlat ve ilk turu oluştur (Sadece adminler)"""
        if not inter.author.guild_permissions.administrator:
            return await inter.send(embed=error("Bu komutu sadece adminler kullanabilir."), ephemeral=True)

        await inter.response.defer()

        tournament = await self.manager.get_active_tournament(inter.guild.id)
        if not tournament:
            return await inter.send(embed=error("Aktif turnuva bulunamadı."), ephemeral=True)
        if tournament[5] != "registration":
            return await inter.send(embed=error("Turnuva zaten başladı."), ephemeral=True)

        result = await self.manager.start_tournament(tournament[0])
        if not result["success"]:
            return await inter.send(embed=error(result["error"]), ephemeral=True)

        embed = Embed(title="🔥 Turnuva Başladı!", description=f"**{tournament[2]}** turnuvası başladı!", color=Color.red())
        embed.add_field(name="Round 1 Eşleşmeleri", value=f"{result['matches']} maç oluşturuldu", inline=False)
        await inter.send(embed=embed)

        # ASCII olarak da göster
        ascii_bracket = await self.manager.generate_ascii_bracket(tournament[0])
        if ascii_bracket:
            # ascii'yi kod bloğu olarak at
            await inter.channel.send(f"```\n{ascii_bracket}\n```")

        # Büyük görsel gönder (dosya olarak)
        img_bytes = await self.manager.generate_bracket_image(tournament[0])
        if img_bytes:
            file = File(img_bytes, filename="bracket.png")
            try:
                # Direkt dosya gönder: Discord önizlemesi daha büyük görünür
                await inter.channel.send(file=file)
            except Exception:
                # fallback embed ile gönder
                img_embed = Embed(title=f"🏆 {tournament[2]} - Round 1", color=0x5865F2)
                img_embed.set_image(url="attachment://bracket.png")
                await inter.channel.send(embed=img_embed, file=file)

    @tournament_group.sub_command(name="kazanan")
    async def winner(self, inter: disnake.ApplicationCommandInteraction, mac_id: str):
        """Maç kazananını buton ile belirle (Sadece adminler)"""
        if not inter.author.guild_permissions.administrator:
            return await inter.send(embed=error("Bu komutu sadece adminler kullanabilir."), ephemeral=True)

        await inter.response.defer()
        match = await self.bot.fetchrow("SELECT * FROM tournament_matches WHERE match_id = ?", mac_id)
        if not match:
            return await inter.send(embed=error("Maç bulunamadı."), ephemeral=True)

        p1 = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE player_id = ?", match[3])
        p2 = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE player_id = ?", match[4]) if match[4] else None

        if not p1:
            return await inter.send(embed=error("Maçta oyuncu bulunamadı."), ephemeral=True)

        # Eğer rakip yoksa otomatik kazanan ata
        if not p2:
            result = await self.manager.set_winner(mac_id, p1[0])
            if not result["success"]:
                return await inter.send(embed=error(result["error"]), ephemeral=True)
            return await inter.send(embed=success(f"{p1[2]} otomatik kazandı (rakip yok)."))

        # Önce büyük görseli gönder (varsa)
        tournament = await self.manager.get_tournament(match[1])
        img_bytes = await self.manager.generate_bracket_image(match[1])
        view = WinnerSelectView(self.bot, mac_id, p1[0], p1[2], p2[0], p2[2], self.manager, allowed_user_id=inter.author.id)

        try:
            if img_bytes:
                file = File(img_bytes, filename="bracket.png")
                await inter.channel.send(file=file)
        except Exception:
            pass

        # Sonra butonlu embed gönder
        embed = Embed(title="🏁 Maç - Kazananı Seç", description=f"**{p1[2]}** vs **{p2[2]}**\nMaç ID: `{mac_id}`", color=0x5865F2)
        embed.add_field(name="Oyuncular", value=f"1️⃣ {p1[2]}\n2️⃣ {p2[2]}", inline=False)
        await inter.send(embed=embed, view=view)

    @tournament_group.sub_command(name="bracket")
    async def bracket(self, inter: disnake.ApplicationCommandInteraction):
        """Turnuva bracket'ini göster (büyük görsel)"""
        await inter.response.defer()
        tournament = await self.manager.get_active_tournament(inter.guild.id)
        if not tournament:
            return await inter.send(embed=error("Aktif turnuva bulunamadı."), ephemeral=True)

        img_bytes = await self.manager.generate_bracket_image(tournament[0])
        if img_bytes:
            file = File(img_bytes, filename="bracket.png")
            try:
                await inter.channel.send(file=file)
            except Exception:
                embed = Embed(title=f"🏆 {tournament[2]} - Bracket", color=0x5865F2)
                embed.set_image(url="attachment://bracket.png")
                await inter.channel.send(embed=embed, file=file)
            return

        ascii_bracket = await self.manager.generate_ascii_bracket(tournament[0])
        if ascii_bracket:
            if len(ascii_bracket) > 1900:
                file = disnake.File(io.BytesIO(ascii_bracket.encode()), filename="bracket.txt")
                await inter.channel.send(file=file)
            else:
                await inter.channel.send(f"```\n{ascii_bracket}\n```")

    @tournament_group.sub_command(name="liste")
    async def list_players(self, inter: disnake.ApplicationCommandInteraction):
        """Turnuvadaki oyuncuları listele"""
        await inter.response.defer()
        tournament = await self.manager.get_active_tournament(inter.guild.id)
        if not tournament:
            return await inter.send(embed=error("Aktif turnuva bulunamadı."), ephemeral=True)

        players = await self.bot.fetch("SELECT * FROM tournament_players WHERE tournament_id = ? ORDER BY joined_at", tournament[0])
        if not players:
            return await inter.send(embed=error("Henüz kayıtlı oyuncu yok."), ephemeral=True)

        embed = Embed(title=f"👥 {tournament[2]} - Oyuncular", description=f"**Toplam:** {len(players)}/{tournament[3]}", color=Color.blue())
        player_list = ""
        for i, p in enumerate(players, 1):
            status = "❌ Elendi" if p[4] else "✅ Aktif"
            discord_mention = f"<@{p[3]}>" if p[3] else "Discord'suz"
            player_list += f"{i}. **{p[2]}** ({discord_mention}) - {status}\n"

        if len(player_list) < 1024:
            embed.add_field(name="Oyuncular", value=player_list, inline=False)
        else:
            chunks = [player_list[i : i + 1000] for i in range(0, len(player_list), 1000)]
            for i, chunk in enumerate(chunks):
                embed.add_field(name=f"Oyuncular ({i+1}/{len(chunks)})", value=chunk, inline=False)

        await inter.send(embed=embed)

    @tournament_group.sub_command(name="debug")
    async def debug_tournament(self, inter: disnake.ApplicationCommandInteraction):
        """Turnuva debug bilgileri (Sadece adminler) — detaylı oyuncu listesi eklendi"""
        if not inter.author.guild_permissions.administrator:
            return await inter.send(embed=error("Bu komutu sadece adminler kullanabilir."), ephemeral=True)

        await inter.response.defer(ephemeral=True)

        tournament = await self.manager.get_active_tournament(inter.guild.id)
        if not tournament:
            return await inter.send(embed=error("Aktif turnuva bulunamadı."), ephemeral=True)

        all_matches = await self.bot.fetch("SELECT round, COUNT(*) as count FROM tournament_matches WHERE tournament_id = ? GROUP BY round", tournament[0])
        current_round_matches = await self.bot.fetch("SELECT * FROM tournament_matches WHERE tournament_id = ? AND round = ?", tournament[0], tournament[6])

        # Oyuncu detaylarını topla
        players = await self.bot.fetch("SELECT * FROM tournament_players WHERE tournament_id = ? ORDER BY joined_at", tournament[0])
        player_lines = []
        for i, p in enumerate(players, 1):
            status = "Elendi" if p[4] else "Aktif"
            mention = f"<@{p[3]}>" if p[3] else "Discord'suz"
            player_lines.append(f"{i}. {p[2]} — {mention} — {status} (ID: {p[0]})")

        player_field = "\n".join(player_lines) if player_lines else "Oyuncu yok"

        embed = Embed(title="🔧 Debug Bilgileri", description=f"**Turnuva:** {tournament[2]}\n**Durum:** {tournament[5]}\n**Current Round:** {tournament[6]}", color=Color.orange())
        rounds_info = "\n".join([f"Round {r[0]}: {r[1]} maç" for r in all_matches]) if all_matches else "Maç yok"
        embed.add_field(name="Tüm Roundlar", value=rounds_info, inline=False)
        current_info = "\n".join([f"{i+1}. ID: {m[0][:12]} (Round {m[2]})" for i, m in enumerate(current_round_matches)]) if current_round_matches else "Maç yok"
        embed.add_field(name=f"Current Round ({tournament[6]}) Maçları", value=current_info[:1024], inline=False)
        embed.add_field(name=f"Oyuncular ({len(players)})", value=(player_field[:1024] if len(player_field) > 0 else "Yok"), inline=False)

        await inter.send(embed=embed, ephemeral=True)

    @tournament_group.sub_command(name="sıradansil")
    async def remove_player(self, inter: disnake.ApplicationCommandInteraction, oyuncu_isim: str):
        """Oyuncuyu turnuvadan çıkar (Sadece adminler)"""
        if not inter.author.guild_permissions.administrator:
            return await inter.send(embed=error("Bu komutu sadece adminler kullanabilir."), ephemeral=True)

        await inter.response.defer()
        tournament = await self.manager.get_active_tournament(inter.guild.id)
        if not tournament:
            return await inter.send(embed=error("Aktif turnuva bulunamadı."), ephemeral=True)

        player = await self.bot.fetchrow("SELECT * FROM tournament_players WHERE tournament_id = ? AND LOWER(player_name) = LOWER(?)", tournament[0], oyuncu_isim)
        if not player:
            return await inter.send(embed=error(f"'{oyuncu_isim}' isimli oyuncu bulunamadı."), ephemeral=True)

        await self.bot.execute("DELETE FROM tournament_players WHERE player_id = ?", player[0])
        embed = Embed(title="✅ Oyuncu Silindi!", description=f"**{player[2]}** turnuvadan çıkarıldı.", color=Color.green())
        await inter.send(embed=embed)


def setup(bot):
    bot.add_cog(Turnuva(bot))
