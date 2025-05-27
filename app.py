import asyncio
import aiohttp
import json
import random
import time
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from fastmcp import FastMCP

# MCP Server instance - HTTP mode için
mcp = FastMCP("Gaming Trend Analytics")

class SteamService:
    def __init__(self):
        self.base_url = 'https://api.steampowered.com'
        self.store_url = 'https://store.steampowered.com'
        self.last_request = 0
        self.request_delay = 1.5  # Rate limiting
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]

    def get_random_user_agent(self) -> str:
        return random.choice(self.user_agents)

    async def make_request(self, url: str, session: aiohttp.ClientSession, is_json: bool = False) -> str:
        now = time.time()
        time_since_last = now - self.last_request
        
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        
        self.last_request = time.time()
        
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'application/json, text/plain, */*' if is_json else 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1' if not is_json else '0',
        }
        
        if is_json:
            headers['X-Requested-With'] = 'XMLHttpRequest'
        
        async with session.get(url, headers=headers, timeout=20) as response:
            if is_json:
                return await response.json()
            return await response.text()

    async def get_trending_games(self) -> List[Dict[str, Any]]:
        """Steam'den gerçek trending oyunları çeker - Featured & Recommended, New & Trending"""
        async with aiohttp.ClientSession() as session:
            games = []
            
            # 1. Featured & Recommended oyunları çek
            try:
                featured_games = await self._get_featured_games(session)
                games.extend(featured_games)
            except Exception as e:
                print(f"Featured games error: {e}")
            
            # 2. New & Trending oyunları çek
            try:
                trending_games = await self._get_new_trending_games(session)
                games.extend(trending_games)
            except Exception as e:
                print(f"New trending games error: {e}")
            
            # 3. Popular New Releases çek
            try:
                new_releases = await self._get_popular_new_releases(session)
                games.extend(new_releases)
            except Exception as e:
                print(f"New releases error: {e}")
            
            # 4. Eğer yeterli veri yoksa, Steam Charts'dan popüler oyunları çek
            if len(games) < 5:
                try:
                    popular_games = await self._get_steam_charts_popular(session)
                    games.extend(popular_games)
                except Exception as e:
                    print(f"Steam charts popular error: {e}")
            
            # 5. Hala yeterli veri yoksa, Steam'in global stats'ından çek
            if len(games) < 3:
                try:
                    stats_games = await self._get_steam_global_stats(session)
                    games.extend(stats_games)
                except Exception as e:
                    print(f"Steam global stats error: {e}")
            
            # Duplicate'ları temizle ve sınırla
            seen_ids = set()
            unique_games = []
            for game in games:
                if game['id'] not in seen_ids and len(unique_games) < 25:
                    seen_ids.add(game['id'])
                    unique_games.append(game)
            
            # Eğer hiç veri çekilemediyse hata fırlat
            if not unique_games:
                raise Exception("No trending games data could be retrieved from any source")
            
            return unique_games

    async def _get_featured_games(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Steam ana sayfasından featured oyunları çeker"""
        response_text = await self.make_request(f'{self.store_url}/?l=english', session)
        soup = BeautifulSoup(response_text, 'html.parser')
        games = []
        
        # Featured carousel'dan oyunları çek
        carousel_items = soup.select('.carousel_items .store_capsule, .featuredcapsule, .main_cluster_capsule')
        
        for item in carousel_items[:10]:  # İlk 10 featured oyun
            try:
                link = item.find('a')
                if not link or 'href' not in link.attrs:
                    continue
                    
                href = link['href']
                app_id_match = re.search(r'/app/(\d+)/', href)
                if not app_id_match:
                    continue
                    
                app_id = app_id_match.group(1)
                
                # Oyun adını çek
                title_elem = item.select_one('.store_capsule_title, .featuredcapsule_title')
                name = title_elem.text.strip() if title_elem else None
                
                if not name:
                    # Alt attribute'dan dene
                    img = item.find('img')
                    if img and 'alt' in img.attrs:
                        name = img['alt'].strip()
                
                # Fiyat bilgisini çek
                price_elem = item.select_one('.discount_final_price, .store_capsule_price')
                price = price_elem.text.strip() if price_elem else 'N/A'
                
                # İndirim bilgisini çek
                discount_elem = item.select_one('.discount_percent')
                discount = 0
                if discount_elem:
                    discount_text = discount_elem.text.strip().replace('-', '').replace('%', '')
                    try:
                        discount = int(discount_text)
                    except:
                        discount = 0
                
                # Resim URL'sini çek
                img_elem = item.find('img')
                image = img_elem['src'] if img_elem and 'src' in img_elem.attrs else None
                
                if name and app_id:
                    games.append({
                        'id': app_id,
                        'name': name,
                        'price': price,
                        'discount': discount,
                        'headerImage': image,
                        'platform': 'Steam',
                        'category': 'Featured',
                        'isTrending': True,
                        'source': 'featured'
                    })
                    
            except Exception as e:
                print(f"Error parsing featured game: {e}")
                continue
        
        return games

    async def _get_new_trending_games(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Steam'den New & Trending oyunları çeker"""
        # Steam'in New & Trending API endpoint'i
        url = f'{self.store_url}/search/results/?query&start=0&count=15&dynamic_data=&sort_by=_ASC&supportedlang=english&snr=1_7_7_popularnew_7&filter=popularnew&infinite=1'
        
        data = await self.make_request(url, session, is_json=True)
        
        if 'results_html' not in data:
            raise Exception("No results_html in Steam trending response")
            
        soup = BeautifulSoup(data['results_html'], 'html.parser')
        games = []
        
        for item in soup.select('.search_result_row'):
            try:
                app_id = item.get('data-ds-appid')
                if not app_id:
                    continue
                
                # Oyun adı
                title_elem = item.select_one('.title')
                name = title_elem.text.strip() if title_elem else None
                
                # Fiyat
                price_elem = item.select_one('.search_price')
                price = price_elem.text.strip() if price_elem else 'N/A'
                
                # Çıkış tarihi
                release_elem = item.select_one('.search_released')
                release_date = release_elem.text.strip() if release_elem else 'Unknown'
                
                # Review skoru
                review_elem = item.select_one('.search_review_summary')
                review_score = None
                if review_elem and 'data-tooltip-html' in review_elem.attrs:
                    tooltip = review_elem['data-tooltip-html']
                    # Review yüzdesini çıkar
                    percentage_match = re.search(r'(\d+)%', tooltip)
                    if percentage_match:
                        review_score = f"{percentage_match.group(1)}%"
                
                # Resim
                img_elem = item.select_one('.search_capsule img')
                image = img_elem['src'] if img_elem and 'src' in img_elem.attrs else None
                
                # Tag'ları çek
                tags = []
                tag_elems = item.select('.search_tag')
                for tag_elem in tag_elems:
                    tag_text = tag_elem.text.strip()
                    if tag_text:
                        tags.append(tag_text)
                
                if name and app_id:
                    games.append({
                        'id': app_id,
                        'name': name,
                        'price': price,
                        'headerImage': image,
                        'platform': 'Steam',
                        'releaseDate': release_date,
                        'reviewScore': review_score,
                        'tags': tags,
                        'category': 'New & Trending',
                        'isTrending': True,
                        'source': 'new_trending'
                    })
                    
            except Exception as e:
                print(f"Error parsing trending game: {e}")
                continue
        
        if not games:
            raise Exception("No trending games found in Steam response")
        
        return games

    async def _get_popular_new_releases(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Steam'den Popular New Releases çeker"""
        # Popular New Releases endpoint
        url = f'{self.store_url}/search/results/?query&start=0&count=10&dynamic_data=&sort_by=Released_DESC&supportedlang=english&filter=popularnew&infinite=1'
        
        data = await self.make_request(url, session, is_json=True)
        
        if 'results_html' not in data:
            raise Exception("No results_html in Steam new releases response")
            
        soup = BeautifulSoup(data['results_html'], 'html.parser')
        games = []
        
        for item in soup.select('.search_result_row'):
            try:
                app_id = item.get('data-ds-appid')
                if not app_id:
                    continue
                
                title_elem = item.select_one('.title')
                name = title_elem.text.strip() if title_elem else None
                
                price_elem = item.select_one('.search_price')
                price = price_elem.text.strip() if price_elem else 'N/A'
                
                release_elem = item.select_one('.search_released')
                release_date = release_elem.text.strip() if release_elem else 'Unknown'
                
                img_elem = item.select_one('.search_capsule img')
                image = img_elem['src'] if img_elem and 'src' in img_elem.attrs else None
                
                if name and app_id:
                    games.append({
                        'id': app_id,
                        'name': name,
                        'price': price,
                        'headerImage': image,
                        'platform': 'Steam',
                        'releaseDate': release_date,
                        'category': 'Popular New Release',
                        'isTrending': True,
                        'source': 'new_releases'
                    })
                    
            except Exception as e:
                print(f"Error parsing new release: {e}")
                continue
        
        return games

    async def _get_steam_charts_popular(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """SteamCharts'dan popüler oyunları çeker"""
        response_text = await self.make_request('https://steamcharts.com/', session)
        soup = BeautifulSoup(response_text, 'html.parser')
        games = []
        
        table = soup.find('table', class_='common-table')
        if not table:
            raise Exception("Could not find SteamCharts table")
        
        rows = table.select('tbody tr')[:10]  # İlk 10 oyun
        
        for index, row in enumerate(rows):
            try:
                cells = row.select('td')
                if len(cells) < 4:
                    continue
                
                # Oyun adı ve link
                name_cell = cells[1]
                name_link = name_cell.find('a')
                name = name_link.text.strip() if name_link else name_cell.text.strip()
                
                # App ID'yi link'ten çıkar
                app_id = f"chart_{index}"
                if name_link and 'href' in name_link.attrs:
                    href = name_link['href']
                    app_id_match = re.search(r'/app/(\d+)', href)
                    if app_id_match:
                        app_id = app_id_match.group(1)
                
                # Mevcut oyuncu sayısı
                current_text = cells[2].text.strip().replace(',', '')
                current_players = 0
                if current_text.isdigit():
                    current_players = int(current_text)
                
                if name and name != 'Game' and current_players > 0:
                    games.append({
                        'id': app_id,
                        'name': name,
                        'currentPlayers': current_players,
                        'platform': 'Steam',
                        'category': 'Popular',
                        'isTrending': True,
                        'source': 'steamcharts'
                    })
                    
            except Exception as e:
                print(f"Error parsing SteamCharts row: {e}")
                continue
        
        if not games:
            raise Exception("No games found in SteamCharts")
        
        return games

    async def _get_steam_global_stats(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Steam'in global stats sayfasından oyunları çeker"""
        response_text = await self.make_request(f'{self.store_url}/stats/', session)
        soup = BeautifulSoup(response_text, 'html.parser')
        games = []
        
        # Steam stats sayfasından oyunları çek
        stat_rows = soup.select('.player_count_row')
        
        for index, row in enumerate(stat_rows[:10]):
            try:
                name_elem = row.select_one('.gameLink')
                if not name_elem:
                    continue
                    
                name = name_elem.text.strip()
                
                # App ID'yi link'ten çıkar
                app_id = f"stats_{index}"
                if 'href' in name_elem.attrs:
                    href = name_elem['href']
                    app_id_match = re.search(r'/app/(\d+)', href)
                    if app_id_match:
                        app_id = app_id_match.group(1)
                
                # Player count
                count_elem = row.select_one('.currentServers')
                current_players = 0
                if count_elem:
                    count_text = count_elem.text.strip().replace(',', '')
                    if count_text.isdigit():
                        current_players = int(count_text)
                
                if name and current_players > 0:
                    games.append({
                        'id': app_id,
                        'name': name,
                        'currentPlayers': current_players,
                        'platform': 'Steam',
                        'category': 'Popular',
                        'isTrending': True,
                        'source': 'steam_global_stats'
                    })
                    
            except Exception as e:
                print(f"Error parsing Steam stats row: {e}")
                continue
        
        if not games:
            raise Exception("No games found in Steam global stats")
        
        return games

    async def get_top_sellers(self) -> List[Dict[str, Any]]:
        """Steam'den gerçek top seller oyunları çeker"""
        async with aiohttp.ClientSession() as session:
            # Steam Top Sellers API
            url = f'{self.store_url}/search/results/?query&start=0&count=20&dynamic_data=&sort_by=_ASC&supportedlang=english&filter=topsellers&infinite=1'
            
            data = await self.make_request(url, session, is_json=True)
            
            if 'results_html' not in data:
                raise Exception("No results_html in Steam top sellers response")
                
            soup = BeautifulSoup(data['results_html'], 'html.parser')
            games = []
            
            for index, item in enumerate(soup.select('.search_result_row')):
                try:
                    app_id = item.get('data-ds-appid')
                    if not app_id:
                        continue
                    
                    title_elem = item.select_one('.title')
                    name = title_elem.text.strip() if title_elem else None
                    
                    price_elem = item.select_one('.search_price')
                    price = price_elem.text.strip() if price_elem else 'N/A'
                    
                    # İndirim bilgisi
                    discount_elem = item.select_one('.search_discount span')
                    discount = 0
                    if discount_elem:
                        discount_text = discount_elem.text.strip().replace('-', '').replace('%', '')
                        try:
                            discount = int(discount_text)
                        except:
                            discount = 0
                    
                    # Review bilgisi
                    review_elem = item.select_one('.search_review_summary')
                    review_score = None
                    review_count = None
                    if review_elem and 'data-tooltip-html' in review_elem.attrs:
                        tooltip = review_elem['data-tooltip-html']
                        percentage_match = re.search(r'(\d+)%', tooltip)
                        count_match = re.search(r'([\d,]+)\s+user reviews', tooltip)
                        if percentage_match:
                            review_score = f"{percentage_match.group(1)}%"
                        if count_match:
                            review_count = count_match.group(1)
                    
                    release_elem = item.select_one('.search_released')
                    release_date = release_elem.text.strip() if release_elem else 'Unknown'
                    
                    img_elem = item.select_one('.search_capsule img')
                    image = img_elem['src'] if img_elem and 'src' in img_elem.attrs else None
                    
                    # Tag'ları çek
                    tags = []
                    tag_elems = item.select('.search_tag')
                    for tag_elem in tag_elems:
                        tag_text = tag_elem.text.strip()
                        if tag_text:
                            tags.append(tag_text)
                    
                    if name and app_id:
                        games.append({
                            'id': app_id,
                            'name': name,
                            'price': price,
                            'discount': discount,
                            'headerImage': image,
                            'platform': 'Steam',
                            'releaseDate': release_date,
                            'reviewScore': review_score,
                            'reviewCount': review_count,
                            'tags': tags,
                            'rank': index + 1,
                            'isTopSeller': True
                        })
                        
                except Exception as e:
                    print(f"Error parsing top seller: {e}")
                    continue
            
            if not games:
                raise Exception("No top sellers found in Steam response")
            
            return games

    async def get_current_player_stats(self) -> List[Dict[str, Any]]:
        """SteamCharts'dan gerçek player istatistiklerini çeker"""
        async with aiohttp.ClientSession() as session:
            try:
                # SteamCharts ana sayfası
                response_text = await self.make_request('https://steamcharts.com/', session)
                soup = BeautifulSoup(response_text, 'html.parser')
                games = []
                
                # Ana tablo satırlarını bul
                table = soup.find('table', class_='common-table')
                if not table:
                    # Alternatif olarak Steam'in kendi stats sayfasını dene
                    return await self._get_steam_stats_alternative(session)
                
                rows = table.select('tbody tr')[:20]  # İlk 20 oyun
                
                for index, row in enumerate(rows):
                    try:
                        cells = row.select('td')
                        if len(cells) < 4:
                            continue
                        
                        # Rank
                        rank_text = cells[0].text.strip()
                        rank = int(rank_text) if rank_text.isdigit() else index + 1
                        
                        # Oyun adı ve link
                        name_cell = cells[1]
                        name_link = name_cell.find('a')
                        name = name_link.text.strip() if name_link else name_cell.text.strip()
                        
                        # App ID'yi link'ten çıkar
                        app_id = f"chart_{index}"
                        if name_link and 'href' in name_link.attrs:
                            href = name_link['href']
                            app_id_match = re.search(r'/app/(\d+)', href)
                            if app_id_match:
                                app_id = app_id_match.group(1)
                        
                        # Mevcut oyuncu sayısı
                        current_text = cells[2].text.strip().replace(',', '')
                        current_players = 0
                        if current_text.isdigit():
                            current_players = int(current_text)
                        
                        # Peak oyuncu sayısı
                        peak_text = cells[3].text.strip().replace(',', '')
                        peak_players = 0
                        if peak_text.isdigit():
                            peak_players = int(peak_text)
                        
                        # 24 saat değişim (varsa)
                        change_24h = None
                        if len(cells) > 4:
                            change_text = cells[4].text.strip()
                            if change_text and change_text != '-':
                                change_24h = change_text
                        
                        if name and name != 'Game' and current_players > 0:
                            games.append({
                                'id': app_id,
                                'name': name,
                                'currentPlayers': current_players,
                                'peakPlayers': peak_players,
                                'change24h': change_24h,
                                'rank': rank,
                                'platform': 'Steam',
                                'isPopular': True,
                                'lastUpdated': datetime.now().isoformat()
                            })
                            
                    except Exception as e:
                        print(f"Error parsing player stats row: {e}")
                        continue
                
                if not games:
                    # SteamCharts'dan veri alınamazsa alternatif dene
                    return await self._get_steam_stats_alternative(session)
                
                return games
                
            except Exception as e:
                print(f"SteamCharts error: {e}")
                return await self._get_steam_stats_alternative(session)

    async def _get_steam_stats_alternative(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Steam'in kendi most played sayfasından veri çeker"""
        response_text = await self.make_request(f'{self.store_url}/stats/', session)
        soup = BeautifulSoup(response_text, 'html.parser')
        games = []
        
        # Steam stats sayfasından oyunları çek
        stat_rows = soup.select('.player_count_row')
        
        for index, row in enumerate(stat_rows[:15]):
            try:
                name_elem = row.select_one('.gameLink')
                if not name_elem:
                    continue
                    
                name = name_elem.text.strip()
                
                # App ID'yi link'ten çıkar
                app_id = f"stats_{index}"
                if 'href' in name_elem.attrs:
                    href = name_elem['href']
                    app_id_match = re.search(r'/app/(\d+)', href)
                    if app_id_match:
                        app_id = app_id_match.group(1)
                
                # Player count
                count_elem = row.select_one('.currentServers')
                current_players = 0
                if count_elem:
                    count_text = count_elem.text.strip().replace(',', '')
                    if count_text.isdigit():
                        current_players = int(count_text)
                
                if name and current_players > 0:
                    games.append({
                        'id': app_id,
                        'name': name,
                        'currentPlayers': current_players,
                        'rank': index + 1,
                        'platform': 'Steam',
                        'isPopular': True,
                        'source': 'steam_stats'
                    })
                    
            except Exception as e:
                print(f"Error parsing Steam stats row: {e}")
                continue
        
        if not games:
            raise Exception("No player statistics could be retrieved from any Steam source")
        
        return games


class EpicGamesService:
    def __init__(self):
        self.base_url = 'https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions'

    async def get_free_games(self) -> List[Dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}?locale=en-US&country=US&allowCountries=US"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(url, headers=headers, timeout=15) as response:
                data = await response.json()
                
                games = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
                
                if not games:
                    raise Exception("No games found in Epic Games response")
                
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
                
                if not filtered_games:
                    raise Exception("No free games with promotions found")
                
                return filtered_games[:15]

    async def get_trending_games(self) -> List[Dict[str, Any]]:
        """Epic Games Store'dan trending oyunları çeker (Epic'in public API'si sınırlı olduğu için web scraping)"""
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Epic Games Store ana sayfasından featured oyunları çek
            async with session.get('https://store.epicgames.com/en-US/', headers=headers, timeout=15) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                games = []
                
                # Epic'in featured game card'larını bul
                game_cards = soup.select('[data-testid*="offer"], .css-1myhtyb, .css-1jx3eyg')
                
                for index, card in enumerate(game_cards[:10]):
                    try:
                        # Oyun adını bul
                        name_elem = card.select_one('h3, [data-testid="offer-title"], .css-2ucwu')
                        name = name_elem.text.strip() if name_elem else None
                        
                        # Fiyat bilgisini bul
                        price_elem = card.select_one('[data-testid="price"], .css-119zqif')
                        price = price_elem.text.strip() if price_elem else 'N/A'
                        
                        # Link'i bul
                        link_elem = card.find('a')
                        game_url = None
                        if link_elem and 'href' in link_elem.attrs:
                            game_url = link_elem['href']
                        
                        # Resim URL'sini bul
                        img_elem = card.find('img')
                        image = img_elem['src'] if img_elem and 'src' in img_elem.attrs else None
                        
                        if name:
                            games.append({
                                'id': f'epic_{index}',
                                'name': name,
                                'price': price,
                                'platform': 'Epic Games',
                                'gameUrl': game_url,
                                'headerImage': image,
                                'category': 'Featured',
                                'trending': True
                            })
                            
                    except Exception as e:
                        print(f"Error parsing Epic game card: {e}")
                        continue
                
                if not games:
                    raise Exception("No trending games found on Epic Games Store")
                
                return games


# Service instances
steam_service = SteamService()
epic_service = EpicGamesService()

# MCP Tools (aynı kalıyor)

@mcp.tool()
async def get_steam_trending_games() -> dict:
    """Get real trending games from Steam platform with live data from multiple sources."""
    try:
        games = await steam_service.get_trending_games()
        return {
            'success': True,
            'platform': 'Steam',
            'type': 'Trending Games',
            'count': len(games),
            'data': games,
            'sources': ['featured', 'new_trending', 'new_releases', 'steamcharts', 'steam_stats'],
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
    """Get real top selling games from Steam platform with live sales data."""
    try:
        games = await steam_service.get_top_sellers()
        return {
            'success': True,
            'platform': 'Steam',
            'type': 'Top Sellers',
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
    """Get real-time most played games from Steam with live player statistics from SteamCharts."""
    try:
        games = await steam_service.get_current_player_stats()
        return {
            'success': True,
            'platform': 'Steam',
            'type': 'Most Played Games (Live Stats)',
            'count': len(games),
            'data': games,
            'source': 'SteamCharts + Steam Stats',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': 'Failed to fetch Steam player statistics',
            'message': str(e)
        }

@mcp.tool()
async def get_epic_free_games() -> dict:
    """Get current and upcoming free games from Epic Games Store with real promotion data."""
    try:
        games = await epic_service.get_free_games()
        return {
            'success': True,
            'platform': 'Epic Games',
            'type': 'Free Games',
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
            'type': 'Trending Games',
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
    """Get comprehensive real-time gaming data from all platforms (Steam and Epic Games)."""
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
                'free': [],
                'trending': []
            }
        },
        'errors': []
    }
    
    # Gather all data concurrently
    tasks = [
        steam_service.get_trending_games(),
        steam_service.get_top_sellers(),
        steam_service.get_current_player_stats(),
        epic_service.get_free_games(),
        epic_service.get_trending_games()
    ]
    
    try:
        steam_trending, steam_top_sellers, steam_popular, epic_free, epic_trending = await asyncio.gather(
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
            
        if isinstance(epic_trending, Exception):
            results['errors'].append(f"Epic trending: {str(epic_trending)}")
        else:
            results['data']['epic']['trending'] = epic_trending
            
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
        'version': '2.0.0',
        'description': 'Gaming Trend Analytics MCP Server - Real-time Steam & Epic Games data',
        'features': [
            'Real-time Steam trending games from multiple sources',
            'Live Steam top sellers with detailed metadata',
            'Live player statistics from SteamCharts',
            'Epic Games free games with promotions',
            'Epic Games trending games',
            'Comprehensive multi-platform data aggregation',
            'No mock data - all real-time sources'
        ],
        'available_tools': [
            'get_steam_trending_games',
            'get_steam_top_sellers', 
            'get_steam_most_played',
            'get_epic_free_games',
            'get_epic_trending_games',
            'get_all_trending_games'
        ]
    }

