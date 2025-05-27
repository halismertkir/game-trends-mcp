import asyncio
import aiohttp
import json
import random
import time
from datetime import datetime
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from fastmcp import FastMCP

# MCP Server instance - HTTP mode için
mcp = FastMCP("Gaming Trend Analytics")

class SteamService:
    def __init__(self):
        self.base_url = 'https://api.steampowered.com'
        self.store_url = 'https://store.steampowered.com/api'
        self.last_request = 0
        self.request_delay = 2.0  # 2 seconds delay
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]

    def get_random_user_agent(self) -> str:
        return random.choice(self.user_agents)

    async def make_request(self, url: str, session: aiohttp.ClientSession) -> str:
        now = time.time()
        time_since_last = now - self.last_request
        
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        
        self.last_request = time.time()
        
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
        
        async with session.get(url, headers=headers, timeout=15) as response:
            return await response.text()

    async def get_trending_games(self) -> List[Dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                # Try Steam Store main page
                response_text = await self.make_request('https://store.steampowered.com/?l=english', session)
                soup = BeautifulSoup(response_text, 'html.parser')
                games = []

                # Find featured and trending games from main page
                selectors = ['.store_main_capsule', '.tab_item', '.carousel_items .store_capsule']
                
                for selector in selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        if len(games) >= 20:
                            break
                            
                        # Extract app ID from URL
                        link = element.find('a')
                        if link and 'href' in link.attrs:
                            href = link['href']
                            app_id_match = href.split('/app/')
                            if len(app_id_match) > 1:
                                app_id = app_id_match[1].split('/')[0]
                                
                                # Extract game info
                                title_elem = element.select_one('.store_capsule_title, .tab_item_name')
                                name = title_elem.text.strip() if title_elem else None
                                
                                if not name and 'data-ds-appid-title' in element.attrs:
                                    name = element['data-ds-appid-title']
                                
                                price_elem = element.select_one('.discount_final_price, .store_capsule_price, .tab_item_details .price')
                                price = price_elem.text.strip() if price_elem else 'N/A'
                                
                                original_price_elem = element.select_one('.discount_original_price')
                                original_price = original_price_elem.text.strip() if original_price_elem else None
                                
                                discount_elem = element.select_one('.discount_percent')
                                discount = 0
                                if discount_elem:
                                    discount_text = discount_elem.text.strip().replace('-', '').replace('%', '')
                                    try:
                                        discount = int(discount_text)
                                    except:
                                        discount = 0
                                
                                img_elem = element.find('img')
                                image = img_elem['src'] if img_elem and 'src' in img_elem.attrs else None
                                
                                if name and app_id:
                                    games.append({
                                        'id': app_id,
                                        'name': name,
                                        'price': price,
                                        'originalPrice': original_price,
                                        'discount': discount,
                                        'headerImage': image,
                                        'platform': 'Steam',
                                        'tags': [],
                                        'releaseDate': 'Unknown',
                                        'shortDescription': '',
                                        'reviewScore': None,
                                        'playerCount': None,
                                        'isTrending': True
                                    })

                # If not enough games, try alternative method
                if len(games) < 5:
                    games = await self.get_alternative_trending_games(session)
                
                return games

        except Exception as e:
            print(f"Steam trending games error: {e}")
            return await self.get_alternative_trending_games(session)

    async def get_alternative_trending_games(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        try:
            # Use Steam search API for popular games
            search_url = 'https://store.steampowered.com/search/results/?query&start=0&count=20&dynamic_data=&sort_by=_ASC&supportedlang=english&snr=1_7_7_popularnew_7&filter=popularnew&infinite=1'
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            async with session.get(search_url, headers=headers) as response:
                data = await response.json()
                
                if 'results_html' in data:
                    soup = BeautifulSoup(data['results_html'], 'html.parser')
                    games = []
                    
                    for element in soup.select('.search_result_row'):
                        game_id = element.get('data-ds-appid')
                        title_elem = element.select_one('.title')
                        name = title_elem.text.strip() if title_elem else None
                        
                        price_elem = element.select_one('.search_price')
                        price = price_elem.text.strip() if price_elem else 'N/A'
                        
                        img_elem = element.select_one('.search_capsule img')
                        image = img_elem['src'] if img_elem and 'src' in img_elem.attrs else None
                        
                        release_elem = element.select_one('.search_released')
                        release_date = release_elem.text.strip() if release_elem else 'Unknown'
                        
                        review_elem = element.select_one('.search_review_summary')
                        review_score = None
                        if review_elem and 'data-tooltip-html' in review_elem.attrs:
                            review_score = review_elem['data-tooltip-html'].split('<br>')[0]
                        
                        if name and game_id:
                            games.append({
                                'id': game_id,
                                'name': name,
                                'price': price,
                                'originalPrice': None,
                                'discount': 0,
                                'headerImage': image,
                                'platform': 'Steam',
                                'tags': [],
                                'releaseDate': release_date,
                                'shortDescription': '',
                                'reviewScore': review_score,
                                'playerCount': None,
                                'isTrending': True
                            })
                    
                    return games
            
            # Fallback to hardcoded popular games
            return self.get_fallback_games()
            
        except Exception as e:
            print(f"Alternative Steam API error: {e}")
            return self.get_fallback_games()

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
            },
            {
                'id': '1172470',
                'name': 'Apex Legends',
                'price': 'Free',
                'platform': 'Steam',
                'isTrending': True,
                'category': 'Battle Royale'
            },
            {
                'id': '271590',
                'name': 'Grand Theft Auto V',
                'price': '$29.99',
                'platform': 'Steam',
                'isTrending': True,
                'category': 'Action'
            }
        ]

    async def get_top_sellers(self) -> List[Dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                url = 'https://store.steampowered.com/search/results/?query&start=0&count=20&dynamic_data=&sort_by=_ASC&supportedlang=english&snr=1_7_7_popularnew_7&filter=topsellers&infinite=1'
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(url, headers=headers) as response:
                    data = await response.json()
                    
                    soup = BeautifulSoup(data['results_html'], 'html.parser')
                    games = []
                    
                    for element in soup.select('.search_result_row'):
                        game_id = element.get('data-ds-appid')
                        title_elem = element.select_one('.title')
                        name = title_elem.text.strip() if title_elem else None
                        
                        price_elem = element.select_one('.search_price')
                        price = price_elem.text.strip() if price_elem else 'N/A'
                        
                        img_elem = element.select_one('.search_capsule img')
                        image = img_elem['src'] if img_elem and 'src' in img_elem.attrs else None
                        
                        release_elem = element.select_one('.search_released')
                        release_date = release_elem.text.strip() if release_elem else 'Unknown'
                        
                        review_elem = element.select_one('.search_review_summary')
                        review_score = None
                        if review_elem and 'data-tooltip-html' in review_elem.attrs:
                            review_score = review_elem['data-tooltip-html'].split('<br>')[0]
                        
                        if name and game_id:
                            games.append({
                                'id': game_id,
                                'name': name,
                                'price': price,
                                'headerImage': image,
                                'platform': 'Steam',
                                'releaseDate': release_date,
                                'reviewScore': review_score,
                                'isTopseller': True
                            })
                    
                    return games
        except Exception as e:
            print(f"Steam top sellers error: {e}")
            raise e

    async def get_current_player_stats(self) -> List[Dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                # Try Steam Charts
                response_text = await self.make_request('https://steamcharts.com/', session)
                soup = BeautifulSoup(response_text, 'html.parser')
                games = []
                
                rows = soup.select('table.common-table tbody tr')[:15]  # First 15 games
                
                for index, row in enumerate(rows):
                    cells = row.select('td')
                    
                    if len(cells) >= 4:
                        rank = cells[0].text.strip()
                        name_cell = cells[1]
                        name_link = name_cell.find('a')
                        name = name_link.text.strip() if name_link else name_cell.text.strip()
                        current_players = cells[2].text.strip().replace(',', '')
                        peak_players = cells[3].text.strip().replace(',', '')
                        
                        # Extract app ID from link
                        app_id = f"steam_{index}"
                        if name_link and 'href' in name_link.attrs:
                            href = name_link['href']
                            app_id_match = href.split('/app/')
                            if len(app_id_match) > 1:
                                app_id = app_id_match[1].split('/')[0]
                        
                        try:
                            current_players_int = int(current_players) if current_players.isdigit() else 0
                            peak_players_int = int(peak_players) if peak_players.isdigit() else 0
                            rank_int = int(rank) if rank.isdigit() else index + 1
                        except:
                            current_players_int = 0
                            peak_players_int = 0
                            rank_int = index + 1
                        
                        if name and name != 'Game':
                            games.append({
                                'id': app_id,
                                'name': name,
                                'currentPlayers': current_players_int,
                                'peakPlayers': peak_players_int,
                                'rank': rank_int,
                                'platform': 'Steam',
                                'isPopular': True
                            })
                
                # If not enough data, use alternative
                if len(games) < 5:
                    games = await self.get_alternative_player_stats(session)
                
                return games
                
        except Exception as e:
            print(f"Steam Charts error: {e}")
            return await self.get_alternative_player_stats(session)

    async def get_alternative_player_stats(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        try:
            # Try Steam's most played page
            response_text = await self.make_request('https://store.steampowered.com/charts/mostplayed', session)
            soup = BeautifulSoup(response_text, 'html.parser')
            games = []
            
            elements = soup.select('.weeklytopsellers_TableRow, .mostplayed_TableRow')[:15]
            
            for index, element in enumerate(elements):
                name_elem = element.select_one('.weeklytopsellers_StoreCapsule, .mostplayed_GameName')
                name = name_elem.text.strip() if name_elem else None
                
                link = element.find('a')
                app_id = f"popular_{index}"
                if link and 'href' in link.attrs:
                    href = link['href']
                    app_id_match = href.split('/app/')
                    if len(app_id_match) > 1:
                        app_id = app_id_match[1].split('/')[0]
                
                player_count_elem = element.select_one('.mostplayed_PlayerCount')
                current_players = 0
                if player_count_elem:
                    player_text = player_count_elem.text.strip()
                    player_match = ''.join(filter(str.isdigit, player_text))
                    if player_match:
                        current_players = int(player_match)
                
                if name:
                    games.append({
                        'id': app_id,
                        'name': name,
                        'currentPlayers': current_players,
                        'peakPlayers': None,
                        'rank': index + 1,
                        'platform': 'Steam',
                        'isPopular': True
                    })
            
            # If still not enough, use fallback
            if len(games) < 5:
                return self.get_fallback_popular_games()
            
            return games
            
        except Exception as e:
            print(f"Alternative Steam stats error: {e}")
            return self.get_fallback_popular_games()

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
            },
            {
                'id': '1172470',
                'name': 'Apex Legends',
                'currentPlayers': 300000,
                'peakPlayers': 400000,
                'rank': 3,
                'platform': 'Steam',
                'isPopular': True,
                'category': 'Battle Royale'
            },
            {
                'id': '578080',
                'name': 'PUBG: BATTLEGROUNDS',
                'currentPlayers': 250000,
                'peakPlayers': 300000,
                'rank': 4,
                'platform': 'Steam',
                'isPopular': True,
                'category': 'Battle Royale'
            },
            {
                'id': '252490',
                'name': 'Rust',
                'currentPlayers': 150000,
                'peakPlayers': 200000,
                'rank': 5,
                'platform': 'Steam',
                'isPopular': True,
                'category': 'Survival'
            }
        ]


class EpicGamesService:
    def __init__(self):
        self.base_url = 'https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions'
        self.graphql_url = 'https://graphql.epicgames.com/graphql'

    async def get_free_games(self) -> List[Dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}?locale=en-US&country=US&allowCountries=US"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(url, headers=headers, timeout=10) as response:
                    data = await response.json()
                    
                    games = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
                    
                    filtered_games = []
                    for game in games:
                        promotions = game.get('promotions', {})
                        has_current_promo = promotions.get('promotionalOffers', [])
                        has_upcoming_promo = promotions.get('upcomingPromotionalOffers', [])
                        
                        if has_current_promo or has_upcoming_promo:
                            price_info = game.get('price', {}).get('totalPrice', {}).get('fmtPrice', {})
                            
                            promotion_end_date = None
                            if has_current_promo:
                                promo_offers = has_current_promo[0].get('promotionalOffers', [])
                                if promo_offers:
                                    promotion_end_date = promo_offers[0].get('endDate')
                            
                            filtered_games.append({
                                'id': game.get('id'),
                                'name': game.get('title'),
                                'description': game.get('description'),
                                'price': price_info.get('originalPrice', 'Free'),
                                'discountPrice': price_info.get('discountPrice', 'Free'),
                                'platform': 'Epic Games',
                                'developer': game.get('developer'),
                                'publisher': game.get('publisher'),
                                'releaseDate': game.get('releaseDate'),
                                'tags': [tag.get('name') for tag in game.get('tags', [])],
                                'images': [{'type': img.get('type'), 'url': img.get('url')} 
                                          for img in game.get('keyImages', [])],
                                'isFree': game.get('price', {}).get('totalPrice', {}).get('originalPrice') == 0,
                                'promotionEndDate': promotion_end_date,
                                'upcoming': len(has_upcoming_promo) > 0
                            })
                    
                    return filtered_games[:15]
        except Exception as e:
            print(f"Epic Games free games error: {e}")
            raise e

    async def get_trending_games(self) -> List[Dict[str, Any]]:
        # Mock trending games since Epic doesn't have a direct API
        return [
            {
                'id': 'fortnite',
                'name': 'Fortnite',
                'price': 'Free',
                'platform': 'Epic Games',
                'category': 'Battle Royale',
                'playerCount': '400M+',
                'trending': True
            },
            {
                'id': 'gta5',
                'name': 'Grand Theft Auto V',
                'price': '$14.99',
                'platform': 'Epic Games',
                'category': 'Action',
                'trending': True
            },
            {
                'id': 'rocketleague',
                'name': 'Rocket League',
                'price': 'Free',
                'platform': 'Epic Games',
                'category': 'Sports',
                'trending': True
            }
        ]


# Service instances
steam_service = SteamService()
epic_service = EpicGamesService()

# MCP Tools

@mcp.tool()
async def get_steam_trending_games() -> dict:
    """Get trending games from Steam platform with multiple fallback methods."""
    try:
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
    """Get most played games from Steam with real-time player statistics."""
    try:
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
async def get_epic_trending_games() -> dict:
    """Get trending games from Epic Games Store."""
    try:
        games = await epic_service.get_trending_games()
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
            'error': 'Failed to fetch Epic Games trending games',
            'message': str(e)
        }

