#!/usr/bin/env python3
"""
Enrich ArtCall opportunities by fetching full descriptions from their individual pages.
The scraper only gets data from the listing page, but each opportunity has a full page with rich content.
"""

import os
import json
import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import anthropic

load_dotenv()

class ArtCallFullEnricher:
    def __init__(self):
        """Initialize with Supabase and Anthropic."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(supabase_url, supabase_key)
        
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.anthropic = anthropic.Anthropic(api_key=anthropic_key)
    
    def fetch_artcall_page(self, url: str) -> Optional[Dict]:
        """Fetch the full content from an ArtCall opportunity page."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract the main content area
            content_data = {}
            
            # Try multiple selectors for the main content
            main_content = (
                soup.find('div', class_='container') or 
                soup.find('main') or 
                soup.find('div', id='content') or
                soup.find('article') or
                soup.body  # Fallback to entire body
            )
            
            if main_content:
                # Get ALL text content from the page
                all_text = main_content.get_text(separator='\n', strip=True)
                
                # Split into lines and filter
                lines = all_text.split('\n')
                meaningful_lines = []
                
                for line in lines:
                    line = line.strip()
                    # Keep lines that are meaningful (not just navigation, etc.)
                    if line and len(line) > 20 and not line.startswith('©'):
                        meaningful_lines.append(line)
                
                # Take a good chunk of content
                content_data['full_description'] = '\n'.join(meaningful_lines[:20])  # First 20 meaningful lines
                
                # Look for specific fields
                # Venue/Gallery
                venue_indicators = ['gallery', 'museum', 'center', 'studio', 'space']
                for elem in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'strong']):
                    text = elem.get_text(strip=True).lower()
                    if any(indicator in text for indicator in venue_indicators):
                        content_data['venue_hint'] = elem.get_text(strip=True)
                        break
                
                # Address
                address_pattern = main_content.find(text=lambda t: t and ('Street' in t or 'Avenue' in t or 'Road' in t or 'Boulevard' in t))
                if address_pattern:
                    content_data['address_hint'] = address_pattern.strip()
                
                # Eligibility details
                eligibility_section = main_content.find(text=lambda t: t and 'eligib' in t.lower())
                if eligibility_section:
                    # Get the parent element and its text
                    parent = eligibility_section.parent
                    if parent:
                        content_data['eligibility_details'] = parent.get_text(strip=True)[:500]
                
                # Awards/Prizes
                awards_section = main_content.find(text=lambda t: t and ('award' in t.lower() or 'prize' in t.lower()))
                if awards_section:
                    parent = awards_section.parent
                    if parent:
                        content_data['awards_info'] = parent.get_text(strip=True)[:300]
            
            return content_data
            
        except Exception as e:
            print(f"    ❌ Error fetching {url}: {e}")
            return None
    
    def enrich_with_full_content(self, opp: Dict, page_content: Dict) -> Dict:
        """Use Haiku to extract structured data from the full page content."""
        
        title = opp.get('title', '')
        organization = opp.get('organization', '')
        location_raw = opp.get('location_raw', '')
        url = opp.get('url', '')
        deadline = opp.get('deadline_raw', '')
        fee = opp.get('fee_raw', '')
        
        # Full description from the page
        full_description = page_content.get('full_description', '')
        venue_hint = page_content.get('venue_hint', '')
        address_hint = page_content.get('address_hint', '')
        eligibility = page_content.get('eligibility_details', '')
        awards = page_content.get('awards_info', '')
        
        prompt = f"""Analyze this art opportunity and provide comprehensive information.

Title: {title}
Organization: {organization}
URL: {url}
Current Location: {location_raw}
Deadline: {deadline}
Fee: {fee}

FULL DESCRIPTION FROM WEBPAGE:
{full_description}

Additional hints:
- Venue/Gallery: {venue_hint}
- Address: {address_hint}
- Eligibility: {eligibility}
- Awards: {awards}

Extract and provide:
1. Complete location information (venue, address, city, state)
2. A comprehensive 3-sentence summary for artists
3. Keywords and opportunity classification

Return JSON:
{{
    "location": {{
        "venue": "specific venue/gallery name",
        "address": "street address if found",
        "city": "city name",
        "state": "2-letter state code",
        "country": "country if not USA",
        "is_online": true/false
    }},
    "summary": "A 3-sentence summary that covers: (1) What this opportunity is and who it's for, including the hosting organization. (2) Key eligibility requirements, medium restrictions, or selection criteria. (3) Deadline, fee structure, and any awards, prizes, or unique benefits.",
    "description": "A longer 2-3 paragraph description with all important details from the webpage",
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "opportunity_type": "exhibition|fair|residency|grant|competition|market|online",
    "eligibility_summary": "Brief eligibility requirements",
    "awards_prizes": "Any awards or prizes mentioned",
    "confidence": "high|medium|low"
}}"""

        try:
            response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1200,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            
            # Parse JSON
            if '{' in content:
                content = content[content.index('{'):]
                # Find matching closing brace
                brace_count = 0
                for i, char in enumerate(content):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            content = content[:i+1]
                            break
            
            return json.loads(content)
            
        except Exception as e:
            print(f"    ❌ Enrichment error: {e}")
            return None
    
    def process_artcall_opportunities(self, limit: int = 10):
        """Process ArtCall opportunities with full page content."""
        
        print("🎨 ArtCall Full Content Enrichment")
        print("="*60)
        
        # Get ArtCall opportunities from database
        response = self.supabase.table('opportunities').select('*').eq(
            'source_platform', 'artcall'
        ).limit(limit).execute()
        
        if not response.data:
            print("No ArtCall opportunities found")
            return
        
        opportunities = response.data
        print(f"Found {len(opportunities)} ArtCall opportunities to enrich\n")
        
        success_count = 0
        
        for i, opp in enumerate(opportunities, 1):
            title = opp.get('title', '')
            url = opp.get('url', '')
            
            print(f"[{i}/{len(opportunities)}] {title[:50]}...")
            print(f"  URL: {url}")
            
            # Step 1: Fetch the full page content
            print("  📄 Fetching full page content...")
            page_content = self.fetch_artcall_page(url)
            
            if not page_content or not page_content.get('full_description'):
                print("  ⚠️  Could not fetch page content")
                continue
            
            # Show what we found
            desc_preview = page_content['full_description'][:150] + '...'
            print(f"  ✅ Found description: {desc_preview}")
            
            # Step 2: Enrich with Haiku using the full content
            print("  🤖 Enriching with AI...")
            enriched = self.enrich_with_full_content(opp, page_content)
            
            if enriched:
                # Prepare update data
                update_data = {}
                
                # Update description with the longer version
                if enriched.get('description'):
                    update_data['description'] = enriched['description']
                    print(f"  ✅ Added full description ({len(enriched['description'])} chars)")
                
                # Update location
                location = enriched.get('location', {})
                if location.get('venue'):
                    print(f"  ✅ Venue: {location['venue']}")
                if location.get('city') and location.get('state'):
                    update_data['location_city'] = location['city']
                    update_data['location_state'] = location['state']
                    update_data['location_raw'] = f"{location['city']}, {location['state']}"
                    print(f"  ✅ Location: {location['city']}, {location['state']}")
                
                # Add the AI summary (store in a new field or append to description)
                if enriched.get('summary'):
                    # For now, prepend the summary to the description
                    summary = enriched['summary']
                    if 'description' in update_data:
                        update_data['description'] = summary + "\n\n" + update_data['description']
                    else:
                        update_data['description'] = summary
                    print(f"  ✅ Added AI summary")
                
                # Update database
                if update_data:
                    try:
                        self.supabase.table('opportunities').update(
                            update_data
                        ).eq('id', opp['id']).execute()
                        
                        success_count += 1
                        print(f"  ✅ Updated database successfully")
                    except Exception as e:
                        print(f"  ❌ Database error: {e}")
            else:
                print("  ⚠️  Could not enrich")
            
            print()
            time.sleep(1)  # Rate limiting
        
        print("="*60)
        print(f"✅ Successfully enriched {success_count}/{len(opportunities)} ArtCall opportunities")
        print("These now have:")
        print("  • Full descriptions from the actual opportunity pages")
        print("  • AI-generated summaries with eligibility and benefits")
        print("  • Better location extraction including venues")

def main():
    """Run ArtCall full enrichment."""
    enricher = ArtCallFullEnricher()
    enricher.process_artcall_opportunities(limit=5)  # Test with first 5

if __name__ == "__main__":
    main()