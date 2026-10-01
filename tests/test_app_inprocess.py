"""Critères de sortie de la 0.0, vérifiés en mémoire via le SDK officiel."""

import pytest

from crm_service.app import build_app
from mircapgen import ConfigurationError, MemoryStore, MircapApp, User, feature
from mircapgen.testing import connect

pytestmark = pytest.mark.anyio


def _store() -> MemoryStore:
    return MemoryStore(
        [
            User("alice", groups=("reader",)),
            User("bob", groups=("manager",)),
            User("carol", groups=("manager",), active=False),
        ]
    )


async def test_list__two_users_with_different_groups__see_different_features() -> None:
    app = build_app(_store())

    async with connect(app, user="alice") as alice:
        alice_tools = await alice.tool_names()
    async with connect(app, user="bob") as bob:
        bob_tools = await bob.tool_names()

    assert alice_tools == ["customer.search", "system.status"]
    assert bob_tools == ["customer.delete", "customer.search", "system.status"]


async def test_list__anonymous__sees_only_public_features() -> None:
    async with connect(build_app()) as anonymous:
        assert await anonymous.tool_names() == ["system.status"]


async def test_call__without_permission__refused_and_feature_not_executed() -> None:
    app = build_app(_store())

    async with connect(app, user="alice") as alice:
        result = await alice.call("customer.delete", {"customer_id": 42})
    async with connect(app, user="bob") as bob:
        still_there = await bob.call("customer.search", {"query": "john"})

    assert not result.success
    assert "inconnu" in result.text
    assert "John Doe" in still_there.text


async def test_call__hidden_feature_and_missing_feature__give_same_answer() -> None:
    async with connect(build_app(_store()), user="alice") as alice:
        hidden = await alice.call("customer.delete", {"customer_id": 1})
        missing = await alice.call("customer.nothing", {"customer_id": 1})

    assert hidden.text.split("«")[0] == missing.text.split("«")[0]


async def test_call__feature_with_context__receives_the_calling_user() -> None:
    async with connect(build_app(_store()), user="bob") as bob:
        result = await bob.call("customer.delete", {"customer_id": 43})

    assert result.success
    assert result.data == {"deleted": True, "by": "bob"}


async def test_call__context_parameter__is_not_in_the_exposed_schema() -> None:
    app = build_app(_store())
    async with connect(app, user="bob") as bob:
        tools = (await bob._client.list_tools()).tools

    delete = next(tool for tool in tools if tool.name == "customer.delete")
    assert list(delete.input_schema["properties"]) == ["customer_id"]


async def test_call__invalid_arguments__french_error_without_echoing_values() -> None:
    async with connect(build_app(_store()), user="bob") as bob:
        wrong_type = await bob.call("customer.delete", {"customer_id": "secret-value"})
        missing = await bob.call("customer.delete", {})
        unknown = await bob.call("customer.delete", {"customer_id": 1, "admin": True})

    assert not wrong_type.success
    assert "secret-value" not in wrong_type.text
    assert "obligatoire" in missing.text
    assert "inconnu" in unknown.text


async def test_connect__group_simulation__matches_group_rights() -> None:
    async with connect(build_app(), groups=["reader"]) as reader:
        assert await reader.can_call("customer.search")
        assert not await reader.can_call("customer.delete")


async def test_ceiling__limits_user_rights_to_the_intersection() -> None:
    async with connect(build_app(_store()), user="bob", ceiling=["customer.read"]) as bob:
        assert await bob.can_call("customer.search")
        assert not await bob.can_call("customer.delete")


async def test_inactive_user__loses_access_to_private_features() -> None:
    async with connect(build_app(_store()), user="carol") as carol:
        assert await carol.tool_names() == ["system.status"]


async def test_require_credential__anonymous_sees_nothing() -> None:
    @feature(name="a.status", public=True, description="d")
    async def status() -> str:
        return "ok"

    app = MircapApp("svc", features=[status], require_credential=True)

    async with connect(app) as anonymous:
        assert await anonymous.tool_names() == []
    async with connect(app, groups=[]) as identified:
        assert await identified.tool_names() == ["a.status"]


async def test_connect__unknown_user__configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        async with connect(build_app(), user="nobody"):
            pass


async def test_unexpected_exception__masked_from_the_agent() -> None:
    @feature(name="a.boom", public=True, description="d")
    async def boom() -> None:
        raise RuntimeError("mot de passe base: hunter2")

    async with connect(MircapApp("svc", features=[boom])) as anonymous:
        result = await anonymous.call("a.boom")

    assert not result.success
    assert "hunter2" not in result.text


async def test_feature_error__message_reaches_the_agent() -> None:
    from mircapgen import FeatureError

    @feature(name="a.refuse", public=True, description="d")
    async def refuse() -> None:
        raise FeatureError("Ce client est verrouillé.")

    async with connect(MircapApp("svc", features=[refuse])) as anonymous:
        result = await anonymous.call("a.refuse")

    assert not result.success
    assert result.text == "Ce client est verrouillé."


async def test_sync_feature__is_executed() -> None:
    @feature(name="a.sync", public=True, description="d")
    def sync_feature(value: int) -> int:
        return value + 1

    async with connect(MircapApp("svc", features=[sync_feature])) as anonymous:
        result = await anonymous.call("a.sync", {"value": 1})

    assert result.success
    assert result.text == "2"


async def test_instructions__are_transmitted_to_the_agent() -> None:
    app = build_app()
    async with connect(app) as session:
        assert (
            session._client.instructions == "Toujours rechercher un client avant d'en supprimer un."
        )
