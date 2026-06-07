# Safe Public Data Ingestion

## Source Chosen

Optional public source:

- Dataset: `bitext/Bitext-customer-support-llm-chatbot-training-dataset`
- Host: Hugging Face
- Format: CSV
- License shown on dataset page: `cdla-sharing-1.0`
- Dataset URL: https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset

This dataset is used only for public customer-support utterance and response patterns. It is **not** treated as real user logs, real platform policy, or real order/account data.

## Safety Rules

- Do not log in or bypass authentication.
- Only download allow-listed public HTTPS URLs.
- Do not crawl arbitrary links.
- Apply a max file size cap.
- Store `source_url`, `license`, `source_name`, and `content_hash` in metadata.
- Filter obvious email/phone-like strings.
- Keep real customer/order data synthetic.

## Commands

Download and clean the public CSV:

```powershell
python scripts/ingest_bitext_public.py --download --limit 500
```

Merge public utterance examples with the local policy KB:

```powershell
python scripts/ingest_bitext_public.py --download --limit 500 --merge-policy-kb
```

Outputs:

```text
data/raw/bitext_customer_support.csv
data/source_registry/bitext_customer_support.json
examples/public_support_utterances.jsonl
examples/support_augmented_kb.jsonl
```

Use the augmented KB in a demo:

```powershell
python -m agent_harness support --online --knowledge examples/support_augmented_kb.jsonl
```

## Resume-Safe Wording

Safe:

```text
补充公开客服语料摄取流程，基于 Hugging Face 上公开 Bitext 客服数据集进行 CSV 清洗、去重、来源登记和 metadata 标注；真实订单与用户数据仍使用模拟数据，避免隐私数据进入系统。
```

Unsafe:

```text
使用真实客服聊天记录训练模型。
```

