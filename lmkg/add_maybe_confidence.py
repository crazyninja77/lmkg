import os
import yaml
import glob

DIRECTORY = r"C:\Work\Python\VU\lmkg\lmkg\data\words\datasets_target"

def process_all_yamls():
    if not os.path.exists(DIRECTORY):
        print(f"Directory not found: {DIRECTORY}")
        return

    yaml_files = glob.glob(os.path.join(DIRECTORY, "*.yaml"))

    for file_path in yaml_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if not data:
            continue

        changed = False
        cases = []
        if "mapping" in data and isinstance(data["mapping"], list):
            cases = data["mapping"]
        elif isinstance(data, dict):
            cases = list(data.values())

        for case in cases:
            if not isinstance(case, dict): continue
            inp = case.get("input", {})
            if not isinstance(inp, dict): continue

            if "input_qid" not in inp:
                inp["input_qid"] = {}
            if "input_qid_certain" not in inp:
                inp["input_qid_certain"] = {}

            for section in ["base", "target"]:
                section_data = inp.get(section, {})
                if isinstance(section_data, dict):
                    for word, qid in section_data.items():
                        if qid is not None:
                            if word not in inp["input_qid"]:
                                inp["input_qid"][word] = qid
                                changed = True
                            if word not in inp["input_qid_certain"]:
                                inp["input_qid_certain"][word] = "no"
                                changed = True

        if changed:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
            print(f"Updated: {os.path.basename(file_path)}")

if __name__ == "__main__":
    process_all_yamls()