import hmac
import hashlib
from typing import Dict, Any

class HeliusClient:
    def __init__(self, api_key: str = None, webhook_secret: str = None):
        self.api_key = api_key
        self.webhook_secret = webhook_secret

    def verify_webhook_signature(self, signature: str, payload: bytes) -> bool:
        """Verify the authenticity of a Helius webhook payload."""
        if not self.webhook_secret:
            return False  # fail-closed: no secret = no authenticated requests
            
        # Helius uses HMAC SHA256
        # Note: Depending on Helius setup, signature verification might differ.
        expected = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)

    def parse_transaction_event(self, data: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """Parse parsed transaction data from Helius."""
        events = []
        for tx in data:
            if tx.get("type") == "SWAP":
                events.append({
                    "type": "SWAP",
                    "signature": tx.get("signature"),
                    "fee": tx.get("fee"),
                    "status": "SUCCESS" if not tx.get("transactionError") else "FAILED",
                    "nativeTransfers": tx.get("nativeTransfers", []),
                    "tokenTransfers": tx.get("tokenTransfers", [])
                })
        return events
