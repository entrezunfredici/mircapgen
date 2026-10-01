"""Features liées aux clients."""

from mircapgen import Context, feature

_CUSTOMERS = {
    42: {"id": 42, "name": "John Doe"},
    43: {"id": 43, "name": "Jeanne Dupont"},
}


@feature(name="customer.search", permission="customer.read")
async def search_customer(query: str) -> list[dict[str, object]]:
    """Recherche des clients par nom."""
    needle = query.lower()
    return [item for item in _CUSTOMERS.values() if needle in str(item["name"]).lower()]


@feature(name="customer.delete", permission="customer.delete")
async def delete_customer(customer_id: int, ctx: Context) -> dict[str, object]:
    """Supprime définitivement un client."""
    removed = _CUSTOMERS.pop(customer_id, None)
    return {"deleted": removed is not None, "by": ctx.user.id if ctx.user else None}
