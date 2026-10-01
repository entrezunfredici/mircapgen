"""Contexte fourni à une Feature : qui appelle, et quelle requête."""

from __future__ import annotations

from dataclasses import dataclass

from mircapgen.rbac.models import User


@dataclass(frozen=True)
class Context:
    """Contexte d'un appel de Feature.

    Une Feature le demande en déclarant un paramètre annoté `Context`. Ce paramètre
    n'apparaît pas dans le schéma exposé à l'agent : l'IA ne peut ni le fournir ni
    le modifier.

    Attributes:
        user: Utilisateur d'agent au nom duquel l'appel est fait, `None` pour une
            Feature publique appelée sans identification.
        request_id: Identifiant de la requête, repris dans les logs.
    """

    user: User | None
    request_id: str
