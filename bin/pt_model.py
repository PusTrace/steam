class BaseStrategy:
    def predict(self, **kwargs):
        raise NotImplementedError


class EVA(BaseStrategy):
    def predict(self, **kwargs):
        price       = kwargs["price"]
        volume      = kwargs["volume"]
        skin_orders = kwargs["skin_orders"]
        linreg      = kwargs["linreg"]

        amount = 1
        default_threshold_top = price * 0.85

        # === Динамическое определение границ диапазона ===
        matching_order = next((order for order in skin_orders if order[0] < default_threshold_top), None)
        matching_volume = next((order for order in skin_orders if order[1] > volume * 2), None)

        if matching_order:
            if matching_order[1] < volume * 1.2:
                threshold_top = matching_order[0]
                if matching_volume:
                    threshold_down = matching_volume[0]
                else:
                    print("[EVA] Нет объемов ниже нижнего порога используется price*0.70")
                    threshold_down = price * 0.70  # запасной вариант
            else:
                print("[EVA] объём верхнего порога слишком велик, пропускаем")
                return None, None, None
        else:
            print("[EVA] Нет ордеров ниже верхнего порога(ошибка)")
            return None, None, None

        # === Поиск стенок в диапазоне ===
        orders_in_range = [o for o in skin_orders if threshold_down <= o[0] <= threshold_top]

        walls = []
        for i in range(len(orders_in_range) - 1):
            current_order = orders_in_range[i]
            next_order = orders_in_range[i + 1]

            wall_volume = next_order[1] - current_order[1]
            if wall_volume > volume * 0.1:
                wall_price = current_order[0]
                walls.append((wall_price, wall_volume))

        # === Перебиваем первую найденную стенку ===
        if walls:
            target_wall_price = walls[0][0]
            y = target_wall_price + price * 0.001  # перебиваем на копейку
            print(f"[EVA] Перебиваем стенку по цене {target_wall_price} -> новая цена {y:.2f}")
        else:
            y = threshold_down
            print("[EVA] Стенок не найдено — используем threshold_down")

        predict_price = price * (100 + linreg)/100
        predicted_profit = predict_price - price
        return round(y, 2), amount, round(predicted_profit, 2)



    
class PTModel:
    def __init__(self, model_type: str):
        strategies = {
            "EVA": EVA
        }

        if model_type not in strategies:
            raise ValueError(f"Unknown model type: {model_type}")

        self.strategy = strategies[model_type]()

    def predict(self, **kwargs):
        return self.strategy.predict(**kwargs)


