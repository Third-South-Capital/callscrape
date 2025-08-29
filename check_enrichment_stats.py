#!/usr/bin/env python3
"""
Check enrichment statistics and calculate API costs.
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(supabase_url, supabase_key)

print('='*80)
print('📊 ENRICHMENT STATISTICS & COST ANALYSIS')
print('='*80)

# Check enrichment log
try:
    with open('data/enrichment_log.json') as f:
        log = json.load(f)
        enriched_ids = log.get('enriched_ids', {})
        print('\n📝 Smart Enrichment Log:')
        print(f'  • Records tracked: {len(enriched_ids)}')
        if enriched_ids:
            # Get dates
            dates = list(enriched_ids.values())
            dates.sort()
            print(f'  • First enrichment: {dates[0][:10]}')
            print(f'  • Last enrichment: {dates[-1][:10]}')
except:
    print('  • No enrichment log found')

# Query database for enriched records
print('\n📊 Database Statistics by Platform:')

platforms = ['showsubmit', 'artcall', 'zapplication', 'cafe', 'artwork_archive']
total_enriched = 0
platform_details = []

for platform in platforms:
    # Count records with enriched fields
    all_records = supabase.table('opportunities').select('id, location_city, location_state, description').eq('source_platform', platform).execute()
    
    if all_records.data:
        with_city = sum(1 for r in all_records.data if r.get('location_city'))
        with_state = sum(1 for r in all_records.data if r.get('location_state'))
        with_desc = sum(1 for r in all_records.data if r.get('description') and len(r.get('description', '')) > 100)
        
        # Consider enriched if has city/state or meaningful description
        enriched = sum(1 for r in all_records.data if 
                      (r.get('location_city') or r.get('location_state')) or 
                      (r.get('description') and len(r.get('description', '')) > 100))
        
        total_enriched += enriched
        
        platform_details.append({
            'name': platform,
            'total': len(all_records.data),
            'with_city': with_city,
            'with_state': with_state,
            'with_desc': with_desc,
            'enriched': enriched
        })
        
        print(f'  {platform:20} Total: {len(all_records.data):3} | City: {with_city:3} | State: {with_state:3} | Desc: {with_desc:3} | Enriched: {enriched:3}')

print(f'\n  TOTAL ENRICHED: ~{total_enriched} records')

# Calculate API costs
print('\n💰 Claude Haiku API Cost Estimation:')
print('  Pricing: $0.25 per million input tokens, $1.25 per million output tokens')
print()

# Count actual API calls made
api_calls_made = 0

# From enrichment sessions:
# 1. Initial ShowSubmit test: ~10 calls
# 2. Smart enrichment run: 20 calls  
# 3. Enrichment analysis: 25 calls
# 4. ArtCall full enrichment: 5 calls
# 5. Various test runs: ~15 calls

estimated_api_calls = 10 + 20 + 25 + 5 + 15  # ~75 calls

# More accurate token estimation based on our prompts
avg_input_tokens = 600   # Our prompts include description, title, organization, etc.
avg_output_tokens = 250  # JSON responses with location, summary, keywords

total_input_tokens = estimated_api_calls * avg_input_tokens
total_output_tokens = estimated_api_calls * avg_output_tokens

input_cost = (total_input_tokens / 1_000_000) * 0.25
output_cost = (total_output_tokens / 1_000_000) * 1.25
total_cost = input_cost + output_cost

print(f'  Estimated API calls made: {estimated_api_calls}')
print(f'  Estimated input tokens: {total_input_tokens:,} (~{avg_input_tokens} per call)')
print(f'  Estimated output tokens: {total_output_tokens:,} (~{avg_output_tokens} per call)')
print(f'  Input cost: ${input_cost:.4f}')
print(f'  Output cost: ${output_cost:.4f}')
print(f'  TOTAL ESTIMATED COST: ${total_cost:.4f}')
print()
print(f'  Average cost per enrichment: ${total_cost/estimated_api_calls:.5f}')

# Projection for full database
total_records = sum(p['total'] for p in platform_details)
remaining_to_enrich = total_records - total_enriched

if remaining_to_enrich > 0:
    print('\n📈 Projection for Full Database Enrichment:')
    print(f'  Records remaining: {remaining_to_enrich}')
    projected_cost = (remaining_to_enrich * (total_cost / estimated_api_calls))
    print(f'  Estimated cost to complete: ${projected_cost:.2f}')
    print(f'  Total cost for all {total_records} records: ${projected_cost + total_cost:.2f}')

print('\n✅ Summary:')
print(f'  • Records enriched so far: {total_enriched}')
print(f'  • API calls made: ~{estimated_api_calls}')
print(f'  • Total cost so far: ${total_cost:.4f}')
print(f'  • Cost efficiency: ${(total_cost/estimated_api_calls)*1000:.2f} per 1000 enrichments')