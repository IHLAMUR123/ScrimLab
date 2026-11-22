from disnake.ext.commands import Cog, slash_command
from disnake import (
    Embed, Color, ButtonStyle, TextInputStyle,
    ui, Member, utils
)
from core import config
from core.embeds import error, success
import disnake

class KayitModal(ui.Modal):
    def __init__(self):
        components = [
            ui.TextInput(
                label="Oyun İçi Kullanıcı Adın ve Etiketin",
                placeholder="Örnek: Faker#TR1",
                custom_id="nick_input",
                style=TextInputStyle.short,
                min_length=3,
                max_length=50,
                required=True
            )
        ]
        super().__init__(
            title="🎮 Kayıt Ol - 1. Adım",
            custom_id="kayit_modal",
            components=components,
            timeout=300
        )

    async def callback(self, inter: disnake.ModalInteraction):
        nick = inter.text_values["nick_input"]
        
        # Kayıt kontrolü
        bot = inter.bot
        data = await bot.fetchrow(
            "SELECT * FROM igns WHERE user_id = ? and guild_id = ?",
            inter.author.id, inter.guild.id
        )
        
        if data:
            return await inter.response.send_message(
                embed=error("Zaten bir kaydın var, yöneticilerle iletişime geçin."),
                ephemeral=True
            )
        
        # Geçici olarak nick'i sakla ve rol seçim menüsünü göster
        view = RolSecimView(nick, bot)
        
        embed = Embed(
            title="🎮 Kayıt Ol - 2. Adım: Rol Seçimi",
            description=f"**Oyun İçi Nick:** `{nick}`\n\nAna rolünü seç:",
            color=Color.blue()
        )
        
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)


class RolSecimView(ui.View):
    def __init__(self, nick: str, bot):
        super().__init__(timeout=180)
        self.nick = nick
        self.bot = bot
        self.selected_rol = None

    @ui.button(label="Top", style=ButtonStyle.blurple, emoji="⚔️")
    async def top_btn(self, button: ui.Button, inter: disnake.MessageInteraction):
        await self.handle_rol_selection(inter, "Top")

    @ui.button(label="Jungle", style=ButtonStyle.blurple, emoji="🌳")
    async def jungle_btn(self, button: ui.Button, inter: disnake.MessageInteraction):
        await self.handle_rol_selection(inter, "Jungle")

    @ui.button(label="Mid", style=ButtonStyle.blurple, emoji="⚡")
    async def mid_btn(self, button: ui.Button, inter: disnake.MessageInteraction):
        await self.handle_rol_selection(inter, "Mid")

    @ui.button(label="ADC", style=ButtonStyle.blurple, emoji="🎯")
    async def adc_btn(self, button: ui.Button, inter: disnake.MessageInteraction):
        await self.handle_rol_selection(inter, "ADC")

    @ui.button(label="Support", style=ButtonStyle.blurple, emoji="🛡️")
    async def support_btn(self, button: ui.Button, inter: disnake.MessageInteraction):
        await self.handle_rol_selection(inter, "Support")

    async def handle_rol_selection(self, inter: disnake.MessageInteraction, rol: str):
        self.selected_rol = rol
        
        # Rank seçim menüsüne geç
        view = RankSecimView(self.nick, rol, self.bot)
        
        embed = Embed(
            title="🎮 Kayıt Ol - 3. Adım: Rank Seçimi",
            description=f"**Oyun İçi Nick:** `{self.nick}`\n**Rol:** `{rol}`\n\nMevcut rank'ini seç:",
            color=Color.blue()
        )
        
        await inter.response.edit_message(embed=embed, view=view)


class RankSecimView(ui.View):
    def __init__(self, nick: str, rol: str, bot):
        super().__init__(timeout=180)
        self.nick = nick
        self.rol = rol
        self.bot = bot
        
        # Rank select menu
        options = [
            disnake.SelectOption(label="Iron", emoji="⚫", description="Demir"),
            disnake.SelectOption(label="Bronze", emoji="🟤", description="Bronz"),
            disnake.SelectOption(label="Silver", emoji="⚪", description="Gümüş"),
            disnake.SelectOption(label="Gold", emoji="🟡", description="Altın"),
            disnake.SelectOption(label="Platinum", emoji="🔵", description="Platin"),
            disnake.SelectOption(label="Emerald", emoji="🟢", description="Zümrüt"),
            disnake.SelectOption(label="Diamond", emoji="💎", description="Elmas"),
            disnake.SelectOption(label="Master", emoji="🔴", description="Ustalık"),
            disnake.SelectOption(label="Grandmaster", emoji="🔥", description="Üstatlık"),
            disnake.SelectOption(label="Challenger", emoji="⭐", description="Şampiyonluk"),
        ]
        
        self.add_item(RankSelectMenu(self.nick, self.rol, self.bot, options))


