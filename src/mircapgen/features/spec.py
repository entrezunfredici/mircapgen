"""Déclaration d'une Feature : métadonnées portées par le décorateur `@feature`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

FEATURE_ATTR = "__mircap_feature__"

FeatureFunction = Callable[..., Any]


@dataclass(frozen=True)
class FeatureSpec:
    """Métadonnées d'une Feature, telles que le développeur les a déclarées.

    Aucune validation n'est faite ici : une déclaration invalide est détectée au
    chargement de l'application, qui exclut la Feature et journalise l'erreur
    (cahier des charges §24).

    Attributes:
        name: Nom de la Feature (`domaine.action`), identique au nom du tool MCP.
        description: Ce que fait la Feature ; par défaut, première ligne de la docstring.
        permission: Permission exigée de l'utilisateur, `None` pour une Feature publique.
        public: `True` si la Feature est appelable sans utilisateur identifié.
        mcp: `False` pour garder la Feature interne (non exposée à un agent).
        label: Libellé lisible, facultatif.
    """

    name: str
    description: str | None = None
    permission: str | None = None
    public: bool = False
    mcp: bool = True
    label: str | None = None
