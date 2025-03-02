import json

def analyze_database(input_filename="main/database/graph_flatness_unsorted.json", output_filename="main/database/graph_flatness.json", net_change_threshold=-2):
    """Анализирует базу данных и сохраняет объекты, где net_change >= net_change_threshold, в новый файл."""
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Фильтрация данных
        filtered_data = {key: value for key, value in data.items() if value.get("net_change", 0) >= net_change_threshold}

        # Сохраняем отфильтрованные данные в новый файл
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=4)

        print(f"Отфильтрованные данные успешно сохранены в {output_filename}")

    except Exception as e:
        print(f"Ошибка при анализе базы данных: {e}")

# Вызов функции для анализа базы данных
analyze_database()
