"""
Zapplication.org scraper for art fairs and festivals.
Uses Selenium for JavaScript-heavy content.
"""

import re
import time
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base import BaseScraper

class ZapplicationScraper(BaseScraper):
    """Scraper for Zapplication.org art fair and festival opportunities."""
    
    def __init__(self, max_events_limit: Optional[int] = None):
        super().__init__("zapplication")
        self.base_url = "https://www.zapplication.org"
        self.driver = None
        self.max_events_limit = max_events_limit  # None = scrape all, or set a limit for testing
        
    def setup_driver(self) -> Optional[webdriver.Chrome]:
        """Setup Chrome driver in headless mode."""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {e}")
            # Try Safari as fallback on Mac
            try:
                driver = webdriver.Safari()
                return driver
            except:
                return None
    
    def extract_from_javascript(self, page_source: str) -> Dict[str, Any]:
        """Extract data from JavaScript variables in the page."""
        data = {}
        
        # Extract from _phpVueData.eventGeneralInfo
        general_info_match = re.search(r'_phpVueData\.eventGeneralInfo\s*=\s*"([^"]+)"', page_source)
        if general_info_match:
            general_info = general_info_match.group(1)
            # Unescape the string
            general_info = general_info.replace('\\"', '"').replace('\\/', '/').replace('\\r\\n', '\n')
            
            # Extract Event Dates
            date_patterns = [
                r'Event Dates?:\s*([A-Z][a-z]+\s+\d{1,2}(?:-\d{1,2})?,?\s*\d{4})',
                r'<strong>Event Dates?:\s*([^<]+)</strong>',
                r'Show Dates?:\s*([A-Z][a-z]+\s+\d{1,2}[^<\n]*\d{4})',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, general_info, re.IGNORECASE)
                if match:
                    data['event_dates'] = match.group(1).strip()
                    break
        
        # Try to extract location
        location_match = re.search(r':location="([^"]+)"', page_source)
        if location_match:
            loc = location_match.group(1)
            if not loc.startswith('{{'):
                data['location'] = loc
        
        return data
    
    def extract_event_details(self, driver: webdriver.Chrome, event_id: str) -> Optional[Dict[str, Any]]:
        """Extract complete event data from individual page."""
        url = f"{self.base_url}/event-info.php?ID={event_id}"
        
        try:
            driver.get(url)
            time.sleep(2)  # Wait for Vue.js to render
            
            page_source = driver.page_source
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            event_data = {
                'id': self.generate_id(event_id),
                'zapp_id': event_id,
                'url': url,
                'event_type': 'fair',  # Zapplication is primarily for fairs/festivals
            }
            
            # Extract from JavaScript
            js_data = self.extract_from_javascript(page_source)
            event_data.update(js_data)
            
            # Title from page title
            title_match = re.search(r'<title>ZAPP - Event Information - ([^<]+)</title>', page_source)
            if title_match:
                event_data['title'] = title_match.group(1).strip()
            elif "Application period is closed" not in body_text:
                # Try to find title in body
                lines = body_text.split('\n')
                for line in lines[:10]:  # Check first 10 lines
                    if len(line) > 10 and 'ZAPP' not in line and 'Event Information' not in line:
                        event_data['title'] = line.strip()
                        break
            
            # Application deadline
            deadline_patterns = [
                r'Application Deadline[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                r'Deadline[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                r'Applications? (?:Due|Close)[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
            ]
            
            for pattern in deadline_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    event_data['deadline'] = match.group(1).strip()
                    break
            
            # Fees
            app_fee_match = re.search(r'Application Fee[:\s]+\$?([\d,]+(?:\.\d{2})?)', body_text)
            if app_fee_match:
                event_data['application_fee'] = f"${app_fee_match.group(1)}"
            
            booth_fee_match = re.search(r'Booth Fee[:\s]+\$?([\d,]+(?:\.\d{2})?)', body_text)
            if booth_fee_match:
                event_data['booth_fee'] = f"${booth_fee_match.group(1)}"
            
            # Organization (often the event name contains it)
            if 'title' in event_data:
                # Try to extract org from title (e.g., "Art Festival by XYZ Organization")
                org_match = re.search(r'by\s+(.+)', event_data['title'])
                if org_match:
                    event_data['organization'] = org_match.group(1).strip()
                else:
                    # Use first part of title as org
                    event_data['organization'] = event_data['title'].split('-')[0].strip()
            
            # Only return if we have at least a title
            if 'title' in event_data:
                return event_data
            
        except Exception as e:
            self.logger.warning(f"Error extracting event {event_id}: {e}")
        
        return None
    
    def fetch_opportunities(self) -> List[Dict[str, Any]]:
        """Fetch all active fairs/festivals from Zapplication."""
        opportunities = []
        
        # First get list of event IDs from main page
        self.logger.info("Fetching event list from Zapplication...")
        
        soup = self.get_soup(self.base_url)
        if not soup:
            return opportunities
        
        # Find all event links
        event_links = soup.find_all('a', href=re.compile(r'event-info\.php\?ID=(\d+)'))
        event_ids = []
        
        for link in event_links:
            match = re.search(r'ID=(\d+)', link.get('href', ''))
            if match:
                event_ids.append(match.group(1))
        
        # Remove duplicates
        event_ids = list(dict.fromkeys(event_ids))
        
        self.logger.info(f"Found {len(event_ids)} events to scrape")
        
        if not event_ids:
            return opportunities
        
        # Setup Selenium driver
        self.logger.info("Starting Selenium WebDriver...")
        driver = self.setup_driver()
        
        if not driver:
            self.logger.error("Failed to setup WebDriver - cannot scrape Zapplication")
            return opportunities
        
        try:
            # Use limit if specified, otherwise process all events
            if self.max_events_limit:
                max_events = min(self.max_events_limit, len(event_ids))
                self.logger.info(f"Limiting to {max_events} events (out of {len(event_ids)} total)")
            else:
                max_events = len(event_ids)
            
            self.logger.info(f"Extracting details from {max_events} events (approx {max_events * 3 // 60} minutes)...")
            
            for i, event_id in enumerate(event_ids[:max_events], 1):
                if i % 10 == 0:
                    self.logger.info(f"Progress: {i}/{max_events} events processed")
                
                event_data = self.extract_event_details(driver, event_id)
                
                if event_data:
                    # Normalize to our standard format
                    opportunity = self.normalize_opportunity(event_data)
                    # Keep extra Zapplication-specific fields
                    opportunity['event_dates'] = event_data.get('event_dates', '')
                    opportunity['application_fee'] = event_data.get('application_fee', '')
                    opportunity['booth_fee'] = event_data.get('booth_fee', '')
                    opportunity['event_type'] = 'fair'
                    
                    opportunities.append(opportunity)
                
                # Be polite to the server
                time.sleep(0.5)
                
        finally:
            driver.quit()
            self.logger.info(f"WebDriver closed. Found {len(opportunities)} valid events")
        
        return opportunities