"""Clés personnelles : génération, empreinte et vérification (cahier des charges §8.5).

Le format des clés est provisoire (question 19 du cahier des charges).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from mircapgen.rbac.models import Identity
from mircapgen.store.base import Store

KEY_PREFIX = "mk_"
_PREFIX_LENGTH = 8


@dataclass(frozen=True)
class GeneratedKey:
    """Clé fraîchement générée.

    Attributes:
        secret: Clé complète, à afficher **une seule fois** puis à ne plus conserver.
        prefix: Repère non secret de la clé.
        key_hash: Empreinte à stocker.
    """

    secret: str
    prefix: str
    key_hash: str


def hash_key(raw_key: str) -> str:
    """Calcule l'empreinte SHA-256 (hexadécimale) d'une clé complète."""
    # CHOIX: SHA-256 simple plutôt qu'un hachage lent (bcrypt, argon2)
    # RAISON: la clé est aléatoire sur 256 bits, un hachage lent n'apporte rien contre
    #         la force brute et ralentirait chaque requête
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_key() -> GeneratedKey:
    """Génère une clé personnelle aléatoire.

    Returns:
        La clé complète, son préfixe et son empreinte.
    """
    prefix = secrets.token_hex(_PREFIX_LENGTH // 2)
    secret = f"{KEY_PREFIX}{prefix}_{secrets.token_urlsafe(32)}"
    return GeneratedKey(secret=secret, prefix=prefix, key_hash=hash_key(secret))


def extract_prefix(raw_key: str) -> str | None:
    """Extrait le préfixe d'une clé complète, ou `None` si le format est invalide."""
    head = len(KEY_PREFIX) + _PREFIX_LENGTH
    if not raw_key.startswith(KEY_PREFIX) or len(raw_key) <= head + 1 or raw_key[head] != "_":
        return None
    return raw_key[len(KEY_PREFIX) : head]


async def authenticate_key(store: Store, raw_key: str) -> Identity | None:
    """Vérifie une clé et renvoie l'identité qu'elle prouve.

    Args:
        store: Persistance où chercher la clé et son utilisateur.
        raw_key: Clé complète présentée par le client.

    Returns:
        L'identité de l'appelant, ou `None` si la clé est invalide, inconnue, révoquée,
        expirée, ou si son utilisateur est inconnu ou désactivé. Le motif précis n'est
        volontairement pas distingué pour l'appelant.
    """
    prefix = extract_prefix(raw_key)
    if prefix is None:
        return None
    record = await store.get_key(prefix)
    # Le hachage est calculé même si la clé est inconnue, pour ne pas révéler par le
    # temps de réponse qu'un préfixe existe.
    presented = hash_key(raw_key)
    if record is None or not hmac.compare_digest(presented, record.key_hash):
        return None
    if record.revoked:
        return None
    if record.expires_at is not None and _as_utc(record.expires_at) <= datetime.now(UTC):
        return None
    user = await store.get_user(record.user_id)
    if user is None or not user.active:
        return None
    return Identity(user=user, method="key", credential_id=record.prefix, ceiling=record.ceiling)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
