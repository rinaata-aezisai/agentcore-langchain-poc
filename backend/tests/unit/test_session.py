"""Session Entity Tests"""

import pytest

from domain.entities.message import Message
from domain.entities.session import Session, SessionNotActiveError, SessionState
from domain.events.session_events import MessageAdded, SessionStarted
from domain.value_objects.content import Content
from domain.value_objects.ids import AgentId, UserId


class TestSession:
    def test_start_session(self):
        session = Session.start(AgentId("agent-1"), UserId("user-1"))

        assert session.state == SessionState.ACTIVE
        assert session.is_active is True
        assert len(session.messages) == 0

        events = session.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], SessionStarted)

    def test_add_message(self):
        session = Session.start(AgentId("agent-1"), UserId("user-1"))
        session.clear_domain_events()

        message = Message.user(Content.from_text("Hello"))
        session.add_message(message)

        assert len(session.messages) == 1
        events = session.get_domain_events()
        assert isinstance(events[0], MessageAdded)

    def test_cannot_add_message_to_ended_session(self):
        session = Session.start(AgentId("agent-1"), UserId("user-1"))
        session.end()

        with pytest.raises(SessionNotActiveError):
            session.add_message(Message.user(Content.from_text("Hello")))


