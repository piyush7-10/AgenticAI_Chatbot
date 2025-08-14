import requests
from bs4 import BeautifulSoup
import json
import time

def scrape_jio_data():
    urls = [
        'https://www.jio.com/mobile/prepaid-plans',
        'https://www.jio.com/mobile/postpaid-plans',
        'https://www.jio.com/fiber/broadband-plans',
        'https://www.jio.com/business/broadband',
        'https://www.jio.com/5g',
        'https://www.jio.com/apps',
    ]
    
    all_data = []
    
    for url in urls:
        try:
            print(f"Scraping {url}...")
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            })
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract all text
            text = soup.get_text(separator=' ', strip=True)
            
            # Extract specific plan details if available
            plans = soup.find_all(['div', 'section'], class_=['plan', 'price', 'offer'])
            plan_texts = [plan.get_text(strip=True) for plan in plans]
            
            data = {
                'url': url,
                'content': text[:10000],  # Increased limit
                'title': soup.title.string if soup.title else 'Jio Services',
                'plans': plan_texts[:10] if plan_texts else []
            }
            all_data.append(data)
            time.sleep(2)  # Be respectful
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    
    # Save to JSON
    with open('data/jio_data.json', 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"✅ Scraped {len(all_data)} pages successfully")
    return all_data

if __name__ == "__main__":
    scrape_jio_data()