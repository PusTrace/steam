from datetime import datetime

class BaseStrategy:
    def decide(self, **kwargs):
        raise NotImplementedError


class EVA(BaseStrategy):
    def load_state(self, **kwargs):
        self.moment_price = kwargs.get("moment_price")
        self.volume = kwargs.get("volume")
        self.high_approx = kwargs.get("high_approx")
        self.low_approx = kwargs.get("low_approx")
        self.linreg_6m = kwargs.get("slope_six_m")
        self.linreg_1m = kwargs.get("slope_one_m")
        self.avg_month_price = kwargs.get("avg_month_price")
        self.avg_week_price = kwargs.get("avg_week_price")
        self.skin_orders = kwargs.get("skin_orders")

    def decide(self, **kwargs):
        """
        EVA strategy for decideing buy price based on market orders.
        :param kwargs: Contains necessary parameters like price, volume, skin_orders.
        :return: Tuple of (decideed price, amount to buy, snapshot of volume before the order).
        """
        self.load_state(**kwargs)  # Reset state

        # Шаг 2. Выбор цены и объема
        y, amount, snapshot = self.analyze_order_book()

        # Шаг 3. Возврат решения
        return y, amount, snapshot
    

    def dinamyc_thresholds(self):
        if self.linreg_1m > 0:
            default_threshold_top = self.avg_week_price * 0.87
        else:
            default_threshold_top = self.avg_week_price * 0.85
        # === Динамическое определение границ диапазона ===
        matching_order = next(order for order in self.skin_orders if order[0] < default_threshold_top)
        if matching_order:
            threshold_top = matching_order[0]
            if matching_order[1] < self.volume * 1.5:
                return threshold_top
            else:
                print("[EVA] Matching order found, but order_volume over buy_volume*1.5 , skipping")
                return None
        
    def analyze_order_book(self):
        if self.linreg_1m > 0:
            amount = 2
        else:
            amount = 1

        threshold_top = self.dinamyc_thresholds()
        if threshold_top is None:
            return None, None, None

        orders_in_range = [o for o in self.skin_orders if o[0] <= threshold_top]

        min_price = orders_in_range[-1][0]
        price_range = threshold_top - min_price if threshold_top != min_price else 1  # защита от деления на 0

        walls = []
        for i in range(len(orders_in_range) - 1):
            current_order = orders_in_range[i]
            next_order = orders_in_range[i + 1]

            wall_volume = next_order[1] - current_order[1]

            # === Квантификатор сложности: чем ближе к threshold_top, тем сложнее ===
            relative_height = (current_order[0] - min_price) / price_range
            difficulty_multiplier = 1 + relative_height ** 2  # от 1.0 до 2.0
            dynamic_threshold = self.volume * 0.1 * difficulty_multiplier

            if wall_volume > dynamic_threshold:
                wall_price = current_order[0]
                walls.append((wall_price, wall_volume))

        # === Перебиваем первую найденную стенку ===
        if walls:
            target_wall_price = walls[0][0]
            y = target_wall_price + self.avg_week_price * 0.001
            print(f"[EVA] Перебиваем стенку по цене {target_wall_price} -> новая цена {y:.2f}")
        else:
            y = min_price
            print("[EVA] [ERROR] Стенок не найдено — используем минимальную цену в диапазоне")

        snapshot = self.do_snapshot(y=y, threshold_top=threshold_top, target_wall_price=target_wall_price)

        return round(y, 2), amount, snapshot

    
    def do_snapshot(self, **kwargs):
        y = kwargs.get("y")
        threshold_top = kwargs.get("threshold_top")
        first_wall_price = kwargs.get("target_wall_price")

        volume_before_y = next((order[1] for order in self.skin_orders if order[0] < y), None)
        volume_before_threshold_top = next((order[1] for order in self.skin_orders if order[0] < threshold_top), None)
        order_volume_at_y = next((order[1] for order in self.skin_orders if order[0] == y), None)
        volume_behind_y = sum(order[1] for order in self.skin_orders if order[0] > y)
        depth_index_y = next((i for i, order in enumerate(self.skin_orders) if order[0] >= y), None)
        distance_to_wall = y - first_wall_price if first_wall_price is not None else None
        relative_diff_y_to_avg = (y - self.avg_week_price) / self.avg_week_price

        normalized = lambda x: x / self.volume if self.volume and x is not None else None

        return {
            "volume_before_y": volume_before_y,
            "volume_before_threshold_top": volume_before_threshold_top,
            "volume_behind_y": volume_behind_y,
            "order_volume_at_y": order_volume_at_y,
            "norm_volume_before_y": normalized(volume_before_y),
            "norm_volume_before_threshold_top": normalized(volume_before_threshold_top),
            "norm_volume_behind_y": normalized(volume_behind_y),
            "norm_order_volume_at_y": normalized(order_volume_at_y),
            "depth_index_y": depth_index_y,
            "distance_to_wall": distance_to_wall,
            "relative_diff_y_to_avg": relative_diff_y_to_avg,
            "snapshot_time": datetime.now().isoformat()
        }




    
