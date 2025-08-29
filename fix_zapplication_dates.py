#!/usr/bin/env python3
"""
Fix Zapplication date parsing and remove past events.
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
from dateutil import parser

load_dotenv()

def fix_zapplication_dates():
    """Fix Zapplication dates and remove past events."""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    supabase = create_client(supabase_url, supabase_key)
    
    print("="*70)
    print("FIXING ZAPPLICATION DATES")
    print("="*70)
    
    today = datetime.now()
    
    # 1. Parse all unparsed Zapplication dates
    print("\n1. PARSING UNPARSED ZAPPLICATION DATES")
    print("-"*40)
    
    response = supabase.table('opportunities').select('*').eq('source_platform', 'zapplication').is_('deadline_parsed', 'null').execute()
    
    print(f"Found {len(response.data)} Zapplication opportunities without parsed dates")
    
    fixed_count = 0
    failed_count = 0
    past_count = 0
    
    for opp in response.data:
        raw_deadline = opp.get('deadline_raw', '')
        
        if raw_deadline:
            try:
                # Parse the date
                parsed_date = parser.parse(raw_deadline, fuzzy=False)
                
                # Check if it's in the past
                if parsed_date < today:
                    # Delete past events
                    supabase.table('opportunities').delete().eq('id', opp['id']).execute()
                    past_count += 1
                    if past_count <= 5:
                        print(f"  🗑️  Removed past event: {opp['title'][:40]}... ({parsed_date.strftime('%Y-%m-%d')})")
                else:
                    # Update with parsed date
                    supabase.table('opportunities').update({
                        'deadline_parsed': parsed_date.isoformat()
                    }).eq('id', opp['id']).execute()
                    
                    fixed_count += 1
                    if fixed_count <= 5:
                        print(f"  ✅ Fixed: {opp['title'][:40]}... → {parsed_date.strftime('%Y-%m-%d')}")
                
            except Exception as e:
                failed_count += 1
                if failed_count <= 3:
                    print(f"  ❌ Failed to parse '{raw_deadline}': {e}")
    
    print(f"\n✅ Fixed {fixed_count} future Zapplication dates")
    print(f"🗑️  Removed {past_count} past events")
    if failed_count > 0:
        print(f"⚠️  Failed to parse {failed_count} dates")
    
    # 2. Check already-parsed dates for past events
    print("\n2. CHECKING ALREADY-PARSED DATES FOR PAST EVENTS")
    print("-"*40)
    
    response = supabase.table('opportunities').select('*').eq('source_platform', 'zapplication').not_.is_('deadline_parsed', 'null').execute()
    
    removed_past = 0
    for opp in response.data:
        try:
            parsed_date = datetime.fromisoformat(opp['deadline_parsed'].replace('Z', '+00:00'))
            if parsed_date < today:
                supabase.table('opportunities').delete().eq('id', opp['id']).execute()
                removed_past += 1
                if removed_past <= 5:
                    print(f"  🗑️  Removed: {opp['title'][:40]}... ({parsed_date.strftime('%Y-%m-%d')})")
        except:
            pass
    
    print(f"🗑️  Removed {removed_past} past events with parsed dates")
    
    # 3. Final statistics
    print("\n3. FINAL STATISTICS")
    print("-"*40)
    
    response = supabase.table('opportunities').select('title, deadline_parsed').eq('source_platform', 'zapplication').execute()
    
    total = len(response.data)
    with_dates = sum(1 for o in response.data if o.get('deadline_parsed'))
    
    print(f"Total Zapplication opportunities: {total}")
    print(f"With parsed dates: {with_dates}")
    print(f"Without parsed dates: {total - with_dates}")
    
    # Get date range
    dates = []
    for opp in response.data:
        if opp.get('deadline_parsed'):
            try:
                date = datetime.fromisoformat(opp['deadline_parsed'].replace('Z', '+00:00'))
                dates.append(date)
            except:
                pass
    
    if dates:
        dates.sort()
        print(f"\nDate range: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")
        
        # Count by month
        month_counts = {}
        for date in dates:
            month_key = f"{date.year}-{date.month:02d}"
            month_counts[month_key] = month_counts.get(month_key, 0) + 1
        
        print("\nOpportunities by month:")
        for month in sorted(month_counts.keys())[:10]:
            print(f"  {month}: {month_counts[month]} opportunities")

if __name__ == "__main__":
    fix_zapplication_dates()