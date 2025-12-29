from typing import Dict, Any, List

def validate_arithmetic(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures quantity * unit_price = total_price for each item.
    Adds a 'validation' field to the data.
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

def validate_tax(data: Dict[str, Any], default_tax_rate: float = 18.0) -> Dict[str, Any]:
    """
    Dynamically verify tax calculations.
    Uses the tax_rate extracted from the invoice itself if available,
    otherwise falls back to the default_tax_rate (18%).
    Supports any tax rate: 1%, 8%, 10%, 18%, 20%, etc.
    """
    items = data.get("items", [])
    sum_items = sum(item.get("total_price", 0) or 0 for item in items)
    
    general = data.get("general_fields", {})
    total_amount = general.get("total_amount")
    
    # Try to use the extracted tax_rate, otherwise use the default
    extracted_tax_rate = general.get("tax_rate")
    tax_rate = extracted_tax_rate if extracted_tax_rate is not None else default_tax_rate
    
    if total_amount is not None:
        # Calculate expected total with the detected/default tax rate
        expected_with_tax = round(sum_items * (1 + (tax_rate / 100)), 2)
        matches_tax = abs(expected_with_tax - total_amount) < 1.0  # Allow small variance
        
        data["tax_validation"] = {
            "sum_items_net": sum_items,
            "detected_tax_rate": tax_rate,
            "expected_total_with_tax": expected_with_tax,
            "actual_total_amount": total_amount,
            "matches_tax_calculation": matches_tax
        }
    return data
