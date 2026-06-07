from pathlib import Path

from agent_harness.data_ingestion.bitext_importer import import_bitext_csv, merge_jsonl


def test_bitext_importer_filters_and_dedupes_public_rows(tmp_path):
    output = tmp_path / "public_support_utterances.jsonl"
    registry = tmp_path / "registry.json"

    result = import_bitext_csv(
        Path("tests/fixtures/bitext_sample.csv"),
        output,
        registry,
        limit=10,
        keep_categories={"ORDER", "PAYMENT"},
    )

    lines = output.read_text(encoding="utf-8").splitlines()
    assert result["rows_imported"] == 2
    assert len(lines) == 2
    assert "cdla-sharing-1.0" in registry.read_text(encoding="utf-8")


def test_merge_jsonl_dedupes_by_id(tmp_path):
    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    merged = tmp_path / "merged.jsonl"
    left.write_text('{"id":"a","text":"one"}\n', encoding="utf-8")
    right.write_text('{"id":"a","text":"one again"}\n{"id":"b","text":"two"}\n', encoding="utf-8")

    result = merge_jsonl([left, right], merged)

    assert result["rows_written"] == 2
    assert len(merged.read_text(encoding="utf-8").splitlines()) == 2

