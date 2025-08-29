#!/usr/bin/env python3
"""
Enrich Zapplication opportunities with AI-generated descriptions.
Zapplication pages don't have good descriptions, so we generate them from the metadata.
"""

import os
import json
import time
from typing import Dict, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import anthropic

load_dotenv()

class ZapplicationEnricher:
    def __init__(self):
        """Initialize with Supabase and Anthropic."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(supabase_url, supabase_key)
        
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.anthropic = anthropic.Anthropic(api_key=anthropic_key)
    
    def generate_description(self, opp: Dict) -> Optional[str]:
        """Generate a 3-sentence description for a Zapplication opportunity."""
        
        title = opp.get('title', '')
        organization = opp.get('organization', '')
        location = opp.get('location_raw', '')
        deadline = opp.get('deadline_raw', '')
        fee = opp.get('fee_raw', '')
        url = opp.get('url', '')
        
        # Extract event dates and other info from extras
        extras = opp.get('extras', {})
        if isinstance(extras, str):
            try:
                extras = json.loads(extras)
            except:
                extras = {}
        
        event_dates = extras.get('event_dates', '')
        app_fee = extras.get('application_fee', '')
        booth_fee = extras.get('booth_fee', '')
        
        prompt = f"""Create a compelling 3-sentence description for this art fair/festival opportunity.

Event Details:
- Title: {title}
- Organization: {organization}
- Location: {location}
- Event Dates: {event_dates}
- Application Deadline: {deadline}
- Application Fee: {app_fee or fee or 'Not specified'}
- Booth Fee: {booth_fee or 'Not specified'}
- URL: {url}

Write exactly 3 sentences that:
1. Introduce the event and its significance/appeal to artists
2. Mention the location, dates, and type of art/vendors accepted
3. Include application deadline and fees

Make it informative and actionable for artists deciding whether to apply. Focus on facts, not speculation."""

        try:
            response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            description = response.content[0].text.strip()
            
            # Ensure it's not too long
            if len(description) > 500:
                # Take first 3 sentences
                sentences = description.split('. ')
                description = '. '.join(sentences[:3]) + '.'
            
            return description
            
        except Exception as e:
            print(f"    ❌ Error generating description: {e}")
            return None
    
    def enrich_zapplication_opportunities(self, limit: int = 20):
        """Enrich Zapplication opportunities with AI descriptions."""
        
        print("🎨 Zapplication AI Enrichment")
        print("="*60)
        
        # Get Zapplication opportunities without descriptions
        response = self.supabase.table('opportunities').select('*').eq(
            'source_platform', 'zapplication'
        ).eq('description', '').limit(limit).execute()
        
        if not response.data:
            print("No Zapplication opportunities need enrichment")
            return
        
        opportunities = response.data
        print(f"Found {len(opportunities)} Zapplication opportunities to enrich\n")
        
        success_count = 0
        
        for i, opp in enumerate(opportunities, 1):
            title = opp.get('title', '')
            
            print(f"[{i}/{len(opportunities)}] {title[:50]}...")
            print(f"  Location: {opp.get('location_raw', 'Unknown')}")
            print(f"  Deadline: {opp.get('deadline_raw', 'Unknown')}")
            
            # Generate AI description
            print("  🤖 Generating description...")
            description = self.generate_description(opp)
            
            if description:
                # Update database
                try:
                    self.supabase.table('opportunities').update({
                        'description': description
                    }).eq('id', opp['id']).execute()
                    
                    success_count += 1
                    print(f"  ✅ Added description: \"{description[:100]}...\"")
                except Exception as e:
                    print(f"  ❌ Database error: {e}")
            else:
                print("  ⚠️  Could not generate description")
            
            print()
            time.sleep(0.5)  # Rate limiting
        
        print("="*60)
        print(f"✅ Successfully enriched {success_count}/{len(opportunities)} Zapplication opportunities")
        print("\nExample enriched opportunities:")
        
        # Show a few examples
        enriched = self.supabase.table('opportunities').select('title, description').eq(
            'source_platform', 'zapplication'
        ).neq('description', '').limit(3).execute()
        
        if enriched.data:
            for ex in enriched.data:
                print(f"\n• {ex['title'][:50]}...")
                print(f"  {ex['description'][:150]}...")

def main():
    """Run Zapplication enrichment."""
    enricher = ZapplicationEnricher()
    enricher.enrich_zapplication_opportunities(limit=10)  # Start with 10

if __name__ == "__main__":
    main()