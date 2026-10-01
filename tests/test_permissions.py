import pytest

from mircapgen.errors import ConfigurationError
from mircapgen.rbac.models import Group
from mircapgen.rbac.permissions import allows, is_valid_pattern, is_valid_permission, matches


@pytest.mark.parametrize("value", ["customer.read", "a.b.c", "invoice_2.read_all"])
def test_is_valid_permission__well_formed__true(value: str) -> None:
    assert is_valid_permission(value)


@pytest.mark.parametrize("value", ["customer", "Customer.read", "customer.*", "*", "a..b", ""])
def test_is_valid_permission__malformed_or_wildcard__false(value: str) -> None:
    assert not is_valid_permission(value)


@pytest.mark.parametrize("value", ["customer.read", "customer.*", "*", "admin.*"])
def test_is_valid_pattern__well_formed__true(value: str) -> None:
    assert is_valid_pattern(value)


@pytest.mark.parametrize("value", ["*.read", "customer.*.x", "**", "customer.", ""])
def test_is_valid_pattern__malformed__false(value: str) -> None:
    assert not is_valid_pattern(value)


def test_matches__exact_and_wildcards__follow_segments() -> None:
    assert matches("customer.read", "customer.read")
    assert not matches("customer.read", "customer.write")
    assert matches("customer.*", "customer.read")
    assert matches("customer.*", "customer.read.all")
    assert not matches("customer.*", "customers.read")
    assert matches("*", "anything.at_all")


def test_allows__no_pattern__denies() -> None:
    assert not allows([], "customer.read")


def test_group__invalid_pattern__raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        Group("bad", ["customer.*.x"])