def test_eva():
    # ==== Входные данные ====
    price = 1387.16
    volume = 300
    linreg = 2.6692650

    # skin_orders (вставь свой JSON вручную, часть ты не дослал — он обрывается на "992.52,...")
    skin_orders = [
        [
            1193.19,
            1,
            "1 buy orders at 1 193,19₸ or higher"
        ],
        [
            1187.17,
            45,
            "45 buy orders at 1 187,17₸ or higher"
        ],
        [
            1183.67,
            137,
            "137 buy orders at 1 183,67₸ or higher"
        ],
        [
            1181.14,
            157,
            "157 buy orders at 1 181,14₸ or higher"
        ],
        [
            1175.9,
            158,
            "158 buy orders at 1 175,90₸ or higher"
        ],
        [
            1175.12,
            245,
            "245 buy orders at 1 175,12₸ or higher"
        ],
        [
            1169.1,
            267,
            "267 buy orders at 1 169,10₸ or higher"
        ],
        [
            1163.06,
            325,
            "325 buy orders at 1 163,06₸ or higher"
        ],
        [
            1157.04,
            407,
            "407 buy orders at 1 157,04₸ or higher"
        ],
        [
            1151.01,
            415,
            "415 buy orders at 1 151,01₸ or higher"
        ],
        [
            1147.32,
            416,
            "416 buy orders at 1 147,32₸ or higher"
        ],
        [
            1144.99,
            420,
            "420 buy orders at 1 144,99₸ or higher"
        ],
        [
            1138.97,
            459,
            "459 buy orders at 1 138,97₸ or higher"
        ],
        [
            1132.93,
            481,
            "481 buy orders at 1 132,93₸ or higher"
        ],
        [
            1132.54,
            486,
            "486 buy orders at 1 132,54₸ or higher"
        ],
        [
            1128.46,
            488,
            "488 buy orders at 1 128,46₸ or higher"
        ],
        [
            1126.9,
            490,
            "490 buy orders at 1 126,90₸ or higher"
        ],
        [
            1120.87,
            498,
            "498 buy orders at 1 120,87₸ or higher"
        ],
        [
            1114.85,
            525,
            "525 buy orders at 1 114,85₸ or higher"
        ],
        [
            1108.83,
            553,
            "553 buy orders at 1 108,83₸ or higher"
        ],
        [
            1108.17,
            557,
            "557 buy orders at 1 108,17₸ or higher"
        ],
        [
            1102.79,
            574,
            "574 buy orders at 1 102,79₸ or higher"
        ],
        [
            1101.79,
            578,
            "578 buy orders at 1 101,79₸ or higher"
        ],
        [
            1096.77,
            632,
            "632 buy orders at 1 096,77₸ or higher"
        ],
        [
            1092.8,
            644,
            "644 buy orders at 1 092,80₸ or higher"
        ],
        [
            1090.74,
            677,
            "677 buy orders at 1 090,74₸ or higher"
        ],
        [
            1087.09,
            679,
            "679 buy orders at 1 087,09₸ or higher"
        ],
        [
            1084.72,
            690,
            "690 buy orders at 1 084,72₸ or higher"
        ],
        [
            1082.04,
            702,
            "702 buy orders at 1 082,04₸ or higher"
        ],
        [
            1078.7,
            715,
            "715 buy orders at 1 078,70₸ or higher"
        ],
        [
            1078.14,
            727,
            "727 buy orders at 1 078,14₸ or higher"
        ],
        [
            1075.89,
            742,
            "742 buy orders at 1 075,89₸ or higher"
        ],
        [
            1074.26,
            752,
            "752 buy orders at 1 074,26₸ or higher"
        ],
        [
            1072.66,
            758,
            "758 buy orders at 1 072,66₸ or higher"
        ],
        [
            1066.64,
            765,
            "765 buy orders at 1 066,64₸ or higher"
        ],
        [
            1060.61,
            767,
            "767 buy orders at 1 060,61₸ or higher"
        ],
        [
            1060,
            779,
            "779 buy orders at 1 060₸ or higher"
        ],
        [
            1057.03,
            781,
            "781 buy orders at 1 057,03₸ or higher"
        ],
        [
            1056.41,
            797,
            "797 buy orders at 1 056,41₸ or higher"
        ],
        [
            1054.59,
            806,
            "806 buy orders at 1 054,59₸ or higher"
        ],
        [
            1052.17,
            811,
            "811 buy orders at 1 052,17₸ or higher"
        ],
        [
            1050.83,
            827,
            "827 buy orders at 1 050,83₸ or higher"
        ],
        [
            1050.46,
            835,
            "835 buy orders at 1 050,46₸ or higher"
        ],
        [
            1049.9,
            867,
            "867 buy orders at 1 049,90₸ or higher"
        ],
        [
            1049.16,
            871,
            "871 buy orders at 1 049,16₸ or higher"
        ],
        [
            1048.47,
            876,
            "876 buy orders at 1 048,47₸ or higher"
        ],
        [
            1048.35,
            888,
            "888 buy orders at 1 048,35₸ or higher"
        ],
        [
            1047.12,
            920,
            "920 buy orders at 1 047,12₸ or higher"
        ],
        [
            1044.74,
            932,
            "932 buy orders at 1 044,74₸ or higher"
        ],
        [
            1043.41,
            948,
            "948 buy orders at 1 043,41₸ or higher"
        ],
        [
            1042.53,
            949,
            "949 buy orders at 1 042,53₸ or higher"
        ],
        [
            1038.95,
            957,
            "957 buy orders at 1 038,95₸ or higher"
        ],
        [
            1037.03,
            968,
            "968 buy orders at 1 037,03₸ or higher"
        ],
        [
            1036.84,
            992,
            "992 buy orders at 1 036,84₸ or higher"
        ],
        [
            1036.72,
            1008,
            "1,008 buy orders at 1 036,72₸ or higher"
        ],
        [
            1036.51,
            1010,
            "1,010 buy orders at 1 036,51₸ or higher"
        ],
        [
            1036.03,
            1012,
            "1,012 buy orders at 1 036,03₸ or higher"
        ],
        [
            1033.75,
            1028,
            "1,028 buy orders at 1 033,75₸ or higher"
        ],
        [
            1032.27,
            1037,
            "1,037 buy orders at 1 032,27₸ or higher"
        ],
        [
            1030.48,
            1039,
            "1,039 buy orders at 1 030,48₸ or higher"
        ],
        [
            1028.15,
            1041,
            "1,041 buy orders at 1 028,15₸ or higher"
        ],
        [
            1026.9,
            1076,
            "1,076 buy orders at 1 026,90₸ or higher"
        ],
        [
            1026.68,
            1088,
            "1,088 buy orders at 1 026,68₸ or higher"
        ],
        [
            1024.15,
            1092,
            "1,092 buy orders at 1 024,15₸ or higher"
        ],
        [
            1022.7,
            1093,
            "1,093 buy orders at 1 022,70₸ or higher"
        ],
        [
            1021,
            1097,
            "1,097 buy orders at 1 021₸ or higher"
        ],
        [
            1020.1,
            1106,
            "1,106 buy orders at 1 020,10₸ or higher"
        ],
        [
            1018.1,
            1115,
            "1,115 buy orders at 1 018,10₸ or higher"
        ],
        [
            1014.09,
            1119,
            "1,119 buy orders at 1 014,09₸ or higher"
        ],
        [
            1014.07,
            1132,
            "1,132 buy orders at 1 014,07₸ or higher"
        ],
        [
            1011.63,
            1136,
            "1,136 buy orders at 1 011,63₸ or higher"
        ],
        [
            1011.19,
            1138,
            "1,138 buy orders at 1 011,19₸ or higher"
        ],
        [
            1006.9,
            1142,
            "1,142 buy orders at 1 006,90₸ or higher"
        ],
        [
            1005.37,
            1153,
            "1,153 buy orders at 1 005,37₸ or higher"
        ],
        [
            1004.29,
            1171,
            "1,171 buy orders at 1 004,29₸ or higher"
        ],
        [
            1002.27,
            1192,
            "1,192 buy orders at 1 002,27₸ or higher"
        ],
        [
            1000.18,
            1193,
            "1,193 buy orders at 1 000,18₸ or higher"
        ],
        [
            998.96,
            1209,
            "1,209 buy orders at 998,96₸ or higher"
        ],
        [
            995.36,
            1217,
            "1,217 buy orders at 995,36₸ or higher"
        ],
        [
            993.86,
            1239,
            "1,239 buy orders at 993,86₸ or higher"
        ],
        [
            992.52,
            1247,
            "1,247 buy orders at 992,52₸ or higher"
        ],
        [
            992.34,
            1264,
            "1,264 buy orders at 992,34₸ or higher"
        ],
        [
            991.62,
            1268,
            "1,268 buy orders at 991,62₸ or higher"
        ],
        [
            990.47,
            1279,
            "1,279 buy orders at 990,47₸ or higher"
        ],
        [
            987.74,
            1287,
            "1,287 buy orders at 987,74₸ or higher"
        ],
        [
            985.79,
            1291,
            "1,291 buy orders at 985,79₸ or higher"
        ],
        [
            983.41,
            1300,
            "1,300 buy orders at 983,41₸ or higher"
        ],
        [
            974.69,
            1308,
            "1,308 buy orders at 974,69₸ or higher"
        ],
        [
            972.38,
            1380,
            "1,380 buy orders at 972,38₸ or higher"
        ],
        [
            972.18,
            1382,
            "1,382 buy orders at 972,18₸ or higher"
        ],
        [
            971.35,
            1390,
            "1,390 buy orders at 971,35₸ or higher"
        ],
        [
            970.79,
            1406,
            "1,406 buy orders at 970,79₸ or higher"
        ],
        [
            967.06,
            1417,
            "1,417 buy orders at 967,06₸ or higher"
        ],
        [
            964.66,
            1421,
            "1,421 buy orders at 964,66₸ or higher"
        ],
        [
            964.2,
            1426,
            "1,426 buy orders at 964,20₸ or higher"
        ],
        [
            960.03,
            1434,
            "1,434 buy orders at 960,03₸ or higher"
        ],
        [
            958.94,
            1435,
            "1,435 buy orders at 958,94₸ or higher"
        ],
        [
            957.62,
            1447,
            "1,447 buy orders at 957,62₸ or higher"
        ],
        [
            957.51,
            1455,
            "1,455 buy orders at 957,51₸ or higher"
        ],
        [
            955.94,
            1464,
            "1,464 buy orders at 955,94₸ or higher"
        ],
        [
            952.6,
            1480,
            "1,480 buy orders at 952,60₸ or higher"
        ]
    ]

    # ==== Тест ====
    model = PTModel("EVA")
    y, amount, profit = model.predict(
            price=price,
            volume=volume,
            skin_orders=skin_orders,
            linreg=linreg,
        )

    print("\n[Результат EVA]")
    print(f"y = {y}")
    print(f"amount = {amount}")
    print(f"predict_profit = {profit}")

if __name__ == "__main__":
    test_eva()