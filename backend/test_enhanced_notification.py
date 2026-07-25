#!/usr/bin/env python3
"""Test the enhanced auto-claim notifications with sender and date information."""

from datetime import datetime

def test_dm_notification_format():
    """Test the DM notification format with sender and date info."""
    
    # Mock claimed_transfers data with timestamp
    claimed_transfers = [
        {
            "token": "STIP", 
            "amount": 20.0, 
            "from_handle": "vyxozcrypto",
            "claimed_at": datetime.now().isoformat()
        }
    ]
    
    print("🧪 TESTING ENHANCED DM NOTIFICATION FORMAT")
    print("=" * 60)
    
    # Simulate the enhanced notification logic
    transfer_details = []
    total_tokens = {}
    
    for transfer in claimed_transfers:
        token = transfer["token"]
        amount = transfer["amount"]
        sender = transfer.get("from_handle", "unknown")
        claimed_at = transfer.get("claimed_at")
        
        # Format transfer detail (with date if available)
        if claimed_at:
            # Parse and format the date nicely
            try:
                dt = datetime.fromisoformat(claimed_at.replace('Z', '+00:00'))
                date_str = dt.strftime("%m/%d %H:%M")
                detail = f"{amount} {token} from @{sender} (on {date_str})"
            except:
                detail = f"{amount} {token} from @{sender}"
        else:
            detail = f"{amount} {token} from @{sender}"
        
        transfer_details.append(detail)
        
        # Add to totals
        if token in total_tokens:
            total_tokens[token] += amount
        else:
            total_tokens[token] = amount
    
    # Create notification text
    detailed_list = ", ".join(transfer_details)
    
    if len(claimed_transfers) == 1:
        # Single transfer - use detailed format
        notification_text = f"🎉 Welcome! I automatically claimed 1 pending transfer for you: {detailed_list}! Your wallet is ready to use."
    else:
        # Multiple transfers - show count and details
        token_summary = []
        for token, amount in total_tokens.items():
            token_summary.append(f"{amount} {token}")
        summary_text = ", ".join(token_summary)
        notification_text = f"🎉 Welcome! I automatically claimed {len(claimed_transfers)} pending transfers for you: {summary_text} (Details: {detailed_list})! Your wallet is ready to use."
    
    print("ENHANCED NOTIFICATION:")
    print(notification_text)
    print("\n" + "=" * 60)
    
    # Compare with old format
    old_format = f"🎉 Welcome! I automatically claimed 1 pending transfer for you: 20.0 STIP! Your wallet is ready to use."
    print("OLD FORMAT (for comparison):")
    print(old_format)
    print("\n" + "=" * 60)
    
    print("✅ Enhancement complete! New format includes sender and timestamp info.")

if __name__ == "__main__":
    test_dm_notification_format()
