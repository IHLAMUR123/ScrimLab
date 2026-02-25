import disnake
from disnake.ext import commands
from disnake import Embed, Color, SelectOption
from datetime import datetime

class CustomRoleModal(disnake.ui.Modal):
    def __init__(self, bot, user, price):
        self.bot = bot
        self.user = user
        self.price = price
        
        components = [
            disnake.ui.TextInput(
                label="Rolün İsmi",
                placeholder="Örn: VIP Oyuncu",
                custom_id="role_name",
                style=disnake.TextInputStyle.short,
                max_length=32,
                min_length=1
            ),
            disnake.ui.TextInput(
                label="Rolün Rengi (HEX)",
                placeholder="Örn: #FF5733 veya ff5733",
                custom_id="role_color",
                style=disnake.TextInputStyle.short,
                max_length=7,
                min_length=6,
                required=False
            )
        ]
        super().__init__(title="🎨 Özel Rolünü Oluştur", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        role_name = inter.text_values["role_name"]
        role_color_input = inter.text_values.get("role_color", "").strip()
        
        # Renk işleme
        if role_color_input:
            # # işaretini kaldır
            role_color_input = role_color_input.replace("#", "")
            try:
                role_color = int(role_color_input, 16)
            except ValueError:
                return await inter.response.send_message(
                    "❌ Geçersiz renk kodu! Örnek: #FF5733",
                    ephemeral=True
                )
        else:
            role_color = 0x5865F2  # Varsayılan Discord mavi
        
        # Bakiye kontrolü
        bakiye = await self.bot.fetchval(
            "SELECT bakiye FROM users WHERE user_id = ?",
            self.user.id
        )
        
        if not bakiye or bakiye < self.price:
            return await inter.response.send_message(
                f"❌ Yetersiz bakiye! Gereken: `{self.price}` 💰\nMevcut: `{bakiye or 0}` 💰",
                ephemeral=True
            )
        
        try:
            # Rolü oluştur
            guild = inter.guild
            custom_role = await guild.create_role(
                name=role_name,
                color=disnake.Color(role_color),
                reason=f"Özel rol - {self.user.name} tarafından satın alındı"
            )
            
            # Kullanıcıya ver
            await self.user.add_roles(custom_role)
            
            # Bakiyeyi düş
            await self.bot.execute(
                "UPDATE users SET bakiye = bakiye - ? WHERE user_id = ?",
                self.price, self.user.id
            )
            
            # Database'e kaydet
            await self.bot.execute(
                "INSERT INTO custom_roles(guild_id, user_id, role_id, price) VALUES(?, ?, ?, ?)",
                guild.id, self.user.id, custom_role.id, self.price
            )
            
            embed = Embed(
                title="✨ Özel Rol Oluşturuldu!",
                description=f"**Rol:** {custom_role.mention}\n**Renk:** `#{role_color_input or '5865F2'}`\n**Ücret:** `{self.price}` 💰",
                color=custom_role.color,
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"Satın Alan: {self.user.display_name}", icon_url=self.user.display_avatar.url)
            
            await inter.response.send_message(embed=embed)
        
        except Exception as e:
            await inter.response.send_message(
                f"❌ Rol oluşturulurken hata: {e}",
                ephemeral=True
            )


class MarketSelect(disnake.ui.Select):
    def __init__(self, bot, market_items):
        self.bot = bot
        self.market_items = market_items
        
        options = []
        for item in market_items:
            role = item['role']
            price = item['price']
            
            options.append(
                SelectOption(
                    label=role.name,
                    value=str(role.id),
                    description=f"Fiyat: {price} 💰",
                    emoji="🎭"
                )
            )
        
        super().__init__(
            placeholder="🛒 Almak istediğin rolü seç...",
            options=options,
            custom_id="market:select"
        )

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)
        
        role_id = int(self.values[0])
        role = inter.guild.get_role(role_id)
        
        if not role:
            return await inter.followup.send("❌ Rol bulunamadı!", ephemeral=True)
        
        # Fiyatı bul
        price = None
        for item in self.market_items:
            if item['role'].id == role_id:
                price = item['price']
                break
        
        if price is None:
            return await inter.followup.send("❌ Fiyat bulunamadı!", ephemeral=True)
        
        # Kullanıcının bakiyesini kontrol et
        bakiye = await self.bot.fetchval(
            "SELECT bakiye FROM users WHERE user_id = ?",
            inter.author.id
        )
        
        if not bakiye or bakiye < price:
            return await inter.followup.send(
                f"❌ **Yetersiz Bakiye!**\n\n"
                f"📊 Gereken: `{price}` 💰\n"
                f"💳 Mevcut: `{bakiye or 0}` 💰\n"
                f"❗ Eksik: `{price - (bakiye or 0)}` 💰",
                ephemeral=True
            )
        
        # Zaten bu role sahip mi?
        if role in inter.author.roles:
            return await inter.followup.send(
                f"⚠️ Zaten {role.mention} rolüne sahipsin!",
                ephemeral=True
            )
        
        # Satın al
        try:
            await inter.author.add_roles(role)
            
            # Bakiyeyi düş
            await self.bot.execute(
                "UPDATE users SET bakiye = bakiye - ? WHERE user_id = ?",
                price, inter.author.id
            )
            
            # Satın alma kaydı
            await self.bot.execute(
                "INSERT INTO market_purchases(guild_id, user_id, role_id, price, purchased_at) VALUES(?, ?, ?, ?, ?)",
                inter.guild.id, inter.author.id, role_id, price, datetime.now()
            )
            
            yeni_bakiye = bakiye - price
            
            embed = Embed(
                title="✅ Satın Alma Başarılı!",
                description=f"🎭 **Rol:** {role.mention}\n💰 **Ücret:** `{price}`\n💳 **Kalan Bakiye:** `{yeni_bakiye}`",
                color=Color.green(),
                timestamp=datetime.now()
            )
            embed.set_footer(text=inter.author.display_name, icon_url=inter.author.display_avatar.url)
            
            await inter.followup.send(embed=embed, ephemeral=True)
            
            # Log kanalına bildir (varsa)
            log_channel_id = 1454210251887874128  # Bakiye log kanalı
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel:
                log_embed = Embed(
                    title="🛒 Market - Rol Satın Alındı",
                    description=f"**Kullanıcı:** {inter.author.mention}\n**Rol:** {role.mention}\n**Ücret:** `{price}` 💰",
                    color=Color.blurple(),
                    timestamp=datetime.now()
                )
                await log_channel.send(embed=log_embed)
        
        except Exception as e:
            await inter.followup.send(
                f"❌ Bir hata oluştu: {e}",
                ephemeral=True
            )


