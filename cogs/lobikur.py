# lobikur.py — MAÇ:random kategorileri için otomatik lobby kurucu

import random
import string
import disnake
import asyncio
from disnake.ext import commands



class VoteView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.votes = {}
        self.message = None

    async def update_embed(self):
        bo1_count = list(self.votes.values()).count("BO1")
        bo3_count = list(self.votes.values()).count("BO3")
        
        embed = self.message.embeds[0]
        embed.description = f"**Oylama Durumu:**\nBO1: {bo1_count}\nBO3: {bo3_count}\n\nToplam Oy: {len(self.votes)}"
        await self.message.edit(embed=embed)

    @disnake.ui.button(label="BO1", style=disnake.ButtonStyle.blurple, custom_id="vote_bo1")
    async def bo1_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.votes[inter.user.id] = "BO1"
        await self.update_embed()
        await inter.response.send_message(content="BO1 için oy verdin!", ephemeral=True)

    @disnake.ui.button(label="BO3", style=disnake.ButtonStyle.green, custom_id="vote_bo3")
    async def bo3_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.votes[inter.user.id] = "BO3"
        await self.update_embed()
        await inter.response.send_message(content="BO3 için oy verdin!", ephemeral=True)

    async def on_timeout(self):
        if len(self.votes) < 9:
             embed = disnake.Embed(title="Oylama Geçersiz", description="Yeterli katılım sağlanamadı (Min 9 kişi).", color=disnake.Color.red())
             await self.message.channel.send(embed=embed)
        else:
             bo1 = list(self.votes.values()).count("BO1")
             bo3 = list(self.votes.values()).count("BO3")
             if bo1 > bo3:
                 winner = "BO1"
                 color = disnake.Color.blurple()
             elif bo3 > bo1:
                 winner = "BO3"
                 color = disnake.Color.green()
             else:
                 winner = "Eşitlik"
                 color = disnake.Color.orange()
             
             embed = disnake.Embed(title="Oylama Bitti", description=f"Oylama Sonucu: **{winner}**", color=color)
             await self.message.channel.send(embed=embed)
        
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)


class RoomCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: disnake.abc.GuildChannel):

        # sadece text kanallar
        if not isinstance(channel, disnake.TextChannel):
            return
        
        # kategori yoksa geç
        if not channel.category:
            return
        
        # KATEGORİ FORMAT: maç:ASD123asd
        kategori_prefix = channel.category.name.split(":", 1)[0].lower()

        # sadece "maç:" olan kategoriler
        if kategori_prefix != "maç":
            return
        
        # discord biraz geç indexleyebilir
        await asyncio.sleep(6)

        guild = channel.guild

        try:
            # kanal adı: scrimlab-XXXX veya lobby-XXXX
            game_id = None

            if channel.name.startswith("lobby-"):
                game_id = channel.name.replace("lobby-", "")
            elif channel.name.startswith("lobi-"):
                game_id = channel.name.replace("lobi-", "")

            if not game_id:
                print("Hata: Kanal isminden game_id çıkarılamadı.")
                return

            # oyuna ait oyuncuları çek
            member_data = await self.bot.fetch(
                "SELECT author_id, role, team FROM game_member_data WHERE game_id = ?",
                game_id
            )

            if not member_data:
                print(f"Hata: {game_id} için oyuncu verisi bulunamadı.")
                return

            # sadece red/blue takımdakiler
            oyuncu_idleri = [x[0] for x in member_data if x[2] in ["red", "blue"]]

            if not oyuncu_idleri:
                print("Hata: Maçta oyuncu bulunamadı.")
                return

            # rastgele lobby kurucu
            kurucu_id = random.choice(oyuncu_idleri)

            kurucu = guild.get_member(int(kurucu_id))
            if not kurucu:
                try:
                    kurucu = await guild.fetch_member(int(kurucu_id))
                except:
                    print("Kurucu üye sunucuda bulunamadı.")
                    return

            # lobby bilgileri
            sifre = "".join(random.choices(string.digits, k=6))
            oda_ismi = f"ScrimLab-{random.randint(100, 999)}"

            embed = disnake.Embed(
                title="**MAÇ LOBİSİ!**",
                description=(
                    f"**Oda Kurucusu:** {kurucu.mention}\n"
                    f"Lobideki oyuncular arasından rastgele seçildin.\n"
                    f"Lütfen lobiyi kur ve diğerlerine bilgiyi ver."
                ),
                color=0x1abc9c
            )

            embed.add_field(name="**Oda İsmi**", value=oda_ismi, inline=True)
            embed.add_field(name="**Oda Şifresi**", value=sifre, inline=True)

            embed.set_footer(
                text=f"{kurucu.display_name} | LoL Client > Özel Oyun Kur",
                icon_url=self.bot.user.display_avatar.url
            )

            await channel.send(content=kurucu.mention, embed=embed)

            # Oylama Başlat
            vote_embed = disnake.Embed(
                title="📊 BO1 vs BO3 Oylaması",
                description="Lütfen oynanacak maç türünü seçiniz.\nOylama 5 dakika sürecektir.\nSadece 9 ve üzeri oy kullanılırsa geçerli sayılacaktır.",
                color=disnake.Color.gold()
            )
            view = VoteView()
            msg = await channel.send(embed=vote_embed, view=view)
            view.message = msg


        except Exception as e:
            print(f"RoomCreator Hatası: {e}")
            import traceback
            print(traceback.format_exc())


def setup(bot):
    bot.add_cog(RoomCreator(bot))
