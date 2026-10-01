"""Client MCP en mémoire pour les tests : un utilisateur simulé, sans réseau ni serveur."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp import Client
from mcp_types import TextContent

from mircapgen.errors import ConfigurationError
from mircapgen.mcp.server import fixed_identity
from mircapgen.rbac.models import Identity, User

if TYPE_CHECKING:
    from mircapgen.app import MircapApp


@dataclass(frozen=True)
class CallResult:
    """Résultat d'un appel de Feature vu par un client.

    Attributes:
        success: `False` si le service a renvoyé une erreur.
        text: Texte renvoyé : le résultat sérialisé en JSON, ou le message d'erreur.
        data: Données structurées lorsque le résultat est un objet, sinon `None`.
    """

    success: bool
    text: str
    data: dict[str, Any] | None = None


class TestSession:
    """Session de test connectée à une application, au nom d'un utilisateur simulé."""

    __test__ = False  # empêche pytest de collecter cette classe comme un test

    def __init__(self, client: Client) -> None:
        self._client = client

    async def tool_names(self) -> list[str]:
        """Noms des Features visibles pour l'utilisateur simulé."""
        result = await self._client.list_tools()
        return sorted(tool.name for tool in result.tools)

    async def can_call(self, name: str) -> bool:
        """Indique si la Feature `name` est visible, donc appelable, par l'utilisateur simulé."""
        return name in await self.tool_names()

    async def call(self, name: str, arguments: dict[str, Any] | None = None) -> CallResult:
        """Appelle la Feature `name` et renvoie son résultat.

        Args:
            name: Nom de la Feature.
            arguments: Paramètres de l'appel.

        Returns:
            Le résultat, avec `success=False` si le service a renvoyé une erreur.
        """
        result = await self._client.call_tool(name, arguments or {})
        text = "".join(block.text for block in result.content if isinstance(block, TextContent))
        return CallResult(
            success=not result.is_error,
            text=text,
            data=result.structured_content,
        )


@asynccontextmanager
async def connect(
    app: MircapApp,
    *,
    user: str | None = None,
    groups: Iterable[str] | None = None,
    ceiling: Iterable[str] | None = None,
) -> AsyncGenerator[TestSession]:
    """Se connecte en mémoire à `app` en simulant un utilisateur d'agent.

    Sans `user` ni `groups`, l'appel est anonyme (Features publiques seulement).

    Args:
        app: Application à tester.
        user: Identifiant d'un utilisateur déjà présent dans le `Store` de l'application.
        groups: Groupes d'un utilisateur ad hoc (alternative à `user`).
        ceiling: Plafond de permissions de l'identifiant simulé.

    Yields:
        Une session de test.

    Raises:
        ConfigurationError: Si `user` est inconnu ou si `user` et `groups` sont donnés
            ensemble.
    """
    if user is not None and groups is not None:
        raise ConfigurationError("Indiquer `user` ou `groups`, pas les deux.")
    identity: Identity | None = None
    if user is not None:
        stored = await app.store.get_user(user)
        if stored is None:
            raise ConfigurationError(f"Utilisateur de test inconnu : « {user} ».")
        identity = Identity(user=stored, method="test", ceiling=_tuple(ceiling))
    elif groups is not None:
        simulated = User(id="test-user", groups=tuple(groups))
        identity = Identity(user=simulated, method="test", ceiling=_tuple(ceiling))

    server = app.server(identity_source=fixed_identity(identity))
    async with Client(server) as client:
        yield TestSession(client)


def _tuple(values: Iterable[str] | None) -> tuple[str, ...] | None:
    return None if values is None else tuple(values)
