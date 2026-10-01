from datetime import UTC, datetime, timedelta

import pytest

from mircapgen import MemoryStore, User
from mircapgen.auth.keys import authenticate_key, extract_prefix, generate_key, hash_key
from mircapgen.store.base import ApiKeyRecord

pytestmark = pytest.mark.anyio


def _store_with_key(**overrides: object) -> tuple[MemoryStore, str]:
    generated = generate_key()
    record = ApiKeyRecord(
        prefix=generated.prefix,
        key_hash=generated.key_hash,
        user_id="alice",
        label="test",
        ceiling=("customer.read",),
    )
    record = ApiKeyRecord(**{**record.__dict__, **overrides})
    return MemoryStore([User("alice", groups=("reader",))], [record]), generated.secret


def test_generate_key__is_random_and_hash_matches() -> None:
    first, second = generate_key(), generate_key()

    assert first.secret != second.secret
    assert first.secret.startswith("mk_")
    assert extract_prefix(first.secret) == first.prefix
    assert hash_key(first.secret) == first.key_hash


@pytest.mark.parametrize("raw", ["", "mk_", "mk_abcd", "xx_12345678_secret", "mk_12345678secret"])
def test_extract_prefix__malformed_key__none(raw: str) -> None:
    assert extract_prefix(raw) is None


async def test_authenticate__valid_key__returns_identity_with_ceiling() -> None:
    store, secret = _store_with_key()

    identity = await authenticate_key(store, secret)

    assert identity is not None
    assert identity.user.id == "alice"
    assert identity.method == "key"
    assert identity.ceiling == ("customer.read",)
    assert identity.credential_id == extract_prefix(secret)


async def test_authenticate__wrong_secret_with_known_prefix__none() -> None:
    store, secret = _store_with_key()
    tampered = secret[:-1] + ("a" if secret[-1] != "a" else "b")

    assert await authenticate_key(store, tampered) is None


async def test_authenticate__unknown_prefix__none() -> None:
    store, _ = _store_with_key()

    assert await authenticate_key(store, generate_key().secret) is None


async def test_authenticate__revoked_key__none() -> None:
    store, secret = _store_with_key(revoked=True)

    assert await authenticate_key(store, secret) is None


async def test_authenticate__expired_key__none() -> None:
    past = datetime.now(UTC) - timedelta(seconds=1)
    store, secret = _store_with_key(expires_at=past)

    assert await authenticate_key(store, secret) is None


async def test_authenticate__not_yet_expired_key__accepted() -> None:
    future = datetime.now(UTC) + timedelta(days=1)
    store, secret = _store_with_key(expires_at=future)

    assert await authenticate_key(store, secret) is not None


async def test_authenticate__inactive_user__none() -> None:
    generated = generate_key()
    store = MemoryStore(
        [User("alice", active=False)],
        [ApiKeyRecord(generated.prefix, generated.key_hash, "alice")],
    )

    assert await authenticate_key(store, generated.secret) is None


async def test_authenticate__key_of_unknown_user__none() -> None:
    generated = generate_key()
    store = MemoryStore([], [ApiKeyRecord(generated.prefix, generated.key_hash, "ghost")])

    assert await authenticate_key(store, generated.secret) is None
