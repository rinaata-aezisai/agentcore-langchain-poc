"""Session Repository Interface (Port)"""

from abc import ABC, abstractmethod
from domain.entities.session import Session
from domain.value_objects.ids import SessionId, UserId


class SessionRepository(ABC):
    @abstractmethod
    async def find_by_id(self, session_id: SessionId) -> Session | None: ...

    @abstractmethod
    async def find_by_user_id(self, user_id: UserId, limit: int = 20) -> list[Session]: ...

    @abstractmethod
    async def save(self, session: Session) -> None: ...

    @abstractmethod
    async def delete(self, session_id: SessionId) -> None: ...


