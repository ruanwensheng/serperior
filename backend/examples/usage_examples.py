import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import List, Dict
import time

########## config

BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/v1/crawl"

############## crawl 1 day
def example_1_basic_single_day():
    print("eg 1 : crawl 1 day")
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    params = {
        "start_date": yesterday,
        "end_date": yesterday,
        "field": "kinh-doanh",
        "num_articles": 5
    }
    
    print(f"\nCrawling date: {yesterday}")
    print(f"Field: {params['field']}")
    print(f"Number of articles: {params['num_articles']}")
    response = requests.get(API_ENDPOINT, params=params)
    if response.status_code == 200:
        data = response.json()
        print(f"\n Crawled {data['total_articles']} articles")
        for i, article in enumerate(data['data'], 1):
            print(f"\n{i}. {article['title'][:70]}...")
            print(f"{article['date']} | {article['url'][:50]}...")
    else:
        print(f"\nError: {response.json()}")

def example_2_multi_day_crawl():
    print("eg2 : Multiday Crawl")
    end_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    start_date = datetime.now().strftime('%Y-%m-%d')
    
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "field": "thoi-su",
        "num_articles": 3 
    }
    
    print(f"\nDate range: {end_date} to {start_date}")
    print(f"Field: {params['field']}")
    print(f"Articles per day: {params['num_articles']}")
    
    response = requests.get(API_ENDPOINT, params=params, timeout=300)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nTotal: {data['total_articles']} articles")
        
        # Group by date
        by_date = {}
        for article in data['data']:
            date = article['date']
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(article)
        
        print(f"\nArticles by date:")
        for date in sorted(by_date.keys(), reverse=True):
            print(f"  {date}: {len(by_date[date])} articles")
    else:
        print(f"\nError: {response.json()}")

def example_3_multiple_fields():


    print("eg3 : Multiple Fields Comparison")

    fields = ['kinh-doanh', 'thoi-su', 'phap-luat', 'du-lich', 'bat-dong-san']
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    results = {}
    
    for field in fields:
        print(f"\nCrawling {field}...")
        
        params = {
            "start_date": yesterday,
            "end_date": yesterday,
            "field": field,
            "num_articles": 5
        }
        
        response = requests.get(API_ENDPOINT, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results[field] = data['total_articles']
            print(f" {field}: {data['total_articles']} articles")
        else:
            results[field] = 0
            print(f"{field}: Failed")
        
        time.sleep(1)  # Delay để tránh spam


    for field, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"  {field:20s}: {count:3d} articles")

