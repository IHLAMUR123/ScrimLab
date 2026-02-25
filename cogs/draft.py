"""
LoL Draft Pick/Ban System
Integrated with existing lobby system
"""
import disnake
from disnake.ext import commands
from disnake import Embed, Color
import asyncio
from typing import List, Dict, Optional
from core.champion_data import champion_manager
from core.draft_view import DraftView


# Draft order (player indices 0-9)
DRAFT_ORDER = [
    # Ban Phase 1
    ('ban', 0), ('ban', 5), ('ban', 6), ('ban', 1), ('ban', 2), ('ban', 7),
    # Pick Phase 1
    ('pick', 0), ('pick', 5), ('pick', 6), ('pick', 1), ('pick', 2), ('pick', 7),
    # Ban Phase 2
    ('ban', 5), ('ban', 1), ('ban', 2), ('ban', 6),
    # Pick Phase 2
    ('pick', 5), ('pick', 1), ('pick', 2), ('pick', 6)
]


class DraftManager:
    def __init__(self, bot, channel, game_id, players):
        self.bot = bot
        self.channel = channel
        self.game_id = game_id
        self.players = players  # List of 10 player dicts: {user_id, team, role}
        
        self.current_step = 0
        self.banned_champions = []
        self.picked_champions = {}  # {user_id: champion_id}
        self.message: Optional[disnake.Message] = None
        self.view: Optional[DraftView] = None
        self.cancelled = False
        
    def get_current_player_id(self) -> int:
        """Get current player's user_id"""
        if self.current_step >= len(DRAFT_ORDER):
            return None
        _, player_idx = DRAFT_ORDER[self.current_step]
        return self.players[player_idx]['user_id']
    
    def get_current_action(self) -> str:
        """Get current action (ban/pick)"""
        if self.current_step >= len(DRAFT_ORDER):
            return "completed"
        action, _ = DRAFT_ORDER[self.current_step]
        return action
    
    def get_available_champions(self) -> List[dict]:
        """Get list of available champions (not banned/picked)"""
        all_champs = champion_manager.get_all_champions()
        used_ids = set(self.banned_champions + list(self.picked_champions.values()))
        return [c for c in all_champs if c['id'] not in used_ids]
    
    async def select_champion(self, champion_id: str, user_id: int) -> bool:
        """Process champion selection"""
        action = self.get_current_action()
        
        # Check if champion is available
        if champion_id in self.banned_champions or champion_id in self.picked_champions.values():
            return False
        
        # Process action
        if action == 'ban':
            self.banned_champions.append(champion_id)
        elif action == 'pick':
            self.picked_champions[user_id] = champion_id
        
        # Move to next step
        self.current_step += 1
        
        # Check if draft is complete
        if self.current_step >= len(DRAFT_ORDER):
            await self.complete_draft()
        
        return True
    
    def get_embed(self) -> Embed:
        """Generate current draft embed"""
        action = self.get_current_action()
        
        if action == "completed":
            return self._get_completed_embed()
        
        # Get current player
        current_player_id = self.get_current_player_id()
        current_player = next(p for p in self.players if p['user_id'] == current_player_id)
        
        # Determine phase
        if self.current_step < 6:
            phase = "🚫 BAN PHASE 1"
        elif self.current_step < 12:
            phase = "✅ PICK PHASE 1"
        elif self.current_step < 16:
            phase = "🚫 BAN PHASE 2"
        else:
            phase = "✅ PICK PHASE 2"
        
        embed = Embed(
            title=f"🎮 DRAFT - {phase}",
            description=f"**Sıra:** <@{current_player_id}> ({action.upper()})\n**Kalan Süre:** ⏱️ 30 saniye",
            color=Color.blue() if current_player['team'] == 'blue' else Color.red()
        )
        
        # Blue team
        blue_players = [p for p in self.players if p['team'] == 'blue']
        blue_text = ""
        for i, player in enumerate(blue_players, 1):
            pick = self.picked_champions.get(player['user_id'])
            if pick:
                champ = champion_manager.get_champion_by_id(pick)
                blue_text += f"{i}. **{champ['name']}**\n"
            else:
                blue_text += f"{i}. ❓\n"
        
        embed.add_field(
            name="🔵 MAVİ TAKIM",
            value=blue_text or "Henüz seçim yok",
            inline=True
        )
        
        # Red team
        red_players = [p for p in self.players if p['team'] == 'red']
        red_text = ""
        for i, player in enumerate(red_players, 1):
            pick = self.picked_champions.get(player['user_id'])
            if pick:
                champ = champion_manager.get_champion_by_id(pick)
                red_text += f"{i}. **{champ['name']}**\n"
            else:
                red_text += f"{i}. ❓\n"
        
        embed.add_field(
            name="🔴 KIRMIZI TAKIM",
            value=red_text or "Henüz seçim yok",
            inline=True
        )
        
        # Bans
        ban_text = ""
        for ban_id in self.banned_champions:
            champ = champion_manager.get_champion_by_id(ban_id)
            ban_text += f"~~{champ['name']}~~ "
        
        embed.add_field(
            name=f"🚫 BANLAR ({len(self.banned_champions)}/10)",
            value=ban_text or "Henüz ban yok",
            inline=False
        )
        
        
        embed.set_footer(text=f"Game ID: {self.game_id} | Adım {self.current_step + 1}/{len(DRAFT_ORDER)}")
        
        return embed
    
    async def get_champion_grid_file(self, page: int = 0) -> Optional[disnake.File]:
        """Generate champion grid image file for specific page"""
        try:
            available_champs = self.get_available_champions()
            if not available_champs:
                return None
            
            # Get IDs for current page (20 per page)
            start_idx = page * 20
            end_idx = min(start_idx + 20, len(available_champs))
            page_champs = available_champs[start_idx:end_idx]
            
            champ_ids = [c['id'] for c in page_champs]
            selected_ids = list(self.banned_champions) + list(self.picked_champions.values())
            
            # Generate grid image
            grid_img = await champion_manager.generate_champion_grid(champ_ids, selected_ids)
            
            # Create Discord file
            return disnake.File(grid_img, filename="champions.png")
        except Exception as e:
            print(f"❌ Champion grid oluşturulamadı: {e}")
            return None
    
    def _get_completed_embed(self) -> Embed:
        """Generate completed draft embed"""
        embed = Embed(
            title="✅ DRAFT TAMAMLANDI!",
            description="Tüm seçimler yapıldı. İyi oyunlar!",
            color=Color.green()
        )
        
        # Blue team picks
        blue_players = [p for p in self.players if p['team'] == 'blue']
        blue_text = ""
        for i, player in enumerate(blue_players, 1):
            pick = self.picked_champions.get(player['user_id'])
            champ = champion_manager.get_champion_by_id(pick)
            blue_text += f"{i}. <@{player['user_id']}> - **{champ['name']}**\n"
        
        embed.add_field(name="🔵 MAVİ TAKIM", value=blue_text, inline=True)
        
        # Red team picks
        red_players = [p for p in self.players if p['team'] == 'red']
        red_text = ""
        for i, player in enumerate(red_players, 1):
            pick = self.picked_champions.get(player['user_id'])
            champ = champion_manager.get_champion_by_id(pick)
            red_text += f"{i}. <@{player['user_id']}> - **{champ['name']}**\n"
        
        embed.add_field(name="🔴 KIRMIZI TAKIM", value=red_text, inline=True)
        
        # Bans
        ban_text = " • ".join([
            champion_manager.get_champion_by_id(b)['name'] 
            for b in self.banned_champions
        ])
        embed.add_field(name="🚫 BANLAR", value=ban_text, inline=False)
        
        return embed
    
    async def update_embed(self):
        """Update the draft message"""
        if self.message:
            await self.message.edit(embed=self.get_embed())
    
    async def complete_draft(self):
        """Complete the draft"""
        self.view.stop()
        await self.message.edit(
            embed=self._get_completed_embed(),
            view=None
        )
    
    async def cancel_draft(self, reason: str):
        """Cancel the draft"""
        self.cancelled = True
        if self.view:
            self.view.stop()
        
        cancel_embed = Embed(
            title="❌ DRAFT İPTAL EDİLDİ",
            description=reason,
            color=Color.red()
        )
        
        if self.message:
            await self.message.edit(embed=cancel_embed, view=None)


