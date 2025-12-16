"""AgentCore Runtime Adapter - invoke_agent_runtime による本番接続

AWS公式ドキュメントに基づく正しい実装:
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-invoke-agent.html

アーキテクチャ:
    Backend → invoke_agent_runtime(agentRuntimeArn) → AgentCore Runtime → ECR Container → Bedrock

必要な環境変数:
    - AGENT_RUNTIME_ARN: AgentCore RuntimeのARN (必須)
    - AWS_REGION: AWSリージョン (デフォルト: us-east-1)

必要なIAMパーミッション:
    - bedrock-agentcore:InvokeAgentRuntime
"""

import json
import logging
import time
import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError

from application.ports.agent_port import AgentPort, AgentResponse
from domain.entities.message import Message

logger = logging.getLogger(__name__)


class AgentCoreRuntimeAdapter(AgentPort):
    """AgentCore Runtime経由でエージェントを呼び出すアダプター

    ECRにデプロイされたエージェントコンテナに対してinvoke_agent_runtimeを実行。
    """

    def __init__(
        self,
        agent_runtime_arn: str,
        region: str = "us-east-1",
        qualifier: str = "DEFAULT",
    ):
        """
        Args:
            agent_runtime_arn: AgentCore RuntimeのARN
                例: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/my-agent
            region: AWSリージョン
            qualifier: エンドポイントの修飾子（DEFAULT, バージョン番号, カスタムエンドポイント名）
        """
        self.agent_runtime_arn = agent_runtime_arn
        self.region = region
        self.qualifier = qualifier

        # boto3クライアント初期化
        self._client = boto3.client(
            "bedrock-agentcore",
            region_name=region,
        )

        logger.info(
            f"AgentCoreRuntimeAdapter initialized: "
            f"arn={agent_runtime_arn}, region={region}, qualifier={qualifier}"
        )

    def _generate_session_id(self) -> str:
        """33文字以上のセッションIDを生成（AgentCore要件）"""
        # UUIDは36文字（ハイフン含む）なので要件を満たす
        return str(uuid.uuid4()) + "-" + str(int(time.time()))

    def _build_payload(
        self,
        context: list[Message],
        instruction: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> bytes:
        """AgentCore Runtime用のペイロードを構築

        エージェントコンテナの /invocations エンドポイントが期待する形式に合わせる。
        """
        # コンテキストをメッセージ履歴に変換
        messages = []
        for msg in context:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        payload = {
            "input": {
                "prompt": instruction,
                "messages": messages,
            }
        }

        # ツールが指定されている場合は追加
        if tools:
            payload["input"]["tools"] = tools

        return json.dumps(payload).encode("utf-8")

    def _parse_response(self, response: dict[str, Any]) -> AgentResponse:
        """AgentCore Runtimeからのレスポンスをパース"""
        content_type = response.get("contentType", "")
        status_code = response.get("statusCode", 200)

        if status_code != 200:
            error_msg = f"AgentCore Runtime returned status {status_code}"
            logger.error(error_msg)
            return AgentResponse(
                content=f"Error: {error_msg}",
                metadata={"error": True, "status_code": status_code},
            )

        # StreamingBodyからレスポンスを読み取り
        response_body = response.get("response")
        if response_body is None:
            return AgentResponse(
                content="No response from agent",
                metadata={"error": True},
            )

        try:
            # ストリーミングレスポンスの処理
            if "text/event-stream" in content_type:
                # Server-Sent Eventsの処理
                content_parts = []
                for line in response_body.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: "):
                            content_parts.append(line_str[6:])
                content = "\n".join(content_parts)
            else:
                # 通常のJSONレスポンス
                raw_content = response_body.read().decode("utf-8")
                response_data = json.loads(raw_content)

                # エージェントコンテナのレスポンス形式に合わせてパース
                output = response_data.get("output", response_data)

                if isinstance(output, dict):
                    # output.message.content[].text 形式
                    message = output.get("message", {})
                    if isinstance(message, dict):
                        content_items = message.get("content", [])
                        if content_items and isinstance(content_items, list):
                            content = content_items[0].get("text", str(output))
                        else:
                            content = str(output)
                    else:
                        content = str(message) if message else str(output)
                else:
                    content = str(output)

            return AgentResponse(
                content=content,
                metadata={
                    "provider": "agentcore_runtime",
                    "agent_runtime_arn": self.agent_runtime_arn,
                    "session_id": response.get("runtimeSessionId"),
                    "status_code": status_code,
                },
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response: {e}")
            return AgentResponse(
                content=f"Failed to parse agent response: {e}",
                metadata={"error": True, "parse_error": str(e)},
            )

    async def execute(
        self,
        context: list[Message],
        instruction: str,
    ) -> AgentResponse:
        """AgentCore Runtimeを経由してエージェントを実行"""
        start_time = time.time()
        session_id = self._generate_session_id()

        logger.info(
            f"Invoking AgentCore Runtime: arn={self.agent_runtime_arn}, "
            f"session={session_id}"
        )

        try:
            payload = self._build_payload(context, instruction)

            response = self._client.invoke_agent_runtime(
                agentRuntimeArn=self.agent_runtime_arn,
                runtimeSessionId=session_id,
                qualifier=self.qualifier,
                contentType="application/json",
                accept="application/json",
                payload=payload,
            )

            result = self._parse_response(response)
            latency_ms = int((time.time() - start_time) * 1000)
            result.metadata["latency_ms"] = latency_ms

            logger.info(f"AgentCore Runtime response received in {latency_ms}ms")
            return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"AgentCore Runtime error: {error_code} - {error_message}")

            return AgentResponse(
                content=f"AgentCore Runtime error: {error_message}",
                metadata={
                    "error": True,
                    "error_code": error_code,
                    "error_message": error_message,
                    "provider": "agentcore_runtime",
                },
            )

        except Exception as e:
            logger.exception(f"Unexpected error calling AgentCore Runtime: {e}")
            return AgentResponse(
                content=f"Unexpected error: {str(e)}",
                metadata={
                    "error": True,
                    "exception": str(e),
                    "provider": "agentcore_runtime",
                },
            )

    async def execute_with_tools(
        self,
        context: list[Message],
        instruction: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResponse:
        """ツール付きでAgentCore Runtimeを経由してエージェントを実行"""
        start_time = time.time()
        session_id = self._generate_session_id()

        logger.info(
            f"Invoking AgentCore Runtime with tools: arn={self.agent_runtime_arn}, "
            f"session={session_id}, tools_count={len(tools) if tools else 0}"
        )

        try:
            payload = self._build_payload(context, instruction, tools)

            response = self._client.invoke_agent_runtime(
                agentRuntimeArn=self.agent_runtime_arn,
                runtimeSessionId=session_id,
                qualifier=self.qualifier,
                contentType="application/json",
                accept="application/json",
                payload=payload,
            )

            result = self._parse_response(response)
            latency_ms = int((time.time() - start_time) * 1000)
            result.metadata["latency_ms"] = latency_ms
            result.metadata["tools_provided"] = len(tools) if tools else 0

            logger.info(f"AgentCore Runtime response received in {latency_ms}ms")
            return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"AgentCore Runtime error: {error_code} - {error_message}")

            return AgentResponse(
                content=f"AgentCore Runtime error: {error_message}",
                metadata={
                    "error": True,
                    "error_code": error_code,
                    "error_message": error_message,
                    "provider": "agentcore_runtime",
                },
            )

        except Exception as e:
            logger.exception(f"Unexpected error calling AgentCore Runtime: {e}")
            return AgentResponse(
                content=f"Unexpected error: {str(e)}",
                metadata={
                    "error": True,
                    "exception": str(e),
                    "provider": "agentcore_runtime",
                },
            )


def create_agentcore_runtime_adapter(
    agent_runtime_arn: str,
    region: str = "us-east-1",
    qualifier: str = "DEFAULT",
) -> AgentCoreRuntimeAdapter:
    """AgentCoreRuntimeAdapterのファクトリ関数"""
    return AgentCoreRuntimeAdapter(
        agent_runtime_arn=agent_runtime_arn,
        region=region,
        qualifier=qualifier,
    )
