"""Pipeline d'un appel : visibilité, autorisation, validation, exécution, audit.

Ce module ne dépend pas du protocole MCP : il reçoit une identité déjà vérifiée et
renvoie un résultat sérialisable. L'adaptateur `mircapgen.mcp` fait le lien avec le SDK.
"""

from __future__ import annotations

import inspect
import logging
import time
from collections.abc import Mapping
from typing import Any

import anyio.to_thread
from pydantic import ValidationError as PydanticValidationError
from pydantic_core import to_jsonable_python

from mircapgen.context import Context
from mircapgen.errors import (
    InternalError,
    MircapError,
    UnknownFeatureError,
    ValidationError,
)
from mircapgen.features.registry import FeatureRegistry, RegisteredFeature
from mircapgen.logs import audit_logger, log_event, technical_logger
from mircapgen.rbac.models import Group, Identity

_VALIDATION_MESSAGES = {
    "missing": "paramètre obligatoire",
    "extra_forbidden": "paramètre inconnu",
}


class Dispatcher:
    """Applique le pipeline de requête aux Features d'un registre.

    Args:
        registry: Features valides de l'application.
        groups: Groupes de droits connus, indexés par nom.
        require_credential: Si `True`, aucun appel n'est accepté sans identité valide,
            y compris pour les Features publiques (`identity.require_credential`).
    """

    def __init__(
        self,
        registry: FeatureRegistry,
        groups: Mapping[str, Group],
        *,
        require_credential: bool = False,
    ) -> None:
        self._registry = registry
        self._groups = groups
        self._require_credential = require_credential

    def visible_features(self, identity: Identity | None) -> list[RegisteredFeature]:
        """Liste les Features que `identity` peut voir (permission = accès + visibilité).

        Args:
            identity: Identité de l'appelant, ou `None` s'il n'est pas identifié.

        Returns:
            Les Features exposées et autorisées, triées par nom. Sans identité, seules
            les Features publiques sont visibles, et aucune si une identité est exigée.
        """
        if identity is None and self._require_credential:
            return []
        return [item for item in self._registry.all() if self._is_visible(item, identity)]

    def _is_visible(self, item: RegisteredFeature, identity: Identity | None) -> bool:
        if not item.exposed:
            return False
        if item.public:
            return True
        if identity is None or item.permission is None:
            return False
        return identity.can(item.permission, self._groups)

    async def call(
        self,
        identity: Identity | None,
        name: str,
        arguments: Mapping[str, Any] | None,
        *,
        request_id: str,
    ) -> Any:
        """Exécute la Feature `name` pour `identity`.

        Args:
            identity: Identité de l'appelant, ou `None` s'il n'est pas identifié.
            name: Nom de la Feature demandée.
            arguments: Paramètres fournis par l'agent.
            request_id: Identifiant de la requête, repris dans les logs.

        Returns:
            Le résultat de la Feature, converti en structure JSON.

        Raises:
            UnknownFeatureError: Si la Feature n'existe pas ou n'est pas visible.
            ValidationError: Si les paramètres ne respectent pas le schéma.
            MircapError: Toute erreur volontaire de la Feature.
            InternalError: Pour toute autre exception, sans en révéler le détail.
        """
        started = time.perf_counter()
        status = "success"
        error_code: str | None = None
        try:
            item = self._find_visible(identity, name)
            kwargs = self._validate(item, arguments, identity, request_id)
            result = await _invoke(item, kwargs)
            return to_jsonable_python(result)
        except MircapError as error:
            status = "denied" if isinstance(error, UnknownFeatureError) else "error"
            error_code = error.code
            raise
        except Exception as error:
            status = "error"
            error_code = InternalError.code
            technical_logger.error("Erreur inattendue dans la Feature « %s »", name, exc_info=error)
            raise InternalError("Une erreur interne est survenue.") from error
        finally:
            log_event(
                audit_logger,
                logging.INFO if status == "success" else logging.WARNING,
                "feature_call",
                request_id=request_id,
                feature=name,
                user=identity.user.id if identity else None,
                auth_method=identity.method if identity else None,
                credential=identity.credential_id if identity else None,
                status=status,
                error=error_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )

    def _find_visible(self, identity: Identity | None, name: str) -> RegisteredFeature:
        for item in self.visible_features(identity):
            if item.name == name:
                return item
        raise UnknownFeatureError(f"Outil inconnu : « {name} ».")

    def _validate(
        self,
        item: RegisteredFeature,
        arguments: Mapping[str, Any] | None,
        identity: Identity | None,
        request_id: str,
    ) -> dict[str, Any]:
        try:
            model = item.input_model.model_validate(dict(arguments or {}))
        except PydanticValidationError as error:
            raise ValidationError(_describe(error)) from None
        kwargs = {field: getattr(model, field) for field in type(model).model_fields}
        if item.context_param is not None:
            kwargs[item.context_param] = Context(
                user=identity.user if identity else None, request_id=request_id
            )
        return kwargs


async def _invoke(item: RegisteredFeature, kwargs: dict[str, Any]) -> Any:
    function = item.function
    if inspect.iscoroutinefunction(function):
        return await function(**kwargs)
    return await anyio.to_thread.run_sync(lambda: function(**kwargs))


def _describe(error: PydanticValidationError) -> str:
    """Résume une erreur de validation en français, sans jamais citer les valeurs reçues."""
    parts: list[str] = []
    for detail in error.errors(include_input=False, include_url=False):
        field = ".".join(str(part) for part in detail["loc"]) or "paramètres"
        reason = _VALIDATION_MESSAGES.get(detail["type"], f"valeur invalide ({detail['msg']})")
        parts.append(f"« {field} » : {reason}")
    return "Paramètres invalides — " + " ; ".join(parts) + "."
