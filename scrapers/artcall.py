"""
ArtCall.org scraper for art opportunities.
"""

import re
from typing import List, Dict, Any
from .base import BaseScraper

class ArtCallScraper(BaseScraper):
    """Scraper for ArtCall.org opportunities."""
    
    def __init__(self):
        super().__init__("artcall")
        self.base_url = "https://artcall.org"
        
    def fetch_opportunities(self) -> List[Dict[str, Any]]:
        """Fetch all active calls from ArtCall.org."""
        opportunities = []
        
        soup = self.get_soup(f"{self.base_url}/calls")
        if not soup:
            return opportunities
            
        # Find all call containers
        call_rows = soup.find_all('div', class_='row mb-5')
        
        for row in call_rows:
            try:
                # Extract title and URL
                title_link = row.find('h3')
                if title_link:
                    title_link = title_link.find('a')
                if not title_link:
                    continue
                
                call_url = title_link.get('href', '')
                if not call_url.startswith('http'):
                    call_url = self.base_url + call_url
                    
                call_title = title_link.text.strip()
                
                # Extract deadline
                deadline_text = ''
                deadline_span = row.find('span', class_='h6', string='Entry Deadline:')
                if deadline_span and deadline_span.next_sibling:
                    deadline_text = deadline_span.next_sibling.strip().replace('\u202f', ' ')
                
                # Extract fee
                fee_text = ''
                fee_span = row.find('span', string=re.compile('Entry Fee:'))
                if fee_span and fee_span.next_sibling:
                    fee_text = ' '.join(fee_span.next_sibling.strip().split())
                
                # Extract location
                location = ''
                badge_span = row.find('span', class_='badge bg-info')
                if badge_span:
                    location = badge_span.text.strip()
                
                # Extract eligibility
                eligibility = ''
                elig_span = row.find('span', class_='h6', string='Eligibility:')
                if elig_span and elig_span.next_sibling:
                    eligibility = elig_span.next_sibling.strip()
                
                # Extract organization from subdomain
                org_name = ''
                if '//' in call_url:
                    subdomain = call_url.split('//')[1].split('.')[0]
                    if subdomain != 'www':
                        org_name = subdomain.replace('-', ' ').title()
                
                opportunity = {
                    'id': self.generate_id(call_url),
                    'title': call_title,
                    'organization': org_name,
                    'url': call_url,
                    'deadline': deadline_text,
                    'location': location,
                    'fee': fee_text,
                    'description': '',
                    
                    # Extra fields
                    'eligibility': eligibility
                }
                
                opportunities.append(opportunity)
                
            except Exception as e:
                self.logger.warning(f"Error parsing ArtCall row: {e}")
                continue
                
        return opportunities