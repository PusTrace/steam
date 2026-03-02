# parsers.py
import requests, logging
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple, Dict, Any
import urllib3
import re
import json
from urllib.parse import quote
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from core.utils import normalize_date


class SteamMarketParser:
    """Парсер данных Steam Market с кешированием в PostgreSQL"""

    STEAM_APPID = 730
    ORDERS_CACHE_DAYS = 1
    PRICES_CACHE_DAYS = 3
    MAX_RETRIES = 5
    RETRY_DELAY_RANGE = (60*60, 60*60*2)

    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/118.0.5993.118 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }

    def __init__(self, session: requests.Session, cookies: dict, db, loud_mode: bool = False):
        self.session = session
        self.session.cookies.update(cookies)
        self.db = db

        self.logger = logging.getLogger(__name__)
        
        self.skin_id: Optional[int] = None
        self.name: Optional[str] = None
        self.item_name_id: Optional[int] = None
        self.buy_price: Optional[float] = None
        self.orders_timestamp: Optional[datetime] = None
        self.history_timestamp: Optional[datetime] = None

        self._buy_orders: List[List] = []
        self._sell_orders: List[List] = []
        self._price_history: List[List] = []

    def load_skin(self, skin_info: Tuple) -> None:
        len_skin_info = len(skin_info)
        if len_skin_info == 7:
            self.skin_id, self.name, self.analysis_timestamp, self.appearance_date, self.item_name_id, self.orders_timestamp, self.history_timestamp = skin_info
        elif len_skin_info == 8:
            self.skin_id, self.name, self.analysis_timestamp, self.appearance_date, self.item_name_id, self.orders_timestamp, self.history_timestamp, self.buy_price = skin_info
        else:
            self.logger.error(f"len of skin_info unexpected {len_skin_info}, expected 7 or 8")

        self.logger.debug(f"skin_info: {skin_info}")
        

    def _retry_request(self, func, *args, **kwargs) -> Any:
        for attempt in range(self.MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except requests.RequestException as e:
                if attempt == self.MAX_RETRIES - 1:
                    self.logger.error(
                        f"Failed after {self.MAX_RETRIES} attempts: {e}"
                    )

                delay = random.uniform(*self.RETRY_DELAY_RANGE)
                self.logger.warning(
                    "Request failed (attempt %s/%s): %s. Retry in %.2fs",
                    attempt + 1, self.MAX_RETRIES, e, delay
                )
                time.sleep(delay)
        

    def _fetch_orders(self) -> Dict:
        if not self.item_name_id:
            raise ValueError("item_name_id is required")

        url = "https://steamcommunity.com/market/itemordershistogram"
        params = {
            "country": "KZ",
            "language": "english",
            "currency": 37,
            "item_nameid": self.item_name_id,
            "norender": 1
        }

        def make_request():
            response = self.session.get(
                url, params=params, headers=self.BASE_HEADERS, timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                self.logger.error(
                    f"API returned success=false for item_nameid={self.item_name_id}"
                )
            return data

        return self._retry_request(make_request)

    def _fetch_price_history(self) -> List[List]:
        if not self.name:
            raise ValueError("skin name is required")

        encoded_name = quote(self.name, safe="")
        url = f"https://steamcommunity.com/market/listings/{self.STEAM_APPID}/{encoded_name}?currency=37"

        headers = {
            **self.BASE_HEADERS,
            "Referer": "https://steamcommunity.com/market/",
            "Accept": "text/html",
        }

        def make_request():
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            html = response.text

            # Проверка на наличие user_info (признак залогиненного юзера)
            if not re.search(r'class="user_info"', html):
                self.logger.error("Cookies are invalid or not authorized (user_info not found)")

            match = re.search(r"var\s+line1\s*=\s*(\[[\s\S]*?\]);", html)
            if not match:
                self.logger.error(f"Price history (line1) not found for {self.name}")

            try:
                raw_prices = json.loads(match.group(1))
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse price history JS array: {e}")

            return self._parse_price_history(raw_prices)


        return self._retry_request(make_request)

    def _parse_price_history(self, raw_prices: List) -> List[List]:
        parsed = []
        for entry in raw_prices:
            try:
                raw_date, raw_price, raw_volume = entry

                clean_date = raw_date.split(":")[0]
                dt = datetime.strptime(clean_date, "%b %d %Y %H")
                dt = normalize_date(dt.replace(tzinfo=timezone.utc))

                price = float(raw_price)
                volume = int(str(raw_volume).replace(",", "").replace(" ", ""))

                parsed.append([dt, price, volume])
            except (ValueError, IndexError) as e:
                self.logger.error(
                    "Malformed price history entry %s: %s", entry, e
                )
        return parsed

    def _is_cache_expired(self, timestamp: Optional[datetime], max_age_days: int) -> bool:
        if timestamp is None:
            return True
        return timestamp < datetime.now(timezone.utc) - timedelta(days=max_age_days)

    def _update_orders_cache(self) -> None:
        """Обновляет ордера (buy/sell) из Steam API или БД"""
        if self._is_cache_expired(self.orders_timestamp, self.ORDERS_CACHE_DAYS):
            self.logger.debug("Orders fetching from Steam API")
            data = self._fetch_orders()

            self._buy_orders = data.get("buy_order_graph", [])
            self._sell_orders = data.get("sell_order_graph", [])

            self.db.insert_or_update_orders(
                self.skin_id, self._buy_orders, self._sell_orders
            )
            self.db.update_skin_orders_timestamp(self.skin_id)
            self.db.commit()
        else:
            self.logger.debug("Orders fetching from db")
            self.db.cursor.execute(
                "SELECT data, sell_orders FROM orders WHERE skin_id = %s",
                (self.skin_id,)
            )
            result = self.db.cursor.fetchone()

            if result:
                self._buy_orders, self._sell_orders = result
            else:
                self.logger.error(
                    "No cached orders found for skin_id=%s, refetching",
                    self.skin_id
                )
                self._update_orders_cache()

    def _update_prices_cache(self) -> None:
        """Обновляет историю цен из Steam API или БД — БЕЗ preprocessing"""
        if self._is_cache_expired(self.history_timestamp, self.PRICES_CACHE_DAYS):
            self.logger.debug("Prices fetching from Steam API")
            self._price_history = self._fetch_price_history()

            # Сохраняем ТОЛЬКО сырую историю
            self.db.update_price_history(self.skin_id, self._price_history)
            self.db.update_skin_history_timestamp(self.skin_id)
            self.db.commit()
        else:
            self.logger.debug("Prices fetching from db")

            self.db.cursor.execute(
                """
                SELECT date, price, volume
                FROM pricehistory
                WHERE skin_id = %s
                ORDER BY date
                """,
                (self.skin_id,)
            )

            rows = self.db.cursor.fetchall()

            if rows:
                self._price_history = [
                    [row[0], float(row[1]), int(row[2])]
                    for row in rows
                ]
            else:
                self.logger.error(
                    "No cached price history for skin_id=%s, refetching",
                    self.skin_id
                )
                self._update_prices_cache()

    def get_data(self) -> Tuple[List[List], List[List], List[List]]:
        """
        Возвращает данные для принятия решения.
        
        Returns:
            (history, buy_orders, sell_orders)
        """
        self._update_orders_cache()
        self._update_prices_cache()
        return self._price_history, self._buy_orders, self._sell_orders

    def update_data(self):
        """Принудительно обновляет ордера и историю цен"""
        self._update_orders_cache()
        self._update_prices_cache()

    def update_skin_info(self, skin_info):
        """Загружает информацию о новом скине"""
        self.load_skin(skin_info)



    def get_inventory(self):
        """
        Возвращает двумерный массив инвентаря:
        [[name, classid, instanceid, asset_id, marketable_time, float_value, int_value], ...]
        """
        url = 'https://steamcommunity.com/inventory/76561198857946351/730/2'

        response = self.session.get(url)
        if response.status_code == 200:
            data = response.json()

            assets = data.get('assets', [])
            descriptions = data.get('descriptions', [])
            asset_properties = data.get('asset_properties', [])

            # Подготавливаем список asset_id -> свойства
            properties_map = {}
            for prop in asset_properties:
                assetid = prop.get("assetid")
                props = prop.get("asset_properties", [])
                float_value, int_value = None, None
                for p in props:
                    if "float_value" in p:
                        float_value = float(p.get("float_value"))
                    if "int_value" in p:
                        int_value = int(p.get("int_value"))
                properties_map[assetid] = (float_value, int_value)

            asset_data_list = []
            for asset in assets:
                asset_data_list.append({
                    "assetid": asset.get('assetid'),
                    "classid": asset.get('classid'),
                    "instanceid": asset.get('instanceid')
                })

            result = []
            for item in descriptions:
                market_hash_name = item.get('market_hash_name')
                classid = item.get('classid')
                instanceid = item.get('instanceid')
                owner_descriptions = item.get('owner_descriptions')
                marketable_time = owner_descriptions[1].get('value') if owner_descriptions else None

                # находим первый asset_id (без массива)
                asset_id = None
                for asset_item in asset_data_list:
                    if classid == asset_item.get('classid') and instanceid == asset_item.get('instanceid'):
                        asset_id = asset_item.get('assetid')
                        break   # <--- выходим сразу, чтобы не копился список

                # достаём float/int по asset_id
                float_value, int_value = (None, None)
                if asset_id:
                    float_value, int_value = properties_map.get(asset_id, (None, None))
                if float_value is not None and int_value is not None:
                    result.append([
                        market_hash_name,
                        int(classid),
                        int(instanceid),
                        int(asset_id),
                        marketable_time,
                        float(float_value),
                        int(int_value)
                    ])
                else:
                    result.append([
                        market_hash_name,
                        int(classid),
                        int(instanceid),
                        int(asset_id),
                        marketable_time,
                        float_value,
                        int_value
                    ])
            return result
        else:
            self.logger.error(f"Ошибка запроса инвентаря: статус {response.status_code}, text: {response.text}")
            return None
    

    def check_my_state(self) -> tuple[float, float, list[dict]]:
        """
        Возвращает данные своих ордеров на покупку и баланс.
        
        Returns:
            (total_sum, my_wallet, my_buy_orders)
        """
        url = "https://steamcommunity.com/market/"
         
        resp = self.session.get(
            url,
            cookies={"ActListPageSize": "100"},
            timeout=15,
            allow_redirects=True,
        )
        
        soup = BeautifulSoup(resp.text, "html.parser")

        total_buyorders = 0.0
        wallet_balance = 0.0
        buy_orders = []

        # ===== BUY_ORDERS =====
        my_buy_order_rows = soup.find_all("div", id=re.compile(r"^mybuyorder_\d+$"))

        for row in my_buy_order_rows:
            # ===== ORDER ID =====
            full_id = row.get("id")              # "mybuyorder_123456789"
            order_id = full_id.split("_")[1]    # "123456789"

            # ===== NAME =====
            name_tag = row.select_one(".market_listing_item_name_link")
            if not name_tag:
                continue
            skin_name = name_tag.get_text(strip=True)

            # ===== PRICE =====
            price_tags = row.select(".market_listing_my_price .market_listing_price")
            if not price_tags:
                continue

            price_text = price_tags[0].get_text(strip=True)
            price_text = price_text.split("@")[-1]

            price_clean = (
                price_text
                .replace("₸", "")
                .replace(" ", "")
                .replace(",", ".")
            )

            price = float(price_clean)

            # ===== QTY =====
            qty_tag = row.select_one(".market_listing_inline_buyorder_qty")
            if qty_tag:
                qty_match = re.search(r"\d+", qty_tag.get_text())
                qty = int(qty_match.group()) if qty_match else 1
            else:
                qty = 1

            total = price * qty
            total_buyorders += total

            # ===== STORE RESULT =====
            buy_orders.append({
                "buy_order_id": order_id,
                "name": skin_name,
                "price": price,
                "qty": qty
            })

        sell_orders = []

        # ===== SELL_ORDERS =====
        my_sell_rows = soup.find_all("div", id=re.compile(r"^mylisting_\d+$"))

        for row in my_sell_rows:
            # ===== ORDER ID =====
            full_id = row.get("id")           # "mylisting_792205646637449623"
            order_id = full_id.split("_")[1] # "792205646637449623"

            # ===== NAME =====
            name_tag = row.select_one(".market_listing_item_name_link")
            if not name_tag:
                continue
            skin_name = name_tag.get_text(strip=True)

            # ===== DATE =====
            date_tag = row.select_one(".market_listing_right_cell.market_listing_listed_date.can_combine")
            date_text = date_tag.get_text(strip=True) if date_tag else ""

            # ===== PRICE =====
            price_tag = row.select_one(".market_listing_right_cell.market_listing_my_price")
            if not price_tag:
                continue

            price_text = price_tag.get_text(strip=True)
            # Убираем всё в скобках
            price_text = re.sub(r"\(.*?\)", "", price_text)
            
            price_clean = (
                price_text
                .replace("₸", "")
                .replace(" ", "")
                .replace(",", ".")
            )
            price_match = re.search(r"\d+(\.\d+)?", price_clean)
            if not price_match:
                continue
            price = float(price_match.group())

            # ===== STORE RESULT =====
            sell_orders.append({
                "sell_order_id": order_id,
                "name": skin_name,
                "date": date_text,
                "price": price,
            })
        
        # ===== WALLET =====
        wallet_tag = soup.select_one(".responsive_menu_user_wallet a")
        if wallet_tag:
            wallet_text = wallet_tag.get_text(strip=True)
            match = re.search(r"([\d\s]+[,\.]\d+)", wallet_text)
            if match:
                wallet_clean = match.group(1).replace(" ", "").replace(",", ".")
                wallet_balance = float(wallet_clean)



        return total_buyorders, wallet_balance, buy_orders, sell_orders

    def get_my_history(self):
        url = "https://steamcommunity.com/market/myhistory/render/?query=&start=0&count=100"
        resp = self.session.get(url, timeout=15, allow_redirects=True)
        data = resp.json()

        results_html = data.get("results_html")
        assets = data.get("assets", {}).get("730", {}).get("2", {})

        soup = BeautifulSoup(results_html, "html.parser")
        history_rows = soup.select(".market_listing_row")

        history = []

        for row in history_rows:
            # Ищем assetid в JS-ховере
            img_elem = row.select_one("img[id$='_image']")
            if not img_elem:
                continue

            # id img = history_row_XXX_YYY_image, берем последний аргумент из hovers
            assetid = None
            for asset_key, asset_val in assets.items():
                if asset_val.get("icon_url") and asset_val["icon_url"].split("/")[-1] in img_elem["src"]:
                    assetid = asset_key
                    break

            if not assetid or assetid not in assets:
                print("NOT FOUND IN ASSETS:", assetid)
                continue

            asset_data = assets[assetid]
            market_name = asset_data.get("market_hash_name")

            price_elem = row.select_one(".market_listing_their_price .market_listing_price")
            listed_date_elem = row.select(".market_listing_listed_date.can_combine")
            gain_loss_elem = row.select_one(".market_listing_left_cell.market_listing_gainorloss")

            price = None
            if price_elem:
                raw_price = price_elem.text.strip().split("(")[0]
                raw_price = raw_price.replace("₸", "").replace(",", ".").replace(" ", "")
                try:
                    price = float(raw_price)
                except ValueError:
                    price = None

            item = {
                "assetid": assetid,
                "name": market_name,
                "price": price,
                "acted_on": listed_date_elem[0].text.strip() if len(listed_date_elem) > 0 else None,
                "listed_on": listed_date_elem[1].text.strip() if len(listed_date_elem) > 1 else None,
                "gain_or_loss": gain_loss_elem.text.strip() if gain_loss_elem else None
            }

            history.append(item)

        return history

if __name__ == "__main__":
    logging.getLogger(__name__).info("SteamMarketParser module loaded")