#!/usr/bin/env python3
"""
Smart enrichment that:
1. Only enriches locations that haven't been enriched yet
2. Tracks when deadlines or other important fields change
3. Maintains an enrichment log to avoid re-processing
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import anthropic

load_dotenv()

class SmartEnricher:
    def __init__(self):
        """Initialize with Supabase and Anthropic."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(supabase_url, supabase_key)
        
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.anthropic = anthropic.Anthropic(api_key=anthropic_key)
        
        # Track enrichment history
        self.enrichment_log_file = 'data/enrichment_log.json'
        self.enrichment_log = self.load_enrichment_log()
    
    def load_enrichment_log(self) -> Dict:
        """Load the enrichment history."""
        if os.path.exists(self.enrichment_log_file):
            with open(self.enrichment_log_file) as f:
                return json.load(f)
        return {
            'enriched_ids': {},  # {opportunity_id: enrichment_date}
            'deadline_changes': [],  # Track deadline changes
            'last_run': None
        }
    
    def save_enrichment_log(self):
        """Save the enrichment history."""
        os.makedirs('data', exist_ok=True)
        with open(self.enrichment_log_file, 'w') as f:
            json.dump(self.enrichment_log, f, indent=2)
    
    def needs_enrichment(self, opp: Dict) -> bool:
        """Check if an opportunity needs location enrichment."""
        
        # Generate a unique ID for this opportunity
        opp_id = f"{opp.get('source_platform')}:{opp.get('title')}"
        
        # Already enriched?
        if opp_id in self.enrichment_log['enriched_ids']:
            return False
        
        # Check if location needs enrichment
        location = opp.get('location_raw') or ''
        location = location.lower()
        
        # These indicate bad/missing location data
        bad_location_indicators = [
            'email', 'email:', 'online', '', 'n/a', 'na', 'unknown'
        ]
        
        # Has bad location?
        if any(indicator in location for indicator in bad_location_indicators):
            return True
        
        # Has no city/state parsed?
        if not opp.get('location_city') and not opp.get('location_state'):
            # But has some location text that might be parseable
            if opp.get('location_raw'):
                return True
        
        return False
    
    def detect_changes(self, current_opp: Dict, previous_opp: Dict) -> Dict:
        """Detect what changed between scrapes."""
        changes = {}
        
        # Check deadline changes
        if current_opp.get('deadline') != previous_opp.get('deadline'):
            changes['deadline'] = {
                'old': previous_opp.get('deadline'),
                'new': current_opp.get('deadline')
            }
        
        # Check fee changes
        if current_opp.get('fee') != previous_opp.get('fee'):
            changes['fee'] = {
                'old': previous_opp.get('fee'),
                'new': current_opp.get('fee')
            }
        
        # Check URL changes (might indicate platform changes)
        if current_opp.get('url') != previous_opp.get('url'):
            changes['url'] = {
                'old': previous_opp.get('url'),
                'new': current_opp.get('url')
            }
        
        return changes
    
    def extract_location_with_haiku(self, opp: Dict) -> Optional[Dict]:
        """Extract location using Haiku (same as before but with better prompting)."""
        
        title = opp.get('title', '')
        organization = opp.get('organization', '')
        scraped_location = opp.get('location', '') or opp.get('location_raw', '')
        url = opp.get('url', '')
        description = opp.get('description', '')
        
        # Skip if already has good location
        if opp.get('location_city') and opp.get('location_state'):
            return None
        
        prompt = f"""Extract the physical location from this art opportunity.

Title: {title}
Organization: {organization}
Location Field: {scraped_location}
URL: {url}
Description: {description[:500] if description else 'None'}

Extract venue, city, and state. Return JSON:
{{
    "venue": "venue name if found",
    "city": "city name",
    "state": "2-letter state code",
    "is_online": true/false,
    "confidence": "high/medium/low"
}}

Return null if no location found or if truly online-only."""

        try:
            response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            
            if 'null' in content.lower()[:20]:
                return None
            
            # Clean JSON response
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
            return None
    
    def process_opportunities(self, source_filter: str = None):
        """Process opportunities intelligently."""
        
        print("🤖 Smart Enrichment Starting...")
        print(f"Last run: {self.enrichment_log.get('last_run', 'Never')}\n")
        
        # Get all opportunities from database (limit for testing)
        query = self.supabase.table('opportunities').select('*')
        if source_filter:
            query = query.eq('source_platform', source_filter)
        
        # For large datasets, you might want to paginate
        response = query.limit(100).execute()  # Testing with first 100
        opportunities = response.data
        
        print(f"📊 Found {len(opportunities)} total opportunities")
        
        # Stats
        needs_enrichment = []
        already_enriched = []
        deadline_changes = []
        
        # Check each opportunity
        for opp in opportunities:
            opp_id = f"{opp.get('source_platform')}:{opp.get('title')}"
            
            # Check if needs enrichment
            if self.needs_enrichment(opp):
                needs_enrichment.append(opp)
            elif opp_id in self.enrichment_log['enriched_ids']:
                already_enriched.append(opp_id)
            
            # Check for deadline changes (if we've seen this before)
            if opp_id in self.enrichment_log.get('previous_deadlines', {}):
                old_deadline = self.enrichment_log['previous_deadlines'][opp_id]
                new_deadline = opp.get('deadline_raw')
                if old_deadline != new_deadline:
                    deadline_changes.append({
                        'id': opp_id,
                        'title': opp.get('title'),
                        'old': old_deadline,
                        'new': new_deadline
                    })
        
        # Report stats
        print(f"✅ Already enriched: {len(already_enriched)}")
        print(f"🔄 Need enrichment: {len(needs_enrichment)}")
        print(f"📅 Deadline changes: {len(deadline_changes)}")
        
        # Show deadline changes
        if deadline_changes:
            print("\n📅 DEADLINE CHANGES DETECTED:")
            for change in deadline_changes[:5]:  # Show first 5
                print(f"  • {change['title'][:50]}")
                print(f"    Old: {change['old']} → New: {change['new']}")
        
        # Process enrichments
        if needs_enrichment:
            print(f"\n🔄 Processing {len(needs_enrichment)} enrichments...")
            
            enriched_count = 0
            for i, opp in enumerate(needs_enrichment[:20], 1):  # Limit to 20 per run
                title = opp.get('title', '')
                opp_id = f"{opp.get('source_platform')}:{title}"
                
                print(f"\n[{i}] {title[:50]}...")
                print(f"  Current location: {opp.get('location_raw', 'None')}")
                
                # Extract location
                location_data = self.extract_location_with_haiku(opp)
                
                if location_data and location_data.get('confidence') in ['high', 'medium']:
                    # Update database
                    update_data = {}
                    
                    if location_data.get('is_online'):
                        update_data['location_raw'] = 'Online'
                    else:
                        parts = []
                        if location_data.get('city'):
                            parts.append(location_data['city'])
                            update_data['location_city'] = location_data['city']
                        if location_data.get('state'):
                            parts.append(location_data['state'])
                            update_data['location_state'] = location_data['state']
                        
                        if parts:
                            update_data['location_raw'] = ', '.join(parts)
                    
                    if update_data:
                        try:
                            self.supabase.table('opportunities').update(
                                update_data
                            ).eq('id', opp['id']).execute()
                            
                            print(f"  ✅ Enriched: {update_data.get('location_raw', 'Online')}")
                            
                            # Mark as enriched
                            self.enrichment_log['enriched_ids'][opp_id] = datetime.now().isoformat()
                            enriched_count += 1
                        except Exception as e:
                            print(f"  ❌ Database error: {e}")
                else:
                    print(f"  ⚠️  Could not extract location")
                    # Still mark as processed to avoid retrying
                    self.enrichment_log['enriched_ids'][opp_id] = datetime.now().isoformat()
                
                time.sleep(0.3)  # Rate limiting
            
            print(f"\n✅ Enriched {enriched_count} opportunities")
        else:
            print("\n✨ All opportunities already enriched!")
        
        # Update log
        self.enrichment_log['last_run'] = datetime.now().isoformat()
        
        # Track current deadlines for next run
        if 'previous_deadlines' not in self.enrichment_log:
            self.enrichment_log['previous_deadlines'] = {}
        
        for opp in opportunities:
            opp_id = f"{opp.get('source_platform')}:{opp.get('title')}"
            self.enrichment_log['previous_deadlines'][opp_id] = opp.get('deadline_raw')
        
        # Save log
        self.save_enrichment_log()
        
        # Summary
        print("\n" + "="*60)
        print("📊 ENRICHMENT SUMMARY")
        print("="*60)
        print(f"Total opportunities: {len(opportunities)}")
        print(f"Already enriched: {len(already_enriched)}")
        print(f"Newly enriched: {enriched_count}")
        print(f"Deadline changes: {len(deadline_changes)}")
        print(f"Next run will skip {len(self.enrichment_log['enriched_ids'])} already-processed items")

def main():
    """Run smart enrichment."""
    enricher = SmartEnricher()
    
    # Process all platforms, or filter to specific one
    enricher.process_opportunities()  # All platforms
    # enricher.process_opportunities('showsubmit')  # Just ShowSubmit

if __name__ == "__main__":
    main()