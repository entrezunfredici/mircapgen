"""Application Mircapgen : assemble Features, droits, stockage et serveur MCP."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from types import ModuleType
from typing import Any

from mircapgen.core.dispatcher import Dispatcher
from mircapgen.features.discovery import discover
from mircapgen.features.registry import FeatureRegistry
from mircapgen.features.spec import FeatureFunction
from mircapgen.logs import log_event, technical_logger
from mircapgen.rbac.models import Group
from mircapgen.store.base import Store
from mircapgen.store.memory import MemoryStore


class MircapApp:
    """Un microservice Mircapgen.

    Args:
        name: Nom du service.
        features: Où chercher les Features : nom de module ou de paquet (parcouru
            récursivement), module, ou liste de fonctions marquées `@feature`.
        groups: Groupes de droits du service.
        store: Persistance des utilisateurs et des clés ; en mémoire par défaut.
        instructions: Texte d'accompagnement transmis aux agents (Helper).
        version: Version du service.
        require_credential: Exige un identifiant valide pour toute connexion, y compris
            pour les Features publiques (`identity.require_credential`).
    """

    def __init__(
        self,
        name: str,
        *,
        features: str | ModuleType | Iterable[FeatureFunction] = (),
        groups: Iterable[Group] = (),
        store: Store | None = None,
        instructions: str | None = None,
        version: str = "0.0.1",
        require_credential: bool = False,
    ) -> None:
        self.name = name
        self.version = version
        self.instructions = instructions
        self.require_credential = require_credential
        self.store: Store = store if store is not None else MemoryStore()
        self.groups: dict[str, Group] = {group.name: group for group in groups}

        functions = discover(features) if isinstance(features, (str, ModuleType)) else features
        self.registry = FeatureRegistry(functions)
        self._report_issues()
        self.dispatcher = Dispatcher(
            self.registry, self.groups, require_credential=require_credential
        )

    def _report_issues(self) -> None:
        for issue in self.registry.issues:
            level = logging.ERROR if issue.severity == "error" else logging.WARNING
            log_event(
                technical_logger,
                level,
                "feature_declaration",
                feature=issue.feature,
                severity=issue.severity,
                message=issue.message,
            )

    def server(self, identity_source: Any = None) -> Any:
        """Construit le serveur MCP de l'application.

        Args:
            identity_source: Source d'identité ; par défaut, l'identité vérifiée de la
                requête HTTP en cours.

        Returns:
            Un serveur MCP bas niveau.
        """
        from mircapgen.mcp.server import build_server, identity_from_access_token

        return build_server(
            self.name,
            version=self.version,
            instructions=self.instructions,
            dispatcher=self.dispatcher,
            identity_source=identity_source or identity_from_access_token,
        )

    def http_app(self, *, host: str = "127.0.0.1") -> Any:
        """Construit l'application HTTP (ASGI) qui sert le MCP sur `/mcp`.

        Args:
            host: Adresse d'écoute prévue ; sert à activer la protection contre le
                rebond DNS pour l'écoute locale.

        Returns:
            Une application Starlette.
        """
        from mircapgen.mcp.http import build_http_app

        return build_http_app(self, host=host)

    def run(self, *, host: str = "127.0.0.1", port: int = 8000) -> None:
        """Lance le service en HTTP.

        Args:
            host: Adresse d'écoute.
            port: Port d'écoute.
        """
        import uvicorn

        uvicorn.run(self.http_app(host=host), host=host, port=port)
