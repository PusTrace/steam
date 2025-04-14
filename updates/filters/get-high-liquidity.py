import json

def find_max_volume(input_filename="database/perfect.json"):
    """Находит элемент с максимальной ликвидностью в JSON файле."""
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        max_volume_item = None
        max_volume = float('-inf')  # Начинаем с наименьшего возможного числа

        for item, details in data.items():
            volume = details.get("liquidity")
            if isinstance(volume, (int, float)):  # Проверяем, что это число
                if volume > max_volume:
                    max_volume = volume
                    max_volume_item = item

        return max_volume_item, max_volume

    except Exception as e:
        print(f"Ошибка: {e}")
        return None, None


# Пример использования функции
item, volume = find_max_volume()
print(f"Элемент с максимальным объемом: {item} с объемом {volume}")
