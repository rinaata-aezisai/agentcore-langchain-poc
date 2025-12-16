"""CQRS Queries

クエリ（読み取り操作）の定義。
"""

from dataclasses import dataclass


@dataclass
class Query:
    """クエリ基底クラス"""

    pass


@dataclass
class GetSessionQuery(Query):
    """セッション取得クエリ"""

    session_id: str


@dataclass
class GetSessionMessagesQuery(Query):
    """セッションメッセージ取得クエリ"""

    session_id: str
    limit: int = 50
    offset: int = 0


@dataclass
class GetActiveSessionsQuery(Query):
    """アクティブセッション取得クエリ"""

    user_id: str


@dataclass
class GetSessionHistoryQuery(Query):
    """セッション履歴取得クエリ"""

    user_id: str
    from_date: str | None = None
    to_date: str | None = None
    limit: int = 20

