"""Logs structurés : une ligne JSON par événement d'audit (cahier des charges §15).

Seuls des champs maîtrisés par le framework sont journalisés. Les arguments des
Features, qui peuvent contenir des données sensibles, ne le sont jamais.
"""

from __future__ import annotations

import json
import logging
from typing import Any

technical_logger = logging.getLogger("mircapgen")
audit_logger = logging.getLogger("mircapgen.audit")


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    """Écrit un événement structuré sur une ligne JSON.

    Args:
        logger: Logger de destination.
        level: Niveau de journalisation.
        event: Nom de l'événement (`feature_call`, `feature_error`…).
        **fields: Champs complémentaires, sérialisables en JSON.
    """
    payload: dict[str, Any] = {"event": event, **fields}
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))
