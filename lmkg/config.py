import os
# config.py - fix this:
_HERE = os.path.dirname(os.path.abspath(__file__))  # = lmkg/

DATASETS_DIR = os.path.join(_HERE, "data", "words", "datasets")          # source
OUTPUT_DIR   = os.path.join(_HERE, "data", "words", "datasets_target")   # output

GRAPHDB_ENDPOINT = "http://localhost:7200/repositories/wikidata5m"
SEARCH_RESULTS_K = 5

BANNED_KEYS = {"depth", "beam", "dfs", "mapping", "use_base_mapping", "suggestions"}