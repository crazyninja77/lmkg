import streamlit as st
from itertools import islice
from lmkg.config import GRAPHDB_ENDPOINT, SEARCH_RESULTS_K

import sys, os
try:
    from .tools import GraphDBTool
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from lmkg.tools import GraphDBTool


@st.cache_data
def search_entities(query: str, k: int = SEARCH_RESULTS_K) -> dict:
    """Returns {QID: description} for the top k Wikidata matches, or {} on failure."""
    try:
        db = GraphDBTool(endpoint=GRAPHDB_ENDPOINT, functions=["search_entities"])
        results = db.search_entities(query)
        if isinstance(results, str):
            return {}
        return dict(islice(results.items(), k))
    except Exception as e:
        st.warning(f"Search failed: {e}")
        return {}