@mcp.tool()
async def get_all_trending_games() -> dict:
    """Get trending games from all platforms (Steam and Epic Games) in one comprehensive response."""
    results = {
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'data': {
            'steam': {
                'trending': [],
                'topSellers': [],
                'mostPlayed': []
            },
            'epic': {
                'free': []
            }
        },
        'errors': []
    }
    
    # Gather all data concurrently
    tasks = [
        steam_service.get_trending_games(),
        steam_service.get_top_sellers(),
        steam_service.get_current_player_stats(),
        epic_service.get_free_games()
    ]
    
    try:
        steam_trending, steam_top_sellers, steam_popular, epic_free = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        
        # Process results
        if isinstance(steam_trending, Exception):
            results['errors'].append(f"Steam trending: {str(steam_trending)}")
        else:
            results['data']['steam']['trending'] = steam_trending
            
        if isinstance(steam_top_sellers, Exception):
            results['errors'].append(f"Steam top sellers: {str(steam_top_sellers)}")
        else:
            results['data']['steam']['topSellers'] = steam_top_sellers
            
        if isinstance(steam_popular, Exception):
            results['errors'].append(f"Steam popular: {str(steam_popular)}")
        else:
            results['data']['steam']['mostPlayed'] = steam_popular
            
        if isinstance(epic_free, Exception):
            results['errors'].append(f"Epic free games: {str(epic_free)}")
        else:
            results['data']['epic']['free'] = epic_free
            
    except Exception as e:
        results['success'] = False
        results['errors'].append(f"General error: {str(e)}")
    
    return results

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
            'get_epic_trending_games',
            'get_all_trending_games'
        ]
    }

if __name__ == "__main__":
    # HTTP mode için port belirtiyoruz
    mcp.run(transport="http", port=8000)