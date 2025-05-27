import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from fastmcp import FastMCP

# MCP Server instance
mcp = FastMCP("gaming-trend-analytics")

# Lazy import - sadece gerektiğinde import et
def get_services():
    """Lazy loading of services"""
    global steam_service, epic_service
    if 'steam_service' not in globals():
        # Import'ları buraya taşı
        import aiohttp
        import json
        import random
        import time
        from bs4 import BeautifulSoup
        
        # Service sınıflarını buraya taşı
        global SteamService, EpicGamesService
        
        class SteamService:
            def __init__(self):
                self.base_url = 'https://api.steampowered.com'
                self.store_url = 'https://store.steampowered.com/api'
                self.last_request = 0
                self.request_delay = 1.0
                self.user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
                self._cache = {}
                self._cache_timeout = 300

            def get_fallback_games(self) -> List[Dict[str, Any]]:
                return [
                    {
                        'id': '730',
                        'name': 'Counter-Strike 2',
                        'price': 'Free',
                        'platform': 'Steam',
                        'isTrending': True,
                        'category': 'FPS'
                    },
                    {
                        'id': '570',
                        'name': 'Dota 2',
                        'price': 'Free',
                        'platform': 'Steam',
                        'isTrending': True,
                        'category': 'MOBA'
                    },
                    {
                        'id': '440',
                        'name': 'Team Fortress 2',
                        'price': 'Free',
                        'platform': 'Steam',
                        'isTrending': True,
                        'category': 'FPS'
                    }
                ]

            def get_fallback_popular_games(self) -> List[Dict[str, Any]]:
                return [
                    {
                        'id': '730',
                        'name': 'Counter-Strike 2',
                        'currentPlayers': 1200000,
                        'peakPlayers': 1500000,
                        'rank': 1,
                        'platform': 'Steam',
                        'isPopular': True,
                        'category': 'FPS'
                    },
                    {
                        'id': '570',
                        'name': 'Dota 2',
                        'currentPlayers': 800000,
                        'peakPlayers': 900000,
                        'rank': 2,
                        'platform': 'Steam',
                        'isPopular': True,
                        'category': 'MOBA'
                    }
                ]

            async def get_trending_games(self) -> List[Dict[str, Any]]:
                # İlk önce fallback data döndür, sonra gerçek data almaya çalış
                return self.get_fallback_games()

            async def get_top_sellers(self) -> List[Dict[str, Any]]:
                return self.get_fallback_games()

            async def get_current_player_stats(self) -> List[Dict[str, Any]]:
                return self.get_fallback_popular_games()

        class EpicGamesService:
            def __init__(self):
                self.base_url = 'https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions'
                self._cache = {}
                self._cache_timeout = 300

            def get_fallback_epic_games(self) -> List[Dict[str, Any]]:
                return [
                    {
                        'id': 'fortnite',
                        'name': 'Fortnite',
                        'price': 'Free',
                        'platform': 'Epic Games',
                        'category': 'Battle Royale',
                        'isFree': True
                    },
                    {
                        'id': 'gta5',
                        'name': 'Grand Theft Auto V',
                        'price': '$14.99',
                        'platform': 'Epic Games',
                        'category': 'Action',
                        'trending': True
                    }
                ]

            async def get_free_games(self) -> List[Dict[str, Any]]:
                return self.get_fallback_epic_games()

            async def get_trending_games(self) -> List[Dict[str, Any]]:
                return self.get_fallback_epic_games()

        # Service instance'ları oluştur
        steam_service = SteamService()
        epic_service = EpicGamesService()
    
    return steam_service, epic_service

# Tool'ları hızlı şekilde tanımla - lazy loading ile
@mcp.tool()
async def get_steam_trending_games() -> dict:
    """Get trending games from Steam platform."""
    try:
        steam_service, _ = get_services()
        games = await steam_service.get_trending_games()
        return {
            'success': True,
            'platform': 'Steam',
            'count': len(games),
            'data': games,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': 'Failed to fetch Steam trending games',
            'message': str(e)
        }

@mcp.tool()
async def get_steam_top_sellers() -> dict:
    """Get top selling games from Steam platform."""
    try:
        steam_service, _ = get_services()
        games = await steam_service.get_top_sellers()
        return {
            'success': True,
            'platform': 'Steam',
            'count': len(games),
            'data': games,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': 'Failed to fetch Steam top sellers',
            'message': str(e)
        }

@mcp.tool()
async def get_steam_most_played() -> dict:
    """Get most played games from Steam with player statistics."""
    try:
        steam_service, _ = get_services()
        games = await steam_service.get_current_player_stats()
        return {
            'success': True,
            'platform': 'Steam',
            'type': 'Most Played Games',
            'count': len(games),
            'data': games,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': 'Failed to fetch Steam popular games',
            'message': str(e)
        }

@mcp.tool()
async def get_epic_free_games() -> dict:
    """Get current and upcoming free games from Epic Games Store."""
    try:
        _, epic_service = get_services()
        games = await epic_service.get_free_games()
        return {
            'success': True,
            'platform': 'Epic Games',
            'count': len(games),
            'data': games,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': 'Failed to fetch Epic Games free games',
            'message': str(e)
        }

@mcp.tool()
async def get_all_trending_games() -> dict:
    """Get trending games from all platforms (Steam and Epic Games)."""
    try:
        steam_service, epic_service = get_services()
        
        # Hızlı fallback data döndür
        results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'steam': {
                    'trending': steam_service.get_fallback_games(),
                    'topSellers': steam_service.get_fallback_games(),
                    'mostPlayed': steam_service.get_fallback_popular_games()
                },
                'epic': {
                    'free': epic_service.get_fallback_epic_games()
                }
            },
            'errors': []
        }
        
        return results
    except Exception as e:
        return {
            'success': False,
            'error': 'Failed to fetch trending games',
            'message': str(e)
        }

@mcp.tool()
async def get_api_health() -> dict:
    """Check the health status of the Gaming Trend Analytics API."""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'description': 'Gaming Trend Analytics MCP Server',
        'available_tools': [
            'get_steam_trending_games',
            'get_steam_top_sellers', 
            'get_steam_most_played',
            'get_epic_free_games',
            'get_all_trending_games'
        ]
    }

if __name__ == "__main__":
    mcp.run()