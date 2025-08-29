#!/usr/bin/env python3
"""
Database integration for art opportunities.
Handles Supabase connection, data ingestion, and deduplication.
"""

import os
import json
import uuid
import hashlib
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from dateutil import parser
import re
from dotenv import load_dotenv

# Try to import Supabase, but make it optional
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: Supabase not installed. Run: pip install supabase")

logger = logging.getLogger(__name__)

class OpportunityDatabase:
    """Manages database operations for art opportunities."""
    
    def __init__(self, use_supabase: bool = True):
        """Initialize database connection."""
        load_dotenv()
        
        self.use_supabase = use_supabase and SUPABASE_AVAILABLE
        self.client = None
        
        if self.use_supabase:
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY')
            
            if url and key:
                self.client = create_client(url, key)
                logger.info("Connected to Supabase")
            else:
                logger.warning("Supabase credentials not found in .env file")
                self.use_supabase = False
    
    def generate_deterministic_id(self, source: str, unique_str: str) -> str:
        """Generate a deterministic UUID from source and unique string."""
        # Use namespace UUID for consistency
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        return str(uuid.uuid5(namespace, f"{source}:{unique_str}"))
    
    def parse_deadline(self, deadline_raw: str) -> Optional[date]:
        """Parse deadline text into a date object."""
        if not deadline_raw:
            return None
        
        try:
            # Handle various formats
            parsed = parser.parse(deadline_raw, fuzzy=True)
            return parsed.date()
        except:
            # Try manual patterns
            patterns = [
                r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
                r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # Month DD, YYYY
            ]
            
            for pattern in patterns:
                match = re.search(pattern, deadline_raw)
                if match:
                    try:
                        if '-' in deadline_raw:
                            return date(*map(int, match.groups()))
                        else:
                            return parser.parse(' '.join(match.groups())).date()
                    except:
                        continue
            
            return None
    
    def parse_location(self, location_raw: str) -> Dict[str, str]:
        """Parse location string into components."""
        result = {
            'location_raw': location_raw or '',
            'location_city': None,
            'location_state': None
        }
        
        if not location_raw:
            return result
        
        # Try common patterns
        patterns = [
            r'^([^,]+),\s*([A-Z]{2})$',  # City, ST
            r'^([^,]+),\s*([A-Za-z\s]+)$',  # City, State Name
        ]
        
        for pattern in patterns:
            match = re.match(pattern, location_raw.strip())
            if match:
                result['location_city'] = match.group(1).strip()
                result['location_state'] = match.group(2).strip()
                break
        
        return result
    
    def parse_fee(self, fee_raw: str) -> Dict[str, Any]:
        """Parse fee information."""
        result = {
            'fee_raw': fee_raw or '',
            'fee_amount': None,
            'fee_is_free': False
        }
        
        if not fee_raw:
            return result
        
        # Check for free
        if 'free' in fee_raw.lower() or fee_raw == '0' or fee_raw == '$0':
            result['fee_is_free'] = True
            result['fee_amount'] = 0
            return result
        
        # Extract numeric amount
        match = re.search(r'\$?\s*(\d+(?:\.\d{2})?)', fee_raw)
        if match:
            result['fee_amount'] = float(match.group(1))
        
        return result
    
    def normalize_opportunity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize opportunity data for database insertion."""
        # Generate deterministic ID
        source = raw_data.get('source_platform', 'unknown')
        unique_str = raw_data.get('url', '') or raw_data.get('id', '') or raw_data.get('title', '')
        
        # Parse structured fields
        location_data = self.parse_location(raw_data.get('location', ''))
        fee_data = self.parse_fee(raw_data.get('fee', ''))
        deadline_parsed = self.parse_deadline(raw_data.get('deadline', ''))
        
        # Build normalized record
        normalized = {
            'id': self.generate_deterministic_id(source, unique_str),
            'title': raw_data.get('title', '').strip(),
            'organization': raw_data.get('organization', '').strip() or None,
            'url': raw_data.get('url', '').strip(),
            'source_platform': source,
            
            # Deadlines
            'deadline_raw': raw_data.get('deadline', ''),
            'deadline_parsed': deadline_parsed.isoformat() if deadline_parsed else None,
            
            # Location
            **location_data,
            
            # Fees
            **fee_data,
            
            # Other fields
            'description': raw_data.get('description', '')[:5000] if raw_data.get('description') else '',
            'eligibility': raw_data.get('eligibility', ''),
            'email': raw_data.get('email', ''),
            
            # Platform-specific data in extras
            'extras': {
                k: v for k, v in raw_data.items() 
                if k not in ['title', 'organization', 'url', 'deadline', 'location', 'fee', 'description']
            },
            
            # Platform ID if available
            'platform_id': raw_data.get('platform_id') or raw_data.get('zapp_id') or raw_data.get('id'),
            
            # Tracking
            'is_active': True if not deadline_parsed or deadline_parsed >= date.today() else False,
            'last_seen': datetime.now().isoformat(),
        }
        
        return normalized
    
    def find_duplicates(self, opportunity: Dict[str, Any], existing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find potential duplicates in existing opportunities."""
        duplicates = []
        
        title_lower = opportunity['title'].lower()
        org_lower = (opportunity.get('organization') or '').lower()
        
        for existing_opp in existing:
            # Check for exact URL match
            if existing_opp['url'] == opportunity['url']:
                duplicates.append(existing_opp)
                continue
            
            # Check for very similar titles
            existing_title = existing_opp['title'].lower()
            if title_lower == existing_title:
                duplicates.append(existing_opp)
                continue
            
            # Check for title + org match
            if org_lower and org_lower == (existing_opp.get('organization') or '').lower():
                # Calculate title similarity
                title_similarity = self._string_similarity(title_lower, existing_title)
                if title_similarity > 0.85:  # 85% similar
                    duplicates.append(existing_opp)
        
        return duplicates
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate simple string similarity ratio."""
        if not s1 or not s2:
            return 0.0
        
        # Simple character overlap ratio
        set1 = set(s1.split())
        set2 = set(s2.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def upsert_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update an opportunity in the database."""
        if not self.use_supabase or not self.client:
            return {"status": "skipped", "reason": "No database connection"}
        
        try:
            # Check if opportunity exists
            response = self.client.table('opportunities').select('*').eq('id', opportunity['id']).execute()
            
            if response.data:
                # Update existing
                existing = response.data[0]
                
                # Update last_seen and increment times_seen
                opportunity['times_seen'] = existing.get('times_seen', 1) + 1
                opportunity['first_seen'] = existing.get('first_seen')
                
                # Preserve some existing data if new data is empty
                if not opportunity.get('organization') and existing.get('organization'):
                    opportunity['organization'] = existing['organization']
                
                # Update
                response = self.client.table('opportunities').update(opportunity).eq('id', opportunity['id']).execute()
                return {"status": "updated", "id": opportunity['id']}
            else:
                # Insert new
                opportunity['first_seen'] = datetime.now().isoformat()
                opportunity['times_seen'] = 1
                
                response = self.client.table('opportunities').insert(opportunity).execute()
                return {"status": "inserted", "id": opportunity['id']}
                
        except Exception as e:
            logger.error(f"Database error: {e}")
            return {"status": "error", "error": str(e)}
    
    def ingest_from_json(self, json_path: str) -> Dict[str, Any]:
        """Ingest opportunities from JSON file."""
        logger.info(f"Loading data from {json_path}")
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON formats
        if isinstance(data, dict) and 'opportunities' in data:
            opportunities = data['opportunities']
        elif isinstance(data, list):
            opportunities = data
        else:
            opportunities = [data]
        
        logger.info(f"Processing {len(opportunities)} opportunities")
        
        results = {
            'total': len(opportunities),
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Get existing opportunities for deduplication
        existing = []
        if self.use_supabase and self.client:
            try:
                response = self.client.table('opportunities').select('id, title, organization, url').execute()
                existing = response.data
            except:
                pass
        
        for raw_opp in opportunities:
            # Normalize data
            normalized = self.normalize_opportunity(raw_opp)
            
            # Check for duplicates
            duplicates = self.find_duplicates(normalized, existing)
            if duplicates and normalized['source_platform'] != duplicates[0].get('source_platform'):
                # This is a cross-platform duplicate
                logger.info(f"Found duplicate: {normalized['title']} on {normalized['source_platform']}")
                # Store the alternate URL
                if 'alternate_urls' not in duplicates[0]:
                    duplicates[0]['alternate_urls'] = []
                duplicates[0]['alternate_urls'].append(normalized['url'])
                normalized = duplicates[0]  # Use existing record
            
            # Upsert to database
            result = self.upsert_opportunity(normalized)
            
            if result['status'] == 'inserted':
                results['inserted'] += 1
                existing.append(normalized)  # Add to existing for future duplicate checks
            elif result['status'] == 'updated':
                results['updated'] += 1
            elif result['status'] == 'error':
                results['errors'] += 1
            else:
                results['skipped'] += 1
        
        logger.info(f"Ingestion complete: {results}")
        return results
    
    def create_scrape_run(self, platform: str) -> Optional[str]:
        """Create a new scrape run record."""
        if not self.use_supabase or not self.client:
            return None
        
        try:
            data = {
                'source_platform': platform,
                'status': 'running',
                'started_at': datetime.now().isoformat()
            }
            
            response = self.client.table('scrape_runs').insert(data).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Error creating scrape run: {e}")
            return None
    
    def update_scrape_run(self, run_id: str, updates: Dict[str, Any]):
        """Update a scrape run record."""
        if not self.use_supabase or not self.client or not run_id:
            return
        
        try:
            updates['completed_at'] = datetime.now().isoformat()
            updates['status'] = 'completed'
            
            self.client.table('scrape_runs').update(updates).eq('id', run_id).execute()
        except Exception as e:
            logger.error(f"Error updating scrape run: {e}")

if __name__ == "__main__":
    # Test database connection and ingestion
    import sys
    
    db = OpportunityDatabase()
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # Try to find the latest opportunities file
        from pathlib import Path
        data_dir = Path("data")
        if data_dir.exists():
            json_files = sorted(data_dir.glob("opportunities_*.json"))
            if json_files:
                json_file = str(json_files[-1])
            else:
                print("No opportunities JSON files found in data/")
                sys.exit(1)
        else:
            print("No data directory found")
            sys.exit(1)
    
    print(f"Ingesting from: {json_file}")
    results = db.ingest_from_json(json_file)
    
    print("\nIngestion Results:")
    print(f"  Total: {results['total']}")
    print(f"  Inserted: {results['inserted']}")
    print(f"  Updated: {results['updated']}")
    print(f"  Errors: {results['errors']}")
    print(f"  Skipped: {results['skipped']}")