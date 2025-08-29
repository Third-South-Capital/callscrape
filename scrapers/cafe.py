"""
CaFE (CallForEntry.org) scraper for art opportunities.
Uses Selenium to get real platform IDs, falls back to API if needed.
"""

import json
import re
import time
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base import BaseScraper
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.state_mapper import normalize_location

class CafeScraper(BaseScraper):
    """Scraper for CallForEntry.org opportunities."""
    
    def __init__(self, use_selenium: bool = True):
        super().__init__("cafe")
        self.api_url = "https://artist.callforentry.org/festivals-ajax.php"
        self.artist_url = "https://artist.callforentry.org/festivals.php"
        self.use_selenium = use_selenium
        self.driver = None
    
    def setup_driver(self) -> Optional[webdriver.Chrome]:
        """Setup Chrome driver for Selenium."""
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
            self.logger.warning(f"Chrome driver failed: {e}, trying Safari")
            try:
                driver = webdriver.Safari()
                return driver
            except:
                self.logger.error("Could not setup any Selenium driver")
                return None
    
    def get_platform_ids_selenium(self) -> Dict[str, str]:
        """Get real CaFE platform IDs using Selenium."""
        platform_ids = {}
        
        if not self.use_selenium:
            return platform_ids
        
        self.logger.info("Fetching real CaFE platform IDs with Selenium...")
        driver = self.setup_driver()
        
        if not driver:
            self.logger.warning("Selenium not available, using API data only")
            return platform_ids
        
        try:
            driver.get(self.artist_url)
            time.sleep(3)  # Wait for initial load
            
            # Wait for the calls to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "More Info"))
                )
            except:
                self.logger.warning("No 'More Info' links found, page might not have loaded")
            
            # Find all links to festival pages
            links = driver.find_elements(By.XPATH, "//a[contains(@href, 'festivals_unique_info.php?ID=')]")
            self.logger.info(f"Found {len(links)} festival links")
            
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and 'ID=' in href:
                        # Extract the real CaFE ID
                        cafe_id = href.split('ID=')[1].split('&')[0].split('#')[0]
                        
                        # Get the title - might be in the link text or nearby
                        title = link.text or link.get_attribute('title') or ''
                        
                        # Clean up title
                        title = re.sub(r'^More Info\s*\n?\s*About\s+', '', title)
                        title = re.sub(r'\s*\(Opens in new tab\)\s*$', '', title)
                        title = ' '.join(title.split()).strip()
                        
                        if title and cafe_id:
                            # Map title to real platform ID
                            platform_ids[title.lower()] = cafe_id
                            
                except Exception as e:
                    continue
            
            self.logger.info(f"Collected {len(platform_ids)} platform IDs")
            
        finally:
            driver.quit()
        
        return platform_ids
        
    def fetch_opportunities(self) -> List[Dict[str, Any]]:
        """Fetch all active calls from CaFE, combining API data with real platform IDs."""
        opportunities = []
        
        # First, get the real platform IDs via Selenium
        platform_ids = self.get_platform_ids_selenium()
        self.logger.info(f"Got {len(platform_ids)} real platform IDs from Selenium")
        
        # Then fetch from API for complete data
        try:
            response = self.session.post(
                self.api_url,
                data={
                    'start-index': '0',
                    'keyword': '',
                    'entry-fee-min': '',
                    'entry-fee-max': '',
                    'participation-fee-min': '',
                    'participation-fee-max': '',
                    'budget-min': '',
                    'budget-max': '',
                    'sort': '0',
                    'show-only-fair-id': '0'
                },
                headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json, text/javascript, */*; q=0.01'
                }
            )
            
            data = json.loads(response.text)
            
            for item in data.get('results', []):
                # Build location string with proper state names
                city = item.get('fair_city', '')
                state_code = item.get('fair_state', '')
                location = normalize_location(city, state_code)
                
                # Try to find the real CaFE ID from Selenium data
                title_lower = item.get('fair_name', '').lower()
                real_cafe_id = None
                
                # Try different matching strategies
                for selenium_title, selenium_id in platform_ids.items():
                    # Exact match
                    if title_lower == selenium_title:
                        real_cafe_id = selenium_id
                        break
                    # Partial match (one contains the other)
                    elif title_lower in selenium_title or selenium_title in title_lower:
                        real_cafe_id = selenium_id
                        break
                    # First 20 characters match
                    elif len(title_lower) > 20 and len(selenium_title) > 20:
                        if title_lower[:20] == selenium_title[:20]:
                            real_cafe_id = selenium_id
                            break
                
                # Use real ID if found, otherwise fallback to API ID (which won't work for applications)
                if real_cafe_id:
                    cafe_platform_url = f"https://artist.callforentry.org/festivals_unique_info.php?ID={real_cafe_id}"
                    self.logger.debug(f"Matched '{item.get('fair_name', '')[:30]}' to real ID: {real_cafe_id}")
                else:
                    # Fallback - this URL won't work for applications but at least provides a reference
                    cafe_platform_url = f"https://artist.callforentry.org/festivals_unique_info.php?ID={item.get('id', '')}"
                    self.logger.warning(f"No real ID found for '{item.get('fair_name', '')[:30]}', using API ID {item.get('id', '')}")
                
                opportunity = {
                    'id': self.generate_id(str(item.get('id', ''))),
                    'title': item.get('fair_name', ''),
                    'organization': item.get('organization_name', ''),
                    'url': cafe_platform_url,  # This is the CaFE platform application URL
                    'deadline': item.get('fair_deadline', ''),  # Already in YYYY-MM-DD format
                    'location': location,
                    'fee': item.get('entry_fee', ''),
                    'description': item.get('description', ''),
                    
                    # Extra fields specific to CaFE
                    'gallery_url': item.get('fair_url', ''),  # This is the gallery's own website
                    'event_start': item.get('event_start', ''),
                    'event_end': item.get('event_end', ''),
                    'email': item.get('fair_email', ''),
                    'eligibility': item.get('eligibility_text', ''),
                    'awards': item.get('awards_text', ''),
                    'booth_fee': item.get('booth_fee', ''),
                    'commission': item.get('commission', ''),
                    'platform_id': real_cafe_id if real_cafe_id else str(item.get('id', '')),  # Store the real platform ID
                    'has_real_id': bool(real_cafe_id)  # Flag to indicate if we have the real ID
                }
                
                opportunities.append(opportunity)
                
        except Exception as e:
            self.logger.error(f"Error fetching CaFE opportunities: {e}")
            
        # Log statistics
        with_real_ids = sum(1 for o in opportunities if o.get('has_real_id', False))
        self.logger.info(f"Fetched {len(opportunities)} CaFE opportunities ({with_real_ids} with real platform IDs)")
            
        return opportunities