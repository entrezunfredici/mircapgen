"""Découverte des Features : parcours d'un module ou d'un paquet."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from types import ModuleType

from mircapgen.features.decorator import get_spec
from mircapgen.features.spec import FeatureFunction


def discover(target: str | ModuleType) -> list[FeatureFunction]:
    """Trouve les fonctions marquées `@feature` dans un module ou un paquet.

    Un paquet est parcouru récursivement. Seules les fonctions **définies** dans un
    module parcouru sont retenues : une Feature importée depuis un autre module n'est
    pas comptée deux fois.

    Args:
        target: Nom d'un module ou d'un paquet, ou le module lui-même.

    Returns:
        Les fonctions marquées, dans l'ordre de découverte.
    """
    root = importlib.import_module(target) if isinstance(target, str) else target
    modules: list[ModuleType] = [root]
    search_path = getattr(root, "__path__", None)
    if search_path is not None:
        for info in pkgutil.walk_packages(search_path, prefix=f"{root.__name__}."):
            modules.append(importlib.import_module(info.name))

    found: list[FeatureFunction] = []
    for module in modules:
        for _, member in inspect.getmembers(module, inspect.isfunction):
            if member.__module__ == module.__name__ and get_spec(member) is not None:
                found.append(member)
    return found
