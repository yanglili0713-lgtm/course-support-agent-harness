from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable


BITEXT_DATASET_URL = "https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset"
BITEXT_RAW_CSV_URL = (
    "https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset/resolve/main/"
    "Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv"
)
BITEXT_LICENSE = "cdla-sharing-1.0"


def import_bitext_csv(
    csv_path: Path,
    output_jsonl: Path,
    registry_path: Path,
    *,
    limit: int = 500,
    keep_categories: set[str] | None = None,
) -> dict:
    """Clean public Bitext rows into JSONL chunks.

    Imported rows are public utterance/response examples for coverage analysis
    and intent testing. They are not real platform logs and not policy evidence.
    """

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    seen_hashes: set[str] = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source, output_jsonl.open("w", encoding="utf-8") as sink:
        reader = csv.DictReader(source)
        for row in reader:
            if kept >= limit:
                break
            category = _clean(row.get("category", "")).upper()
            if keep_categories and category not in keep_categories:
                continue
            instruction = _clean(row.get("instruction", ""))
            response = _clean(row.get("response", ""))
            intent = _clean(row.get("intent", ""))
            if not instruction or not response:
                continue
            if _looks_personal(instruction) or _looks_personal(response):
                continue
            digest = hashlib.sha256(f"{instruction}\n{response}".encode("utf-8")).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            chunk = {
                "id": f"bitext-{digest[:12]}",
                "text": f"User: {instruction}\nAgent pattern: {response}",
                "metadata": {
                    "topic": "support",
                    "policy_topic": _map_policy_topic(category, intent),
                    "difficulty": "any",
                    "source_type": "public_dataset",
                    "source_name": "bitext_customer_support",
                    "source_url": BITEXT_DATASET_URL,
                    "license": BITEXT_LICENSE,
                    "category": category,
                    "intent": intent,
                    "content_hash": digest,
                },
            }
            sink.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            kept += 1

    registry = {
        "source_name": "bitext_customer_support",
        "source_url": BITEXT_DATASET_URL,
        "raw_csv_url": BITEXT_RAW_CSV_URL,
        "license": BITEXT_LICENSE,
        "allowed_use": "public customer-support utterance examples; do not treat as private business logs",
        "privacy_boundary": "importer filters obvious emails/phone-like strings; synthetic order data stays separate",
        "rows_imported": kept,
        "output_jsonl": str(output_jsonl),
    }
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return registry


def merge_jsonl(inputs: Iterable[Path], output_path: Path) -> dict:
    """Merge JSONL files with id-level de-duplication."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    written = 0
    with output_path.open("w", encoding="utf-8") as sink:
        for path in inputs:
            with path.open("r", encoding="utf-8") as source:
                for line in source:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    row_id = str(row.get("id") or hashlib.sha256(line.encode("utf-8")).hexdigest())
                    if row_id in seen:
                        continue
                    seen.add(row_id)
                    sink.write(json.dumps(row, ensure_ascii=False) + "\n")
                    written += 1
    return {"rows_written": written, "output_jsonl": str(output_path)}


def _clean(value: str) -> str:
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())


def _looks_personal(value: str) -> bool:
    lowered = value.lower()
    if "@" in lowered and "." in lowered:
        return True
    digits = sum(char.isdigit() for char in lowered)
    return digits >= 9 and "{{" not in lowered


def _map_policy_topic(category: str, intent: str) -> str:
    text = f"{category} {intent}".lower()
    if any(word in text for word in ["refund", "cancel", "return"]):
        return "refund"
    if any(word in text for word in ["invoice", "payment", "billing"]):
        return "invoice"
    if any(word in text for word in ["account", "login", "password"]):
        return "identity"
    if any(word in text for word in ["order", "delivery", "shipping"]):
        return "order"
    return "support_example"

