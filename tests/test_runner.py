from pathlib import Path

from agent_harness.control_plane import HarnessRunner
from agent_harness.llm import MockLLMClient
from agent_harness.schemas import HarnessState, SessionConfig


def test_offline_runner_creates_replay_artifacts(tmp_path):
    config = SessionConfig(
        topic="rag",
        difficulty="mid",
        rounds=1,
        profile_path=Path("examples/resume_profile.yaml"),
        knowledge_path=Path("examples/knowledge_base.jsonl"),
        run_root=tmp_path,
        offline=True,
    )
    runner = HarnessRunner(config, MockLLMClient())

    result = runner.run(lambda question, round_index: "embedding filter dedupe rerank evaluation")

    assert result.state == HarnessState.DONE
    assert (result.run_dir / "transcript.jsonl").exists()
    assert (result.run_dir / "memory_snapshot.json").exists()
    assert result.final_report_path.exists()
    assert "Score" in result.final_report_path.read_text(encoding="utf-8")

