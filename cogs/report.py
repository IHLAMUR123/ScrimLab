import disnake
from disnake.ext import commands
from datetime import datetime
import asyncio

from core import config

class ReportSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="report", 
        description="Anonim olarak şikayette bulunun."
    )
    async def report(
        self, 
        inter: disnake.ApplicationCommandInteraction, 
        kisi: disnake.Member, 
        sebep: str, 
        kanit: str
    ):
        report_channel_id = config.REPORT_CHANNEL_ID

        report_channel = self.bot.get_channel(report_channel_id)
        
        # 1. Kanaldaki 'bot düşünüyor' yazısını ANINDA sil (İz bırakmaz)
        try:
            msg = await inter.original_message()
            await msg.delete()
        except:
            pass

        # 2. Kullanıcıya DM Gönder
        try:
            await inter.author.send(
                f"✅ **Şikayetin anonim olarak alındı.**\n"
                f"Şikayet edilen: `{kisi.name}`\n"
                f"Yetkililer inceleyip gerekirse bu DM üzerinden sana dönüş yapacaktır."
            )
        except disnake.Forbidden:
            # Kullanıcının DM'si kapalıysa uyaracak bir yer yok çünkü kanal izini sildik.
            pass

        # 3. Yetkili Kanalına Raporu Gönder
        if report_channel:
            embed = disnake.Embed(
                title="📥 YENİ ANONİM ŞİKAYET",
                color=disnake.Color.red(),
                description=f"Cevap vermek için: `!cevap {inter.author.id} mesajınız`",
                timestamp=datetime.now()
            )
            embed.add_field(name="Şikayet Eden (Gizli)", value=f"{inter.author.mention} (`{inter.author.id}`)", inline=True)
            embed.add_field(name="Şikayet Edilen", value=f"{kisi.mention} (`{kisi.id}`)", inline=True)
            embed.add_field(name="Sebep", value=f"```\n{sebep}\n```", inline=False)
            embed.add_field(name="Kanıt", value=kanit, inline=False)
            embed.set_footer(text="Cevap sistemini kullanmak için kullanıcının ID'sini kopyalayın.")
            
            await report_channel.send(embed=embed)

    # --- CEVAP VERME SİSTEMİ ---
    @commands.command(name="cevap")
    @commands.has_permissions(administrator=True) # Sadece adminler cevap verebilir
    async def cevap(self, ctx, user_id: int, *, mesaj: str):
        """Adminlerin rapor kanalından kullanıcıya cevap vermesini sağlar: !cevap ID mesaj"""
        
        target_user = self.bot.get_user(user_id)
        if not target_user:
            return await ctx.send("❌ Kullanıcı bulunamadı (Botun ortak bir sunucuda olması gerekir).", delete_after=5)

        try:
            embed = disnake.Embed(
                title="🛡️ Yetkili Cevabı",
                description=f"Şikayetinize istinaden yetkililerimizden bir yanıt var:\n\n**Mesaj:** {mesaj}",
                color=disnake.Color.green(),
                timestamp=datetime.now()
            )
            embed.set_footer(text="bizi tercih ettiğiniz için teşekkürler.")
            
            await target_user.send(embed=embed)
            await ctx.message.add_reaction("✅")
            await ctx.send(f"🚀 Cevap başarıyla {target_user.name} kullanıcısına iletildi.", delete_after=5)
        except disnake.Forbidden:
            await ctx.send("❌ Kullanıcının DM'si kapalı olduğu için mesaj iletilemedi.", delete_after=5)

def setup(bot):
    bot.add_cog(ReportSystem(bot))
