#!/usr/bin/env python3
"""
Rahatemlak.az Real Estate Scraper - All-in-One Version
Async scraper with crash recovery, checkpoint/resume, and incremental CSV saving

Requirements:
    pip install beautifulsoup4 aiohttp lxml

Usage:
    python rahatemlak_scraper.py

Features:
    - Async/concurrent scraping with aiohttp
    - Crash-proof with checkpoint/resume
    - Incremental CSV saving (no data loss)
    - Automatic retry of failed URLs
    - Graceful shutdown handling
    - Progress logging
"""

# ======================== CONFIGURATION ========================
# Edit these settings before running

START_PAGE = 1              # Starting page number
END_PAGE = 415               # Ending page number (set higher for more data)
CATEGORY = "alqi-satqi"     # "alqi-satqi" (for sale) or "kiraye" (for rent)
MAX_CONCURRENT = 5          # Number of concurrent requests (3-10 recommended)
BATCH_SIZE = 10             # Number of listings per batch (5-20 recommended)

# File names
CSV_OUTPUT = "properties.csv"
CHECKPOINT_FILE = "checkpoint.pkl"
LOG_FILE = "scraper.log"
FAILED_URLS_FILE = "failed_urls.txt"

# Advanced settings (usually don't need to change)
REQUEST_TIMEOUT = 30        # Seconds
BATCH_DELAY = 2             # Seconds between batches
PAGE_DELAY = 3              # Seconds between pages

# ===============================================================

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import csv
import json
import logging
import signal
import sys
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin
import re
from datetime import datetime
from pathlib import Path
import pickle
from dataclasses import dataclass, field


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ScraperState:
    """Maintains scraper state for checkpoint/resume"""
    processed_urls: Set[str] = field(default_factory=set)
    failed_urls: Set[str] = field(default_factory=set)
    current_page: int = 1
    total_properties: int = 0
    last_checkpoint: str = ""


