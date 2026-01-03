
from services.price_service import fetch_metadata
import logging

logging.basicConfig(level=logging.INFO)

urls = [
    # Generic (GitHub - has OG tags)
    "https://github.com/microsoft/playwright-python",
    # Amazon (from previous logs)
    "https://www.amazon.com/dp/B08JWGFKF2/", 
]

for url in urls:
    print(f"\n--- Testing {url} ---")
    data = fetch_metadata(url)
    print(f"Title: {data.get('title')}")
    print(f"Image: {data.get('image_url')}")
    print(f"Price: {data.get('price')}")
    print(f"Full Data: {data}")
