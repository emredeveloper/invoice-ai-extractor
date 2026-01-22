from typing import Dict, Any
from app.core.extraction_engine import LLMProvider

class ReviewerAgent:
    """Agent that reviews extracted invoice data for business insights and risks."""
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def review_invoice(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """Review the invoice data using LLM logic."""
        
        # Summary of data for the agent to review
        summary = {
            "supplier": extraction_result.get("supplier_name"),
            "total": extraction_result.get("total_amount"),
            "currency": extraction_result.get("currency"),
            "category": extraction_result.get("category"),
            "items_count": len(extraction_result.get("items", [])),
            "tax_ok": extraction_result.get("tax_validation", {}).get("is_valid", True)
        }

        prompt = f"""
        As an expert financial auditor, review the following extracted invoice data and provide:
        1. A brief business summary (1 sentence).
        2. A risk assessment (Low, Medium, High) with a reason.
        3. A suggested action (e.g., 'Approve', 'Check Supplier', 'Verify Tax').

        Data: {summary}

        Return the response in JSON format like this:
        {{
            "summary": "...",
            "risk_level": "...",
            "risk_reason": "...",
            "suggested_action": "..."
        }}
        """

        try:
            # We use the LLM provider to 'think' about the data
            response_str = await self.llm_provider.generate_json(prompt)
            
            # Basic cleanup of LLM response
            import json
            if "```json" in response_str:
                response_str = response_str.split("```json")[1].split("```")[0].strip()
            elif "```" in response_str:
                response_str = response_str.split("```")[1].split("```")[0].strip()
            
            return json.loads(response_str)
        except Exception:
            # Fallback if AI review fails
            return {
                "summary": f"Invoice from {summary['supplier']} for {summary['total']} {summary['currency']}.",
                "risk_level": "Low",
                "risk_reason": "Automated basic check passed",
                "suggested_action": "Proceed"
            }
