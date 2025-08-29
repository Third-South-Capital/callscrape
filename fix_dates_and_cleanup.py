#!/usr/bin/env python3
"""
Fix date parsing issues and remove bad test data.
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
from dateutil import parser

load_dotenv()

def fix_dates_and_cleanup():
    """Fix Artwork Archive dates and remove test data."""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    supabase = create_client(supabase_url, supabase_key)
    
    print("="*70)
    print("FIXING DATES AND CLEANING BAD DATA")
    print("="*70)
    
    # 1. Remove obvious test/fake data
    print("\n1. REMOVING TEST/FAKE DATA")
    print("-"*40)
    
    bad_titles = [
        "Join The Free NOT REAL ART Database For Artists",
        "JuBu December Test Event #4"
    ]
    
    for title in bad_titles:
        response = supabase.table('opportunities').delete().eq('title', title).execute()
        print(f"✅ Removed: {title}")
    
    # Also remove any opportunities with deadlines after 2026
    response = supabase.table('opportunities').select('id, title, deadline_parsed').execute()
    removed_count = 0
    for opp in response.data:
        if opp.get('deadline_parsed'):
            try:
                date = datetime.fromisoformat(opp['deadline_parsed'].replace('Z', '+00:00'))
                if date.year > 2026:
                    supabase.table('opportunities').delete().eq('id', opp['id']).execute()
                    print(f"✅ Removed future date: {opp['title'][:50]} ({date.year})")
                    removed_count += 1
            except:
                pass
    
    print(f"Removed {removed_count} opportunities with dates after 2026")
    
    # 2. Fix Artwork Archive date parsing
    print("\n2. FIXING ARTWORK ARCHIVE DATE PARSING")
    print("-"*40)
    
    # Get all Artwork Archive opportunities without parsed dates
    response = supabase.table('opportunities').select('*').eq('source_platform', 'artwork_archive').is_('deadline_parsed', 'null').execute()
    
    print(f"Found {len(response.data)} Artwork Archive opportunities without parsed dates")
    
    fixed_count = 0
    failed_count = 0
    
    for opp in response.data:
        raw_deadline = opp.get('deadline_raw', '')
        
        if raw_deadline:
            try:
                # Parse the date
                parsed_date = parser.parse(raw_deadline, fuzzy=False)
                
                # Update the record
                supabase.table('opportunities').update({
                    'deadline_parsed': parsed_date.isoformat()
                }).eq('id', opp['id']).execute()
                
                fixed_count += 1
                if fixed_count <= 5:  # Show first 5 examples
                    print(f"  Fixed: {opp['title'][:40]}... → {parsed_date.strftime('%Y-%m-%d')}")
                
            except Exception as e:
                failed_count += 1
                if failed_count <= 3:  # Show first 3 failures
                    print(f"  ❌ Failed to parse '{raw_deadline}' for {opp['title'][:30]}: {e}")
    
    print(f"\n✅ Fixed {fixed_count} Artwork Archive dates")
    if failed_count > 0:
        print(f"⚠️  Failed to parse {failed_count} dates")
    
    # 3. Show final date range
    print("\n3. FINAL DATE RANGE")
    print("-"*40)
    
    response = supabase.table('opportunities').select('title, deadline_parsed, source_platform').execute()
    
    dates = []
    for opp in response.data:
        if opp.get('deadline_parsed'):
            try:
                date = datetime.fromisoformat(opp['deadline_parsed'].replace('Z', '+00:00'))
                dates.append((date, opp['source_platform'], opp['title']))
            except:
                pass
    
    dates.sort()
    
    if dates:
        print(f"Earliest: {dates[0][0].strftime('%Y-%m-%d')} ({dates[0][1]})")
        print(f"Latest: {dates[-1][0].strftime('%Y-%m-%d')} ({dates[-1][1]})")
        print(f"Total opportunities with valid dates: {len(dates)}")
        
        # Count by year
        year_counts = {}
        for date, _, _ in dates:
            year = date.year
            year_counts[year] = year_counts.get(year, 0) + 1
        
        print("\nOpportunities by year:")
        for year in sorted(year_counts.keys()):
            print(f"  {year}: {year_counts[year]} opportunities")

if __name__ == "__main__":
    fix_dates_and_cleanup()