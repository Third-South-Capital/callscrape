"""
Enhanced location enrichment with transparency and standardization.

Key principles:
1. Be transparent when location is not specified
2. Standardize to "City, State" format where possible  
3. Handle online/virtual events clearly
4. Extract location from descriptions when missing
5. Handle international locations properly
"""

import re
from typing import Optional, Dict, Tuple
from .location_normalizer import STATE_ABBREV
from .state_mapper import STATE_CODE_MAP

# Extended country list for international recognition
COUNTRIES = {
    'united states', 'usa', 'canada', 'united kingdom', 'uk', 'australia',
    'germany', 'france', 'italy', 'spain', 'netherlands', 'belgium',
    'japan', 'china', 'india', 'mexico', 'brazil', 'argentina',
    'south africa', 'egypt', 'israel', 'dubai', 'singapore', 'korea',
    'sweden', 'norway', 'denmark', 'finland', 'switzerland', 'austria',
    'portugal', 'greece', 'turkey', 'russia', 'poland', 'czech republic',
    'new zealand', 'ireland', 'scotland', 'wales'
}

# Canadian provinces and territories
CANADIAN_PROVINCES = {
    'ontario': 'ON', 'quebec': 'QC', 'british columbia': 'BC', 'alberta': 'AB',
    'manitoba': 'MB', 'saskatchewan': 'SK', 'nova scotia': 'NS',
    'new brunswick': 'NB', 'newfoundland': 'NL', 'prince edward island': 'PE',
    'northwest territories': 'NT', 'yukon': 'YT', 'nunavut': 'NU'
}

# Common venue indicators
VENUE_KEYWORDS = [
    'gallery', 'museum', 'center', 'centre', 'studio', 'space',
    'institute', 'foundation', 'society', 'college', 'university',
    'library', 'theater', 'theatre', 'pavilion', 'hall', 'school'
]

# Location extraction patterns
LOCATION_PATTERNS = [
    # "located/held in City, State" patterns
    r'(?:located|based|situated|held)\s+(?:in|at)\s+(?:the\s+)?(?:[\w\s]+?(?:Gallery|Museum|Center|Institute|Foundation|Studio|Space)\s+)?(?:in\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+([A-Z]{2})\b',
    # "City, State residents" patterns
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+([A-Z]{2})\s+(?:residents?|artists?|only)',
    # Address patterns with street names
    r'\d+\s+[\w\s]+(?:St|Street|Rd|Road|Ave|Avenue|Blvd|Boulevard|Dr|Drive)[,\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+([A-Z]{2})\b',
    # "Exhibition at/in [venue] in City, State" patterns
    r'(?:exhibition|show|display|event)\s+(?:at|in)\s+[\w\s]+\s+in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+([A-Z]{2})\b',
    # Simple "City, State" pattern at the end of sentences
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+([A-Z]{2})\b(?:[.\s]|$)',
]


def enrich_location(
    opportunity: Dict,
    extract_from_description: bool = True
) -> Dict:
    """
    Enrich location data for an opportunity with transparency.
    
    Args:
        opportunity: The opportunity dictionary
        extract_from_description: Whether to try extracting from description
        
    Returns:
        Updated opportunity with enriched location data
    """
    # Get existing location
    current_location = opportunity.get('location', '').strip()
    original_location = current_location
    
    # Initialize location metadata
    location_meta = {
        'original': original_location,
        'enriched': None,
        'confidence': 'high',  # high, medium, low, not_specified
        'type': None,  # physical, online, hybrid, not_specified
        'extraction_source': None  # field, description, inferred
    }
    
    # Step 1: Check if location exists and is meaningful
    if current_location:
        # Check for online/virtual
        if is_online_location(current_location):
            location_meta['enriched'] = 'Online'
            location_meta['type'] = 'online'
            location_meta['extraction_source'] = 'field'
        else:
            # Try to standardize existing location
            standardized = standardize_location(current_location)
            if standardized and standardized != 'Not Specified':
                location_meta['enriched'] = standardized
                location_meta['type'] = 'physical'
                location_meta['extraction_source'] = 'field'
            else:
                location_meta['confidence'] = 'low'
    
    # Step 2: If no good location, try extracting from description
    if (not location_meta['enriched'] or location_meta['confidence'] == 'low') and extract_from_description:
        description = opportunity.get('description', '')
        if description:
            extracted = extract_location_from_text(description)
            if extracted:
                location_meta['enriched'] = extracted['location']
                location_meta['confidence'] = extracted['confidence']
                location_meta['type'] = extracted['type']
                location_meta['extraction_source'] = 'description'
    
    # Step 3: Check organization field as fallback
    if not location_meta['enriched']:
        org = opportunity.get('organization', '')
        if org:
            # Some organizations include location in their name
            org_location = extract_location_from_org(org)
            if org_location:
                location_meta['enriched'] = org_location
                location_meta['confidence'] = 'medium'
                location_meta['type'] = 'physical'
                location_meta['extraction_source'] = 'inferred'
    
    # Step 4: Final fallback
    if not location_meta['enriched']:
        location_meta['enriched'] = 'Not Specified'
        location_meta['confidence'] = 'not_specified'
        location_meta['type'] = 'not_specified'
        location_meta['extraction_source'] = None
    
    # Update opportunity
    opportunity['location'] = location_meta['enriched']
    
    # Store metadata in extras
    if 'extras' not in opportunity:
        opportunity['extras'] = {}
    opportunity['extras']['location_metadata'] = location_meta
    
    return opportunity


