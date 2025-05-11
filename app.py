import sys
from config import TARGET_SITES
from scraper import VapeScraper
from attribute_extractor import LLMProcessor
import pandas as pd

def main():
    print("Available sites:")
    for i, site in enumerate(TARGET_SITES.keys()):
        print(f"{i+1}. {site}")
    site_idx = int(input("Select a site by number: ")) - 1
    site_name = list(TARGET_SITES.keys())[site_idx]

    num_urls = int(input("How many product URLs to find? "))

    scraper = VapeScraper()
    print(f"Finding {num_urls} product URLs for {site_name}...")
    urls = scraper.find_product_urls(site_name, max_urls=num_urls)
    print(f"Found {len(urls)} product URLs.")

    no_to_scrape = int(input("How many product pages to scrape? "))

    print("Scraping product pages...")
    products = scraper.scrape_urls(urls[:no_to_scrape], site_name)
    print(f"Scraped {len(products)} products.")
    print("Running LLM processor...")
    llm = LLMProcessor(batch_size=4)
    structured = llm.process_products(products)
    df = llm.save_structured_data(structured)

    print(f"\nSaved structured data to CSV: {df.shape[0]} rows, {df.shape[1]} columns")
    print(df.head())

if __name__ == "__main__":
    main()