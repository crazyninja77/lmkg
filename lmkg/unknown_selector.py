import os
import sys
import glob

# Make sure we can import from lmkg
try:
    from lmkg.config import OUTPUT_DIR
    from lmkg.io_utils import load_yaml, save_qid, get_section_words, load_case
except ImportError:
    # Add project root to path for standalone execution
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)
    from lmkg.config import OUTPUT_DIR
    from lmkg.io_utils import load_yaml, save_qid, get_section_words, load_case


def find_unknown_tasks(source_dir: str) -> list:
    """Scans all YAML files and returns a list of tasks for words marked as UNKNOWN."""
    tasks = []
    yaml_files = glob.glob(os.path.join(source_dir, "*.yaml"))

    for file_path in yaml_files:
        data = load_yaml(file_path)
        cases = data.get("mapping", [])

        for case_index, case in enumerate(cases):
            inp = case.get("input", {})
            if not isinstance(inp, dict):
                continue

            for section in ["base", "target"]:
                section_data = inp.get(section, {})
                if isinstance(section_data, dict):
                    for word, qid in section_data.items():
                        if qid == "UNKNOWN":
                            tasks.append((file_path, case_index, section, word))
    return tasks


def print_context(case_data: dict, active_section: str, active_word: str):
    """Prints a simplified context view to the terminal."""
    inp = case_data.get("input", {})
    mappings = case_data.get("output", {}).get("mapping", [])

    print("\n" + "=" * 60)
    print(" " * 25 + "CASE CONTEXT")
    print("=" * 60)

    for section in ["base", "target"]:
        words = get_section_words(inp, section)
        print(f"\n{section.capitalize()} words:")
        if not words:
            print("  (empty)")
        for w, qid in words.items():
            is_current = (section == active_section and w == active_word)
            arrow = "-> " if is_current else "   "
            label = f"({qid})" if qid else "(unlabelled)"
            print(f"  {arrow}{w:<20} {label}")

    if mappings:
        print("\nMappings:")
        for m in mappings:
            print(f"  - {m}")
    print("=" * 60 + "\n")


def main():
    """Main loop to process unknown words."""
    print("Searching for words marked as 'UNKNOWN'...")
    tasks = find_unknown_tasks(OUTPUT_DIR)

    if not tasks:
        print("No 'UNKNOWN' words found. All done!")
        return

    total_tasks = len(tasks)
    print(f"Found {total_tasks} unknown word(s) to review.\n")

    for i, (file_path, case_index, section, word) in enumerate(tasks):
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen

        print(f"Processing task {i + 1} of {total_tasks}")
        print(f"File: {os.path.basename(file_path)}")

        # Use load_case to get the specific case data
        case_data = load_case(file_path, case_index)

        print_context(case_data, section, word)

        prompt = f"Enter QID for '{word}' (or press Enter to keep as UNKNOWN): "
        new_qid = input(prompt).strip()

        if new_qid:
            # User entered a QID, let's save it.
            # We assume high confidence when manually entering.
            try:
                save_qid(file_path, case_index, section, word, new_qid, certainty="yes")
                print(f"\nUpdated '{word}' to '{new_qid}'.")
            except Exception as e:
                print(f"\nError saving QID: {e}")
            # Pause to show result before next item
            input("Press Enter to continue...")

    print("\nFinished reviewing all UNKNOWN words.")


if __name__ == "__main__":
    main()