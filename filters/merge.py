import json

def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
        return {}
    except json.JSONDecodeError:
        print(f"Ошибка при разборе JSON в {filename}.")
        return {}

def merge_json(json1, json2):
    merged_json = {}

    for key, value in json1.items():
        clean_key = key.replace(".png", "").strip()
        merged_json[clean_key] = value if isinstance(value, dict) else {}

    for key, value in json2.items():
        clean_key = key.replace(".png", "").strip()
        if clean_key in merged_json:
            if isinstance(merged_json[clean_key], dict) and isinstance(value, dict):
                merged_json[clean_key].update(value)
            else:
                print(f"Предупреждение: конфликт типов данных у ключа '{clean_key}'.")
        else:
            merged_json[clean_key] = value if isinstance(value, dict) else {}

    return merged_json



merged_data = merge_json(load_json("main/database/graph_flatness.json"), load_json("main/database/perfect.json"))

with open("main/database/perfect_data.json", 'w', encoding='utf-8') as f:
    json.dump(merged_data, f, ensure_ascii=False, indent=4)
