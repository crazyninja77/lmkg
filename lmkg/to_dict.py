import os
import yaml

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "data", "words", "datasets_target")

def main():
    if not os.path.exists(DATASETS_DIR):
        print(f"Directory not found: {DATASETS_DIR}")
        return

    banned_words = {
        "input", "inputs", "outputs", "output", "depth", "dfs", 
        "mapping", "base", "target", "beam", "use_base_mapping", "suggestions"
    }
    
    files = sorted([f for f in os.listdir(DATASETS_DIR) if f.endswith(".yaml")])
    
    for filename in files:
        filepath = os.path.join(DATASETS_DIR, filename)
        changed = False
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                
            if not isinstance(data, dict):
                continue
                
            for section in list(data.keys()):
                if section in banned_words:
                    continue
                    
                val = data[section]
                # Migration: Convert List to Dict with None values
                if isinstance(val, list):
                    new_dict = {item: None for item in val if isinstance(item, str) and item not in banned_words}
                    data[section] = new_dict
                    changed = True
                    
            if changed:
                with open(filepath, "w", encoding="utf-8") as f_out:
                    yaml.safe_dump(data, f_out, default_flow_style=False, sort_keys=False)
                print(f"Successfully formatted {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    main()