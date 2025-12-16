"""Strands Identity Adapter

AgentCore Identity サービスの実装。
認証、認可、トークン管理。
"""

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any
import uuid

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from application.ports.identity_port import (
    IdentityPort,
    IdentityConfig,
    AuthProvider,
    AuthStatus,
    AuthResult,
    TokenInfo,
    IdentityClaims,
)


class StrandsIdentityAdapter(IdentityPort):
    """Strands Agents Identity アダプター
    
    AgentCore Identityの機能:
    - 認証管理
    - トークン発行・検証
    - 権限管理
    - セッション管理
    """

    def __init__(self):
        self._config: IdentityConfig | None = None
        self._tokens: dict[str, TokenInfo] = {}
        self._identities: dict[str, IdentityClaims] = {}
        self._permissions: dict[str, list[str]] = {}
        self._revoked_tokens: set[str] = set()

    async def initialize(self, config: IdentityConfig) -> bool:
        """Identityサービスを初期化"""
        self._config = config
        return True

    async def authenticate(
        self,
        credentials: dict[str, Any],
    ) -> AuthResult:
        """認証を実行"""
        provider = self._config.provider if self._config else AuthProvider.API_KEY
        
        if provider == AuthProvider.API_KEY:
            return await self._authenticate_api_key(credentials)
        elif provider == AuthProvider.JWT:
            return await self._authenticate_jwt(credentials)
        else:
            return AuthResult(
                status=AuthStatus.INVALID,
                metadata={"error": f"Unsupported provider: {provider}"},
            )

    async def _authenticate_api_key(
        self,
        credentials: dict[str, Any],
    ) -> AuthResult:
        """APIキー認証"""
        api_key = credentials.get("api_key")
        if not api_key:
            return AuthResult(status=AuthStatus.INVALID)
        
        # 簡易的なAPIキー検証（本番では安全なストレージから検証）
        # デモ用: "demo-api-key-xxx" 形式を受け入れ
        if api_key.startswith("demo-api-key-"):
            identity_id = str(uuid.uuid4())
            token_info = await self._generate_token(identity_id)
            
            return AuthResult(
                status=AuthStatus.VALID,
                identity_id=identity_id,
                token_info=token_info,
                permissions=["read", "write", "execute"],
            )
        
        return AuthResult(status=AuthStatus.INVALID)

    async def _authenticate_jwt(
        self,
        credentials: dict[str, Any],
    ) -> AuthResult:
        """JWT認証"""
        token = credentials.get("token")
        if not token:
            return AuthResult(status=AuthStatus.INVALID)
        
        # JWT検証（簡易実装）
        return await self.validate_token(token)

    async def validate_token(self, token: str) -> AuthResult:
        """トークンを検証"""
        if token in self._revoked_tokens:
            return AuthResult(status=AuthStatus.REVOKED)
        
        token_info = self._tokens.get(token)
        if not token_info:
            return AuthResult(status=AuthStatus.INVALID)
        
        if token_info.expires_at and token_info.expires_at < datetime.now():
            return AuthResult(status=AuthStatus.EXPIRED)
        
        # トークンからidentity_idを取得
        identity_id = token_info.metadata.get("identity_id")
        permissions = self._permissions.get(identity_id, [])
        
        return AuthResult(
            status=AuthStatus.VALID,
            identity_id=identity_id,
            token_info=token_info,
            permissions=permissions,
        )

    async def refresh_token(self, refresh_token: str) -> TokenInfo | None:
        """トークンを更新"""
        # リフレッシュトークンを検証
        for token, info in self._tokens.items():
            if info.refresh_token == refresh_token:
                identity_id = info.metadata.get("identity_id")
                if identity_id:
                    # 古いトークンを無効化
                    self._revoked_tokens.add(token)
                    del self._tokens[token]
                    # 新しいトークンを生成
                    return await self._generate_token(identity_id)
        return None

    async def revoke_token(self, token: str) -> bool:
        """トークンを無効化"""
        if token in self._tokens:
            self._revoked_tokens.add(token)
            del self._tokens[token]
            return True
        return False

    async def get_identity(self, identity_id: str) -> IdentityClaims | None:
        """アイデンティティ情報を取得"""
        return self._identities.get(identity_id)

    async def check_permission(
        self,
        identity_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """権限をチェック"""
        permissions = self._permissions.get(identity_id, [])
        permission_key = f"{resource}:{action}"
        
        # ワイルドカードチェック
        return (
            permission_key in permissions
            or f"{resource}:*" in permissions
            or "*:*" in permissions
            or action in permissions  # 簡易的なアクション権限
        )

    async def list_permissions(self, identity_id: str) -> list[str]:
        """権限一覧を取得"""
        return self._permissions.get(identity_id, [])

    async def _generate_token(self, identity_id: str) -> TokenInfo:
        """トークンを生成"""
        token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        
        ttl = self._config.token_ttl_seconds if self._config else 3600
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        token_info = TokenInfo(
            token=token,
            token_type="Bearer",
            expires_at=expires_at,
            refresh_token=refresh_token,
            scopes=["read", "write"],
            metadata={"identity_id": identity_id},
        )
        
        self._tokens[token] = token_info
        self._permissions[identity_id] = ["read", "write", "execute"]
        
        # Identity claimsを作成
        self._identities[identity_id] = IdentityClaims(
            subject=identity_id,
            issuer=self._config.issuer if self._config else "agentcore",
            audience=self._config.audience if self._config else "api",
            issued_at=datetime.now(),
            expires_at=expires_at,
            scopes=["read", "write"],
        )
        
        return token_info


def create_strands_identity() -> StrandsIdentityAdapter:
    """ファクトリ関数"""
    return StrandsIdentityAdapter()

