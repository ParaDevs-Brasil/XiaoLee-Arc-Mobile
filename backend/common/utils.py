def normalize_token_symbol(symbol: str) -> str:
    """Normalize token symbol by removing common prefixes/suffixes and converting to uppercase."""
    if not symbol:
        return ""
    
    # Convert to uppercase and strip whitespace
    normalized = symbol.upper().strip()
    
    # Remove common numeric prefixes (like "1WIP" -> "WIP")
    import re
    normalized = re.sub(r'^[0-9]+\.?[0-9]*', '', normalized)
    
    # Remove common prefixes and suffixes
    prefixes_to_remove = ['$', '@', '#']
    suffixes_to_remove = ['.E', '-E']
    
    for prefix in prefixes_to_remove:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    
    for suffix in suffixes_to_remove:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    
    # Handle special cases
    token_mappings = {
        'USDCE': 'USDC',
        'USDC.E': 'USDC',
        'WETH': 'WETH',  # If you want to treat WETH as ETH
    }
    
    if normalized in token_mappings:
        normalized = token_mappings[normalized]
    
    return normalized