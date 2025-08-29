#!/usr/bin/env python3
"""
Analyze enrichment quality with before/after comparison and add AI-generated summaries.
Tests on a sample of 25 records across different platforms.
"""

import os
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import anthropic

load_dotenv()

class EnrichmentAnalyzer:
    def __init__(self):
        """Initialize with Supabase and Anthropic."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(supabase_url, supabase_key)
        
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.anthropic = anthropic.Anthropic(api_key=anthropic_key)
    
    def get_sample_opportunities(self, sample_size: int = 25) -> List[Dict]:
        """Get a diverse sample of opportunities for testing."""
        
        print("📊 Gathering sample opportunities...")
        
        # Get a mix from different platforms
        samples = []
        
        # Platforms to sample from
        platforms = ['showsubmit', 'cafe', 'zapplication', 'artwork_archive', 'artcall']
        
        for platform in platforms:
            # Get 5 from each platform
            response = self.supabase.table('opportunities').select('*').eq(
                'source_platform', platform
            ).limit(5).execute()
            
            if response.data:
                samples.extend(response.data)
                print(f"  • {platform}: {len(response.data)} opportunities")
        
        # Shuffle and limit to sample_size
        random.shuffle(samples)
        samples = samples[:sample_size]
        
        print(f"\n✅ Selected {len(samples)} opportunities for analysis")
        return samples
    
    def enrich_opportunity(self, opp: Dict) -> Dict:
        """
        Enrich a single opportunity with:
        1. Better location data
        2. AI-generated 3-sentence summary
        """
        
        title = opp.get('title', '')
        organization = opp.get('organization', '')
        description = opp.get('description', '')
        location_raw = opp.get('location_raw', '')
        deadline = opp.get('deadline_raw', '')
        fee = opp.get('fee_raw', '')
        url = opp.get('url', '')
        
        prompt = f"""Analyze this art opportunity and provide:
1. Location extraction (venue, city, state)
2. A 3-sentence summary for artists

Opportunity Details:
Title: {title}
Organization: {organization}
Location: {location_raw}
Deadline: {deadline}
Fee: {fee}
URL: {url}
Description: {description[:1000] if description else 'No description available'}

Provide response as JSON:
{{
    "location": {{
        "venue": "venue name if found",
        "city": "city name",
        "state": "2-letter state code",
        "country": "country if not USA",
        "is_online": true/false
    }},
    "summary": "A 3-sentence summary that covers: (1) What this opportunity is and who it's for. (2) Key eligibility requirements, medium restrictions, or important details. (3) Deadline, fee, and any unique benefits or features.",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "opportunity_type": "exhibition|fair|residency|grant|competition|market|online",
    "confidence": "high|medium|low"
}}