class PTModel:
    def __init__(self, model_type: str):
        strategies = {
            "EVA": EVA
        }

        if model_type not in strategies:
            raise ValueError(f"Unknown model type: {model_type}")

        self.strategy = strategies[model_type]()

    def decide(self, **kwargs):
        return self.strategy.decide(**kwargs)


def test_eva():
    skin_orders = [[2215.87, 1, '1 buy orders at 2 215,87₸ or higher'], [2203.49, 6, '6 buy orders at 2 203,49₸ or higher'], [2197.3, 30, '30 buy orders at 2 197,30₸ or higher'], [2172.53, 45, '45 buy orders at 2 172,53₸ or higher'], [2165.69, 48, '48 buy orders at 2 165,69₸ or higher'], [2130.3, 51, '51 buy orders at 2 130,30₸ or higher'], [2067.32, 54, '54 buy orders at 2 067,32₸ or higher'], [2064.89, 56, '56 buy orders at 2 064,89₸ or higher'], [2032.53, 68, '68 buy orders at 2 032,53₸ or higher'], [2029.17, 69, '69 buy orders at 2 029,17₸ or higher'], [2011.61, 81, '81 buy orders at 2 011,61₸ or higher'], [1999.23, 93, '93 buy orders at 1 999,23₸ or higher'], [1993.04, 107, '107 buy orders at 1 993,04₸ or higher'], [1986.86, 177, '177 buy orders at 1 986,86₸ or higher'], [1986.3, 181, '181 buy orders at 1 986,30₸ or higher'], [1979.16, 186, '186 buy orders at 1 979,16₸ or higher'], [1977.93, 194, '194 buy orders at 1 977,93₸ or higher'], [1974.47, 196, '196 buy orders at 1 974,47₸ or higher'], [1968.28, 198, '198 buy orders at 1 968,28₸ or higher'], [1933.38, 200, '200 buy orders at 1 933,38₸ or higher'], [1912.58, 206, '206 buy orders at 1 912,58₸ or higher'], [1900.19, 215, '215 buy orders at 1 900,19₸ or higher'], [1855.27, 216, '216 buy orders at 1 855,27₸ or higher'], [1838.3, 217, '217 buy orders at 1 838,30₸ or higher'], [1828.43, 221, '221 buy orders at 1 828,43₸ or higher'], [1819.1, 229, '229 buy orders at 1 819,10₸ or higher'], [1813.55, 230, '230 buy orders at 1 813,55₸ or higher'], [1813.2, 236, '236 buy orders at 1 813,20₸ or higher'], [1807.36, 239, '239 buy orders at 1 807,36₸ or higher'], [1802.05, 240, '240 buy orders at 1 802,05₸ or higher'], [1801.16, 242, '242 buy orders at 1 801,16₸ or higher'], [1790.18, 243, '243 buy orders at 1 790,18₸ or higher'], [1783.08, 247, '247 buy orders at 1 783,08₸ or higher'], [1764.98, 249, '249 buy orders at 1 764,98₸ or higher'], [1757.83, 250, '250 buy orders at 1 757,83₸ or higher'], [1748, 252, '252 buy orders at 1 748₸ or higher'], [1744.39, 263, '263 buy orders at 1 744,39₸ or higher'], [1726.89, 264, '264 buy orders at 1 726,89₸ or higher'], [1698.36, 268, '268 buy orders at 1 698,36₸ or higher'], [1683.55, 269, '269 buy orders at 1 683,55₸ or higher'], [1671.19, 277, '277 buy orders at 1 671,19₸ or higher'], [1646.76, 297, '297 buy orders at 1 646,76₸ or higher'], [1645.2, 299, '299 buy orders at 1 645,20₸ or higher'], [1621.9, 310, '310 buy orders at 1 621,90₸ or higher'], [1619.25, 314, '314 buy orders at 1 619,25₸ or higher'], [1615.47, 315, '315 buy orders at 1 615,47₸ or higher'], [1602.49, 316, '316 buy orders at 1 602,49₸ or higher'], [1587.07, 317, '317 buy orders at 1 587,07₸ or higher'], [1584.53, 323, '323 buy orders at 1 584,53₸ or higher'], [1578.34, 331, '331 buy orders at 1 578,34₸ or higher'], [1553.58, 339, '339 buy orders at 1 553,58₸ or higher'], [1552.89, 344, '344 buy orders at 1 552,89₸ or higher'], [1511, 355, '355 buy orders at 1 511₸ or higher'], [1479.3, 439, '439 buy orders at 1 479,30₸ or higher'], [1479.22, 445, '445 buy orders at 1 479,22₸ or higher'], [1460.7, 451, '451 buy orders at 1 460,70₸ or higher'], [1430.28, 452, '452 buy orders at 1 430,28₸ or higher'], [1407.55, 460, '460 buy orders at 1 407,55₸ or higher'], [1381.22, 461, '461 buy orders at 1 381,22₸ or higher'], [1380.27, 465, '465 buy orders at 1 380,27₸ or higher'], [1364.25, 467, '467 buy orders at 1 364,25₸ or higher'], [1361.71, 477, '477 buy orders at 1 361,71₸ or higher'], [1356.83, 485, '485 buy orders at 1 356,83₸ or higher'], [1341.82, 495, '495 buy orders at 1 341,82₸ or higher'], [1339.64, 497, '497 buy orders at 1 339,64₸ or higher'], [1333.26, 510, '510 buy orders at 1 333,26₸ or higher'], [1330.74, 532, '532 buy orders at 1 330,74₸ or higher'], [1326.73, 541, '541 buy orders at 1 326,73₸ or higher'], [1312.51, 549, '549 buy orders at 1 312,51₸ or higher'], [1312.23, 562, '562 buy orders at 1 312,23₸ or higher'], [1312.19, 582, '582 buy orders at 1 312,19₸ or higher'], [1307.51, 595, '595 buy orders at 1 307,51₸ or higher'], [1306.7, 605, '605 buy orders at 1 306,70₸ or higher'], [1299.8, 617, '617 buy orders at 1 299,80₸ or higher'], [1293.61, 637, '637 buy orders at 1 293,61₸ or higher'], [1293.09, 643, '643 buy orders at 1 293,09₸ or higher'], [1287.43, 654, '654 buy orders at 1 287,43₸ or higher'], [1286.66, 664, '664 buy orders at 1 286,66₸ or higher'], [1276.55, 674, '674 buy orders at 1 276,55₸ or higher'], [1274.45, 687, '687 buy orders at 1 274,45₸ or higher'], [1271.21, 700, '700 buy orders at 1 271,21₸ or higher'], [1267, 713, '713 buy orders at 1 267₸ or higher'], [1259.37, 724, '724 buy orders at 1 259,37₸ or higher'], [1256.6, 730, '730 buy orders at 1 256,60₸ or higher'], [1256.49, 741, '741 buy orders at 1 256,49₸ or higher'], [1251.74, 754, '754 buy orders at 1 251,74₸ or higher'], [1250.36, 774, '774 buy orders at 1 250,36₸ or higher'], [1244.37, 778, '778 buy orders at 1 244,37₸ or higher'], [1244.3, 789, '789 buy orders at 1 244,30₸ or higher'], [1244.1, 797, '797 buy orders at 1 244,10₸ or higher'], [1236.09, 811, '811 buy orders at 1 236,09₸ or higher'], [1231.5, 817, '817 buy orders at 1 231,50₸ or higher'], [1225.53, 827, '827 buy orders at 1 225,53₸ or higher'], [1224.91, 830, '830 buy orders at 1 224,91₸ or higher'], [1221.91, 831, '831 buy orders at 1 221,91₸ or higher'], [1213.53, 851, '851 buy orders at 1 213,53₸ or higher'], [1209.3, 853, '853 buy orders at 1 209,30₸ or higher'], [1206.4, 856, '856 buy orders at 1 206,40₸ or higher'], [1205.55, 868, '868 buy orders at 1 205,55₸ or higher'], [1194.3, 871, '871 buy orders at 1 194,30₸ or higher'], [1185.1, 873, '873 buy orders at 1 185,10₸ or higher']],
    
    pt_model = PTModel(model_type="EVA")
    y, amount, snapshot = pt_model.decide(skin_orders=skin_orders[0], slope_six_m = -6.936237812244004, slope_one_m = -8.047897084084791, avg_month_price = 2186.0670585952857, avg_week_price = 2165.141007828283, volume = 100, high_approx = 2378.7958994708993, low_approx = 1937.7979948717948, moment_price = 2011.404)
    print(f"Decided price: {y}, Amount: {amount}, Snapshot: {snapshot}")
if __name__ == "__main__":
    test_eva()