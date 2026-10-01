"""Features techniques, ouvertes à tous."""

from mircapgen import feature


@feature(name="system.status", public=True)
async def system_status() -> dict[str, str]:
    """Indique l'état du service."""
    return {"status": "ok"}
