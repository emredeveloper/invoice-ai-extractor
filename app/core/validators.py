from typing import Dict, Any, List

class DataValidator:
    """Validator class for invoice data."""

    @staticmethod
    def validate_arithmetic(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensures quantity * unit_price = total_price for each item.
        """
        items = data.get("items", [])
        data["arithmetic_validation"] = []
        
        for i, item in enumerate(items):
            qty = item.get("quantity")
            unit_p = item.get("unit_price")
            total_p = item.get("total_price")
            
            if qty is not None and unit_p is not None and total_p is not None:
                expected = round(qty * unit_p, 2)
                is_valid = abs(expected - total_p) < 0.01
                data["arithmetic_validation"].append({
                    "item_index": i,
                    "is_valid": is_valid,
                    "expected": expected,
                    "found": total_p
                })
        return data

    @staticmethod
    def validate_tax(data: Dict[str, Any], default_tax_rate: float = 18.0) -> Dict[str, Any]:
        """
        Dynamically verify tax calculations.
        """
        items = data.get("items", [])
        sum_items = sum(item.get("total_price", 0) or 0 for item in items)
        
        # In multi-page or local LLM results, fields might be top-level or under general_fields
        total_amount = data.get("total_amount")
        tax_rate = data.get("tax_rate")
        
        if tax_rate is None:
            tax_rate = default_tax_rate
        
        if total_amount is not None:
            expected_with_tax = round(sum_items * (1 + (tax_rate / 100)), 2)
            matches_tax = abs(expected_with_tax - total_amount) < 1.0
            
            data["tax_validation"] = {
                "sum_items_net": sum_items,
                "detected_tax_rate": tax_rate,
                "expected_total_with_tax": expected_with_tax,
                "actual_total_amount": total_amount,
                "matches_tax_calculation": matches_tax
            }
        return data

    @classmethod
    def validate_invoice(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform all validations.
        """
        data = cls.validate_arithmetic(data)
        data = cls.validate_tax(data)
        return data
