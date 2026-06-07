# GitHub Upload Checklist

Use this checklist before pushing the project. It keeps secrets and generated
runtime files out of the repository, while preserving the evidence needed for
resume review and interview discussion.

## 1. Environment

The support demo itself runs on the Python standard library. `pytest` is only
needed when you want to run the test suite.

```powershell
cd D:\study\work
python --version
python -m pip install pytest
```

If your package mirror fails, install from another reachable index or skip the
pytest command temporarily. The CLI demo and `support-eval` do not require
pytest.

## 2. DeepSeek Config

Keep `.env` local. Do not upload it.

```env
AGENT_HARNESS_BASE_URL=https://api.deepseek.com
AGENT_HARNESS_API_KEY=your_deepseek_api_key
AGENT_HARNESS_CHAT_MODEL=deepseek-v4-flash
AGENT_HARNESS_EMBEDDING_MODEL=local-hash
```

## 3. Final Verification Commands

```powershell
python -m pytest
python -m agent_harness support-eval --output runs\eval\final_pre_github_eval.json
python -m agent_harness support --offline --knowledge examples\support_augmented_kb.jsonl
python -m agent_harness support --online --knowledge examples\support_augmented_kb.jsonl
```

Expected result:

- `pytest`: `23 passed`
- `support-eval`: `3/3 passed`
- offline support demo: `Finished: DONE`
- online DeepSeek support demo: `Finished: DONE`

## 4. What To Upload

Upload:

- `agent_harness/`
- `examples/support_policy_kb.jsonl`
- `examples/support_augmented_kb.jsonl`
- `examples/public_support_utterances.jsonl`
- `data/source_registry/`
- `docs/`
- `tests/`
- `scripts/`
- `README.md`, `.env.example`, `pyproject.toml`, `requirements.txt`

Do not upload:

- `.env`
- `runs/`
- `data/raw/`
- `data/processed/`
- `.pytest_cache/`
- `__pycache__/`

The current `.gitignore` already excludes these generated or sensitive paths.

## 5. Git Commands

```powershell
git init
git status --short
git add .
git status --short
```

Before committing, confirm that `.env`, `runs/`, `data/raw/`, and
`__pycache__/` do not appear in `git status --short`.

Then commit and push:

```powershell
git commit -m "Build course support Agent Harness"
git branch -M main
git remote add origin https://github.com/yanglili0713-lgtm/xxx.git
git push -u origin main
```

