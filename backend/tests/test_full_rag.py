from serperior.api.vector_db import ArticleVectorDB
from serperior.rag.rag_service import RAGService
from serperior.rag.llm_client import LLMClient
import os
import logging

logging.basicConfig(level=logging.INFO)

def test_full_rag():
    print("Initialize RAG System...")
    db = ArticleVectorDB()
    rag = RAGService(db)
    
    # Check for API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n[WARNING] GEMINI_API_KEY env var not set.")
        print("Please set it: $env:GEMINI_API_KEY='your_key'")
        print("Using dummy LLM behavior for test locally if key missing.")
    
    llm = LLMClient(provider="gemini", api_key=api_key)
    
    query = "Lộc Trời"
    print(f"\nQuerying: {query}")
    
    # 1. Retrieve
    context = rag.retrieve_context(query)
    print(f"Context Length: {len(context)} chars")
    
    if not context:
        print("No context found. Aborting generation.")
        return

    # 2. Format
    messages = rag.format_prompt(query, context)
    
    # 3. Generate
    print("\nGenerating Answer...")
    answer = llm.generate_answer(messages)
    
    print("\n=== FINAL ANSWER ===")
    print(answer)

if __name__ == "__main__":
    test_full_rag()
