from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_harness.control_plane import HarnessRunner
from agent_harness.control_plane.support_runner import SupportHarnessRunner
from agent_harness.evaluation.support_eval import run_support_eval
from agent_harness.llm import build_client, load_model_config
from agent_harness.schemas import SessionConfig
from agent_harness.business.support_schemas import SupportConfig

try:  # Rich is a runtime dependency, but this fallback keeps error reporting tidy.
    from rich.console import Console
except Exception:  # pragma: no cover - only used in stripped environments
    Console = None


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        run_command(args)
        return
    if args.command == "support":
        support_command(args)
        return
    if args.command == "support-eval":
        support_eval_command(args)
        return
    parser.print_help()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-harness",
        description="Controllable, verifiable, replayable Agent Harness CLI.",
    )
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="Run an interview training session.")
    run.add_argument("--profile", default="examples/resume_profile.yaml")
    run.add_argument("--knowledge", default="examples/knowledge_base.jsonl")
    run.add_argument("--topic", default="rag")
    run.add_argument("--difficulty", default="mid")
    run.add_argument("--rounds", type=int, default=3)
    run.add_argument("--run-root", default="runs")
    run.add_argument("--max-replans", type=int, default=1)
    run.add_argument("--offline", dest="offline", action="store_true", default=True)
    run.add_argument("--online", dest="offline", action="store_false")
    run.add_argument(
        "--auto-answer",
        action="store_true",
        help="Use deterministic sample answers instead of interactive input.",
    )
    support = sub.add_parser("support", help="Run the realistic customer-support agent scenario.")
    support.add_argument("--user-id", default="u_1001")
    support.add_argument("--knowledge", default="examples/support_policy_kb.jsonl")
    support.add_argument("--customer-db", default="examples/support_customers.yaml")
    support.add_argument("--run-root", default="runs")
    support.add_argument("--offline", dest="offline", action="store_true", default=True)
    support.add_argument("--online", dest="offline", action="store_false")
    support.add_argument(
        "--message",
        action="append",
        help="Customer message. Pass multiple --message values for a multi-turn session.",
    )
    support_eval = sub.add_parser("support-eval", help="Run support scenario regression eval.")
    support_eval.add_argument("--output", default="runs/eval/support_eval.json")
    return parser


def run_command(args: argparse.Namespace) -> None:
    console = Console() if Console else None
    model_config = load_model_config()
    config = SessionConfig(
        topic=args.topic,
        difficulty=args.difficulty,
        rounds=args.rounds,
        profile_path=Path(args.profile),
        knowledge_path=Path(args.knowledge),
        run_root=Path(args.run_root),
        offline=args.offline,
        max_replans=args.max_replans,
        model=model_config,
    )
    client = build_client(config.model, offline=config.offline)
    runner = HarnessRunner(config, client)

    def answer_provider(question: str, round_index: int) -> str:
        _print(console, f"\n[Round {round_index}] Examiner question:\n{question}\n")
        if args.auto_answer or not sys.stdin.isatty():
            return (
                "我会先明确召回目标，再做 embedding 检索和 metadata filter，"
                "之后按文档 id 去重，并用难度和简历相关性重排；验证上会看命中率、"
                "人工评分和失败样例。"
            )
        return input("Your answer> ").strip()

    result = runner.run(answer_provider)
    _print(console, f"\nFinished: {result.state.value}")
    _print(console, f"Run dir: {result.run_dir}")
    _print(console, f"Final report: {result.final_report_path}")


def support_command(args: argparse.Namespace) -> None:
    console = Console() if Console else None
    messages = args.message or [
        "我昨天买的 RAG 实战课今天打不开了，再不解决我就要退款。",
        "刚才还是进不去，你们是不是把我的账号弄错了？",
        "如果能打开就不用退了，顺便帮我看下发票什么时候能开。",
    ]
    model_config = load_model_config()
    config = SupportConfig(
        user_id=args.user_id,
        knowledge_path=Path(args.knowledge),
        customer_db_path=Path(args.customer_db),
        run_root=Path(args.run_root),
        offline=args.offline,
        model=model_config,
    )
    runner = SupportHarnessRunner(config, build_client(config.model, offline=config.offline))
    result = runner.run(messages)
    for turn in result.turns:
        _print(console, f"\n[Turn {turn.turn_index}] {turn.user_message}")
        _print(console, f"route={turn.route.intent.value} final={turn.final_intent.value} flags={turn.monitor_flags}")
        _print(console, turn.answer)
    _print(console, f"\nFinished: {result.state.value}")
    _print(console, f"Run dir: {result.run_dir}")
    _print(console, f"Report: {result.report_path}")


def support_eval_command(args: argparse.Namespace) -> None:
    console = Console() if Console else None
    summary = run_support_eval(Path(args.output))
    _print(console, f"Support eval: {summary['passed']}/{summary['total']} passed")
    _print(console, f"Output: {args.output}")


def _print(console, message: str) -> None:
    if console:
        console.print(message)
    else:
        print(message)
