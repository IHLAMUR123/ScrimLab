import disnake
from disnake.ext import commands
import random

class DuelloView(disnake.ui.View):
    def __init__(self, bot, challenger, target, amount):
        super().__init__(timeout=60.0)
        self.bot = bot
        self.challenger = challenger
        self.target = target
        self.amount = amount

    @disnake.ui.button(label="Kabul Et", style=disnake.ButtonStyle.green, emoji="⚔️")
    async def accept(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Sadece düello edilen kişi kabul edebilir
        if inter.author.id != self.target.id:
            return await inter.send("Bu düello teklifi sana gelmedi!", ephemeral=True)

        # Güncel bakiyeleri kontrol et
        c_bal = await self.bot.fetchval("SELECT bakiye FROM users WHERE user_id = ?", self.challenger.id) or 0
        t_bal = await self.bot.fetchval("SELECT bakiye FROM users WHERE user_id = ?", self.target.id) or 0

        if c_bal < self.amount:
            return await inter.response.edit_message(content=f"❌ Düello iptal: {self.challenger.mention} bakiyesi yetersiz!", embed=None, view=None)
        if t_bal < self.amount:
            return await inter.send("Yeterli bakiyen yok!", ephemeral=True)

        # Zarlar atılıyor
        c_roll = random.randint(1, 100)
        t_roll = random.randint(1, 100)
        while c_roll == t_roll: # Beraberlik istemiyoruz
            t_roll = random.randint(1, 100)

        winner = self.challenger if c_roll > t_roll else self.target
        loser = self.target if winner == self.challenger else self.challenger

        # Parayı transfer et
        await self.bot.execute("UPDATE users SET bakiye = bakiye - ? WHERE user_id = ?", self.amount, loser.id)
        await self.bot.execute("UPDATE users SET bakiye = bakiye + ? WHERE user_id = ?", self.amount, winner.id)

        # Sonuç Embedı
        embed = disnake.Embed(
            title="⚔️ Düello Sonuçlandı!",
            description=f"{self.challenger.mention} vs {self.target.mention}",
            color=disnake.Color.gold()
        )
        embed.add_field(name=f"🎲 {self.challenger.display_name}", value=f"Zar: `{c_roll}`", inline=True)
        embed.add_field(name=f"🎲 {self.target.display_name}", value=f"Zar: `{t_roll}`", inline=True)
        embed.add_field(name="🏆 KAZANAN", value=f"{winner.mention}\nKazanç: `{self.amount}` 💰", inline=False)
        embed.set_footer(text="Kaybeden taraftan bakiye otomatik tahsil edildi.")

        await inter.response.edit_message(embed=embed, view=None)
        self.stop()

    @disnake.ui.button(label="Reddet", style=disnake.ButtonStyle.red, emoji="🛡️")
    async def decline(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.target.id:
            return await inter.send("Bu senin düellon değil!", ephemeral=True)
        
        await inter.response.edit_message(content=f"🛡️ {self.target.mention} düellodan kaçtı!", embed=None, view=None)
        self.stop()

class Duello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="duello",
        description="Bir oyuncuya bakiyesine meydan okursun."
    )
    async def duello(self, inter: disnake.ApplicationCommandInteraction, kullanıcı: disnake.Member, miktar: int):
        if miktar <= 0:
            return await inter.send("Miktar sıfırdan büyük olmalıdır!", ephemeral=True)
        
        if kullanıcı.id == inter.author.id:
            return await inter.send("Kendi kendine düello yapamazsın, o kadar da yalnız değilsindir!", ephemeral=True)
        
        if kullanıcı.bot:
            return await inter.send("Botlarla düello yapamazsın, hile yaparlar!", ephemeral=True)

        # Bakiye kontrolü
        challenger_bal = await self.bot.fetchval("SELECT bakiye FROM users WHERE user_id = ?", inter.author.id) or 0
        if challenger_bal < miktar:
            return await inter.send(f"Yeterli bakiyen yok! Mevcut: `{challenger_bal}`", ephemeral=True)

        target_bal = await self.bot.fetchval("SELECT bakiye FROM users WHERE user_id = ?", kullanıcı.id) or 0
        if target_bal < miktar:
            return await inter.send(f"Karşı tarafın (`{kullanıcı.display_name}`) yeterli bakiyesi yok!", ephemeral=True)

        embed = disnake.Embed(
            title="⚔️ DÜELLO MEYDAN OKUMASI",
            description=f"{inter.author.mention}, {kullanıcı.mention} kişisini **{miktar}** 💰 değerinde düelloya davet ediyor!",
            color=disnake.Color.red()
        )
        embed.set_footer(text="Kabul etmek için 60 saniyen var!")

        await inter.send(content=f"{kullanıcı.mention}", embed=embed, view=DuelloView(self.bot, inter.author, kullanıcı, miktar))

def setup(bot):
    bot.add_cog(Duello(bot))
