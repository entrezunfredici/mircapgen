from collections.abc import Iterator

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _restore_example_data() -> Iterator[None]:
    """Les Features d'exemple modifient des données de module : on les restaure."""
    from crm_service.features import customer

    snapshot = dict(customer._CUSTOMERS)
    yield
    customer._CUSTOMERS.clear()
    customer._CUSTOMERS.update(snapshot)
