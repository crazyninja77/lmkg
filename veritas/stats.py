import json
from collections import Counter
from pathlib import Path

from tap import Tap


class Arguments(Tap):
    file_path: str


def _compute_and_print_stats(path: Path, prefix_label=None):
    n_instances = 0
    total_passage_words = 0
    supporting_counts = []
    contradicting_counts = []
    entity_counter = Counter()
    relation_counter = Counter()

    with path.open() as f:
        for line in f:
            data = json.loads(line)
            n_instances += 1

            # Passage length
            total_passage_words += len(data["input"].split())

            # Supporting triples
            support_triples = data['meta_obj']['non_formatted_wikidata_id_output']
            supporting_counts.append(len(support_triples))
            for s, r, o in support_triples:
                entity_counter.update([s, o])
                relation_counter.update([r])

            # Contradicting triples
            neg_triples = data["output"][1]["neg_non_formatted_wikidata_id_output"]
            contradicting_counts.append(len(neg_triples))
            for s, r, o in neg_triples:
                entity_counter.update([s, o])
                relation_counter.update([r])

    # Compute summary stats
    avg_words = total_passage_words / n_instances if n_instances else 0
    avg_support = sum(supporting_counts) / n_instances if n_instances else 0
    avg_contradict = sum(contradicting_counts) / n_instances if n_instances else 0

    # print(f"File: {path}")
    # print(f"Total instances: {n_instances}")
    # print(f"Avg. passage length (words): {avg_words:.1f}")
    # print(f"Avg. supporting triples per instance: {avg_support:.2f}")
    # print(f"Avg. contradicting triples per instance: {avg_contradict:.2f}")
    # print(f"Unique entities: {len(entity_counter)}")
    # print(f"Unique relations: {len(relation_counter)}")

    latex_prefix = f"{prefix_label} & " if prefix_label else ""
    print(
        f"{latex_prefix}{n_instances:,} & {avg_words:.1f} & {avg_support:.2f} & {avg_contradict:.2f} & {len(entity_counter):,} & {len(relation_counter):,}\\\\"
    )


def main(args: Arguments):
    path = Path(args.file_path)

    if path.is_dir():
        files = sorted(path.glob("*.jsonl"))
        if not files:
            print(f"No .jsonl files found in folder: {path}")
            return
        order_map = {"train": 0, "val": 1, "test": 2}

        def file_rank(p: Path):
            name = p.name.lower()
            for k in ("train", "val", "test"):
                if k in name:
                    return order_map[k]
            return 99

        files.sort(key=lambda p: (file_rank(p), p.name))

        for fp in files:
            name = fp.name.lower()
            label = "Train" if "train" in name else ("Val" if "val" in name else ("Test" if "test" in name else None))
            _compute_and_print_stats(fp, prefix_label=label)
    else:
        name = path.name.lower()
        label = "Train" if "train" in name else ("Val" if "val" in name else ("Test" if "test" in name else None))
        _compute_and_print_stats(path, prefix_label=label)


if __name__ == "__main__":
    args = Arguments().parse_args()
    main(args)
