import csv
import os
import sys
from itertools import islice

import streamlit as st

# Adjust path to import from lmkg
try:
    from .tools import GraphDBTool
except ImportError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)
    from lmkg.tools import GraphDBTool

DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "test", "dataset.csv")
WORDS_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "words", "entities.csv")


@st.cache_data
def search_top_entities(query: str, k: int = 6):
    """
    Searches for a query string in Wikidata and returns the top k results.
    """
    # Initialize the GraphDBTool.
    # We assume the default endpoint is running locally as per README.
    endpoint = "http://localhost:7200/repositories/wikidata5m"

    # We only load the search_entities function to minimize overhead/checks
    db = GraphDBTool(endpoint=endpoint, functions=["search_entities"])

    # The search_entities method returns a dictionary of all matches
    # or a string message if none are found.
    results = db.search_entities(query)

    if isinstance(results, str):
        return {}

    # Slice the dictionary to get the first k items.
    # Python 3.7+ dictionaries preserve insertion order.
    top_results = dict(islice(results.items(), k))

    return top_results


def save_selection(word: str, qid: str):
    """
    Saves the selected word and QID to the dataset file.
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(DATA_FILE_PATH), exist_ok=True)

    # Check if file exists to write header
    file_exists = os.path.isfile(DATA_FILE_PATH)
    rows = []
    if os.path.isfile(DATA_FILE_PATH):
        with open(DATA_FILE_PATH, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

    header = ["word", "qid"]
    new_rows = [header]

    # Skip header in input if present
    start_idx = 0
    if rows and rows[0] == header:
        start_idx = 1

    for i in range(start_idx, len(rows)):
        row = rows[i]
        if row and row[0] != word:
            new_rows.append(row)

    new_rows.append([word, qid])

    with open(DATA_FILE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)


@st.cache_data
def load_words():
    if not os.path.exists(WORDS_FILE_PATH):
        return []
    with open(WORDS_FILE_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        # Remove header if present
        if rows and rows[0] and rows[0][0].lower() == "word":
            rows = rows[1:]
        return [r[0] for r in rows if r]


st.title("Entity Selector")

words = load_words()

if "word_index" not in st.session_state:
    # Determine start index by checking against dataset.csv
    processed_words = set()
    if os.path.exists(DATA_FILE_PATH):
        with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            saved_rows = list(reader)
            if saved_rows and saved_rows[0] == ["word", "qid"]:
                saved_rows = saved_rows[1:]
            processed_words = {r[0] for r in saved_rows if r}

    st.session_state.word_index = 0
    for i, word in enumerate(words):
        if word not in processed_words:
            st.session_state.word_index = i
            break
    else:
        st.session_state.word_index = len(words)

if not words:
    st.error(f"No words found in {WORDS_FILE_PATH}")
elif st.session_state.word_index >= len(words):
    st.success("All words have been processed!")
    if st.button("Restart"):
        st.session_state.word_index = 0
        st.rerun()
else:
    current_word = words[st.session_state.word_index]
    st.write(f"Processing word {st.session_state.word_index + 1} of {len(words)}")
    st.progress(st.session_state.word_index / len(words))
    st.header(f"Word: {current_word}")

    results = search_top_entities(current_word, k=6)

    def save_and_next(word, qid):
        save_selection(word, qid)
        st.session_state.word_index += 1

    if not results:
        st.warning("No results found.")
        if st.button("UNKNOWN", key=f"{current_word}_UNKNOWN"):
            save_and_next(current_word, "UNKNOWN")
        if st.button("Skip"):
            st.session_state.word_index += 1
            st.rerun()
    else:
        st.write("Select the correct entity:")
        for entity_id, description in results.items():
            button_label = f"{entity_id}: {description}"
            st.button(
                button_label,
                key=f"{current_word}_{entity_id}",
                on_click=save_and_next,
                args=(current_word, entity_id),
            )
        
        if st.button("UNKNOWN", key=f"{current_word}_UNKNOWN"):
            save_and_next(current_word, "UNKNOWN")

        if st.button("Skip"):
            st.session_state.word_index += 1
            st.rerun()
