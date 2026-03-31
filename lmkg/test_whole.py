"""
Step-by-step diagnostic for the entity selector setup.
Run with: python lmkg/test_setup.py
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "  [PASS]"
FAIL = "  [FAIL]"
INFO = "  [INFO]"


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ─────────────────────────────────────────────────────────────────────────────
section("1. config.py — path resolution")
# ─────────────────────────────────────────────────────────────────────────────

try:
    from lmkg.config import DATASETS_DIR, OUTPUT_DIR, GRAPHDB_ENDPOINT, BANNED_KEYS
    print(f"{INFO} DATASETS_DIR : {DATASETS_DIR}")
    print(f"{INFO} OUTPUT_DIR   : {OUTPUT_DIR}")
    print(f"{INFO} ENDPOINT     : {GRAPHDB_ENDPOINT}")
except Exception as e:
    print(f"{FAIL} Could not import config: {e}")
    sys.exit(1)

if os.path.exists(DATASETS_DIR):
    print(f"{PASS} DATASETS_DIR exists")
else:
    print(f"{FAIL} DATASETS_DIR does not exist: {DATASETS_DIR}")
    print(f"       Fix the path in config.py")

if os.path.exists(OUTPUT_DIR):
    print(f"{PASS} OUTPUT_DIR exists")
else:
    print(f"{INFO} OUTPUT_DIR does not exist yet — will be created on first run")


# ─────────────────────────────────────────────────────────────────────────────
section("2. YAML files — structure check")
# ─────────────────────────────────────────────────────────────────────────────

yaml_files = []
if os.path.exists(DATASETS_DIR):
    yaml_files = sorted([f for f in os.listdir(DATASETS_DIR) if f.endswith(".yaml")])
    print(f"{INFO} Found {len(yaml_files)} YAML file(s): {yaml_files}\n")

    for filename in yaml_files:
        filepath = os.path.join(DATASETS_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Top level must be a dict with a 'mapping' key
            if not isinstance(data, dict):
                print(f"{FAIL} {filename}: top-level is not a dict (got {type(data).__name__})")
                continue
            if "mapping" not in data:
                print(f"{FAIL} {filename}: no top-level 'mapping' key (keys: {list(data.keys())})")
                continue

            cases = data["mapping"]
            if not isinstance(cases, list):
                print(f"{FAIL} {filename}: 'mapping' is not a list (got {type(cases).__name__})")
                continue

            print(f"{PASS} {filename}: {len(cases)} case(s)")

            # Check each case
            for i, case in enumerate(cases):
                if not isinstance(case, dict):
                    print(f"  {FAIL}   case {i}: not a dict")
                    continue

                inp = case.get("input", {})
                out = case.get("output", {})
                base = inp.get("base")
                target = inp.get("target")
                mapping = out.get("mapping")

                base_type = type(base).__name__ if base is not None else "missing"
                target_type = type(target).__name__ if target is not None else "missing"

                # base and target should be list (source) or dict (already migrated)
                base_ok = isinstance(base, (list, dict))
                target_ok = isinstance(target, (list, dict))

                status = PASS if (base_ok and target_ok) else FAIL
                print(f"  {status}   case {i}: "
                      f"base={base_type}({len(base) if base else 0}) "
                      f"target={target_type}({len(target) if target else 0}) "
                      f"mappings={len(mapping) if isinstance(mapping, list) else 0}")

                if not base_ok:
                    print(f"           base value: {base}")
                if not target_ok:
                    print(f"           target value: {target}")

        except Exception as e:
            print(f"{FAIL} {filename}: could not read — {e}")
else:
    print(f"{FAIL} Skipping — DATASETS_DIR not found")


# ─────────────────────────────────────────────────────────────────────────────
section("3. io_utils — imports and copy creation")
# ─────────────────────────────────────────────────────────────────────────────

try:
    from lmkg.io_utils import (
        list_source_files, ensure_copy_exists,
        load_yaml, get_section_words, get_next_task, save_qid, load_case
    )
    print(f"{PASS} io_utils imported OK")
except Exception as e:
    print(f"{FAIL} Could not import io_utils: {e}")
    sys.exit(1)

try:
    sources = list_source_files()
    print(f"{PASS} list_source_files() returned {len(sources)} file(s)")
except Exception as e:
    print(f"{FAIL} list_source_files() raised: {e}")
    sources = []

for source_path in sources:
    filename = os.path.basename(source_path)
    try:
        out_path = ensure_copy_exists(source_path)
        print(f"{PASS} {filename} → copy at: {out_path}")

        # Verify all base/target sections are dicts (not lists) in the copy
        data = load_yaml(out_path)
        all_migrated = True
        for i, case in enumerate(data.get("mapping", [])):
            inp = case.get("input", {})
            for sec in ["base", "target"]:
                val = inp.get(sec)
                if isinstance(val, list):
                    print(f"  {FAIL}   case {i} '{sec}' is still a list — migration failed")
                    all_migrated = False
                elif isinstance(val, dict):
                    none_count = sum(1 for v in val.values() if v is None)
                    done_count = sum(1 for v in val.values() if v is not None)
                    print(f"  {INFO}   case {i} '{sec}': "
                          f"{done_count} labelled, {none_count} remaining")
        if all_migrated:
            print(f"  {PASS}   all sections are dicts")

    except Exception as e:
        print(f"{FAIL} ensure_copy_exists({filename}): {e}")


# ─────────────────────────────────────────────────────────────────────────────
section("4. io_utils — task queue")
# ─────────────────────────────────────────────────────────────────────────────

try:
    out_path, case_index, sec, word = get_next_task(skipped=set())
    if word:
        print(f"{PASS} get_next_task() found first unlabelled word:")
        print(f"       file    : {os.path.basename(out_path)}")
        print(f"       case    : {case_index}")
        print(f"       section : {sec}")
        print(f"       word    : '{word}'")
    else:
        print(f"{INFO} get_next_task() returned None")
        print(f"       Either no YAML files exist, or all words are already labelled")
except Exception as e:
    print(f"{FAIL} get_next_task() raised: {e}")
    out_path, case_index, sec, word = None, None, None, None


# ─────────────────────────────────────────────────────────────────────────────
section("5. io_utils — load_case (context display)")
# ─────────────────────────────────────────────────────────────────────────────

if word and out_path is not None:
    try:
        case_data = load_case(out_path, case_index)
        inp = case_data.get("input", {})
        out = case_data.get("output", {})
        print(f"{PASS} load_case() returned case {case_index}:")
        print(f"       base    : {get_section_words(inp, 'base')}")
        print(f"       target  : {get_section_words(inp, 'target')}")
        print(f"       mappings: {out.get('mapping', [])}")
    except Exception as e:
        print(f"{FAIL} load_case() raised: {e}")
else:
    print(f"{INFO} Skipping — no unlabelled word available")


# ─────────────────────────────────────────────────────────────────────────────
section("6. io_utils — save_qid (dry run, then undo)")
# ─────────────────────────────────────────────────────────────────────────────

if word and out_path is not None:
    try:
        # Write test QID
        save_qid(out_path, case_index, sec, word, "Q_TEST", certainty="yes")
        data_after = load_yaml(out_path)
        inp_after = data_after["mapping"][case_index]["input"]
        qid_after = inp_after.get(sec, {}).get(word)

        if (qid_after == "Q_TEST" 
            and inp_after.get("input_qid", {}).get(word) == "Q_TEST" 
            and inp_after.get("input_qid_certain", {}).get(word) == "yes"):
            print(f"{PASS} save_qid() correctly wrote QID and certainty 'yes' for '{word}'")
        else:
            print(f"{FAIL} save_qid() did not write correctly. Base/Target: {qid_after}, "
                  f"input_qid: {inp_after.get('input_qid', {}).get(word)}, "
                  f"certainty: {inp_after.get('input_qid_certain', {}).get(word)}")

        # Undo — restore to None so the word stays in the queue
        save_qid(out_path, case_index, sec, word, None)
        data_restored = load_yaml(out_path)
        qid_restored = data_restored["mapping"][case_index]["input"][sec].get(word)

        if qid_restored is None:
            print(f"{PASS} Restored '{word}' back to null — queue intact")
        else:
            print(f"{FAIL} Restore failed (got '{qid_restored}')")

    except Exception as e:
        print(f"{FAIL} save_qid() test raised: {e}")
else:
    print(f"{INFO} Skipping — no unlabelled word available")


# ─────────────────────────────────────────────────────────────────────────────
section("7. GraphDB connection")
# ─────────────────────────────────────────────────────────────────────────────

try:
    from lmkg.tools import GraphDBTool
    db = GraphDBTool(endpoint=GRAPHDB_ENDPOINT, functions=["search_entities"])
    if db.is_alive():
        print(f"{PASS} GraphDB is reachable at {GRAPHDB_ENDPOINT}")

        results = db.search_entities("water")
        if isinstance(results, dict) and len(results) > 0:
            print(f"{PASS} search_entities('water') returned {len(results)} result(s):")
            for qid, desc in list(results.items())[:3]:
                print(f"       {qid}: {desc}")
        else:
            print(f"{FAIL} search_entities('water') returned unexpected: {results}")
    else:
        print(f"{FAIL} GraphDB not reachable at {GRAPHDB_ENDPOINT}")
        print(f"       Start GraphDB before running the Streamlit app")
except Exception as e:
    print(f"{FAIL} GraphDB test raised: {e}")
    print(f"       This will not stop the app from loading — only search will fail")


# ─────────────────────────────────────────────────────────────────────────────
section("Summary")
# ─────────────────────────────────────────────────────────────────────────────

print("""
  Steps 1-6 must all pass for the app to work correctly.
  Step 7 requires GraphDB to be running — start it before
  launching the Streamlit app.

  To run the app:
      streamlit run lmkg/app.py
""")