import asyncio
import re
import random
import time
import threading
import urllib3
from urllib.parse import urljoin
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Optional, Union, List, Dict
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from tqdm.asyncio import tqdm as async_tqdm
# playwright
from playwright.async_api import async_playwright, Page
#==================
from .async_crawler import AsyncCrawler
import os
import subprocess
import tempfile


# Vietnam timezone
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

class DantriCrawler(AsyncCrawler):
    MIN_HTML_SIZE = 1000
    MIN_TITLE_LENGTH = 15
    MIN_BODY_PARAGRAPH = 25

    def __init__(self, start: Union[str, date, datetime], # done
                 end: Union[str, date, datetime],  # done
                 output_folder: Optional[str]='data', # done
                 max_workers: int = 5,
                 articles_per_day: int = 5,
                 sleep_range: tuple = (0.3,0.8),
                 incre: bool = True,
                 auto_save : bool = True ): # done
        super().__init__(start, end, output_folder, auto_save)
        self.max_workers = max_workers
        self.articles_per_day = articles_per_day
        self.sleep_min, self.sleep_max = sleep_range
        self.increment = incre


        self.results = []
        self.results_lock = None
        self.seen_ids = set()
        self.quick_date_cache = {}
        self.html_cache = {}
        self.session = None
        
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def _get_data_name(self) -> str:
        return "dantri_press"
    
    @staticmethod
    # convert to date object
    def _to_date(x: Union[str, date, datetime]) -> date:
        if isinstance(x, datetime):
            return x.date()
        if isinstance(x, date):
            return x
        if isinstance(x, str):
            return datetime.fromisoformat(x).date()
        raise ValueError(f"Unsupported date type: {type(x)}")
         
    @staticmethod
    def _next_business_day(d: date) -> date:
      
        wd = d.weekday()
        if wd == 5:  # Sat
            return d + timedelta(days=2)
        if wd == 6:  # Sun
            return d + timedelta(days=1)
        return d
    
    @staticmethod
    def _trading_date_from_ts(local_dt: datetime, cutoff_hour: int = 15) -> date:

        assert local_dt.tzinfo is not None
        d = local_dt.date()
        if local_dt.hour >= cutoff_hour:
            d = d + timedelta(days=1)
        return DantriCrawler._next_business_day(d)    
    

    #=============================================================================================
    def _setup_session(self):
        """Setup requests session"""
        self.session = requests.Session()
        self.session.verify = False
        
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': random.choice(user_agents),
            'Referer': 'https://dantri.com.vn/',
        }
        self.session.headers.update(headers)
    
    def _sleep(self):
        # randomize sleeping time
        time.sleep(random.uniform(self.sleep_min, self.sleep_max))
    
    def _get_content_with_url(self, url: str, timeout: int = 15) -> Optional[str]:
        # http
        for attempt in range(3):
            try:
                self._sleep()
                r = self.session.get(url, timeout=timeout, allow_redirects=True)
                if r.status_code == 200 and r.text:
                    r.encoding = "utf-8"
                    return r.text
                if r.status_code in (403, 429):
                    time.sleep(1.5 + attempt)
                    continue
            except Exception:
                if attempt < 2:
                    time.sleep(1.0 + attempt * 0.5)
                continue
        return None    

    def _get_content_with_curl(self, url: str) -> Optional[str]:
       # if http fails
        if '#' in url:
            url = url.split('#')[0]
        if not url.startswith('http'):
            return None
        try:
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.html') as temp_file:
                temp_filename = temp_file.name
            curl_command = [
                'curl', '-s', '-L', '--compressed', '--max-time', '15',
                '--user-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                '--header', 'Accept: text/html,application/xhtml+xml,application/xml',
                '--referer', 'https://dantri.com.vn/', '--output', temp_filename, url
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True, timeout=20)
            if result.returncode == 0:
                with open(temp_filename, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                os.unlink(temp_filename)
                if len(content) > 1000:
                    return content
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
        except Exception:
            pass
        return None
    
    def _get_content_enhanced(self, url: str) -> Optional[str]:
       
        content = self._get_content_with_url(url)
        if content:
            return content
        return self._get_content_with_curl(url) 
    
    
   
    @staticmethod
    def _extract_article_id(url: str) -> str:
        """Extract ID from URL"""
        m = re.search(r'-(\d+)\.htm', url)
        return m.group(1) if m else url
    
    def _parse_published_ts(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Parse article timestamp from HTML"""
        # 1) time.author-time with datetime attribute
        date_element = soup.select_one("time.author-time")
        if date_element and date_element.has_attr('datetime'):
            date_str = date_element['datetime'].strip().replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=VN_TZ)
                return dt.astimezone(VN_TZ)
            except Exception:
                pass
        
        # 2) span.date
        date_element = soup.select_one("span.date")
        if date_element:
            raw = date_element.get_text(strip=True)
            m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4}).*?(\d{1,2}):(\d{2})', raw)
            if m:
                dd, mth, y, hh, mm = map(int, m.groups())
                return datetime(y, mth, dd, hh, mm, tzinfo=VN_TZ)
            m2 = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', raw)
            if m2:
                dd, mth, y = map(int, m2.groups())
                return datetime(y, mth, dd, 0, 0, tzinfo=VN_TZ)
        
        # 3) time.time
        date_element = soup.select_one("time.time")
        if date_element and date_element.has_attr('datetime'):
            date_str = date_element.get('datetime').strip().replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=VN_TZ)
                return dt.astimezone(VN_TZ)
            except Exception:
                pass
        
        return None
    
    def _parse_article_from_html(self, html: str, url: str) -> Optional[Dict]:
        """Parse article from HTML"""
        if not html or len(html) < self.MIN_HTML_SIZE:
            return None
        try:
            soup = BeautifulSoup(html, "lxml")
            ts_local = self._parse_published_ts(soup)
            if ts_local is None:
                return None

            title_el = soup.select_one("h1.title-detail, h1.title_news_detail")
            if not title_el:
                title_el = soup.find("h1")
            title = title_el.get_text(strip=True) if title_el else None
            if not title or len(title) < self.MIN_TITLE_LENGTH:
                return None

            body_parts = []
            desc = soup.select_one("p.description, p.lead-detail, p.lead, p.sapo")
            if desc:
                txt = desc.get_text(strip=True)
                if txt:
                    body_parts.append(txt)

            main = soup.select_one("article.fck_detail, div.fck_detail, article.content_detail, div.singular-content")
            if main:
                for p in main.find_all("p"):
                    cls = p.get("class") or []
                    if any("author" in c for c in cls):
                        continue
                    txt = p.get_text(strip=True)
                    if txt and len(txt) > self.MIN_BODY_PARAGRAPH:
                        body_parts.append(txt)
            else:
                for p in soup.select("article p"):
                    txt = p.get_text(strip=True)
                    if txt and len(txt) > self.MIN_BODY_PARAGRAPH:
                        body_parts.append(txt)

            body = "\n\n".join(body_parts).strip() if body_parts else ""
            art_id = self._extract_article_id(url)

            return {
                "trading_date": self._trading_date_from_ts(ts_local).strftime("%Y-%m-%d"),
                "date": ts_local.date().strftime("%Y-%m-%d"),
                "id": art_id,
                "title": title,
                "body": body if body else "N/A",
                "url": url,
            }
        except Exception:
            return None
    
    def _get_links_from_category_page(self, page_url: str) -> List[str]:
        """Extract article links from category page"""
        raw_content = self._get_content_enhanced(page_url)
        if not raw_content:
            return []
        
        soup = BeautifulSoup(raw_content, 'lxml')
        link_elements = soup.select("article a[href*='.htm']")
        base_url = "https://dantri.com.vn/"
        seen = set()
        valid_links = []
        
        for element in link_elements:
            href = element.get('href')
            if not href:
                continue
            
            if '#' in href:
                href = href.split('#')[0]
            
            href = urljoin(base_url, href)
            
            if (href.endswith('.htm') and
                'dantri.com.vn/kinh-doanh/' in href and
                re.search(r'\d{10,}', href) and
                href not in seen):
                valid_links.append(href)
                seen.add(href)
        
        return valid_links
    
    def _quick_date(self, url: str) -> Optional[str]:
    
        if url in self.quick_date_cache:
            return self.quick_date_cache[url]

        html = self._get_content_enhanced(url)
        if not html:
            self.quick_date_cache[url] = None
            return None

        soup = BeautifulSoup(html, "lxml")
        ts_local = self._parse_published_ts(soup)
        if ts_local is None:
            self.quick_date_cache[url] = None
            return None

        d = ts_local.date().strftime("%Y-%m-%d")
        self.quick_date_cache[url] = d
        self.html_cache[url] = html
        return d
    
    def _fetch_and_parse(self, link: str) -> Optional[Dict]:
        """Fetch and parse with cache reuse"""
        html = self.html_cache.pop(link, None)
        if html is None:
            html = self._get_content_enhanced(link)
        return self._parse_article_from_html(html, link)
    
    def _load_existing_ids(self) -> set:
        """Load existing article IDs from CSV for incremental crawling"""
        if not self.incremental:
            return set()
        
        output_filepath = self._get_output_filepath(self._get_data_name())
        if output_filepath is None or not Path(output_filepath).exists():
            return set()
        
        try:
            existing_df = pd.read_csv(output_filepath, usecols=["id"])
            existing_ids = set(existing_df["id"].astype(str))
            print(f"Incremental mode: Loaded {len(existing_ids)} existing article IDs")
            return existing_ids
        except Exception as error:
            print(f"Warning: Could not read existing IDs: {error}")
            return set()
    
    def _crawl_sync(self) -> pd.DataFrame:
        # Setup
        try:
            start_d = self._to_date(self.start_date)
            end_d = self._to_date(self.end_date)
        except (ValueError, TypeError) as e:
            print(f"Invalid date format: {e}")
            return pd.DataFrame()
        
        if start_d < end_d:
            print("START_DATE must >= END_DATE (START=newest, END=oldest)")
            return pd.DataFrame()
        
        # Generate target dates
        target_dates = []
        cur = start_d
        while cur >= end_d:
            target_dates.append(cur.strftime("%Y-%m-%d"))
            cur -= timedelta(days=1)
        
        target_set = set(target_dates)
        print(f"Target: {len(target_set)} dates from {start_d} to {end_d}")
        
        # Load existing IDs
        existing_ids = self._load_existing_ids()
        
        # Initialize state
        date_counter = defaultdict(int)
        self.results.clear()
        self.seen_ids.clear()
        self.quick_date_cache.clear()
        self.html_cache.clear()
        self.results_lock = threading.Lock()
        
        # Setup session
        self._setup_session()
        
        # Print config
        print(f"\n{'='*80}")
        print("DANTRI CRAWLER (Enhanced - Linear + Parallel)")
        print(f"{'='*80}")
        print(f"DATE RANGE : {self.start_date} → {self.end_date}")
        pd_label = "∞" if self.unlimited_per_day else str(self.articles_per_day)
        print(f"PER-DAY    : {pd_label} | MAX_WORKERS: {self.max_workers}")
        print(f"TARGET     : {len(target_set)} days")
        print(f"{'='*80}\n")
        
        # Progress bar
        if self.unlimited_per_day:
            pbar = tqdm(total=None, desc="Crawling", ncols=88)
        else:
            pbar = tqdm(total=len(target_set) * self.articles_per_day, desc="Crawling", ncols=88)
        
        # ===== LINEAR CRAWL WITH PARALLEL PROCESSING =====
        current_d = start_d
        consecutive_empty_days = 0
        MAX_EMPTY_DAYS = 3  # Early stop after 3 consecutive empty days
        
        while current_d >= end_d:
            current_date_str = current_d.strftime('%Y-%m-%d')
            
            # Early stop: Check if quota already met for this date
            if (not self.unlimited_per_day) and (date_counter[current_date_str] >= self.articles_per_day):
                print(f"✓ [{current_date_str}] Quota already met, skipping...")
                current_d -= timedelta(days=1)
                continue
            
            # Early stop: Check if all dates have met quota
            if (not self.unlimited_per_day) and all(date_counter[dd] >= self.articles_per_day for dd in target_set):
                print(f"\n✓ QUOTA REACHED - All target dates satisfied")
                break
            
            current_url = f"https://dantri.com.vn/kinh-doanh/from/{current_date_str}/to/{current_date_str}.htm"
            print(f"\nProcessing date: {current_date_str}")
            
            # Get links from page
            links = self._get_links_from_category_page(current_url)
            
            if not links:
                consecutive_empty_days += 1
                print(f"   ↳ No links found (empty day {consecutive_empty_days}/{MAX_EMPTY_DAYS})")
                
                # Early stop: Too many consecutive empty days
                if consecutive_empty_days >= MAX_EMPTY_DAYS:
                    print(f"\nStopping: {MAX_EMPTY_DAYS} consecutive empty days detected")
                    break
                
                current_d -= timedelta(days=1)
                continue
            
            consecutive_empty_days = 0  # Reset counter
            print(f"   Found {len(links)} links on page")
            
            # ===== MULTI-LAYER FILTERING =====
            # Layer 1: Quick date pre-filter
            print(f"   🔍 Layer 1: Quick date filtering...")
            dates_on_page = []
            for lnk in links:
                d = self._quick_date(lnk)
                if d:
                    dates_on_page.append((lnk, d))
            
            if not dates_on_page:
                print(f"   ↳ No valid dates found, skipping...")
                current_d -= timedelta(days=1)
                continue
            
            print(f"   ✓ Found {len(dates_on_page)} articles with valid dates")
            
            # Layer 2: Filter by target date and quota
            print(f"   🔍 Layer 2: Target date & quota filtering...")
            candidates = []
            for lnk, d in dates_on_page:
                if d not in target_set:
                    continue
                if (not self.unlimited_per_day) and (date_counter[d] >= self.articles_per_day):
                    continue
                candidates.append((lnk, d))
            
            if not candidates:
                print(f"   ↳ No candidates after filtering (quota met or out of range)")
                current_d -= timedelta(days=1)
                continue
            
            print(f"   ✓ {len(candidates)} candidates to crawl")
            
            # Layer 3: Prioritize dates with fewer articles
            if not self.unlimited_per_day:
                candidates.sort(key=lambda x: (date_counter[x[1]], x[1]))
            
            # ===== PARALLEL PROCESSING WITH as_completed() =====
            with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                futures = [ex.submit(self._fetch_and_parse, lnk) for lnk, _ in candidates]
                for fut in as_completed(futures):
                    art = fut.result()
                    if not art:
                        continue
                    
                    d = art["date"]
                    aid = art["id"]
                    
                    # Skip if date not in target range
                    if d not in target_set:
                        continue
                    
                    # Skip if ID already exists
                    if aid in existing_ids or aid in self.seen_ids:
                        continue
                    
                    # Skip if daily quota reached
                    if (not self.unlimited_per_day) and (date_counter[d] >= self.articles_per_day):
                        continue
                    
                    with self.results_lock:
                        self.results.append(art)
                        self.seen_ids.add(aid)
                        existing_ids.add(aid)
                        date_counter[d] += 1
                        pbar.update(1)
                        
                        if self.unlimited_per_day:
                            print(f"  ✓ [{d}] {art['title'][:60]}")
                        else:
                            print(f"  ✓ [{d}] ({date_counter[d]}/{self.articles_per_day}) {art['title'][:60]}")
            
            current_d -= timedelta(days=1)
        
        pbar.close()
        
        # Summary
        got = len(self.results)
        days_cov = len(set(r["date"] for r in self.results))
        print(f"\n{'='*80}")
        print("CRAWLING RESULTS - DANTRI PRESS")
        print(f"{'='*80}")
        if self.unlimited_per_day:
            print(f"Total articles: {got} (no daily limit)")
        else:
            print(f"Total articles: {got} / {len(target_set) * self.articles_per_day} (target)")
        print(f"Days covered: {days_cov} / {len(target_set)} target dates")
        if days_cov > 0:
            coverage_pct = (days_cov / len(target_set)) * 100
            print(f"Coverage: {coverage_pct:.1f}%")
        
        if date_counter:
            dates_with_articles = len([d for d, count in date_counter.items() if count > 0])
            print(f"Dates with articles: {dates_with_articles}")
            if not self.unlimited_per_day:
                dates_full = len([d for d, count in date_counter.items() if count >= self.articles_per_day])
                print(f"Dates meeting quota: {dates_full}")
        
        print(f"{'='*80}\n")
        
        # Save
        if self.results:
            new_df = pd.DataFrame(self.results)
            output_filepath = self._get_output_filepath(self._get_data_name())
            
            if self.auto_save and output_filepath is not None:
                if self.incremental and Path(output_filepath).exists():
                    try:
                        existing_df = pd.read_csv(output_filepath)
                        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                        combined_df = combined_df.sort_values(by=["trading_date", "id"], ascending=[False, True])
                        combined_df = combined_df.drop_duplicates(subset=['id'], keep='first')
                        combined_df.to_csv(output_filepath, index=False, encoding='utf-8-sig')
                        print(f"Saved (merged): {output_filepath}")
                        return combined_df
                    except Exception as e:
                        print(f"Warning: Could not merge: {e}")
                
                new_df.to_csv(output_filepath, index=False, encoding='utf-8-sig')
                print(f"Saved: {output_filepath}")
            else:
                print("ℹauto_save=False, skipping file save")
            
            return new_df
        else:
            print("No articles collected - returning empty DataFrame")
        
        return pd.DataFrame()
    
    async def crawl_async(self) -> pd.DataFrame:
        """Async wrapper for sync implementation"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._crawl_sync)
    
    def __del__(self):
        """Cleanup"""
        try:
            if hasattr(self, "session") and self.session:
                self.session.close()
        except Exception:
            pass