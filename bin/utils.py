import urllib.parse
def generate_market_url(skin_name):
    """Генерирует URL для скина на маркете Steam."""
    encoded_name = urllib.parse.quote(skin_name)
    url = f"https://steamcommunity.com/market/listings/730/{encoded_name}"
    return url

from datetime import datetime, timezone

def normalize_date(raw_date):
    """Преобразует дату (строку ISO или datetime) в UTC-aware datetime, округлённый до часа."""
    if isinstance(raw_date, str):
        try:
            dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Не удалось распарсить дату: {raw_date}")
    elif isinstance(raw_date, datetime):
        dt = raw_date
    else:
        raise TypeError(f"Ожидалась строка или datetime, а получено: {type(raw_date)}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Округляем до часа
    dt = dt.replace(minute=0, second=0, microsecond=0)
    return dt

def process_to_table():
    """
    """
    import pandas as pd

    # Original list of buy orders
    buy_orders = [
        [2215.87, 1, '1 buy orders at 2 215,87₸ or higher'], [2203.49, 6, '6 buy orders at 2 203,49₸ or higher'],
        [2197.3, 30, '30 buy orders at 2 197,30₸ or higher'], [2172.53, 45, '45 buy orders at 2 172,53₸ or higher'],
        [2165.69, 48, '48 buy orders at 2 165,69₸ or higher'], [2130.3, 51, '51 buy orders at 2 130,30₸ or higher'],
        [2067.32, 54, '54 buy orders at 2 067,32₸ or higher'], [2064.89, 56, '56 buy orders at 2 064,89₸ or higher'],
        [2032.53, 68, '68 buy orders at 2 032,53₸ or higher'], [2029.17, 69, '69 buy orders at 2 029,17₸ or higher'],
        [2011.61, 81, '81 buy orders at 2 011,61₸ or higher'], [1999.23, 93, '93 buy orders at 1 999,23₸ or higher'],
        [1993.04, 107, '107 buy orders at 1 993,04₸ or higher'], [1986.86, 177, '177 buy orders at 1 986,86₸ or higher'],
        [1986.3, 181, '181 buy orders at 1 986,30₸ or higher'], [1979.16, 186, '186 buy orders at 1 979,16₸ or higher'],
        [1977.93, 194, '194 buy orders at 1 977,93₸ or higher'], [1974.47, 196, '196 buy orders at 1 974,47₸ or higher'],
        [1968.28, 198, '198 buy orders at 1 968,28₸ or higher'], [1933.38, 200, '200 buy orders at 1 933,38₸ or higher'],
        [1912.58, 206, '206 buy orders at 1 912,58₸ or higher'], [1900.19, 215, '215 buy orders at 1 900,19₸ or higher'],
        [1855.27, 216, '216 buy orders at 1 855,27₸ or higher'], [1838.3, 217, '217 buy orders at 1 838,30₸ or higher'],
        [1828.43, 221, '221 buy orders at 1 828,43₸ or higher'], [1819.1, 229, '229 buy orders at 1 819,10₸ or higher'],
        [1813.55, 230, '230 buy orders at 1 813,55₸ or higher'], [1813.2, 236, '236 buy orders at 1 813,20₸ or higher'],
        [1807.36, 239, '239 buy orders at 1 807,36₸ or higher'], [1802.05, 240, '240 buy orders at 1 802,05₸ or higher'],
        [1801.16, 242, '242 buy orders at 1 801,16₸ or higher'], [1790.18, 243, '243 buy orders at 1 790,18₸ or higher'],
        [1783.08, 247, '247 buy orders at 1 783,08₸ or higher'], [1764.98, 249, '249 buy orders at 1 764,98₸ or higher'],
        [1757.83, 250, '250 buy orders at 1 757,83₸ or higher'], [1748, 252, '252 buy orders at 1 748₸ or higher'],
        [1744.39, 263, '263 buy orders at 1 744,39₸ or higher'], [1726.89, 264, '264 buy orders at 1 726,89₸ or higher'],
        [1698.36, 268, '268 buy orders at 1 698,36₸ or higher'], [1683.55, 269, '269 buy orders at 1 683,55₸ or higher'],
        [1671.19, 277, '277 buy orders at 1 671,19₸ or higher'], [1646.76, 297, '297 buy orders at 1 646,76₸ or higher'],
        [1645.2, 299, '299 buy orders at 1 645,20₸ or higher'], [1621.9, 310, '310 buy orders at 1 621,90₸ or higher'],
        [1619.25, 314, '314 buy orders at 1 619,25₸ or higher'], [1615.47, 315, '315 buy orders at 1 615,47₸ or higher'],
        [1602.49, 316, '316 buy orders at 1 602,49₸ or higher'], [1587.07, 317, '317 buy orders at 1 587,07₸ or higher'],
        [1584.53, 323, '323 buy orders at 1 584,53₸ or higher'], [1578.34, 331, '331 buy orders at 1 578,34₸ or higher'],
        [1553.58, 339, '339 buy orders at 1 553,58₸ or higher'], [1552.89, 344, '344 buy orders at 1 552,89₸ or higher'],
        [1511, 355, '355 buy orders at 1 511₸ or higher'], [1479.3, 439, '439 buy orders at 1 479,30₸ or higher'],
        [1479.22, 445, '445 buy orders at 1 479,22₸ or higher'], [1460.7, 451, '451 buy orders at 1 460,70₸ or higher'],
        [1430.28, 452, '452 buy orders at 1 430,28₸ or higher'], [1407.55, 460, '460 buy orders at 1 407,55₸ or higher'],
        [1381.22, 461, '461 buy orders at 1 381,22₸ or higher'], [1380.27, 465, '465 buy orders at 1 380,27₸ or higher'],
        [1364.25, 467, '467 buy orders at 1 364,25₸ or higher'], [1361.71, 477, '477 buy orders at 1 361,71₸ or higher'],
        [1356.83, 485, '485 buy orders at 1 356,83₸ or higher'], [1341.82, 495, '495 buy orders at 1 341,82₸ or higher'],
        [1339.64, 497, '497 buy orders at 1 339,64₸ or higher'], [1333.26, 510, '510 buy orders at 1 333,26₸ or higher'],
        [1330.74, 532, '532 buy orders at 1 330,74₸ or higher'], [1326.73, 541, '541 buy orders at 1 326,73₸ or higher'],
        [1312.51, 549, '549 buy orders at 1 312,51₸ or higher'], [1312.23, 562, '562 buy orders at 1 312,23₸ or higher'],
        [1312.19, 582, '582 buy orders at 1 312,19₸ or higher'], [1307.51, 595, '595 buy orders at 1 307,51₸ or higher'],
        [1306.7, 605, '605 buy orders at 1 306,70₸ or higher'], [1299.8, 617, '617 buy orders at 1 299,80₸ or higher'],
        [1293.61, 637, '637 buy orders at 1 293,61₸ or higher'], [1293.09, 643, '643 buy orders at 1 293,09₸ or higher'],
        [1287.43, 654, '654 buy orders at 1 287,43₸ or higher'], [1286.66, 664, '664 buy orders at 1 286,66₸ or higher'],
        [1276.55, 674, '674 buy orders at 1 276,55₸ or higher'], [1274.45, 687, '687 buy orders at 1 274,45₸ or higher'],
        [1271.21, 700, '700 buy orders at 1 271,21₸ or higher'], [1267, 713, '713 buy orders at 1 267₸ or higher'],
        [1259.37, 724, '724 buy orders at 1 259,37₸ or higher'], [1256.6, 730, '730 buy orders at 1 256,60₸ or higher'],
        [1256.49, 741, '741 buy orders at 1 256,49₸ or higher'], [1251.74, 754, '754 buy orders at 1 251,74₸ or higher'],
        [1250.36, 774, '774 buy orders at 1 250,36₸ or higher'], [1244.37, 778, '778 buy orders at 1 244,37₸ or higher'],
        [1244.3, 789, '789 buy orders at 1 244,30₸ or higher'], [1244.1, 797, '797 buy orders at 1 244,10₸ or higher'],
        [1236.09, 811, '811 buy orders at 1 236,09₸ or higher'], [1231.5, 817, '817 buy orders at 1 231,50₸ or higher'],
        [1225.53, 827, '827 buy orders at 1 225,53₸ or higher'], [1224.91, 830, '830 buy orders at 1 224,91₸ or higher'],
        [1221.91, 831, '831 buy orders at 1 221,91₸ or higher'], [1213.53, 851, '851 buy orders at 1 213,53₸ or higher'],
        [1209.3, 853, '853 buy orders at 1 209,30₸ or higher'], [1206.4, 856, '856 buy orders at 1 206,40₸ or higher'],
        [1205.55, 868, '868 buy orders at 1 205,55₸ or higher'], [1194.3, 871, '871 buy orders at 1 194,30₸ or higher'],
        [1185.1, 873, '873 buy orders at 1 185,10₸ or higher']
    ]

    # Create DataFrame
    df = pd.DataFrame(buy_orders, columns=["Price (₸)", "Order Count", "Description"])

    # Display the table to user
    print(df)
