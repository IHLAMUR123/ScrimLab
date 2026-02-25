"""
Champion data management for LoL Draft system.
Fetches and caches champion data from Riot Data Dragon API.
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont
import io


class ChampionDataManager:
    def __init__(self):
        self.champions: Dict[str, dict] = {}
        self.version: str = ""
        self.base_url = "https://ddragon.leagueoflegends.com"
        self.icon_cache: Dict[str, Image.Image] = {}  # Cache downloaded icons
        
    async def load_champions(self):
        """Load champion data from Riot Data Dragon API"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get latest version
                async with session.get(f"{self.base_url}/api/versions.json") as resp:
                    versions = await resp.json()
                    self.version = versions[0]
                
                # Get champion data (Turkish)
                async with session.get(
                    f"{self.base_url}/cdn/{self.version}/data/tr_TR/champion.json"
                ) as resp:
                    data = await resp.json()
                    self.champions = data['data']
                    
            print(f"✅ {len(self.champions)} champion yüklendi (Patch {self.version})")
            return True
        except Exception as e:
            print(f"❌ Champion verisi yüklenemedi: {e}")
            return False
    
    def get_champion_icon_url(self, champion_id: str) -> str:
        """Get champion icon URL"""
        return f"{self.base_url}/cdn/{self.version}/img/champion/{champion_id}.png"
    
    async def download_champion_icon(self, champion_id: str) -> Optional[Image.Image]:
        """Download and cache champion icon"""
        if champion_id in self.icon_cache:
            return self.icon_cache[champion_id]
        
        try:
            url = self.get_champion_icon_url(champion_id)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        img = Image.open(io.BytesIO(img_data))
                        self.icon_cache[champion_id] = img
                        return img
        except Exception as e:
            print(f"❌ {champion_id} ikonu indirilemedi: {e}")
        return None
    
    async def generate_champion_grid(self, champion_ids: List[str], selected_ids: List[str] = None) -> io.BytesIO:
        """Generate a grid image of champion icons (4 rows x 5 cols)"""
        if selected_ids is None:
            selected_ids = []
        
        # Settings
        icon_size = 120
        cols = 5
        rows = 4
        padding = 5
        bg_color = (20, 25, 35)
        selected_color = (100, 100, 100, 128)  # Gray overlay for selected
        
        # Create canvas
        width = cols * icon_size + (cols + 1) * padding
        height = rows * icon_size + (rows + 1) * padding
        canvas = Image.new('RGB', (width, height), bg_color)
        
        # Download and place icons
        for idx, champ_id in enumerate(champion_ids[:20]):  # Max 20
            if idx >= 20:
                break
            
            row = idx // cols
            col = idx % cols
            x = col * icon_size + (col + 1) * padding
            y = row * icon_size + (row + 1) * padding
            
            # Download icon
            icon = await self.download_champion_icon(champ_id)
            if icon:
                # Resize to fit
                icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                
                # Apply gray overlay if selected/banned
                if champ_id in selected_ids:
                    overlay = Image.new('RGBA', (icon_size, icon_size), selected_color)
                    icon = icon.convert('RGBA')
                    icon = Image.alpha_composite(icon, overlay)
                
                # Paste onto canvas
                canvas.paste(icon.convert('RGB'), (x, y))
        
        # Convert to bytes
        buf = io.BytesIO()
        canvas.save(buf, format='PNG')
        buf.seek(0)
        return buf
        
    async def load_champions(self):
        """Load champion data from Riot Data Dragon API"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get latest version
                async with session.get(f"{self.base_url}/api/versions.json") as resp:
                    versions = await resp.json()
                    self.version = versions[0]
                
                # Get champion data (Turkish)
                async with session.get(
                    f"{self.base_url}/cdn/{self.version}/data/tr_TR/champion.json"
                ) as resp:
                    data = await resp.json()
                    self.champions = data['data']
                    
            print(f"✅ {len(self.champions)} champion yüklendi (Patch {self.version})")
            return True
        except Exception as e:
            print(f"❌ Champion verisi yüklenemedi: {e}")
            return False
    
    def get_champion_icon_url(self, champion_id: str) -> str:
        """Get champion icon URL"""
        return f"{self.base_url}/cdn/{self.version}/img/champion/{champion_id}.png"
    
    def get_all_champions(self) -> List[dict]:
        """Get all champions sorted by name"""
        champs = []
        for champ_id, champ_data in self.champions.items():
            champs.append({
                'id': champ_id,
                'name': champ_data['name'],
                'icon': self.get_champion_icon_url(f"{champ_id}.png")
            })
        return sorted(champs, key=lambda x: x['name'])
    
    def get_champion_by_id(self, champion_id: str) -> Optional[dict]:
        """Get champion data by ID"""
        if champion_id in self.champions:
            champ = self.champions[champion_id]
            return {
                'id': champion_id,
                'name': champ['name'],
                'icon': self.get_champion_icon_url(f"{champion_id}.png")
            }
        return None
    
    def search_champion(self, query: str) -> Optional[dict]:
        """Search champion by name (case-insensitive)"""
        query_lower = query.lower()
        for champ_id, champ_data in self.champions.items():
            if query_lower in champ_data['name'].lower():
                return {
                    'id': champ_id,
                    'name': champ_data['name'],
                    'icon': self.get_champion_icon_url(f"{champ_id}.png")
                }
        return None


# Global instance
champion_manager = ChampionDataManager()
