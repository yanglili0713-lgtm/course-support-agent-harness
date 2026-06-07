from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_harness.data_ingestion.bitext_importer import BITEXT_RAW_CSV_URL, import_bitext_csv, merge_jsonl
from agent_harness.data_ingestion.safe_fetch import download_public_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely ingest public Bitext customer-support data.")
    parser.add_argument("--download", action="store_true", help="Download the public CSV from Hugging Face.")
    parser.add_argument("--raw-csv", default="data/raw/bitext_customer_support.csv")
    parser.add_argument("--output", default="examples/public_support_utterances.jsonl")
    parser.add_argument("--registry", default="data/source_registry/bitext_customer_support.json")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--merge-policy-kb", action="store_true")
    parser.add_argument("--merged-output", default="examples/support_augmented_kb.jsonl")
    args = parser.parse_args()

    raw_csv = Path(args.raw_csv)
    if args.download:
        download_public_file(BITEXT_RAW_CSV_URL, raw_csv)
    if not raw_csv.exists():
        raise SystemExit(f"Missing {raw_csv}. Run with --download, or place the public Bitext CSV there manually.")

    registry = import_bitext_csv(
        raw_csv,
        Path(args.output),
        Path(args.registry),
        limit=args.limit,
        keep_categories={"ORDER", "PAYMENT", "ACCOUNT"},
    )
    print(f"imported {registry['rows_imported']} rows into {registry['output_jsonl']}")
    if args.merge_policy_kb:
        merged = merge_jsonl([Path("examples/support_policy_kb.jsonl"), Path(args.output)], Path(args.merged_output))
        print(f"merged {merged['rows_written']} rows into {merged['output_jsonl']}")


if __name__ == "__main__":
    main()