class Draft(commands.Cog):
    """🎮 LoL Draft Pick/Ban Sistemi"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_drafts: Dict[int, DraftManager] = {}  # {channel_id: DraftManager}
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Load champion data on bot start"""
        await champion_manager.load_champions()
    
    @commands.slash_command(name="draft")
    async def draft_group(self, inter):
        """Draft komutları"""
        pass
    
    @draft_group.sub_command(name="başlat")
    async def start_draft(self, inter: disnake.ApplicationCommandInteraction, test_mode: bool = False):
        """
        LoL draft pick/ban sistemini başlat
        
        Parameters
        ----------
        test_mode: 2 kişiyle test modu (her oyuncu 5 champion seçer)
        """
        await inter.response.defer()
        
        # Check if in lobby channel
        if not inter.channel.name.startswith("lobby-"):
            return await inter.send(
                embed=Embed(
                    title="❌ Hata",
                    description="Bu komut sadece lobi kanallarında kullanılabilir!",
                    color=Color.red()
                ),
                ephemeral=True
            )
        
        # Extract game_id from channel name
        game_id = inter.channel.name.replace("lobby-", "")
        
        # Check if draft already active
        if inter.channel.id in self.active_drafts:
            return await inter.send(
                embed=Embed(
                    title="❌ Hata",
                    description="Bu lobide zaten aktif bir draft var!",
                    color=Color.red()
                ),
                ephemeral=True
            )
        
        # Get players from database (FIXED: author_id not user_id)
        players_data = await self.bot.fetch(
            "SELECT author_id, team, role FROM game_member_data WHERE game_id = ? ORDER BY team, author_id",
            game_id
        )
        
        # Test mode: allow 2 players
        if test_mode:
            if not players_data or len(players_data) < 2:
                return await inter.send(
                    embed=Embed(
                        title="❌ Hata",
                        description=f"Test modu için en az 2 oyuncu gerekli! (Şu an: {len(players_data) if players_data else 0})",
                        color=Color.red()
                    ),
                    ephemeral=True
                )
            
            # Duplicate players to fill 10 slots
            # Player 1 plays as P1, P2, P3, P4, P5
            # Player 2 plays as P6, P7, P8, P9, P10
            blue_player = players_data[0]
            red_player = players_data[1] if len(players_data) > 1 else players_data[0]
            
            players = []
            # Blue team (5 copies of player 1)
            for i in range(5):
                players.append({'user_id': blue_player[0], 'team': 'blue', 'role': blue_player[2]})
            # Red team (5 copies of player 2)
            for i in range(5):
                players.append({'user_id': red_player[0], 'team': 'red', 'role': red_player[2]})
        else:
            # Normal mode: require 10 players
            if not players_data or len(players_data) != 10:
                return await inter.send(
                    embed=Embed(
                        title="❌ Hata",
                        description=f"Bu lobide 10 oyuncu olmalı! (Şu an: {len(players_data) if players_data else 0})\n\nTest için `/draft başlat test_mode:True` kullan.",
                        color=Color.red()
                    ),
                    ephemeral=True
                )
            
            # Convert to player list
            players = [
                {'user_id': p[0], 'team': p[1], 'role': p[2]}
                for p in players_data
            ]
        
        # Create draft manager
        draft_manager = DraftManager(self.bot, inter.channel, game_id, players)
        self.active_drafts[inter.channel.id] = draft_manager
        
        # Create view
        view = DraftView(draft_manager, timeout=30)
        draft_manager.view = view
        await view.update_components()
        
        # Send initial message with champion grid
        embed = draft_manager.get_embed()
        test_notice = "\n\n**🧪 TEST MODU AKTIF**" if test_mode else ""
        embed.description += test_notice
        
        # Generate champion grid image
        grid_file = await draft_manager.get_champion_grid_file()
        if grid_file:
            embed.set_image(url="attachment://champions.png")
            message = await inter.channel.send(embed=embed, file=grid_file, view=view)
        else:
            message = await inter.channel.send(embed=embed, view=view)
        
        draft_manager.message = message
        view.message = message
        
        await inter.send(f"✅ Draft başlatıldı!{' (Test Modu)' if test_mode else ''}", ephemeral=True)
        
        # Wait for completion or timeout
        await view.wait()
        
        # Cleanup
        if inter.channel.id in self.active_drafts:
            del self.active_drafts[inter.channel.id]



def setup(bot):
    bot.add_cog(Draft(bot))
