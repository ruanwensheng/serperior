import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_health():

    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_get_fields():

    response = requests.get(f"{BASE_URL}/api/v1/fields")
    data = response.json()
    print(f"Valid fields: {data['valid_fields']}\n")
    return data['valid_fields']

def test_crawl(start_date, end_date, field="kinh-doanh", num_articles=5):

    print(f"   Field: {field}")
    print(f"   Date range: {end_date} to {start_date}")
    print(f"   Articles per day: {num_articles}\n")
    
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "field": field,
        "num_articles": num_articles
    }
    
    response = requests.get(f"{BASE_URL}/api/v1/crawl", params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"{data['message']}")
        print(f" Total articles: {data['total_articles']}\n")
        
        # Hiển thị 3 bài đầu tiên
        print("Sample articles:")
        for i, article in enumerate(data['data'][:3], 1):
            print(f"\n{i}. [{article['date']}] {article['title'][:80]}...")
            print(f"   URL: {article['url']}")
        
        return data
    else:
        error = response.json()
        print(f"Error {error['status_code']}: {error['error']}")
        return None

def test_error_handling():
    
    # Test 1: Ngày sai định dạng
    print("\n1. Invalid date format:")
    response = requests.get(
        f"{BASE_URL}/api/v1/crawl",
        params={"start_date": "2024/12/16", "end_date": "2024-12-15"}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Error: {response.json()['error'][:100]}...")
    
    # Test 2: Field không hợp lệ
    print("\n2. Invalid field:")
    response = requests.get(
        f"{BASE_URL}/api/v1/crawl",
        params={"start_date": "2024-12-16", "end_date": "2024-12-15", "field": "invalid"}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Error: {response.json()['error'][:100]}...")
    
    # Test 3: Khoảng ngày sai
    print("\n3. Invalid date range:")
    response = requests.get(
        f"{BASE_URL}/api/v1/crawl",
        params={"start_date": "2024-12-15", "end_date": "2024-12-16"}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Error: {response.json()['error'][:100]}...")

def save_to_file(data, filename="crawled_articles.json"):
    """Lưu kết quả vào file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {filename}")

if __name__ == "__main__":
    
    # Test 1: Health check
    test_health()
    
    # Test 2: Get valid fields
    valid_fields = test_get_fields()
    
    # Test 3: Crawl articles
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    data = test_crawl(
        start_date=today.strftime('%Y-%m-%d'),
        end_date=yesterday.strftime('%Y-%m-%d'),
        field="kinh-doanh",
        num_articles=3
    )
    
    # Test 4: Save results
    if data:
        save_to_file(data)
    
    # Test 5: Error handling
    test_error_handling()
