from typing import List, Dict, Tuple, Optional
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import argparse

class PhoBERTEntityExtractor:
    def __init__(self, model_name: str = "NlpHUST/ner-vietnamese-electra-base"):
        """
        
        Tham số:
            model_name: default = "NlpHUST/ner-vietnamese-electra-base"
        Attributes:
        - tokenizer
        - model
        - device
        - entity_labels : nhãn     
        """
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(model_name)

        except Exception as e:
            print(f"Error loading model: {e}")
            print("Trying backup plan model...")
     
            model_name = "vinai/phobert-base"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(
                model_name,
                num_labels=9  # labels = [O, B-PER, I-PER, B-ORG, I-ORG, B-LOC, I-LOC, B-MISC, I-MISC]
            )
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        
        # map sang Vietnamese)
        self.entity_labels = {
            "PER": "Người",
            "PERSON": "Người",
            "ORG": "Tổ chức",
            "ORGANIZATION": "Tổ chức",
            "LOC": "Địa điểm",
            "LOCATION": "Địa điểm",
            "MISC": "Khác"
        }
    
    def extract_entities(self, text: str) -> List[Dict]:
        """
        Extract named entities from text
        
        Args:
            text: text tiếng Việt
            
        Returns:
            List of entities with type and text (vd: )
        """
        try:
            # Tokenize input
            inputs = self.tokenizer(
                text,
                # đầu vào định dạng pytorch tensor
                return_tensors="pt",
                truncation=True,
                max_length=256,
                padding=True
            ).to(self.device)
            
            # inference 
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.argmax(outputs.logits, dim=2)
            
            # post processing
            tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
            labels = predictions[0].cpu().numpy()
            
            # Extract entities
            entities = []
            current_entity = None
            current_tokens = []
            
            for token, label_id in zip(tokens, labels):
                if token in ["<s>", "</s>", "<pad>", "<unk>"]:
                    continue
                
                # Get label from model config
                if hasattr(self.model.config, 'id2label'):
                    label = self.model.config.id2label.get(int(label_id), "O")
                else:
                    label = "O"
                
                if label.startswith("B-"):
                    # Save previous entity
                    if current_entity:
                        entities.append({
                            "text": self._merge_tokens(current_tokens),
                            "type": current_entity,
                            "type_vi": self.entity_labels.get(current_entity, current_entity)
                        })
                    # Start new entity
                    current_entity = label[2:]
                    current_tokens = [token]
                elif label.startswith("I-") and current_entity == label[2:]:
                    # Continue current entity
                    current_tokens.append(token)
                else:
                    # Outside any entity
                    if current_entity:
                        entities.append({
                            "text": self._merge_tokens(current_tokens),
                            "type": current_entity,
                            "type_vi": self.entity_labels.get(current_entity, current_entity)
                        })
                    current_entity = None
                    current_tokens = []
            
            # Add last entity if exists
            if current_entity:
                entities.append({
                    "text": self._merge_tokens(current_tokens),
                    "type": current_entity,
                    "type_vi": self.entity_labels.get(current_entity, current_entity)
                })
            
            return entities
            
        except Exception as e:
            print(f"lỗi: {e}")
            return []
    
    def _merge_tokens(self, tokens: List[str]) -> str:
        """Merge subword tokens back to words"""
        text = " ".join(tokens)
        # Clean up Vietnamese tokenization
        text = text.replace("@@ ", "")
        text = text.replace("_", " ")
        text = text.strip()
        return text

# test

if __name__ =="__main__":
    test1 = PhoBERTEntityExtractor(model_name = "NlpHUST/ner-vietnamese-electra-base")
    text = "Đây là nhận định của PGS.TS Bùi Hoài Sơn, Ủy viên chuyên trách Ủy ban Văn hóa - Xã hội của Quốc hội, khi trao đổi với phóng viên Dân trí về chặng đường 80 năm Ngày Tổng tuyển cử đầu tiên (6/1/1946)"
    print(test1.extract_entities(text))