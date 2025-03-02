import json

def analyze_database(input_filename, output_filename, price_threshold, volume_threshold):
    """Анализирует базу данных и сохраняет объекты, подходящие по параметрам, в новый файл."""
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        filtered_data = {}

        def parse_price(price):
            """Преобразует строку цены в float, если она есть, иначе возвращает None."""
            if price:
                return float(price.replace('₸', '').replace(' ', '').replace(',', '.'))
            return None

        for item, details in data.items():
            # Преобразуем цены в числа
            details["lowest_price"] = parse_price(details.get("lowest_price"))
            details["median_price"] = parse_price(details.get("median_price"))

            # Берем медианную цену, если есть, иначе минимальную
            price_reference = details["median_price"] if details["median_price"] is not None else details["lowest_price"]

            if price_reference is None:
                continue  # Пропускаем, если нет ни одной цены


            # Обрабатываем volume
            volume = details.get("volume")
            if volume is not None:
                details["volume"] = int(volume.replace(',', '').replace(' ', ''))
            else:
                details["volume"] = 0  # Устанавливаем 0, если volume отсутствует

            # Проверяем условия фильтрации
            if price_reference < price_threshold and details["volume"] >= volume_threshold:
                filtered_data[item] = details
                print(f"Добавлено: {item} с ценой {price_reference} и объемом {details['volume']}")

        # Сохраняем отфильтрованные данные в новый файл
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=4)

        print(f"Отфильтрованные данные успешно сохранены в {output_filename}")

    except Exception as e:
        print(f"Ошибка при анализе базы данных: {e}")

# Вызов функции
if __name__ == "__main__":
    analyze_database("steam/database/database.json", "steam/database/filtred_price&volume.json", price_threshold=1000, volume_threshold=30)
