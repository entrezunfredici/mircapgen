"""Contrat de stockage des données du framework (cahier des charges §12.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from mircapgen.rbac.models import User


@dataclass(frozen=True)
class ApiKeyRecord:
    """Clé personnelle telle que conservée : jamais en clair, seulement son empreinte.

    Attributes:
        prefix: Repère non secret, repris dans les logs.
        key_hash: Empreinte SHA-256 (hexadécimale) de la clé complète.
        user_id: Utilisateur propriétaire.
        label: Étiquette libre (par exemple « Hermes du bureau »).
        ceiling: Plafond de permissions de la clé, `None` si aucun.
        expires_at: Date d'expiration (UTC), `None` si la clé n'expire pas.
        revoked: `True` si la clé a été révoquée.
    """

    prefix: str
    key_hash: str
    user_id: str
    label: str = ""
    ceiling: tuple[str, ...] | None = None
    expires_at: datetime | None = None
    revoked: bool = False


class Store(Protocol):
    """Ce que le framework lit dans la persistance.

    L'accès est asynchrone pour le reste du framework, quelle que soit
    l'implémentation (mémoire, SQL, ou celle d'un développeur).
    """

    async def get_user(self, user_id: str) -> User | None:
        """Renvoie l'utilisateur `user_id`, ou `None` s'il est inconnu."""
        ...

    async def get_key(self, prefix: str) -> ApiKeyRecord | None:
        """Renvoie la clé de préfixe `prefix`, ou `None` si elle est inconnue."""
        ...
