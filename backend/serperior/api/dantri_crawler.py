import requests
import time
import random
import ssl
from urllib.parse import urlparse, urljoin
import urllib3
import subprocess
import tempfile
import os
import re
import json
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime, timedelta
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import threading
from .base_crawler import BaseCrawler

class DantriCrawler(BaseCrawler):

    def __init__(self, max_workers=5, field = 'kinh-doanh'):
        # domain of field: 
        # 'kinh-doanh'
        # 'thoi-su'
        # 'phap-luat'
        # 'du-lich'
        # 'bat-dong-san'
        self.field = field
        self.results = []
        self.results_lock = threading.Lock()
        self.max_workers = max_workers
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.session = requests.Session()
        self.session.verify = False
        self._setup_session()

    def _setup_session(self):
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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

    def _get_content_(self, url):
        for attempt in range(2):
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
                if attempt < 1:
                    time.sleep(random.uniform(1, 2))
                continue
        return None

    def _get_content_with_curl(self, url):
        if '#' in url: url = url.split('#')[0]
        if not url.startswith('http'): return None
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
                if len(content) > 1000: return content
            if os.path.exists(temp_filename): os.unlink(temp_filename)
        except Exception:
            pass
        return None

    def _get_content_enhanced(self, url):
        content = self._get_content_(url)
        if content:
            return content
        return self._get_content_with_curl(url)

    @lru_cache(maxsize=128)
    def _parse_date_string(self, date_str: str) -> str:
        match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', date_str)
        if match:
            try:
                date_obj = datetime.strptime(match.group(1), '%d/%m/%Y')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError: pass

        try:
            if '+' in date_str: date_str = date_str.split('+')[0]
            if 'T' in date_str: date_str = date_str.split('T')[0]
            date_obj = datetime.fromisoformat(date_str)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError: pass

        return None

    def _parse_article_from_html(self, html_content: str, url: str) -> dict:
        try:
            if not html_content or len(html_content) < 500: return None
            soup = BeautifulSoup(html_content, 'lxml')
#=============date=========
            publish_date = None
            date_element = soup.select_one("time.author-time")
            if date_element and date_element.has_attr('datetime'):
                date_str = date_element['datetime']
                publish_date = self._parse_date_string(date_str)
            else:
                date_element = soup.select_one("span.date")
                if date_element:
                    date_str = date_element.get_text().strip()
                    publish_date = self._parse_date_string(date_str)
                else:
                    date_element = soup.select_one("time.time")
                    if date_element and date_element.has_attr('datetime'):
                        date_str = date_element.get('datetime')
                        publish_date = self._parse_date_string(date_str)
#=================title===========
            title_detail = None
            title_element = soup.select_one("h1.title-detail, h1.title_news_detail")
            if title_element:
                title_detail = title_element.get_text().strip()

            if not title_detail:
                title_element = soup.find("h1")
                if title_element:
                    title_detail = title_element.get_text().strip()

            if not title_detail or len(title_detail) < 10:
                return None
            