Make the summary informative and actionable for artists deciding whether to apply."""

        try:
            response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=800,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            
            # Parse JSON response
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
    
    def analyze_enrichment(self, original: Dict, enriched: Dict) -> Dict:
        """Analyze the quality of enrichment."""
        
        analysis = {
            'title': original.get('title', ''),
            'platform': original.get('source_platform', ''),
            'before': {
                'location': original.get('location_raw', ''),
                'has_city': bool(original.get('location_city')),
                'has_state': bool(original.get('location_state')),
                'has_description': bool(original.get('description'))
            },
            'after': {},
            'improvements': []
        }
        
        if enriched:
            # Location improvements
            location = enriched.get('location', {})
            if location.get('city') and not original.get('location_city'):
                analysis['improvements'].append('Added city')
            if location.get('state') and not original.get('location_state'):
                analysis['improvements'].append('Added state')
            if location.get('venue'):
                analysis['improvements'].append('Identified venue')
            
            # Summary addition
            if enriched.get('summary'):
                analysis['improvements'].append('Generated summary')
                analysis['after']['summary'] = enriched['summary']
            
            # Keywords and type
            if enriched.get('keywords'):
                analysis['improvements'].append(f"Added {len(enriched['keywords'])} keywords")
            if enriched.get('opportunity_type'):
                analysis['improvements'].append(f"Classified as {enriched['opportunity_type']}")
            
            analysis['after']['location'] = location
            analysis['after']['confidence'] = enriched.get('confidence', 'unknown')
        
        analysis['improvement_count'] = len(analysis['improvements'])
        
        return analysis
    
    def run_analysis(self):
        """Run the full before/after analysis."""
        
        print("\n" + "="*70)
        print("🔬 ENRICHMENT QUALITY ANALYSIS")
        print("="*70)
        
        # Get sample
        samples = self.get_sample_opportunities(25)
        
        # Analyze each
        results = []
        
        for i, opp in enumerate(samples, 1):
            title = opp.get('title', '')[:50]
            platform = opp.get('source_platform', '')
            
            print(f"\n[{i}/25] {title}...")
            print(f"  Platform: {platform}")
            print(f"  Before: {opp.get('location_raw', 'No location')}")
            
            # Enrich
            enriched = self.enrich_opportunity(opp)
            
            if enriched:
                location = enriched.get('location', {})
                
                # Show location improvements
                if location.get('city') or location.get('state'):
                    loc_str = f"{location.get('city', '')}, {location.get('state', '')}"
                    print(f"  ✅ After: {loc_str}")
                    if location.get('venue'):
                        print(f"     Venue: {location['venue']}")
                
                # Show summary (truncated)
                if enriched.get('summary'):
                    summary = enriched['summary']
                    print(f"  📝 Summary: {summary[:100]}...")
                
                # Keywords and type
                if enriched.get('keywords'):
                    print(f"  🏷️  Keywords: {', '.join(enriched['keywords'])}")
                if enriched.get('opportunity_type'):
                    print(f"  📂 Type: {enriched['opportunity_type']}")
            
            # Analyze
            analysis = self.analyze_enrichment(opp, enriched)
            results.append(analysis)
            
            # Rate limiting
            time.sleep(0.5)
        
        # Summary statistics
        print("\n" + "="*70)
        print("📊 ENRICHMENT SUMMARY")
        print("="*70)
        
        # Count improvements
        total_improvements = sum(r['improvement_count'] for r in results)
        with_city = sum(1 for r in results if 'Added city' in r['improvements'])
        with_state = sum(1 for r in results if 'Added state' in r['improvements'])
        with_venue = sum(1 for r in results if 'Identified venue' in r['improvements'])
        with_summary = sum(1 for r in results if 'Generated summary' in r['improvements'])
        with_keywords = sum(1 for r in results if any('keywords' in imp for imp in r['improvements']))
        
        print(f"\n📈 Improvement Statistics:")
        print(f"  • Total improvements: {total_improvements}")
        print(f"  • Added city: {with_city}/{len(results)} ({with_city/len(results)*100:.1f}%)")
        print(f"  • Added state: {with_state}/{len(results)} ({with_state/len(results)*100:.1f}%)")
        print(f"  • Identified venue: {with_venue}/{len(results)} ({with_venue/len(results)*100:.1f}%)")
        print(f"  • Generated summary: {with_summary}/{len(results)} ({with_summary/len(results)*100:.1f}%)")
        print(f"  • Added keywords: {with_keywords}/{len(results)} ({with_keywords/len(results)*100:.1f}%)")
        
        # Platform breakdown
        print(f"\n🎯 By Platform:")
        platform_stats = {}
        for r in results:
            platform = r['platform']
            if platform not in platform_stats:
                platform_stats[platform] = {'total': 0, 'improvements': 0}
            platform_stats[platform]['total'] += 1
            platform_stats[platform]['improvements'] += r['improvement_count']
        
        for platform, stats in platform_stats.items():
            avg_improvements = stats['improvements'] / stats['total'] if stats['total'] > 0 else 0
            print(f"  • {platform}: {avg_improvements:.1f} improvements per record")
        
        # Show best examples
        print(f"\n⭐ Best Enrichments (most improvements):")
        best = sorted(results, key=lambda x: x['improvement_count'], reverse=True)[:3]
        for r in best:
            print(f"  • {r['title'][:40]}: {r['improvement_count']} improvements")
            print(f"    {', '.join(r['improvements'][:3])}")
        
        # Save detailed results
        output_file = f"data/enrichment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        # Show sample summaries
        print(f"\n📝 Sample AI-Generated Summaries:")
        print("-"*70)
        
        summaries = [r for r in results if r.get('after', {}).get('summary')][:3]
        for i, r in enumerate(summaries, 1):
            print(f"\n{i}. {r['title'][:50]}")
            print(f"   Platform: {r['platform']}")
            print(f"\n   {r['after']['summary']}")
        
        return results

def main():
    """Run the enrichment analysis."""
    analyzer = EnrichmentAnalyzer()
    results = analyzer.run_analysis()

if __name__ == "__main__":
    main()