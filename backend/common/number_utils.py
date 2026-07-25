"""
Utility functions for formatting numbers in Xiaolee responses
"""

from decimal import Decimal
from typing import Union

def format_amount(amount: Union[str, int, float, Decimal], token: str = "") -> str:
    """
    Format amount to appropriate decimal places based on value and token type.
    
    Rules:
    - For very small amounts (< 0.01): Show up to 8 significant digits
    - For normal amounts: Show 2 decimal places
    - Remove trailing zeros
    """
    
    # Convert to Decimal for precise handling
    if isinstance(amount, str):
        amount = Decimal(amount)
    elif isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    
    # Handle zero
    if amount == 0:
        return "0"
    
    # Handle very small amounts (less than 0.01)
    if abs(amount) < Decimal('0.01'):
        # For very small amounts, show up to 8 significant digits
        # Convert to string and find significant digits
        amount_str = f"{amount:.12f}".rstrip('0').rstrip('.')
        
        # Count significant digits after decimal point
        if '.' in amount_str:
            decimal_part = amount_str.split('.')[1]
            # Find first non-zero digit
            first_non_zero = 0
            for i, digit in enumerate(decimal_part):
                if digit != '0':
                    first_non_zero = i
                    break
            
            # Show at least 2 significant digits after first non-zero
            min_decimals = first_non_zero + 2
            max_decimals = min(8, min_decimals)
            
            formatted = f"{amount:.{max_decimals}f}".rstrip('0').rstrip('.')
        else:
            formatted = amount_str
    else:
        # For normal amounts, show 2 decimal places and remove trailing zeros
        formatted = f"{amount:.2f}".rstrip('0').rstrip('.')
    
    return formatted

def format_transfer_amount(transfer_data: dict) -> str:
    """
    Format a transfer amount with token symbol.
    
    Args:
        transfer_data: Dict with 'amount' and 'token' keys
    
    Returns:
        Formatted string like "0.05 ETH" or "1,234.56 USDC"
    """
    amount = transfer_data.get('amount', 0)
    token = transfer_data.get('token', '')
    
    formatted_amount = format_amount(amount, token)
    
    # Add commas for large amounts
    if '.' in formatted_amount:
        integer_part, decimal_part = formatted_amount.split('.')
        if len(integer_part) > 3:
            # Add commas to integer part
            integer_with_commas = f"{int(integer_part):,}"
            formatted_amount = f"{integer_with_commas}.{decimal_part}"
    else:
        # No decimal part
        if len(formatted_amount) > 3:
            formatted_amount = f"{int(formatted_amount):,}"
    
    return f"{formatted_amount} {token}".strip()

# Test cases for verification
if __name__ == "__main__":
    test_cases = [
        (0.00000001, "BTC"),
        (0.000123, "ETH"),
        (0.05, "ETH"),
        (10.00, "USD"),
        (1234.567, "USDC"),
        (0, "STIP"),
        (50.0, "STIP"),
        ("15.25000000", "USDC")
    ]
    
    print("Testing number formatting:")
    for amount, token in test_cases:
        formatted = format_transfer_amount({"amount": amount, "token": token})
        print(f"{amount} {token} -> {formatted}")
