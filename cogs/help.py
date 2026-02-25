from disnake import Color, Embed
from disnake.ext.commands import Cog, slash_command, command
from disnake import ui, ButtonStyle

# Dinamik Buton Sınıfı
class DinamikButon(ui.Button):
    def __init__(self, bot, ctx, etiket, emoji, embed):
        self.bot = bot
        self.ctx = ctx
        self.embed = embed
        super().__init__(style=ButtonStyle.gray, label=etiket, emoji=emoji)

    async def callback(self, inter):
        await inter.response.defer()
        await inter.edit_original_message(embed=self.embed)

# Dinamik Buton Görünümü
class DinamikButonlar(ui.View):
    def __init__(self, bot, ctx, etiketler, emojiler, embedler):
        super().__init__(timeout=300.0)
        for i, etiket in enumerate(etiketler):
            if i < len(emojiler) and i < len(embedler):
                self.add_item(DinamikButon(bot, ctx, etiket, emojiler[i], embedler[i]))

# Yardım Cog'u
class Yardim(Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cog açıklaması; emoji ve başlık şeklinde olacak (Örn: "📔;Yardım")
        self.description = "📔;Yardım Menüsü"

    async def yardim_menu(self, ctx):
        ana_embed = Embed(
            title="📔 Yardım Menüsü",
            description=(
                f"Merhaba! Aşağıdan komutları inceleyebilirsin.\n"
                f"\n📶 Bot Gecikmesi: {round(self.bot.latency * 1000)}ms\n"
                f"💡 Komutlar kategorilere ayrılmıştır, butonlardan geçiş yapabilirsiniz."
            ),
            color=Color.blurple(),
        )

        embedler = [ana_embed]
        etiketler = ["Ana Sayfa"]
        emojiler = ["🏠"]

        for cmd in self.bot.slash_commands:
            # Hata Önleyici Kontroller
            if not cmd.cog or not hasattr(cmd.cog, 'description') or not cmd.cog.description:
                continue
            if ";" not in cmd.cog.description:
                continue
            if cmd.cog.qualified_name in ["Yardim", "Etkinlikler", "Geliştirici"]:
                continue
            if not cmd.body.description:
                continue

            # Cog açıklamasını parçala
            parts = cmd.cog.description.split(";")
            emoji = parts[0].strip()
            baslik = parts[1].strip()

            # Embed listesinde bu kategori var mı kontrol
            hedef_embed = next((x for x in embedler if x.title == f"{emoji} {baslik}"), None)

            if hedef_embed is None:
                yeni_embed = Embed(
                    title=f"{emoji} {baslik}",
                    description="",
                    color=Color.blurple()
                )
                embedler.append(yeni_embed)
                etiketler.append(baslik)
                emojiler.append(emoji)
                hedef_embed = yeni_embed

            # Komut açıklamasını ekle
            if len(cmd.children):
                alt_komutlar = "\n".join(f"• `/{cmd.qualified_name} {x.name}`" for x in cmd.children.values())
                embed_aciklama = f"\n\n**/{cmd.qualified_name}**\n{alt_komutlar}"
            else:
                embed_aciklama = f"\n`/{cmd.qualified_name}` - {cmd.body.description}"
            
            hedef_embed.description += embed_aciklama

        await ctx.send(
            embed=embedler[0],
            view=DinamikButonlar(self.bot, ctx, etiketler, emojiler, embedler)
        )

    @slash_command(name="yardım", description="Tüm komutları ve özellikleri listeler.")
    async def yardim_slash(self, ctx):
        await self.yardim_menu(ctx)

    @command(name="yardım")
    async def yardim_text(self, ctx):
        await self.yardim_menu(ctx)

def setup(bot):
    bot.add_cog(Yardim(bot))
