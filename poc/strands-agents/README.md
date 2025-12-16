# Strands Agents PoC

AWS Bedrock AgentCore (Strands Agents) の検証。

## セットアップ

```bash
# 1. backend をインストール
cd ../../backend
pip install -e .

# 2. このpocをインストール
cd ../poc/strands-agents
pip install -e .
```

## backendとの連携

`src/adapter.py` が `backend/src/application/ports/agent_port.py` を実装。

```python
from adapter import StrandsAgentAdapter

agent = StrandsAgentAdapter(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region="us-east-1",
)
```

## 特徴

| 項目 | 内容 |
|------|------|
| AWSネイティブ | ◎ Bedrock完全統合 |
| セットアップ | ○ シンプル |
| Observability | CloudWatch統合 |
