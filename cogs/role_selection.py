import disnake
from disnake import Embed, Color, ui, ButtonStyle, SelectOption
from disnake.ext.commands import Cog, slash_command

LOL_RANKS = [
    "Iron", "Bronze", "Silver", "Gold", "Platinum",
    "Emerald", "Diamond", "Master", "Grandmaster", "Challenger"
]

LOL_ROLES = ["Top", "Jungle", "Mid", "ADC", "Support"]


# ===== RANK SELECT =====
class RankSelect(ui.Select):
    def __init__(self):
        options = [SelectOption(label=rank, value=rank, emoji="🏆") for rank in LOL_RANKS]
        super().__init__(
            placeholder="🏆 Rank seç",
            options=options,
            max_values=1,
            custom_id="persistent_rank_select"
        )

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)

        selected_rank = self.values[0]

        # Eski rank rollerini kaldır
        for rank in LOL_RANKS:
            role = disnake.utils.get(inter.guild.roles, name=rank)
            if role and role in inter.author.roles:
                await inter.author.remove_roles(role)

        # Yeni rank rolü
        new_role = disnake.utils.get(inter.guild.roles, name=selected_rank)
        if new_role:
            await inter.author.add_roles(new_role)

        await inter.send(
            embed=Embed(
                description=f"✅ `{selected_rank}` rank rolün verildi!",
                color=Color.green()
            ),
            ephemeral=True
        )


# ===== ROLE SELECT =====
class RoleSelect(ui.Select):
    def __init__(self):
        options = [
            SelectOption(label="Top", emoji="⚔️"),
            SelectOption(label="Jungle", emoji="🌲"),
            SelectOption(label="Mid", emoji="⚡"),
            SelectOption(label="ADC", emoji="🎯"),
            SelectOption(label="Support", emoji="🛡️")
        ]

        super().__init__(
            placeholder="🎮 Oynadığın roller (max 3)",
            options=options,
            max_values=3,
            custom_id="persistent_role_select"
        )

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)

        selected_roles = self.values

        # Eski roller
        for role_name in LOL_ROLES:
            role = disnake.utils.get(inter.guild.roles, name=role_name)
            if role and role in inter.author.roles:
                await inter.author.remove_roles(role)

        # Yeni roller
        for role_name in selected_roles:
            role = disnake.utils.get(inter.guild.roles, name=role_name)
            if role:
                await inter.author.add_roles(role)

        await inter.send(
            embed=Embed(
                description=f"✅ `{', '.join(selected_roles)}` rollerin verildi!",
                color=Color.green()
            ),
            ephemeral=True
        )


# ===== MATCH INFO BUTTON =====
class MatchInfoButton(ui.Button):
    def __init__(self):
        super().__init__(
            label="📢 Maç duyurularını aç / kapat",
            style=ButtonStyle.blurple,
            custom_id="persistent_matchinfo_btn"
        )

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)

        role = disnake.utils.get(inter.guild.roles, name="maç bilgi")

        if not role:
            return await inter.send(
                embed=Embed(description="❌ `maç bilgi` rolü bulunamadı.", color=Color.red()),
                ephemeral=True
            )

        if role in inter.author.roles:
            await inter.author.remove_roles(role)
            text = "🟠 Maç duyuru rolü kaldırıldı."
            color = Color.orange()
        else:
            await inter.author.add_roles(role)
            text = "🟣 Maç duyuru rolü verildi!"
            color = Color.purple()

        await inter.send(embed=Embed(description=text, color=color), ephemeral=True)


# ===== VIEW =====
class RolePanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # 🔥 Kalıcı
        self.add_item(RankSelect())
        self.add_item(RoleSelect())
        self.add_item(MatchInfoButton())


# ===== COG =====
class RolePanel(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="rol_panel")
    async def rol_panel(self, ctx):
        """Modern rol seçim panelini gönder"""

        embed = Embed(
            title="🌌 SCRIMLAB ROL PANELİ",
            description=(
                "**Rollerini buradan seçebilirsin.**\n\n"
                "🏆 Rank → oyun ligini seç\n"
                "🎮 Rol → oynadığın koridorlar\n"
                "📢 Maç duyuru → bildirim rolü\n\n"
                "_Bunlar Sadece Seni Tanımamız İçin.._"
            ),
            color=Color.from_rgb(88, 101, 242)
        )

        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text="Scrimlab • Rol sistemi aktif")

        # Reply değil → düz kanala gönder
        await ctx.channel.send(embed=embed, view=RolePanelView())


    # ===== Restart sonrası persistent fix =====
    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(RolePanelView())
        print("✅ Rol paneli persistent olarak yüklendi.")


def setup(bot):
    bot.add_cog(RolePanel(bot))
