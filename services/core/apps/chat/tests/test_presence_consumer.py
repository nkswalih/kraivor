"""App-level presence and the handshake that carries it.

The members rail used to read "Online - 0" for a signed-in user because the
server never selected the ``auth`` subprotocol the browser offered: per
RFC 6455 the browser then fails the connection milliseconds after
``accept()``, so every socket flapped, retried, and gave up — and presence,
which broadcast transitions only with no roster, had nothing left to show.
"""

import asyncio
import fnmatch

import pytest
from channels.testing import WebsocketCommunicator

from apps.chat.consumers import NotificationConsumer, PresenceConsumer


class FakeRedis:
    """Just enough of the sync redis client for the presence consumer."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def decr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) - 1
        return self.store[key]

    def expire(self, key: str, ttl: int) -> bool:
        return True

    def delete(self, key: str) -> None:
        self.store.pop(key, None)

    def scan_iter(self, match: str = "*"):
        return [k for k in self.store if fnmatch.fnmatch(k, match)]


def _authed(consumer, user_id: str):
    """Wrap a consumer the way JWTAuthMiddleware does: scope['user_id']."""
    inner = consumer.as_asgi()

    async def app(scope, receive, send):
        scope["user_id"] = user_id
        await inner(scope, receive, send)

    return app


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def fake_redis(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr("apps.chat.consumers.get_redis", lambda: redis)
    return redis


class TestHandshakeSubprotocol:
    @pytest.mark.parametrize("consumer", [PresenceConsumer, NotificationConsumer])
    def test_accept_selects_the_auth_subprotocol(self, consumer):
        # The browser offers ['auth', <jwt>]. Selecting nothing makes it fail
        # the handshake client-side — the bug that killed every socket.
        async def scenario():
            conn = WebsocketCommunicator(
                _authed(consumer, "u1"),
                "/ws/",
                subprotocols=["auth", "some.jwt.token"],
            )
            connected, subprotocol = await conn.connect()
            assert connected is True
            assert subprotocol == "auth"
            await conn.disconnect()

        _run(scenario())

    def test_clients_without_subprotocols_are_unaffected(self):
        async def scenario():
            conn = WebsocketCommunicator(_authed(PresenceConsumer, "u1"), "/ws/")
            connected, subprotocol = await conn.connect()
            assert connected is True
            assert subprotocol is None
            await conn.disconnect()

        _run(scenario())


class TestPresenceRoster:
    def test_joiner_receives_the_users_already_online(self, fake_redis):
        fake_redis.store["presence:conn:u2"] = 1  # signed in before us

        async def scenario():
            conn = WebsocketCommunicator(
                _authed(PresenceConsumer, "u1"), "/ws/presence/"
            )
            await conn.connect()

            first = await conn.receive_json_from()
            assert first["type"] == "presence.sync"
            assert set(first["user_ids"]) == {"u1", "u2"}

            # Our own arrival is broadcast back to us from the group.
            second = await conn.receive_json_from()
            assert second == {
                "type": "presence",
                "user_id": "u1",
                "status": "online",
            }

            await conn.disconnect()

        _run(scenario())

    def test_a_second_tab_is_not_another_offline_flap(self, fake_redis):
        async def scenario():
            first_tab = WebsocketCommunicator(
                _authed(PresenceConsumer, "u1"), "/ws/presence/"
            )
            await first_tab.connect()
            await first_tab.receive_json_from()  # presence.sync
            await first_tab.receive_json_from()  # own online broadcast

            second_tab = WebsocketCommunicator(
                _authed(PresenceConsumer, "u1"), "/ws/presence/"
            )
            await second_tab.connect()
            await second_tab.receive_json_from()  # presence.sync
            # Counter is at 2: no second "online" broadcast…
            assert await second_tab.receive_nothing(timeout=0.2)
            # …and closing one tab keeps the user online.
            await second_tab.disconnect()
            assert await first_tab.receive_nothing(timeout=0.2)

            await first_tab.disconnect()

        _run(scenario())

    def test_last_disconnect_broadcasts_offline(self, fake_redis):
        async def scenario():
            observer = WebsocketCommunicator(
                _authed(PresenceConsumer, "u3"), "/ws/presence/"
            )
            await observer.connect()
            await observer.receive_json_from()  # presence.sync
            await observer.receive_json_from()  # own online broadcast

            leaving = WebsocketCommunicator(
                _authed(PresenceConsumer, "u2"), "/ws/presence/"
            )
            await leaving.connect()
            await leaving.receive_json_from()  # presence.sync
            await observer.receive_json_from()  # u2's online echo

            await leaving.disconnect()
            frame = await observer.receive_json_from()
            assert frame == {
                "type": "presence",
                "user_id": "u2",
                "status": "offline",
            }

            await observer.disconnect()

        _run(scenario())

    def test_heartbeat_keeps_the_session_alive(self, fake_redis):
        async def scenario():
            conn = WebsocketCommunicator(
                _authed(PresenceConsumer, "u1"), "/ws/presence/"
            )
            await conn.connect()
            await conn.receive_json_from()  # presence.sync
            await conn.receive_json_from()  # own online broadcast

            await conn.send_json_to({"action": "heartbeat"})
            assert await conn.receive_nothing(timeout=0.2)
            assert "presence:conn:u1" in fake_redis.store

            await conn.disconnect()
            assert "presence:conn:u1" not in fake_redis.store

        _run(scenario())
