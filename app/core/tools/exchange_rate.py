import httpx
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class ExchangeRateTool:
    """Tool to fetch exchange rates and convert amounts to TRY."""
    
    def __init__(self):
        # Using a free API for demonstration. In production, use a reliable provider.
        self.api_url = "https://api.exchangerate-api.com/v4/latest/USD"

    async def get_conversion_rate(self, from_currency: str, to_currency: str = "TRY") -> Optional[float]:
        """Fetch current conversion rate."""
        if not from_currency:
            return None

        normalized = from_currency.upper()
        if normalized in ("TL", "TRY"):
            normalized = "TRY"

        target = to_currency.upper()

        if normalized == target:
            return 1.0

        from_currency = normalized
        to_currency = target
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://api.exchangerate-api.com/v4/latest/{from_currency}")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("rates", {}).get(to_currency)
        except Exception as e:
            logger.error(f"Error fetching exchange rate: {e}")
        
        # Fallback rates if API is down
        fallbacks = {
            "USD": 30.25,
            "EUR": 33.10,
            "GBP": 38.50
        }
        return fallbacks.get(from_currency)

    async def convert_to_try(self, amount: float, currency: str) -> Dict[str, Any]:
        """Convert amount to TRY and return metadata."""
        if not amount:
            return {"amount_try": 0, "rate": 0}
            
        rate = await self.get_conversion_rate(currency, "TRY")
        if rate:
            return {
                "amount_try": round(amount * rate, 2),
                "rate": rate,
                "currency": "TRY"
            }
        return {"amount_try": amount, "rate": 1.0, "currency": currency}
