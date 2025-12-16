"""Identity Port - Identity & Access Management Service Interface

AgentCore Identity / Cognito + Custom Auth に対応。
認証、認可、トークン管理。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from enum import Enum


class AuthProvider(str, Enum):
    """認証プロバイダー"""
    AGENTCORE = "agentcore"  # AgentCore Identity
    COGNITO = "cognito"  # AWS Cognito
    OAUTH2 = "oauth2"  # OAuth2/OIDC
    API_KEY = "api_key"  # APIキー
    JWT = "jwt"  # JWT Bearer


class AuthStatus(str, Enum):
    """認証ステータス"""
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    REVOKED = "revoked"


@dataclass
class IdentityConfig:
    """Identity設定"""
    provider: AuthProvider = AuthProvider.API_KEY
    issuer: str = ""
    audience: str = ""
    token_ttl_seconds: int = 3600
    refresh_ttl_seconds: int = 86400
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenInfo:
    """トークン情報"""
    token: str
    token_type: str = "Bearer"
    expires_at: datetime | None = None
    refresh_token: str | None = None
    scopes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthResult:
    """認証結果"""
    status: AuthStatus
    identity_id: str | None = None
    token_info: TokenInfo | None = None
    permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IdentityClaims:
    """アイデンティティクレーム"""
    subject: str
    issuer: str
    audience: str
    issued_at: datetime
    expires_at: datetime
    scopes: list[str] = field(default_factory=list)
    custom_claims: dict[str, Any] = field(default_factory=dict)


class IdentityPort(ABC):
    """Identity Port - 認証・認可

    Strands Agents: AgentCore Identity
    LangChain: Custom Auth / AWS Cognito
    """

    @abstractmethod
    async def initialize(self, config: IdentityConfig) -> bool:
        """Identityサービスを初期化"""
        ...

    @abstractmethod
    async def authenticate(
        self,
        credentials: dict[str, Any],
    ) -> AuthResult:
        """認証を実行"""
        ...

    @abstractmethod
    async def validate_token(self, token: str) -> AuthResult:
        """トークンを検証"""
        ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> TokenInfo | None:
        """トークンを更新"""
        ...

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """トークンを無効化"""
        ...

    @abstractmethod
    async def get_identity(self, identity_id: str) -> IdentityClaims | None:
        """アイデンティティ情報を取得"""
        ...

    @abstractmethod
    async def check_permission(
        self,
        identity_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """権限をチェック"""
        ...

    @abstractmethod
    async def list_permissions(self, identity_id: str) -> list[str]:
        """権限一覧を取得"""
        ...