class MarketView(disnake.ui.View):
    def __init__(self, bot, market_items, custom_role_price):
        super().__init__(timeout=300)
        self.bot = bot
        self.custom_role_price = custom_role_price
        
        # Rol seçim menüsü
        if market_items:
            self.add_item(MarketSelect(bot, market_items))
    
    @disnake.ui.button(label="✨ Özel Rol Oluştur", style=disnake.ButtonStyle.blurple, emoji="🎨")
    async def custom_role_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Bakiye kontrolü
        bakiye = await self.bot.fetchval(
            "SELECT bakiye FROM users WHERE user_id = ?",
            inter.author.id
        )
        
        if not bakiye or bakiye < self.custom_role_price:
            return await inter.response.send_message(
                f"❌ **Yetersiz Bakiye!**\n\n"
                f"💰 Özel Rol Fiyatı: `{self.custom_role_price}`\n"
                f"💳 Senin Bakiyen: `{bakiye or 0}`\n"
                f"❗ Eksik: `{self.custom_role_price - (bakiye or 0)}`",
                ephemeral=True
            )
        
        # Zaten özel rolü var mı?
        existing = await self.bot.fetchrow(
            "SELECT role_id FROM custom_roles WHERE guild_id = ? AND user_id = ?",
            inter.guild.id, inter.author.id
        )
        
        if existing:
            role = inter.guild.get_role(existing[0])
            if role:
                return await inter.response.send_message(
                    f"⚠️ Zaten bir özel rolün var: {role.mention}\n"
                    f"Silmek için `/market deleteCustomRole` kullan.",
                    ephemeral=True
                )
        
        # Modal aç
        await inter.response.send_modal(
            CustomRoleModal(self.bot, inter.author, self.custom_role_price)
        )


