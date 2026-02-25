import asyncio
import itertools
import json
import random
import re
import traceback
import uuid
import string
from datetime import datetime, timedelta
from urllib.parse import quote

import async_timeout
import websockets
from disnake import (ButtonStyle, Color, Embed, PermissionOverwrite,
                     SelectOption, ui)
import disnake
from disnake.ext import tasks
from trueskill import Rating, quality

from core.buttons import ConfirmationButtons
from core.embeds import error, success
from core.selectmenus import SelectMenuDeploy

LOL_LABELS = ["Top", "Jungle", "Mid", "ADC", "Support"]
VALORANT_LABELS = ["Controller", "Initiator", "Sentinel", "Duelist", "Flex"]
OVERWATCH_LABELS = ["Tank", "DPS 1", "DPS 2", "Support 1", "Support 2"]
OTHER_LABELS = ["Role 1", "Role 2", "Role 3", "Role 4", "Role 5"]


async def gen_1v1_embed(bot, game_id: str) -> Embed:
    """Builds the 1v1 queue embed with current participants."""
    participants = await bot.fetch(
        "SELECT author_id FROM game_member_data WHERE game_id = ?", game_id
    )
    
    # Progress bar oluştur
    filled = len(participants)
    progress = "▰" * filled + "▱" * (2 - filled)
    status_emoji = "🟢" if filled == 2 else "🟡" if filled == 1 else "⚫"
    
    # Oyuncu listesi
    lines = []
    player_emojis = ["🔴", "🔵"]
    for idx, row in enumerate(participants):
        lines.append(f"{player_emojis[idx]} <@{row[0]}>")
    
    if not lines:
        body = "```\n⏳ Rakip bekleniyor...\n```"
    elif len(lines) == 1:
        body = f"{lines[0]}\n\n```diff\n+ Bir rakip daha bekleniyor!\n```"
    else:
        body = "\n⚔️ **VS** ⚔️\n".join(lines)

    embed = Embed(
        title="⚔️ 1v1 ARENA ⚔️",
        description=(
            f"```ansi\n\u001b[1;33m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\u001b[0m\n```\n"
            f"**{status_emoji} Durum:** `{filled}/2 Oyuncu`\n"
            f"**📊 İlerleme:** {progress}\n\n"
            f"🎮 *Butona tıklayarak sıraya katıl!*"
        ),
        color=Color.from_rgb(255, 85, 85) if filled == 0 else Color.from_rgb(255, 170, 0) if filled == 1 else Color.from_rgb(85, 255, 85),
    )
    
    embed.add_field(
        name="🏟️ Arena Oyuncuları", 
        value=body, 
        inline=False
    )
    
    # Ödül bilgisi
    embed.add_field(
        name="🏆 Ödül", 
        value="```\n🥇 Kazanan: +25 MMR\n🥈 Kaybeden: -15 MMR\n```", 
        inline=True
    )
    
    # Kurallar
    embed.add_field(
        name="📜 Kurallar", 
        value="```\n• ARAM Haritası\n• First Blood Kazanır\n• Geri Dönüş Yasak\n```", 
        inline=True
    )
    
    # Thumbnail
    embed.set_thumbnail(url="https://media.giphy.com/media/l0HlNQ03J5JxX6lva/giphy.gif")
    
    # Banner
    embed.set_image(url="https://cdn.discordapp.com/attachments/1452690176760479755/1453399438755369082/ding-ding-ding-alistar_1.gif")
    
    with open("assets/tips.txt", "r") as f:
        tips = f.readlines()
    tip = random.choice(tips) if tips else ""
    
    embed.set_footer(
        text=f"🎮 {game_id} • 💡 {tip.strip() if tip else 'İyi oyunlar!'}",
        icon_url="https://cdn.discordapp.com/emojis/1078086241221877941.png"
    )
    embed.timestamp = datetime.now()
    
    return embed


def generate_lobby_credentials() -> tuple[str, str]:
    """Returns a random lobby name and password."""
    lobby_name = f"1v1-{random.randint(1000, 9999)}"
    password = "".join(random.choices(string.digits, k=6))
    return lobby_name, password

async def start_queue(bot, channel, game, author=None, existing_msg = None, game_id = None):
    def region_icon(region, game):
        # Sadece League of Legends için region_icon
        if region == "euw":
            icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853028175934/OW_Europe.png"
        elif region == "eune":
            icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853028175934/OW_Europe.png"
        elif region == "br":
            icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444852579373136/OW_Americas.png"
        elif region == "la":
            icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444852579373136/OW_Americas.png"
        elif region == "jp":
            icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853233684581/VAL_AP.png"
        elif region == "las":
            icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444852579373136/OW_Americas.png"
        elif region == "tr":
            icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853233684581/VAL_AP.png"
        elif region == "oce":
            icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853233684581/VAL_AP.png"
        elif region == "ru":
            icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853233684581/VAL_AP.png"
        else:
            icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444852369670214/VAL_NA.png"
        return icon_url

    def banner_icon(game):
        return "https://cdn.discordapp.com/attachments/1452690176760479755/1453399438755369082/ding-ding-ding-alistar_1.gif?ex=694d4f35&is=694bfdb5&hm=0ff1c7c933ecc2d5a43f1efb7aae9d20bc74b93f435e8f02d4a1ea1dc6f2ee2a&"

    def get_title(game):
        return "League of Legends"

    data = await bot.fetchrow(
        "SELECT * FROM queuechannels WHERE channel_id = ?",
        channel.id
    )
    if not data:
        try:
            return await channel.send(
                embed=error(
                    f"{channel.mention} is not setup as the queue channel, please run this command in a queue channel."
                )
            )
        except:
            if author:
                return await author.send(embed=error(f"Could not send queue in {channel.mention}, please check my permissions."))

    # If you change this - update /events.py L28 as well!
    
    testmode = await bot.check_testmode(channel.guild.id)
    if game == "1v1":
        # Özel 1v1 sırası: rol seçimi yok, sadece 2 kişi.
        if not game_id and existing_msg and existing_msg.embeds:
            try:
                footer = existing_msg.embeds[0].footer.text or ""
                game_id = footer.split("\n")[0].replace("🎮", "").strip()
            except Exception:
                game_id = None
        if not game_id:
            game_id = str(uuid.uuid4()).split("-")[0]

        embed = await gen_1v1_embed(bot, game_id)
        view = Queue1v1(bot, game_id)
        try:
            if existing_msg:
                await existing_msg.edit(embed=embed, view=view, content="")
            else:
                await channel.send(embed=embed, view=view)
        except Exception:
            if author:
                await author.send(
                    embed=error(
                        f"{channel.mention} kanalına 1v1 kuyruğu gönderilemedi, yetkilerimi kontrol eder misin?"
                    )
                )
        return

    if testmode:
        title = "Test Modu"
    else:
        title = get_title(game)
    
    # Oyuncu sayısını hesapla
    if existing_msg and game_id:
        game_members = await bot.fetch(
            "SELECT * FROM game_member_data WHERE game_id = ?",
            game_id
        )
        player_count = len(game_members)
    else:
        player_count = 0
        game_members = []
    
    # Sade gri renk
    embed = Embed(
        title=title,
        color=Color.from_rgb(47, 49, 54)  # Discord koyu gri
    )
    
    # Sadece oyuncu sayısı
    embed.description = f"{player_count}/10"
    
    # Tek oyuncu listesi - takım ayrımı yok
    if existing_msg and game_members:
        players = ""
        for member in game_members:
            players += f"<@{member[0]}>\n"
        players = players.strip() or "-"
    else:
        players = "-"
    
    embed.add_field(name="Oyuncular", value=players, inline=False)
    sbmm = True
    
    # Footer sadece oyun ID
    if existing_msg:
        footer_game_id = game_id
    else:
        footer_game_id = str(uuid.uuid4()).split("-")[0]
    
    embed.set_footer(text=footer_game_id)
    
    duo_pref = await bot.fetchrow(
        "SELECT * FROM duo_queue_preference WHERE guild_id = ?",
        channel.guild.id
    )
    duo = bool(duo_pref)
    
    try:
        if existing_msg:
            await existing_msg.edit(embed=embed, view=Queue(bot, sbmm, duo, game, testmode), content="")
        else:
            await channel.send(embed=embed, view=Queue(bot, sbmm, duo, game, testmode))
    except:
        if author:
            await author.send(embed=error(f"Could not send queue in {channel.mention}, please check my permissions."))


