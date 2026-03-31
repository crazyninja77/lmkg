import os
import yaml
import glob
import argparse
from collections import Counter

# Use config to get directories, which is more robust
try:
    from lmkg.config import OUTPUT_DIR
except ImportError:
    # Fallback for running as a script from a different CWD
    # This path is based on your project's file structure
    _HERE = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(_HERE, "data", "words", "datasets_target")

def is_case_complete(case: dict, skip_low_confidence: bool) -> bool:
    """
    Checks if a case is fully annotated.

    A case is complete if all words in its 'base' and 'target' sections
    have a QID that is not None or 'UNKNOWN'.

    If skip_low_confidence is True, it also checks that all words have
    a confidence of 'yes' (not 'no').
    """
    inp = case.get("input", {})
    if not isinstance(inp, dict):
        return False

    certainty_dict = inp.get("input_qid_certain", {})
    has_any_words = False

    for section in ["base", "target"]:
        section_data = inp.get(section, {})
        if not isinstance(section_data, dict):
            # If it's still a list, it's not processed, so not complete.
            return False

        if not section_data:  # empty section
            continue

        has_any_words = True
        for word, qid in section_data.items():
            # Condition 1: Must have a valid QID
            if qid is None or qid == "UNKNOWN":
                return False

            # Condition 2: If enabled, must have high confidence
            if skip_low_confidence:
                if certainty_dict.get(word) == "no":
                    return False

    # An empty case is not a "completed" case.
    return has_any_words


def compile_completed_cases(source_dir: str, output_file: str, skip_low_confidence: bool = False):
    """
    Scans YAML files in a directory, extracts completed cases, and saves
    them to a single new YAML file.
    """
    if not os.path.exists(source_dir):
        print(f"Error: Source directory not found at '{source_dir}'")
        return

    all_completed_cases = []
    yaml_files = glob.glob(os.path.join(source_dir, "*.yaml"))

    print(f"Scanning {len(yaml_files)} files in '{os.path.basename(source_dir)}'...")

    for file_path in yaml_files:
        try:
            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            cases = data.get("mapping", [])
            if not isinstance(cases, list):
                continue

            for case in cases:
                if is_case_complete(case, skip_low_confidence):
                    # Add the source file directly into the case structure
                    case['source_file'] = filename
                    all_completed_cases.append(case)

        except Exception as e:
            print(f"Warning: Could not process file '{os.path.basename(file_path)}': {e}")

    total_cases = len(all_completed_cases)
    print(f"\nFound {total_cases} completed cases in total.")

    if not all_completed_cases:
        print("No completed cases to write.")
        return

    # Generate summary from the final list
    print("\nSummary of completed cases by file:")
    file_counts = Counter(case.get('source_file', 'unknown') for case in all_completed_cases)
    for filename, count in file_counts.items():
        print(f"  - {filename}: {count} cases")

    output_data = {"mapping": all_completed_cases}

    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(output_data, f, default_flow_style=False, sort_keys=False)
        print(f"\nSuccessfully saved compiled cases to '{output_file}'")
    except Exception as e:
        print(f"Error: Failed to write output file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile fully annotated cases from multiple YAML files into a single file.")
    parser.add_argument("--source_dir", type=str, default=OUTPUT_DIR, help="Directory containing the YAML files to scan.")
    parser.add_argument("--output_file", type=str, default=os.path.join(os.path.dirname(OUTPUT_DIR), "completed_cases.yaml"), help="Path to save the compiled YAML file.")
    parser.add_argument("--skip_low_confidence", action="store_true", help="If set, also skip cases where any word has a confidence of 'no'.")

    args = parser.parse_args()

    compile_completed_cases(source_dir=args.source_dir, output_file=args.output_file, skip_low_confidence=args.skip_low_confidence)