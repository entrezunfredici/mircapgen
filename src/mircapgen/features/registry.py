"""Registre des Features d'une application : validation des déclarations et schémas."""

from __future__ import annotations

import inspect
import re
import typing
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, create_model

from mircapgen.context import Context
from mircapgen.features.decorator import get_spec
from mircapgen.features.spec import FeatureFunction, FeatureSpec
from mircapgen.rbac.permissions import is_valid_permission

_NAME_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")


@dataclass(frozen=True)
class Issue:
    """Problème détecté sur une déclaration de Feature.

    Attributes:
        severity: `error` exclut la Feature du service, `warning` la laisse active.
        feature: Nom de la Feature concernée.
        message: Explication en français.
    """

    severity: Literal["error", "warning"]
    feature: str
    message: str


@dataclass(frozen=True)
class RegisteredFeature:
    """Feature validée, prête à être exposée.

    Attributes:
        spec: Déclaration d'origine.
        function: Fonction métier.
        description: Description effective (déclarée ou tirée de la docstring).
        permission: Permission effectivement exigée, `None` si la Feature est publique
            ou interne.
        public: `True` si la Feature est effectivement publique.
        input_model: Modèle Pydantic décrivant les paramètres visibles par l'agent.
        context_param: Nom du paramètre qui reçoit le `Context`, s'il y en a un.
    """

    spec: FeatureSpec
    function: FeatureFunction
    description: str
    permission: str | None
    public: bool
    input_model: type[BaseModel]
    context_param: str | None

    @property
    def name(self) -> str:
        """Nom de la Feature."""
        return self.spec.name

    @property
    def exposed(self) -> bool:
        """`True` si la Feature peut être présentée à un agent."""
        return self.spec.mcp


class FeatureRegistry:
    """Ensemble des Features valides d'une application, et problèmes détectés."""

    def __init__(self, functions: Iterable[FeatureFunction] = ()) -> None:
        self._features: dict[str, RegisteredFeature] = {}
        self.issues: list[Issue] = []
        self._load(functions)

    def get(self, name: str) -> RegisteredFeature | None:
        """Renvoie la Feature nommée `name`, ou `None` si elle est inconnue ou exclue."""
        return self._features.get(name)

    def all(self) -> list[RegisteredFeature]:
        """Toutes les Features valides, triées par nom."""
        return sorted(self._features.values(), key=lambda item: item.name)

    @property
    def errors(self) -> list[Issue]:
        """Problèmes bloquants (Features exclues)."""
        return [issue for issue in self.issues if issue.severity == "error"]

    def _load(self, functions: Iterable[FeatureFunction]) -> None:
        by_name: dict[str, list[FeatureFunction]] = {}
        for function in functions:
            spec = get_spec(function)
            if spec is not None:
                by_name.setdefault(spec.name, []).append(function)

        for name, candidates in by_name.items():
            if len(candidates) > 1:
                # CHOIX: exclure toutes les Features homonymes plutôt que d'en garder une
                # RAISON: garder la première rendrait le comportement dépendant de l'ordre
                #         d'import ; en cas de doute, on ferme
                self._error(
                    name, "Nom de Feature dupliqué : toutes les Features de ce nom sont exclues."
                )
                continue
            registered = self._validate(candidates[0])
            if registered is not None:
                self._features[name] = registered

    def _error(self, feature: str, message: str) -> None:
        self.issues.append(Issue("error", feature, message))

    def _warning(self, feature: str, message: str) -> None:
        self.issues.append(Issue("warning", feature, message))

    def _validate(self, function: FeatureFunction) -> RegisteredFeature | None:
        spec = get_spec(function)
        if spec is None:  # pragma: no cover - filtré par l'appelant
            return None
        name = spec.name
        valid = True

        if not _NAME_RE.match(name):
            self._error(name, "Nom invalide : attendu « domaine.action » en minuscules.")
            valid = False

        description = spec.description or _docstring_summary(function)
        if not description:
            self._warning(name, "Aucune description : l'agent ne saura pas à quoi sert la Feature.")

        permission = spec.permission
        public = spec.public
        if spec.mcp:
            if permission is None and not public:
                self._error(
                    name,
                    "Ni `permission` ni `public=True` déclarés : la Feature est inaccessible.",
                )
                valid = False
            elif permission is not None and public:
                # CHOIX: la règle la plus restrictive s'applique en cas de double déclaration
                # RAISON: une erreur de copier-coller ne doit jamais ouvrir une Feature protégée
                self._warning(
                    name,
                    "`permission` et `public=True` déclarés ensemble : la permission est exigée, "
                    "`public` est ignoré.",
                )
                public = False
            if permission is not None and not is_valid_permission(permission):
                self._error(name, f"Permission invalide : « {permission} ».")
                valid = False

        built = _build_input_model(function, name)
        if isinstance(built, str):
            self._error(name, built)
            valid = False

        if not valid or isinstance(built, str):
            return None
        input_model, context_param = built
        return RegisteredFeature(
            spec=spec,
            function=function,
            description=description or "",
            permission=permission,
            public=public,
            input_model=input_model,
            context_param=context_param,
        )


def _docstring_summary(function: FeatureFunction) -> str:
    doc = inspect.getdoc(function)
    return doc.strip().splitlines()[0].strip() if doc else ""


def _build_input_model(
    function: FeatureFunction, name: str
) -> tuple[type[BaseModel], str | None] | str:
    """Construit le modèle des paramètres visibles par l'agent.

    Returns:
        Le modèle et le nom du paramètre `Context`, ou un message d'erreur si la
        signature n'est pas supportée.
    """
    signature = inspect.signature(function)
    try:
        hints = typing.get_type_hints(function, include_extras=True)
    except Exception as error:
        return f"Annotations illisibles : {error}"

    fields: dict[str, Any] = {}
    context_param: str | None = None
    for parameter in signature.parameters.values():
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            return "Les paramètres `*args` et `**kwargs` ne sont pas supportés."
        annotation = hints.get(parameter.name, Any)
        if annotation is Context:
            if context_param is not None:
                return "Un seul paramètre `Context` est autorisé."
            context_param = parameter.name
            continue
        if parameter.annotation is inspect.Parameter.empty:
            return f"Le paramètre « {parameter.name} » n'a pas d'annotation de type."
        default = ... if parameter.default is inspect.Parameter.empty else parameter.default
        fields[parameter.name] = (annotation, default)

    model_name = "Input_" + re.sub(r"\W", "_", name)
    model = create_model(model_name, __config__=ConfigDict(extra="forbid"), **fields)
    return model, context_param
