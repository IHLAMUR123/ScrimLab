import disnake
from disnake.ext import commands

class Oylama(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="oylama",
        description="Bir üstteki mesaja 1️⃣ ve 2️⃣ oylama ekler",
        default_member_permissions=disnake.Permissions(administrator=True)
    )
    async def oylama(self, inter: disnake.ApplicationCommandInteraction):
        channel = inter.channel

        # Son 2 mesajı al
        messages = [msg async for msg in channel.history(limit=2)]
        if len(messages) < 2:
            await inter.response.send_message(
                "Oylanacak mesaj bulunamadı.",
                ephemeral=True
            )
            return

        target_message = messages[1]

        await target_message.add_reaction("1️⃣")
        await target_message.add_reaction("2️⃣")

        await inter.response.send_message(
            "Oylama başlatıldı. 1️⃣ veya 2️⃣ ile oy verebilirsiniz.",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        if reaction.emoji not in ["1️⃣", "2️⃣"]:
            return

        message = reaction.message

        other_emoji = "2️⃣" if reaction.emoji == "1️⃣" else "1️⃣"


        # Tek oy kuralı
        for react in message.reactions:
            if react.emoji == other_emoji:
                await react.remove(user)
                break

def setup(bot):
    bot.add_cog(Oylama(bot))
