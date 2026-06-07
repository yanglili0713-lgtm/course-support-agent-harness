from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export support transcripts into simple SFT JSONL.")
    parser.add_argument("--run-dir", required=True, help="A support run directory containing transcript.jsonl.")
    parser.add_argument("--output", default="datasets/support_sft.jsonl")
    args = parser.parse_args()
    rows = export(Path(args.run_dir) / "transcript.jsonl")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {output}")


def export(transcript_path: Path) -> list[dict]:
    """Convert accepted resolver answers into chat-style SFT rows.

    The training target is deliberately narrow: teach a small model the customer
    response style after the Harness has already selected tools and evidence.
    We do not fine-tune the model to control routing or permissions.
    """

    rows: list[dict] = []
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event_type") != "customer_answer":
            continue
        result = event["payload"]["result"]
        rows.append(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是课程平台客服，只能基于已验证工具结果和政策证据回答，不能泄露内部 id 或完整邮箱。",
                    },
                    {"role": "user", "content": result["user_message"]},
                    {"role": "assistant", "content": result["answer"]},
                ],
                "metadata": {
                    "intent": result["final_intent"],
                    "monitor_flags": result["monitor_flags"],
                },
            }
        )
    return rows


if __name__ == "__main__":
    main()

