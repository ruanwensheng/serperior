import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import hashlib
import json

class ArticleVectorDB:
    
    def __init__(self, persist_directory: str = None):
        """
        Initialize ChromaDB with PhoBERT embeddings
        
        Args:
            persist_directory: Where to store the database
        """
        if persist_directory is None:
            import os
            # Default to backend/data/real_chroma_db
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            persist_directory = os.path.join(base_dir, "data", "real_chroma_db")

        

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
        # a collection: a table in db
        try:
            # to get the collection existed in that client (A persistent client instance defined by path folder)
            self.collection = self.client.get_collection("dantri_articles")
            print(" Loaded existing collection")
        except:

            # nếu chưa có hoặc lỗi thì tạo collection đó 
         
            self.collection = self.client.create_collection(
                # tên bảng
                name="dantri_articles",
                # 
                metadata={"description": "Dantri news articles"}
            )
            print("Created new collection")


    def _generate_id(self, article: Dict) -> str:
        """Generate unique ID for AN article
        args: aritcle: {date - title - body - url}
        """
        # idex từ cột key (ở đây là url)
        if article.get('url'):
            return hashlib.md5(article['url'].encode()).hexdigest()
        else:
            text = f"{article.get('title', '')}{article.get('date', '')}"
            return hashlib.md5(text.encode()).hexdigest()
        
    def add_articles(self, articles: List[Dict]) -> int:
        """
        thêm các articals (list of dicts) vào vector db
        
        Args:
            articles: List of article dicts {'title', 'body', 'date', 'url'}
            
        Returns:
            số lượng bài báo
        """
        if not articles:
            print("Không có báo sao đc")
            return 0
        
        print(f"Processing {len(articles)} articles...")
        
        documents = []  
        metadatas = [] 
        ids = []        
        seen_ids = set()        
        
        # duyệt từng bài báo trong danh sách
        for article in articles:
            # kết hợp title và body
            text = f"{article.get('title', '')}. {article.get('body', '')}"
            
            if len(text.strip()) < 10: 
                continue
            
            # Convert date to int YYYYMMDD for filtering
            date_str = article.get('date', '')
            date_int = 0
            try:
                if date_str:
                    date_int = int(date_str.replace('-', ''))
            except:
                pass

            # Generate ID first to check for duplicates
            article_id = self._generate_id(article)
            
            if article_id in seen_ids:
                continue
                
            seen_ids.add(article_id)

            # documents là những thông tin quan trọng
            # metadatas là những thông tin phụ, ko cần preprocess và ko cần LLM phải nhận
            documents.append(text)
            metadatas.append({
                'title': article.get('title', ''),
                'date': date_int, # Store as int
                'date_str': date_str, # Store original string for display
                'url': article.get('url', ''),
                'body': article.get('body', '')[:500]  
            })
            ids.append(article_id)
        
        if not documents:
            print(" No valid articles to add")
            return 0
        
        # Generate embeddings
        print("generating embeddings...")
        embeddings = self.embedding_model.encode(
            documents, 
            show_progress_bar=True,
            # save in numpy form 
            convert_to_numpy=True 
        ).tolist()
        
        # Add to ChromaDB
        print("lưu vào collection (named ...)...")
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
    
        #self.client.persist()
        
        print(f"đã thêm {len(documents)} articles to database")
        return len(documents)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for relevant articles
        1. embed the query
        2. tìm kiếm : self.collection.query(...)
        3. hậu xử lý
        
        Args:
            query: 
            top_k: top bài báo relevant
            
        Returns:
            List of dicts các bài liên quan
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(
            query,
            convert_to_numpy=True
        ).tolist()
        
        #-- tìm kiếm trong chromadb
        # need to find the structure of results
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        #--post processing kết quả
        articles = []

        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                meta = results['metadatas'][0][i]
                articles.append({
                    'content': results['documents'][0][i],
                    'metadata': meta,
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return articles
    
    def count(self) -> int:
        """ tổng số bài """
        return self.collection.count()
    
    
    def get_articles_by_date(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Get articles within a date range from database
        """
        try:
            # Convert query dates to int
            start_int = int(start_date.replace('-', ''))
            end_int = int(end_date.replace('-', ''))

            results = self.collection.get(
                where={
                    "$and": [
                        {"date": {"$gte": start_int}},
                        {"date": {"$lte": end_int}}
                    ]
                }
            )
            
            articles = []
            if results['documents']:
                for i in range(len(results['documents'])):
                    meta = results['metadatas'][i]
                    articles.append({
                        'title': meta.get('title', ''),
                        'body': meta.get('body', ''), 
                        'date': meta.get('date_str', ''), # Retrieve original string
                        'url': meta.get('url', ''),
                    })
            return articles
        except Exception as e:
            print(f"Error querying DB: {e}")
            return []

    def check_existence(self, date: str) -> bool:
        """Check if we have any articles for a specific date"""
        try:
            date_int = int(date.replace('-', ''))
            results = self.collection.get(
                where={"date": date_int},
                limit=1
            )
            return len(results['ids']) > 0
        except:
            return False

    def get_stats(self) -> Dict:
        """Get database statistics"""
        return {
            "total_articles": self.collection.count()
        }

    def clear(self):
        """mỗi lần người dùng request crawl mới thì những dữ liệu cũ sẽ bị clear"""
        self.client.delete_collection("dantri_articles")
        self.collection = self.client.create_collection("dantri_articles")
        print("Database cleared")
