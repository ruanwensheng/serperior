from serperior.api.vector_db import ArticleVectorDB
from serperior.rag.rag_service import RAGService
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_rag_retrieval():
    print("Initialize DB...")
    db = ArticleVectorDB() # Uses default path
    
    rag = RAGService(db)
    
    query = "Lộc Trời"
    print(f"\nQuerying: {query}")
    
    context = rag.retrieve_context(query, top_k=3)
    print("\n--- Retrieved Context ---")
    print(context)
    
    print("\n--- Formatted Prompt ---")
    prompt = rag.format_prompt(query, context)
    for p in prompt:
        print(f"[{p['role'].upper()}]: {p['content'][:100]}...")

if __name__ == "__main__":
    test_rag_retrieval()
