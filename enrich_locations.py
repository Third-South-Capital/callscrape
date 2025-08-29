#!/usr/bin/env python3
"""
Enrich location data using Claude Haiku by extracting proper locations from descriptions.
Focuses on opportunities where location data is clearly wrong (e.g., "email" as location).
"""

import os
import json
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import anthropic

load_dotenv()

class LocationEnricher:
    def __init__(self):
        """Initialize enricher with Supabase and Anthropic clients."""
        # Supabase setup
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(supabase_url, supabase_key)
        
        # Anthropic setup
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_key:
            raise ValueError("Please set ANTHROPIC_API_KEY in .env file")
        self.anthropic = anthropic.Anthropic(api_key=anthropic_key)
        
    def get_problematic_opportunities(self, platform_filter: str = None) -> List[Dict]:
        """Get opportunities with clearly wrong location data."""
        print("🔍 Finding opportunities with problematic locations...")
        
        # Get opportunities, optionally filtered by platform
        if platform_filter:
            response = self.supabase.table('opportunities').select('*').eq(
                'source_platform', platform_filter
            ).execute()
        else:
            response = self.supabase.table('opportunities').select('*').execute()
        opportunities = response.data
        
        problematic = []
        
        for opp in opportunities:
            location = opp.get('location_raw') or ''
            location = location.lower()
            description = opp.get('description', '')
            
            # Identify clearly wrong locations
            is_problematic = any([
                location in ['email', 'email:', 'online', '', 'n/a', 'na', 'unknown'],
                location.startswith('http'),
                location.startswith('www'),
                '@' in location,
                len(location) < 3,
            ])
            
            # For ShowSubmit, "Email" is the main issue (case-insensitive)
            if opp.get('source_platform') == 'showsubmit' and 'email' in location:
                is_problematic = True
            
            if is_problematic:
                # For ShowSubmit with Email location, always process (we'll get description separately)
                if opp.get('source_platform') == 'showsubmit' and location == 'email':
                    problematic.append(opp)
                # For others, only process if description likely contains location info
                elif description and len(description) > 50:
                    problematic.append(opp)
        
        print(f"📊 Found {len(problematic)} opportunities with problematic locations")
        
        # Group by source
        by_source = {}
        for opp in problematic:
            source = opp.get('source_platform', 'unknown')
            by_source[source] = by_source.get(source, 0) + 1
        
        print("By source platform:")
        for source, count in by_source.items():
            print(f"  - {source}: {count}")
        
        return problematic
    
    def extract_location_with_haiku(self, title: str, description: str, location_raw: str, organization: str = None, url: str = None) -> Optional[Dict]:
        """Use Claude Haiku to extract proper location from description."""
        
        # Extract clues from URL (e.g., njws = New Jersey Watercolor Society)
        url_hints = ""
        if url and 'showsubmit.com' in url:
            # Extract the slug which often contains location hints
            parts = url.split('/')[-1].split('-')
            if parts:
                url_hints = f"URL hints: {' '.join(parts[:3])}"
        
        # For ShowSubmit with no description, use organization name which often contains location
        if not description or len(description) < 50:
            description = f"Organization: {organization}" if organization else "No description available"
        
        prompt = f"""Extract the physical location from this art opportunity information.

Title: {title}
Organization: {organization or 'Unknown'}
Current Location Field: {location_raw}
{url_hints}
Description or Context: {description}

Look for:
- Street addresses (e.g., "620 Broad St.")
- City names and states (e.g., "Shrewsbury, NJ")
- Venue names (e.g., "Guild of Creative Art")
- Delivery/shipping locations
- Exhibition venues

Return a JSON object with these fields (use null if not found):
{{
    "venue": "venue or organization name",
    "address": "street address if mentioned",
    "city": "city name",
    "state": "state abbreviation (2 letters)",
    "country": "country if not USA",
    "is_online": true/false,
    "confidence": "high/medium/low"
}}

If location is genuinely online/virtual, set is_online=true.
If no location found, return null.
Only return the JSON, no other text."""

        try:
            response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            content = response.content[0].text.strip()
            
            # Handle null response
            if content.lower() == 'null':
                return None
                
            # Clean up response if needed
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            location_data = json.loads(content)
            
            # Validate response
            if location_data and location_data.get('confidence') in ['high', 'medium']:
                return location_data
            
            return None
            
        except Exception as e:
            print(f"  ❌ Error extracting location: {e}")
            return None
    
    def update_opportunity_location(self, opp_id: str, location_data: Dict) -> bool:
        """Update opportunity with enriched location data."""
        
        # Build location string
        location_parts = []
        
        if location_data.get('is_online'):
            location_raw = "Online"
            location_city = None
            location_state = None
        else:
            if location_data.get('city'):
                location_parts.append(location_data['city'])
            if location_data.get('state'):
                location_parts.append(location_data['state'])
            
            location_raw = ', '.join(location_parts) if location_parts else None
            location_city = location_data.get('city')
            location_state = location_data.get('state')
        
        if not location_raw:
            return False
        
        # Update in database
        try:
            update_data = {
                'location_raw': location_raw,
                'location_city': location_city,
                'location_state': location_state
            }
            
            if location_data.get('country') and location_data['country'] != 'USA':
                update_data['location_country'] = location_data['country']
            
            response = self.supabase.table('opportunities').update(
                update_data
            ).eq('id', opp_id).execute()
            
            return bool(response.data)
            
        except Exception as e:
            print(f"  ❌ Error updating database: {e}")
            return False
    
    def enrich_locations(self, limit: int = 50, platform: str = None):
        """Enrich location data for problematic opportunities."""
        
        # Get problematic opportunities
        opportunities = self.get_problematic_opportunities(platform_filter=platform)
        
        if not opportunities:
            print("✅ No problematic locations found!")
            return
        
        # Limit for testing
        if limit:
            opportunities = opportunities[:limit]
            print(f"\n🎯 Processing first {limit} opportunities (testing mode)")
        
        print("\n" + "="*60)
        print("Starting enrichment with Claude Haiku...")
        print("="*60)
        
        enriched_count = 0
        failed_count = 0
        
        for i, opp in enumerate(opportunities, 1):
            title = opp.get('title', '')
            description = opp.get('description', '')
            location_raw = opp.get('location_raw', '')
            
            print(f"\n[{i}/{len(opportunities)}] {title[:60]}...")
            print(f"  Current location: '{location_raw}'")
            
            # Extract location with Haiku
            organization = opp.get('organization', '')
            url = opp.get('url', '')
            location_data = self.extract_location_with_haiku(title, description, location_raw, organization, url)
            
            if location_data:
                # Build readable location
                if location_data.get('is_online'):
                    new_location = "Online"
                else:
                    parts = []
                    if location_data.get('city'):
                        parts.append(location_data['city'])
                    if location_data.get('state'):
                        parts.append(location_data['state'])
                    new_location = ', '.join(parts) if parts else "Unknown"
                
                print(f"  ✅ Extracted: {new_location} (confidence: {location_data.get('confidence')})")
                
                # Update database
                if self.update_opportunity_location(opp['id'], location_data):
                    print(f"  ✅ Updated in database")
                    enriched_count += 1
                else:
                    print(f"  ❌ Failed to update database")
                    failed_count += 1
            else:
                print(f"  ⚠️  Could not extract location")
                failed_count += 1
            
            # Rate limiting for API
            time.sleep(0.5)
        
        # Summary
        print("\n" + "="*60)
        print("📊 ENRICHMENT SUMMARY")
        print("="*60)
        print(f"✅ Successfully enriched: {enriched_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📈 Success rate: {enriched_count/(enriched_count+failed_count)*100:.1f}%")

def main():
    """Main function."""
    enricher = LocationEnricher()
    
    # Process all ShowSubmit opportunities with Email location issue
    print("🎯 Processing ALL ShowSubmit opportunities with 'Email' location issue\n")
    enricher.enrich_locations(limit=None, platform='showsubmit')
    
    # To process all ShowSubmit: enricher.enrich_locations(limit=None, platform='showsubmit')
    # To process all platforms: enricher.enrich_locations(limit=None)

if __name__ == "__main__":
    main()