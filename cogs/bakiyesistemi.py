import disnake
from disnake.ext import commands
import re
from datetime import datetime

class BakiyeSistemi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.win_reward = 50
        self.log_channel_id = 1454210251887874128 

    async def send_bakiye_log(self, title, description, color=disnake.Color.blue()):
        log_channel = self.bot.get_channel(self.log_channel_id)
        if log_channel:
            embed = disnake.Embed(
                title=f"📋 [BAKİYE LOG] {title}",
                description=description,
                color=color,
                timestamp=datetime.now()
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != self.bot.user.id:
            return
        if not message.embeds:
            return
            
        embed = message.embeds[0]
        if embed.title == "Oyun Sonlandı!":
            for field in embed.fields:
                if field.name == "Kazanan Takım":
                    winner_ids = re.findall(r'<@!?(\d+)>', field.value)
                    
                    if winner_ids:
                        mentions_list = []
                        for uid in winner_ids:
                            user_id = int(uid)
                            await self.bot.execute(
                                "INSERT INTO users (user_id, bakiye) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET bakiye = bakiye + ?", 
                                user_id, self.win_reward, self.win_reward
                            )
                            mentions_list.append(f"<@{user_id}>")

                        winners_str = ", ".join(mentions_list)
                        await self.send_bakiye_log(
                            "Otomatik Ödül Dağıtımı",
                            f"**Maç:** {message.jump_url}\n**Ödül:** `{self.win_reward}`\n**Kazananlar:** {winners_str}",
                            disnake.Color.green()
                        )

    @commands.slash_command(name="cüzdan", description="Bakiyenizi görüntüler.")
    async def cüzdan(self, inter: disnake.ApplicationCommandInteraction, kullanıcı: disnake.Member = None):
        # 1. Önce defer yaparak Discord'a zaman kazandırıyoruz
        await inter.response.defer()
        
        target = kullanıcı or inter.author
        res = await self.bot.fetchval("SELECT bakiye FROM users WHERE user_id = ?", target.id)
        bakiye = res if res is not None else 0
        
        embed = disnake.Embed(
            title="💰 Cüzdan", 
            description=f"{target.mention} bakiyesi: **{bakiye} 💰**", 
            color=disnake.Color.gold()
        )
        # 2. defer() kullandığımız için edit_original_message artık çalışır
        await inter.edit_original_message(embed=embed)

    @commands.slash_command(name="bakiyedüzenle", description="[Admin] Bakiye ekler/çıkarır.")
    @commands.has_permissions(administrator=True)
    async def bakiyedüzenle(self, inter: disnake.ApplicationCommandInteraction, kullanıcı: disnake.Member, miktar: int):
        # 1. defer yaparak zaman kazanıyoruz (Veritabanı işlemi sürerken hata vermemesi için)
        await inter.response.defer()
        
        await self.bot.execute(
            "INSERT INTO users (user_id, bakiye) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET bakiye = bakiye + ?", 
            kullanıcı.id, miktar, miktar
        )
        
        durum = "eklendi" if miktar > 0 else "çıkarıldı"
        await inter.edit_original_message(content=f"✅ {kullanıcı.mention} hesabına `{abs(miktar)}` bakiye {durum}.")
        
        await self.send_bakiye_log(
            "Manuel Müdahale",
            f"**Yetkili:** {inter.author.mention}\n**Kullanıcı:** {kullanıcı.mention}\n**Miktar:** `{miktar}`\n**İşlem:** {durum.capitalize()}",
            disnake.Color.orange()
        )

def setup(bot):
    bot.add_cog(BakiyeSistemi(bot))
