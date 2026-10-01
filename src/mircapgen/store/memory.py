"""Stockage en mémoire : tests, prototype et chargement depuis un fichier YAML."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from mircapgen.errors import ConfigurationError
from mircapgen.rbac.models import User
from mircapgen.store.base import ApiKeyRecord


class MemoryStore:
    """Implémentation du `Store` qui garde tout en mémoire.

    Args:
        users: Utilisateurs d'agents connus.
        keys: Clés personnelles connues (empreintes uniquement).
    """

    def __init__(self, users: Iterable[User] = (), keys: Iterable[ApiKeyRecord] = ()) -> None:
        self._users = {user.id: user for user in users}
        self._keys = {key.prefix: key for key in keys}

    async def get_user(self, user_id: str) -> User | None:
        """Renvoie l'utilisateur `user_id`, ou `None` s'il est inconnu."""
        return self._users.get(user_id)

    async def get_key(self, prefix: str) -> ApiKeyRecord | None:
        """Renvoie la clé de préfixe `prefix`, ou `None` si elle est inconnue."""
        return self._keys.get(prefix)

    def add_user(self, user: User) -> None:
        """Ajoute ou remplace un utilisateur."""
        self._users[user.id] = user

    def add_key(self, key: ApiKeyRecord) -> None:
        """Ajoute ou remplace une clé."""
        self._keys[key.prefix] = key

    @classmethod
    def from_yaml(cls, path: str | Path) -> MemoryStore:
        """Charge utilisateurs et clés depuis un fichier YAML.

        Format attendu :

        ```yaml
        users:
          - id: alice
            groups: [reader]
            keys:
              - prefix: ab12cd34
                hash: <empreinte sha-256 hexadécimale>
                label: Hermes du bureau
                ceiling: [customer.read]
        ```

        Args:
            path: Chemin du fichier.

        Returns:
            Le stockage initialisé.

        Raises:
            ConfigurationError: Si le fichier est absent ou mal formé.
        """
        try:
            raw: Any = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        except OSError as error:
            raise ConfigurationError(f"Fichier d'utilisateurs illisible : {path}.") from error
        except yaml.YAMLError as error:
            raise ConfigurationError(f"Fichier d'utilisateurs mal formé : {path}.") from error
        return cls.from_mapping(raw or {})

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> MemoryStore:
        """Construit le stockage depuis un dictionnaire (voir `from_yaml`)."""
        users: list[User] = []
        keys: list[ApiKeyRecord] = []
        for entry in data.get("users", []):
            try:
                user = User(
                    id=str(entry["id"]),
                    groups=tuple(entry.get("groups", ())),
                    display_name=entry.get("display_name"),
                    active=bool(entry.get("active", True)),
                )
                users.append(user)
                for key in entry.get("keys", []):
                    ceiling = key.get("ceiling")
                    expires = key.get("expires_at")
                    keys.append(
                        ApiKeyRecord(
                            prefix=str(key["prefix"]),
                            key_hash=str(key["hash"]),
                            user_id=user.id,
                            label=str(key.get("label", "")),
                            ceiling=tuple(ceiling) if ceiling is not None else None,
                            expires_at=_parse_datetime(expires) if expires else None,
                            revoked=bool(key.get("revoked", False)),
                        )
                    )
            except (KeyError, TypeError) as error:
                raise ConfigurationError(
                    "Entrée d'utilisateur ou de clé invalide dans le fichier d'utilisateurs."
                ) from error
        return cls(users, keys)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
