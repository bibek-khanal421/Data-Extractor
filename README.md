# Vape Product Scraper

A Python-based web scraper and data processor for vape products. This tool scrapes product information from vape websites, processes the data using LLM (Large Language Model), and outputs structured data in CSV format.

## Features

- Multi-site scraping support
- Automated product URL discovery
- Detailed product information extraction
- LLM-powered data structuring
- CSV output with structured product data
- CLI interface

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure target sites:**
   - Edit `config.py` to add or modify target websites
   - Configure the .env file using .env.sample
   - Each site should have a base URL and product URL pattern

## Usage

### Command Line Interface

Run the script directly:
```bash
python script.py
```

The CLI will guide you through:
1. Selecting a target site
2. Specifying number of URLs to find
3. Choosing how many products to scrape
4. Processing with LLM
5. Saving results to CSV

## Project Structure

```
vape-product-scraper/
├── app.py              # CLI interface
├── scraper.py          # Core scraping functionality
├── attribute_extractor.py    # LLM data processing
├── config.py           # Site configurations
├── requirements.txt    # Project dependencies
└── output/            # Generated output files
    └── {site_name}/   # Site-specific output
    └── structured_products_<uid>.csv/   # Structured csv data
```

## Approach

1. **URL Discovery**
   - Scrapes target websites to find product URLs
   - Uses configurable patterns to identify product pages
   - Supports multiple sites with different structures

2. **Product Scraping**
   - Extracts detailed product information
   - Handles different page layouts
   - Saves raw data as text files

3. **LLM Processing**
   - Processes raw product data
   - Extracts structured information
   - Standardizes data format

4. **Data Output**
   - Generates structured CSV files
   - Includes all extracted product attributes
   - Supports data download

## Configuration

Edit `config.py` to add new sites:
```python
TARGET_SITES = {
    'site_name': {
        'base_url': 'https://example.com',
        'product_url_pattern': 'pattern'
    }
}
```

## Output Format

The CSV output includes:
- Brand
- Model
- Flavor
- Puff Count
- Nicotine Strength
- Battery Capacity
- Coil Type
(Any data not found will be replaced with null value)

## Requirements

- Python 3.8+
- BeautifulSoup4
- Pandas
- Other dependencies in requirements.txt

## Author

Bibek Khanal