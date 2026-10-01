"""Décorateur `@feature` : marque une fonction métier comme Feature."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from mircapgen.features.spec import FEATURE_ATTR, FeatureFunction, FeatureSpec

_F = TypeVar("_F", bound=FeatureFunction)


def feature(
    *,
    name: str,
    description: str | None = None,
    permission: str | None = None,
    public: bool = False,
    mcp: bool = True,
    label: str | None = None,
) -> Callable[[_F], _F]:
    """Déclare une fonction comme Feature exposable à un agent.

    Le décorateur ne fait que **marquer** la fonction avec ses métadonnées : il
    n'enregistre rien dans un état global. C'est l'application qui découvre les
    fonctions marquées en parcourant ses modules, ce qui garde les tests isolés et
    chaque fichier de Feature indépendant.

    Args:
        name: Nom de la Feature (`domaine.action`).
        description: Ce que fait la Feature ; par défaut, première ligne de la docstring.
        permission: Permission exigée (`domaine.verbe`) ; à omettre pour une Feature publique.
        public: `True` pour une Feature appelable sans utilisateur identifié.
        mcp: `False` pour garder la Feature interne.
        label: Libellé lisible, facultatif.

    Returns:
        Un décorateur qui renvoie la fonction d'origine, inchangée.
    """
    spec = FeatureSpec(
        name=name,
        description=description,
        permission=permission,
        public=public,
        mcp=mcp,
        label=label,
    )

    def decorate(function: _F) -> _F:
        setattr(function, FEATURE_ATTR, spec)
        return function

    return decorate


def get_spec(function: FeatureFunction) -> FeatureSpec | None:
    """Renvoie la déclaration portée par `function`, ou `None` si elle n'est pas une Feature."""
    spec = getattr(function, FEATURE_ATTR, None)
    return spec if isinstance(spec, FeatureSpec) else None