def is_online_location(location: str) -> bool:
    """Check if location indicates online/virtual event."""
    online_keywords = [
        'online', 'virtual', 'zoom', 'digital', 'remote',
        'internet', 'web-based', 'webinar', 'streaming'
    ]
    location_lower = location.lower()
    return any(keyword in location_lower for keyword in online_keywords)


def standardize_location(location: str) -> Optional[str]:
    """
    Standardize location to "City, State" format.
    Returns None if cannot standardize.
    """
    # Check for online/virtual first
    if is_online_location(location):
        return 'Online'
    
    # Remove noise
    location = re.sub(r'\(.*?\)', '', location)  # Remove parenthetical
    location = re.sub(r'\s+', ' ', location).strip()
    
    # Check for country (international)
    location_lower = location.lower()
    
    # Special handling for Canada - format as Province, Canada
    if 'canada' in location_lower:
        # Try to find province
        for province, abbrev in CANADIAN_PROVINCES.items():
            if province in location_lower or f', {abbrev}' in location or f' {abbrev} ' in location:
                # Check for city
                city_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+(?:' + province + '|' + abbrev + ')', location, re.IGNORECASE)
                if city_match:
                    city = city_match.group(1)
                    city = ' '.join(word.capitalize() for word in city.split())
                    return f"{city}, {abbrev}, Canada"
                else:
                    return f"{abbrev}, Canada"
        # Check for city without province
        city_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+Canada', location, re.IGNORECASE)
        if city_match:
            city = city_match.group(1)
            city = ' '.join(word.capitalize() for word in city.split())
            return f"{city}, Canada"
        # No city/province found, just return Canada
        return "Canada"
    
    # Handle UK special case
    if 'uk' in location_lower or 'united kingdom' in location_lower:
        city_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+(?:UK|United Kingdom)', location, re.IGNORECASE)
        if city_match:
            city = city_match.group(1)
            city = ' '.join(word.capitalize() for word in city.split())
            return f"{city}, United Kingdom"
        return "United Kingdom"
    
    # Check for other countries
    for country in COUNTRIES:
        if country in location_lower and country not in ['united states', 'usa', 'canada', 'uk', 'united kingdom']:
            # Extract city/province if possible
            city_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+' + re.escape(country), location, re.IGNORECASE)
            if city_match:
                city = city_match.group(1)
                # Proper case the city name
                city = ' '.join(word.capitalize() for word in city.split())
                return f"{city}, {country.title()}"
            return country.title()
    
    # Handle US/Canada locations
    if ',' in location:
        parts = location.split(',')
        if len(parts) >= 2:
            city = parts[0].strip()
            state = parts[1].strip()
            
            # Proper case the city name
            city = ' '.join(word.capitalize() for word in city.split())
            
            # Remove ZIP codes
            state = re.sub(r'\s*\d{5}(?:-\d{4})?\s*', '', state).strip()
            
            # Handle numeric state codes (for CAFE platform)
            if state.isdigit():
                state_info = STATE_CODE_MAP.get(state)
                if state_info:
                    state = state_info[1]  # Use state abbreviation
                    return f"{city}, {state}"
                else:
                    # Unknown numeric code, keep as-is
                    return f"{city}, {state}"
            
            # Convert state name to abbreviation
            if len(state) > 2 and state.lower() in STATE_ABBREV:
                state = STATE_ABBREV[state.lower()]
            elif len(state) == 2:
                state = state.upper()
            else:
                # Try to find state name in the string
                for state_name, abbrev in STATE_ABBREV.items():
                    if state_name in state.lower():
                        state = abbrev
                        break
            
            if city and len(state) == 2:
                return f"{city}, {state}"
            elif city and state:
                # Return as-is if we can't resolve state but both exist
                return f"{city}, {state}"
    
    # Handle addresses with street patterns
    address_match = re.search(r'\d+\s+[\w\s]+(?:St|Street|Rd|Road|Ave|Avenue|Blvd|Boulevard|Dr|Drive)[,\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+([A-Z]{2})', location, re.IGNORECASE)
    if address_match:
        city = address_match.group(1)
        state = address_match.group(2).upper()
        city = ' '.join(word.capitalize() for word in city.split())
        return f"{city}, {state}"
    
    # Single word might be just a state
    if ' ' not in location and len(location) > 2:
        if location.lower() in STATE_ABBREV:
            return STATE_ABBREV[location.lower()].upper()
    
    return None


