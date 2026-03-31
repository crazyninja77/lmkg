import sys
import os
from itertools import islice

try:
    from .tools import GraphDBTool
except ImportError:
    # Handle execution as a standalone script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)
    from lmkg.tools import GraphDBTool


def search_top_k(query: str, k: int = 10):
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

    #ONLY LIST KEYWORD AND SHORT DESCR
    
    if isinstance(results, str):
        print(f"Search result: {results}")
        return

    # Slice the dictionary to get the first k items.
    # Python 3.7+ dictionaries preserve insertion order.
    top_results = dict(islice(results.items(), k))
    
    print(f"Top {len(top_results)} results for '{query}':")
    for entity_id, description in top_results.items():
        print(f"{entity_id}: {description}")


if __name__ == "__main__":
    # Join command line arguments to form the query, or use a default
    if len(sys.argv) > 1:
        query_text = " ".join(sys.argv[1:])
    else:
        query_text = "Amsterdam"
        
    search_top_k(query_text, k=10)

#WHEN SELECTED STORE LINK

#streamlit

#push on own account and