import os
import sys
import yaml
from itertools import islice

import streamlit as st

try:
    from .tools import GraphDBTool
except ImportError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)
    from lmkg.tools import GraphDBTool

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "data", "words", "datasets_target")
BANNED_WORDS = {"input", "inputs", "outputs", "output", "depth", "dfs", "mapping",
                "base", "target", "beam", "use_base_mapping", "suggestions"}


@st.cache_data
def search_top_entities(query: str, k: int = 6):
    endpoint = "http://localhost:7200/repositories/wikidata5m"
    db = GraphDBTool(endpoint=endpoint, functions=["search_entities"])
    results = db.search_entities(query)
    if isinstance(results, str):
        return {}
    return dict(islice(results.items(), k))


def save_selection_yaml(file_path: str, case_key: str, section: str, word: str, qid: str):
    """Save chosen QID back into input.base or input.target as a dict entry."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Navigate to input -> base/target
    case = data.get(case_key, {})
    inp = case.get("input", {})

    if section in inp and isinstance(inp[section], dict):
        inp[section][word] = qid
        case["input"] = inp
        data[case_key] = case
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def migrate_list_to_dict(section_val):
    """Convert a list of words to a dict with None values."""
    if isinstance(section_val, list):
        return {item: None for item in section_val if isinstance(item, str) and item not in BANNED_WORDS}
    return section_val


def get_next_task(skipped_items):
    """
    Scans YAML files, migrates list->dict if needed,
    returns (filepath, case_key, section, word) for the first unlabelled word.
    """
    if not os.path.exists(DATASETS_DIR):
        st.error(f"Directory not found: {DATASETS_DIR}")
        return None, None, None, None

    files = sorted([f for f in os.listdir(DATASETS_DIR) if f.endswith(".yaml")])

    for filename in files:
        filepath = os.path.join(DATASETS_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            changed = False

            for case_key, case_val in data.items():
                if not isinstance(case_val, dict):
                    continue
                inp = case_val.get("input", {})
                if not isinstance(inp, dict):
                    continue

                for section in ["base", "target"]:
                    if section not in inp:
                        continue

                    # Migrate list -> dict
                    if isinstance(inp[section], list):
                        inp[section] = migrate_list_to_dict(inp[section])
                        case_val["input"] = inp
                        data[case_key] = case_val
                        changed = True

                    if isinstance(inp[section], dict):
                        for word, qid in inp[section].items():
                            if word in BANNED_WORDS:
                                continue
                            if qid is None and (filepath, case_key, section, word) not in skipped_items:
                                if changed:
                                    with open(filepath, "w", encoding="utf-8") as f_out:
                                        yaml.safe_dump(data, f_out, default_flow_style=False, sort_keys=False)
                                return filepath, case_key, section, word

            if changed:
                with open(filepath, "w", encoding="utf-8") as f_out:
                    yaml.safe_dump(data, f_out, default_flow_style=False, sort_keys=False)

        except Exception as e:
            st.error(f"Error processing {filename}: {e}")
            continue

    return None, None, None, None


def load_case_context(filepath, case_key):
    """Load the full case for context display."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get(case_key, {})
    except Exception:
        return {}


def render_context(case_data, current_section, current_word):
    """Show the full case so the human has context when picking a QID."""
    inp = case_data.get("input", {})
    out = case_data.get("output", {})
    mappings = out.get("mapping", [])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Base words**")
        for word, qid in (inp.get("base") or {}).items():
            prefix = "➡️ " if (current_section == "base" and word == current_word) else ""
            tag = f"`{qid}`" if qid else "⬜ unlabelled"
            st.markdown(f"{prefix}**{word}** — {tag}")

    with col2:
        st.markdown("**Target words**")
        for word, qid in (inp.get("target") or {}).items():
            prefix = "➡️ " if (current_section == "target" and word == current_word) else ""
            tag = f"`{qid}`" if qid else "⬜ unlabelled"
            st.markdown(f"{prefix}**{word}** — {tag}")

    if mappings:
        st.markdown("**Mappings**")
        for m in mappings:
            st.markdown(f"- {m}")


# ── Callbacks ──────────────────────────────────────────────────────────────────

def on_select(filepath, case_key, section, word, qid):
    save_selection_yaml(filepath, case_key, section, word, qid)


def on_skip(filepath, case_key, section, word):
    st.session_state.skipped_items.add((filepath, case_key, section, word))


# ── UI ─────────────────────────────────────────────────────────────────────────

st.title("Entity Selector")

if "skipped_items" not in st.session_state:
    st.session_state.skipped_items = set()

current_file, current_case, current_section, current_word = get_next_task(st.session_state.skipped_items)

if not current_word:
    st.success("All words have been processed!")
    if st.button("Restart"):
        st.session_state.skipped_items = set()
        st.rerun()
else:
    filename = os.path.basename(current_file)
    st.subheader(f"📄 {filename} — case: `{current_case}` — section: `{current_section}`")
    st.header(f"🔍 Word: {current_word}")

    # ── Context panel ──────────────────────────────────────────────────────────
    with st.expander("📋 Case context", expanded=True):
        case_data = load_case_context(current_file, current_case)
        render_context(case_data, current_section, current_word)

    st.divider()

    # ── Entity search results ──────────────────────────────────────────────────
    results = search_top_entities(current_word, k=4)

    if not results:
        st.warning("No Wikidata results found for this word.")
    else:
        st.write("Select the correct Wikidata entity:")
        for entity_id, description in results.items():
            st.button(
                f"{entity_id}: {description}",
                key=f"{current_word}_{entity_id}",
                on_click=on_select,
                args=(current_file, current_case, current_section, current_word, entity_id),
            )

    st.button(
        "❓ UNKNOWN",
        key=f"{current_word}_UNKNOWN",
        on_click=on_select,
        args=(current_file, current_case, current_section, current_word, "UNKNOWN"),
    )
    st.button(
        "⏭️ Skip",
        key=f"{current_word}_Skip",
        on_click=on_skip,
        args=(current_file, current_case, current_section, current_word),
    )