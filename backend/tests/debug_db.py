from serperior.api.vector_db import ArticleVectorDB
import os

def debug_db():
    print("Debug DB...")
    # Manually reconstruct path to match api.py logic if needed, or rely on default
    # But running from root, __file__ resolution might differ if not installed as package?
    # Actually, we run with `python backend/tests/debug_db.py`.
    # `vector_db.py` is in `backend/serperior/api/vector_db.py`.
    # logic: keys off __file__ location of vector_db.py, so it should be consistent regardless of run CWD.
    
    db = ArticleVectorDB()
    count = db.count()
    print(f"Total articles: {count}")
    
    if count > 0:
        print("Peeking at first 5 articles:")
        results = db.collection.get(limit=5)
        for i, meta in enumerate(results['metadatas']):
            print(f"[{i}] Date: '{meta.get('date')}' | Title: {meta.get('title')}")
            
        print("\nTesting Query for 2024-12-16:")
        query_res = db.get_articles_by_date("2024-12-16", "2024-12-16")
        print(f"Query Result Count: {len(query_res)}")

if __name__ == "__main__":
    debug_db()
