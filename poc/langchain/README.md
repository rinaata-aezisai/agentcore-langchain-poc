# LangChain PoC

LangChain + LangGraph の検証。

## セットアップ

```bash
# 1. backend をインストール
cd ../../backend
pip install -e .

# 2. このpocをインストール
cd ../poc/langchain
pip install -e .

# 3. API Key設定
export ANTHROPIC_API_KEY=your-key
```

## backendとの連携

`src/adapter.py` が `backend/src/application/ports/agent_port.py` を実装。

```python
from adapter import LangChainAgentAdapter

agent = LangChainAgentAdapter(
    model_name="claude-3-5-sonnet-20241022",
    temperature=0.7,
)
```

## 特徴

| 項目 | 内容 |
|------|------|
| エコシステム | ◎ 成熟 |
| ワークフロー | ◎ LangGraph |
| Observability | ◎ LangSmith/LangFuse |