def extract_location_from_text(text: str) -> Optional[Dict]:
    """
    Extract location from description text using patterns.
    Returns dict with location, confidence, and type.
    """
    # First check for online indicators
    if is_online_location(text[:500]):  # Check first 500 chars
        return {
            'location': 'Online',
            'confidence': 'high',
            'type': 'online'
        }
    
    # Try location patterns
    for pattern in LOCATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            city = match.group(1).strip()
            state = match.group(2).strip()
            
            # Validate and standardize
            if state.lower() in STATE_ABBREV:
                state = STATE_ABBREV[state.lower()]
            elif len(state) == 2:
                state = state.upper()
            else:
                continue  # Skip if can't resolve state
            
            return {
                'location': f"{city}, {state}",
                'confidence': 'medium',
                'type': 'physical'
            }
    
    # Look for venue + location combinations
    for keyword in VENUE_KEYWORDS:
        pattern = rf'{keyword}[^.]*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+([A-Z]{{2}})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            city = match.group(1).strip()
            state = match.group(2).upper()
            return {
                'location': f"{city}, {state}",
                'confidence': 'low',
                'type': 'physical'
            }
    
    return None


def extract_location_from_org(org: str) -> Optional[str]:
    """
    Try to extract location from organization name.
    Many orgs include city/state in their name.
    """
    # Patterns like "Gallery of Austin" or "New York Museum"
    patterns = [
        r'(?:of|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+([A-Z]{2})',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]+([A-Z]{2})\s+(?:' + '|'.join(VENUE_KEYWORDS) + ')',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, org, re.IGNORECASE)
        if match:
            city = match.group(1).strip()
            state = match.group(2).upper()
            if len(state) == 2:  # Valid state code
                return f"{city}, {state}"
    
    # Check if org name contains a known city
    # This would need a city database for accuracy
    # For now, return None
    return None


def batch_enrich_locations(opportunities: list) -> Tuple[list, Dict]:
    """
    Enrich locations for a batch of opportunities.
    
    Returns:
        Tuple of (enriched opportunities, statistics)
    """
    stats = {
        'total': len(opportunities),
        'enriched': 0,
        'not_specified': 0,
        'online': 0,
        'extracted_from_description': 0,
        'inferred': 0,
        'by_confidence': {'high': 0, 'medium': 0, 'low': 0, 'not_specified': 0}
    }
    
    for opp in opportunities:
        original = opp.get('location', '')
        enrich_location(opp)
        
        # Update stats
        if 'extras' in opp and 'location_metadata' in opp['extras']:
            meta = opp['extras']['location_metadata']
            
            if meta['enriched'] != original:
                stats['enriched'] += 1
            
            if meta['enriched'] == 'Not Specified':
                stats['not_specified'] += 1
            elif meta['enriched'] == 'Online':
                stats['online'] += 1
            
            if meta['extraction_source'] == 'description':
                stats['extracted_from_description'] += 1
            elif meta['extraction_source'] == 'inferred':
                stats['inferred'] += 1
            
            stats['by_confidence'][meta['confidence']] += 1
    
    return opportunities, stats


def format_location_display(opportunity: Dict) -> str:
    """
    Format location for display with confidence indicator.
    Used in GUI to show transparency about location data.
    """
    location = opportunity.get('location', '')
    
    if 'extras' in opportunity and 'location_metadata' in opportunity.get('extras', {}):
        meta = opportunity['extras']['location_metadata']
        
        if meta['confidence'] == 'not_specified':
            return "📍 Location Not Specified"
        elif meta['confidence'] == 'low':
            return f"📍 {location} (uncertain)"
        elif meta['extraction_source'] == 'description':
            return f"📍 {location} (from description)"
        elif meta['extraction_source'] == 'inferred':
            return f"📍 {location} (inferred)"
        else:
            return f"📍 {location}"
    
    return f"📍 {location}" if location else "📍 Location Not Specified"