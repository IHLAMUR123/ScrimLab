"""
Kalıcı Takım Sistemi
/takım komutları ile takım yönetimi
"""
import disnake
from disnake.ext import commands
from disnake import Embed, Color
import uuid
import random
from datetime import datetime
from core.embeds import error, success
from core.buttons import ConfirmationButtons


class Teams(commands.Cog):
    """🏆 Kalıcı Takım Sistemi"""
    
    def __init__(self, bot):
        self.bot = bot
        self.team_emojis = ["🔷", "🔶", "🔴", "🟢", "🟡"]
    
    @commands.slash_command(name="takım")
    async def team_group(self, inter):
        """Takım komutları"""
        pass
    
    @team_group.sub_command(name="kur")
    async def create_team(self, inter: disnake.ApplicationCommandInteraction, isim: str):
        """
        Yeni takım oluştur
        
        Parameters
        ----------
        isim: Takım adı
        """
        await inter.response.defer(ephemeral=True)
        
        # Kullanıcı zaten takımda mı?
        existing_team = await self.bot.fetchrow(
            "SELECT team_id FROM team_members WHERE user_id = ?",
            inter.author.id
        )
        
        if existing_team:
            return await inter.send(
                embed=error("Zaten bir takımdasın! Önce `/takım ayrıl` kullan."),
                ephemeral=True
            )
        
        # Takım adı kullanılıyor mu?
        name_check = await self.bot.fetchrow(
            "SELECT team_id FROM teams WHERE guild_id = ? AND team_name = ?",
            inter.guild.id, isim
        )
        
        if name_check:
            return await inter.send(
                embed=error(f"**{isim}** adı zaten kullanılıyor!"),
                ephemeral=True
            )
        
        # Yeni takım oluştur
        team_id = str(uuid.uuid4())[:8]
        
        # Discord rolü oluştur
        random_color = disnake.Color(random.randint(0, 0xFFFFFF))
        role = await inter.guild.create_role(
            name=f"{isim}",
            color=random_color,
            mentionable=True
        )
        
        # Veritabanına kaydet
        await self.bot.execute(
            "INSERT INTO teams(team_id, guild_id, team_name, captain_id, role_id) VALUES(?, ?, ?, ?, ?)",
            team_id, inter.guild.id, isim, inter.author.id, role.id
        )
        
        await self.bot.execute(
            "INSERT INTO team_members(team_id, user_id) VALUES(?, ?)",
            team_id, inter.author.id
        )
        
        await self.bot.execute(
            "INSERT INTO team_stats(team_id) VALUES(?)",
            team_id
        )
        
        # Kaptana rol ver
        await inter.author.add_roles(role)
        
        embed = Embed(
            title="✅ Takım Oluşturuldu!",
            description=f"**{isim}** takımı başarıyla kuruldu!\n\nKaptan: {inter.author.mention}",
            color=random_color
        )
        embed.add_field(name="Takım ID", value=f"`{team_id}`", inline=False)
        embed.add_field(name="Üye Sayısı", value="1/5", inline=True)
        embed.add_field(name="Rol", value=role.mention, inline=True)
        
        await inter.send(embed=embed, ephemeral=True)
    
    @team_group.sub_command(name="davet")
    async def invite_member(self, inter: disnake.ApplicationCommandInteraction, kullanıcı: disnake.Member):
        """
        Takıma oyuncu davet et (sadece kaptan)
        
        Parameters
        ----------
        kullanıcı: Davet edilecek oyuncu
        """
        await inter.response.defer(ephemeral=True)
        
        # Kullanıcının takımını bul
        team_data = await self.bot.fetchrow(
            """SELECT t.team_id, t.team_name, t.captain_id, t.role_id 
               FROM teams t 
               JOIN team_members tm ON t.team_id = tm.team_id 
               WHERE tm.user_id = ? AND t.guild_id = ?""",
            inter.author.id, inter.guild.id
        )
        
        if not team_data:
            return await inter.send(
                embed=error("Bir takımda değilsin!"),
                ephemeral=True
            )
        
        # Kaptan kontrolü
        if team_data[2] != inter.author.id:
            return await inter.send(
                embed=error("Sadece kaptan oyuncu davet edebilir!"),
                ephemeral=True
            )
        
        # Davet edilen kullanıcı zaten takımda mı?
        target_team = await self.bot.fetchrow(
            "SELECT team_id FROM team_members WHERE user_id = ?",
            kullanıcı.id
        )
        
        if target_team:
            return await inter.send(
                embed=error(f"{kullanıcı.mention} zaten bir takımda!"),
                ephemeral=True
            )
        
        # Takım dolu mu?
        member_count = await self.bot.fetchval(
            "SELECT COUNT(*) FROM team_members WHERE team_id = ?",
            team_data[0]
        )
        
        if member_count >= 5:
            return await inter.send(
                embed=error("Takım dolu! (Max 5 kişi)"),
                ephemeral=True
            )
        
        # Onay butonu gönder (PUBLIC olarak channel'a)
        view = ConfirmationButtons(kullanıcı.id)
        invite_embed = Embed(
            title="📨 Takım Daveti",
            description=f"{kullanıcı.mention}, **{team_data[1]}** takımına davet edildin!\n\nKaptan: {inter.author.mention}",
            color=Color.blue()
        )
        
        # Önce ephemeral onay
        await inter.send(
            embed=success(f"{kullanıcı.mention} kullanıcısına davet gönderildi!"),
            ephemeral=True
        )
        
        # Sonra public davet mesajı
        msg = await inter.channel.send(embed=invite_embed, view=view)
        await view.wait()
        
        if view.value:
            # Kabul edildi
            role = inter.guild.get_role(team_data[3])
            await kullanıcı.add_roles(role)
            
            await self.bot.execute(
                "INSERT INTO team_members(team_id, user_id) VALUES(?, ?)",
                team_data[0], kullanıcı.id
            )
            
            # Başarı mesajı göster ve sil
            await msg.edit(
                embed=success(f"{kullanıcı.mention} takıma katıldı!"),
                view=None
            )
            await msg.delete(delay=5)  # 5 saniye sonra sil
        else:
            # Red mesajı göster ve sil
            await msg.edit(
                embed=error(f"{kullanıcı.mention} daveti reddetti."),
                view=None
            )
            await msg.delete(delay=5)  # 5 saniye sonra sil

    
    @team_group.sub_command(name="ayrıl")
    async def leave_team(self, inter: disnake.ApplicationCommandInteraction):
        """Takımdan ayrıl"""
        await inter.response.defer(ephemeral=True)
        
        # Kullanıcının takımını bul
        team_data = await self.bot.fetchrow(
            """SELECT t.team_id, t.team_name, t.captain_id, t.role_id 
               FROM teams t 
               JOIN team_members tm ON t.team_id = tm.team_id 
               WHERE tm.user_id = ? AND t.guild_id = ?""",
            inter.author.id, inter.guild.id
        )
        
        if not team_data:
            return await inter.send(
                embed=error("Bir takımda değilsin!"),
                ephemeral=True
            )
        
        # Rolü kaldır
        role = inter.guild.get_role(team_data[3])
        if role:
            await inter.author.remove_roles(role)
        
        # Veritabanından çıkar
        await self.bot.execute(
            "DELETE FROM team_members WHERE team_id = ? AND user_id = ?",
            team_data[0], inter.author.id
        )
        
        # Kalan üye sayısı
        remaining_members = await self.bot.fetch(
            "SELECT user_id FROM team_members WHERE team_id = ?",
            team_data[0]
        )
        
        if not remaining_members:
            # Son üye, takımı sil
            if role:
                await role.delete()
            
            await self.bot.execute("DELETE FROM teams WHERE team_id = ?", team_data[0])
            await self.bot.execute("DELETE FROM team_stats WHERE team_id = ?", team_data[0])
            
            await inter.send(
                embed=success(f"**{team_data[1]}** takımından ayrıldın. Takım silindi (son üye)."),
                ephemeral=True
            )
        elif team_data[2] == inter.author.id:
            # Kaptan ayrıldı, yeni kaptan seç
            new_captain_id = remaining_members[0][0]
            await self.bot.execute(
                "UPDATE teams SET captain_id = ? WHERE team_id = ?",
                new_captain_id, team_data[0]
            )
            
            await inter.send(
                embed=success(f"**{team_data[1]}** takımından ayrıldın. Yeni kaptan: <@{new_captain_id}>"),
                ephemeral=True
            )
        else:
            await inter.send(
                embed=success(f"**{team_data[1]}** takımından ayrıldın."),
                ephemeral=True
            )
    
    @team_group.sub_command(name="dağıt")
    async def disband_team(self, inter: disnake.ApplicationCommandInteraction):
        """Takımı dağıt (sadece kaptan)"""
        await inter.response.defer(ephemeral=True)
        
        # Kullanıcının takımını bul
        team_data = await self.bot.fetchrow(
            """SELECT t.team_id, t.team_name, t.captain_id, t.role_id 
               FROM teams t 
               JOIN team_members tm ON t.team_id = tm.team_id 
               WHERE tm.user_id = ? AND t.guild_id = ?""",
            inter.author.id, inter.guild.id
        )
        
        if not team_data:
            return await inter.send(
                embed=error("Bir takımda değilsin!"),
                ephemeral=True
            )
        
        # Kaptan kontrolü
        if team_data[2] != inter.author.id:
            return await inter.send(
                embed=error("Sadece kaptan takımı dağıtabilir!"),
                ephemeral=True
            )
        
        # Onay iste
        view = ConfirmationButtons(inter.author.id)
        confirm_embed = Embed(
            title="⚠️ Takım Dağıtma Onayı",
            description=f"**{team_data[1]}** takımını dağıtmak istediğinden emin misin?\n\nBu işlem geri alınamaz!",
            color=Color.red()
        )
        
        await inter.send(embed=confirm_embed, view=view)
        await view.wait()
        
        if view.value:
            # Tüm üyelerden rolü kaldır
            members = await self.bot.fetch(
                "SELECT user_id FROM team_members WHERE team_id = ?",
                team_data[0]
            )
            
            role = inter.guild.get_role(team_data[3])
            if role:
                for member_data in members:
                    member = inter.guild.get_member(member_data[0])
                    if member:
                        await member.remove_roles(role)
                
                await role.delete()
            
            # Veritabanından sil
            await self.bot.execute("DELETE FROM teams WHERE team_id = ?", team_data[0])
            await self.bot.execute("DELETE FROM team_members WHERE team_id = ?", team_data[0])
            await self.bot.execute("DELETE FROM team_stats WHERE team_id = ?", team_data[0])
            
            await inter.edit_original_message(
                embed=success(f"**{team_data[1]}** takımı dağıtıldı."),
                view=None
            )
        else:
            await inter.edit_original_message(
                embed=error("İşlem iptal edildi."),
                view=None
            )
    
    @team_group.sub_command(name="bilgi")
    async def team_info(self, inter: disnake.ApplicationCommandInteraction, takım_adı: str = None):
        """
        Takım bilgilerini göster
        
        Parameters
        ----------
        takım_adı: Takım adı (boş bırakırsan kendi takımın)
        """
        await inter.response.defer()
        
        if takım_adı:
            # Belirtilen takımı bul
            team_data = await self.bot.fetchrow(
                "SELECT * FROM teams WHERE guild_id = ? AND team_name = ?",
                inter.guild.id, takım_adı
            )
        else:
            # Kullanıcının takımını bul
            team_data = await self.bot.fetchrow(
                """SELECT t.* FROM teams t 
                   JOIN team_members tm ON t.team_id = tm.team_id 
                   WHERE tm.user_id = ? AND t.guild_id = ?""",
                inter.author.id, inter.guild.id
            )
        
        if not team_data:
            return await inter.send(
                embed=error("Takım bulunamadı!"),
                ephemeral=True
            )
        
        # Üyeleri getir
        members = await self.bot.fetch(
            "SELECT user_id FROM team_members WHERE team_id = ?",
            team_data[0]
        )
        
        # İstatistikleri getir
        stats = await self.bot.fetchrow(
            "SELECT * FROM team_stats WHERE team_id = ?",
            team_data[0]
        )
        
        # Embed oluştur
        role = inter.guild.get_role(team_data[4])
        embed = Embed(
            title=f"🏆 {team_data[2]}",
            color=role.color if role else Color.blue()
        )
        
        embed.add_field(name="Takım ID", value=f"`{team_data[0]}`", inline=True)
        embed.add_field(name="Kaptan", value=f"<@{team_data[3]}>", inline=True)
        embed.add_field(name="Üye Sayısı", value=f"{len(members)}/5", inline=True)
        
        if stats:
            win_rate = (stats[1] / max(stats[1] + stats[2], 1)) * 100
            embed.add_field(name="Kazanma", value=str(stats[1]), inline=True)
            embed.add_field(name="Kaybetme", value=str(stats[2]), inline=True)
            embed.add_field(name="Win Rate", value=f"{win_rate:.1f}%", inline=True)
            embed.add_field(name="ELO", value=str(stats[3]), inline=True)
        
        # Üyeler
        member_list = "\n".join([f"<@{m[0]}>" for m in members])
        embed.add_field(name="Üyeler", value=member_list, inline=False)
        
        if role:
            embed.add_field(name="Rol", value=role.mention, inline=False)
        
        embed.set_footer(text=f"Oluşturulma: {team_data[5]}")
        
        await inter.send(embed=embed)
    
    @team_group.sub_command(name="liste")
    async def list_teams(self, inter: disnake.ApplicationCommandInteraction):
        """Sunucudaki tüm takımları listele"""
        await inter.response.defer()
        
        teams = await self.bot.fetch(
            "SELECT * FROM teams WHERE guild_id = ? ORDER BY team_name",
            inter.guild.id
        )
        
        if not teams:
            return await inter.send(
                embed=error("Bu sunucuda henüz takım yok!"),
                ephemeral=True
            )
        
        embed = Embed(
            title=f"🏆 Takımlar ({len(teams)})",
            color=Color.gold()
        )
        
        for team in teams:
            member_count = await self.bot.fetchval(
                "SELECT COUNT(*) FROM team_members WHERE team_id = ?",
                team[0]
            )
            
            stats = await self.bot.fetchrow(
                "SELECT wins, losses FROM team_stats WHERE team_id = ?",
                team[0]
            )
            
            win_loss = f"{stats[0]}W {stats[1]}L" if stats else "0W 0L"
            
            embed.add_field(
                name=team[2],
                value=f"Kaptan: <@{team[3]}>\nÜyeler: {member_count}/5\nSkor: {win_loss}",
                inline=True
            )
        
        await inter.send(embed=embed)


def setup(bot):
    bot.add_cog(Teams(bot))