class Join1v1Button(ui.Button):
    def __init__(self, bot):
        super().__init__(label="Katıl (1v1)", style=ButtonStyle.green, custom_id="1v1-queue:join")
        self.bot = bot

    async def callback(self, inter):
        await inter.response.defer(ephemeral=True)
        view: Queue1v1 = self.view  # type: ignore
        view.ensure_game_id(inter)

        preference = await self.bot.fetchrow(
            "SELECT * FROM queue_preference WHERE guild_id = ?", inter.guild.id
        )
        if preference and preference[1] == 2:
            in_other = await self.bot.fetch(
                "SELECT * FROM game_member_data WHERE author_id = ? and game_id != ?",
                inter.author.id,
                view.game_id,
            )
            if in_other:
                return await inter.send(
                    embed=error("Başka bir sıradasın, önce oradan ayrılmalısın."),
                    ephemeral=True,
                )

        existing = await self.bot.fetchrow(
            "SELECT * FROM game_member_data WHERE author_id = ? and game_id = ?",
            inter.author.id,
            view.game_id,
        )
        if existing:
            return await inter.send(embed=error("Zaten 1v1 sırasındasın."), ephemeral=True)

        participants = await self.bot.fetch(
            "SELECT author_id FROM game_member_data WHERE game_id = ?", view.game_id
        )
        if len(participants) >= 2:
            return await inter.send(
                embed=error("Sıra dolu, birinin çıkmasını bekle."), ephemeral=True
            )

        team = "red" if not participants else "blue"
        await self.bot.execute(
            "INSERT INTO game_member_data(author_id, role, team, game_id, queue_id, channel_id) VALUES(?, ?, ?, ?, ?, ?)",
            inter.author.id,
            "1v1",
            team,
            view.game_id,
            inter.message.id,
            inter.channel.id,
        )

        await view.refresh(inter)

        if len(participants) + 1 == 2:
            await view.start_match(inter)
        else:
            await inter.send(embed=success("1v1 sırasına katıldın."), ephemeral=True)


class Leave1v1Button(ui.Button):
    def __init__(self, bot):
        super().__init__(label="Sıradan Ayrıl", style=ButtonStyle.red, custom_id="1v1-queue:leave")
        self.bot = bot

    async def callback(self, inter):
        await inter.response.defer(ephemeral=True)
        view: Queue1v1 = self.view  # type: ignore
        view.ensure_game_id(inter)

        existing = await self.bot.fetchrow(
            "SELECT * FROM game_member_data WHERE author_id = ? and game_id = ?",
            inter.author.id,
            view.game_id,
        )
        if not existing:
            return await inter.send(embed=error("Bu 1v1 kuyruğunda değilsin."), ephemeral=True)

        await self.bot.execute(
            "DELETE FROM game_member_data WHERE author_id = ? and game_id = ?",
            inter.author.id,
            view.game_id,
        )
        await view.refresh(inter)
        await inter.send(embed=success("Kuyruktan ayrıldın."), ephemeral=True)


