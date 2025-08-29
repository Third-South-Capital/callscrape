"""
Fee normalization utility.
Standardizes fee formats across different platforms.
"""

import re

def normalize_fee(fee_str: str) -> str:
    """
    Normalize fee string to consistent format.
    
    Args:
        fee_str: Raw fee string from scraper
        
    Returns:
        Normalized fee string
        
    Examples:
        "15.00" -> "$15"
        "$20" -> "$20"
        "Free to Enter" -> "Free"
        "15.00 - 22.50" -> "$15-$22.50"
        "0.00" -> "Free"
    """
    if not fee_str:
        return ""
    
    fee_str = str(fee_str).strip()
    
    # Handle free entries
    if fee_str.lower() in ['free', 'free to enter', '0', '0.00', '$0', '$0.00']:
        return "Free"
    
    # Handle "No Fee" variants
    if 'no fee' in fee_str.lower():
        return "Free"
    
    # Handle ranges like "15.00 - 22.50"
    if ' - ' in fee_str or ' to ' in fee_str.lower():
        # Split on separator
        separator = ' - ' if ' - ' in fee_str else ' to '
        parts = fee_str.split(separator)
        if len(parts) == 2:
            # Normalize each part
            min_fee = normalize_single_fee(parts[0])
            max_fee = normalize_single_fee(parts[1])
            if min_fee and max_fee:
                return f"{min_fee}-{max_fee}"
    
    # Handle single fees
    return normalize_single_fee(fee_str)

def normalize_single_fee(fee_str: str) -> str:
    """
    Normalize a single fee value.
    
    Args:
        fee_str: Single fee string
        
    Returns:
        Normalized fee with $ prefix
    """
    if not fee_str:
        return ""
    
    fee_str = fee_str.strip()
    
    # Extract numeric value
    # Remove all non-numeric except decimal point
    numeric_str = re.sub(r'[^\d.]', '', fee_str)
    
    if not numeric_str:
        return fee_str  # Return original if no numeric value found
    
    try:
        # Convert to float
        fee_value = float(numeric_str)
        
        # Check if it's free
        if fee_value == 0:
            return "Free"
        
        # Format as currency
        if fee_value == int(fee_value):
            return f"${int(fee_value)}"
        else:
            # Keep decimal if not .00
            if fee_value * 100 == int(fee_value * 100):
                return f"${fee_value:.2f}".rstrip('0').rstrip('.')
            else:
                return f"${fee_value:.2f}"
    except ValueError:
        return fee_str  # Return original if can't parse

def batch_normalize_fees(opportunities: list) -> list:
    """
    Normalize fees for a batch of opportunities.
    
    Args:
        opportunities: List of opportunity dictionaries
        
    Returns:
        Updated list with normalized fees
    """
    normalized_count = 0
    
    for opp in opportunities:
        original_fee = opp.get('fee', '')
        if original_fee:
            normalized_fee = normalize_fee(original_fee)
            if normalized_fee != original_fee:
                opp['fee'] = normalized_fee
                opp['fee_normalized'] = True
                normalized_count += 1
    
    print(f"Normalized {normalized_count} fee entries")
    return opportunities

# Test the normalizer
if __name__ == "__main__":
    test_fees = [
        "15.00",
        "$20",
        "Free to Enter",
        "15.00 - 22.50",
        "0.00",
        "25.00",
        "$35",
        "No Fee",
        "10",
        "$45.50",
        "free"
    ]
    
    print("Fee normalization tests:")
    for fee in test_fees:
        normalized = normalize_fee(fee)
        print(f"  '{fee}' -> '{normalized}'")