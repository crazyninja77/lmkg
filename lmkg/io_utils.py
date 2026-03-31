import os
import yaml
from config import DATASETS_DIR, OUTPUT_DIR, BANNED_KEYS


# ── File discovery ─────────────────────────────────────────────────────────────

def list_source_files() -> list[str]:
    if not os.path.exists(DATASETS_DIR):
        raise FileNotFoundError(f"Datasets directory not found: {DATASETS_DIR}")
    return sorted(
        os.path.join(DATASETS_DIR, f)
        for f in os.listdir(DATASETS_DIR)
        if f.endswith(".yaml")
    )


def output_path_for(source_path: str) -> str:
    """Constructs the corresponding path in the output directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, os.path.basename(source_path))


# ── Reading ────────────────────────────────────────────────────────────────────

def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_section_words(inp: dict, section: str) -> dict:
    """
    Returns {word: qid_or_None} for base or target.
    Handles both list format (source files) and dict format (migrated files).
    """
    val = inp.get(section)
    if isinstance(val, list):
        return {item: None for item in val
                if isinstance(item, str) and item not in BANNED_KEYS}
    if isinstance(val, dict):
        return {k: v for k, v in val.items() if k not in BANNED_KEYS}
    return {}


# ── Copy management ────────────────────────────────────────────────────────────

def ensure_copy_exists(source_path: str) -> str:
    """
    Creates a working copy in OUTPUT_DIR if one doesn't exist.
    If a copy already exists but has lists instead of dicts, it migrates
    them while preserving any existing progress.
    """
    out_path = output_path_for(source_path)
    
    if os.path.exists(out_path):
        data = load_yaml(out_path)
        needs_save = False
    else:
        data = load_yaml(source_path)
        needs_save = True

    # data["mapping"] is a list of case dicts
    for case in data.get("mapping", []):
        if not isinstance(case, dict):
            continue
        inp = case.get("input", {})
        if not isinstance(inp, dict):
            continue
        for section in ["base", "target"]:
            val = inp.get(section)
            if isinstance(val, list):
                inp[section] = {item: None for item in val if isinstance(item, str) and item not in BANNED_KEYS}
                needs_save = True

    if needs_save:
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    return out_path


# ── Task queue ─────────────────────────────────────────────────────────────────

def get_next_task(skipped: set) -> tuple:
    """
    Returns (file_path, case_index, section, word) for the first unlabelled
    non-skipped word across all source files.
    case_index is the integer index into data["mapping"].
    Returns (None, None, None, None) when everything is done.
    """
    for source_path in list_source_files():
        out_path = ensure_copy_exists(source_path)
        data = load_yaml(out_path)

        for case_index, case in enumerate(data.get("mapping", [])):
            if not isinstance(case, dict):
                continue
            inp = case.get("input", {})

            for section in ["base", "target"]:
                for word, qid in get_section_words(inp, section).items():
                    if qid is None and (out_path, case_index, section, word) not in skipped:
                        return out_path, case_index, section, word

    return None, None, None, None


# ── Writing ────────────────────────────────────────────────────────────────────

def save_qid(out_path: str, case_index: int, section: str, word: str, qid: str, certainty: str = "yes"):
    """Writes QID into the correct case by index: word: Q1234"""
    data = load_yaml(out_path)
    cases = data.get("mapping", [])

    if case_index >= len(cases):
        raise IndexError(f"case_index {case_index} out of range ({len(cases)} cases)")

    inp = cases[case_index].get("input", {})

    # This should not happen if ensure_copy_exists ran, but as a safeguard:
    if isinstance(inp.get(section), list):
        inp[section] = {
            item: None for item in inp[section]
            if isinstance(item, str) and item not in BANNED_KEYS
        }

    inp[section][word] = qid

    if "input_qid" not in inp:
        inp["input_qid"] = {}
    inp["input_qid"][word] = qid

    if "input_qid_certain" not in inp:
        inp["input_qid_certain"] = {}
    inp["input_qid_certain"][word] = certainty

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def reset_file_progress(out_path: str):
    """
    Loads a working copy file, sets all QID values to None, and clears
    certainty/qid dictionaries.
    """
    if not os.path.exists(out_path):
        return

    data = load_yaml(out_path)
    cases = data.get("mapping", [])

    for case in cases:
        if not isinstance(case, dict):
            continue
        inp = case.get("input", {})
        if not isinstance(inp, dict):
            continue

        # Reset QIDs in base and target sections
        for section in ["base", "target"]:
            section_data = inp.get(section, {})
            if isinstance(section_data, dict):
                for word in section_data:
                    section_data[word] = None

        # Clear the dedicated QID and certainty sections
        if "input_qid" in inp:
            inp["input_qid"] = {}
        if "input_qid_certain" in inp:
            inp["input_qid_certain"] = {}

    # Save the reset data back to the file
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def load_case(out_path: str, case_index: int) -> dict:
    """Returns the full case dict at the given index for context display."""
    data = load_yaml(out_path)
    cases = data.get("mapping", [])
    if case_index < len(cases):
        return cases[case_index]
    return {}