class RahatemlakScraper:
    """Async scraper for rahatemlak.az with crash recovery"""

    BASE_URL = "https://rahatemlak.az"

    def __init__(self):
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self.state = self.load_checkpoint()
        self.shutdown_flag = False
        self.csv_lock = asyncio.Lock()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'DNT': '1',
        }

        self._init_csv()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.warning(f"\n{'='*60}")
        logger.warning(f"Shutdown signal received. Saving progress...")
        logger.warning(f"{'='*60}")
        self.shutdown_flag = True
        self.save_checkpoint()

    def load_checkpoint(self) -> ScraperState:
        """Load checkpoint from file if exists"""
        if Path(CHECKPOINT_FILE).exists():
            try:
                with open(CHECKPOINT_FILE, 'rb') as f:
                    state = pickle.load(f)
                logger.info(f"✓ Checkpoint loaded: {len(state.processed_urls)} URLs processed")
                logger.info(f"  → Resuming from page {state.current_page}")
                return state
            except Exception as e:
                logger.error(f"Error loading checkpoint: {e}")
        return ScraperState()

    def save_checkpoint(self):
        """Save current state"""
        try:
            self.state.last_checkpoint = datetime.now().isoformat()
            with open(CHECKPOINT_FILE, 'wb') as f:
                pickle.dump(self.state, f)
            logger.info(f"✓ Checkpoint saved: {self.state.total_properties} properties scraped")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")

    def _init_csv(self):
        """Initialize CSV file with headers"""
        if not Path(CSV_OUTPUT).exists():
            headers = [
                'property_id', 'url', 'title', 'price', 'price_per_m2',
                'property_number', 'view_count', 'date_added', 'description',
                'property_type', 'floor', 'rooms', 'area', 'document',
                'city', 'district', 'settlement', 'address',
                'features', 'author_name', 'author_type',
                'phone', 'phone_full', 'image_count', 'scraped_at'
            ]
            with open(CSV_OUTPUT, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
            logger.info(f"✓ CSV initialized: {CSV_OUTPUT}")

    async def append_to_csv(self, data: Dict):
        """Append property to CSV (thread-safe)"""
        async with self.csv_lock:
            try:
                flat_data = {
                    'property_id': data.get('property_id'),
                    'url': data.get('url'),
                    'title': data.get('title'),
                    'price': data.get('price'),
                    'price_per_m2': data.get('price_per_m2'),
                    'property_number': data.get('property_number'),
                    'view_count': data.get('view_count'),
                    'date_added': data.get('date_added'),
                    'description': data.get('description'),
                    'property_type': data.get('general_info', {}).get('Əmlak növü'),
                    'floor': data.get('general_info', {}).get('Mərtəbə'),
                    'rooms': data.get('general_info', {}).get('Otaq'),
                    'area': data.get('general_info', {}).get('Sahə'),
                    'document': data.get('general_info', {}).get('Çıxarış'),
                    'city': data.get('location_info', {}).get('Şəhər'),
                    'district': data.get('location_info', {}).get('Rayon'),
                    'settlement': data.get('location_info', {}).get('Qəsəbə'),
                    'address': data.get('location_info', {}).get('Ünvan'),
                    'features': '; '.join(data.get('features', [])),
                    'author_name': data.get('author_name'),
                    'author_type': data.get('author_type'),
                    'phone': data.get('phone'),
                    'phone_full': data.get('phone_full'),
                    'image_count': len(data.get('images', [])),
                    'scraped_at': data.get('scraped_at'),
                }

                with open(CSV_OUTPUT, 'a', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=flat_data.keys())
                    writer.writerow(flat_data)

            except Exception as e:
                logger.error(f"Error writing to CSV: {e}")

    async def get_listing_urls(self, session: aiohttp.ClientSession, page: int) -> List[str]:
        """Get property URLs from a listings page"""
        url = f"{self.BASE_URL}/{CATEGORY}?page={page}"
        logger.info(f"Fetching page {page}...")

        try:
            async with self.semaphore:
                async with session.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT) as response:
                    html = await response.text()

            soup = BeautifulSoup(html, 'lxml')
            links = []

            for card in soup.find_all('a', href=re.compile(r'/elan/\d+')):
                href = card.get('href')
                if href and '/elan/' in href:
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self.state.processed_urls and full_url not in links:
                        links.append(full_url)

            logger.info(f"  → Found {len(links)} new properties on page {page}")
            return links

        except Exception as e:
            logger.error(f"Error fetching page {page}: {e}")
            return []

    async def extract_property(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        """Extract property details"""
        if self.shutdown_flag:
            return None

        try:
            async with self.semaphore:
                async with session.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT) as response:
                    html = await response.text()

            soup = BeautifulSoup(html, 'lxml')

            # Extract CSRF token for phone fetch
            csrf_token = None
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                csrf_token = csrf_meta.get('content')

            # Property ID
            property_id = re.search(r'/elan/(\d+)', url)
            property_id = property_id.group(1) if property_id else None

            # Basic info
            title = soup.find('h1')
            title = title.text.strip() if title else None

            price_elem = soup.find('div', class_='price-value')
            price = price_elem.text.strip() if price_elem else None

            price_m2_elem = soup.find('div', class_='price-part')
            price_m2 = price_m2_elem.text.strip() if price_m2_elem else None

            # Detail lists
            view_count = property_number = date_added = None
            for detail in soup.find_all('div', class_='detail-list'):
                title_div = detail.find('div', class_='detail-list-title')
                text_div = detail.find('div', class_='detail-list-text')
                if not (title_div and text_div):
                    continue
                title_text = title_div.text.strip()
                if 'Baxış' in title_text:
                    view_count = text_div.text.strip()
                elif 'nömrəsi' in title_text:
                    property_number = text_div.text.strip()
                elif 'Əlavə' in title_text:
                    date_added = text_div.text.strip()

            # General info
            general_info = {}
            for box in soup.find_all('div', class_='overview-box'):
                t = box.find('div', class_='overview-box-content-title')
                v = box.find('div', class_='overview-box-content-text')
                if t and v:
                    general_info[t.text.strip()] = v.text.strip()

            # Description
            desc_elem = soup.find('div', class_='text-box')
            description = desc_elem.get_text(separator=' ', strip=True) if desc_elem else None

            # Location
            location_info = {}
            for box in soup.find_all('div', class_='location-box'):
                t = box.find('div', class_='location-box-title')
                v = box.find('div', class_='location-box-text')
                if t and v:
                    location_info[t.text.strip().rstrip(':')] = v.text.strip()

            # Images
            images = []
            for img in soup.find_all('img', class_='lazyload'):
                src = img.get('data-src') or img.get('src')
                if src and 'property' in src and src not in images:
                    images.append(src)

            # Features
            features = []
            for span in soup.find_all('span', class_=['bg-document', 'bg-mortgage', 'bg-repair']):
                feat = span.get('data-info')
                if feat:
                    features.append(feat)

            # Author
            author_name = author_type = None
            elem = soup.find('div', class_='author-content-name')
            if elem:
                author_name = elem.text.strip()
            elem = soup.find('div', class_='author-content-type')
            if elem:
                author_type = elem.text.strip()

            data = {
                'property_id': property_id,
                'url': url,
                'title': title,
                'price': price,
                'price_per_m2': price_m2,
                'property_number': property_number,
                'view_count': view_count,
                'date_added': date_added,
                'description': description,
                'general_info': general_info,
                'location_info': location_info,
                'features': features,
                'images': images,
                'author_name': author_name,
                'author_type': author_type,
                'scraped_at': datetime.now().isoformat()
            }

            # Get phone
            if property_id and csrf_token:
                phone = await self.get_phone(session, property_id, url, csrf_token)
                if phone:
                    data.update(phone)

            return data

        except Exception as e:
            logger.error(f"Error extracting {url}: {e}")
            self.state.failed_urls.add(url)
            return None

    async def get_phone(self, session: aiohttp.ClientSession, prop_id: str, referer: str, csrf_token: str) -> Optional[Dict]:
        """Get phone via AJAX"""
        try:
            headers = {
                **self.headers,
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-TOKEN': csrf_token,
                'Referer': referer,
                'Origin': self.BASE_URL,
            }

            async with self.semaphore:
                async with session.post(
                    f"{self.BASE_URL}/ajax/property/view-phone",
                    data={'id': prop_id},
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('status'):
                            return {
                                'phone': result.get('phone'),
                                'phone_full': result.get('phone_full')
                            }
                    else:
                        logger.debug(f"Phone fetch status {response.status} for {prop_id}")
        except Exception as e:
            logger.debug(f"Phone fetch failed for {prop_id}: {e}")
        return None

    async def process_listing(self, session: aiohttp.ClientSession, url: str):
        """Process single listing"""
        if self.shutdown_flag:
            return

        try:
            data = await self.extract_property(session, url)
            if data:
                await self.append_to_csv(data)
                self.state.processed_urls.add(url)
                self.state.total_properties += 1

                logger.info(f"  ✓ [{self.state.total_properties}] Property {data.get('property_id')}")

                # Checkpoint every 10
                if self.state.total_properties % 10 == 0:
                    self.save_checkpoint()
            else:
                self.state.failed_urls.add(url)

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            self.state.failed_urls.add(url)

    async def scrape(self):
        """Main scraping logic"""
        start_page = max(START_PAGE, self.state.current_page)

        logger.info(f"\n{'='*60}")
        logger.info(f"Starting scraper...")
        logger.info(f"Pages: {start_page} to {END_PAGE}")
        logger.info(f"Category: {CATEGORY}")
        logger.info(f"Concurrency: {MAX_CONCURRENT}")
        logger.info(f"Output: {CSV_OUTPUT}")
        logger.info(f"{'='*60}\n")

        async with aiohttp.ClientSession() as session:
            for page in range(start_page, END_PAGE + 1):
                if self.shutdown_flag:
                    logger.warning("Shutdown requested, stopping...")
                    break

                self.state.current_page = page
                logger.info(f"\n{'─'*60}")
                logger.info(f"PAGE {page}/{END_PAGE}")
                logger.info(f"{'─'*60}")

                # Get URLs
                urls = await self.get_listing_urls(session, page)
                if not urls:
                    logger.warning(f"No new listings on page {page}")
                    continue

                # Process in batches
                for i in range(0, len(urls), BATCH_SIZE):
                    if self.shutdown_flag:
                        break

                    batch = urls[i:i+BATCH_SIZE]
                    logger.info(f"Batch {i//BATCH_SIZE + 1}: Processing {len(batch)} listings...")

                    tasks = [self.process_listing(session, url) for url in batch]
                    await asyncio.gather(*tasks, return_exceptions=True)

                    await asyncio.sleep(BATCH_DELAY)

                self.save_checkpoint()
                await asyncio.sleep(PAGE_DELAY)

        # Save failed URLs
        if self.state.failed_urls:
            with open(FAILED_URLS_FILE, 'w') as f:
                f.write('\n'.join(self.state.failed_urls))
            logger.warning(f"\n{len(self.state.failed_urls)} failed URLs saved to {FAILED_URLS_FILE}")

        logger.info(f"\n{'='*60}")
        logger.info(f"SCRAPING COMPLETED!")
        logger.info(f"Total properties: {self.state.total_properties}")
        logger.info(f"Failed URLs: {len(self.state.failed_urls)}")
        logger.info(f"Data saved to: {CSV_OUTPUT}")
        logger.info(f"{'='*60}\n")

    async def retry_failed(self):
        """Retry failed URLs"""
        if not self.state.failed_urls:
            logger.info("No failed URLs to retry")
            return

        logger.info(f"\nRetrying {len(self.state.failed_urls)} failed URLs...")
        failed_copy = list(self.state.failed_urls)
        self.state.failed_urls.clear()

        async with aiohttp.ClientSession() as session:
            tasks = [self.process_listing(session, url) for url in failed_copy]
            await asyncio.gather(*tasks, return_exceptions=True)

        self.save_checkpoint()
        logger.info(f"Retry complete. Remaining failures: {len(self.state.failed_urls)}")


def main():
    """Main entry point"""
    try:
        scraper = RahatemlakScraper()
        asyncio.run(scraper.scrape())

        # Optional: retry failed
        if scraper.state.failed_urls:
            retry = input("\nRetry failed URLs? (y/n): ")
            if retry.lower() == 'y':
                asyncio.run(scraper.retry_failed())

    except KeyboardInterrupt:
        logger.warning("\n\nInterrupted by user")
    except Exception as e:
        logger.error(f"\nFatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
