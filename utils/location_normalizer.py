"""
Comprehensive location normalization for all platforms.
Handles various formats and cleans up messy data.
"""

import re
from .state_mapper import normalize_location as normalize_cafe_location

# Common state abbreviations and names
STATE_ABBREV = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
    'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
    'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY',
    # DC and territories
    'district of columbia': 'DC', 'washington dc': 'DC', 'washington d.c.': 'DC',
    'puerto rico': 'PR', 'virgin islands': 'VI', 'guam': 'GU',
    # Canadian provinces
    'ontario': 'ON', 'quebec': 'QC', 'british columbia': 'BC', 'alberta': 'AB',
    'manitoba': 'MB', 'saskatchewan': 'SK', 'nova scotia': 'NS',
    'new brunswick': 'NB', 'newfoundland': 'NL', 'prince edward island': 'PE'
}

def normalize_location(location: str, platform: str) -> str:
    """
    Normalize location based on platform-specific patterns.
    
    Args:
        location: Raw location string
        platform: Source platform name
        
    Returns:
        Normalized location string
    """
    if not location:
        return ""
    
    location = location.strip()
    
    # Handle online/virtual locations
    if any(word in location.lower() for word in ['online', 'virtual', 'zoom', 'digital']):
        return "Online"
    
    # Platform-specific handling
    if platform == 'cafe':
        # CaFE uses "City, StateCode" format with numeric codes
        if ',' in location:
            parts = location.split(',', 1)
            city = parts[0].strip()
            state_code = parts[1].strip()
            return normalize_cafe_location(city, state_code)
        return location
    
    elif platform == 'artcall':
        # ArtCall typically just has state names
        state_lower = location.lower().strip()
        if state_lower in STATE_ABBREV:
            return STATE_ABBREV[state_lower].upper()
        return location
    
    elif platform == 'showsubmit':
        # ShowSubmit has messy locations mixed with exhibition details
        # Try to extract actual location information
        location = clean_showsubmit_location(location)
        return location
    
    elif platform == 'artwork_archive':
        # ArtworkArchive has "City, State ZIP, Country" format
        location = clean_artwork_archive_location(location)
        return location
    
    elif platform == 'zapplication':
        # Zapplication often has no location
        return location if location else ""
    
    else:
        # Default handling
        return clean_generic_location(location)

def clean_showsubmit_location(location: str) -> str:
    """
    Extract actual location from ShowSubmit's messy location field.
    
    ShowSubmit often includes exhibition details in the location field.
    Try to extract just the city/state information.
    """
    # Common patterns to remove
    remove_patterns = [
        r'\(.*?\)',  # Remove parenthetical content
        r'Entry Fee.*',  # Remove entry fee info
        r'Eligibility.*',  # Remove eligibility info
        r'Deadline.*',  # Remove deadline info
        r'Exhibition.*',  # Remove exhibition details
        r'gallery opens.*',  # Remove gallery hours
        r'Artists can enter.*',  # Remove submission details
    ]
    
    cleaned = location
    for pattern in remove_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Look for address patterns
    # Try to find "City, State" or "Number Street City"
    address_match = re.search(r'(\d+\s+[\w\s]+(?:St|Street|Rd|Road|Ave|Avenue|Blvd|Boulevard|Dr|Drive))[,\s]+(\w+)', cleaned)
    if address_match:
        # Found an address, extract city
        city = address_match.group(2)
        # Try to find state after city
        state_match = re.search(rf'{city}[,\s]+([A-Z]{{2}}|\w+)', cleaned)
        if state_match:
            state = state_match.group(1)
            if len(state) == 2:  # Already abbreviated
                return f"{city}, {state}"
            elif state.lower() in STATE_ABBREV:
                return f"{city}, {STATE_ABBREV[state.lower()]}"
    
    # Try to find city/state pattern
    city_state_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+([A-Z]{2}|[A-Z][a-z]+)', cleaned)
    if city_state_match:
        city = city_state_match.group(1)
        state = city_state_match.group(2)
        if len(state) == 2:  # Already abbreviated
            return f"{city}, {state}"
        elif state.lower() in STATE_ABBREV:
            return f"{city}, {STATE_ABBREV[state.lower()]}"
    
    # If nothing found, return first 50 chars cleaned up
    cleaned = ' '.join(cleaned.split())[:50]
    return cleaned if len(cleaned) > 3 else ""

def clean_artwork_archive_location(location: str) -> str:
    """
    Clean ArtworkArchive location format.
    
    Typically: "City, State ZIP, United States" -> "City, State"
    """
    # Remove "United States" suffix
    location = re.sub(r',?\s*United States\s*$', '', location, flags=re.IGNORECASE)
    
    # Remove ZIP codes
    location = re.sub(r'\s+\d{5}(?:-\d{4})?', '', location)
    
    # Clean up extra commas and spaces
    location = re.sub(r',\s*,', ',', location)
    location = re.sub(r'\s+', ' ', location)
    location = location.strip(' ,')
    
    # Normalize state if it's spelled out
    if ',' in location:
        parts = location.rsplit(',', 1)
        if len(parts) == 2:
            city = parts[0].strip()
            state = parts[1].strip()
            
            # Convert full state name to abbreviation
            if state.lower() in STATE_ABBREV:
                state = STATE_ABBREV[state.lower()]
            
            return f"{city}, {state}"
    
    return location

def clean_generic_location(location: str) -> str:
    """
    Generic location cleaning for unknown platforms.
    """
    # Remove common noise
    location = re.sub(r'\(.*?\)', '', location)  # Remove parenthetical
    location = re.sub(r'\s+', ' ', location)  # Clean whitespace
    location = location.strip()
    
    # Try to format as "City, State"
    if ',' in location:
        parts = location.split(',')
        if len(parts) >= 2:
            city = parts[0].strip()
            state = parts[1].strip()
            
            # Convert state name to abbreviation if needed
            if state.lower() in STATE_ABBREV:
                state = STATE_ABBREV[state.lower()]
            
            return f"{city}, {state}"
    
    return location

def batch_normalize_locations(opportunities: list) -> list:
    """
    Normalize locations for a batch of opportunities.
    
    Args:
        opportunities: List of opportunity dictionaries
        
    Returns:
        Updated list with normalized locations
    """
    normalized_count = 0
    
    for opp in opportunities:
        original_location = opp.get('location', '')
        platform = opp.get('source_platform', '')
        
        if original_location:
            normalized = normalize_location(original_location, platform)
            if normalized != original_location:
                opp['location'] = normalized
                opp['location_normalized'] = True
                normalized_count += 1
    
    print(f"Normalized {normalized_count} location entries")
    return opportunities