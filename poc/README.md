# PoC - Agent Framework Comparison

AWS Bedrock AgentCore (Strands Agents) と LangChain の比較検証。

## ディレクトリ構成

```
poc/
├── strands-agents/     # AgentCore実装
│   ├── src/
│   │   ├── adapter.py  # ← backend AgentPort実装
│   │   └── example.py
│   └── pyproject.toml
│
└── langchain/          # LangChain実装
    ├── src/
    │   ├── adapter.py  # ← backend AgentPort実装
    │   └── example.py
    └── pyproject.toml
```

## backendとの依存関係

```
backend/
└── src/
    └── application/
        └── ports/
            └── agent_port.py   # AgentPort (Interface)
                    ↑
                    │ implements
        ┌───────────┴───────────┐
        │                       │
poc/strands-agents/         poc/langchain/
└── src/adapter.py          └── src/adapter.py
    StrandsAgentAdapter         LangChainAgentAdapter
```

## 切り替え方法

環境変数 `AGENT_TYPE` で切り替え:

```python
# backend/src/api/dependencies.py
import os

def get_agent() -> AgentPort:
    agent_type = os.getenv("AGENT_TYPE", "langchain")
    
    if agent_type == "strands":
        from poc.strands_agents.src.adapter import StrandsAgentAdapter
        return StrandsAgentAdapter()
    else:
        from poc.langchain.src.adapter import LangChainAgentAdapter
        return LangChainAgentAdapter()
```

## 比較サマリー

| 観点 | Strands Agents | LangChain |
|------|----------------|-----------|
| AWSネイティブ | ◎ | ○ |
| ワークフロー | △ | ◎ LangGraph |
| Observability | CloudWatch | LangSmith/Fuse |
| 学習コスト | ○ | △ |



