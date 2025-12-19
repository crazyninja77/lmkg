import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import streamlit as st


# Simple helper to check if a module is available
def _optional_import(module_name: str):
    try:
        return __import__(module_name)
    except Exception:  # pragma: no cover
        return None


def _stable_seed_from_text(text: str) -> int:
    # Deterministic seed derived from text (e.g., annotator ID)
    h = hashlib.md5(text.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


@st.cache_resource(show_spinner=False)
def load_hf_dataset():
    datasets = _optional_import("datasets")
    if datasets is None:
        st.error(
            "Missing dependency: 'datasets'. Install with: pip install datasets"
        )
        st.stop()
    from datasets import load_dataset  # type: ignore

    ds = load_dataset("ddaza/valtex", "valtex-rebel")
    return ds


def build_tasks(test_split) -> List[dict]:
    tasks = []
    # Create one task per example; show ALL neg triples together
    for i in range(len(test_split)):
        data = test_split[i]
        passage = data.get("input", "")

        # Surface (readable) triples
        try:
            support_triples = data["output"][0]["non_formatted_surface_output"]
        except Exception:
            support_triples = []
        try:
            neg_triples = data["output"][1]["neg_non_formatted_surface_output"]
        except Exception:
            neg_triples = []

        # Wikidata ID triples
        try:
            support_triples_ids = data.get("meta_obj", {}).get(
                "non_formatted_wikidata_id_output", []
            )
        except Exception:
            support_triples_ids = []
        try:
            neg_triples_ids = data["output"][1][
                "neg_non_formatted_wikidata_id_output"
            ]
        except Exception:
            neg_triples_ids = []

        if not isinstance(support_triples, list):
            support_triples = []
        if not isinstance(neg_triples, list):
            neg_triples = []
        if not isinstance(support_triples_ids, list):
            support_triples_ids = []
        if not isinstance(neg_triples_ids, list):
            neg_triples_ids = []

        tasks.append(
            {
                "example_index": i,
                "passage": passage,
                "support_triples": support_triples,
                "candidate_triples": neg_triples,
                "support_triples_ids": support_triples_ids,
                "candidate_triples_ids": neg_triples_ids,
            }
        )
    return tasks


def _annotations_path() -> Path:
    # Save alongside this file
    here = Path(__file__).resolve().parent
    return here / "annotations.csv"


def _read_existing_annotations() -> List[dict]:
    import csv

    path = _annotations_path()
    if not path.exists():
        return []
    rows = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _append_annotation(row: dict) -> None:
    import csv

    path = _annotations_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        fieldnames = [
            "annotation_id",
            "annotator_id",
            "example_index",
            "neg_index",
            "label",
            "timestamp_utc",
            "elapsed_ms",
            "candidate_triple",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def _format_triple(triple) -> str:
    # triple is expected to be [subject, relation, object] or tuple
    try:
        s, r, o = triple
        return f"({s}) -[{r}]-> ({o})"
    except Exception:
        return str(triple)


def _wikidata_url(identifier: str) -> str | None:
    if not isinstance(identifier, str):
        return None
    if identifier.startswith("Q"):
        return f"https://wikidata.org/wiki/{identifier}"
    if identifier.startswith("P"):
        return f"https://wikidata.org/wiki/Property:{identifier}"
    return None


def _format_triple_ids_markdown(triple) -> str:
    try:
        s, r, o = triple
    except Exception:
        return str(triple)

    def _fmt(e):
        url = _wikidata_url(e) if isinstance(e, str) else None
        if url:
            return f"[{e}]({url})"
        return str(e)

    return f"({_fmt(s)}) -[{_fmt(r)}]-> ({_fmt(o)})"


def _completed_example_indices(annotator_id: str) -> set[int]:
    existing = _read_existing_annotations()
    done_examples: set[int] = set()
    for r in existing:
        if r.get("annotator_id") != annotator_id:
            continue
        ex_idx_str = r.get("example_index", "-1")
        try:
            ex_idx = int(ex_idx_str)
        except Exception:
            continue
        try:
            neg_idx = int(r.get("neg_index", -1))
        except Exception:
            neg_idx = -1
        # Example-level annotations have neg_index == -1
        if neg_idx == -1 and ex_idx >= 0:
            done_examples.add(ex_idx)
    return done_examples


def _filter_unlabeled(tasks: List[dict], annotator_id: str) -> List[dict]:
    existing = _read_existing_annotations()
    done_examples = set()
    for r in existing:
        if r.get("annotator_id") == annotator_id:
            ex_idx_str = r.get("example_index", "-1")
            try:
                ex_idx = int(ex_idx_str)
            except Exception:
                ex_idx = -1
            # If neg_index == -1 (example-level annotation), mark whole example as done
            try:
                neg_idx = int(r.get("neg_index", -1))
            except Exception:
                neg_idx = -1
            if neg_idx == -1 and ex_idx >= 0:
                done_examples.add(ex_idx)
    result = []
    for t in tasks:
        if t["example_index"] not in done_examples:
            result.append(t)
    return result


def main():
    st.set_page_config(page_title="VALTEX Triple Validation", layout="wide")

    st.title("VALTEX: Triple Validation")
    st.caption(
        "Task: Review ALL candidate (NEG) triples. Click YES only if ALL contradict the passage; otherwise click NO."
    )

    with st.sidebar:
        st.header("Annotator")
        annotator_id = st.text_input("Annotator ID (required)", value="")
        show_support = st.checkbox("Show supporting triples", value=True)
        show_wikidata_ids = st.checkbox("Show Wikidata ID triples", value=True)

        st.markdown("---")
        st.header("Data source")
        data_source = st.radio(
            "Select data source",
            ["HuggingFace dataset", "Upload JSONL file"],
            index=0,
        )
        uploaded_file = None
        if data_source == "Upload JSONL file":
            uploaded_file = st.file_uploader(
                "JSONL file (one JSON object per line)",
                type=["json", "jsonl"],
            )

        st.markdown("---")
        st.caption("Annotations are saved to valtex/annotations.csv")

    if not annotator_id:
        st.info("Enter your Annotator ID to begin.")
        st.stop()

    # Load data according to the selected source
    if data_source == "HuggingFace dataset":
        ds = load_hf_dataset()
        split = ds.get("test")
        if split is None or len(split) == 0:
            st.error("No test split found or it is empty.")
            st.stop()
    else:
        if uploaded_file is None:
            st.info("Upload a JSONL file to begin.")
            st.stop()

        # Parse JSONL file: one JSON object per line
        try:
            file_bytes = uploaded_file.getvalue()
            lines = file_bytes.decode("utf-8").splitlines()
        except Exception as e:
            st.error(f"Could not read uploaded file: {e}")
            st.stop()

        records: List[dict] = []
        for line_no, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                st.error(f"Error parsing JSON on line {line_no}: {e}")
                st.stop()
            records.append(obj)

        if not records:
            st.error("Uploaded file is empty or contains only blank lines.")
            st.stop()

        split = records

    n_total = len(split)
    done_examples = _completed_example_indices(annotator_id)
    n_done = len(done_examples)
    n_remaining = max(n_total - n_done, 0)

    st.subheader("Progress")
    st.write(
        f"Remaining for you: {n_remaining} / {n_total} (already annotated items are hidden)"
    )

    if n_remaining == 0:
        st.success("You have completed all available items. Thank you!")
        st.stop()

    # Determine which example index to show next (lazy, example-level)
    if "current_example_index" not in st.session_state:
        st.session_state.current_example_index = 0

    idx = st.session_state.current_example_index
    # Skip already annotated examples for this annotator
    while idx < n_total and idx in done_examples:
        idx += 1

    st.session_state.current_example_index = idx

    if idx >= n_total:
        st.success("You have completed all available items. Thank you!")
        st.stop()

    # Reset per-item timer
    if "_per_item_started" not in st.session_state:
        st.session_state._per_item_started = time.time()

    st.subheader(f"Item {idx + 1} of {n_total}")

    data = split[idx]

    # Extract passage and triples lazily for the current example only
    passage = data.get("input", "")
    try:
        support_triples = data["output"][0]["non_formatted_surface_output"]
    except Exception:
        support_triples = []
    try:
        candidate_triples = data["output"][1]["neg_non_formatted_surface_output"]
    except Exception:
        candidate_triples = []

    try:
        support_triples_ids = data.get("meta_obj", {}).get(
            "non_formatted_wikidata_id_output", []
        )
    except Exception:
        support_triples_ids = []
    try:
        candidate_triples_ids = data["output"][1][
            "neg_non_formatted_wikidata_id_output"
        ]
    except Exception:
        candidate_triples_ids = []
    # Optional: LLM judgement reasoning attached by the generation script
    try:
        llm_judgement_reasoning = data["output"][1].get("judgement_reasoning")
    except Exception:
        llm_judgement_reasoning = None

    if not isinstance(support_triples, list):
        support_triples = []
    if not isinstance(candidate_triples, list):
        candidate_triples = []
    if not isinstance(support_triples_ids, list):
        support_triples_ids = []
    if not isinstance(candidate_triples_ids, list):
        candidate_triples_ids = []

    st.subheader("Passage")
    st.write(passage)

    # Two-pane layout: left = original/supporting data, right = contradicting data
    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Supporting data")
        if show_support:
            st.markdown("**Supporting triples (surface)**")
            if support_triples:
                for t in support_triples:
                    st.markdown(f"- {_format_triple(t)}")
            else:
                st.caption("No supporting triples available.")
            if show_wikidata_ids:
                st.markdown("**Supporting triples (Wikidata IDs)**")
                if support_triples_ids:
                    for t in support_triples_ids:
                        st.markdown(f"- {_format_triple_ids_markdown(t)}")
                else:
                    st.caption("No supporting ID triples available.")
        else:
            st.caption("Supporting triples are hidden. Enable them in the sidebar.")

    with right_col:
        st.subheader("Contradicting data")
        st.markdown("**Candidate (NEG) triples to validate (assess ALL together)**")
        if candidate_triples:
            for t in candidate_triples:
                st.markdown(f"- {_format_triple(t)}")
        else:
            st.caption("No NEG triples available.")
        if show_wikidata_ids:
            st.markdown("**Candidate (NEG) triples (Wikidata IDs)**")
            if candidate_triples_ids:
                for t in candidate_triples_ids:
                    st.markdown(f"- {_format_triple_ids_markdown(t)}")
            else:
                st.caption("No NEG ID triples available.")

    st.subheader("LLM judgement")
    if llm_judgement_reasoning:
        reasoning_text = str(llm_judgement_reasoning)
        st.markdown(reasoning_text)
    else:
        st.caption("No stored LLM judgement is available for this item.")

    # Center the YES / NO / SKIP buttons underneath the judgement section
    cols = st.columns([1, 1, 1, 1, 1])

    def _submit(label: str):
        started = st.session_state._per_item_started
        elapsed_ms = int((time.time() - started) * 1000)
        # Join all candidate triples into one string to keep CSV schema stable
        joined_triples = " || ".join(_format_triple(t) for t in candidate_triples)
        record = {
            "annotation_id": str(uuid.uuid4()),
            "annotator_id": annotator_id,
            "example_index": idx,
            "neg_index": -1,
            "label": label,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": elapsed_ms,
            "candidate_triple": joined_triples,
        }
        _append_annotation(record)
        # Move to next example
        st.session_state.current_example_index = idx + 1
        st.session_state._per_item_started = time.time()
        st.rerun()

    with cols[1]:
        if st.button("YES (contradicted)"):
            _submit("YES")
    with cols[2]:
        if st.button("NO (not contradicted)"):
            _submit("NO")
    with cols[3]:
        if st.button("SKIP"):
            _submit("SKIP")


if __name__ == "__main__":
    main()


