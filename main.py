#!/usr/bin/env python3
"""
Main orchestrator for art opportunity scrapers.
Fetches opportunities from all platforms and combines them.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import hashlib

# Add the current directory to path to import scrapers
sys.path.insert(0, str(Path(__file__).parent))

from scrapers import SCRAPERS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'scraper_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)

logger = logging.getLogger(__name__)

class OpportunityAggregator:
    """Aggregates opportunities from all platforms and handles deduplication."""
    
    def __init__(self):
        self.opportunities = []
        self.duplicates = []
        
    def add_opportunities(self, opportunities: List[Dict], platform: str):
        """Add opportunities from a platform to the collection."""
        logger.info(f"Adding {len(opportunities)} opportunities from {platform}")
        
        for opp in opportunities:
            opp['source_platform'] = platform
            self.opportunities.append(opp)
    
    def deduplicate(self):
        """Remove duplicate opportunities across platforms."""
        seen_titles = {}
        unique_opportunities = []
        
        for opp in self.opportunities:
            # Create a normalized title for comparison
            normalized_title = opp['title'].lower().strip()
            
            # Check for similar titles (simple approach)
            if normalized_title in seen_titles:
                # Mark as duplicate and merge data
                existing = seen_titles[normalized_title]
                self.duplicates.append({
                    'title': opp['title'],
                    'platforms': [existing['source_platform'], opp['source_platform']]
                })
                
                # Merge data (prefer non-empty fields)
                for key, value in opp.items():
                    if value and not existing.get(key):
                        existing[key] = value
            else:
                seen_titles[normalized_title] = opp
                unique_opportunities.append(opp)
        
        self.opportunities = unique_opportunities
        
        if self.duplicates:
            logger.info(f"Found {len(self.duplicates)} duplicate opportunities")
    
    def save_results(self, output_dir: str = "data"):
        """Save aggregated results to JSON files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save main opportunities file
        main_file = output_path / f"opportunities_{timestamp}.json"
        with open(main_file, 'w') as f:
            json.dump(self.opportunities, f, indent=2, default=str)
        
        logger.info(f"Saved {len(self.opportunities)} opportunities to {main_file}")
        
        # Save duplicates report if any
        if self.duplicates:
            dup_file = output_path / f"duplicates_{timestamp}.json"
            with open(dup_file, 'w') as f:
                json.dump(self.duplicates, f, indent=2)
            logger.info(f"Saved duplicates report to {dup_file}")
        
        # Save summary statistics
        stats = self.get_statistics()
        stats_file = output_path / f"stats_{timestamp}.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        return main_file
    
    def get_statistics(self) -> Dict:
        """Generate statistics about the scraped data."""
        stats = {
            'total_opportunities': len(self.opportunities),
            'duplicates_found': len(self.duplicates),
            'scraped_at': datetime.now().isoformat(),
            'by_platform': {},
            'data_quality': {
                'with_deadline': 0,
                'with_organization': 0,
                'with_location': 0,
                'with_fee': 0
            }
        }
        
        # Count by platform
        for opp in self.opportunities:
            platform = opp.get('source_platform', 'unknown')
            stats['by_platform'][platform] = stats['by_platform'].get(platform, 0) + 1
            
            # Check data quality
            if opp.get('deadline'):
                stats['data_quality']['with_deadline'] += 1
            if opp.get('organization'):
                stats['data_quality']['with_organization'] += 1
            if opp.get('location'):
                stats['data_quality']['with_location'] += 1
            if opp.get('fee'):
                stats['data_quality']['with_fee'] += 1
        
        return stats