def example_4_save_to_csv():

    print("\n" + "="*80)
    print("eg4: Save to CSV")
    print("="*80)
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    params = {
        "start_date": yesterday,
        "end_date": yesterday,
        "field": "kinh-doanh",
        "num_articles": 10
    }
    
    response = requests.get(API_ENDPOINT, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(data['data'])
        
        # Save to CSV
        filename = f"news_{yesterday}_{params['field']}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"\nSaved {len(df)} articles to {filename}")
        print(df[['date', 'title']].head())
    else:
        print(f"\n Error: {response.json()}")

def example_5_save_to_json():


    print("eg5: Save to JSON")

    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    params = {
        "start_date": yesterday,
        "end_date": yesterday,
        "field": "thoi-su",
        "num_articles": 10
    }
    
    response = requests.get(API_ENDPOINT, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        # Add metadata
        output = {
            "metadata": {
                "crawled_at": datetime.now().isoformat(),
                "date_range": f"{params['end_date']} to {params['start_date']}",
                "field": params['field'],
                "total_articles": data['total_articles']
            },
            "articles": data['data']
        }
        
        # Save to JSON
        filename = f"news_{yesterday}_{params['field']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\nSaved to {filename}")
        print(f"Total articles: {output['metadata']['total_articles']}")
    else:
        print(f"\nError: {response.json()}")

def example_6_error_handling():
    
    print("eg6: Error Handling Best Practices")
    
    def safe_crawl(start_date, end_date, field, num_articles, max_retries=3):
        """Crawl với retry logic"""
        
        for attempt in range(max_retries):
            try:
                print(f"\nAttempt {attempt + 1}/{max_retries}")
                
                params = {
                    "start_date": start_date,
                    "end_date": end_date,
                    "field": field,
                    "num_articles": num_articles
                }
                
                response = requests.get(
                    API_ENDPOINT, 
                    params=params,
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Got {data['total_articles']} articles")
                    return data
                
                elif response.status_code == 400:
                    # Bad request - không retry
                    error = response.json()
                    print(f"Bad request: {error['error']}")
                    return None
                
                elif response.status_code == 500:
                    # Server error - retry
                    print(f"Server error, retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
            except requests.exceptions.Timeout:
                print(f"Timeout, retrying...")
                time.sleep(2 ** attempt)
                continue
                
            except requests.exceptions.ConnectionError:
                print(f"Connection error, retrying...")
                time.sleep(2 ** attempt)
                continue
                
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                return None
        
        print(f"\nFailed after {max_retries} attempts")
        return None
    
    # Test với retry logic
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    result = safe_crawl(yesterday, yesterday, "kinh-doanh", 5)
    
    if result:
        print(f"\n✅ Final result: {result['total_articles']} articles")

def example_7_batch_processing():

    print("eg7: Batch Processing")

    tasks = [
        {"field": "kinh-doanh", "days_back": 3, "num_articles": 5},
        {"field": "thoi-su", "days_back": 3, "num_articles": 5},
        {"field": "phap-luat", "days_back": 3, "num_articles": 3},
    ]
    
    all_results = []
    
    for i, task in enumerate(tasks, 1):
        print(f"\nTask {i}/{len(tasks)}: {task['field']}")
        
        end_date = (datetime.now() - timedelta(days=task['days_back'])).strftime('%Y-%m-%d')
        start_date = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "field": task['field'],
            "num_articles": task['num_articles']
        }
        
        response = requests.get(API_ENDPOINT, params=params, timeout=300)
        
        if response.status_code == 200:
            data = response.json()
            all_results.extend(data['data'])
            print(f" {data['total_articles']} articles")
        else:
            print(f"Failed")
        
        time.sleep(2)  # Delay giữa các tasks
    
    # Save all results
    if all_results:
        df = pd.DataFrame(all_results)
        filename = f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\ntotal: {len(all_results)} articles saved to {filename}")

def example_8_data_analysis():

    print("eg8: Basic Data Analysis")
 
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    params = {
        "start_date": yesterday,
        "end_date": yesterday,
        "field": "kinh-doanh",
        "num_articles": 20
    }
    response = requests.get(API_ENDPOINT, params=params)
    
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['data'])
        
        print(f"\nANALYSIS RESULTS:")
   
        print(f"\n1. Basic Statistics:")
        print(f"   Total articles: {len(df)}")
        print(f"   Unique dates: {df['date'].nunique()}")
        
        # 2. Title length analysis
        df['title_length'] = df['title'].str.len()
        print(f"\n2. Title Length:")
        print(f"   Average: {df['title_length'].mean():.1f} characters")
        print(f"   Min: {df['title_length'].min()}")
        print(f"   Max: {df['title_length'].max()}")
        
        # 3. Most common words in titles (simple)
        all_titles = ' '.join(df['title'].values).lower()
        words = all_titles.split()
        word_freq = {}
        for word in words:
            if len(word) > 3: 
                word_freq[word] = word_freq.get(word, 0) + 1
        
        print(f"\n3. Top 10 Most Common Words:")
        for word, count in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {word}: {count}")
        
        df['body_length'] = df['body'].str.len()
        print(f"\n4. Body Length:")
        print(f"   Average: {df['body_length'].mean():.1f} characters")
        
    else:
        print(f"\nError: {response.json()}")



def main():
    
    examples = {
        "1": ("Basic Single Day Crawl", example_1_basic_single_day),
        "2": ("Multi-day Crawl", example_2_multi_day_crawl),
        "3": ("Multiple Fields Comparison", example_3_multiple_fields),
        "4": ("Save to CSV", example_4_save_to_csv),
        "5": ("Save to JSON", example_5_save_to_json),
        "6": ("Error Handling", example_6_error_handling),
        "7": ("Batch Processing", example_7_batch_processing),
        "8": ("Data Analysis", example_8_data_analysis),
        "all": ("Run All Examples", None),
    }

    print("\n choose an example to run:")
    
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    print("-" * 80)
    choice = input("\nEnter your choice (or 'q' to quit): ").strip()
    
    if choice == 'q':
        print("\n byee")
        return
    
    if choice == 'all':
        for key, (name, func) in examples.items():
            if func:
                try:
                    func()
                    time.sleep(2)
                except Exception as e:
                    print(f"\nError in {name}: {str(e)}")
    elif choice in examples:
        name, func = examples[choice]
        if func:
            try:
                func()
            except Exception as e:
                print(f"\nError: {str(e)}")
    else:
        print("\nInvalid choice!")


if __name__ == "__main__":
    main()