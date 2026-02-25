"""
Discord UI components for LoL Draft system.
Includes View, Select Menu, and Buttons for champion selection.
"""
import disnake
from disnake.ui import View, Select, Button, button
from typing import List, Dict, Optional
import asyncio


class DraftView(View):
    def __init__(self, draft_manager, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.draft_manager = draft_manager
        self.message: Optional[disnake.Message] = None
        self.current_page = 0
        self.max_page = 0
        
    async def update_components(self):
        """Update buttons based on current state"""
        self.clear_items()
        
        # Get available champions (20 per page to fit 4 rows + 1 control row)
        champions = self.draft_manager.get_available_champions()
        self.max_page = (len(champions) - 1) // 20
        
        # Get current page champions
        start_idx = self.current_page * 20
        end_idx = min(start_idx + 20, len(champions))
        page_champions = champions[start_idx:end_idx]
        
        # Create champion selection buttons (5 per row, max 20 = 4 rows)
        for i, champ in enumerate(page_champions):
            btn = Button(
                label=champ['name'][:80],  # Discord limit
                style=disnake.ButtonStyle.secondary,
                custom_id=f"select_{champ['id']}",
                row=i // 5  # 5 buttons per row
            )
            btn.callback = self._make_champion_callback(champ['id'])
            self.add_item(btn)
        
        # Add pagination buttons (last row) - max 5 buttons per row
        prev_btn = Button(
            label=f"◀️ {self.current_page + 1}/{self.max_page + 1}",
            style=disnake.ButtonStyle.primary,
            disabled=(self.current_page == 0),
            custom_id="prev_page",
            row=4
        )
        prev_btn.callback = self.prev_page
        self.add_item(prev_btn)
        
        next_btn = Button(
            label=f"▶️ {self.current_page + 1}/{self.max_page + 1}",
            style=disnake.ButtonStyle.primary,
            disabled=(self.current_page >= self.max_page),
            custom_id="next_page",
            row=4
        )
        next_btn.callback = self.next_page
        self.add_item(next_btn)
        
        # Add cancel button
        cancel_btn = Button(
            label="❌ İptal",
            style=disnake.ButtonStyle.danger,
            custom_id="cancel_draft",
            row=4
        )
        cancel_btn.callback = self.cancel_draft
        self.add_item(cancel_btn)
    
    def _make_champion_callback(self, champion_id: str):
        """Create callback for champion selection button"""
        async def callback(inter: disnake.MessageInteraction):
            await inter.response.defer()
            
            # Check if it's the current player's turn
            if inter.user.id != self.draft_manager.get_current_player_id():
                return await inter.followup.send(
                    "❌ Şu an senin sıran değil!",
                    ephemeral=True
                )
            
            # Process selection
            success = await self.draft_manager.select_champion(champion_id, inter.user.id)
            
            if success:
                # Update embed and components
                self.current_page = 0  # Reset to first page
                await self.update_components()
                
                # Regenerate champion grid image
                embed = self.draft_manager.get_embed()
                grid_file = await self.draft_manager.get_champion_grid_file(self.current_page)
                
                if grid_file:
                    embed.set_image(url="attachment://champions.png")
                    await self.message.edit(embed=embed, file=grid_file, view=self)
                else:
                    await self.message.edit(embed=embed, view=self)
            else:
                await inter.followup.send(
                    "❌ Bu champion zaten seçildi veya banlandı!",
                    ephemeral=True
                )
        
        return callback
    
    async def update_champion_grid(self):
        """Update the champion grid in the main embed"""
        champions = self.draft_manager.get_available_champions()
        start_idx = self.current_page * 25
        end_idx = min(start_idx + 25, len(champions))
        page_champions = champions[start_idx:end_idx]
        
        # Get main embed
        embed = self.draft_manager.get_embed()
        
        # Add champion grid field
        grid_text = ""
        for i, champ in enumerate(page_champions):
            # Add champion icon as inline image link
            grid_text += f"[{champ['name']}]({champ['icon']}) "
            if (i + 1) % 5 == 0:  # New line every 5 champions
                grid_text += "\n"
        
        embed.add_field(
            name=f"📋 Championlar (Sayfa {self.current_page + 1}/{self.max_page + 1})",
            value=grid_text or "Champion yok",
            inline=False
        )
        
        return embed

    
    async def prev_page(self, inter: disnake.MessageInteraction):
        """Go to previous page"""
        await inter.response.defer()
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_components()
            
            # Regenerate grid for new page
            embed = self.draft_manager.get_embed()
            grid_file = await self.draft_manager.get_champion_grid_file(self.current_page)
            
            if grid_file:
                embed.set_image(url="attachment://champions.png")
                await self.message.edit(embed=embed, file=grid_file, view=self)
            else:
                await self.message.edit(embed=embed, view=self)
    
    async def next_page(self, inter: disnake.MessageInteraction):
        """Go to next page"""
        await inter.response.defer()
        if self.current_page < self.max_page:
            self.current_page += 1
            await self.update_components()
            
            # Regenerate grid for new page
            embed = self.draft_manager.get_embed()
            grid_file = await self.draft_manager.get_champion_grid_file(self.current_page)
            
            if grid_file:
                embed.set_image(url="attachment://champions.png")
                await self.message.edit(embed=embed, file=grid_file, view=self)
            else:
                await self.message.edit(embed=embed, view=self)
    
    async def cancel_draft(self, inter: disnake.MessageInteraction):
        """Cancel the draft (admin only)"""
        if not inter.user.guild_permissions.administrator:
            return await inter.response.send_message(
                "❌ Sadece adminler draft'ı iptal edebilir!",
                ephemeral=True
            )
        
        await inter.response.defer()
        self.stop()
        await self.draft_manager.cancel_draft("Admin tarafından iptal edildi")
    
    async def on_timeout(self):
        """Handle timeout"""
        await self.draft_manager.cancel_draft("⏱️ Süre doldu! Draft iptal edildi.")
