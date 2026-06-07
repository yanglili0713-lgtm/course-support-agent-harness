# Data Change Record

## 2026-06-07 Safe Public Data Supplement

- Added `agent_harness/data_ingestion/safe_fetch.py`.
- Added `agent_harness/data_ingestion/bitext_importer.py`.
- Added `scripts/ingest_bitext_public.py`.
- Added tests for CSV cleaning, de-duplication, registry output, and JSONL merge.
- Chosen optional public data source: Hugging Face Bitext customer-support dataset.
- Safety boundary: public utterance examples only; no private chat logs, no real users, no real orders.
- Source metadata written per chunk: `source_url`, `source_name`, `license`, `content_hash`.
- Local fixture verification completed: `python scripts\ingest_bitext_public.py --raw-csv tests\fixtures\bitext_sample.csv --output data\processed\fixture_public_support.jsonl --registry data\source_registry\fixture_bitext.json --limit 10 --merge-policy-kb --merged-output data\processed\fixture_augmented_kb.jsonl`.
- External download was not executed in this environment because the network approval request was rejected by the tool system. The script remains ready for the user to run locally.
