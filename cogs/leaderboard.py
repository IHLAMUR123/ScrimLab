from disnake import Color, Embed, OptionChoice
from disnake.ext.commands import Cog, Param, command, slash_command
from Paginator import CreatePaginator
from core.embeds import error

class Leaderboard(Cog):
    """
    ⏫;Sıralama
    """

    def __init__(self, bot):
        self.bot = bot

    async def leaderboard(self, ctx, game, type="mmr"):
        if not type.lower() in ['mmr', 'mvp']:
            return await ctx.send(embed=error('Skor tablosu türü "mmr" veya "mvp" olabilir.'))
        
        if type == 'mmr':
            st_pref = await self.bot.fetchrow("SELECT * FROM switch_team_preference WHERE guild_id = ?", ctx.guild.id)
            if not st_pref:
                user_data = await self.bot.fetch(
                    "SELECT * FROM mmr_rating WHERE guild_id = ? and game = ?",
                    ctx.guild.id, game
                )
                user_data = sorted(list(user_data), key=lambda x: float(x[2]) - (2 * float(x[3])), reverse=True)
            else:
                user_data = await self.bot.fetch(
                    "SELECT *, (points.wins + 0.0) / (MAX(points.wins + points.losses, 1.0) + 0.0) AS percentage FROM points WHERE guild_id = ? and game = ?",
                    ctx.guild.id, game
                )
                user_data = sorted(list(user_data), key=lambda x: x[4], reverse=True)
                user_data = sorted(list(user_data), key=lambda x: x[2], reverse=True)
        else:
            user_data = await self.bot.fetch(
                "SELECT * FROM mvp_points WHERE guild_id = ? and game = ?",
                ctx.guild.id, game
            )
            user_data = sorted(list(user_data), key=lambda x: x[2], reverse=True)

        if not user_data:
            return await ctx.send(embed=error("Sunulacak giriş yok."))

        embed = Embed(title=f"🏆 LoL Liderlik Tablosu", color=Color.blurple())
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        embeds = [embed]
        current_embed = 0
        vals = 1

        async def add_field(data, current_embed) -> None:
            user_history = await self.bot.fetch("SELECT role FROM members_history WHERE user_id = ? and game = ?", data[1], game)
            
            # Sadece LoL Rolleri
            roles_players = {'top': 0, 'jungle': 0, 'mid': 0, 'support': 0, 'adc': 0}
            
            if user_history:
                for history in user_history:
                    if history[0] in roles_players:
                        roles_players[history[0]] += 1
                
                most_played_role_key = max(roles_players, key=lambda x: roles_players[x])
                if not roles_players[most_played_role_key]:
                    most_played_role = "<:fill:1066868480537800714>"
                else:
                    most_played_role = self.bot.role_emojis.get(most_played_role_key, "<:fill:1066868480537800714>")
            else:
                most_played_role = "<:fill:1066868480537800714>"

            p_data = await self.bot.fetchrow("SELECT * FROM points WHERE user_id = ? and guild_id = ? and game = ?", data[1], ctx.guild.id, game)
            wins, losses = (p_data[2], p_data[3]) if p_data else (0, 0)
            total = max(wins + losses, 1)
            percentage = round((wins / total) * 100)

            name = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"#{i+1}")
            member = ctx.guild.get_member(data[1])
            member_name = member.name if member else "Bilinmeyen Üye"

            if type == 'mvp':
                val_str = f"{most_played_role} {member_name}   {wins}W {losses}L {percentage}% WR {data[2]} MVP"
            else:
                skill = round(float(data[2]) - (2 * float(data[3])), 2)
                display_mmr = f"{int(skill*100)}" if data[4] >= 10 else f"{data[4]}/10"
                val_str = f"{most_played_role} {member_name}   {display_mmr} {wins}W {losses}L {percentage}% WR"
            
            embeds[current_embed].add_field(name=name, value=val_str, inline=False)

        for i, data in enumerate(user_data):
            if vals <= 5:
                await add_field(data, current_embed)
                vals += 1
            else:
                e = Embed(color=Color.blurple())
                if ctx.guild.icon: e.set_thumbnail(url=ctx.guild.icon.url)
                embeds.append(e)
                current_embed += 1
                await add_field(data, current_embed)
                vals = 1

        if len(embeds) != 1:
            await ctx.send(embed=embeds[0], view=CreatePaginator(embeds, ctx.author.id))
        else:
            await ctx.send(embed=embeds[0])

    @slash_command(name="sıralama")
    async def leaderboard_lol(self, ctx, type=Param(default="mmr", choices=[OptionChoice("MVP", "mvp"), OptionChoice("MMR", "mmr")])):
        """LoL Liderlik Tablosunu Gör."""
        await self.leaderboard(ctx, 'lol', type)
    
    @command(name="sıralama")
    async def leaderboard_lol_prefix(self, ctx, type="mmr"):
        await self.leaderboard(ctx, 'lol', type)

    async def rank(self, ctx, game, type):
        if type.lower() not in ['mvp', 'mmr']:
            return await ctx.send(embed=error("Derece türü 'mmr' veya 'mvp' olabilir."))

        if type == 'mmr':
            user_data = await self.bot.fetch("SELECT * FROM mmr_rating WHERE guild_id = ? and game = ?", ctx.guild.id, game)
            user_data = sorted(list(user_data), key=lambda x: float(x[2]) - (2 * float(x[3])), reverse=True)
        else:
            user_data = await self.bot.fetch("SELECT * FROM mvp_points WHERE guild_id = ? and game = ?", ctx.guild.id, game)
            user_data = sorted(list(user_data), key=lambda x: x[2], reverse=True)

        if not user_data or ctx.author.id not in [x[1] for x in user_data]:
            return await ctx.send(embed=error("Henüz bir oyun oynamadınız veya veri bulunamadı."))
        
        ign = await self.bot.fetchrow("SELECT ign FROM igns WHERE guild_id = ? and user_id = ? and game = ?", ctx.guild.id, ctx.author.id, game)
        display_name = ign[0] if ign else ctx.author.name
        
        embed = Embed(title=f"⏫ LoL Rank: {display_name}", color=ctx.author.color)
        if ctx.author.avatar: embed.set_thumbnail(url=ctx.author.avatar.url)

        for i, data in enumerate(user_data):
            if data[1] == ctx.author.id:
                p_data = await self.bot.fetchrow("SELECT * FROM points WHERE user_id = ? and game = ?", data[1], game)
                wins, losses = (p_data[2], p_data[3]) if p_data else (0, 0)
                total = max(wins + losses, 1)
                percentage = round((wins / total) * 100, 2)

                if type == 'mvp':
                    val = f"<@{data[1]}> - **{wins}** Wins - **{percentage}%** WR - **{data[2]}x** MVP"
                else:
                    skill = round(float(data[2]) - (2 * float(data[3])), 2)
                    display_mmr = f"**{int(skill*100)}** MMR" if data[4] >= 10 else f"**{data[4]}/10** Maç"
                    val = f"<@{data[1]}> - **{wins}** Wins - **{percentage}%** WR - {display_mmr}"
                
                embed.add_field(name=f"#{i + 1}", value=val, inline=False)
                await ctx.send(embed=embed)
                break

    @slash_command(name="rank")
    async def rank_lol(self, ctx, type = Param(choices=[OptionChoice('MMR', 'mmr'), OptionChoice('MVP', 'mvp')])):
        """Derecenizi kontrol edin."""
        await self.rank(ctx, 'lol', type)

    @command(name="rank")
    async def rank_lol_prefix(self, ctx, type="mmr"):
        await self.rank(ctx, 'lol', type)

def setup(bot):
    bot.add_cog(Leaderboard(bot))
