"""
ShowSubmit.com scraper for art opportunities.
"""

import re
import time
from typing import List, Dict, Any
from datetime import datetime
from .base import BaseScraper

class ShowSubmitScraper(BaseScraper):
    """Scraper for ShowSubmit.com opportunities."""
    
    def __init__(self):
        super().__init__("showsubmit")
        self.base_url = "https://showsubmit.com"
        
    def fetch_detail_page(self, url: str) -> Dict[str, Any]:
        """Fetch individual show page for complete details."""
        detail_data = {}
        
        try:
            soup = self.get_soup(url)
            if not soup:
                return detail_data
            
            # Extract complete deadline with year
            # Look for patterns like "Deadline is Month Day"
            text = soup.get_text()
            
            # Find deadline patterns
            deadline_patterns = [
                r'Deadline\s+is\s+([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?)',
                r'Deadline[:\s]+([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?)',
            ]
            
            for pattern in deadline_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    deadline_text = match.group(1)
                    
                    # Look for year nearby or add current year
                    year_pattern = r'([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})'
                    year_matches = re.findall(year_pattern, text)
                    
                    # Try to find matching date with year
                    deadline_month = deadline_text.split()[0].lower()
                    for full_date in year_matches:
                        if deadline_month in full_date.lower():
                            detail_data['deadline'] = full_date
                            break
                    
                    # If no year found, add current/next year
                    if 'deadline' not in detail_data:
                        current_year = datetime.now().year
                        # Simple heuristic: if month has passed, use next year
                        months = ['january', 'february', 'march', 'april', 'may', 'june',
                                 'july', 'august', 'september', 'october', 'november', 'december']
                        current_month = datetime.now().month
                        deadline_month_num = months.index(deadline_month) + 1 if deadline_month in months else current_month
                        
                        if deadline_month_num < current_month:
                            current_year += 1
                        
                        detail_data['deadline'] = f"{deadline_text}, {current_year}"
                    break
            
            # Extract entry fees
            fee_patterns = [
                r'\$(\d+(?:\.\d{2})?)',  # Any dollar amount
                r'Entry [Ff]ee[:\s]*\$?(\d+)',
                r'[Ff]ee[:\s]*\$?(\d+)',
            ]
            
            for pattern in fee_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    # Take the first fee found
                    detail_data['fee'] = f"${matches[0]}"
                    break
            
            # Extract location if available
            location_patterns = [
                r'Location[:\s]*([^,\n]+)',
                r'Gallery[:\s]*([^,\n]+)',
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    detail_data['location'] = match.group(1).strip()
                    break
            
            # Extract description - get the main content paragraphs
            description_parts = []
            
            # Look for main content paragraphs
            main_content = soup.find('div', class_='show-detail') or soup.find('div', class_='content') or soup
            paragraphs = main_content.find_all('p')
            
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                # Skip navigation/header paragraphs
                if p_text and len(p_text) > 50 and not any(skip in p_text.lower() for skip in ['deadline', 'entry fee', 'email']):
                    description_parts.append(p_text)
            
            # If we didn't find good paragraphs, get all text
            if not description_parts:
                # Get all text but clean it up
                all_text = soup.get_text(separator=' ', strip=True)
                # Take a chunk from the middle (skip header/footer)
                if len(all_text) > 200:
                    description_parts = [all_text[100:800]]
            
            if description_parts:
                detail_data['description'] = ' '.join(description_parts[:3])  # Take first 3 paragraphs
                    
        except Exception as e:
            self.logger.warning(f"Error fetching detail page {url}: {e}")
            
        return detail_data
    
    def fetch_opportunities(self) -> List[Dict[str, Any]]:
        """Fetch all active calls from ShowSubmit."""
        opportunities = []
        
        # Use the correct URL: /open-calls not /calls
        soup = self.get_soup(f"{self.base_url}/open-calls")
        if not soup:
            return opportunities
            
        current_year = datetime.now().year
        
        # Find all show links
        show_links = soup.find_all('a', href=lambda h: h and '/show/' in h)
        
        # Process unique shows (avoid duplicates from multiple links to same show)
        processed_urls = set()
        
        for link in show_links:
            try:
                url = link.get('href', '')
                if not url or url in processed_urls:
                    continue
                    
                if not url.startswith('http'):
                    url = self.base_url + url
                    
                processed_urls.add(url)
                
                # Navigate up from the link to find the container with all info
                container = link
                for _ in range(5):  # Go up max 5 levels
                    container = container.parent
                    if not container:
                        break
                    
                    # Check if we found the right container with org and title
                    if container.find('p', class_='org-heading') and container.find('p', class_='show-title'):
                        break
                
                if not container:
                    continue
                
                # Extract title
                title = ''
                title_elem = container.find('p', class_='show-title')
                if title_elem:
                    title = title_elem.text.strip()
                
                # Extract organization
                org = ''
                org_elem = container.find('p', class_='org-heading')
                if org_elem:
                    org = org_elem.text.strip()
                
                # Extract deadline - look for text containing "Deadline:"
                deadline = ''
                deadline_text = container.find(text=lambda t: t and 'Deadline:' in t)
                if deadline_text:
                    # Get the next sibling or parent's text
                    deadline_elem = deadline_text.parent
                    if deadline_elem:
                        deadline = deadline_elem.text.replace('Deadline:', '').strip()
                        # Add current year if not present
                        if deadline and str(current_year) not in deadline:
                            deadline = f"{deadline}, {current_year}"
                
                # Extract location - often in the org-heading or nearby
                location = ''
                # Sometimes location is part of org text or in a separate element
                
                # Extract fee - look for entry fee info
                fee = ''
                fee_text = container.find(text=lambda t: t and '$' in t if t else False)
                if fee_text:
                    fee = fee_text.strip()
                
                # Start with basic data from listing page
                opportunity = {
                    'id': self.generate_id(url),
                    'title': title,
                    'organization': org,
                    'url': url,
                    'deadline': deadline,
                    'location': location,
                    'fee': fee,
                    'description': ''
                }
                
                # Fetch detail page for complete data
                if url:
                    self.logger.debug(f"Fetching details for: {title}")
                    time.sleep(0.3)  # Be polite to the server
                    detail_data = self.fetch_detail_page(url)
                    
                    # Update with detail data (overwrites basic data if found)
                    for key, value in detail_data.items():
                        if value:  # Only update if we got a value
                            opportunity[key] = value
                
                # Only add if we have at least a title
                if title:
                    opportunities.append(opportunity)
                
            except Exception as e:
                self.logger.warning(f"Error parsing ShowSubmit link: {e}")
                continue
                
        return opportunities