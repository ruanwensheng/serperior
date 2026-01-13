import os
import logging
import requests
import json
from typing import List, Dict, Optional, Union

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, provider: str = "gemini", api_key: str = None):
        """
        Initialize LLM Client.
        provider: 'gemini' or 'ollama' (future)
        """
        self.provider = provider
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        # We don't need SDK setup if using REST

    def generate_answer(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate answer from messages.
        messages format: [{'role': 'system', 'content': ...}, {'role': 'user', 'content': ...}]
        """
        if self.provider == "gemini":
            if not self.api_key:
                return "Gemini API Key missing."

            try:
                # Construct flow
                # Combine system and user for simplicity as Gemini chat structure is specific
                prompt_text = ""
                for msg in messages:
                   prompt_text += f"{msg['role'].title()}: {msg['content']}\n\n"

                # Use verified available model alias
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={self.api_key}"
                
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt_text}]
                    }]
                }
                
                headers = {'Content-Type': 'application/json'}
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    try:
                        return data['candidates'][0]['content']['parts'][0]['text']
                    except (KeyError, IndexError):
                        return "Không nhận được phản hồi từ Gemini (Format Error)."
                else:
                    logger.error(f"Gemini API Error: {response.text}")
                    return f"Gemini API Error: {response.status_code} - {response.text}"
                
            except Exception as e:
                logger.error(f"Gemini generation error: {e}")
                return f"Error: {str(e)}"
        
        return "LLM Provider not configured."
