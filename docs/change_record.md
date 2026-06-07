# Change Record

本文件记录本轮根据 `couragec/LLMInternSkill` 自查后的修改，方便后续复盘。

## 2026-06-07 Skill 自查与补强

- 安装并读取 `llm-intern-skill`，采用“Do not fabricate. Diagnose first, polish second.”原则。
- 增强 `agent_harness/evaluation/support_eval.py`：从简单 `3/3 passed` 扩展为 final intent accuracy、raw route accuracy、monitor flag recall、tool success rate、policy coverage rate、PII safe rate。
- 新增 `docs/incident_log.md`：记录高置信错误路由、RAG 召回不全、长对话记忆丢失、历史记忆污染当前任务四个真实工程问题。
- 新增 `docs/evidence_contract.md`：按证据等级标记哪些简历表述可以写、哪些要降级、哪些不能写。
- 新增 `output/02_materials_audit.md`：审计项目材料、证据强弱、缺失项和所有权风险。
- 新增 `output/03_truth_boundary.md`：明确“可以写 / 谨慎写 / 不能写”的项目边界。
- 新增 `output/04_evidence_contract.md`：抽取可安全进入简历的 claim。
- 新增 `output/06_targeted_resume.md`：生成稳健版项目经历简历描述。
- 新增 `output/07_interview_grilling.md`：按面试官追问方式列出高风险问题。
- 新增 `output/08_answer_cards.md`：给出危险回答、及格回答、强回答。
- 新增 `output/09_upgrade_plan.md`：拆分半天、1 天、3 天、1 周的证据升级计划。
- 已验证：`python -m pytest` 通过 12 个测试；`python -m agent_harness support-eval --output runs\eval\support_eval.json` 输出 3/3 passed，并包含 final intent accuracy、tool success rate、policy coverage rate、PII safe rate 等指标。
- 新增 `docs/demo_guide.md`：整理项目状态、一键演示命令、评测命令、测试命令和简历可写展示方式。
- 新增 DeepSeek 兼容配置：`AGENT_HARNESS_EMBEDDING_MODEL=local-hash` 时，Chat 走 DeepSeek API，RAG embedding 使用本地确定性 hash embedding，避免调用 DeepSeek 不支持的 `/embeddings` 路径。
- 新增 `docs/deepseek_setup.md`：记录 DeepSeek `.env` 配置和运行方式。
- 新增 `requirements.txt` 和 `docs/install_guide.md`：解决新 conda 环境缺少 `pydantic/httpx/numpy/python-dotenv/PyYAML/rich` 依赖导致无法运行的问题。
- 将 `pyproject.toml` 的 Python 要求从 `>=3.12` 调整为 `>=3.10`，适配用户当前 `LLM2_lora` 环境。
- 将核心支持客服 demo 改为标准库优先：移除运行时对 `pydantic/httpx/numpy/python-dotenv/PyYAML/rich` 的硬依赖，避免 pip 镜像 SSL 问题阻塞演示；`requirements.txt` 只保留可选测试依赖 `pytest`。
- 修复 DeepSeek 在线演示暴露的发票越权承诺问题：新增 invoice promise Gate，禁止在没有 `invoice_create` 工具结果时承诺“我将为您开具/帮您办理”；Resolver prompt 增加未授权动作约束，并将 Gate 修复指令写入 procedural memory。
- 修复 DeepSeek 在线演示暴露的访问失败工单承诺问题：当用户表达“还是/仍然/进不去/无法进入”等重复访问失败信号时，Resolver 会在 `access_reset` 后实际调用 `escalation_ticket`，避免回复中承诺不存在的工单。
# 2026-06-07 GitHub readiness recheck

- Rechecked support control-plane implementation against the resume claims:
  Router / Monitor / Resolver workflow, RAG backfill, MCP-like gateway,
  Risk Gate, transcript replay, and public-data augmented knowledge base.
- Verified the latest generated transcript contains raw route, final intent,
  RAG backfill flags, customer-facing answers, tool result counts, and Gate
  PASS decisions.
- Added `docs/github_upload_checklist.md` with final VSCode commands, DeepSeek
  `.env` example, expected verification output, and upload/ignore boundaries.
- Confirmed generated and sensitive paths are ignored by `.gitignore`: `.env`,
  `runs/`, `data/raw/`, `data/processed/`, `.pytest_cache/`, `__pycache__/`.
- Current local verification in the Codex environment:
  `pytest` 23 passed, `support-eval` 3/3 passed, offline support demo finished
  with state `DONE`.
