"""
Base scraper class with shared functionality for all art call platforms.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
import json
import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.fee_normalizer import normalize_fee

class BaseScraper(ABC):
    """Base class for all art opportunity scrapers."""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def fetch_opportunities(self) -> List[Dict[str, Any]]:
        """Fetch opportunities from the platform. Must be implemented by subclasses."""
        pass
    
    def generate_id(self, unique_string: str) -> str:
        """Generate a unique ID for an opportunity."""
        return hashlib.md5(f"{self.platform_name}_{unique_string}".encode()).hexdigest()[:12]
    
    def parse_deadline(self, deadline_text: str) -> Optional[str]:
        """Parse deadline text into ISO format. Override for platform-specific parsing."""
        # Basic implementation - subclasses can override
        return deadline_text.strip() if deadline_text else None
    
    def normalize_opportunity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize opportunity data to common schema."""
        # Normalize fee if present
        fee = raw_data.get('fee', '')
        if fee:
            fee = normalize_fee(fee)
        
        return {
            'id': raw_data.get('id', ''),
            'platform': self.platform_name,
            'title': raw_data.get('title', ''),
            'organization': raw_data.get('organization', ''),
            'deadline': raw_data.get('deadline', ''),
            'url': raw_data.get('url', ''),
            'location': raw_data.get('location', ''),
            'fee': fee,
            'description': raw_data.get('description', ''),
            'scraped_at': datetime.now().isoformat(),
            'raw_data': raw_data  # Keep original for reference
        }
    
    def save_to_file(self, opportunities: List[Dict], filename: str = None):
        """Save opportunities to JSON file."""
        if not filename:
            filename = f"{self.platform_name}_opportunities_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(filename, 'w') as f:
            json.dump(opportunities, f, indent=2, default=str)
        
        self.logger.info(f"Saved {len(opportunities)} opportunities to {filename}")
        return filename
    
    def get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup object from URL."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    def run(self) -> List[Dict[str, Any]]:
        """Main execution method."""
        self.logger.info(f"Starting {self.platform_name} scraper...")
        
        try:
            opportunities = self.fetch_opportunities()
            normalized = [self.normalize_opportunity(opp) for opp in opportunities]
            
            self.logger.info(f"Found {len(normalized)} opportunities from {self.platform_name}")
            return normalized
            
        except Exception as e:
            self.logger.error(f"Error in {self.platform_name} scraper: {e}")
            return []