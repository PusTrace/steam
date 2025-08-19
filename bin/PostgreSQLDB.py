import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from bin.utils import normalize_date

class PostgreSQLDB:
    def __init__(
        self,
        host="127.0.0.1",
        port=5432,
        dbname="steam",
        user="postgres",
        password="DEFAULT_PASSWORD"
    ):
        self.conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        self.cursor = self.conn.cursor()


    def insert_or_update_orders(self, skin_id, skin_orders):
        self.cursor.execute("""
            INSERT INTO orders (skin_id, data)
            VALUES (%s, %s)
            ON CONFLICT (skin_id) DO UPDATE
            SET data = EXCLUDED.data
        """, (skin_id, Json(skin_orders)))

    def update_skin_orders_timestamp(self, skin_id):
        self.cursor.execute("""
            UPDATE skins
            SET orders_timestamp = %s
            WHERE id = %s
        """, (datetime.now().isoformat(), skin_id))

    def update_skin_price_timestamp(self, skin_id):
        self.cursor.execute("""
            UPDATE skins
            SET price_timestamp = %s
            WHERE id = %s
        """, (datetime.now().isoformat(), skin_id))

    def update_price_history(self, skin_id, price_history):
        # Получаем уже существующие даты для этого skin_id
        self.cursor.execute("""
            SELECT date FROM pricehistory WHERE skin_id = %s
        """, (skin_id,))
        existing_dates = set(row[0] for row in self.cursor.fetchall())

        to_insert = []

        for record in price_history:
            raw_date, price, volume = record
            dt = normalize_date(raw_date)
            # Вставляем только если ещё не существует
            if dt not in existing_dates:
                to_insert.append((skin_id, dt, price, volume))

        # Массовая вставка новых записей
        if to_insert:
            self.cursor.executemany("""
                INSERT INTO pricehistory (skin_id, date, price, volume)
                VALUES (%s, %s, %s, %s)
            """, to_insert)

    def update_skins_analysis(self, id, moment_price, volume, high_approx, low_approx,
                            slope_six_m, slope_one_m, avg_month_price, avg_week_price):

        # Приводим к обычным float
        slope_six_m = float(slope_six_m)
        slope_one_m = float(slope_one_m)
        avg_month_price = float(avg_month_price)
        avg_week_price = float(avg_week_price)

        self.cursor.execute("""
            UPDATE skins
            SET moment_price = %s,
                volume = %s,
                high_approx = %s,
                low_approx = %s,
                analysis_timestamp = %s,
                linreg_6m = %s,
                linreg_1m = %s,
                avg_month_price = %s,
                avg_week_price = %s
            WHERE id = %s
        """, (
            moment_price,
            volume,
            high_approx,
            low_approx,
            datetime.now(),
            slope_six_m,
            slope_one_m,
            avg_month_price,
            avg_week_price,
            id
        ))

    def log_placement(self, skin_id, name, y, amount, model_type, placed_snapshot):
        self.cursor.execute("""
            INSERT INTO logs (skin_id, name, y, amount, model_type, placed_time, placed_snapshot)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (skin_id, name, y, amount, model_type, datetime.now().isoformat(), Json(placed_snapshot)))

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()
        
    def get_filtered_skins(self, price):  # TODO: change moment price to avg
        self.cursor.execute(
            """
            SELECT id, name, orders_timestamp, price_timestamp, item_name_id
            FROM skins
            WHERE 
                moment_price < %s
                AND moment_price > 20
                AND volume > 10
                AND item_name_id IS NOT NULL
                AND name NOT IN (SELECT name FROM logs)
            """, (price,)
        )
        return self.cursor.fetchall()

    
