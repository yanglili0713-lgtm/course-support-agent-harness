from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_harness.evaluation.riskbench_eval import run_riskbench_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CourseSupportBench risk evaluation.")
    parser.add_argument("--bench", default="data/course_support_bench.jsonl")
    parser.add_argument(
        "--modes",
        default="llm_only,rag_only,agent_harness_without_gate,agent_harness",
        help="Comma-separated modes.",
    )
    parser.add_argument("--risk-policy", default="configs/risk_policy.yaml")
    parser.add_argument("--tool-permissions", default="configs/tool_permissions.yaml")
    parser.add_argument("--output-dir", default="runs/eval_course_support")
    args = parser.parse_args()

    summary = run_riskbench_eval(
        bench_path=Path(args.bench),
        modes=[item.strip() for item in args.modes.split(",") if item.strip()],
        output_dir=Path(args.output_dir),
        risk_policy_path=Path(args.risk_policy),
        tool_permissions_path=Path(args.tool_permissions),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
