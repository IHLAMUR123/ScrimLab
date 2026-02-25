import disnake
from disnake.ext import commands

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="profil",
        description="Oyuncu profilini gösterir"
    )
    async def profile(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.User = None
    ):
        # --- ÖNCE DEFER (çok önemli) ---
        await inter.response.defer()

        target = user or inter.author
        user_id = target.id

        # 1. Maç İstatistikleri
        stats = await self.bot.fetchrow(
            """
            SELECT 
                COUNT(*), 
                SUM(CASE WHEN result = 'won' THEN 1 ELSE 0 END) 
            FROM members_history 
            WHERE user_id = ?
            """,
            user_id
        )

        total_matches = stats[0] if stats and stats[0] is not None else 0
        wins = stats[1] if stats and stats[1] is not None else 0
        losses = total_matches - wins
        winrate = round((wins / total_matches) * 100, 1) if total_matches > 0 else 0.0

        # 2. Sıralama Verileri
        rank = await self.bot.fetchval(
            """
            SELECT pos FROM (
                SELECT user_id, RANK() OVER (ORDER BY wins DESC) AS pos
                FROM points
            )
            WHERE user_id = ?
            """,
            user_id
        )

        total_players = await self.bot.fetchval("SELECT COUNT(*) FROM points")

        # 3. Bakiye
        bakiye = await self.bot.fetchval(
            "SELECT bakiye FROM users WHERE user_id = ?",
            user_id
        )
        bakiye = bakiye if bakiye is not None else 0

        # 4. Embed
        embed = disnake.Embed(
            title=f"👤 {target.display_name} Profili",
            description=f"Cüzdan: `{bakiye}` 💰",
            color=0x5865F2
        )

        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(
            name="🎮 Maç İstatistikleri",
            value=(
                f"**Toplam Maç:** `{total_matches}`\n"
                f"✅ **Galibiyet:** `{wins}`\n"
                f"❌ **Mağlubiyet:** `{losses}`\n"
                f"📊 **Winrate:** `% {winrate}`"
            ),
            inline=False
        )

        rank_text = f"**#{rank} / {total_players}**" if rank else "Sıralama dışı"
        embed.add_field(
            name="🏅 Lig Sıralaması",
            value=rank_text,
            inline=True
        )

        embed.set_footer(
            text="ScrimLabTR",
            icon_url=self.bot.user.display_avatar.url
        )

        # --- Defer ettiğimiz mesajı şimdi düzenliyoruz ---
        await inter.edit_original_message(embed=embed)

def setup(bot):
    bot.add_cog(Profile(bot))
