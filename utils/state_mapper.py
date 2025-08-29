"""
State code to name mapping utility.
Maps numeric state codes to full state names and abbreviations.
"""

# State mapping - appears to be alphabetical order
# Based on the pattern: Anchorage, 2 = Alaska (2nd alphabetically)
STATE_CODE_MAP = {
    '1': ('Alabama', 'AL'),
    '2': ('Alaska', 'AK'),
    '3': ('Arizona', 'AZ'),
    '4': ('Arkansas', 'AR'),
    '5': ('California', 'CA'),
    '6': ('Colorado', 'CO'),
    '7': ('Connecticut', 'CT'),
    '8': ('Delaware', 'DE'),
    '9': ('Florida', 'FL'),
    '10': ('Georgia', 'GA'),
    '11': ('Hawaii', 'HI'),
    '12': ('Idaho', 'ID'),
    '13': ('Illinois', 'IL'),
    '14': ('Indiana', 'IN'),
    '15': ('Iowa', 'IA'),
    '16': ('Kansas', 'KS'),
    '17': ('Kentucky', 'KY'),
    '18': ('Louisiana', 'LA'),
    '19': ('Louisiana', 'LA'),  # Appears to be duplicate
    '20': ('Maine', 'ME'),
    '21': ('Maryland', 'MD'),
    '22': ('Massachusetts', 'MA'),
    '23': ('Michigan', 'MI'),
    '24': ('Minnesota', 'MN'),
    '25': ('Mississippi', 'MS'),
    '26': ('Missouri', 'MO'),
    '27': ('Montana', 'MT'),
    '28': ('Nebraska', 'NE'),
    '29': ('Nevada', 'NV'),
    '30': ('New Hampshire', 'NH'),
    '31': ('New Jersey', 'NJ'),
    '32': ('New Mexico', 'NM'),
    '33': ('New York', 'NY'),
    '34': ('North Carolina', 'NC'),
    '35': ('North Dakota', 'ND'),
    '36': ('Ohio', 'OH'),
    '37': ('Oklahoma', 'OK'),
    '38': ('Oregon', 'OR'),
    '39': ('Pennsylvania', 'PA'),
    '40': ('Rhode Island', 'RI'),
    '41': ('South Carolina', 'SC'),
    '42': ('South Dakota', 'SD'),
    '43': ('Tennessee', 'TN'),
    '44': ('Texas', 'TX'),
    '45': ('Utah', 'UT'),
    '46': ('Vermont', 'VT'),
    '47': ('Virginia', 'VA'),
    '48': ('Washington', 'WA'),
    '49': ('West Virginia', 'WV'),
    '50': ('Wisconsin', 'WI'),
    '51': ('Wyoming', 'WY'),
    '52': ('International', 'INTL'),  # For international locations
}

def normalize_location(city: str, state_code: str, use_abbreviation: bool = True) -> str:
    """
    Normalize location string from city and state code.
    
    Args:
        city: City name
        state_code: Numeric state code or state name
        use_abbreviation: If True, use state abbreviation, else full name
        
    Returns:
        Formatted location string like "Tucson, AZ" or "Tucson, Arizona"
    """
    if not city and not state_code:
        return ""
    
    # Clean up inputs
    city = (city or "").strip()
    state_code = str(state_code).strip()
    
    # If state_code is numeric, map it
    if state_code.isdigit():
        state_info = STATE_CODE_MAP.get(state_code)
        if state_info:
            state = state_info[1] if use_abbreviation else state_info[0]
        else:
            state = state_code  # Keep original if not found
    else:
        # Already a state name or abbreviation
        state = state_code
    
    # Format location
    if city and state:
        return f"{city}, {state}"
    elif city:
        return city
    elif state:
        return state
    else:
        return ""

def fix_location_in_opportunity(opp: dict) -> dict:
    """
    Fix location field in an opportunity dict.
    
    Args:
        opp: Opportunity dictionary
        
    Returns:
        Updated opportunity with normalized location
    """
    location = opp.get('location', '')
    
    # Try to parse existing location format "City, StateCode"
    if ',' in location:
        parts = location.split(',', 1)
        if len(parts) == 2:
            city = parts[0].strip()
            state = parts[1].strip()
            
            # Normalize the location
            normalized = normalize_location(city, state)
            if normalized != location:
                opp['location'] = normalized
                opp['location_normalized'] = True
    
    return opp

def batch_fix_locations(opportunities: list) -> list:
    """
    Fix locations for a batch of opportunities.
    
    Args:
        opportunities: List of opportunity dictionaries
        
    Returns:
        Updated list with normalized locations
    """
    fixed_count = 0
    for opp in opportunities:
        original_location = opp.get('location', '')
        fix_location_in_opportunity(opp)
        if opp.get('location', '') != original_location:
            fixed_count += 1
    
    print(f"Fixed {fixed_count} location entries")
    return opportunities