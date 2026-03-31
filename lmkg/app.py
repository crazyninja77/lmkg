import os
import sys
from itertools import islice

import streamlit as st

try:
    from .tools import GraphDBTool
    from .config import DATASETS_DIR, OUTPUT_DIR, GRAPHDB_ENDPOINT
    from .io_utils import get_next_task, save_qid, load_case, get_section_words, reset_file_progress
except ImportError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)
    from lmkg.tools import GraphDBTool
    from lmkg.config import DATASETS_DIR, OUTPUT_DIR, GRAPHDB_ENDPOINT
    from lmkg.io_utils import get_next_task, save_qid, load_case, get_section_words, reset_file_progress

def on_reset_file(out_path):
    reset_file_progress(out_path)
    # Clear any skipped items associated with this specific file
    st.session_state.skipped = {
        item for item in st.session_state.skipped if item[0] != out_path
    }

# ── Search ─────────────────────────────────────────────────────────────────────

@st.cache_data
def search_entities(query: str, k: int = 5) -> dict:
    """Query GraphDB and return top k {QID: description} matches."""
    try:
        db = GraphDBTool(endpoint=GRAPHDB_ENDPOINT, functions=["search_entities"])
        results = db.search_entities(query)
        if isinstance(results, str):
            return {}
        return dict(islice(results.items(), k))
    except Exception as e:
        st.warning(f"Search failed: {e}")
        return {}


# ── Context panel ──────────────────────────────────────────────────────────────

def render_context(case_data: dict, active_section: str, active_word: str):
    """
    Shows base and target words side by side with QID status.
    The current word is highlighted. Output mappings shown below.
    """
    inp = case_data.get("input", {})
    mappings = case_data.get("output", {}).get("mapping", [])

    col1, col2 = st.columns(2)

    for col, sec in zip([col1, col2], ["base", "target"]):
        with col:
            st.markdown(f"**{sec.capitalize()}**")
            words = get_section_words(inp, sec)
            if not words:
                st.caption("(empty)")
            for w, qid in words.items():
                is_current = (sec == active_section and w == active_word)
                arrow = "➡️ " if is_current else "\u00a0\u00a0\u00a0\u00a0"
                label = f"`{qid}`" if qid else "⬜"
                st.markdown(f"{arrow}**{w}** — {label}")

    if mappings:
        st.markdown("---")
        st.markdown("**Mappings**")
        for m in mappings:
            st.markdown(f"- `{m}`")


# ── Callbacks ──────────────────────────────────────────────────────────────────

def on_select(out_path, case_index, section, word, qid, certainty="yes"):
    save_qid(out_path, case_index, section, word, qid, certainty)


def on_skip(out_path, case_index, section, word):
    st.session_state.skipped.add((out_path, case_index, section, word))


# ── Progress ───────────────────────────────────────────────────────────────────

def count_progress() -> tuple[int, int]:
    """Returns (labelled, total) across all output copies."""
    from lmkg.io_utils import list_source_files, ensure_copy_exists, load_yaml
    total = 0
    labelled = 0
    try:
        for source_path in list_source_files():
            out_path = ensure_copy_exists(source_path)
            data = load_yaml(out_path)
            for case in data.get("mapping", []):
                inp = case.get("input", {})
                for sec in ["base", "target"]:
                    words = get_section_words(inp, sec)
                    total += len(words)
                    labelled += sum(1 for q in words.values() if q is not None)
    except Exception:
        pass
    return labelled, total


# ── App ────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Entity Selector", layout="wide")

if "skipped" not in st.session_state:
    st.session_state.skipped = set()

out_path, case_index, section, word = get_next_task(st.session_state.skipped)

# ── Top bar: title + progress ──────────────────────────────────────────────────
title_col, prog_col = st.columns([1, 2])
with title_col:
    st.title("🏷️ Entity Selector")
with prog_col:
    labelled, total = count_progress()
    if total > 0:
        st.metric("Progress", f"{labelled} / {total}")
        st.progress(labelled / total)

st.divider()

# ── Done state ─────────────────────────────────────────────────────────────────
if not word:
    st.success("✅ All words have been labelled!")
    if st.button("Restart (clear skipped)"):
        st.session_state.skipped = set()
        st.rerun()

else:
    # ── File / case info ───────────────────────────────────────────────────────
    info_col, reset_col = st.columns([4, 1])
    with info_col:
        st.caption(
            f"📄 `{os.path.basename(out_path)}` — "
            f"case {case_index + 1} — "
            f"section: `{section}`"
        )
    with reset_col:
        st.button("⚠️ Reset File", on_click=on_reset_file, args=(out_path,), help="Clear all progress for this file and start over.")

    # ── Two-column layout: context LEFT, selection RIGHT ───────────────────────
    left, right = st.columns([1, 1])

    # ── LEFT: case context ─────────────────────────────────────────────────────
    with left:
        st.subheader("📋 Case context")
        case_data = load_case(out_path, case_index)
        render_context(case_data, section, word)

    # ── RIGHT: current word + search results + actions ─────────────────────────
    with right:
        st.subheader(f"🔍 `{word}`")

        results = search_entities(word)

        if results:
            st.write("Select the correct Wikidata entity:")
            for qid, description in results.items():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.button(
                        f"{qid} — {description}",
                        key=f"{word}_{qid}_yes",
                        on_click=on_select,
                        args=(out_path, case_index, section, word, qid, "yes"),
                    )
                with col2:
                    st.button(
                        "Maybe",
                        key=f"{word}_{qid}_maybe",
                        on_click=on_select,
                        args=(out_path, case_index, section, word, qid, "no"),
                    )
        else:
            st.warning("No Wikidata results found. GraphDB may not be running.")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.button(
                "❓ UNKNOWN",
                key=f"{word}_UNKNOWN",
                on_click=on_select,
                args=(out_path, case_index, section, word, "UNKNOWN", "yes"),
                use_container_width=True,
            )
        with col2:
            st.button(
                "⏭️ Skip",
                key=f"{word}_Skip",
                on_click=on_skip,
                args=(out_path, case_index, section, word),
                use_container_width=True,
            )