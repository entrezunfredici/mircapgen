"""Format des permissions et correspondance avec les jokers (cahier des charges §9.2)."""

from __future__ import annotations

import re
from collections.abc import Iterable

_SEGMENT = r"[a-z0-9_]+"
_PERMISSION_RE = re.compile(rf"^{_SEGMENT}(\.{_SEGMENT})+$")
_PATTERN_RE = re.compile(rf"^(\*|{_SEGMENT}(\.{_SEGMENT})*(\.\*)?)$")


def is_valid_permission(permission: str) -> bool:
    """Indique si `permission` est une permission concrète valide (`domaine.verbe`).

    Une permission exigée par une Feature n'accepte aucun joker.

    Args:
        permission: Chaîne à tester.

    Returns:
        `True` si la chaîne a au moins deux segments en minuscules séparés par des points.
    """
    return _PERMISSION_RE.match(permission) is not None


def is_valid_pattern(pattern: str) -> bool:
    """Indique si `pattern` est valide dans un groupe ou un plafond.

    Un motif est une permission, éventuellement terminée par `.*`, ou un `*` seul.

    Args:
        pattern: Chaîne à tester.

    Returns:
        `True` si le motif est bien formé.
    """
    return _PATTERN_RE.match(pattern) is not None


def matches(pattern: str, permission: str) -> bool:
    """Indique si `pattern` couvre `permission`.

    `customer.*` couvre toute permission qui commence par `customer.` ; `*` couvre tout.

    Args:
        pattern: Motif d'un groupe ou d'un plafond.
        permission: Permission concrète exigée par une Feature.

    Returns:
        `True` si la permission est couverte.
    """
    if pattern == "*":
        return True
    if pattern.endswith(".*"):
        return permission.startswith(pattern[:-1])
    return pattern == permission


def allows(patterns: Iterable[str], permission: str) -> bool:
    """Indique si au moins un motif de `patterns` couvre `permission`."""
    return any(matches(pattern, permission) for pattern in patterns)
