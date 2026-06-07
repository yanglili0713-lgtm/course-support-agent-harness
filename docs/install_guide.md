# Install Guide

## Why This Error Happens

If you run the project inside a fresh conda environment, for example:

```powershell
(LLM2_lora) PS D:\study\work> python -m agent_harness support --online
```

and see:

```text
ModuleNotFoundError: No module named 'pydantic'
```

it means the current environment does not have the project runtime dependencies installed.

## Good News: The Core Demo No Longer Needs These Dependencies

The support demo was changed to stdlib-first mode. It no longer requires
`pydantic`, `httpx`, `numpy`, `python-dotenv`, `PyYAML`, or `rich`.

Try this first:

```powershell
cd D:\study\work
python -m agent_harness support --online
```

## If You Want To Run Tests

Only `pytest` is needed for the test suite:

Use the same Python that will run the project:

```powershell
cd D:\study\work
python -m pip install pytest -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

If HTTPS still fails, try HTTP:

```powershell
python -m pip install pytest -i http://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

If the mirror is unstable, try the official index:

```powershell
python -m pip install pytest -i https://pypi.org/simple
```

## Verify

```powershell
python -m agent_harness support --online
python -m pytest
```

## DeepSeek .env

```env
AGENT_HARNESS_BASE_URL=https://api.deepseek.com
AGENT_HARNESS_API_KEY=你的DeepSeek_API_Key
AGENT_HARNESS_CHAT_MODEL=deepseek-v4-flash
AGENT_HARNESS_EMBEDDING_MODEL=local-hash
```
