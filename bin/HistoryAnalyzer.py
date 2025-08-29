import numpy as np
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from steam.bin.PostgreSQLDB import PostgreSQLDB
import os
import matplotlib.pyplot as plt
from collections import defaultdict

class HistoryAnalyzer:
    def __init__(self, history, debug=False):
        """
        history: список записей [datetime, price, volume]
        """
        self.history = sorted(history, key=lambda r: r[0])
        self.moment_price = self.history[-1][1]
        self.aggregate_daily()
        if debug:
            self.raw_history = list(self.history)  # сохраняем исходную историю для отладки

        self.now = datetime.now(timezone.utc)
        self.one_week_ago = self.now - timedelta(days=7)
        self.one_month_ago = self.now - timedelta(days=30)
        self.six_month_ago = self.now - timedelta(days=180)

    def calc_avg(self):
        week_prices = []
        month_prices = []

        for dt, price, v in self.history:
            if dt >= self.one_week_ago:
                week_prices.append(price)
            if dt >= self.one_month_ago:
                month_prices.append(price)

        avg_week_price = sum(week_prices) / len(week_prices) if week_prices else None
        avg_month_price = sum(month_prices) / len(month_prices) if month_prices else None
        
        return avg_month_price, avg_week_price

    def bef_cleaning_summary(self):
        """
        Возвращает аппрокс. высокую и низкую цену за неделю.
        """
        month_prices = []
        week_volumes = []

        for dt, price, volume in self.history:
            if dt >= self.one_week_ago:
                week_volumes.append(volume)
            if dt >= self.one_month_ago:
                month_prices.append(price)

        volume = sum(week_volumes) if week_volumes else None

        sorted_month = sorted(month_prices)
        high_approx = sum(sorted_month[-3:]) / min(3, len(sorted_month)) if sorted_month else None
        low_approx = sum(sorted_month[:3]) / min(3, len(sorted_month)) if sorted_month else None
        

        return high_approx, low_approx, volume, self.moment_price

    def remove_price_outliers_iqr(self, factor=1.5, debug=False):
        """
        Удаляет выбросы внутри каждого месяца по IQR.
        factor — множитель чувствительности IQR (обычно 1.5)
        """
        if not self.history:
            return

        # Группировка по (год, месяц)
        monthly_groups = defaultdict(list)
        for rec in self.history:
            dt = rec[0]  # datetime
            key = (dt.year, dt.month)
            monthly_groups[key].append(rec)

        cleaned = []

        for key in sorted(monthly_groups.keys()):
            month_records = monthly_groups[key]
            prices = np.array([rec[1] for rec in month_records])

            if len(prices) < 4:
                cleaned.extend(month_records)
                continue

            q1 = np.percentile(prices, 25)
            q3 = np.percentile(prices, 75)
            iqr = q3 - q1

            lower = q1 - factor * iqr
            upper = q3 + factor * iqr

            filtered = [rec for rec in month_records if lower <= rec[1] <= upper]

            if debug:
                outliers = [rec for rec in month_records if rec not in filtered]
                print(f"[{key}] удалено {len(outliers)} выбросов")

            cleaned.extend(filtered)

        self.history = sorted(cleaned, key=lambda r: r[0])

    def linreg(self, since_dt):
        """Возвращает (наклон, пересечение, x, y) для истории с since_dt до now"""
        # фильтруем точки за нужный период
        filtered = [(d, p) for d, p, v in self.history if d >= since_dt]
        if len(filtered) < 2:
            return None  # данных мало – регрессия бессмысленна

        # превращаем даты в x (число дней от начала периода)
        start = filtered[0][0]
        x = np.array([(d - start).total_seconds() / 86400 for d, _ in filtered])
        y = np.array([(p) for _, p in filtered])

        # линейная регрессия 1-й степени
        slope, intercept = np.polyfit(x, y, 1)
        return slope, intercept, x, y
    
    def calc_trends(self):
        """
        Возвращает словарь с параметрами трендов:
        {
            "6m": {"slope": ..., "intercept": ...},
            "1m": {"slope": ..., "intercept": ...}
        }
        """
        result = {}
        six_m = self.linreg(self.six_month_ago)
        one_m = self.linreg(self.one_month_ago)

        if six_m:
            slope, intercept, *_ = six_m
            result["6m"] = {"slope": slope, "intercept": intercept}
        else:
            result["6m"] = None

        if one_m:
            slope, intercept, *_ = one_m
            result["1m"] = {"slope": slope, "intercept": intercept}
        else:
            result["1m"] = None

        return result
    
    def aggregate_daily(self):
        """
        Если в одном дне несколько записей — берём среднюю цену и суммарный объём.
        Возвращает список [datetime (начало дня UTC), avg_price, total_volume]
        """
        daily = defaultdict(list)

        for dt, price, volume in self.history:
            day = dt.date()  # группируем только по дате
            daily[day].append((price, volume))

        aggregated = []
        for day, records in daily.items():
            prices = [p for p, _ in records]
            volumes = [v for _, v in records]
            avg_price = sum(prices) / len(prices)
            total_volume = sum(volumes)
            day_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
            aggregated.append([day_start, avg_price, total_volume])

        # сортируем по дате
        aggregated.sort(key=lambda r: r[0])
        self.history = aggregated
    
