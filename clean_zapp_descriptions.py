#!/usr/bin/env python3
"""
Clean up bad Zapplication descriptions in the database.
Remove contact info that was incorrectly saved as descriptions.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def clean_zapplication_descriptions():
    """Remove bad descriptions from Zapplication opportunities."""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    supabase = create_client(supabase_url, supabase_key)
    
    print("="*70)
    print("CLEANING ZAPPLICATION DESCRIPTIONS")
    print("="*70)
    
    # Get all Zapplication opportunities
    response = supabase.table('opportunities').select('id, title, description').eq('source_platform', 'zapplication').execute()
    
    if not response.data:
        print("No Zapplication opportunities found")
        return
    
    total = len(response.data)
    print(f"Found {total} Zapplication opportunities")
    
    # Find bad descriptions
    bad_descriptions = []
    for opp in response.data:
        desc = opp.get('description', '')
        if desc and any(bad in desc for bad in [
            'Contact Information:', 
            'Ph:', 
            'fairs@',
            'Images:', 
            'booth shot is required',
            'Location:'  # These are just repeating the location field
        ]):
            bad_descriptions.append(opp)
    
    print(f"Found {len(bad_descriptions)} opportunities with bad descriptions")
    
    if bad_descriptions:
        print("\nExamples of bad descriptions to remove:")
        for opp in bad_descriptions[:5]:
            print(f"  • {opp['title'][:50]}")
            print(f"    {opp['description'][:100]}...")
        
        print(f"\nClearing {len(bad_descriptions)} bad descriptions...")
        
        # Clear the bad descriptions
        for opp in bad_descriptions:
            supabase.table('opportunities').update({
                'description': ''  # Clear the description
            }).eq('id', opp['id']).execute()
        
        print(f"✅ Cleared {len(bad_descriptions)} bad descriptions")
    
    # Stats after cleaning
    remaining_with_desc = total - len(bad_descriptions)
    print(f"\n📊 Final stats:")
    print(f"  • Total Zapplication opportunities: {total}")
    print(f"  • Cleaned bad descriptions: {len(bad_descriptions)}")
    print(f"  • Remaining with descriptions: {remaining_with_desc}")
    print("\nThese opportunities are now ready for AI enrichment!")

if __name__ == "__main__":
    clean_zapplication_descriptions()