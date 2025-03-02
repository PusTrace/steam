import json

def top_liquidity(input_filename):
    """Находит топ элементов с наибольшей ликвидностью в JSON файле."""
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Фильтруем и сортируем по убыванию ликвидности
        sorted_items = sorted(
            [(item, details["liquidity"]) for item, details in data.items()
             if isinstance(details.get("liquidity"), (int, float))],
            key=lambda x: x[1],  
            reverse=True  # Сортируем от большего к меньшему
        )

        return sorted_items[:]

    except Exception as e:
        print(f"Ошибка: {e}")
        return []

# Пример использования
top = top_liquidity("main/database/perfect.json")
print(top)