class Queue1v1(ui.View):
    def __init__(self, bot, game_id=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.game_id = game_id
        self.add_item(Join1v1Button(bot))
        self.add_item(Leave1v1Button(bot))

    def ensure_game_id(self, inter):
        if not self.game_id and inter.message and inter.message.embeds:
            try:
                footer = inter.message.embeds[0].footer.text or ""
                self.game_id = footer.split("\n")[0].replace("🎮", "").strip()
            except Exception:
                self.game_id = None
        if not self.game_id:
            self.game_id = str(uuid.uuid4()).split("-")[0]

    async def refresh(self, inter):
        self.ensure_game_id(inter)
        embed = await gen_1v1_embed(self.bot, self.game_id)
        await inter.message.edit(embed=embed, view=self)

    async def start_match(self, inter):
        participants = await self.bot.fetch(
            "SELECT author_id FROM game_member_data WHERE game_id = ?", self.game_id
        )
        if len(participants) < 2:
            return

        # Lobi bilgisini göndermek için özel bir kanal oluştur/kullan
        lobby_channel = inter.channel
        try:
            category = inter.channel.category
            if category:
                existing = disnake.utils.get(category.text_channels, name="1v1-lobi")
                if existing:
                    lobby_channel = existing
                else:
                    lobby_channel = await category.create_text_channel("1v1-lobi")
        except Exception:
            lobby_channel = inter.channel

        lobby_name, password = generate_lobby_credentials()
        mentions = " vs ".join(f"<@{row[0]}>" for row in participants)
        lobby_embed = Embed(
            title="1v1 Lobi",
            description=(
                f"{mentions}\n\n"
                f"**Oda İsmi:** `{lobby_name}`\n"
                f"**Şifre:** `{password}`\n\n"
                "*Map Olarak Aram Seçiniz.*"
            ),
            color=Color.green(),
        )
        lobby_embed.set_image(
            url="https://static.wikia.nocookie.net/leagueoflegends/images/6/6d/Howling_Abyss_Screenshot.jpg/revision/latest?cb=20130317071425"
        )

        await lobby_channel.send(embed=lobby_embed)
        await self.bot.execute(
            "DELETE FROM game_member_data WHERE game_id = ?", self.game_id
        )
        await start_queue(self.bot, inter.channel, "1v1")
class SpectateButton(ui.View):
    def __init__(self, bot, game_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.game_id = game_id

    async def process_button(self, button, inter):
        await inter.response.defer(ephemeral=True)

        if "Kırmızı" in button.label:
            team = "red"
        elif "Mavi" in button.label:
            team = "blue"
        else:
            return await inter.send(embed=error("Geçersiz buton."), ephemeral=True)

        data = await self.bot.fetchrow(
            "SELECT * FROM games WHERE game_id = ?",
            self.game_id
        )

        if not data:
            return await inter.send(embed=error("Bu maç sonlandı."), ephemeral=True)

        members_data = await self.bot.fetch(
            "SELECT * FROM game_member_data WHERE game_id = ?",
            self.game_id
        )
        for member in members_data:
            if member[0] == inter.author.id:
                return await inter.send(
                    embed=error("Kendi maçını izleyemezsin."),
                    ephemeral=True,
                )

        await inter.send(
            embed=success(f"Şuanda {team} takımını izliyorsun!"), ephemeral=True
        )

        lobby = self.bot.get_channel(data[1])

        if team == "red":
            voice = self.bot.get_channel(data[2])
        else:
            voice = self.bot.get_channel(data[3])

        if lobby:
            lobby_overwrites = lobby.overwrites
            lobby_overwrites.update(
                {
                    inter.author: PermissionOverwrite(send_messages=True),
                }
            )
            await lobby.edit(overwrites=lobby_overwrites)

        if voice:
            voice_overwrites = voice.overwrites
            voice_overwrites.update(
                {
                    inter.author: PermissionOverwrite(
                        send_messages=True, connect=True, speak=False
                    ),
                }
            )
            await voice.edit(overwrites=voice_overwrites)

    @ui.button(label="Kırmızı Takımı İzle", style=ButtonStyle.danger, custom_id="lol-specred")
    async def spec_red(self, button, inter):
        await self.process_button(button, inter)

    @ui.button(label="Mavi Takımı İzle", style=ButtonStyle.primary, custom_id="lol-specblue")
    async def spec_blue(self, button, inter):
        await self.process_button(button, inter)

    @ui.button(label="AFK Kontrol Et", style=ButtonStyle.secondary, custom_id="afk-check")
    async def afk_check(self, button, inter):
        await inter.response.defer(ephemeral=True)

        # Oyun verilerini al
        game_data = await self.bot.fetchrow("SELECT * FROM games WHERE game_id = ?", self.game_id)
        if not game_data:
            return await inter.send(embed=error("Oyun bulunamadı."), ephemeral=True)

        # Oyun üyelerini al
        members_data = await self.bot.fetch("SELECT * FROM game_member_data WHERE game_id = ?", self.game_id)

        # Ses kanallarını al
        red_voice = self.bot.get_channel(game_data[2])
        blue_voice = self.bot.get_channel(game_data[3])

        afk_players = []
        for member_data in members_data:
            user_id = member_data[0]
            member = inter.guild.get_member(user_id)
            if member and member.voice:
                if red_voice and blue_voice and member.voice.channel not in [red_voice, blue_voice]:
                    afk_players.append((user_id, member_data[1], member_data[2]))  # user_id, role, team
            else:
                afk_players.append((user_id, member_data[1], member_data[2]))

        if not afk_players:
            return await inter.send(embed=success("AFK oyuncu bulunamadı."), ephemeral=True)

        # Yedek oyuncuları al
        substitutes = await self.bot.fetch("SELECT user_id FROM game_substitute_data WHERE game_id = ?", self.game_id)
        if not substitutes:
            return await inter.send(embed=error("Yedek oyuncu bulunamadı."), ephemeral=True)

        # Her AFK oyuncu için yedek çağır
        for afk_user_id, role, team in afk_players:
            for sub in substitutes:
                sub_user_id = sub[0]
                sub_member = inter.guild.get_member(sub_user_id)
                if not sub_member:
                    continue

                # Yedek'e DM gönder
                try:
                    dm_embed = Embed(
                        title="Yedek Oyuncu Çağrısı",
                        description=f"Bir oyuncu AFK kaldı. {role.capitalize()} rolü için yerine geçmek ister misiniz?\nOyun ID: {self.game_id}",
                        color=Color.blue()
                    )
                    await sub_member.send(embed=dm_embed, view=SubstituteAcceptButton(self.bot, self.game_id, afk_user_id, role, team, sub_user_id, inter.guild.id))
                    await inter.send(embed=success(f"{sub_member.display_name} yedek oyuncuya çağrı gönderildi."), ephemeral=True)
                    break  # İlk yedek'e gönder, kabul ederse çık
                except Exception as e:
                    print(f"Yedek oyuncuya DM gönderilemedi {sub_user_id}: {e}")
                    continue

class SubstituteAcceptButton(ui.View):
    def __init__(self, bot, game_id, afk_user_id, role, team, sub_user_id, guild_id):
        super().__init__(timeout=300)  # 5 dakika
        self.bot = bot
        self.game_id = game_id
        self.afk_user_id = afk_user_id
        self.role = role
        self.team = team
        self.sub_user_id = sub_user_id
        self.guild_id = guild_id

    @ui.button(label="Kabul Et", style=ButtonStyle.success)
    async def accept(self, button, inter):
        await inter.response.defer()

        # AFK oyuncuyu çıkar
        await self.bot.execute("DELETE FROM game_member_data WHERE author_id = ? AND game_id = ?", self.afk_user_id, self.game_id)

        # Yedek oyuncuyu ekle
        await self.bot.execute(
            "INSERT INTO game_member_data(author_id, role, team, game_id, channel_id) VALUES(?, ?, ?, ?, ?)",
            self.sub_user_id, self.role, self.team, self.game_id, 0  # channel_id'yi uygun şekilde ayarla
        )

        # Yedek listesinden çıkar
        await self.bot.execute("DELETE FROM game_substitute_data WHERE game_id = ? AND user_id = ?", self.game_id, self.sub_user_id)

        # Rolleri güncelle
        game_data = await self.bot.fetchrow("SELECT * FROM games WHERE game_id = ?", self.game_id)
        if game_data:
            guild = self.bot.get_guild(self.guild_id)
            red_role = guild.get_role(game_data[4])
            blue_role = guild.get_role(game_data[5])
            if red_role and blue_role:
                afk_member = guild.get_member(self.afk_user_id)
                sub_member = guild.get_member(self.sub_user_id)
                if afk_member:
                    await afk_member.remove_roles(red_role, blue_role)
                if sub_member:
                    if self.team == "red":
                        await sub_member.add_roles(red_role)
                    else:
                        await sub_member.add_roles(blue_role)

        await inter.send(embed=success("Yedek oyuncu olarak kabul ettiniz. Rolünüz güncellendi."))

    @ui.button(label="Reddet", style=ButtonStyle.danger)
    async def reject(self, button, inter):
        await inter.response.defer()
        await inter.send(embed=error("Yedek oyuncu çağrısını reddettiniz."))

class RoleButtons(ui.Button):
    def __init__(self, bot, label, custom_id, disabled=False):
        super().__init__(
            label=label, style=ButtonStyle.green, custom_id=custom_id, disabled=disabled
        )
        self.bot = bot
        self.cooldown = None
    
    async def in_ongoing_game(self, inter) -> bool:
        data = await self.bot.fetch(f"SELECT * FROM games")
        for entry in data:
            user_roles = [x.id for x in inter.author.roles]
            if entry[4] in user_roles or entry[5] in user_roles:
                return True

        return False

    async def overwatch_team(self, label, view):
        team = "blue"

        def disable():
            view.disabled.append(label)
            
        if label == "tank":
            data = await self.bot.fetchrow(
                "SELECT * FROM game_member_data WHERE role = ? and game_id = ?",
                label, view.game_id
            )
            if data:
                if data[2] == "blue":
                    team = "red"
                disable()
        else:
            data = await self.bot.fetch(
                "SELECT * FROM game_member_data WHERE role = ? and game_id = ?",
                label, view.game_id
            )
            if len(data) > 2:
                if data[2] == "blue":
                    team = "red"
                if len(data)+1 == 4:
                    disable()
        
        return team

    async def add_participant(self, inter, button, view) -> None:
        preference = await self.bot.fetchrow("SELECT * FROM queue_preference WHERE guild_id = ?", inter.guild.id)
        if preference:
            preference = preference[1]
        else:
            preference = 1
        
        if preference == 2:
            in_other_games = await self.bot.fetch(
                "SELECT * FROM game_member_data WHERE author_id = ? and game_id != ?",
                inter.author.id, view.game_id
            )
            if in_other_games:
                return await inter.send(
                    embed=error(f"You cannot be a part of multiple queues."),
                    ephemeral=True,
                )

        label = button.label.lower()
        team = "blue"

        data = await self.bot.fetchrow(
            "SELECT * FROM game_member_data WHERE role = ? and game_id = ?",
            label, view.game_id
        )
        if data:
            if data[2] == "blue":
                team = "red"
            view.disabled.append(label)

        await self.bot.execute(
            "INSERT INTO game_member_data(author_id, role, team, game_id, queue_id, channel_id) VALUES($1, $2, $3, $4, $5, $6)",
            inter.author.id,
            label,
            team,
            view.game_id,
            inter.message.id,
            inter.channel.id
        )

        embed = await view.gen_embed(inter.message, view.game_id)

        await inter.message.edit(view=view, embed=embed, attachments=[])

        await inter.send(
            embed=success(f"Sıraya Başarıyla Girdiniz Rolünüz: **{label.capitalize()}**."),
            ephemeral=True,
        )

    async def disable_buttons(self, inter, view):
        for label in view.disabled:
            for btn in view.children:
                if isinstance(btn, ui.Button) and hasattr(btn, 'label'):
                    if btn.label and btn.label.lower() == label:
                        btn.disabled = True
                        btn.style = ButtonStyle.gray
        
        await inter.message.edit(view=view)

    async def callback(self, inter):
        await inter.response.defer(ephemeral=True)

        assert self.view is not None
        view: Queue = self.view

        # if not self.cooldown:
        #     self.cooldown = datetime.now() + timedelta(seconds=1.5)
        # else:
        #     if self.cooldown <= datetime.now():
        #         self.cooldown = datetime.now() + timedelta(seconds=1.5)
        #     else:
        #         await asyncio.sleep((datetime.now() - self.cooldown).seconds)

        view.check_gameid(inter)
        
        if await self.in_ongoing_game(inter):
            return await inter.send(embed=error("Zaten Şuan Bir Oyun/Sıradasın."), ephemeral=True)
        
        game_members = await self.bot.fetch(
            "SELECT * FROM game_member_data WHERE game_id = ?",
            view.game_id
        )
        for member in game_members:
            data = await self.bot.fetch(
                "SELECT * FROM game_member_data WHERE role = ? and game_id = ?",
                member[1], view.game_id
            )
            if len(data) == 2:
                if member[1] not in view.disabled:
                    view.disabled.append(member[1])
        
        if self.label.lower() in view.disabled:
            return await inter.send(embed=error("Bu Rol Seçilmiş Başka Bir Rol Seçin."), ephemeral=True)

        if await view.has_participated(inter, view.game_id):
            return await inter.send(
                embed=error("Zaten Bu Oyunun Bir Parçasısın."),
                ephemeral=True,
            )

        await self.add_participant(inter, self, view)
        await self.disable_buttons(inter, view)
        await view.check_end(inter)

class LeaveButton(ui.Button):
    def __init__(self, bot, game):
        self.bot = bot
        super().__init__(
            label="Sıradan Ayrıl", style=ButtonStyle.red, custom_id=f"{game}-queue:leave"
        )

    async def callback(self, inter):
        await inter.response.defer(ephemeral=True)
        assert self.view is not None
        view: Queue = self.view
        view.check_gameid(inter)
        if await view.has_participated(inter, view.game_id):
            await self.bot.execute(
                "DELETE FROM game_member_data WHERE author_id = ? and game_id = ?",
                inter.author.id, view.game_id
            )
            await self.bot.execute(
                "DELETE FROM duo_queue WHERE user1_id = ? AND game_id = ? OR user2_id = ? AND game_id = ?",
                inter.author.id, view.game_id, inter.author.id, view.game_id
            )

            embed = await view.gen_embed(inter.message, view.game_id)

            for button in view.children:
                if button.label in ["Sıradan Ayrıl", "Takım Değiştir", "Duo"]:
                    continue

                data = await self.bot.fetch(
                    f"SELECT * FROM game_member_data WHERE game_id = '{view.game_id}' and role = '{button.label.lower()}'"
                )
                if len(data) < 2:
                    if button.disabled:
                        view.disabled.remove(button.label.lower())
                        button.disabled = False
                        button.style = ButtonStyle.green

            await inter.message.edit(view=view, embed=embed)

            await inter.send(
                embed=success("Katılımcı listesinden çıkarıldınız."),
                ephemeral=True,
            )

        else:
            existing_sub = await self.bot.fetchrow(
                "SELECT * FROM game_substitute_data WHERE game_id = ? AND user_id = ?",
                view.game_id, inter.author.id
            )
            if existing_sub:
                await self.bot.execute(
                    "DELETE FROM game_substitute_data WHERE game_id = ? AND user_id = ?",
                    view.game_id, inter.author.id
                )

                embed = await view.gen_embed(inter.message, view.game_id)
                await inter.message.edit(view=view, embed=embed, attachments=[])

                await inter.send(
                    embed=success("Yedek oyuncu listesinden çıkarıldınız."),
                    ephemeral=True,
                )
            else:
                await inter.send(
                    embed=error("Siz bu oyunun katılımcısı değilsiniz."), ephemeral=True
                )

class YedekOyuncuButton(ui.Button):
    def __init__(self, bot, game):
        self.bot = bot
        super().__init__(
            label="Yedek Oyuncu", style=ButtonStyle.secondary, custom_id=f"{game}-queue:substitute"
        )

    async def callback(self, inter):
        await inter.response.defer(ephemeral=True)
        
        assert self.view is not None
        view: Queue = self.view
        view.check_gameid(inter)

        # Eğer zaten sıradaysa veya yedekse, çık
        if await view.has_participated(inter, view.game_id):
            return await inter.send(embed=error("Zaten sıradasınız."), ephemeral=True)
        
        existing_sub = await self.bot.fetchrow(
            "SELECT * FROM game_substitute_data WHERE game_id = ? AND user_id = ?",
            view.game_id, inter.author.id
        )
        if existing_sub:
            return await inter.send(embed=error("Zaten yedek oyuncusunuz."), ephemeral=True)

        await self.bot.execute(
            "INSERT INTO game_substitute_data(game_id, user_id) VALUES(?, ?)",
            view.game_id, inter.author.id
        )

        embed = await view.gen_embed(inter.message, view.game_id)
        await inter.message.edit(view=view, embed=embed, attachments=[])

        await inter.send(
            embed=success("Yedek oyuncu olarak kaydedildiniz. Eğer bir oyuncu AFK olursa, otomatik olarak yerine geçeceksiniz."),
            ephemeral=True,
        )

class SwitchteamButton(ui.Button):
    def __init__(self, bot, game):
        self.bot = bot
        super().__init__(
            label="Takım Değiştir", style=ButtonStyle.blurple, custom_id=f"{game}-queue:switch"
        )
    
    async def callback(self, inter):
        await inter.response.defer(ephemeral=True)
        
        assert self.view is not None
        view: Queue = self.view
        view.check_gameid(inter)

        data = await self.bot.fetchrow(
            f"SELECT * FROM game_member_data WHERE author_id = {inter.author.id} and game_id = '{view.game_id}'"
        )
        if data:
            check = await self.bot.fetchrow(
                f"SELECT * FROM game_member_data WHERE role = '{data[1]}' and game_id = '{view.game_id}' and author_id != {inter.author.id}"
            )
            if check:
                return await inter.send(
                    "The other team position for this role is already occupied.",
                    ephemeral=True,
                )

            if data[2] == "blue":
                team = "red"
            else:
                team = "blue"

            await self.bot.execute(
                f"UPDATE game_member_data SET team = '{team}' WHERE game_id = $1 and author_id = $2",
                view.game_id,
                inter.author.id,
            )
            await inter.edit_original_message(embed=await view.gen_embed(inter.message, view.game_id))
            await inter.send(f"Şu Takıma Atandınz: **{team.capitalize()}**.", ephemeral=True)

        else:
            await inter.send(
                embed=error("Siz bu oyunun bir parçası değilsiniz.."), ephemeral=True
            )

class DuoButton(ui.Button):
    def __init__(self, bot, game):
        self.bot = bot
        super().__init__(
            label="Duo", style=ButtonStyle.blurple, custom_id=f"{game}-queue:duo"
        )
 
    async def callback(self, inter):
        await inter.response.defer(ephemeral=True)
        duo_pref = await self.bot.fetchrow(f"SELECT * FROM duo_queue_preference WHERE guild_id = {inter.guild.id}")
        if not duo_pref:
            return await inter.send(embed=error("Duo queue is not enabled. Please ask an admin to run `/admin duo_queue Enabled`"), ephemeral=True)
    
        assert self.view is not None
        view = self.view
        if isinstance(view, Queue):
            view.check_gameid(inter)

        queue_check = await self.bot.fetchrow(
            f"SELECT * FROM game_member_data WHERE author_id = {inter.author.id} and game_id = '{view.game_id}'"
        )
        if not queue_check:
            return await inter.send(embed=error("Sırada Değilsiniz"), ephemeral=True)
        
        # Kullanıcının zaten bir takımda olup olmadığını kontrol et
        existing_duo = await self.bot.fetchrow(
            f"SELECT * FROM duo_queue WHERE game_id = '{view.game_id}' AND (user1_id = {inter.author.id} OR user2_id = {inter.author.id} OR user3_id = {inter.author.id} OR user4_id = {inter.author.id} OR user5_id = {inter.author.id})"
        )
        if existing_duo:
            return await inter.send(embed=error("Zaten bir takımdasınız."), ephemeral=True)
        
        queue_members = await self.bot.fetch(
            f"SELECT * FROM game_member_data WHERE game_id = '{view.game_id}'"
        )
        
        options = []
        for member_data in queue_members:
            member = inter.guild.get_member(member_data[0])
            if member.id == inter.author.id:
                continue
            if member_data[1] == queue_check[1]:
                continue
            
            # Bu oyuncu zaten bir takımda mı kontrol et
            member_in_duo = await self.bot.fetchrow(
                f"SELECT * FROM duo_queue WHERE game_id = '{view.game_id}' AND (user1_id = {member.id} OR user2_id = {member.id} OR user3_id = {member.id} OR user4_id = {member.id} OR user5_id = {member.id})"
            )
            if member_in_duo:
                continue
            
            options.append(SelectOption(label=member.display_name, value=member.id))

        if not options:
            return await inter.send(
                embed=error("Şuanda takım olmaya uygun oyuncu bulunamadı."),
                ephemeral=True
            )
        available_options_count = len(options)
        max_selectable = min(available_options_count, 4)
        async def Function(select_inter, vals, *args):
            # Seçilen oyuncuları al (max 4 kişi daha seçilebilir, toplam 5 kişilik takım)
            selected_members = [int(v) for v in vals]
            
            # Onay işlemi için ilk oyuncudan başla
            all_confirmed = True
            confirmed_members = [inter.author.id]
            
            for member_id in selected_members:
                con_view = ConfirmationButtons(member_id)
                m = inter.guild.get_member(member_id)
                
                try:
                    await m.send(
                        embed=Embed(
                            title="👥 Takım İsteği",
                            description=f"**{inter.author.display_name}** sizi takımına davet etti ({len(confirmed_members)}/{len(selected_members)+1} kişi). Kabul ediyor musunuz?",
                            color=Color.red()
                        ),
                        view=con_view
                    )
                except Exception as e:
                    print(f"Takım DM gönderme hatası: {e}")
                    await inter.send(embed=error(f"{m.display_name} kişisine takım daveti gönderilemedi."), ephemeral=True)
                    all_confirmed = False
                    break
                
                await con_view.wait()
                if con_view.value:
                    confirmed_members.append(member_id)
                else:
                    all_confirmed = False
                    await inter.send(embed=error(f"{m.display_name} takım davetini reddetti."), ephemeral=True)
                    break
            
            if all_confirmed and len(confirmed_members) >= 2:
                # Takımı veritabanına ekle (max 5 kişi)
                if len(confirmed_members) == 2:
                    await self.bot.execute(
                        f"INSERT INTO duo_queue(guild_id, user1_id, user2_id, game_id) VALUES($1, $2, $3, $4)",
                        inter.guild.id, confirmed_members[0], confirmed_members[1], args[0]
                    )
                elif len(confirmed_members) == 3:
                    await self.bot.execute(
                        f"INSERT INTO duo_queue(guild_id, user1_id, user2_id, user3_id, game_id) VALUES($1, $2, $3, $4, $5)",
                        inter.guild.id, confirmed_members[0], confirmed_members[1], confirmed_members[2], args[0]
                    )
                elif len(confirmed_members) == 4:
                    await self.bot.execute(
                        f"INSERT INTO duo_queue(guild_id, user1_id, user2_id, user3_id, user4_id, game_id) VALUES($1, $2, $3, $4, $5, $6)",
                        inter.guild.id, confirmed_members[0], confirmed_members[1], confirmed_members[2], confirmed_members[3], args[0]
                    )
                elif len(confirmed_members) == 5:
                    await self.bot.execute(
                        f"INSERT INTO duo_queue(guild_id, user1_id, user2_id, user3_id, user4_id, user5_id, game_id) VALUES($1, $2, $3, $4, $5, $6, $7)",
                        inter.guild.id, confirmed_members[0], confirmed_members[1], confirmed_members[2], confirmed_members[3], confirmed_members[4], args[0]
                    )
                
                if isinstance(view, Queue):
                    embed = await view.gen_embed(inter.message, args[0])
                else:
                    ready_ups = await self.bot.fetch(
                        f"SELECT * FROM ready_ups WHERE game_id = '{view.game_id}'"
                    )
                    ready_ups = [x[1] for x in ready_ups]
                    st_pref = await self.bot.fetchrow(f"SELECT * FROM switch_team_preference WHERE guild_id = {inter.guild.id}")
                    if st_pref:
                        embed = await ReadyButton(self.bot, view.game, view.game_id, inter.message).team_embed(ready_ups)
                    else:
                        embed = await ReadyButton(self.bot, view.game, view.game_id, inter.message).anonymous_team_embed(ready_ups)
                await inter.message.edit(embed=embed, attachments=[]) 
                
                # Tüm takım üyelerine bildirim gönder
                for member_id in confirmed_members:
                    m = inter.guild.get_member(member_id)
                    if m:
                        await m.send(embed=success(f"Başarıyla {len(confirmed_members)} kişilik takım oluşturuldu!"))

        await inter.send(content="Takımınıza eklemek istediğiniz oyuncuları seçin.", view=SelectMenuDeploy(self.bot, inter.author.id, options, 1, max_selectable, Function, view.game_id), ephemeral=True)

class ReadyButton(ui.Button):
    def __init__(self, bot, game, game_id, msg = None):
        self.bot = bot
        self.game = game
        self.game_id = game_id
        self.time_of_execution = datetime.now()

        self.data = None
        self.msg = msg

        super().__init__(
            label="Hazır Ol!", style=ButtonStyle.green, custom_id=f"{game}-queue:readyup"
        )

        self.disable_button.start()
    
    async def anonymous_team_embed(self, ready_ups):
        embed = self.msg.embeds[0]
        embed.clear_fields()
        embed.description = "Bunlar son takımlar değil. **Takımlar rastgele dağıtılacaktır**"
        duos = await self.bot.fetch(f"SELECT * FROM duo_queue WHERE game_id = '{self.game_id}'")
        in_duo = {}
        duo_emojis_list = [":one:", ":two:", ":three:", ":four:", ":five:"]
        for i, duo in enumerate(duos):
            current_emoji = duo_emojis_list[i] if i < len(duo_emojis_list) else ":white_small_square:"
            for col_idx in range(1, 6):
                if col_idx < len(duo) and isinstance(duo[col_idx], int):
                    in_duo[duo[col_idx]] = current_emoji
        
        # Kalıcı Takım Emoji Sistemi
        team_emojis_list = ["🔷", "🔶", "🔴", "🟢", "🟡"]
        in_team = {}
        
        team_data = await self.bot.fetch(
            f"SELECT * FROM game_member_data WHERE game_id = '{self.game_id}'"
        )
        
        # Her oyuncunun takımını kontrol et
        player_teams = {}
        for player in team_data:
            team_check = await self.bot.fetchrow(
                "SELECT team_id FROM team_members WHERE user_id = ?",
                player[0]
            )
            if team_check:
                team_id = team_check[0]
                if team_id not in player_teams:
                    player_teams[team_id] = []
                player_teams[team_id].append({'user_id': player[0], 'role': player[1]})
        
        # Her takım için rol çakışması kontrolü ve emoji atama
        team_emoji_idx = 0
        for team_id, members in player_teams.items():
            # Rol çakışması kontrolü
            role_counts = {}
            for member in members:
                role = member['role']
                role_counts[role] = role_counts.get(role, 0) + 1
            
            # Geçerli kompozisyonu bul
            valid_members = []
            used_roles = set()
            
            for member in members:
                if member['role'] not in used_roles:
                    valid_members.append(member)
                    used_roles.add(member['role'])
            
            # En az 2 kişi geçerli kompozisyonda olmalı
            if len(valid_members) >= 2 and team_emoji_idx < len(team_emojis_list):
                current_team_emoji = team_emojis_list[team_emoji_idx]
                for member in valid_members:
                    in_team[member['user_id']] = current_team_emoji
                team_emoji_idx += 1
        
        value1 = ""
        value2 = ""
        for i, team in enumerate(team_data):
            value = ""
            if team[0] in ready_ups:
                value += "✅"
            else:
                value += "❌"
            
            # Önce takım emojisi, sonra duo emojisi
            if team[0] in in_team:
                value += f"{in_team[team[0]]} "
            elif team[0] in in_duo:
                value += f"{in_duo[team[0]]} "
            
            value += f"<@{team[0]}> - {self.bot.role_emojis.get(team[1].lower())} {team[1].capitalize()}\n"
            if i in range(0, 5):
                value1 += value
            else:
                value2 += value

        # Yedek oyuncuları ekle
        substitutes = await self.bot.fetch(f"SELECT user_id FROM game_substitute_data WHERE game_id = '{self.game_id}'")
        sub_names = [f"<@{sub[0]}>" for sub in substitutes] if substitutes else []
        text = "\n".join(sub_names) if sub_names else ""
        value1 += f"\n**Yedek Oyuncular:**\n{text}"

        embed.add_field(name="👥 Oyuncular", value=value1)
        embed.add_field(name="👥 Oyuncular", value=value2)

        with open('assets/tips.txt', 'r') as f:
            tips = f.readlines()
            tip = random.choice(tips) 
        embed.set_footer(text="🎮 " + self.game_id + '\n' + "💡 " + tip)

        return embed

    async def team_embed(self, ready_ups):

        embed = self.msg.embeds[0]
        embed.clear_fields()
        teams = ["blue", "red"]
        embed.description = ""

        duos = await self.bot.fetch(f"SELECT * FROM duo_queue WHERE game_id = '{self.game_id}'")
        in_duo = {}
        duo_emojis_list = [":one:", ":two:", ":three:", ":four:", ":five:"]
        for i, duo in enumerate(duos):
            current_emoji = duo_emojis_list[i] if i < len(duo_emojis_list) else ":white_small_square:"
            for col_idx in range(1, 6):
                if col_idx < len(duo) and isinstance(duo[col_idx], int):
                    in_duo[duo[col_idx]] = current_emoji

        # Kalıcı Takım Emoji Sistemi
        team_emojis_list = ["🔷", "🔶", "🔴", "🟢", "🟡"]
        in_team = {}
        
        # Sıradaki tüm oyuncuları al
        all_players = await self.bot.fetch(
            f"SELECT author_id, role FROM game_member_data WHERE game_id = '{self.game_id}'"
        )
        
        # Her oyuncunun takımını kontrol et
        player_teams = {}
        for player in all_players:
            team_data = await self.bot.fetchrow(
                "SELECT team_id FROM team_members WHERE user_id = ?",
                player[0]
            )
            if team_data:
                team_id = team_data[0]
                if team_id not in player_teams:
                    player_teams[team_id] = []
                player_teams[team_id].append({'user_id': player[0], 'role': player[1]})
        
        # Her takım için rol çakışması kontrolü ve emoji atama
        team_emoji_idx = 0
        for team_id, members in player_teams.items():
            # Rol çakışması kontrolü
            role_counts = {}
            for member in members:
                role = member['role']
                role_counts[role] = role_counts.get(role, 0) + 1
            
            # Geçerli kompozisyonu bul (her rolden 1)
            valid_members = []
            used_roles = set()
            
            for member in members:
                if member['role'] not in used_roles:
                    valid_members.append(member)
                    used_roles.add(member['role'])
            
            # En az 2 kişi geçerli kompozisyonda olmalı
            if len(valid_members) >= 2 and team_emoji_idx < len(team_emojis_list):
                current_team_emoji = team_emojis_list[team_emoji_idx]
                for member in valid_members:
                    in_team[member['user_id']] = current_team_emoji
                team_emoji_idx += 1

        # Yedek oyuncuları ekle
        substitutes = await self.bot.fetch(f"SELECT user_id FROM game_substitute_data WHERE game_id = '{self.game_id}'")
        sub_names = [f"<@{sub[0]}>" for sub in substitutes] if substitutes else []
        text = "\n".join(sub_names) if sub_names else ""

        for team in teams:

            team_data = await self.bot.fetch(
                f"SELECT * FROM game_member_data WHERE game_id = '{self.game_id}' and team = '{team}'"
            )

            if team == "red":
                name = "🔴 Takım 2 (Red Side)"
            elif team == "blue":
                name = "🔵 Takım 1 (Blue Side)"
            else:
                name = f"{team.capitalize()}"

            if team_data:
            
                value = ""
                for data in team_data:
                    
                    if data[0] in ready_ups:
                        value += "✅ "
                    else:
                        value += "❌ "
                    
                    # Önce takım emojisi, sonra duo emojisi
                    if data[0] in in_team:
                        value += f"{in_team[data[0]]} "
                    elif data[0] in in_duo:
                         value += f"{in_duo[data[0]]} "

                    value += f"<@{data[0]}> - `{data[1].capitalize()}`\n"
            else:
                value = "Henüz Kimse Sırada Değil."

            if team == "blue":
                value += f"\n**Yedek Oyuncular:**\n{text}"

            embed.add_field(name=name, value=value)

        with open('assets/tips.txt', 'r') as f:
            tips = f.readlines()
            tip = random.choice(tips) 
        embed.set_footer(text="🎮 " + self.game_id + '\n' + "💡 " + tip)

        return embed

    async def lol_lobby(self, inter, lobby_channel):
        response = None
        async with websockets.connect("wss://draftlol.dawe.gg/") as websocket:
            data = {"type": "createroom", "blueName": "Scrimlab Mavi Takım", "redName": "Scrimlab Kırmızı Takım", "disabledTurns": [], "disabledChamps": [], "timePerPick": "30", "timePerBan": "30"}
            await websocket.send(json.dumps(data))
            
            try:
                async with async_timeout.timeout(10):
                    result = await websocket.recv()
                    if result:
                        data = json.loads(result)
                        response = ("🔵 https://draftlol.dawe.gg/" + data["roomId"] +"/" +data["bluePassword"], "🔴 https://draftlol.dawe.gg/" + data["roomId"] +"/" +data["redPassword"], "\n**İzleyici:** https://draftlol.dawe.gg/" + data["roomId"])
            except asyncio.TimeoutError:
                pass
        
        if response:
            await lobby_channel.send(
                embed=Embed(
                    title="League of Legends Draft (Karakterler Buradan Seçilir.) eğer 2 takımda kabul ederse zorunlu değildir.",
                    description="\n".join(response),
                    color=Color.blurple()
                )
            )
        else:
            await lobby_channel.send(
                embed=error("Draftlol çalışmıyor, bağlantılar alınamadı.")
            )

        region = await self.bot.fetchrow(f"SELECT region FROM queuechannels WHERE channel_id = {inter.channel.id}")
        if not region[0]:
            region = "na"
        else:
            region = region[0]
        teams = {
            'blue': '',
            'red': ''
        }

        for team in teams:
            url = f'https://www.op.gg/multisearch/{region}?summoners='
            data = await self.bot.fetch(
                f"SELECT * FROM game_member_data WHERE game_id = '{self.game_id}' and team = '{team}'"
            )

            nicknames = []

            for entry in data:
                ign = await self.bot.fetchrow(
                    f"SELECT ign FROM igns WHERE guild_id = {inter.guild.id} and user_id = {entry[0]} and game = 'lol'"
                )

                if ign:
                    # ❗ TAM BURADA encode ediyoruz
                    nicknames.append(quote(ign[0], safe=''))
                else:
                    member = lobby_channel.guild.get_member(entry[0])

                    if member.nick:
                        nick = member.nick
                    else:
                        nick = member.name

                    pattern = re.compile("ign ", re.IGNORECASE)
                    nick = pattern.sub("", nick)

                    pattern2 = re.compile("ign: ", re.IGNORECASE)
                    nick = pattern2.sub("", nick)

                    # yine encode
                    nicknames.append(quote(str(nick), safe=''))

            # virgulü biz koyuyoruz, encode ETMİYORUZ
            url += ",".join(nicknames)

            teams[team] = url
        
        await lobby_channel.send(
            embed=Embed(
                title="🔗 Multi OP.GG",
                description=f"🔵{teams['blue']}\n🔴{teams['red']} \n \n :warning: eğer op.ggler eksik ise adminlere bildirin.",
                color=Color.blurple()
            )
        )
        


    async def check_members(self, msg):
        members = await self.bot.fetch(
            f"SELECT * FROM game_member_data WHERE game_id = '{self.game_id}'"
        )
        if await self.bot.check_testmode(msg.guild.id):
            required_members = 2
        else:
            required_members = 10

        if len(members) != required_members:
            self.disable_button.stop()
            await start_queue(self.bot, msg.channel, self.game, None, msg, self.game_id)

    @tasks.loop(seconds=1)
    async def disable_button(self):
        await self.bot.wait_until_ready()
        
        if self.msg:
            await self.check_members(self.msg)
            # Update the stored message and stop timer if ready up phase was removed
            msg = self.bot.get_message(self.msg.id)
            if not msg:
                msg = await self.msg.channel.fetch_message(self.msg.id)
                if msg:
                    self.msg = msg
            else:
                self.msg = msg

            if not self.msg.components[0].children[0].label == "Ready Up!":
                self.disable_button.stop()
                return

        if (datetime.now() - self.time_of_execution).seconds >= 300:
            if self.msg:
                ready_ups = await self.bot.fetch(
                    f"SELECT user_id FROM ready_ups WHERE game_id = '{self.game_id}'"
                )

                ready_ups = [x[0] for x in ready_ups]
                game_members = [member[0] for member in self.data]
                players_removed = []

                for user_id in game_members:
                    if user_id not in ready_ups:
                        await self.bot.execute(
                            f"DELETE FROM game_member_data WHERE author_id = {user_id} and game_id = '{self.game_id}'"
                        )
                        players_removed.append(user_id)
                        await self.bot.execute(
                            f"DELETE FROM duo_queue WHERE game_id = '{self.game_id}' and user1_id = {user_id} OR game_id = '{self.game_id}' and user2_id = {user_id}"
                        )

                        user = self.bot.get_user(user_id)
                        await user.send(
                            embed=Embed(
                                description=f"You were removed from the [queue]({self.msg.jump_url}) for not being ready on time.",
                                color=Color.red(),
                            )
                        )

                await self.bot.execute(
                    f"DELETE FROM ready_ups WHERE game_id = '{self.game_id}'"
                )
                st_pref = await self.bot.fetchrow(f"SELECT * FROM switch_team_preference WHERE guild_id = {self.msg.guild.id}")
                if not st_pref:
                    sbmm = True
                else:
                    sbmm = False
                duo_pref = await self.bot.fetchrow(f"SELECT * FROM duo_queue_preference WHERE guild_id = {self.msg.guild.id}")
                if duo_pref:
                    duo = True
                else:
                    duo = False
                test_mode = await self.bot.check_testmode(self.msg.guild.id)
                await self.msg.edit(
                    embed=await Queue.gen_embed(self, self.msg, self.game_id, test_mode),
                    view=Queue(self.bot, sbmm, duo, self.game),
                    content="Not all players were ready, Queue has been vacated.",
                )
                await self.msg.channel.send(
                    content=", ".join(f"<@{x}>" for x in players_removed),
                    embed=Embed(
                        description="Bahsedilen oyuncular maçı kabul etmemesi sebebiyle sıradan çıkarıldı.",
                        color=Color.blurple(),
                    ),
                    delete_after=60.0,
                )

                self.disable_button.stop()

            else:
                self.time_of_execution = datetime.now()

    async def callback(self, inter):
        if not inter.response.is_done():
            await inter.response.defer()

        if not self.msg:
            self.msg = inter.message

        if not self.data:
            self.data = await self.bot.fetch(
                f"SELECT * FROM game_member_data WHERE game_id = '{self.game_id}'"
            )
        
        await self.check_members(inter.message)

        game_members = [member[0] for member in self.data]
        ready_ups = await self.bot.fetch(
            f"SELECT * FROM ready_ups WHERE game_id = '{self.game_id}'"
        )
        ready_ups = [x[1] for x in ready_ups]

        if inter.author.id in game_members:
            if inter.author.id in ready_ups:
                await inter.send(
                    embed=success("Zaten Hazır Butonuna Tıklamışsın."), ephemeral=True
                )
                return

            await self.bot.execute(
                "INSERT INTO ready_ups(game_id, user_id) VALUES($1, $2)",
                self.game_id,
                inter.author.id,
            )
            ready_ups.append(inter.author.id)

            st_pref = await self.bot.fetchrow(f"SELECT * FROM switch_team_preference WHERE guild_id = {inter.guild.id}")
            if st_pref:
                embed = await self.team_embed(ready_ups)
            else:
                embed = await self.anonymous_team_embed(ready_ups)
            sub_count = len(await self.bot.fetch(f"SELECT * FROM game_substitute_data WHERE game_id = '{self.game_id}'"))
            await inter.message.edit(
                f"{len(ready_ups)}/10 Kişi Hazır! ({sub_count} Yedek Oyuncu)\nŞu Saatten Önce Hazır Olmanız Gerekmektedir: <t:{int(datetime.timestamp((self.time_of_execution + timedelta(seconds=290))))}:t>",
                embed=embed,
            )

            if await self.bot.check_testmode(inter.guild.id):
                required_readyups = 2
            else:
                required_readyups = 10
            if len(ready_ups) == required_readyups:
                
                if not st_pref:
                    member_data = await self.bot.fetch(
                        f"SELECT * FROM game_member_data WHERE game_id = '{self.game_id}'"
                    )

                    if self.game == 'lol':
                        labels = LOL_LABELS
                    
                    if await self.bot.check_testmode(inter.guild.id):
                        roles_occupation = {
                            labels[0].upper(): [{'user_id': 890, 'rating': Rating()}, {'user_id': 3543, 'rating': Rating()}],
                            labels[1].upper(): [{'user_id': 709, 'rating': Rating()}, {'user_id': 901, 'rating': Rating()},],
                            labels[2].upper(): [{'user_id': 789, 'rating': Rating()}, {'user_id': 981, 'rating': Rating()}, ],
                            labels[3].upper(): [{'user_id': 234, 'rating': Rating()}, {'user_id': 567, 'rating': Rating()}, ],
                            labels[4].upper(): []
                        }
                    else:
                        roles_occupation = {
                        labels[0].upper(): [],
                        labels[1].upper(): [],
                        labels[2].upper(): [],
                        labels[3].upper(): [],
                        labels[4].upper(): []
                        }

                    for data in member_data:
                        member_rating = await self.bot.fetchrow(f"SELECT * FROM mmr_rating WHERE user_id = {data[0]} and guild_id = {inter.guild.id} and game = '{self.game}'")
                        if member_rating:
                            mu = float(member_rating[2])
                            sigma = float(member_rating[3])
                            rating = Rating(mu, sigma)

                        else:
                            rating = Rating()
                            await self.bot.execute(
                                f"INSERT INTO mmr_rating(guild_id, user_id, mu, sigma, counter, game) VALUES($1, $2, $3, $4, $5, $6)",
                                inter.guild.id,
                                data[0],
                                rating.mu,
                                rating.sigma,
                                0,
                                self.game
                            )

                        roles_occupation[data[1].upper()].append({'user_id': data[0], 'rating': rating})

                    all_occupations = [*roles_occupation.values()]

                    unique_combinations = list(itertools.product(*all_occupations))
                    team_data = []
                    qualities = []
                    for pair in unique_combinations:
                        players_in_pair = [x['user_id'] for x in list(pair)]
                        t2 = []
                        for x in roles_occupation:
                            for val in roles_occupation[x]:
                                if val['user_id'] not in players_in_pair:
                                    t2.append(val)
                        duo = await self.bot.fetch(
                            f"SELECT * FROM duo_queue WHERE game_id = '{self.game_id}'"
                        )
                        check = True
                        for duo_data in duo:
                            user1 = duo_data[1]
                            user2 = duo_data[2]
                            
                            if not ( ( user1 in players_in_pair and user2 in players_in_pair ) or ( user1 in [x['user_id'] for x in t2] and user2 in [x['user_id'] for x in t2] ) ):
                                check = False
                        if not check:
                            # Skip the pair
                            continue

                        qua = quality([[x['rating'] for x in list(pair)], [x['rating'] for x in t2]])
                        qualities.append(qua)
                        team_data.append({'quality': qua, 'teams': [list(pair), t2]})

                    closet_quality = qualities[min(range(len(qualities)), key=lambda i: abs(qualities[i] - 50))]
                    for entry in team_data:
                        if entry['quality'] == closet_quality:
                            final_teams = entry['teams']
                    
                    for i, team_entries in enumerate(final_teams):
                        if i:
                            team = 'blue'
                        else:
                            team = 'red'
                        for entry in team_entries:
                            await self.bot.execute("UPDATE game_member_data SET team = $1 WHERE author_id = $2", team, entry['user_id'])
                    self.data = await self.bot.fetch(
                        f"SELECT * FROM game_member_data WHERE game_id = '{self.game_id}'"
                    )
                else:
                    pass
                            
                preference = await self.bot.fetchrow(f"SELECT * FROM queue_preference WHERE guild_id = {inter.guild.id}")
                if preference:
                    preference = preference[1]
                else:
                    preference = 1

                if preference == 1:
                    for member in game_members:
                        # Remove member from all other queues
                        await self.bot.execute(
                            f"DELETE FROM game_member_data WHERE author_id = {member} and game_id != '{self.game_id}'"
                        )

                await self.bot.execute(
                    f"DELETE FROM ready_ups WHERE game_id = '{self.game_id}'"
                )

                try:
                    # Creating roles
                    red_role = await inter.guild.create_role(
                        name=f"Kırmızı Takım: {self.game_id}"
                    )
                    blue_role = await inter.guild.create_role(
                        name=f"Mavi Takım: {self.game_id}"
                    )

                    overwrites_red = {
                        inter.guild.default_role: PermissionOverwrite(connect=False),
                        red_role: PermissionOverwrite(connect=True),
                        self.bot.user: PermissionOverwrite(
                            send_messages=True, manage_channels=True, connect=True
                        ),
                    }
                    overwrites_blue = {
                        inter.guild.default_role: PermissionOverwrite(connect=False),
                        blue_role: PermissionOverwrite(connect=True),
                        self.bot.user: PermissionOverwrite(
                            send_messages=True, manage_channels=True, connect=True
                        ),
                    }
                    mutual_overwrites = {
                        inter.guild.default_role: PermissionOverwrite(
                            send_messages=False
                        ),
                        red_role: PermissionOverwrite(send_messages=True),
                        blue_role: PermissionOverwrite(send_messages=True),
                        self.bot.user: PermissionOverwrite(
                            send_messages=True, manage_channels=True
                        ),
                    }

                    # Creating channels
                    game_category_id = await self.bot.fetchrow(f"SELECT * FROM game_categories WHERE guild_id = {inter.guild.id} and game = '{self.game}'")
                    if game_category_id:
                        game_category = self.bot.get_channel(game_category_id[1])
                    else:
                        game_category = await inter.guild.create_category(
                            name=f"Maç: {self.game_id}", overwrites=mutual_overwrites
                        )
                    game_lobby = await game_category.create_text_channel(
                        f"Lobby: {self.game_id}", overwrites=mutual_overwrites
                    )

                    voice_channel_red = await game_category.create_voice_channel(
                        f"Kırmızı Takım: {self.game_id}", overwrites=overwrites_red
                    )
                    voice_channel_blue = await game_category.create_voice_channel(
                        f"Mavi Takım: {self.game_id}", overwrites=overwrites_blue
                    )

                except:
                    # If this ever fails due to limitations of discord or lack of permissions
                    await inter.send(
                        embed=error(
                            "Could not create channels/roles. Please contact the administrators."
                        )
                    )
                    print(traceback.format_exc())
                    return

                await inter.message.edit(
                    content="Oyun Şuanda Oynanıyor",
                    view=SpectateButton(self.bot, self.game_id),
                )

                for entry in self.data:
                    if entry[2] == "red":
                        member = inter.guild.get_member(entry[0])
                        await member.add_roles(red_role)

                    elif entry[2] == "blue":
                        member = inter.guild.get_member(entry[0])
                        await member.add_roles(blue_role)

                await game_lobby.send(
                    content=f"{red_role.mention} {blue_role.mention}",
                    embed=await self.team_embed(ready_ups),
                    view=SpectateButton(self.bot, self.game_id)
                )
                await game_lobby.send(
                    embed=Embed(
                        title=":warning: Uyarı",
                        description=f"Kazananı onaylamak için, `!win` veya `/win` yazınız.\n "
                                    f"**6** oy ve fazlası geçerlidir.\n"
                                    f"Sadece Lobidekilerin Oyu Geçerlidir.\n \n"
                                    f"Eğer Kazanan Yanlış İşaretlenirse <#1453371166147477575> kanalı üzerinden İletişime geçin.",
                        color=Color.yellow(),
                    )
                  )
                await self.bot.execute(
                    f"INSERT INTO games(game_id, lobby_id, voice_red_id, voice_blue_id, red_role_id, blue_role_id, queuechannel_id, msg_id, game) VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                    self.game_id,
                    game_lobby.id,
                    voice_channel_red.id,
                    voice_channel_blue.id,
                    red_role.id,
                    blue_role.id,
                    inter.channel.id,
                    inter.message.id,
                    self.game
                )

                if self.game == 'lol':
                    await self.lol_lobby(inter, game_lobby)

                self.disable_button.cancel()
                await start_queue(self.bot, inter.channel, self.game)

        else:
            await inter.send(
                embed=error("Bu oyunun bir parçası değilsin."), ephemeral=True
            )

class ReadyUp(ui.View):
    def __init__(self, bot, game, game_id, duo):
        super().__init__(timeout=None)
        self.bot = bot
        self.game_id = game_id
        self.game = game
        self.add_item(ReadyButton(bot, game, game_id))
        if duo:
            self.add_item(DuoButton(bot, game))


class Queue(ui.View):
    def __init__(self, bot, sbmm, duo, game, testmode):
        super().__init__(timeout=None)
        self.bot = bot
        self.disabled = []
        self.game_id = None
        self.game = game
        self.msg = None
        if game == 'lol':
            labels = LOL_LABELS

        for i, label in enumerate(labels):
            if i != len(labels)-1:
                self.add_item(RoleButtons(bot, label, f"{game}-queue:{label.lower()}", testmode))
            else:
                self.add_item(RoleButtons(bot, label, f"{game}-queue:{label.lower()}", False))
        
        self.add_item(LeaveButton(bot, game))
        self.add_item(YedekOyuncuButton(bot, game))
        if not sbmm:
            self.add_item(SwitchteamButton(bot, game))
        if duo and sbmm:
            self.add_item(DuoButton(bot, game))
            self.duo = True
        else:
            self.duo = False
    
    def check_gameid(self, inter):
        if not self.game_id:
            self.game_id = inter.message.embeds[0].footer.text.split('\n')[0].replace(' ', '').replace("🎮", "")

    async def has_participated(self, inter, game_id) -> bool:
        data = await self.bot.fetchrow(
            f"SELECT * FROM game_member_data WHERE author_id = {inter.author.id} and game_id = '{game_id}'"
        )
        if data:
            return True
        return False
    
    async def gen_embed(self, msg, game_id) -> Embed:
        embed = msg.embeds[0]
        embed.clear_fields()
        
        # Tüm katılımcıları al
        all_participants = await self.bot.fetch(
            f"SELECT * FROM game_member_data WHERE game_id = '{game_id}'"
        )
        player_count = len(all_participants)
        
        # Progress bar ve dinamik renk
        max_players = 10
        progress_filled = min(player_count, max_players)
        progress = "█" * progress_filled + "░" * (max_players - progress_filled)
        
        if player_count == 0:
            embed_color = Color.from_rgb(88, 101, 242)
            status_emoji = "⏳"
            status_text = "Oyuncu Bekleniyor"
        elif player_count < 5:
            embed_color = Color.from_rgb(255, 170, 0)
            status_emoji = "🟡"
            status_text = f"{player_count}/10 Oyuncu"
        elif player_count < 10:
            embed_color = Color.from_rgb(87, 242, 135)
            status_emoji = "🟢"
            status_text = f"{player_count}/10 Oyuncu"
        else:
            embed_color = Color.from_rgb(255, 85, 85)
            status_emoji = "🔥"
            status_text = "HAZIR!"
        
        embed.color = embed_color
        
        # Rol emojileri ve sıralaması
        role_info = {
            "top": {"emoji": "<:Top:1454081617382477908>", "display": "Top", "icon": "🗡️"},
            "jungle": {"emoji": "<:Jungle:1454081696327667836>", "display": "Jungle", "icon": "🌲"},
            "mid": {"emoji": "<:Mid:1454081643374448836>", "display": "Mid", "icon": "⚡"},
            "adc": {"emoji": "<:ADC:1454081581445812244>", "display": "ADC", "icon": "🏹"},
            "support": {"emoji": "<:Support:1454081735087231048>", "display": "Support", "icon": "🛡️"}
        }
        role_order = ["top", "jungle", "mid", "adc", "support"]
        
        # Duo kontrolü
        duos = await self.bot.fetch(f"SELECT * FROM duo_queue WHERE game_id = '{game_id}'")
        in_duo = {}
        duo_markers = ["①", "②", "③", "④", "⑤"]
        for i, duo in enumerate(duos):
            marker = duo_markers[i] if i < len(duo_markers) else ""
            for col_idx in range(1, 6):
                if col_idx < len(duo) and isinstance(duo[col_idx], int):
                    in_duo[duo[col_idx]] = marker
        
        # Takım kontrolü (kalıcı takımlar için)
        team_markers = ["🔷", "🔶", "🟣", "🟢", "🟡"]
        in_team = {}
        player_teams = {}
        for player in all_participants:
            team_check = await self.bot.fetchrow(
                "SELECT team_id FROM team_members WHERE user_id = ?",
                player[0]
            )
            if team_check:
                team_id = team_check[0]
                if team_id not in player_teams:
                    player_teams[team_id] = []
                player_teams[team_id].append({'user_id': player[0], 'role': player[1]})
        
        team_idx = 0
        for team_id, members in player_teams.items():
            valid_members = []
            used_roles = set()
            for member in members:
                if member['role'] not in used_roles:
                    valid_members.append(member)
                    used_roles.add(member['role'])
            
            if len(valid_members) >= 2 and team_idx < len(team_markers):
                marker = team_markers[team_idx]
                for member in valid_members:
                    in_team[member['user_id']] = marker
                team_idx += 1
        
        # Oyuncuları role göre grupla
        role_players = {role: [] for role in role_order}
        for player in all_participants:
            role = player[1].lower()
            if role in role_players:
                role_players[role].append(player[0])
        
        # Oyuncu listesi oluştur
        player_lines = []
        
        for role in role_order:
            info = role_info.get(role, {"emoji": "❓", "display": role.capitalize(), "icon": "❓"})
            players_in_role = role_players[role]
            
            if players_in_role:
                for uid in players_in_role:
                    duo_mark = in_duo.get(uid, "")
                    team_mark = in_team.get(uid, "")
                    marker = f" {team_mark}" if team_mark else (f" {duo_mark}" if duo_mark else "")
                    player_lines.append(f"{info['emoji']} **{info['display']}** ┃ <@{uid}>{marker}")
            else:
                player_lines.append(f"{info['icon']} **{info['display']}** ┃ `Boş slot`")
        
        # Listeyi oluştur
        if player_count > 0:
            player_text = "\n".join(player_lines)
        else:
            player_text = "```\n⏳ Henüz kimse sırada değil...\n   Rol seçerek ilk sen katıl!\n```"
        
        # Ana oyuncu listesi
        embed.add_field(
            name=f"👥 Oyuncu Listesi ({player_count}/10)",
            value=player_text,
            inline=False
        )
        
        # Yedek oyuncular
        substitutes = await self.bot.fetch(f"SELECT user_id FROM game_substitute_data WHERE game_id = '{game_id}'")
        if substitutes:
            sub_names = [f"<@{sub[0]}>" for sub in substitutes]
            sub_text = " • ".join(sub_names)
            embed.add_field(
                name="🔄 Yedek Oyuncular",
                value=sub_text,
                inline=False
            )
        
        # Açıklama güncelle
        embed.description = (
            f"```ansi\n\u001b[1;33m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\u001b[0m\n```\n"
            f"**{status_emoji} Durum:** {status_text}\n"
            f"**📊 İlerleme:** {progress}\n\n"
            f"*Takımlar maç başladığında rastgele belirlenecek!*"
        )
        
        # Footer
        with open('assets/tips.txt', 'r') as f:
            tips = f.readlines()
            tip = random.choice(tips).strip() if tips else "İyi oyunlar!"
        
        embed.set_footer(
            text=f"🎮 {game_id} • 💡 {tip}",
            icon_url="https://cdn.discordapp.com/emojis/1078086241221877941.png"
        )
        embed.timestamp = datetime.now()

        return embed

    async def check_end(self, inter) -> None:
        checks_passed = 0
        
        if await self.bot.check_testmode(inter.guild.id):
            required_checks = 1
        else:
            required_checks = 5
        
        for button in self.children:
            if not isinstance(button, RoleButtons):
                continue
            
            if button.label in ["Sıradan Ayrıl", "Takım Değiştir", "Duo", "Yedek Oyuncu"]:
                continue

            data = await self.bot.fetch(
                f"SELECT * FROM game_member_data WHERE game_id = '{self.game_id}' and role = '{button.label.lower()}'"
            )
            
            if len(data) >= 2:
                checks_passed += 1

        if await self.bot.check_testmode(inter.guild.id):
            required_checks = 1
        else:
            required_checks = 5
        if checks_passed == required_checks:
            member_data = await self.bot.fetch(
                f"SELECT * FROM game_member_data WHERE game_id = '{self.game_id}'"
            )

            mentions = (
                ", ".join(f"<@{data[0]}>" for data in member_data)
            )

            self.msg = inter.message
            st_pref = await self.bot.fetchrow(f"SELECT * FROM switch_team_preference WHERE guild_id = {inter.guild.id}")
            if st_pref:
                embed = await ReadyButton.team_embed(self, [])
            else:
                embed = await ReadyButton.anonymous_team_embed(self, [])
            
            # self.ready_up = True
            await inter.edit_original_message(
                view=None
            )
            sub_count = len(await self.bot.fetch(f"SELECT * FROM game_substitute_data WHERE game_id = '{self.game_id}'"))
            await inter.edit_original_message(
                view=ReadyUp(self.bot, self.game, self.game_id, self.duo),
                content=f"0/10 Oyuncu Hazır! ({sub_count} Yedek Oyuncu)",
                embed=embed
            )

            embed = Embed(
                description=f"Oyun Bulundu Hazır Ol!", color=Color.blurple()
            )

            await inter.message.reply(mentions, embed=embed, delete_after=300.0)
            # --- DM GÖNDERME KISMI (GÜNCELLENDİ) ---
            import disnake # Disnake kullandığın için garantiye alalım

            dm_embed = disnake.Embed(
                title="**Maç Bulundu!**",
                description=f"**{inter.guild.name}** sunucusundaki maçın hazır. <#1454458642622451824> kanalından hazır verebilirsin 5 dakika süren var iyi eğlenceler...",
                color=disnake.Color.green()
            )
            
            for data in member_data:
                try:
                    user_id = int(data[0]) 
                    user = await self.bot.fetch_user(user_id)
                    if user:
                        # disnake'de doğrudan embed=dm_embed şeklinde gönderilir
                        await user.send(embed=dm_embed)
                except Exception as e:
                    print(f"DM Hatası ({data[0]}): {e}")
            # -------------------------

            # Kanala atılacak son mesajdaki embed hatasını da düzeltelim
            reply_embed = disnake.Embed(
                description="Oyun Bulundu Hazır Ol!", 
                color=disnake.Color.blurple()
            )

            # Mentions kısmından sonra embed'i bu şekilde gönderiyoruz
            await inter.message.reply(content=mentions, embed=reply_embed, delete_after=300.0)
