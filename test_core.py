import pytest
from validators import validate_arithmetic, validate_tax

def test_arithmetic_validation():
    data = {
        "items": [
            {"product_name": "A", "quantity": 2, "unit_price": 50, "total_price": 100},
            {"product_name": "B", "quantity": 1, "unit_price": 20, "total_price": 25} # Incorrect
        ]
    }
    result = validate_arithmetic(data)
    assert result["arithmetic_validation"][0]["is_valid"] is True
    assert result["arithmetic_validation"][1]["is_valid"] is False

def test_tax_validation():
    data = {
        "general_fields": {"total_amount": 118},
        "items": [
            {"total_price": 100}
        ]
    }
    result = validate_tax(data, tax_rate=0.18)
    assert result["tax_validation"]["matches_standard_vat"] is True

    data_fail = {
        "general_fields": {"total_amount": 150},
        "items": [
            {"total_price": 100}
        ]
    }
    result_fail = validate_tax(data_fail, tax_rate=0.18)
    assert result_fail["tax_validation"]["matches_standard_vat"] is False
