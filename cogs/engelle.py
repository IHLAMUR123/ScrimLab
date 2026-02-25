from disnake.ext.commands import Cog, slash_command, Param
from disnake import Member
from core.embeds import error, success

class EngelleCog(Cog):
    """
    🚫 Engelleme Sistemi
    """
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="engelle")
    async def engelle(
        self,
        ctx,
        kullanici: Member = Param(name="kullanıcı", description="Engellemek istediğin kullanıcı")
    ):
        """Belirtilen kullanıcıyı engelle - Mümkün olduğunca aynı takıma düşmezsiniz"""
        
        # DEFER EKLE - Timeout önlemek için
        await ctx.response.defer(ephemeral=True)
        
        # Kendini engelleme kontrolü
        if kullanici.id == ctx.author.id:
            return await ctx.edit_original_response(
                embed=error("Kendini engelleyemezsin!")
            )
        
        # Bot engelleme kontrolü
        if kullanici.bot:
            return await ctx.edit_original_response(
                embed=error("Botları engelleyemezsin!")
            )
        
        try:
            # Zaten engellenmiş mi kontrol et
            existing = await self.bot.fetchrow(
                "SELECT * FROM blocked_users WHERE guild_id = ? AND blocker_id = ? AND blocked_id = ?",
                ctx.guild.id, ctx.author.id, kullanici.id
            )
            
            if existing:
                return await ctx.edit_original_response(
                    embed=error(f"{kullanici.display_name} zaten engellenmiş!")
                )
            
            # Engelleme listesine ekle
            await self.bot.execute(
                "INSERT INTO blocked_users(guild_id, blocker_id, blocked_id) VALUES(?, ?, ?)",
                ctx.guild.id, ctx.author.id, kullanici.id
            )
            
            await ctx.edit_original_response(
                embed=success(
                    f"✅ {kullanici.display_name} engellendi!\n\n"
                    f"⚠️ **Not:** Mümkün olduğunca aynı takıma düşmeyeceksiniz. "
                    f"Ancak karşı takım doluysa veya uygun kombinasyon bulunamazsa "
                    f"sistem sizi yine de sıraya alacak."
                )
            )
        except Exception as e:
            await ctx.edit_original_response(
                embed=error(f"Bir hata oluştu: {str(e)}\n\n**Not:** Veritabanı tablolarının oluşturulduğundan emin ol!")
            )
            print(f"Engelle komutu hatası: {e}")

    @slash_command(name="engel-kaldir")
    async def engel_kaldir(
        self,
        ctx,
        kullanici: Member = Param(name="kullanıcı", description="Engelini kaldırmak istediğin kullanıcı")
    ):
        """Belirtilen kullanıcının engelini kaldır"""
        
        # DEFER EKLE
        await ctx.response.defer(ephemeral=True)
        
        try:
            # Engellenmiş mi kontrol et
            existing = await self.bot.fetchrow(
                "SELECT * FROM blocked_users WHERE guild_id = ? AND blocker_id = ? AND blocked_id = ?",
                ctx.guild.id, ctx.author.id, kullanici.id
            )
            
            if not existing:
                return await ctx.edit_original_response(
                    embed=error(f"{kullanici.display_name} zaten engelli değil!")
                )
            
            # Engeli kaldır
            await self.bot.execute(
                "DELETE FROM blocked_users WHERE guild_id = ? AND blocker_id = ? AND blocked_id = ?",
                ctx.guild.id, ctx.author.id, kullanici.id
            )
            
            await ctx.edit_original_response(
                embed=success(f"✅ {kullanici.display_name} engelinden kaldırıldı!")
            )
        except Exception as e:
            await ctx.edit_original_response(
                embed=error(f"Bir hata oluştu: {str(e)}\n\n**Not:** Veritabanı tablolarının oluşturulduğundan emin ol!")
            )
            print(f"Engel kaldır komutu hatası: {e}")

    @slash_command(name="engelli-liste")
    async def engelli_liste(self, ctx):
        """Engellediğin kullanıcıların listesini göster"""
        
        # DEFER EKLE
        await ctx.response.defer(ephemeral=True)
        
        try:
            blocked_users = await self.bot.fetch(
                "SELECT blocked_id FROM blocked_users WHERE guild_id = ? AND blocker_id = ?",
                ctx.guild.id, ctx.author.id
            )
            
            if not blocked_users:
                return await ctx.edit_original_response(
                    embed=success("Hiç engellenmiş kullanıcın yok.")
                )
            
            blocked_list = []
            for row in blocked_users:
                user = ctx.guild.get_member(row[0])
                if user:
                    blocked_list.append(f"• {user.display_name} ({user.mention})")
                else:
                    blocked_list.append(f"• Bilinmeyen Kullanıcı (ID: {row[0]})")
            
            from disnake import Embed, Color
            embed = Embed(
                title="🚫 Engelli Kullanıcılar",
                description="\n".join(blocked_list),
                color=Color.red()
            )
            embed.set_footer(text=f"Toplam {len(blocked_users)} kullanıcı engellendi")
            
            await ctx.edit_original_response(embed=embed)
        except Exception as e:
            await ctx.edit_original_response(
                embed=error(f"Bir hata oluştu: {str(e)}\n\n**Not:** Veritabanı tablolarının oluşturulduğundan emin ol!")
            )
            print(f"Engelli liste komutu hatası: {e}")

def setup(bot):
    bot.add_cog(EngelleCog(bot))