class RankSelectMenu(ui.StringSelect):
    def __init__(self, nick: str, rol: str, bot, options):
        super().__init__(
            placeholder="Rank'ini seç...",
            options=options,
            custom_id="rank_select"
        )
        self.nick = nick
        self.rol = rol
        self.bot = bot

    async def callback(self, inter: disnake.MessageInteraction):
        rank = self.values[0]
        
        # Veritabanına kaydet
        await self.bot.execute(
            "INSERT INTO igns(guild_id, user_id, game, ign) VALUES(?,?,?,?)",
            inter.guild.id, inter.author.id, "lol", self.nick
        )
        
        # Rolleri ata
        member: Member = inter.author
        guild = inter.guild
        
        rol_silinecek_id = config.NEW_MEMBER_ROLE_ID  # Yeni Katıldı
        rol_verilecek_id = config.MEMBER_ROLE_ID  # Kayıtlı Üye
        
        eklenecek_roller = []
        
        # Koridor rolü
        koridor_rolu = utils.get(guild.roles, name=self.rol)
        if koridor_rolu:
            eklenecek_roller.append(koridor_rolu)
        
        # Rank rolü
        rank_rolu = utils.get(guild.roles, name=rank)
        if rank_rolu:
            eklenecek_roller.append(rank_rolu)
        
        # Ana kayıtlı rolü
        ana_rol = guild.get_role(rol_verilecek_id)
        if ana_rol:
            eklenecek_roller.append(ana_rol)
        
        # Rolleri uygula
        try:
            eski_rol = guild.get_role(rol_silinecek_id)
            if eski_rol and eski_rol in member.roles:
                await member.remove_roles(eski_rol)
            
            if eklenecek_roller:
                await member.add_roles(*eklenecek_roller)
        except Exception as e:
            print(f"Rol verme hatası: {e}")
        
        # Başarı mesajı
        success_embed = Embed(
            title="✅ Kayıt Başarılı!",
            description=(
                f"**Oyun İçi Nick:** `{self.nick}`\n"
                f"**Rol:** `{self.rol}`\n"
                f"**Rank:** `{rank}`\n\n"
                f"<#{config.QUEUE_CHANNEL_ID}> Kanalından istediğin rolü seçip 5v5'e katılabilirsin.\n"
                f"Hesabın başarıyla kaydedildi — iyi oyunlar!"
            ),
            color=Color.green()
        )
        success_embed.set_footer(text=f"herhangi bir sorun olursa ticket üzerinden iletişime geçebilirsin.")
        
        await inter.response.edit_message(embed=success_embed, view=None)
        
        # DM gönder
        try:
            dm_embed = Embed(
                title="🎉 Başarıyla Kayıt Oldun!",
                description=(
                    f"**Sunucu:** {guild.name}\n"
                    f"**Oyun İçi Nick:** `{self.nick}`\n"
                    f"**Rol:** `{self.rol}`\n"
                    f"**Rank:** `{rank}`\n\n"
                ),
                color=Color.green()
            )
            
            dm_embed.add_field(
                name="📋 Bilgilendirme",
                value=(
                    f"""🎮  **SCRİMLAB NEDİR?**
Scrimlab, *League of Legends’ta* özel lobiler kurup **5’e 5 — turnuva draftı formatında**, *scrim / esports / flex* tadında maçlar oynamamızı sağlayan bir sistemdir. Discord botumuz bu sistemi hem rekabetçı kılıyor hemde uygulanışını kolaylaştırıyor

🏆 **KAYIT OLUP MAÇ ARAMAK**
-  Kayıt kanalından kayıt ol butonu ile nick#etiket rol rank seçerek otomatik şekilde kayıt olup
-  Sıra (<#{config.QUEUE_CHANNEL_ID}>) Kanalından hızlıca rol seçip maçlara katılabilirsin
-  Maç saatleri hakkında bilgi almak için <#{config.MATCH_INFO_CHANNEL_ID}> kanalından maç bilgi rolü alabilirsin.

────────────────────────
‼️ **BUG / İSTEK / ÖNERİ**  
- Bildirmek için **<#{config.SUPPORT_CHANNEL_ID}>** 
────────────────────────"""
                ),
                inline=False
            )
            
            dm_embed.set_footer(text="❓ Sorular için yöneticilerle iletişime geç")
            
            await member.send(embed=dm_embed)
        except Exception as e:
            print(f"DM gönderilemedi ({member.id}): {e}")


class KayitStartView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Kayıt Ol",
        style=ButtonStyle.green,
        emoji="📝",
        custom_id="kayit_start_button"
    )
    async def kayit_button(self, button: ui.Button, inter: disnake.MessageInteraction):
        # Modal'ı aç
        await inter.response.send_modal(KayitModal())


class Utility(Cog):
    """
    🛠️ Araçlar
    """
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="kayıt-embed")
    async def kayit_embed(self, ctx):
        """Kayıt embed'ini oluştur (Sadece yöneticiler)"""
        
        # Yönetici kontrolü
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send(
                embed=error("Bu komutu sadece yöneticiler kullanabilir!"),
                ephemeral=True
            )
        
        embed = Embed(
            title="🎮 Scrimlab Kayıt Sistemi",
            description=(
                "Sunucumuza hoş geldin!\n\n"
                "Kayıt olmak için aşağıdaki **Kayıt Ol** butonuna tıkla.\n\n"
                "**Kayıt Adımları:**\n"
                "1️⃣ Oyun içi nick ve etiketini yaz\n"
                "2️⃣ Ana rolünü seç\n"
                "3️⃣ Mevcut rank'ini seç\n\n"
                "**Neden kayıt olmalıyım?**\n"
                "✅ 5v5 maçlarına katılabilirsin\n"
                "✅ Özel rollere erişim kazanırsın\n"
                "✅ Takım arkadaşları bulabilirsin\n"
            ),
            color=Color.blue()
        )
        
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(
            text="Sorun yaşarsan yöneticilerle iletişime geç",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        
        # Görsel ekle (isteğe bağlı)
        # embed.set_image(url="BİR_GÖRSELİN_URL'Sİ")
        
        view = KayitStartView()
        
        await ctx.channel.send(embed=embed, view=view)
        await ctx.send(
            embed=success("Kayıt embed'i başarıyla oluşturuldu!"),
            ephemeral=True
        )

    @Cog.listener()
    async def on_ready(self):
        """Bot başladığında persistent view'ları yükle"""
        self.bot.add_view(KayitStartView())


def setup(bot):
    bot.add_cog(Utility(bot))
