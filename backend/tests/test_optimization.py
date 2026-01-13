import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def test_optimization():
    print("Testing Optimization...")
    
    # Define a date range
    start_date = "2024-12-16"
    end_date = "2024-12-16"
    field = "kinh-doanh"
    
    # 1. First Call: Should crawl and save to DB
    print("\n--- 1. First Call (Cold Start) ---")
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/analyze/full", params={
        "start_date": start_date,
        "end_date": end_date,
        "field": field,
        "num_articles": 3
    })
    duration1 = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json().get('data', {})
        source = data.get('source')
        print(f"Status: {response.status_code}")
        print(f"Source: {source}") # Should be 'crawler' (or 'database' if already there from previous runs)
        print(f"Duration: {duration1:.2f}s")
    else:
        print(f"Error: {response.text}")
        return

    # 2. Second Call: Should use DB
    print("\n--- 2. Second Call (Cached) ---")
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/analyze/full", params={
        "start_date": start_date,
        "end_date": end_date,
        "field": field,
        "num_articles": 3
    })
    duration2 = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json().get('data', {})
        source = data.get('source')
        print(f"Status: {response.status_code}")
        print(f"Source: {source}") # Should be 'database'
        print(f"Duration: {duration2:.2f}s")
        
        if source == 'database' and duration2 < duration1:
            print("\n✅ Optimization Verified: Cached call was faster and used database.")
        else:
            print("\n⚠️  Optimization Check: Result unclear (maybe first run was already cached or crawler is very fast).")
            
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_optimization()
