#!/usr/bin/env python3
"""
Phase 2: Enrichment - Fetches descriptions for opportunities that need them.
This can run slowly in the background.
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import OpportunityDatabase
from scrapers.cafe_direct import CafeDirectScraper
from scrapers.artcall_enhanced import ArtCallEnhancedScraper
from scrapers.artwork_archive_enhanced import ArtworkArchiveEnhancedScraper
from scrapers.showsubmit import ShowSubmitScraper
from scrapers.zapplication import ZapplicationScraper
from utils.location_enricher import enrich_location, format_location_display

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OpportunityEnricher:
    """Enriches opportunities with descriptions and additional details."""
    
    def __init__(self, batch_size: int = 10, delay_between_batches: float = 5.0):
        self.db = OpportunityDatabase()
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        
        # Initialize scrapers
        self.scrapers = {
            'cafe': CafeDirectScraper(),
            'artcall': ArtCallEnhancedScraper(),
            'artwork_archive': ArtworkArchiveEnhancedScraper(),
            'showsubmit': ShowSubmitScraper(),
            'zapplication': ZapplicationScraper()
        }
        
        # Configure rate limiting
        if 'artcall' in self.scrapers:
            self.scrapers['artcall'].rate_limit_delay = 1.5
        if 'artwork_archive' in self.scrapers:
            self.scrapers['artwork_archive'].rate_limit_delay = 2.0
            self.scrapers['artwork_archive'].max_retries = 5
    
    def enrich_cafe_opportunity(self, opp: Dict) -> Dict:
        """Enrich a CAFE opportunity with description."""
        # CAFE direct scraper already gets full descriptions from API
        # No additional enrichment needed
        if opp.get('description'):
            logger.info(f"    ✓ Already has {len(opp['description'])} chars from API")
            opp['needs_enrichment'] = False
        else:
            logger.info(f"    ⚠ No description available")
        return opp
    
    def enrich_artcall_opportunity(self, opp: Dict) -> Dict:
        """Enrich an ArtCall opportunity with description."""
        scraper = self.scrapers['artcall']
        
        try:
            # Extract detail page
            details = scraper.extract_detail_page(opp['url'])
            
            if details:
                # Update opportunity with enriched data
                if details.get('description'):
                    opp['description'] = details['description']
                    logger.info(f"    ✓ Got {len(details['description'])} chars")
                
                # Add other enriched fields
                for field in ['organization', 'location', 'fee', 'deadline', 
                             'eligibility', 'prizes', 'jury', 'event_dates']:
                    if details.get(field):
                        opp[field] = details[field]
                
                opp['enriched_at'] = datetime.now().isoformat()
                opp['needs_enrichment'] = False
            else:
                logger.warning(f"    ✗ No details extracted")
                
        except Exception as e:
            logger.error(f"    ✗ Error: {e}")
        
        return opp
    
    def enrich_artwork_archive_opportunity(self, opp: Dict) -> Dict:
        """Enrich an Artwork Archive opportunity with description."""
        scraper = self.scrapers['artwork_archive']
        
        try:
            # Extract detail page
            details = scraper.extract_detail_page(opp['url'])
            
            if details:
                # Update opportunity with enriched data
                if details.get('description'):
                    opp['description'] = details['description']
                    logger.info(f"    ✓ Got {len(details['description'])} chars")
                
                # Add other enriched fields
                for field in ['organization', 'location', 'fee', 'deadline',
                             'eligibility', 'entry_details']:
                    if details.get(field):
                        opp[field] = details[field]
                
                opp['enriched_at'] = datetime.now().isoformat()
                opp['needs_enrichment'] = False
            else:
                logger.warning(f"    ✗ No details extracted")
                
        except Exception as e:
            logger.error(f"    ✗ Error: {e}")
        
        return opp
    
    def enrich_showsubmit_opportunity(self, opp: Dict) -> Dict:
        """Enrich a ShowSubmit opportunity (limited due to login requirements)."""
        # ShowSubmit requires login for most descriptions
        logger.info(f"    ⚠ ShowSubmit requires login for descriptions")
        return opp
    
    def enrich_zapplication_opportunity(self, opp: Dict) -> Dict:
        """Enrich a Zapplication opportunity."""
        # Zapplication scraper already gets descriptions in initial scrape
        logger.info(f"    ⚠ Zapplication enrichment requires Selenium")
        return opp
    
    def enrich_opportunity(self, opp: Dict) -> Dict:
        """Enrich a single opportunity based on its platform."""
        platform = opp.get('source_platform', '')
        
        enrichers = {
            'cafe': self.enrich_cafe_opportunity,
            'artcall': self.enrich_artcall_opportunity,
            'artwork_archive': self.enrich_artwork_archive_opportunity,
            'showsubmit': self.enrich_showsubmit_opportunity,
            'zapplication': self.enrich_zapplication_opportunity
        }
        
        # Platform-specific enrichment
        if platform in enrichers:
            opp = enrichers[platform](opp)
        else:
            logger.warning(f"  Unknown platform: {platform}")
        
        # Apply location enrichment to all opportunities
        opp = enrich_location(opp, extract_from_description=True)
        
        # Log location status
        if 'extras' in opp and 'location_metadata' in opp['extras']:
            meta = opp['extras']['location_metadata']
            if meta['enriched'] == 'Not Specified':
                logger.info(f"    📍 Location: Not Specified")
            elif meta['confidence'] == 'low':
                logger.info(f"    📍 Location: {meta['enriched']} (uncertain)")
            else:
                logger.info(f"    📍 Location: {meta['enriched']}")
        
        return opp
    
    def enrich_from_file(self, json_file: str, limit: int = None) -> List[Dict]:
        """Enrich opportunities from a JSON file."""
        # Load opportunities
        with open(json_file, 'r') as f:
            opportunities = json.load(f)
        
        if limit:
            opportunities = opportunities[:limit]
        
        logger.info(f"Loaded {len(opportunities)} opportunities to enrich")
        
        # Group by platform for efficient processing
        by_platform = {}
        for opp in opportunities:
            platform = opp.get('source_platform', 'unknown')
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(opp)
        
        # Process each platform
        enriched = []
        for platform, platform_opps in by_platform.items():
            logger.info(f"\nEnriching {len(platform_opps)} {platform} opportunities...")
            
            # Process in batches
            for i in range(0, len(platform_opps), self.batch_size):
                batch = platform_opps[i:i+self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (len(platform_opps) + self.batch_size - 1) // self.batch_size
                
                logger.info(f"  Batch {batch_num}/{total_batches} ({len(batch)} items)")
                
                for j, opp in enumerate(batch, 1):
                    logger.info(f"  [{i+j}/{len(platform_opps)}] {opp['title'][:50]}...")
                    enriched_opp = self.enrich_opportunity(opp)
                    enriched.append(enriched_opp)
                
                # Delay between batches to avoid rate limiting
                if i + self.batch_size < len(platform_opps):
                    logger.info(f"  Waiting {self.delay_between_batches}s before next batch...")
                    time.sleep(self.delay_between_batches)
        
        return enriched
    
    def update_database(self, opportunities: List[Dict]):
        """Update database with enriched opportunities."""
        logger.info("\nUpdating database with enriched data...")
        
        success_count = 0
        error_count = 0
        
        for opp in opportunities:
            try:
                # Update the opportunity in database
                result = self.db.client.table('opportunities').update({
                    'description': opp.get('description'),
                    'extras': opp,  # Store all enriched data in extras
                    'updated_at': datetime.now().isoformat()
                }).eq('id', opp['id']).execute()
                
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to update {opp['id']}: {e}")
                error_count += 1
        
        logger.info(f"✓ Updated {success_count} opportunities")
        if error_count > 0:
            logger.warning(f"✗ Failed to update {error_count} opportunities")
    
    def run(self, input_file: str = None, limit: int = None):
        """Run the enrichment process."""
        logger.info("="*70)
        logger.info("PHASE 2: ENRICHMENT")
        logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*70)
        
        # Find input file if not specified
        if not input_file:
            # Look for most recent phase1_new file
            data_dir = Path("data")
            new_files = sorted(data_dir.glob("phase1_new_*.json"))
            if new_files:
                input_file = str(new_files[-1])
                logger.info(f"Using most recent new opportunities file: {input_file}")
            else:
                logger.error("No phase1_new files found. Run phase1_fast_scrape.py first.")
                return False
        
        # Enrich opportunities
        enriched = self.enrich_from_file(input_file, limit=limit)
        
        # Save enriched data
        output_dir = Path("data")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"phase2_enriched_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(enriched, f, indent=2, default=str)
        
        # Update database
        self.update_database(enriched)
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("PHASE 2 COMPLETE")
        logger.info("="*70)
        
        with_desc = sum(1 for o in enriched 
                       if o.get('description') and len(o.get('description', '')) > 50)
        logger.info(f"Total enriched: {len(enriched)}")
        logger.info(f"With descriptions: {with_desc}/{len(enriched)}")
        logger.info(f"Saved to: {output_file}")
        
        return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 2: Enrich opportunities with descriptions")
    parser.add_argument('--input', help='Input JSON file with opportunities to enrich')
    parser.add_argument('--limit', type=int, help='Limit number to enrich (for testing)')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
    
    args = parser.parse_args()
    
    enricher = OpportunityEnricher(batch_size=args.batch_size)
    success = enricher.run(input_file=args.input, limit=args.limit)
    
    if success:
        print("\n✓ Phase 2 complete. Opportunities enriched and saved to database.")
    else:
        print("\n✗ Phase 2 failed. Check logs for details.")