#!/usr/bin/env python3
"""
Check raw ShowSubmit data to understand Email location issue.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def main():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Get ShowSubmit opportunities
    response = supabase.table('opportunities').select('*').eq(
        'source_platform', 'showsubmit'
    ).execute()
    
    showsubmit_opps = response.data
    print(f"Found {len(showsubmit_opps)} ShowSubmit opportunities\n")
    
    # Check first few with Email location
    email_locations = []
    for opp in showsubmit_opps:
        loc = opp.get('location_raw')
        if loc and 'email' in str(loc).lower():
            email_locations.append(opp)
    
    print(f"Found {len(email_locations)} with 'Email' in location\n")
    
    # Show first 3 examples
    for i, opp in enumerate(email_locations[:3], 1):
        print(f"[{i}] {opp['title']}")
        print(f"    location_raw: {repr(opp.get('location_raw'))}")
        print(f"    location_city: {repr(opp.get('location_city'))}")
        print(f"    location_state: {repr(opp.get('location_state'))}")
        desc = opp.get('description', '')
        if desc:
            print(f"    Description length: {len(desc)}")
            print(f"    Description snippet: {desc[:200]}...")
        else:
            print(f"    Description: None or empty")
        print()

if __name__ == "__main__":
    main()