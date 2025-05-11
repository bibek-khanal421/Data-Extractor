import os
import json
import pandas as pd
from typing import List, Dict, Callable
import time
from openai import OpenAI, AzureOpenAI
from datetime import datetime
from functools import wraps

def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying operations on error."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"Error in {func.__name__}: {str(e)}")
                        return None
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class LLMProcessor:
    _instance = None
    _client = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LLMProcessor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, batch_size=4):
        if not self._initialized:
            self.batch_size = batch_size
            self._initialize_client()
            self._initialized = True
            
    def _ensure_output_directory(self):
        """Create output directory if it doesn't exist."""
        output_dir = "output"
        if not os.path.exists(output_dir):
            print(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir)
            print("Output directory created successfully")
            
    def _initialize_client(self):
        """Initialize OpenAI or Azure OpenAI client."""
        try:
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            
            if all([azure_api_key, azure_endpoint, azure_deployment]):
                print("Initializing Azure OpenAI client...")
                self._client = AzureOpenAI(
                    api_key=azure_api_key,
                    api_version="2024-02-15-preview",
                    azure_endpoint=azure_endpoint
                )
                self._deployment = azure_deployment
                print("Azure OpenAI client initialized successfully")
                return
            
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                print("Initializing OpenAI client...")
                self._client = OpenAI(api_key=openai_api_key)
                self._deployment = "gpt-4-turbo-preview"  
                print("OpenAI client initialized successfully")
                return
                
            raise ValueError("No valid API credentials found. Please set either Azure OpenAI or OpenAI credentials.")
            
        except Exception as e:
            print(f"Warning: OpenAI client initialization failed: {str(e)}")
            print("LLM-based attribute extraction will be disabled")
            self._client = None
            self._deployment = None
            
    @retry_on_error(max_retries=3)
    def _process_with_model(self, prompt: str) -> str:
        """Process a prompt using OpenAI or Azure OpenAI."""
        if not self._client:
            print("LLM client not initialized. Skipping processing.")
            return None
            
        messages = [
            {"role": "system", "content": "You are a precise data extraction assistant that extracts specific attributes from product information. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        print("\n=== LLM Input ===")
        print(json.dumps(messages, indent=2))
        print("===============\n")
        
        response = self._client.chat.completions.create(
            model=self._deployment,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            response_format={ "type": "json_object" }  
        )
        
        generated_text = response.choices[0].message.content
        
        print("\n=== LLM Output ===")
        print(generated_text)
        print("================\n")
        
        return generated_text
            
    @retry_on_error(max_retries=3)
    def _process_single_product(self, product: Dict) -> Dict:
        """Process a single product using LLM."""
        prompt = f"""Extract the following attributes from this vape product information:
        - Brand
        - Model/Type
        - Flavor
        - Puff Count
        - Nicotine Strength
        - Battery Capacity
        - Coil Type
        
        Product Information:
        {product['content']}
        
        Return ONLY a JSON object with the following structure, no other text:
        {{
            "brand": "extracted brand",
            "model": "extracted model/type",
            "flavor": "extracted flavor",
            "puff_count": "extracted puff count",
            "nicotine_strength": "extracted nicotine strength",
            "battery_capacity": "extracted battery capacity",
            "coil_type": "extracted coil type"
        }}
        
        If an attribute cannot be found, use "N/A" as the value.
        """
        
        response = self._process_with_model(prompt)
        if response:
            try:
                result = json.loads(response)
                
                required_fields = [
                    "brand", "model", "flavor", "puff_count",
                    "nicotine_strength", "battery_capacity", "coil_type"
                ]
                
                if all(field in result for field in required_fields):
                    return result
                else:
                    print(f"Missing required fields in response for {product['file_name']}")
                    return self._get_default_attributes()
                    
            except json.JSONDecodeError as e:
                print(f"Error parsing LLM response for {product['file_name']}: {str(e)}")
                return self._get_default_attributes()
        
        return self._get_default_attributes()
            
    def _get_default_attributes(self) -> Dict:
        """Return default attributes when processing fails."""
        return {
            "brand": "N/A",
            "model": "N/A",
            "flavor": "N/A",
            "puff_count": "N/A",
            "nicotine_strength": "N/A",
            "battery_capacity": "N/A",
            "coil_type": "N/A"
        }
        
    def process_products(self, products: List[Dict]) -> List[Dict]:
        """Process products in batches using LLM."""
        structured_products = []
        
        products_by_site = {}
        for product in products:
            site = product.get('site')
            if not site:
                url = product.get('url', '')
                if 'vaperanger' in url:
                    site = 'vaperanger'
                elif 'vapewholesale' in url:
                    site = 'vapewholesale'
                else:
                    site = 'unknown'
            
            if site not in products_by_site:
                products_by_site[site] = []
            products_by_site[site].append(product)
        
        for site, site_products in products_by_site.items():
            site_dir = f"output/{site}"
            if not os.path.exists(site_dir):
                print(f"Warning: No text files found for site {site}")
                for product in site_products:
                    try:
                        content = f"""URL: {product.get('url', 'N/A')}

Title: {product.get('title', 'N/A')}

Price: {product.get('price', 'N/A')}

Description: {product.get('description', 'N/A')}

Specifications:
{json.dumps(product.get('specifications', {}), indent=2)}

Raw Text Content:
{product.get('raw_text', 'N/A')}"""

                        structured_product = self._process_single_product({
                            'file_name': f"{product.get('slug', 'unknown')}.txt",
                            'content': content
                        })
                        structured_products.append(structured_product)
                    except Exception as e:
                        print(f"Error processing product: {str(e)}")
                        structured_products.append(self._get_default_attributes())
                continue
                
            text_files = [f for f in os.listdir(site_dir) if f.endswith('.txt')]
            
            for i in range(0, len(text_files), self.batch_size):
                batch_files = text_files[i:i + self.batch_size]
                batch_products = []
                
                for file_name in batch_files:
                    file_path = os.path.join(site_dir, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            batch_products.append({
                                'file_name': file_name,
                                'content': content
                            })
                    except Exception as e:
                        print(f"Error reading file {file_name}: {str(e)}")
                
                if batch_products:
                    for product in batch_products:
                        structured_product = self._process_single_product(product)
                        structured_products.append(structured_product)
                
                time.sleep(1)
        
        return structured_products
    
    def save_structured_data(self, structured_products: List[Dict]) -> pd.DataFrame:
        """Save structured data to CSV and return DataFrame."""
        if not structured_products:
            return pd.DataFrame()
            
        self._ensure_output_directory()
            
        df = pd.DataFrame(structured_products)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/structured_products_{timestamp}.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved structured data to: {output_path}")
        
        return df 