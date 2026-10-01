from mircapgen import feature
from mircapgen.features.registry import FeatureRegistry


def _issues(registry: FeatureRegistry, severity: str) -> list[str]:
    return [issue.feature for issue in registry.issues if issue.severity == severity]


def test_registry__valid_feature__is_registered_with_description_from_docstring() -> None:
    @feature(name="a.read", permission="a.read")
    async def read() -> str:
        """Lit une chose.

        Détail ignoré.
        """
        return "x"

    registry = FeatureRegistry([read])

    item = registry.get("a.read")
    assert item is not None
    assert item.description == "Lit une chose."
    assert registry.issues == []


def test_registry__no_permission_and_not_public__excluded_with_error() -> None:
    @feature(name="a.nothing", description="d")
    async def nothing() -> None: ...

    registry = FeatureRegistry([nothing])

    assert registry.get("a.nothing") is None
    assert _issues(registry, "error") == ["a.nothing"]


def test_registry__permission_and_public__restrictive_wins_with_warning() -> None:
    @feature(name="a.both", description="d", permission="a.write", public=True)
    async def both() -> None: ...

    registry = FeatureRegistry([both])

    item = registry.get("a.both")
    assert item is not None
    assert item.public is False
    assert item.permission == "a.write"
    assert _issues(registry, "warning") == ["a.both"]


def test_registry__internal_feature__needs_neither_permission_nor_public() -> None:
    @feature(name="a.internal", description="d", mcp=False)
    async def internal() -> None: ...

    registry = FeatureRegistry([internal])

    item = registry.get("a.internal")
    assert item is not None
    assert not item.exposed
    assert registry.issues == []


def test_registry__duplicate_names__all_excluded() -> None:
    @feature(name="a.dup", description="d", permission="a.read")
    async def first() -> None: ...

    @feature(name="a.dup", description="d", permission="a.read")
    async def second() -> None: ...

    registry = FeatureRegistry([first, second])

    assert registry.get("a.dup") is None
    assert _issues(registry, "error") == ["a.dup"]


def test_registry__invalid_name_or_permission__excluded() -> None:
    @feature(name="BadName", description="d", permission="a.read")
    async def bad_name() -> None: ...

    @feature(name="a.wild", description="d", permission="a.*")
    async def wildcard_permission() -> None: ...

    registry = FeatureRegistry([bad_name, wildcard_permission])

    assert registry.all() == []
    assert sorted(_issues(registry, "error")) == ["BadName", "a.wild"]


def test_registry__unsupported_signatures__excluded() -> None:
    @feature(name="a.varargs", description="d", permission="a.read")
    async def varargs(*args: int) -> None: ...

    @feature(name="a.noannotation", description="d", permission="a.read")
    async def no_annotation(value) -> None:  # type: ignore[no-untyped-def]
        ...

    registry = FeatureRegistry([varargs, no_annotation])

    assert registry.all() == []
    assert len(registry.errors) == 2


def test_registry__missing_description__warning_only() -> None:
    @feature(name="a.nodesc", permission="a.read")
    async def nodesc() -> None: ...

    registry = FeatureRegistry([nodesc])

    assert registry.get("a.nodesc") is not None
    assert _issues(registry, "warning") == ["a.nodesc"]
