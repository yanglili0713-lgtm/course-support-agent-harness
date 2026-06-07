# Replay And Review

运行结束后先看三个文件：

- `transcript.jsonl`：逐行 JSON 事件，适合排查状态机、工具调用、Gate 决策。
- `memory_snapshot.json`：四层记忆当前状态。
- `final_report.md`：面向人的训练复盘。

复盘顺序：

1. 看 `session_plan` 是否符合主题、维度和难度。
2. 看 `retrieval` 的 evidence 是否经过 metadata filter。
3. 看 `question_gate` 和 `grade_gate` 是否 PASS 或受控 REPLAN。
4. 看 `memory_consolidated` 是否把评分结果固化到了 semantic/procedural memory。
5. 如果 HALT，定位最后一个 gate 事件的 reason。

