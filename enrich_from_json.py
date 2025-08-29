#!/usr/bin/env python3
"""
Enrich locations using the original scraped JSON data which has more complete information.
This bypasses the database sync issues and uses the raw scraped data.
"""

import os
import json
import time
from typing import Dict, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import anthropic

load_dotenv()

class DirectEnricher:
    def __init__(self):
        """Initialize with Supabase and Anthropic."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(supabase_url, supabase_key)
        
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.anthropic = anthropic.Anthropic(api_key=anthropic_key)
    
    def extract_location_with_haiku(self, opp: Dict) -> Optional[Dict]:
        """Extract location using ALL available data from scraped JSON."""
        
        title = opp.get('title', '')
        organization = opp.get('organization', '')
        scraped_location = opp.get('location', '')  # The raw scraped location
        url = opp.get('url', '')
        description = opp.get('description', '')
        
        # Extract URL hints
        url_hints = ""
        if 'showsubmit.com' in url:
            parts = url.split('/')[-1].split('-')
            url_hints = f"URL slug: {'-'.join(parts[:4])}"
        
        prompt = f"""Extract the physical location from this art opportunity.

Title: {title}
Organization: {organization}
Scraped Location Field: {scraped_location}
URL: {url}
{url_hints}
Description: {description[:500] if description else 'None'}

The scraped location may be messy (e.g., "ExhibitionMiddletown Arts Center (MAC)36 Church StreetMiddletown").
Extract the venue name, street address, city, and state.

For "njws" in URL = New Jersey Watercolor Society = New Jersey location.

Return JSON:
{{
    "venue": "venue name",
    "address": "street address",
    "city": "city name",
    "state": "2-letter state code",
    "is_online": true/false,
    "confidence": "high/medium/low"
}}

Return null if no location found."""

        try:
            response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            
            # Debug: show what Haiku returned
            # print(f"    Haiku response: {content[:100]}...")
            
            if content.lower() == 'null' or 'null' in content.lower()[:20]:
                return None
            
            # Clean up response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1] if '```' in content else content
            
            # Remove any text before the JSON
            if '{' in content:
                content = content[content.index('{'):]
            
            # Remove any text after the JSON
            if content.count('}') > 0:
                # Find the last matching brace
                brace_count = 0
                for i, char in enumerate(content):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            content = content[:i+1]
                            break
            
            return json.loads(content.strip())
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return None
    
    def enrich_showsubmit(self):
        """Enrich ShowSubmit opportunities using scraped JSON data."""
        
        # Load the most recent scraped data
        json_files = sorted([f for f in os.listdir('data') if f.startswith('opportunities_')])
        if not json_files:
            print("No scraped data found")
            return
        
        latest_file = f"data/{json_files[-1]}"
        print(f"Loading {latest_file}")
        
        with open(latest_file) as f:
            data = json.load(f)
        
        # Get ALL ShowSubmit opportunities to enrich
        showsubmit_opps = [
            o for o in data 
            if o.get('source_platform') == 'showsubmit'
        ]
        
        print(f"Found {len(showsubmit_opps)} ShowSubmit opportunities to enrich\n")
        
        success_count = 0
        
        for i, opp in enumerate(showsubmit_opps[:10], 1):  # Test with first 10
            title = opp.get('title', '')
            scraped_location = opp.get('location', '')
            
            print(f"[{i}] {title[:50]}...")
            print(f"    Scraped location: '{scraped_location}'")
            
            location_data = self.extract_location_with_haiku(opp)
            
            if location_data and location_data.get('confidence') in ['high', 'medium']:
                parts = []
                if location_data.get('venue'):
                    print(f"    ✅ Venue: {location_data['venue']}")
                if location_data.get('city'):
                    parts.append(location_data['city'])
                if location_data.get('state'):
                    parts.append(location_data['state'])
                
                new_location = ', '.join(parts) if parts else 'Online'
                print(f"    ✅ Extracted: {new_location}")
                
                # Update in database
                if self.update_database(title, location_data):
                    success_count += 1
                    print(f"    ✅ Updated database")
            else:
                print(f"    ❌ Could not extract")
            
            print()
            time.sleep(0.5)  # Rate limiting
        
        print(f"\n✅ Successfully enriched {success_count}/{len(showsubmit_opps[:10])} opportunities")
    
    def update_database(self, title: str, location_data: Dict) -> bool:
        """Update opportunity in database."""
        try:
            # Find the opportunity by title
            response = self.supabase.table('opportunities').select('id').eq(
                'title', title
            ).eq('source_platform', 'showsubmit').execute()
            
            if not response.data:
                return False
            
            opp_id = response.data[0]['id']
            
            # Build update data
            update_data = {}
            
            if location_data.get('is_online'):
                update_data['location_raw'] = 'Online'
            else:
                parts = []
                if location_data.get('city'):
                    parts.append(location_data['city'])
                if location_data.get('state'):
                    parts.append(location_data['state'])
                
                if parts:
                    update_data['location_raw'] = ', '.join(parts)
                    update_data['location_city'] = location_data.get('city')
                    update_data['location_state'] = location_data.get('state')
            
            # Update
            self.supabase.table('opportunities').update(
                update_data
            ).eq('id', opp_id).execute()
            
            return True
            
        except Exception as e:
            print(f"      Database error: {e}")
            return False

def main():
    enricher = DirectEnricher()
    enricher.enrich_showsubmit()

if __name__ == "__main__":
    main()