def main(platforms: List[str] = None, zap_limit: int = None):
    """
    Main execution function.
    
    Args:
        platforms: List of platform names to scrape. If None, scrapes all.
        zap_limit: Limit number of Zapplication events to scrape (None = all).
    """
    logger.info("="*60)
    logger.info("Starting Art Opportunity Scraper")
    logger.info("="*60)
    
    # Determine which platforms to scrape
    if platforms is None:
        platforms = list(SCRAPERS.keys())
    
    aggregator = OpportunityAggregator()
    successful_platforms = []
    failed_platforms = []
    
    # Run each scraper
    for platform in platforms:
        if platform not in SCRAPERS:
            logger.warning(f"Unknown platform: {platform}")
            continue
        
        logger.info(f"\nScraping {platform}...")
        
        try:
            scraper_class = SCRAPERS[platform]
            # Special handling for Zapplication with limit
            if platform == 'zapplication' and zap_limit is not None:
                scraper = scraper_class(max_events_limit=zap_limit)
            else:
                scraper = scraper_class()
            opportunities = scraper.run()
            
            if opportunities:
                aggregator.add_opportunities(opportunities, platform)
                successful_platforms.append(platform)
                logger.info(f"✓ {platform}: {len(opportunities)} opportunities")
            else:
                logger.warning(f"✗ {platform}: No opportunities found")
                failed_platforms.append(platform)
                
        except Exception as e:
            logger.error(f"✗ {platform}: Failed with error: {e}")
            failed_platforms.append(platform)
    
    # Process results
    if aggregator.opportunities:
        logger.info("\n" + "="*60)
        logger.info("Processing results...")
        
        # Deduplicate
        aggregator.deduplicate()
        
        # Save results
        output_file = aggregator.save_results()
        
        # Print summary
        stats = aggregator.get_statistics()
        
        logger.info("\n" + "="*60)
        logger.info("SCRAPING COMPLETE")
        logger.info("="*60)
        logger.info(f"✓ Total opportunities: {stats['total_opportunities']}")
        logger.info(f"✓ Duplicates removed: {stats['duplicates_found']}")
        logger.info(f"✓ Successful platforms: {', '.join(successful_platforms)}")
        
        if failed_platforms:
            logger.info(f"✗ Failed platforms: {', '.join(failed_platforms)}")
        
        logger.info("\nOpportunities by platform:")
        for platform, count in stats['by_platform'].items():
            logger.info(f"  - {platform}: {count}")
        
        logger.info("\nData quality:")
        total = stats['total_opportunities']
        if total > 0:
            for field, count in stats['data_quality'].items():
                percentage = (count / total) * 100
                logger.info(f"  - {field}: {count}/{total} ({percentage:.1f}%)")
        
        logger.info(f"\n✓ Results saved to: {output_file}")
        
        return True
    else:
        logger.error("\n✗ No opportunities found from any platform")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape art opportunities from multiple platforms")
    parser.add_argument(
        '--platforms',
        nargs='+',
        choices=list(SCRAPERS.keys()),
        help='Platforms to scrape (default: all)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--sync-db',
        action='store_true',
        help='Sync results to Supabase database'
    )
    parser.add_argument(
        '--db-only',
        action='store_true',
        help='Only sync existing data to database (no scraping)'
    )
    parser.add_argument(
        '--zap-limit',
        type=int,
        default=None,
        help='Limit number of Zapplication events to scrape (default: all)'
    )
    parser.add_argument(
        '--enrich',
        action='store_true',
        help='Run smart location enrichment after scraping (uses Claude Haiku)'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle database-only mode
    if args.db_only:
        from database import OpportunityDatabase
        from pathlib import Path
        
        db = OpportunityDatabase()
        data_dir = Path("data")
        if data_dir.exists():
            json_files = sorted(data_dir.glob("opportunities_*.json"))
            if json_files:
                latest_file = json_files[-1]
                logger.info(f"Syncing {latest_file} to database...")
                results = db.ingest_from_json(str(latest_file))
                logger.info(f"Database sync complete: {results}")
                sys.exit(0)
            else:
                logger.error("No opportunities files found in data/")
                sys.exit(1)
        else:
            logger.error("No data directory found")
            sys.exit(1)
    
    # Run the scraper
    success = main(platforms=args.platforms, zap_limit=args.zap_limit)
    
    # Sync to database if requested
    if success and args.sync_db:
        from database import OpportunityDatabase
        from pathlib import Path
        
        db = OpportunityDatabase()
        data_dir = Path("data")
        if data_dir.exists():
            json_files = sorted(data_dir.glob("opportunities_*.json"))
            if json_files:
                latest_file = json_files[-1]
                logger.info(f"\nSyncing to database: {latest_file}")
                results = db.ingest_from_json(str(latest_file))
                logger.info(f"Database sync complete: {results}")
    
    # Run enrichment if requested
    if args.enrich:
        logger.info("\n" + "="*60)
        logger.info("Running smart location enrichment...")
        logger.info("="*60)
        try:
            from smart_enrichment import SmartEnricher
            enricher = SmartEnricher()
            enricher.process_opportunities()
        except Exception as e:
            logger.error(f"Enrichment failed: {e}")
    
    sys.exit(0 if success else 1)