def plot_history(history, title, analyzer):
    # history = [(datetime, price, volume), ...]
    dates = [d for d, p, v in history]
    prices = [p for d, p, v in history]

    plt.figure(figsize=(12, 6))
    plt.plot(dates, prices, label="Цена", color='blue')

    raw_dates = [d for d, p, v in analyzer.raw_history]
    raw_prices = [p for d, p, v in analyzer.raw_history]
    plt.plot(raw_dates, raw_prices, label="До очистки", color='gray', alpha=0.4)
    # Получаем тренды
    trends = analyzer.calc_trends()

    for label, color in [("6m", "red"), ("1m", "green")]:
        t = trends.get(label)
        if not t:
            continue

        slope, intercept = t["slope"], t["intercept"]

        # Для построения оси X относительно начала периода
        since_dt = analyzer.six_month_ago if label == "6m" else analyzer.one_month_ago
        filtered = [(d, p) for d, p, v in history if d >= since_dt]
        if len(filtered) < 2:
            continue

        start = filtered[0][0]
        x_days = np.array([(d - start).total_seconds() / 86400 for d, _ in filtered])
        y_pred = slope * x_days + intercept
        print(f"Тренд {label}: наклон={slope}, пересечение={intercept}")

        plt.plot(
            [d for d, _ in filtered],
            y_pred,
            label=f"Лин. тренд {label}",
            color=color,
            linestyle="--"
        )

    plt.title(title)
    plt.legend()
    plt.show()

def preprocessing(history, debug=False):
    """
    Выполняет предобработку истории цен и возвращает наклоны трендов.
    """
    analyzer = HistoryAnalyzer(history, debug=debug)

    high_approx, low_approx, volume, moment_price = analyzer.bef_cleaning_summary()  # аппрокс. высокая и низкая цена за неделю
    # remove outliers factor=0.2
    analyzer.remove_price_outliers_iqr(0.2, debug)

    six_m = analyzer.linreg(analyzer.six_month_ago)
    if six_m:
        slope_six_m, *_= six_m
    one_m = analyzer.linreg(analyzer.one_month_ago)
    if one_m:
        slope_one_m, *_ = one_m
    if debug:
        plot_history(analyzer.history, "История цен", analyzer)

    avg_month_price, avg_week_price = analyzer.calc_avg()

    return slope_six_m, slope_one_m, avg_month_price, avg_week_price, volume, high_approx, low_approx, moment_price

def test():
    load_dotenv()
    db = PostgreSQLDB(password=os.getenv("DEFAULT_PASSWORD"))
    skin_id = 245  # Пример ID скина
    db.cursor.execute("""
        SELECT date, price, volume
        FROM pricehistory
        WHERE skin_id = %s
        AND date >= NOW() - INTERVAL '6 months'
        ORDER BY date ASC;
    """, (skin_id,))
    history = db.cursor.fetchall()

    linreg_6m, linreg_1m, avg_month_price, avg_week_price, volume, high_approx, low_approx, moment_price = preprocessing(history, debug=True)
    print(f"slope_six_m = {linreg_6m}, slope_one_m = {linreg_1m}, avg_month_price = {avg_month_price}, avg_week_price = {avg_week_price}, total_week_volume = {volume}, high_approx = {high_approx}, low_approx = {low_approx}, moment_price = {moment_price}")

if __name__ == "__main__":
    print("preprocess.py is a module, not a script. Use it as an import in your code.")
    test()