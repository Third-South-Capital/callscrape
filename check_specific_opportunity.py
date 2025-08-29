#!/usr/bin/env python3
"""
Check what data we have for specific ShowSubmit opportunity.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def main():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Find the NJWS opportunity
    response = supabase.table('opportunities').select('*').ilike(
        'title', '%83rd%Annual%Open%Juried%'
    ).execute()
    
    if response.data:
        for opp in response.data:
            print(f"Title: {opp['title']}")
            print(f"Organization: {opp.get('organization')}")
            print(f"URL: {opp.get('url')}")
            print(f"Location Raw: {opp.get('location_raw')}")
            print(f"Description: {opp.get('description')}")
            print(f"\nWhat Haiku sees:")
            print(f"  Title: {opp['title']}")
            print(f"  Organization: {opp.get('organization')}")
            print(f"  Description: {opp.get('description') or f'Organization: {opp.get('organization')}'}")
            print()

if __name__ == "__main__":
    main()