class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Tablolar oluştur
        await self.bot.execute("""
            CREATE TABLE IF NOT EXISTS market_items(
                guild_id INTEGER,
                role_id INTEGER,
                price INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        
        await self.bot.execute("""
            CREATE TABLE IF NOT EXISTS custom_roles(
                guild_id INTEGER,
                user_id INTEGER,
                role_id INTEGER,
                price INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        
        await self.bot.execute("""
            CREATE TABLE IF NOT EXISTS market_purchases(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                role_id INTEGER,
                price INTEGER,
                purchased_at TIMESTAMP
            )
        """)
        
        await self.bot.execute("""
            CREATE TABLE IF NOT EXISTS market_settings(
                guild_id INTEGER PRIMARY KEY,
                custom_role_price INTEGER DEFAULT 500
            )
        """)

    @commands.slash_command(name="market")
    async def market(self, inter):
        """Market komutları"""
        pass

    @market.sub_command(name="liste")
    async def market_open(self, inter: disnake.ApplicationCommandInteraction):
        """🛒 Market'i aç ve roller satın al"""
        
        # Market rollerini al
        market_data = await self.bot.fetch(
            "SELECT role_id, price FROM market_items WHERE guild_id = ?",
            inter.guild.id
        )
        
        market_items = []
        for item in market_data:
            role = inter.guild.get_role(item[0])
            if role:
                market_items.append({
                    'role': role,
                    'price': item[1]
                })
        
        # Özel rol fiyatı
        custom_price_data = await self.bot.fetchrow(
            "SELECT custom_role_price FROM market_settings WHERE guild_id = ?",
            inter.guild.id
        )
        custom_role_price = custom_price_data[0] if custom_price_data else 500
        
        # Kullanıcının bakiyesi
        bakiye = await self.bot.fetchval(
            "SELECT bakiye FROM users WHERE user_id = ?",
            inter.author.id
        )
        
        # Embed oluştur
        embed = Embed(
            title="🛒 ROL MARKET",
            description=f"💳 **Bakiyen:** `{bakiye or 0}` 💰\n\n"
                       f"🎭 Roller aşağıdaki menüden seçilebilir.\n"
                       f"✨ Özel rol oluşturmak için butona bas!\n\n"
                       f"💎 **Özel Rol Fiyatı:** `{custom_role_price}` 💰",
            color=Color.gold(),
            timestamp=datetime.now()
        )
        
        if market_items:
            role_list = "\n".join([
                f"• {item['role'].mention} - `{item['price']}` 💰"
                for item in market_items
            ])
            embed.add_field(
                name="🎭 Mevcut Roller",
                value=role_list,
                inline=False
            )
        else:
            embed.add_field(
                name="⚠️ Uyarı",
                value="Market'te henüz rol yok! Admin `/market add` ile rol ekleyebilir.",
                inline=False
            )
        
        embed.set_footer(text="Maç kazanarak coin kazanabilirsin!", icon_url=inter.guild.icon.url if inter.guild.icon else None)
        
        view = MarketView(self.bot, market_items, custom_role_price)
        await inter.send(embed=embed, view=view)

    @market.sub_command(name="add")
    @commands.has_permissions(administrator=True)
    async def market_add(
        self,
        inter: disnake.ApplicationCommandInteraction,
        rol: disnake.Role,
        fiyat: int
    ):
        """Market'e rol ekle (Admin)"""
        
        if fiyat < 0:
            return await inter.send("❌ Fiyat 0'dan küçük olamaz!", ephemeral=True)
        
        # Zaten var mı kontrol et
        existing = await self.bot.fetchrow(
            "SELECT * FROM market_items WHERE guild_id = ? AND role_id = ?",
            inter.guild.id, rol.id
        )
        
        if existing:
            # Fiyatı güncelle
            await self.bot.execute(
                "UPDATE market_items SET price = ? WHERE guild_id = ? AND role_id = ?",
                fiyat, inter.guild.id, rol.id
            )
            await inter.send(f"✅ {rol.mention} rolünün fiyatı `{fiyat}` 💰 olarak güncellendi!")
        else:
            # Yeni ekle
            await self.bot.execute(
                "INSERT INTO market_items(guild_id, role_id, price) VALUES(?, ?, ?)",
                inter.guild.id, rol.id, fiyat
            )
            await inter.send(f"✅ {rol.mention} market'e `{fiyat}` 💰 fiyatıyla eklendi!")

    @market.sub_command(name="remove")
    @commands.has_permissions(administrator=True)
    async def market_remove(
        self,
        inter: disnake.ApplicationCommandInteraction,
        rol: disnake.Role
    ):
        """Market'ten rol çıkar (Admin)"""
        
        result = await self.bot.execute(
            "DELETE FROM market_items WHERE guild_id = ? AND role_id = ?",
            inter.guild.id, rol.id
        )
        
        await inter.send(f"✅ {rol.mention} market'ten kaldırıldı!")

    @market.sub_command(name="set_custom_price")
    @commands.has_permissions(administrator=True)
    async def market_set_custom_price(
        self,
        inter: disnake.ApplicationCommandInteraction,
        fiyat: int
    ):
        """Özel rol fiyatını ayarla (Admin)"""
        
        if fiyat < 0:
            return await inter.send("❌ Fiyat 0'dan küçük olamaz!", ephemeral=True)
        
        # Var mı kontrol et
        existing = await self.bot.fetchrow(
            "SELECT * FROM market_settings WHERE guild_id = ?",
            inter.guild.id
        )
        
        if existing:
            await self.bot.execute(
                "UPDATE market_settings SET custom_role_price = ? WHERE guild_id = ?",
                fiyat, inter.guild.id
            )
        else:
            await self.bot.execute(
                "INSERT INTO market_settings(guild_id, custom_role_price) VALUES(?, ?)",
                inter.guild.id, fiyat
            )
        
        await inter.send(f"✅ Özel rol fiyatı `{fiyat}` 💰 olarak ayarlandı!")

    @market.sub_command(name="özelrolüsil")
    async def market_delete_custom(self, inter: disnake.ApplicationCommandInteraction):
        """Özel rolünü sil ve para iadesi al (%50)"""
        
        custom_role_data = await self.bot.fetchrow(
            "SELECT role_id, price FROM custom_roles WHERE guild_id = ? AND user_id = ?",
            inter.guild.id, inter.author.id
        )
        
        if not custom_role_data:
            return await inter.send("❌ Özel rolün yok!", ephemeral=True)
        
        role = inter.guild.get_role(custom_role_data[0])
        refund = custom_role_data[1] // 2  # %50 iade
        
        try:
            # Rolü sil
            if role:
                await role.delete(reason=f"{inter.author.name} özel rolünü sildi")
            
            # Database'den sil
            await self.bot.execute(
                "DELETE FROM custom_roles WHERE guild_id = ? AND user_id = ?",
                inter.guild.id, inter.author.id
            )
            
            # Para iadesi
            await self.bot.execute(
                "UPDATE users SET bakiye = bakiye + ? WHERE user_id = ?",
                refund, inter.author.id
            )
            
            embed = Embed(
                title="🗑️ Özel Rol Silindi",
                description=f"**Rol:** {role.name if role else 'Silinmiş'}\n**İade:** `{refund}` 💰 (%50)",
                color=Color.orange()
            )
            await inter.send(embed=embed)
        
        except Exception as e:
            await inter.send(f"❌ Hata: {e}", ephemeral=True)

def setup(bot):
    bot.add_cog(Market(bot))
