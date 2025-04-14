import json

def filter_json(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    filtered_data = {k: v for k, v in data.items() if v.get("volume") not in [0, None]}
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=4)

# Пример использования
filter_json("database/database.json", "database/for_all_orders.json")
