import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from serperior.api.vector_db import ArticleVectorDB
from serperior.api.dantri_crawler import DantriCrawler


def test_with_real_data():

    crawler = DantriCrawler(field='kinh-doanh')
    articles = crawler.crawl_by_date_range(
        start_date='2026-01-07',
        end_date='2026-01-06',
        num_articles=10,
        save=False
    )
    
    if not articles:
        print("No articles crawled")
        return
    
    print(f"Crawled {len(articles)} articles")
    # Use default persist_directory (backend/data/real_chroma_db)
    db = ArticleVectorDB()
    count = db.add_articles(articles)
    
    print(f"Stored {count} articles in database")
    

    test_queries = [
        "tin tức kinh tế hôm nay",
        "giá cả thị trường",
        "doanh nghiệp"
    ]

    for query in test_queries:
        print(f"\n{query}")
        results = db.search(query, top_k=3)
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['metadata']['title'][:60]}...")

if __name__ == "__main__":

    # Uncomment to test with real data
    test_with_real_data()
