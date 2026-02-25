import disnake
from disnake.ext import commands
from datetime import datetime, timedelta
import asyncio

# Global hafıza (Bot kapanınca sıfırlanır, DB'ye bağlamak istersen belirtebilirsin)
active_warnings = {} # {user_id: bitis_zamani}
original_nicks = {}  # {user_id: eski_isim}

class UyariSistemi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # SENİN REPOR KANAL ID'Nİ ROL ID OLARAK VARSAYDIM, DEĞİŞTİRMEYİ UNUTMA ❗
        self.uyari_rol_id = 1454162669597622303 

    # --- TİMEOUT MODAL (FORM) SINIFI ---
    class TimeoutModal(disnake.ui.Modal):
        def __init__(self, target_member, reason):
            self.target_member = target_member
            self.reason = reason
            components = [
                disnake.ui.TextInput(
                    label="Kaç saat timeout atılsın?",
                    placeholder="Örn: 24",
                    custom_id="timeout_hours",
                    style=disnake.TextInputStyle.short,
                    max_length=2,
                )
            ]
            super().__init__(title="Kullanıcı Zaten Uyarılı!", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            hours = inter.text_values["timeout_hours"]
            try:
                h = int(hours)
                await self.target_member.timeout(duration=timedelta(hours=h), reason=self.reason)
                await inter.response.send_message(
                    f"🚫 {self.target_member.mention} zaten uyarılıydı! İkinci ihlalden dolayı `{h}` saat timeout atıldı.",
                    ephemeral=False
                )
            except Exception as e:
                await inter.response.send_message(f"❌ Hata: {e}", ephemeral=True)

    @commands.slash_command(
        name="uyariver",
        description="Kullanıcıya süreli uyarı verir."
    )
    @commands.has_permissions(manage_messages=True)
    async def uyariver(
        self, 
        inter: disnake.ApplicationCommandInteraction, 
        kisi: disnake.Member, 
        sebep: str, 
        sure_dakika: int
    ):
        # 1. KONTROL: KİŞİ ZATEN UYARILI MI?
        if kisi.id in active_warnings:
            # ÖNEMLİ: Eğer defer edildiyse modal açılmaz. 
            # interaction.response.send_modal kullanabilmek için defer'ı bypass etmeliyiz.
            # Ancak main.py'de otomatik defer olduğu için modal açmak zordur.
            # Çözüm: Zaten uyarılıysa direkt mesajla soralım veya modal deneyelim.
            try:
                await inter.response.send_modal(modal=self.TimeoutModal(kisi, sebep))
            except disnake.InteractionResponded:
                # Eğer main.py defer attıysa modal gönderemeyiz, bu yüzden takip eden mesajı kullanırız.
                await inter.edit_original_message(content=f"⚠️ {kisi.mention} zaten uyarılı! Lütfen manuel olarak timeout atın veya uyarının bitmesini bekleyin.")
            return

        # 2. İLK UYARI İŞLEMLERİ
        active_warnings[kisi.id] = datetime.now() + timedelta(minutes=sure_dakika)
        original_nicks[kisi.id] = kisi.display_name
        role = inter.guild.get_role(self.uyari_rol_id)

        # DM Bildirimi
        try:
            embed = disnake.Embed(
                title="⚠️ UYARI ALDINIZ",
                description=f"**Sebep:** {sebep}\n**Süre:** {sure_dakika} Dakika",
                color=disnake.Color.red()
            )
            await kisi.send(embed=embed)
        except: pass

        # İsim Değiştirme ve Rol Verme
        try:
            if role: await kisi.add_roles(role)
            await kisi.edit(nick=f"⚠️ {kisi.display_name[:28]}")
        except: pass

        await inter.edit_original_message(content=f"✅ {kisi.mention} için `{sure_dakika}` dakikalık uyarı başlatıldı.")

        # Süre Bitimi Bekleme
        await asyncio.sleep(sure_dakika * 60)
        
        # Eğer hala uyarılıysa (manuel kaldırılmadıysa) temizle
        if kisi.id in active_warnings:
            await self.clear_warning_logic(kisi, role)

    @commands.slash_command(
        name="uyarikaldir",
        description="Kullanıcının uyarısını anında temizler."
    )
    @commands.has_permissions(manage_messages=True)
    async def uyarikaldir(self, inter: disnake.ApplicationCommandInteraction, kisi: disnake.Member):
        if kisi.id not in active_warnings:
            return await inter.edit_original_message(content="❌ Bu kullanıcının aktif bir uyarısı yok.")
        
        role = inter.guild.get_role(self.uyari_rol_id)
        await self.clear_warning_logic(kisi, role)
        await inter.edit_original_message(content=f"🛡️ {kisi.mention} üzerindeki uyarı kaldırıldı ve ismi düzeltildi.")

    async def clear_warning_logic(self, member, role):
        """Rolü alan ve ismi eski haline döndüren yardımcı fonksiyon"""
        if member.id in active_warnings:
            del active_warnings[member.id]
        
        old_nick = original_nicks.pop(member.id, member.display_name.replace("⚠️ ", ""))
        
        try:
            if role: await member.remove_roles(role)
            await member.edit(nick=old_nick)
        except: pass

def setup(bot):
    bot.add_cog(UyariSistemi(bot))
