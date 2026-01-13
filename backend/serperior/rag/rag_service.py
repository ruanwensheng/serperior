from typing import List, Dict, Optional
import logging
from ..api.vector_db import ArticleVectorDB

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, vector_db: ArticleVectorDB):
        self.vector_db = vector_db

    def retrieve_context(self, query: str, top_k: int = 5) -> str:
        """
        Retrieve context from vector database and format it for the LLM.
        """
        logger.info(f"Retrieving context for query: {query}")
        try:
            results = self.vector_db.search(query, top_k=top_k)
            
            if not results:
                return ""
            context_parts = []
            for i, doc in enumerate(results):
                # doc = {'content': ..., 'metadata': ..., 'distance': ...}
                metadata = doc.get('metadata', {})
                title = metadata.get('title', 'Unknown Title')
                date = metadata.get('date_str', 'Unknown Date') # Using date_str we added
                body = doc.get('content', '') # Content is title + body
                
                # Format: [Date] Title
                # Content...
                context_parts.append(f"Source {i+1} [{date}]: {title}\n{body}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return ""

    def format_prompt(self, query: str, context: str) -> str:
        """
        Combine user query and context into a prompt.
        """
        system_prompt = """Bạn là một trợ lý AI thông minh, chuyên trả lời câu hỏi dựa trên tin tức được cung cấp.
        Hãy trả lời câu hỏi của người dùng một cách chính xác, khách quan, và chỉ sử dụng thông tin từ các bài báo dưới đây.
        Nếu thông tin không có trong bài báo, hãy nói rằng bạn không biết.
        """
        
        user_prompt = f"""
        Thông tin bài báo (Context):
        {context}
        
        Câu hỏi: {query}
        
        Trả lời:
        """

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
