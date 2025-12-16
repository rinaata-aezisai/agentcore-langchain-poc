"""LangChain Identity Adapter

カスタム認証実装。
AWS Cognitoまたはカスタム認証。
"""

import secrets
from datetime import datetime, timedelta
from typing import Any
import uuid
import jwt

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


class LangChainIdentityAdapter(IdentityPort):
    """LangChain Identity (Custom Auth) アダプター
    
    LangChain相当機能:
    - カスタム認証
    - JWT統合
    - AWS Cognitoラッパー
    """

    def __init__(self):
        self._config: IdentityConfig | None = None
        self._tokens: dict[str, TokenInfo] = {}
        self._identities: dict[str, IdentityClaims] = {}
        self._permissions: dict[str, list[str]] = {}
        self._revoked_tokens: set[str] = set()
        self._jwt_secret = secrets.token_urlsafe(32)

    async def initialize(self, config: IdentityConfig) -> bool:
        """Identityサービスを初期化"""
        self._config = config
        return True

    async def authenticate(
        self,
        credentials: dict[str, Any],
    ) -> AuthResult:
        """認証を実行"""
        provider = self._config.provider if self._config else AuthProvider.JWT
        
        if provider == AuthProvider.API_KEY:
            return await self._authenticate_api_key(credentials)
        elif provider == AuthProvider.JWT:
            return await self._authenticate_jwt(credentials)
        elif provider == AuthProvider.OAUTH2:
            return await self._authenticate_oauth(credentials)
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
        
        if api_key.startswith("lc-api-key-"):
            identity_id = str(uuid.uuid4())
            token_info = await self._generate_jwt_token(identity_id)
            
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
        
        return await self.validate_token(token)

    async def _authenticate_oauth(
        self,
        credentials: dict[str, Any],
    ) -> AuthResult:
        """OAuth認証"""
        access_token = credentials.get("access_token")
        if not access_token:
            return AuthResult(status=AuthStatus.INVALID)
        
        # OAuth検証（簡易実装）
        identity_id = str(uuid.uuid4())
        token_info = await self._generate_jwt_token(identity_id)
        
        return AuthResult(
            status=AuthStatus.VALID,
            identity_id=identity_id,
            token_info=token_info,
            permissions=["read"],
        )

    async def validate_token(self, token: str) -> AuthResult:
        """トークンを検証"""
        if token in self._revoked_tokens:
            return AuthResult(status=AuthStatus.REVOKED)
        
        try:
            # JWTデコード
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=["HS256"],
            )
            
            identity_id = payload.get("sub")
            exp = payload.get("exp")
            
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                return AuthResult(status=AuthStatus.EXPIRED)
            
            token_info = self._tokens.get(token)
            permissions = self._permissions.get(identity_id, [])
            
            return AuthResult(
                status=AuthStatus.VALID,
                identity_id=identity_id,
                token_info=token_info,
                permissions=permissions,
            )
        except jwt.InvalidTokenError:
            return AuthResult(status=AuthStatus.INVALID)

    async def refresh_token(self, refresh_token: str) -> TokenInfo | None:
        """トークンを更新"""
        for token, info in list(self._tokens.items()):
            if info.refresh_token == refresh_token:
                identity_id = info.metadata.get("identity_id")
                if identity_id:
                    self._revoked_tokens.add(token)
                    del self._tokens[token]
                    return await self._generate_jwt_token(identity_id)
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
        
        return (
            permission_key in permissions
            or f"{resource}:*" in permissions
            or "*:*" in permissions
            or action in permissions
        )

    async def list_permissions(self, identity_id: str) -> list[str]:
        """権限一覧を取得"""
        return self._permissions.get(identity_id, [])

    async def _generate_jwt_token(self, identity_id: str) -> TokenInfo:
        """JWTトークンを生成"""
        ttl = self._config.token_ttl_seconds if self._config else 3600
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        payload = {
            "sub": identity_id,
            "iss": self._config.issuer if self._config else "langchain",
            "aud": self._config.audience if self._config else "api",
            "iat": datetime.now().timestamp(),
            "exp": expires_at.timestamp(),
        }
        
        token = jwt.encode(payload, self._jwt_secret, algorithm="HS256")
        refresh_token = secrets.token_urlsafe(32)
        
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
        
        self._identities[identity_id] = IdentityClaims(
            subject=identity_id,
            issuer=self._config.issuer if self._config else "langchain",
            audience=self._config.audience if self._config else "api",
            issued_at=datetime.now(),
            expires_at=expires_at,
            scopes=["read", "write"],
        )
        
        return token_info


def create_langchain_identity() -> LangChainIdentityAdapter:
    """ファクトリ関数"""
    return LangChainIdentityAdapter()

