"""Strands Agents 使用例 - 2025年12月版

AWS Bedrock AgentCore (Strands Agents) の最新機能を活用した実装例。

機能:
- 基本的なエージェント実行
- AgentCore Memory API 統合
- キャッシング設定
- Guardrails設定
- ツール使用
"""

import os

from strands import Agent
from strands.models import BedrockModel
from strands.types.content import SystemContentBlock

from .tools import AVAILABLE_TOOLS, get_current_weather, calculate


def basic_example():
    """基本的なStrands Agentsの使用例"""
    # デフォルト設定でエージェント作成
    # Claude Sonnet 4がデフォルトで使用される
    agent = Agent()

    response = agent("こんにちは！今日の天気を教えてください。")
    print(f"Response: {response}")


def custom_model_example():
    """カスタムモデル設定の例"""
    # 特定のモデルを指定
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        temperature=0.7,
        max_tokens=4096,
    )

    agent = Agent(
        model=model,
        system_prompt="あなたは親切なAIアシスタントです。日本語で回答してください。",
    )

    response = agent("AWSのBedrockについて教えてください。")
    print(f"Response: {response}")


def caching_example():
    """キャッシング機能の使用例（2025年12月新機能）"""
    # プロンプトとツールのキャッシングを有効化
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        cache_prompt="default",
        cache_tools="default",
    )

    # SystemContentBlockでキャッシュポイントを設定
    system_content = [
        SystemContentBlock(
            text="""あなたは親切なAIアシスタントです。
            
この長いシステムプロンプトはキャッシュされます。
様々な指示や設定をここに記載できます。
キャッシュにより、2回目以降のリクエストでコスト削減が可能です。
"""
        ),
        SystemContentBlock(cachePoint={"type": "default"})
    ]

    agent = Agent(
        model=model,
        system_prompt=system_content,
    )

    # 1回目のリクエスト（キャッシュ書き込み）
    response1 = agent("Pythonについて教えてください。")
    print(f"1st Response: {response1}")
    if hasattr(response1, "metrics"):
        print(f"Cache write tokens: {response1.metrics.accumulated_usage.get('cacheWriteInputTokens', 0)}")

    # 2回目のリクエスト（キャッシュ読み込み）
    response2 = agent("JavaScriptについて教えてください。")
    print(f"2nd Response: {response2}")
    if hasattr(response2, "metrics"):
        print(f"Cache read tokens: {response2.metrics.accumulated_usage.get('cacheReadInputTokens', 0)}")


def tools_example():
    """ツール使用の例"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        cache_tools="default",  # ツールキャッシングを有効化
    )

    agent = Agent(
        model=model,
        system_prompt="あなたは親切なAIアシスタントです。ツールを適切に使用してください。",
        tools=[get_current_weather, calculate],
    )

    # 天気を取得
    response = agent("東京の天気を教えてください。")
    print(f"Weather Response: {response}")

    # 計算を実行
    response = agent("123 * 456 を計算してください。")
    print(f"Calculate Response: {response}")


def guardrails_example():
    """Guardrails設定の例（2025年12月新機能）"""
    # NOTE: guardrail_idは事前にAWSコンソールで作成が必要
    guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID")

    if not guardrail_id:
        print("BEDROCK_GUARDRAIL_ID環境変数が設定されていません。スキップします。")
        return

    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        guardrail_id=guardrail_id,
        guardrail_version="DRAFT",
        guardrail_trace="enabled",
    )

    agent = Agent(
        model=model,
        system_prompt="あなたは親切なAIアシスタントです。",
    )

    response = agent("安全なコンテンツについて教えてください。")
    print(f"Guardrails Response: {response}")


def reasoning_example():
    """Reasoning機能の例（2025年12月新機能）"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        additional_request_fields={
            "thinking": {
                "type": "enabled",
                "budget_tokens": 4096  # 最小1024
            }
        }
    )

    agent = Agent(
        model=model,
        system_prompt="あなたは論理的思考が得意なAIアシスタントです。",
    )

    # 推論が必要な質問
    response = agent(
        "列車が時速120kmで450kmの距離を移動するとき、何時間かかりますか？"
    )
    print(f"Reasoning Response: {response}")


