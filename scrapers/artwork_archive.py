"""
ArtworkArchive.com scraper for art opportunities.
"""

import re
import time
from typing import List, Dict, Any, Optional
from .base import BaseScraper

class ArtworkArchiveScraper(BaseScraper):
    """Scraper for ArtworkArchive.com opportunities."""
    
    def __init__(self, fetch_details: bool = False):
        super().__init__("artwork_archive")
        self.base_url = "https://www.artworkarchive.com"
        self.fetch_details = fetch_details  # Whether to fetch individual pages for org names
    
    def fetch_detail_page(self, url: str) -> Dict[str, Any]:
        """Fetch individual page to extract organization and original source URL."""
        detail_data = {}
        
        try:
            soup = self.get_soup(url)
            if not soup:
                return detail_data
            
            # Look for Apply button which often has the original source
            apply_button = soup.find('a', string=re.compile('Apply', re.I))
            if apply_button:
                apply_url = apply_button.get('href', '')
                if apply_url and apply_url.startswith('http'):
                    detail_data['original_source_url'] = apply_url
                    
                    # Try to infer organization from the domain
                    domain = apply_url.split('//')[1].split('/')[0]
                    
                    # Clean up domain to get org name
                    if 'callforentry.org' in domain:
                        subdomain = domain.split('.')[0]
                        if subdomain and subdomain != 'artist':
                            detail_data['organization'] = subdomain.replace('-', ' ').title()
                    elif 'artcall.org' in domain:
                        subdomain = domain.split('.')[0]
                        if subdomain:
                            detail_data['organization'] = subdomain.replace('-', ' ').title()
                    else:
                        # Use domain name as org
                        if domain.startswith('www.'):
                            domain = domain[4:]
                        org_name = domain.split('.')[0]
                        if org_name and org_name.lower() not in ['www', 'w']:
                            org_name = org_name.replace('-', ' ').replace('_', ' ')
                            # Handle camelCase
                            org_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', org_name)
                            detail_data['organization'] = org_name.title()
            
            # Also try to find organization in the page content
            if 'organization' not in detail_data:
                # Look for patterns like "by Organization Name"
                org_patterns = [
                    r'(?:by|from|presented by)\s+([A-Z][^,\n]{2,50})',
                    r'Organization:\s*([^,\n]+)',
                ]
                
                page_text = soup.get_text()
                for pattern in org_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        detail_data['organization'] = match.group(1).strip()
                        break
                        
        except Exception as e:
            self.logger.warning(f"Error fetching detail page {url}: {e}")
        
        return detail_data
        
    def fetch_opportunities(self) -> List[Dict[str, Any]]:
        """Fetch all active calls from ArtworkArchive."""
        opportunities = []
        page = 1
        max_pages = 20  # Increase to get more opportunities like before
        
        while page <= max_pages:
            try:
                # Construct URL for pagination
                url = f"{self.base_url}/call-for-entry"
                if page > 1:
                    url += f"?page={page}"
                
                soup = self.get_soup(url)
                if not soup:
                    break
                
                # Find all opportunity containers
                containers = soup.find_all('div', class_='opportunity-container')
                
                if not containers:
                    self.logger.debug(f"No more opportunities found on page {page}")
                    break
                
                self.logger.debug(f"Found {len(containers)} opportunities on page {page}")
                
                for container in containers:
                    try:
                        # The container is usually wrapped in an anchor tag
                        parent_link = container.find_parent('a')
                        if not parent_link:
                            # Try immediate parent
                            if container.parent and container.parent.name == 'a':
                                parent_link = container.parent
                        
                        call_url = ''
                        if parent_link:
                            call_url = parent_link.get('href', '')
                            if call_url and not call_url.startswith('http'):
                                call_url = self.base_url + call_url
                        
                        # Extract title - they use h2 tags
                        title = ''
                        title_elem = container.find('h2')
                        if not title_elem:
                            title_elem = container.find('h3')
                        if not title_elem:
                            title_elem = container.find('h4')
                        if title_elem:
                            title = title_elem.text.strip()
                        
                        # Extract organization
                        org = ''
                        org_elem = container.find('p', class_='text-sm')
                        if org_elem:
                            org = org_elem.text.strip()
                        
                        # Extract deadline - in p.opportunity-date
                        deadline = ''
                        deadline_elem = container.find('p', class_='opportunity-date')
                        if deadline_elem:
                            # Get just the date part, not the "Ends today" part
                            deadline_text = deadline_elem.text.strip()
                            # Split by newline and take first part
                            if '\n' in deadline_text:
                                deadline = deadline_text.split('\n')[0].strip()
                            else:
                                deadline = deadline_text
                        
                        # Extract location
                        location = ''
                        location_elem = container.find('span', string=re.compile('Location'))
                        if location_elem:
                            if location_elem.next_sibling:
                                location = str(location_elem.next_sibling).strip()
                            elif location_elem.parent:
                                location_text = location_elem.parent.text
                                location = location_text.replace('Location', '').strip()
                        
                        # Extract fee
                        fee = ''
                        fee_elem = container.find('span', string=re.compile('Fee'))
                        if fee_elem:
                            if fee_elem.next_sibling:
                                fee = str(fee_elem.next_sibling).strip()
                            elif fee_elem.parent:
                                fee_text = fee_elem.parent.text
                                fee = fee_text.replace('Entry Fee', '').replace('Fee', '').strip()
                        
                        # Extract type
                        opp_type = ''
                        type_elem = container.find('span', class_='badge')
                        if type_elem:
                            opp_type = type_elem.text.strip()
                        
                        opportunity = {
                            'id': self.generate_id(call_url or title),
                            'title': title,
                            'organization': org,
                            'url': call_url,
                            'deadline': deadline,
                            'location': location,
                            'fee': fee,
                            'description': '',
                            
                            # Extra fields
                            'opportunity_type': opp_type
                        }
                        
                        # Fetch detail page if enabled and URL exists
                        if self.fetch_details and call_url:
                            self.logger.debug(f"Fetching details for: {title}")
                            time.sleep(0.3)  # Be polite
                            detail_data = self.fetch_detail_page(call_url)
                            
                            # Update with detail data
                            for key, value in detail_data.items():
                                if value and not opportunity.get(key):
                                    opportunity[key] = value
                        
                        # Only add if we have at least a title
                        if title:
                            opportunities.append(opportunity)
                        
                    except Exception as e:
                        self.logger.warning(f"Error parsing ArtworkArchive container: {e}")
                        continue
                
                # Move to next page
                page += 1
                
                # Stop if we found no opportunities (even if max pages not reached)
                if len(containers) == 0:
                    break
                
            except Exception as e:
                self.logger.error(f"Error fetching ArtworkArchive page {page}: {e}")
                break
        
        return opportunities