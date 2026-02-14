import logging
from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta, timezone

class OrderBookAnalyzer:
    """Анализатор стаканов ордеров — поиск стенок ликвидности"""
    def __init__(self):
        self.log = logging.getLogger(__name__)
    
    def analyze(
        self, 
        buy_orders: List[Tuple[float, int]], 
        sell_orders: List[Tuple[float, int]],
        avg_week_price: float,
        slope_1m: float,
        volume_week: int
    ) -> Tuple[Optional[float], Optional[int]]:
        """
        Главный метод — возвращает цену и количество для покупки.
        
        Args:
            buy_orders: список ордеров на покупку [(price, volume)]
            sell_orders: список ордеров на продажу [(price, volume)]
            avg_week_price: средняя цена за неделю
            slope_1m: тренд за месяц
            volume_week: объём продаж за неделю
        
        Returns:
            (price, amount) или (None, None)
        """
        self.buy_orders = buy_orders
        self.sell_orders = sell_orders
        self.avg_week_price = avg_week_price
        self.slope_1m = slope_1m
        self.volume_week = volume_week
        
        # Определяем количество для покупки на основе тренда
        amount = 2 if slope_1m < 0 else 1
        
 
        self.log.debug("=== ORDER BOOK ANALYSIS ===")
        self.log.debug(f"Purchase amount: {amount} (based on {'uptrend' if slope_1m < 0 else 'downtrend'})")
        
        # Вычисляем динамический порог
        threshold_top = self._calculate_threshold()
        if threshold_top is None:
            self.log.debug("Threshold calculation failed, aborting")
            return None, None
        
        # Фильтруем ордера в пределах порога
        orders_in_range = [o for o in buy_orders if o[0] <= threshold_top]
        
        
        self.log.debug(f"Orders within threshold: {len(orders_in_range)} / {len(buy_orders)}")
        
        if len(orders_in_range) < 4:
            self.log.warning(f"Too few orders in range: {len(orders_in_range)} < 4")
            return None, None
        
        # Ограничиваем зону поиска
        realistic_orders = self._filter_price_zone(orders_in_range, threshold_top)
        if not realistic_orders:
            self.log.warning("No orders in realistic price zone")
            return None, None
        
        # Ищем стенки ликвидности
        liquidity_walls = self._find_liquidity_walls(realistic_orders)
        if not liquidity_walls:
            self.log.warning("No liquidity walls detected")
            return None, None
        
        # Выбираем лучшую стенку
        target_price = self._select_best_wall(liquidity_walls)
        
        return round(target_price, 2), amount
    
    def _calculate_threshold(self) -> Optional[float]:
        """Вычисляет динамический порог для фильтрации ордеров"""
        
 
        self.log.debug("=== DYNAMIC THRESHOLDS CALCULATION ===")
        
        # Средняя по топ-5 sell orders
        top_sell_orders = self.sell_orders[:5]
        avg_sell_price = sum(order[0] for order in top_sell_orders) / len(top_sell_orders)
        
 
        self.log.debug(f"Top {len(top_sell_orders)} sell orders: {[f'{o[0]:.2f}₸' for o in top_sell_orders]}")
        self.log.debug(f"Average sell price: {avg_sell_price:.2f}₸")
        
        # Берём минимум между средней недельной ценой и средней sell orders
        threshold_price = min(self.avg_week_price, avg_sell_price)
        self.threshold_price = threshold_price
        
 
        self.log.debug(f"avg_week_price: {self.avg_week_price:.2f}₸")
        self.log.debug(f"threshold_price (min of both): {threshold_price:.2f}₸")
        self.log.debug(f"Using: {'avg_week' if threshold_price == self.avg_week_price else 'avg_sell'}")
        
        # Определяем множитель в зависимости от тренда
        if self.slope_1m < 0:
            multiplier = 0.86
            trend = "DOWNTREND"
        else:
            multiplier = 0.85
            trend = "UPTREND"
        
        default_threshold_top = threshold_price * multiplier
        
 
        self.log.debug(f"Market trend: {trend} (slope_1m={self.slope_1m:.4f})")
        self.log.debug(f"Multiplier: {multiplier} → default_threshold_top: {default_threshold_top:.2f}₸")
        self.log.debug(f"Looking for first order below {default_threshold_top:.2f}₸...")
        
        # Ищем первый ордер ниже порога
        try:
            matching_order = next(order for order in self.buy_orders if order[0] < default_threshold_top)
        except StopIteration:
            self.log.error(f"No orders found below threshold {default_threshold_top:.2f}₸")

            closest_order = min(self.buy_orders, key=lambda x: abs(x[0] - default_threshold_top))
            self.log.debug(f"Closest order: {closest_order[0]:.2f}₸ (diff: {closest_order[0] - default_threshold_top:+.2f}₸)")
            return None
        
        threshold_top = matching_order[0]
        order_volume = matching_order[1]
        volume_limit = self.volume_week * 1.7
        
 
        self.log.debug(f"Found matching order: price={threshold_top:.2f}₸, volume={order_volume}")
        self.log.debug(f"Volume check: {order_volume} < {volume_limit:.0f} (volume * 1.7)?")
        
        # Проверка объёма
        if order_volume < volume_limit:
            self.log.info(f"✓ Threshold accepted: {threshold_top:.2f}₸")
 
            self.log.debug(f"Volume OK: {order_volume} < {volume_limit:.0f}")
            discount_pct = (1 - threshold_top / self.avg_week_price) * 100
            self.log.debug(f"Discount from avg_week: {discount_pct:.1f}%")
            return threshold_top
        else:
            self.log.warning(f"Order volume too high: {order_volume} > {volume_limit:.0f}, skipping")
 
            excess_pct = (order_volume / volume_limit - 1) * 100
            self.log.debug(f"Volume excess: +{excess_pct:.1f}%")
            return None
    
    def _filter_price_zone(self, orders_in_range: List, threshold_top: float) -> List:
        """Ограничивает зону поиска в пределах разумного диапазона цен"""
        
        min_price = orders_in_range[-1][0]
        price_range = threshold_top - min_price
        
        # Настраиваемый параметр для зоны поиска
        PRICE_ZONE_PERCENTAGE = 0.4
        min_realistic_price = threshold_top - (price_range * PRICE_ZONE_PERCENTAGE)
        
        realistic_orders = [o for o in orders_in_range if o[0] >= min_realistic_price]
        
 
        self.log.debug("=== PRICE ZONE FILTERING ===")
        self.log.debug(f"Full price range: {threshold_top:.2f}₸ → {min_price:.2f}₸ (span: {price_range:.2f}₸)")
        self.log.debug(f"Initial zone: top {PRICE_ZONE_PERCENTAGE*100:.0f}% → min_price: {min_realistic_price:.2f}₸")
        self.log.debug(f"Orders in initial zone: {len(realistic_orders)}")
        
        # Расширяем зону если слишком мало ордеров
        if len(realistic_orders) < 3:
            PRICE_ZONE_PERCENTAGE = 0.6
            min_realistic_price = threshold_top - (price_range * PRICE_ZONE_PERCENTAGE)
            realistic_orders = [o for o in orders_in_range if o[0] >= min_realistic_price]
            
 
            self.log.debug(f"Zone expanded to {PRICE_ZONE_PERCENTAGE*100:.0f}% → min_price: {min_realistic_price:.2f}₸")
            self.log.debug(f"Orders in expanded zone: {len(realistic_orders)}")
        
        if realistic_orders:
            self.log.debug(f"Realistic price span: {realistic_orders[0][0]:.2f}₸ → {realistic_orders[-1][0]:.2f}₸")
            self.log.debug(f"Volume in zone: {realistic_orders[0][1]} → {realistic_orders[-1][1]}")
        
        return realistic_orders
    
    def _find_liquidity_walls(self, realistic_orders: List) -> List[Dict]:
        """Собирает данные о стенах ликвидности"""
        
        liquidity_walls = []
        
        for i in range(len(realistic_orders) - 1):
            current_order = realistic_orders[i]
            next_order = realistic_orders[i + 1]
            
            current_price = current_order[0]
            current_volume = current_order[1]
            next_volume = next_order[1]
            
            volume_jump = next_volume - current_volume
            volume_growth_pct = (volume_jump / current_volume * 100) if current_volume > 0 else 0
            wall_score = volume_jump * (1 + volume_growth_pct / 100)
            
            liquidity_walls.append({
                'price': current_price,
                'volume_jump': volume_jump,
                'volume_growth_pct': volume_growth_pct,
                'score': wall_score,
                'cumulative_before': current_volume,
                'cumulative_after': next_volume
            })
        
        if not liquidity_walls:
            return []
        
        # Сортируем по скору
        liquidity_walls.sort(key=lambda x: x['score'], reverse=True)
        
        # Статистика
        all_jumps = [w['volume_jump'] for w in liquidity_walls]
        mean_jump = sum(all_jumps) / len(all_jumps)
        variance = sum((j - mean_jump) ** 2 for j in all_jumps) / len(all_jumps)
        stdev_jump = variance ** 0.5
        significance_threshold = mean_jump + 0.5 * stdev_jump
        
 
        self.log.debug("=== WALL STATISTICS ===")
        self.log.debug(f"Total walls detected: {len(liquidity_walls)}")
        self.log.debug(f"Mean volume jump: {mean_jump:.2f}")
        self.log.debug(f"Standard deviation: {stdev_jump:.2f}")
        self.log.debug(f"Significance threshold: {significance_threshold:.2f}")
        self.log.debug(f"Min jump: {min(all_jumps):.2f}, Max jump: {max(all_jumps):.2f}")
        
        # Отбираем значимые стенки
        MIN_WALLS = 3
        MAX_WALLS = 8
        
        significant_walls = [w for w in liquidity_walls if w['volume_jump'] > significance_threshold]
        
        if len(significant_walls) < MIN_WALLS:
            candidate_walls = liquidity_walls[:MIN_WALLS] if len(liquidity_walls) >= MIN_WALLS else liquidity_walls
 
            self.log.debug(f"Only {len(significant_walls)} significant walls, using top {len(candidate_walls)}")
        else:
            candidate_walls = significant_walls[:MAX_WALLS]
         
            self.log.debug(f"Found {len(significant_walls)} significant walls, using top {len(candidate_walls)}")
        
        if candidate_walls:
            self.log.debug(f"=== TOP {len(candidate_walls)} CANDIDATE WALLS ===")
            for i, wall in enumerate(candidate_walls, 1):
                self.log.debug(
                    f"{i}. Price: {wall['price']:.2f}₸ | "
                    f"Jump: {wall['volume_jump']} (+{wall['volume_growth_pct']:.1f}%) | "
                    f"Score: {wall['score']:.2f}"
                )
                self.log.debug(f"   Volume transition: {wall['cumulative_before']} → {wall['cumulative_after']}")
        
        return candidate_walls
    
    def _select_best_wall(self, candidate_walls: List[Dict]) -> float:
        """Выбирает самую высокую цену среди кандидатов"""
        
        best_wall = max(candidate_walls, key=lambda x: x['price'])
        target_price = best_wall['price'] + self.avg_week_price * 0.001
        
 
        self.log.debug("=== WALL SELECTION ===")
        self.log.debug(f"Selected wall price: {best_wall['price']:.2f}₸")
        self.log.debug(f"Volume jump at wall: {best_wall['volume_jump']} (+{best_wall['volume_growth_pct']:.1f}%)")
        self.log.debug(f"Wall score: {best_wall['score']:.2f}")
        self.log.debug(f"Micro adjustment: +{self.avg_week_price * 0.001:.2f}₸")
        self.log.debug(f"Final target price: {target_price:.2f}₸")
        
        discount_from_threshold = (1 - target_price / self.threshold_price) * 100
        discount_from_week = (1 - target_price / self.avg_week_price) * 100
        
        self.log.debug("=== PRICE ANALYSIS ===")
        self.log.debug(f"Target vs threshold: {discount_from_threshold:.1f}% discount")
        self.log.debug(f"Target vs avg_week: {discount_from_week:.1f}% discount")
        
        self.log.info(
            f"✓ Selected wall: {target_price:.2f}₸ "
            f"(threshold: {self.threshold_price:.2f}₸, "
            f"volume_jump: {best_wall['volume_jump']})"
        )
        
        return target_price