#=========================body=====

            def clean_body_text(body: str) -> str:
                """Loại bỏ tên báo ở đầu body"""
                if not body:
                    return ""
                
                # Loại bỏ (Tên báo) - 
                cleaned = re.sub(r'^\([^)]+\)\s*-\s*', '', body.strip())
                
                return cleaned.strip()


            body_element = soup.select_one("h2.singular-sapo")
            if body_element:
                body_detail = body_element.get_text().strip()
                body_detail = clean_body_text(body_detail)
                
            if not body_element:
                body_detail = title_detail
            if not body_detail:
                return None   


            return {
                "title": title_detail,
                "publish_date": publish_date,
                "body": body_detail
            }
        except Exception:
            return None

    def _get_links_from_category_page(self, page_url: str, num_articles: int = 5) -> list:
        # THAM SỐ: num_articles - số lượng bài báo cần lấy từ trang (mặc định = 5)
        raw_content = self._get_content_enhanced(page_url)

        if raw_content is None:
            return []

        soup = BeautifulSoup(raw_content, 'lxml')
        link_elements = soup.select("article a[href*='.htm']")
        base_url = "https://dantri.com.vn/"
        seen = set()
        valid_links = []

        for element in link_elements:
            href = element.get('href')
            if href:
                if '#' in href:
                    href = href.split('#')[0]

                href = urljoin(base_url, href)

                if (href.endswith('.htm') and
                    f'dantri.com.vn/{self.field}/' in href and
                    re.search(r'\d{10,}', href) and
                    href not in seen):
                    valid_links.append(href)
                    seen.add(href)

                    if len(valid_links) == num_articles:
                        return valid_links

        return valid_links

    def _process_article(self, link, target_dates_set, crawled_dates_counter):
        html_content = self._get_content_enhanced(link)
        if not html_content:
            return None

        article_data = self._parse_article_from_html(html_content, link)
        if not article_data or not article_data.get('publish_date'):
            return None

        date_str = article_data['publish_date']

        if date_str in target_dates_set and crawled_dates_counter.get(date_str, 0) < 5:
            return {
                "date": date_str,
                "title": article_data['title'],
                "body": article_data['body'],
                "url": link
            }
        return None

    def crawl_by_date_range(self, start_date: str, end_date: str, num_articles: int = 5, save: bool = False):
        self.results = []

        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            print("Lỗi: Định dạng ngày không hợp lệ. Vui lòng dùng 'YYYY-MM-DD'.")
            return []

        target_dates = []
        current_d = start_date_obj
        while current_d >= end_date_obj:
            target_dates.append(current_d.strftime('%Y-%m-%d'))
            current_d -= timedelta(days=1)

        target_dates_set = set(target_dates)
        crawled_dates_counter = {date: 0 for date in target_dates_set}

        if not target_dates_set:
            print("Khoảng ngày không hợp lệ.")
            return []

        total_expected = len(target_dates_set) * num_articles
        pbar = tqdm(total=total_expected, desc="Đang thu thập bài báo")

        current_d = start_date_obj

        while current_d >= end_date_obj:
            current_date_str = current_d.strftime('%Y-%m-%d')
            current_url = f"https://dantri.com.vn/{self.field}/from/{current_date_str}/to/{current_date_str}.htm"

            print(f"\nĐang quét trang: {current_url}", flush=True)

            links = self._get_links_from_category_page(current_url, num_articles= num_articles)

            if not links:
                print(f"Không tìm thấy bài báo cho ngày {current_date_str}. Chuyển ngày tiếp.", flush=True)
                current_d -= timedelta(days=1)
                continue

            for link in links:
                result = self._process_article(link, target_dates_set, crawled_dates_counter)

                if result:
                    date_str = result['date']
                    with self.results_lock:
                        if crawled_dates_counter[date_str] < num_articles:
                            crawled_dates_counter[date_str] += 1
                            self.results.append(result)
                            # pbar.update(1)
                            print(f"✓ Tìm thấy [{date_str}] ({crawled_dates_counter[date_str]}/{num_articles}): {result['title'][:60]}...", flush=True)

            current_d -= timedelta(days=1)

        pbar.close()
        print(f"\n--- done ---")
        print(f"Đã crawl được {len(self.results)}/{total_expected} bài báo.")

        # if save True
        if save and self.results:
            df = pd.DataFrame(self.results)
            df.sort_values(by="date", ascending=False, inplace = True)
            output_filename = f"dantri_from_{end_date}_to_{start_date}.csv"
            df.to_csv(output_filename, index=False, encoding='utf-8-sig')
            print(f"\nsaved in file: {output_filename}")

        elif self.results:
            return self.results
        


    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

if __name__ == "__main__":
    END_DATE = "2024-12-15"
    START_DATE = "2024-12-16"
    print(f"Bắt đầu crawl from {START_DATE} to {END_DATE}...")
    crawler = DantriCrawler(field = 'kinh-doanh')
    data = crawler.crawl_by_date_range(
        start_date=START_DATE,
        end_date=END_DATE
    )
    # data is a list of dictionaries: [{'a':1, 'b':2},{'a':2, 'b':3}]
    if data:
        df = pd.DataFrame(data)
        df = df.sort_values(by="date", ascending=False)
        print(df[['date', 'title']])

        output_filename = f"vnexpress_from_{END_DATE}_to_{START_DATE}.csv"
        df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        print(f"\nsaved in file: {output_filename}")
    else:
        print("\nyou failed")            
       