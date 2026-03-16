import psycopg2
from psycopg2.extras import Json, DictCursor
from datetime import datetime, timezone, timedelta

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
        self.conn.set_client_encoding("UTF8")
        self.cursor = self.conn.cursor()


    def insert_or_update_orders(self, skin_id, skin_orders, sell_orders=None):
        if sell_orders is not None:
            self.cursor.execute("""
                INSERT INTO orders (skin_id, data, sell_orders)
                VALUES (%s, %s, %s)
                ON CONFLICT (skin_id) DO UPDATE
                SET data = EXCLUDED.data,
                 sell_orders = EXCLUDED.sell_orders 
            """, (skin_id, Json(skin_orders), Json(sell_orders)))
        else:
            self.cursor.execute("""
                INSERT INTO orders (skin_id, data)
                VALUES (%s, %s)
                ON CONFLICT (skin_id) DO UPDATE
                SET data = EXCLUDED.data
            """, (skin_id, Json(skin_orders)))

    def update_skin_orders_timestamp(self, skin_id):
        now = datetime.now(timezone.utc)
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE skins
                SET orders_timestamp = %s
                WHERE id = %s
            """, (now, skin_id))
        self.conn.commit()

    
    def update_skin_history_timestamp(self, skin_id):
        now = datetime.now(timezone.utc)
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE skins
                SET history_timestamp = %s
                WHERE id = %s
            """, (now, skin_id))
        self.conn.commit()



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

    def update_skins_analysis(self, id, data):    
        slope_6m, slope_1m, avg_month, avg_week, volume, high, low, moment, avg_5_sell_orders, avg_5_buy_orders, spread, mid_price, spread_percent, bid_depth = data

        now = datetime.now()

        self.cursor.execute("""
            INSERT INTO analysis_data (
                skin_id,
                analysis_timestamp,
                moment_price,
                volume,
                low_approx,
                high_approx,
                slope_1m,
                slope_6m,
                avg_month_price,
                avg_week_price,
                avg_5_sell_orders,
                avg_5_buy_orders,
                spread, 
                mid_price, 
                spread_percent, 
                bid_depth
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """, (
            id,
            now,
            moment,
            volume,
            low,
            high,
            slope_1m,
            slope_6m,
            avg_month,
            avg_week,
            avg_5_sell_orders,
            avg_5_buy_orders,
            spread,
            mid_price,
            spread_percent,
            bid_depth
        ))
        
        analysis_id = self.cursor.fetchone()[0]
        
        self.cursor.execute("""
            UPDATE skins
            SET analysis_timestamp = %s
            WHERE id = %s
        """,(now, id))
        return analysis_id

    def log_placement(self, skin_id, name, y, amount, model_type, placed_snapshot):
        self.cursor.execute("""
            INSERT INTO logs (skin_id, name, y, amount, model_type, placed_time, placed_snapshot)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (skin_id, name, y, amount, model_type, datetime.now().isoformat(), Json(placed_snapshot)))

    def commit(self):
        """Коммит транзакции"""
        try:
            self.conn.commit()
        except Exception as e:
            print(f"[DB] Commit failed: {e}")
            raise

    def close(self):
        self.cursor.close()
        self.conn.close()
        
    def get_filtered_skins(self, max_price, my_orders: list[str]):
        self.cursor.execute(
            """
            SELECT id, name, orders_timestamp, analysis_timestamp, item_name_id
            FROM skins_with_analysis
            WHERE 
                COALESCE(avg_month_price, moment_price) < %s
                AND volume > 70
                AND COALESCE(avg_month_price, moment_price) > 20
                AND item_name_id IS NOT NULL
                AND name NOT IN (SELECT name FROM logs)
                AND name <> ALL(%s)
            ORDER BY volume()
            """,
            (
                max_price,
                my_orders if my_orders else []
            )
        )
        return self.cursor.fetchall()


    def get_skins(self, inventory):
        skin_names = tuple(skin[0] for skin in inventory)
        
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    s.id,
                    s.name,
                    s.analysis_timestamp,
                    s.appearance_date,
                    s.item_name_id,
                    s.orders_timestamp,
                    s.history_timestamp,
                    -- Получаем последнюю цену покупки
                    (
                        SELECT price
                        FROM order_events oe
                        WHERE oe.name = s.name
                        AND oe.event_type = 'BUY_PLACED'
                        ORDER BY oe.created_at DESC
                        LIMIT 1
                    ) AS buy_price
                FROM skins s
                WHERE s.name IN %s
            """, (skin_names,))
            
            rows = cursor.fetchall()
            
            # Возвращаем dict по имени с buy_price как отдельным полем
            return {row["name"]: row for row in rows}





    def log_sell_orders(self, data):
        self.cursor.execute("""
            INSERT INTO sell_orders (
                skin_id,
                status,
                name,
                snapshot,
                buy_price,
                sell_price,
                profit,
                asset_id,
                classid,
                instanceid,
                float_value,
                int_pattern
            )
            VALUES (
                %s, 'active', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, data)




    def add_skin(self, skin_name):
        self.cursor.execute("""
            INSERT INTO skins (name)
            VALUES (%s)
        """, (skin_name,))
    
    def insert_stickers_to_db(self, string):
        self.cursor.execute("""
                                INSERT INTO stickers (name)
                                VALUES (%s) ON CONFLICT (name) DO NOTHING
                            """, (string,))
    
    def rollback(self):
        """Откат транзакции при ошибке"""
        try:
            self.conn.rollback()
        except Exception as e:
            print(f"[DB] Rollback failed: {e}")
            
    def get_data_for_test_strategy(self, name):
        self.cursor.execute("""
                            select id from skins where name=(%s)
                            """, (name,))
        skin_id = self.cursor.fetchone()
        
        self.cursor.execute("""
                            select date, price, volume from pricehistory where skin_id=(%s)
                            """, (skin_id,))
        history = self.cursor.fetchall()
        
        self.cursor.execute("""
                            select data, sell_orders from orders where skin_id=(%s);
                            """, (skin_id,))
        buy_orders, sell_orders = self.cursor.fetchone()
        return history, buy_orders, sell_orders
    
    def get_all_skins(self, until_date):
        if until_date is not None:
            self.cursor.execute("""
                                select * from skins 
                                where item_name_id is not null 
                                AND (analysis_timestamp < %s or analysis_timestamp is NULL)
                                order by analysis_timestamp asc; 
                                """, (until_date, ))
        else:
            self.cursor.execute("""
                                select * from skins 
                                where item_name_id is not null 
                                order by analysis_timestamp asc; 
                                """)
        return self.cursor.fetchall()

    def get_skins_without_item_nameid(self):
        self.cursor.execute(
            """
            select name from skins where item_name_id is NULL 
            """
        )
        return self.cursor.fetchall()
    
    def save_item_name_id(self, skin_name, item_name_id):
        self.cursor.execute(
            """
            UPDATE skins
            SET 
            item_name_id = %s
            WHERE name = %s
            """,
            (item_name_id, skin_name),
        )
        
    def get_test_skin(self, skin):
        self.cursor.execute("""
                                SELECT id, name, orders_timestamp, history_timestamp, item_name_id FROM skins WHERE name = %s
                                """, (skin, ))
        return self.cursor.fetchone()
    
    def buy_placed(self, skin_name, price, amount, analysis_id):
        self.cursor.execute("""
            INSERT INTO order_events (name, price, amount, event_type, analysis_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (skin_name, price, amount, 'BUY_PLACED', analysis_id))
        self.commit()

    def insert_filled(self, new_event_type, skin_name, price, amount, analysis_id):
        """
        new_event_type: тип события, которое вставляем ('BUY_FILLED', 'SELL_PLACED', 'SELL_FILLED')
        """
        self.cursor.execute(f"""
            SELECT p.id, p.amount - COALESCE(SUM(f.amount),0) AS remaining
            FROM order_events p
            LEFT JOIN order_events f
            ON f.parent_id = p.id AND f.event_type = %s
            WHERE p.event_type = %s AND p.name = %s
            GROUP BY p.id, p.amount
            HAVING (p.amount - COALESCE(SUM(f.amount),0)) >= %s
            ORDER BY p.created_at
            LIMIT 1
        """, (new_event_type, 'BUY_PLACED', skin_name, amount))
        
        row = self.cursor.fetchone()
        if not row:
            raise Exception(f"No available BUY_PLACED with enough remaining amount")
        
        parent_id = row[0]
        
        self.cursor.execute("""
            INSERT INTO order_events (parent_id, event_type, amount, price, analysis_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (parent_id, new_event_type, amount, price, analysis_id))
        self.commit()

    def insert_my_history(self, my_history):
        try:
            self.cursor.execute("BEGIN")

            self.cursor.executemany("""
                INSERT INTO history_validator (
                    asset_id,
                    name,
                    price,
                    acted_on,
                    listed_on,
                    gain_or_loss
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, my_history)

            self.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"DB insert error: {e}")
            # do nothing
    
    def get_sell_placed_events(self):
        self.cursor.execute("""
            WITH buy_summary AS (
                SELECT
                    bp.id AS buy_placed_id,
                    bp.name,
                    bp.amount AS buy_placed_amount
                FROM order_events bp
                WHERE bp.event_type = 'BUY_PLACED'
            ),
            sell_placed_summary AS (
                SELECT parent_id AS buy_placed_id, SUM(amount) AS sell_placed_amount
                FROM order_events
                WHERE event_type = 'SELL_PLACED'
                GROUP BY parent_id
            ),
            sell_filled_summary AS (
                SELECT parent_id AS buy_placed_id, SUM(amount) AS sell_filled_amount
                FROM order_events
                WHERE event_type = 'SELL_FILLED'
                GROUP BY parent_id
            )
            SELECT
                b.buy_placed_id,
                b.name,
                COALESCE(sfs.sell_filled_amount,0) AS sell_filled_amount,
                COALESCE(sps.sell_placed_amount,0) - COALESCE(sfs.sell_filled_amount,0) AS remaining_to_sell
            FROM buy_summary b
            LEFT JOIN sell_placed_summary sps ON sps.buy_placed_id = b.buy_placed_id
            LEFT JOIN sell_filled_summary sfs ON sfs.buy_placed_id = b.buy_placed_id
            WHERE COALESCE(sps.sell_placed_amount,0) - COALESCE(sfs.sell_filled_amount,0) > 0;

        """)
        return self.cursor.fetchall() # buy_placed_id, name, sell_filled_amount, remaining_to_sell
    
    
    def get_skins_without_price(self, skins):
        skin_names = tuple(skin for skin in skins)
        self.cursor.execute("""
            SELECT 
                *
            FROM skins
            WHERE name IN %s
        """, (skin_names,))

        return self.cursor.fetchall()
    
    
    def insert_filled_bulk(self, events):
        """
        events: список кортежей (new_event_type, skin_name, price, amount, analysis_id)
        new_event_type: 'BUY_FILLED' | 'SELL_PLACED' | 'SELL_FILLED'
        """
        insert_rows = []
        
        for item in events:
            new_event_type, skin_name, price, amount, analysis_id = item
            # ищем подходящий BUY_PLACED
            self.cursor.execute("""
                SELECT p.id, p.amount - COALESCE(SUM(f.amount),0) AS remaining
                FROM order_events p
                LEFT JOIN order_events f
                ON f.parent_id = p.id AND f.event_type = %s
                WHERE p.event_type = %s AND p.name = %s
                GROUP BY p.id, p.amount
                HAVING (p.amount - COALESCE(SUM(f.amount),0)) >= %s
                ORDER BY p.created_at
                LIMIT 1
            """, (new_event_type, 'BUY_PLACED', skin_name, amount))

            row = self.cursor.fetchone()
            if not row:
                raise Exception(f"No available BUY_PLACED with enough remaining amount for {skin_name}")

            parent_id = row[0]

            insert_rows.append((parent_id, new_event_type, amount, price, analysis_id, skin_name))

        # массовая вставка
        self.cursor.executemany("""
            INSERT INTO order_events (parent_id, event_type, amount, price, analysis_id, name)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, insert_rows)

        self.commit()
        
    def get_full_transaction(self, from_date):
        to_date = from_date + timedelta(days=1)
        self.cursor.execute("""
            SELECT *
            FROM order_events
            WHERE COALESCE(parent_id, id) IN (
                SELECT COALESCE(parent_id, id)
                FROM order_events
                GROUP BY COALESCE(parent_id, id)
                HAVING 
                    BOOL_OR(event_type = 'BUY_PLACED')
                    AND BOOL_OR(event_type = 'BUY_FILLED')
                    AND BOOL_OR(event_type = 'SELL_PLACED')
                    AND BOOL_OR(event_type = 'SELL_FILLED')
                    AND MAX(CASE WHEN event_type = 'SELL_FILLED' THEN created_at END) 
                    BETWEEN %s AND %s
            )
            ORDER BY COALESCE(parent_id, id), created_at;
            """, (from_date, to_date))
        return self.cursor.fetchall()