class PumpDetector:
    """Детектор манипуляций с ценой (памп/дамп)"""
    
    def __init__(self):
        # Пороги (калибруй под свои данные)
        self.BOOST_THRESHOLD = 10           # рост цены >10% (памп)
        self.VOLATILITY_THRESHOLD = 18      # средняя волатильность >18%
        self.log = logging.getLogger(__name__)
    
    def check(
        self, 
        history: List[Tuple[datetime, float, int]]
    ) -> Tuple[bool, List[str], float]:
        """
        Главный метод детекции манипуляций.
        
        Args:
            history: история продаж [(datetime, price, volume)]
        
        Returns:
            is_manipulated: bool
        """
        
 
        self.log.debug("=== PUMP DETECTION ===")
        
        if len(history) < 20:
 
            self.log.debug("Недостаточно данных для анализа (<20 записей)")
            return True
        
        # Извлекаем только цены
        prices = [p for _, p, _ in history if p is not None]
        year_ago = datetime.now(tz=timezone.utc) - timedelta(365)
        year_prices = [p for date, p, _ in history if p is not None and date >= year_ago]
        if len(prices) < 20:
            return True
        
        # === 1. Проверка на ПАМП (буст цены) ===
        boost_check = self._check_price_boost(prices, year_prices)
 
        self.log.debug(f"[BOOST] {boost_check['reason']}")
        if boost_check['detected']:
            return True
        
        # === 2. Проверка волатильности ===
        volatility_check = self._check_volatility(prices)
 
        self.log.debug(f"[VOLATILITY] {volatility_check['reason']}")
        if volatility_check['detected']:
            return True
        
        return False
    
    def _check_price_boost(self, prices: List[float], year_prices: List[float]) -> dict:
        """
        Проверка на памп (буст цены).
        Сравниваем медиану последних 50 продаж с медианой истории за год.
        """
        if len(prices) < 50:
            return {'detected': False, 'reason': ''}
        
        # Первая половина истории = baseline
        
        # Последние 50 продаж
        last_50 = prices[-50:]
        
        # Считаем медианы
        baseline_median = self._median(year_prices)
        recent_median = self._median(last_50)
 
        self.log.debug(f"baseline_median: {baseline_median}, recent_median:{recent_median}")
        
        # Процент роста
        boost_pct = ((recent_median - baseline_median) / baseline_median) * 100
        
        if boost_pct >= self.BOOST_THRESHOLD:
            return {
                'detected': True,
                'reason': f"Обнаружен буст цены (рост на {boost_pct:.1f}%)"
            }
        
        return {'detected': False, 'reason': ''}
    
    def _check_volatility(self, prices: List[float]) -> dict:
        """
        Проверка волатильности.
        Средний процент изменения между соседними продажами.
        """
        if len(prices) < 2:
            return {'detected': False, 'reason': ''}
        
        total_change = 0
        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                change = abs((prices[i] - prices[i - 1]) / prices[i - 1]) * 100
                total_change += change
        
        volatility = total_change / (len(prices) - 1)
        
        if volatility > self.VOLATILITY_THRESHOLD:
            return {
                'detected': True,
                'reason': f"Высокая волатильность ({volatility:.1f}%)"
            }
        
        return {'detected': False, 'reason': ''}
    
    
    def _median(self, arr: List[float]) -> float:
        """Вычисляет медиану массива"""
        sorted_arr = sorted(arr)
        mid = len(sorted_arr) // 2
        
        if len(sorted_arr) % 2 == 0:
            return (sorted_arr[mid - 1] + sorted_arr[mid]) / 2
        else:
            return sorted_arr[mid]