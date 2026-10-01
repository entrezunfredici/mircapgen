"""Modèles du RBAC : utilisateurs d'agents, groupes et identité d'un appel."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from mircapgen.errors import ConfigurationError
from mircapgen.rbac.permissions import allows, is_valid_pattern


@dataclass(frozen=True)
class Group:
    """Groupe de droits : un nom et les motifs de permissions qu'il accorde.

    Attributes:
        name: Nom unique du groupe.
        permissions: Motifs accordés (`customer.read`, `customer.*`, `*`).
    """

    name: str
    permissions: frozenset[str] = field(default_factory=frozenset[str])

    def __init__(self, name: str, permissions: Iterable[str] = ()) -> None:
        patterns = frozenset(permissions)
        for pattern in patterns:
            if not is_valid_pattern(pattern):
                raise ConfigurationError(
                    f"Motif de permission invalide dans le groupe « {name} » : « {pattern} »."
                )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "permissions", patterns)


@dataclass(frozen=True)
class User:
    """Utilisateur d'agent : la personne au nom de laquelle un agent agit.

    Attributes:
        id: Identifiant unique stable.
        groups: Noms des groupes de droits auxquels il appartient.
        display_name: Nom lisible, facultatif.
        active: Un utilisateur désactivé est refusé même avec un identifiant valide.
    """

    id: str
    groups: tuple[str, ...] = ()
    display_name: str | None = None
    active: bool = True


@dataclass(frozen=True)
class Identity:
    """Qui appelle : l'utilisateur, la méthode de preuve et le plafond de l'identifiant.

    Attributes:
        user: Utilisateur d'agent identifié.
        method: Méthode d'identification (`key` en 0.0).
        credential_id: Repère non secret de l'identifiant d'accès (préfixe de clé).
        ceiling: Plafond de permissions de l'identifiant, `None` si aucun.
    """

    user: User
    method: str
    credential_id: str | None = None
    ceiling: tuple[str, ...] | None = None

    def user_patterns(self, groups: Mapping[str, Group]) -> frozenset[str]:
        """Motifs de permissions accordés à l'utilisateur par ses groupes."""
        patterns: set[str] = set()
        for name in self.user.groups:
            group = groups.get(name)
            if group is not None:
                patterns.update(group.permissions)
        return frozenset(patterns)

    def can(self, permission: str, groups: Mapping[str, Group]) -> bool:
        """Indique si l'appel est autorisé pour `permission`.

        Les droits effectifs sont l'intersection des droits de l'utilisateur et du
        plafond de l'identifiant d'accès (cahier des charges §8.7).

        Args:
            permission: Permission concrète exigée par une Feature.
            groups: Groupes connus du service, indexés par nom.

        Returns:
            `True` si l'utilisateur et le plafond autorisent la permission.
        """
        if not self.user.active:
            return False
        if not allows(self.user_patterns(groups), permission):
            return False
        return self.ceiling is None or allows(self.ceiling, permission)
