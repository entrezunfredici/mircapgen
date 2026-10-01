"""Assemblage du service d'exemple."""

from mircapgen import Group, MemoryStore, MircapApp
from mircapgen.store.base import Store


def build_app(store: Store | None = None) -> MircapApp:
    """Construit l'application d'exemple.

    Args:
        store: Persistance à utiliser ; en mémoire par défaut.

    Returns:
        Un service avec deux groupes : `reader` (lecture) et `manager` (lecture et suppression).
    """
    return MircapApp(
        "crm-service",
        features="crm_service.features",
        groups=[
            Group("reader", ["customer.read"]),
            Group("manager", ["customer.read", "customer.delete"]),
        ],
        store=store if store is not None else MemoryStore(),
        instructions="Toujours rechercher un client avant d'en supprimer un.",
    )
