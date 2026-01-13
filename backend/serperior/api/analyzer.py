from typing import List, Dict, Tuple, Optional
from collections import Counter
import re
from datetime import datetime
import pandas as pd
from underthesea import word_tokenize, pos_tag
import numpy as np
# PhoBERT imports
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import argparse
from .extractor import PhoBERTEntityExtractor

class NewsAnalyzer:
    """trích xuất thực thể"""
    
    def __init__(self, use_phobert: bool = True):
        """
        Initialize analyzer
        
        Args:
            use_phobert: dùng phobert
        """
        # Vietnamese stopwords
        self.stopwords = set([
            'của', 'và', 'các', 'có', 'được', 'theo', 'trong', 
            'từ', 'với', 'cho', 'về', 'là', 'một', 'này', 
            'đã', 'tại', 'đến', 'để', 'những', 'người', 'khi',
            'năm', 'ngày', 'tháng', 'vào', 'sau', 'trước', 'giờ',
            'sẽ', 'bị', 'hơn', 'đang', 'cũng', 'không', 'thì'
        ])
        
        # Sentiment keywords
        self.positive_words = set([
            'tăng', 'tốt', 'mạnh', 'cao', 'khả quan', 'tích cực',
            'phát triển', 'thành công', 'hiệu quả', 'lợi nhuận',
            'ổn định', 'cải thiện', 'nâng cao', 'tiến bộ', 'thuận lợi',
            'tăng trưởng', 'bùng nổ', 'vượt', 'đột phá', 'kỷ lục'
        ])
        
        self.negative_words = set([
            'giảm', 'xấu', 'yếu', 'thấp', 'tiêu cực', 'khó khăn',
            'suy giảm', 'thất bại', 'thiệt hại', 'lỗ', 'thua lỗ',
            'bất ổn', 'sụt giảm', 'đình trệ', 'khủng hoảng', 'rủi ro',
            'suy thoái', 'đình đốn', 'sa thải', 'phá sản', 'âm'
        ])
        
        # Init PhoBERT NER
        self.use_phobert = use_phobert
        self.entity_extractor = None
        
        if use_phobert:
            try:
                self.entity_extractor = PhoBERTEntityExtractor()
                print("PhoBERT Entity Extractor initialized")
            except Exception as e:
                print(f"Could not initialize PhoBERT: {e}")
                print("Entity extraction will be disabled")
                self.use_phobert = False
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Trích xuất từ khóa quan trọng từ text
        
        Args:
            text: Văn bản 
            top_n: Số từ khóa cần lấy
            
        Returns:
            List of (keyword, frequency) 
        """
        # Tokenize
        words = word_tokenize(text.lower())
        
        # Filter loại stopword
        filtered_words = [
            word for word in words
            if (len(word) > 2 and 
                word not in self.stopwords and
                not word.isdigit() and
                word.isalpha())
        ]
        
        # Count frequency
        word_freq = Counter(filtered_words)
        
        return word_freq.most_common(top_n)
    
    def extract_entities_from_text(self, text: str) -> List[Dict]:
        """
        Extract entities from a single text using PhoBERT
        
        Args:
            text: Input text
            
        Returns:
            List of entities
        """
        if not self.use_phobert or not self.entity_extractor:
            return []
        
        return self.entity_extractor.extract_entities(text)
    
    def extract_entities_from_articles(self, articles: List[Dict]) -> Dict:
        """
        Extract and aggregate entities from multiple articles
        
        Args:
            articles: List of article dicts
            
        Returns:
            Dict with entity analysis
        """
        if not self.use_phobert or not self.entity_extractor:
            return {
                "entities": [],
                "by_type": {},
                "total_count": 0,
                "articles_with_entities": []
            }
        
        all_entities = []
        articles_with_entities = []
        entity_counter = Counter()
        by_type = {"PER": [], "ORG": [], "LOC": [], "MISC": [], "PERSON": [], "ORGANIZATION":[],"LOCATION":[]}
        
        for article in articles:
            text = f"{article.get('title', '')} {article.get('body', '')}"
            
            # Extract entities
            entities = self.extract_entities_from_text(text)
            
            if entities:
                # Add to article-level results
                articles_with_entities.append({
                    "title": article.get('title'),
                    "date": article.get('date'),
                    "url": article.get('url'),
                    "entities": entities
                })
                
                for entity in entities:
                    entity_key = f"{entity['text']}|{entity['type']}"
                    entity_counter[entity_key] += 1
            
                    entity_type = entity['type']
                    if entity_type in by_type:
                        by_type[entity_type].append(entity['text'])
        
        # Process aggregated entities
        top_entities = []
        for entity_key, count in entity_counter.most_common(50):
            text, entity_type = entity_key.split('|')
            top_entities.append({
                "text": text,
                "type": entity_type,
                "type_vi": self.entity_extractor.entity_labels.get(entity_type, entity_type),
                "count": count
            })
        
        # Count unique entities by type
        by_type_summary = {}
        for etype, entities in by_type.items():
            unique_entities = list(set(entities))
            by_type_summary[etype] = {
                "count": len(unique_entities),
                "type_vi": self.entity_extractor.entity_labels.get(etype, etype),
                "top_entities": Counter(entities).most_common(10)
            }
        
        return {
            "entities": top_entities,
            "by_type": by_type_summary,
            "total_count": len(all_entities),
            "unique_count": len(entity_counter),
            "articles_with_entities": articles_with_entities[:10]  # Top 10 articles
        }
    
    def analyze_trend(self, articles: List[Dict], top_n: int = 20) -> Dict:
        """
        Phân tích xu hướng từ danh sách bài báo
        
        Args:
            articles: List of article dicts
            top_n: Top N keywords
            
        Returns:
            Dict with trend analysis results
        """
        if not articles:
            return {
                "keywords": [],
                "total_articles": 0,
                "date_range": None,
                "timeline": {}
            }
        
        # Combine all text
        all_text = " ".join([
            f"{article.get('title', '')} {article.get('body', '')}"
            for article in articles
        ])
        
        # Extract keywords
        keywords = self.extract_keywords(all_text, top_n)
        
        # Date range
        dates = [article.get('date') for article in articles if article.get('date')]
        date_range = {
            "start": min(dates) if dates else None,
            "end": max(dates) if dates else None
        }
        
        # Timeline analysis
        keyword_timeline = self._analyze_keyword_timeline(articles, keywords)
        
        return {
            "keywords": [
                {"word": word, "count": count} 
                for word, count in keywords
            ],
            "total_articles": len(articles),
            "date_range": date_range,
            "timeline": keyword_timeline
        }
    
    def _analyze_keyword_timeline(self, articles: List[Dict], 
                                   top_keywords: List[Tuple[str, int]]) -> Dict:
        """Phân tích keywords theo timeline"""
        top_5_words = [word for word, _ in top_keywords[:5]]
        
        # Group by date
        by_date = {}
        for article in articles:
            date = article.get('date')
            if not date:
                continue
            
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(article)
        
        # Count keywords per date
        timeline = {}
        for date, day_articles in sorted(by_date.items()):
            day_text = " ".join([
                f"{a.get('title', '')} {a.get('body', '')}"
                for a in day_articles
            ]).lower()
            
            timeline[date] = {
                word: day_text.count(word)
                for word in top_5_words
            }
        
        return timeline
    
    def full_analysis(self, articles: List[Dict], top_n: int = 20) -> Dict:
        print(f"Analyzing {len(articles)} articles...")
        
        
        print("Extracting trends...")
        trend_result = self.analyze_trend(articles, top_n)
        
        
        
        # Entity extraction
        entities_result = {}
        if self.use_phobert:
            print("Extracting entities...")
            entities_result = self.extract_entities_from_articles(articles)
        
        print("Analysis complete!")
        
        return {
            "entities": entities_result,
            "summary": {
                "total_articles": len(articles),
                "date_range": trend_result.get('date_range'),
                "top_entities": entities_result.get('entities', [])[:10] if entities_result else []
            }
        }