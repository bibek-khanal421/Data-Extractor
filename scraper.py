import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from dotenv import load_dotenv
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import List, Dict
from config import TARGET_SITES
from tqdm import tqdm

load_dotenv()

class VapeScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.products = []
        self.visited_urls = set()
        self.base_domain = None
        self.product_urls = set()
        self.found_urls_lock = threading.Lock()

        self.target_sites = TARGET_SITES

    def is_valid_url(self, url):
        """Check if URL is valid and belongs to the same domain."""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.base_domain if parsed.netloc else False
        except:
            return False

    def is_product_url(self, url, site_name):
        """Check if URL matches the product pattern for the given site."""
        pattern = self.target_sites[site_name]['product_pattern']
        return pattern in url

    def get_page(self, url):
        """Get page content with retry mechanism."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=5)
                response.raise_for_status()
                return response.text
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Error fetching {url}: {str(e)}")
                    return None
                time.sleep(0.5)

    def process_page(self, url, site_name):
        """Process a single page and extract links."""
        if url in self.visited_urls:
            return set(), set()
        
        with self.found_urls_lock:
            self.visited_urls.add(url)
        
        html = self.get_page(url)
        if not html:
            return set(), set()
        
        soup = BeautifulSoup(html, 'html.parser')
        product_links = set()
        category_links = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(self.base_url, href)
            
            if not self.is_valid_url(full_url):
                continue
                
            if self.is_product_url(full_url, site_name):
                product_links.add(full_url)
            elif full_url not in self.visited_urls:
                if any(term in full_url.lower() for term in ['product', 'collection', 'category', 'shop']):
                    category_links.add(full_url)
        
        return product_links, category_links

    def find_product_urls(self, site_name, max_urls=100):
        """Find product URLs for a given site using parallel processing."""
        site_info = self.target_sites[site_name]
        self.base_url = site_info['base_url']
        self.base_domain = urlparse(self.base_url).netloc
        
        
        self.visited_urls = set()
        product_urls = set()
        urls_to_visit = {self.base_url}  
        
        max_workers = 20 
        batch = 50 
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while urls_to_visit and len(product_urls) < max_urls:
                batch_size = min(batch, len(urls_to_visit))  
                current_batch = set(list(urls_to_visit)[:batch_size])
                urls_to_visit = urls_to_visit - current_batch
                
                future_to_url = {
                    executor.submit(self.process_page, url, site_name): url 
                    for url in current_batch
                }
                
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        page_products, page_categories = future.result()
                        
                        new_products = page_products - product_urls
                        if len(product_urls) + len(new_products) > max_urls:
                            remaining = max_urls - len(product_urls)
                            product_urls.update(list(new_products)[:remaining])
                            if len(product_urls) >= max_urls:
                                break
                        else:
                            product_urls.update(new_products)
                        
                        if len(product_urls) < max_urls:
                            urls_to_visit.update(page_categories - self.visited_urls - urls_to_visit) # also ensure not to add what's already in urls_to_visit
                        
                    except Exception as e:
                        print(f"Error processing {url}: {str(e)}")
                
                if len(product_urls) >= max_urls:
                    break
        
        return list(product_urls)

    def extract_slug(self, url):
        """Extract product information from a page."""
        product = {
            'url': url,
            'slug': urlparse(url).path.strip('/'),
        }
        return product

    def scrape_urls(self, urls, site_name):
        """Scrape a list of specific URLs."""
        if not urls:
            return []
        
        site_info = self.target_sites[site_name]
        self.base_url = site_info['base_url']
        self.base_domain = urlparse(self.base_url).netloc
        
        site_dir = f"output/{site_name}"
        os.makedirs(site_dir, exist_ok=True)
        
        
        products = []
        for i, url in tqdm(enumerate(urls, 1)):
            
            html = self.get_page(url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                product_info = self.extract_slug(url)
                
                product_info['site'] = site_name
                
                raw_text = self._extract_raw_text(soup)
                
                product_slug = product_info['slug'].replace('/', '_')
                product_file = f"{site_dir}/{product_slug}.txt"
                with open(product_file, 'w', encoding='utf-8') as f:
                    f.write(f"URL: {url}\n\n")
                    f.write("\nRaw Text Content:\n")
                    f.write(raw_text)
                
                products.append(product_info)
                
            
            time.sleep(1)
        
        return products


    def _extract_raw_text(self, soup: BeautifulSoup) -> str:
        """Extract all text content from the page, preserving structure."""
        for script in soup(["script", "style"]):
            script.decompose()
            
        text_parts = []
        
        title = soup.find('title')
        if title:
            text_parts.append(f"Title: {title.get_text(strip=True)}")
            
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            text_parts.append(f"Meta Description: {meta_desc.get('content', '')}")
            
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|product'))
        if main_content:
            for element in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th']):
                text = element.get_text(strip=True)
                if text:
                    text_parts.append(text)
                    
        specs = soup.find_all(['table', 'dl'])
        for spec in specs:
            text = spec.get_text(strip=True)
            if text:
                text_parts.append(f"Specifications: {text}")
                
        return "\n".join(text_parts)
        
        