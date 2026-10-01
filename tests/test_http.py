"""Chemin réel : clé en `Authorization: Bearer` sur un vrai serveur HTTP local."""

import socket
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass

import httpx2
import pytest
import uvicorn
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from crm_service.app import build_app
from mircapgen import MemoryStore, User
from mircapgen.auth.keys import generate_key
from mircapgen.store.base import ApiKeyRecord

pytestmark = pytest.mark.anyio


@dataclass
class Service:
    url: str
    alice_key: str
    bob_key: str
    revoked_key: str


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def service() -> Iterator[Service]:
    alice, bob, old = generate_key(), generate_key(), generate_key()
    store = MemoryStore(
        [User("alice", groups=("reader",)), User("bob", groups=("manager",))],
        [
            ApiKeyRecord(alice.prefix, alice.key_hash, "alice"),
            ApiKeyRecord(bob.prefix, bob.key_hash, "bob"),
            ApiKeyRecord(old.prefix, old.key_hash, "bob", revoked=True),
        ],
    )
    port = _free_port()
    config = uvicorn.Config(
        build_app(store).http_app(), host="127.0.0.1", port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "le serveur HTTP de test n'a pas démarré"
    try:
        yield Service(f"http://127.0.0.1:{port}/mcp", alice.secret, bob.secret, old.secret)
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _client(url: str, key: str | None) -> Client:
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    http = httpx2.AsyncClient(headers=headers)
    return Client(streamable_http_client(url, http_client=http))


async def _tool_names(url: str, key: str | None) -> list[str]:
    async with _client(url, key) as client:
        return sorted(tool.name for tool in (await client.list_tools()).tools)


async def test_http__valid_keys__each_user_sees_own_features(service: Service) -> None:
    assert await _tool_names(service.url, service.alice_key) == ["customer.search", "system.status"]
    assert await _tool_names(service.url, service.bob_key) == [
        "customer.delete",
        "customer.search",
        "system.status",
    ]


async def test_http__no_key__only_public_features(service: Service) -> None:
    assert await _tool_names(service.url, None) == ["system.status"]


async def test_http__call_with_identity__feature_receives_user(service: Service) -> None:
    async with _client(service.url, service.bob_key) as client:
        result = await client.call_tool("customer.delete", {"customer_id": 43})

    assert not result.is_error
    assert result.structured_content == {"deleted": True, "by": "bob"}


async def test_http__alice_cannot_call_manager_feature(service: Service) -> None:
    async with _client(service.url, service.alice_key) as client:
        result = await client.call_tool("customer.delete", {"customer_id": 42})

    assert result.is_error


@pytest.mark.parametrize("which", ["garbage", "revoked"])
async def test_http__refused_key__gets_401_not_anonymous_access(
    service: Service, which: str
) -> None:
    key = "mk_deadbeef_notarealkey" if which == "garbage" else service.revoked_key

    async with httpx2.AsyncClient() as http:
        response = await http.post(
            service.url,
            headers={
                "Authorization": f"Bearer {key}",
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )

    assert response.status_code == 401
    assert "invalid_token" in response.headers["www-authenticate"]
    assert key not in response.text
