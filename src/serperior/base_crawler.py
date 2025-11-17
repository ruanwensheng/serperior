from abc import ABC, abstractmethod
import requests
import random
import urllib3
import subprocess
import tempfile
import os
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set
from bs4 import BeautifulSoup
from functools import lru_cache
import time
import re


class BaseCrawler(ABC):

    def __init__(self, max_workers: int = 5):
        self.results: List[Dict] = []
        self.results_lock = threading.Lock()
        self.max_workers = max_workers
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.session = requests.Session()
        self.session.verify = False
        self._setup_session()

    def _setup_session(self) -> None:
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
        }
        self.session.headers.update(headers)

    def _get_content_(self, url: str, max_retries: int = 2) -> Optional[str]:
        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(0.3, 0.8))
                response = self.session.get(url, timeout=15, allow_redirects=True)
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    return response.text
                elif response.status_code == 403:
                    time.sleep(random.uniform(1, 2))
                    continue
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(1, 2))
                continue
        return None

    def _get_content_with_curl(self, url: str) -> Optional[str]:
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
                '--output', temp_filename, url
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
        content = self._get_content_(url)
        if content:
            return content
        return self._get_content_with_curl(url)

    @lru_cache(maxsize=128)
    def _parse_date_string(self, date_str: str) -> Optional[str]:
        match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', date_str)
        if match:
            try:
                date_obj = datetime.strptime(match.group(1), '%d/%m/%Y')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass
        try:
            if '+' in date_str:
                date_str = date_str.split('+')[0]
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
            date_obj = datetime.fromisoformat(date_str)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            pass
        return None

    def _generate_date_range(self, start_date: str, end_date: str) -> List[str]:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Invalid date format. Please use 'YYYY-MM-DD'.")
        dates = []
        current_d = start_date_obj
        while current_d >= end_date_obj:
            dates.append(current_d.strftime('%Y-%m-%d'))
            current_d -= timedelta(days=1)
        return dates

    @abstractmethod
    def _parse_article_from_html(self, html_content: str, url: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def _get_links_from_category_page(self, page_url: str, num_articles: int = 5) -> List[str]:
        pass

    @abstractmethod
    def _process_article(self, link: str, target_dates_set: Set[str], 
                        crawled_dates_counter: Dict[str, int]) -> Optional[Dict]:
        pass

    @abstractmethod
    def crawl_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        pass

    def clear_results(self) -> None:
        with self.results_lock:
            self.results.clear()

    def get_results(self) -> List[Dict]:
        with self.results_lock:
            return self.results.copy()

    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()