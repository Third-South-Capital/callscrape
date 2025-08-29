#!/usr/bin/env python3
"""
Check for opportunities with bad location data, especially ShowSubmit.
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
    
    # Check for bad locations
    bad_locations = []
    
    for opp in showsubmit_opps:
        location = opp.get('location_raw', '').lower()
        title = opp.get('title', '')
        description = opp.get('description', '')
        
        if location in ['email', 'email:', 'online', '', 'n/a'] or '@' in location:
            bad_locations.append(opp)
            print(f"❌ {title[:50]}")
            print(f"   Location: '{opp.get('location_raw')}'")
            
            # Check if description contains location info
            desc_lower = description.lower() if description else ''
            if any(word in desc_lower for word in ['delivered to', 'ship to', 'mail to', ', nj', ', ny', ', ca', ', tx', ', fl']):
                print(f"   ✅ Description likely contains location")
                print(f"   Sample: {description[:150]}...")
            print()
    
    print(f"\n📊 Summary: {len(bad_locations)}/{len(showsubmit_opps)} ShowSubmit opportunities have bad locations")
    
    # Check other platforms too
    print("\n🔍 Checking other platforms...")
    
    all_response = supabase.table('opportunities').select('source_platform, location_raw').execute()
    
    by_platform = {}
    bad_by_platform = {}
    
    for opp in all_response.data:
        platform = opp.get('source_platform', 'unknown')
        location = opp.get('location_raw') or ''
        location = location.lower()
        
        by_platform[platform] = by_platform.get(platform, 0) + 1
        
        if location in ['email', 'email:', 'online', '', 'n/a'] or '@' in location:
            bad_by_platform[platform] = bad_by_platform.get(platform, 0) + 1
    
    print("\nBad locations by platform:")
    for platform in sorted(by_platform.keys()):
        bad_count = bad_by_platform.get(platform, 0)
        total_count = by_platform[platform]
        if bad_count > 0:
            print(f"  {platform}: {bad_count}/{total_count} ({bad_count/total_count*100:.1f}%)")

if __name__ == "__main__":
    main()