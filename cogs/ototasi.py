import disnake
from disnake.ext import commands
import asyncio

class OtoTasi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.processing = set()

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
                           
        if not isinstance(channel, disnake.VoiceChannel):
            return

        c_name = channel.name

                            
        if not (c_name.startswith("Kırmızı Takım") or c_name.startswith("Mavi Takım")):
            return

        if channel.id in self.processing:
            return

        self.processing.add(channel.id)

        try:
                                     
            await asyncio.sleep(6)

            base_name = c_name.split(":")[0]                                  

                          
            for attempt in range(2):
                members_to_move = []

                for member in channel.guild.members:
                                    
                    if member.bot:
                        continue

                                   
                    if not member.voice:
                        continue

                                            
                    if member.voice.channel and member.voice.channel.id == channel.id:
                        continue

                                                                          
                    has_match = any(role.name.startswith(base_name) for role in member.roles)
                    if has_match:
                        members_to_move.append(member)

                      
                for i, member in enumerate(members_to_move):
                    try:
                        await member.move_to(channel)
                        print(f"[BAŞARILI] {member.display_name} -> {c_name} odasına taşındı")

                                     
                        if (i + 1) % 2 == 0:
                            await asyncio.sleep(1)

                    except disnake.HTTPException as e:
                                    
                        retry_after = getattr(e, "retry_after", 20)
                        print(f"[RATE LIMIT] {retry_after} sn bekleniyor...")
                        await asyncio.sleep(retry_after)
                        try:
                            await member.move_to(channel)
                            print(f"[RETRY] {member.display_name} taşındı")
                        except Exception as retry_err:
                            print(f"[HATA] retry patladı: {retry_err}")

                    except disnake.Forbidden:
                        print(f"[İZİN HATASI] {member.display_name} taşınamadı")
                    except Exception as e:
                        print(f"[GENEL HATA] {member.display_name}: {e}")

                                                                
                if not members_to_move:
                    break

                                                     
                await asyncio.sleep(5)

        finally:
            self.processing.discard(channel.id)

def setup(bot):
    bot.add_cog(OtoTasi(bot))
