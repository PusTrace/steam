import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from bin.utils import normalize_date

class PostgreSQLDB:
    def __init__(self, host, port, dbname, user, password):
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


    def update_skins_analysis(self, id, price, volume, approx_max, approx_min, linreg_change):
        self.cursor.execute("""
            UPDATE skins
            SET price = %s,
                volume = %s,
                approx_max = %s,
                approx_min = %s,
                analysis_timestamp = %s,
                linreg = %s
            WHERE id = %s
        """, (price, volume, approx_max, approx_min, datetime.now().isoformat(), linreg_change, id))

    def insert_log(self, skin_id, price, amount, profit, model_type):
        self.cursor.execute("""
            INSERT INTO logs (skin_id, event_type, event_time, price, quantity, profit, model_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (skin_id, "placement", datetime.now().isoformat(), price, amount, profit, model_type))

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()
        
    def get_filtred_skins(self):
        self.cursor.execute(
            """
            SELECT id, name, orders_timestamp, price_timestamp, item_name_id
            FROM skins
            WHERE 
                price < 1500
                AND price > 20
                AND volume > 10
                AND item_name_id IS NOT NULL
                AND linreg > 0
            """,
        )
        return self.cursor.fetchall()
    
