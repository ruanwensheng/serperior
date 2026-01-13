from serperior.api.vector_db import ArticleVectorDB
import shutil
import os

def clear_db():
    print("Clearing DB...")
    db = ArticleVectorDB()
    # verify path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    persist_directory = os.path.join(base_dir, "data", "real_chroma_db")
    
    print(f"Target: {persist_directory}")
    try:
        # Close client connection if possible or just nuke the dir (unsafe while running?)
        # safe way: use client.reset() if allowed or just delete collection
        try:
            db.client.delete_collection("dantri_articles")
            print("Deleted collection 'dantri_articles'")
        except Exception as e:
            print(f"Collection delete failed (maybe empty): {e}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clear_db()