def multimodal_example():
    """マルチモーダル入力の例"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
    )

    agent = Agent(model=model)

    # ドキュメント入力
    response = agent([
        {
            "document": {
                "format": "txt",
                "name": "sample",
                "source": {
                    "bytes": b"This is a sample document about AI and machine learning."
                }
            }
        },
        {
            "text": "このドキュメントについて日本語で説明してください。"
        }
    ])
    print(f"Multimodal Response: {response}")


def memory_short_term_example():
    """短期記憶（会話履歴）の使用例

    AgentCore Memory Session Managerを使った短期記憶の実装。
    参考: https://dev.classmethod.jp/articles/strands-agents-agentcore-memory-session-manager/

    NOTE: bedrock-agentcoreパッケージのインストールが必要
    pip install 'bedrock-agentcore[strands-agents]'
    """
    try:
        from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
        from bedrock_agentcore.memory.integrations.strands.session_manager import (
            AgentCoreMemorySessionManager
        )
    except ImportError:
        print("bedrock-agentcoreがインストールされていません。")
        print("pip install 'bedrock-agentcore[strands-agents]' を実行してください。")
        return

    from datetime import datetime

    # Memory IDは事前にAWSコンソールで作成しておく
    # または環境変数から取得
    MEM_ID = os.environ.get("AGENTCORE_MEMORY_ID", "your-existing-memory-id")
    ACTOR_ID = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    SESSION_ID = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # AgentCore Memory Configを作成
    agentcore_memory_config = AgentCoreMemoryConfig(
        memory_id=MEM_ID,
        session_id=SESSION_ID,
        actor_id=ACTOR_ID
    )

    # Session Managerを作成
    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=agentcore_memory_config,
        region_name="us-east-1"
    )

    # モデル設定
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1"
    )

    # Agentの引数にSessionManagerを設定するだけで短期記憶が有効に
    agent = Agent(
        model=model,
        system_prompt="あなたは親切なアシスタントです。ユーザーとの会話を覚えておいてください。",
        session_manager=session_manager,
    )

    # 会話（短期記憶が自動的に管理される）
    print("=== 1回目の発言 ===")
    response1 = agent("私の名前は田中です。よろしくお願いします！")
    print(f"Response: {response1}")

    print("\n=== 2回目の発言 ===")
    response2 = agent("私の趣味はプログラミングです")
    print(f"Response: {response2}")

    print("\n=== 3回目の発言（短期記憶の確認） ===")
    response3 = agent("私の名前と趣味を教えてください")
    print(f"Response: {response3}")


def memory_long_term_example():
    """長期記憶（User Preference）の使用例

    retrieval_configを使って長期記憶を取得する実装。
    セッションが変わっても同じACTOR_IDなら過去の記憶を参照可能。

    参考: https://dev.classmethod.jp/articles/strands-agents-agentcore-memory-session-manager/

    NOTE: bedrock-agentcoreパッケージのインストールが必要
    pip install 'bedrock-agentcore[strands-agents]'
    """
    try:
        from bedrock_agentcore.memory.integrations.strands.config import (
            AgentCoreMemoryConfig,
            RetrievalConfig
        )
        from bedrock_agentcore.memory.integrations.strands.session_manager import (
            AgentCoreMemorySessionManager
        )
    except ImportError:
        print("bedrock-agentcoreがインストールされていません。")
        print("pip install 'bedrock-agentcore[strands-agents]' を実行してください。")
        return

    from datetime import datetime

    # Memory IDとStrategy IDは事前にAWSコンソールで作成・確認しておく
    MEM_ID = os.environ.get("AGENTCORE_MEMORY_ID", "your-existing-memory-id")
    MEMORY_STRATEGY_ID = os.environ.get("AGENTCORE_STRATEGY_ID", "preference_builtin_XXXXX")
    # ACTOR_IDは同じユーザーなら同じ値を使用（長期記憶はACTOR_ID単位で保存）
    ACTOR_ID = os.environ.get("AGENTCORE_ACTOR_ID", "user_persistent_123")
    # SESSION_IDは新しいセッションごとに変更
    SESSION_ID = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # namespaceを構築: /strategies/{memoryStrategyId}/actors/{actorId}
    NAMESPACE = f"/strategies/{MEMORY_STRATEGY_ID}/actors/{ACTOR_ID}"

    # retrieval_configに長期記憶のnamespaceを設定
    # top_k: 取得する記憶の最大数
    # relevance_score: 関連性スコアの閾値（0.0〜1.0）
    agentcore_memory_config = AgentCoreMemoryConfig(
        memory_id=MEM_ID,
        session_id=SESSION_ID,
        actor_id=ACTOR_ID,
        retrieval_config={
            NAMESPACE: RetrievalConfig(top_k=5, relevance_score=0.5)
        }
    )

    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=agentcore_memory_config,
        region_name="us-east-1"
    )

    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1"
    )

    agent = Agent(
        model=model,
        system_prompt="あなたは親切なアシスタントです。ユーザーの好みを覚えておいてください。",
        session_manager=session_manager,
    )

    # 新しいセッションでも長期記憶から過去の好みを参照できる
    print("=== 長期記憶からの好みの取得 ===")
    response = agent("私の好みを教えてください。")
    print(f"Response: {response}")


def memory_full_example():
    """短期記憶 + 長期記憶の完全な使用例

    AgentCoreMemoryManagerを使った統合実装。
    """
    try:
        from .adapter import AgentCoreMemoryManager
    except ImportError:
        print("AgentCoreMemoryManagerのインポートに失敗しました。")
        return

    from datetime import datetime

    # 方法1: 既存のMemoryに接続
    # （AWSコンソールで事前にMemoryを作成している場合）
    print("=== 既存Memoryへの接続例 ===")
    try:
        manager = AgentCoreMemoryManager.from_existing_memory(
            memory_id=os.environ.get("AGENTCORE_MEMORY_ID", "your-memory-id"),
            actor_id="user_123",
            strategy_namespaces=[
                "/strategies/{strategyId}/actors/{actorId}",  # 実際のstrategyIdに置換
            ],
            retrieval_top_k=5,
            retrieval_relevance_score=0.5,
        )
        print(f"Memory Info: {manager.get_memory_info()}")
    except Exception as e:
        print(f"既存Memory接続エラー: {e}")

    # 方法2: 新規Memoryを作成
    # （APIから新しいMemoryを作成する場合）
    print("\n=== 新規Memory作成例 ===")
    try:
        manager = AgentCoreMemoryManager.create_with_strategies(
            name=f"DemoMemory_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            description="Demo memory with all strategies",
            actor_id="user_123",
            enable_preferences=True,
            enable_semantic=True,
            enable_summary=True,
        )
        print(f"Memory Info: {manager.get_memory_info()}")

        # エージェント作成
        model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region_name="us-east-1"
        )

        agent = Agent(
            model=model,
            system_prompt="あなたは親切なAIアシスタントです。ユーザーの好みを覚えて活用してください。",
            session_manager=manager.get_session_manager(),
        )

        # 会話（好みを学習）
        print("\n=== 会話開始 ===")
        agent("私は寿司が好きです。特にマグロが好きです。")
        agent("ピザも好きです。")

        # 学習した内容を活用
        response = agent("今日のランチは何がいいと思いますか？")
        print(f"Response: {response}")

    except Exception as e:
        print(f"新規Memory作成エラー: {e}")


def memory_example():
    """AgentCore Memory API統合の例（後方互換性のためのエイリアス）"""
    memory_full_example()


def main():
    """メイン関数"""
    print("=" * 60)
    print("Strands Agents Examples - 2025年12月版")
    print("=" * 60)

    print("\n--- 基本的な使用例 ---")
    basic_example()

    print("\n--- カスタムモデル設定 ---")
    custom_model_example()

    print("\n--- ツール使用例 ---")
    tools_example()

    # 以下は環境設定が必要な例
    # print("\n--- キャッシング例 ---")
    # caching_example()
    #
    # print("\n--- Guardrails例 ---")
    # guardrails_example()
    #
    # print("\n--- Reasoning例 ---")
    # reasoning_example()
    #
    # print("\n--- Memory API 短期記憶例 ---")
    # memory_short_term_example()
    #
    # print("\n--- Memory API 長期記憶例 ---")
    # memory_long_term_example()
    #
    # print("\n--- Memory API 完全例 ---")
    # memory_full_example()


if __name__ == "__main__":
    main()
