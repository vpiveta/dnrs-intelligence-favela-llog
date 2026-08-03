from datetime import date
from decimal import Decimal

from app.core.identity import abbreviate_person, client_address_key, normalize_address
from app.core.operational_rules import value_risk_level


def test_client_recurrence_key_requires_same_address():
    a = client_address_key("João Silva", "Rua A, 10")
    b = client_address_key("JOAO SILVA", "Rua A 10")
    c = client_address_key("João Silva", "Rua B, 20")
    assert a == b
    assert a != c


def test_address_preserves_number():
    assert "10" in normalize_address("Rua A, nº 10")


def test_driver_abbreviation():
    assert abbreviate_person("João da Silva Santos") == "João S."


def test_value_ranges():
    assert value_risk_level(Decimal("99.99")) == "BAIXO"
    assert value_risk_level(Decimal("100")) == "MEDIO"
    assert value_risk_level(Decimal("500")) == "ALTO"
    assert value_risk_level(Decimal("1000")) == "CRITICO"
