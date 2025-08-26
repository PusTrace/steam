
def check_CupAndLoss(my_price, current_price, orders, volume):
    if round(current_price, 2) / 0.87 < round(my_price, 2):
        return True

    if volume is None:
        print("Объем равен None")
        return False
    else:
        volume = int(volume.replace(" ", "").replace(",", ""))
    buy_order_graph = orders.get("buy_order_graph")
    
    df = pd.DataFrame(buy_order_graph, columns=['price', 'count', 'description'])
    df['price_rounded'] = df['price'].round(2)

    # Округляем my_price отдельно
    my_price_rounded = round(my_price, 2)
    
    # Вместо query просто фильтруем по маске
    match = df[df['price_rounded'] == my_price_rounded]
    if not match.empty:
        order_count = int(match.iloc[0]['count'])
        return volume * 32 > order_count
    else:
        print(f"Ордер с ценой {my_price_rounded} не найден в списке. Ошибка в проверке CupAndLoss.")
        return False


if __name__ == "__main__":
    
    # 1. launch driver and get cookies
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    cookies = driver_normal.get_cookies()
    driver_normal.quit()

    # 2. connect to db
    load_dotenv()
    db = PostgreSQLDB(password=os.getenv("DEFAULT_PASSWORD"))

    # 3. get data from api
    inventory = get_inventory(cookies)
    db.log_orders_complete()

    logs = db.get_logged_skins()

    # check orders which is not in inventory
    orders_dict = get_list_of_my_orders(cookies)

    for skin in logs:
        if skin in inventory:
            continue  # пропускаем, обработаем позже

        my_price = data.get("order_price")
        url = data.get("url")
        if skin in orders_dict:
            buy_order_id = orders_dict[skin]
        else:
            continue
        if skin in item_nameids:
            skin_id = item_nameids[skin]

        if skin in all_orders:
            date_orders = all_orders[skin].get("timestamp_orders")
            timestamp_orders = datetime.fromisoformat(date_orders).date()

        if skin in database:
            date_price = database[skin].get("timestamp")    
            timestamp_price = datetime.fromisoformat(date_price).date()

        print(f"Получение данных для '{skin}' .")
        price, orders = get_market_data(skin, skin_id, timestamp_orders, timestamp_price, proxies)
        
        lowest_price = price.get("lowest_price")
        median_price = price.get("median_price")
        volume = price.get("volume")
        
        if median_price:
            current_price = float(median_price.replace("₸", "").replace(",", ".").replace(" ", "").strip())
        else:
            current_price = float(lowest_price.replace("₸", "").replace(",", ".").replace(" ", "").strip())
        
        CupAndLoss = check_CupAndLoss(my_price, current_price, orders, volume)
        if CupAndLoss:
            cancel_order(skin, buy_order_id, cookies)