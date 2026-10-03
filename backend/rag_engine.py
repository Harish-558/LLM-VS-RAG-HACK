import json
import os
import numpy as np
from typing import List, Dict, Any

class RAGEngine:
    def __init__(self, knowledge_base_path: str = "knowledge_base.json"):
        self.knowledge_base_path = knowledge_base_path
        self.documents: List[Dict[str, Any]] = []
        self.texts: List[str] = []
        self.use_faiss = False
        self.index = None
        self.model = None

        self.load_knowledge_base()
        self.init_embeddings_and_index()

    def load_knowledge_base(self):
        if not os.path.isabs(self.knowledge_base_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(base_dir, self.knowledge_base_path)
        else:
            full_path = self.knowledge_base_path

        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                self.documents = json.load(f)
        else:
            # Default fallback dataset
            self.documents = [
                {
                    "id": "fact-1",
                    "title": "Quantum Nova-X Processor",
                    "category": "Technology",
                    "content": "The Nova-X Quantum Processor was developed by QuantumCore Systems and launched on October 14, 2025. It operates at 128 superconducting qubits with gate fidelity of 99.94%."
                }
            ]
        self.texts = [f"Title: {doc['title']}\nContent: {doc['content']}" for doc in self.documents]

    def init_embeddings_and_index(self):
        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            # Lightweight sentence-transformer model
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            embeddings = self.model.encode(self.texts, convert_to_numpy=True)
            
            # Normalize for cosine similarity
            faiss.normalize_L2(embeddings)
            dimension = embeddings.shape[1]
            
            self.index = faiss.IndexFlatIP(dimension) # Inner Product (Cosine similarity when normalized)
            self.index.add(embeddings)
            self.use_faiss = True
            print(f"[RAGEngine] Initialized FAISS index with {len(self.documents)} documents.")
        except Exception as e:
            print(f"[RAGEngine] SentenceTransformer/FAISS init fallback notice: {e}")
            self.use_faiss = False

    def search(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        if not self.documents:
            return []

        top_k = min(top_k, len(self.documents))

        if self.use_faiss and self.model and self.index:
            try:
                import faiss
                query_vector = self.model.encode([query], convert_to_numpy=True)
                faiss.normalize_L2(query_vector)
                scores, indices = self.index.search(query_vector, top_k)
                
                results = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx >= 0 and idx < len(self.documents):
                        doc = self.documents[idx].copy()
                        doc["relevance_score"] = float(score)
                        results.append(doc)
                return results
            except Exception as err:
                print(f"[RAGEngine] Search fallback due to FAISS error: {err}")

        # Lexical/keyword fallback if FAISS/Transformer offline
        query_words = set(query.lower().split())
        scored_docs = []
        for doc in self.documents:
            text = (doc["title"] + " " + doc["content"]).lower()
            score = sum(1.0 for word in query_words if len(word) > 2 and word in text)
            scored_docs.append((score, doc))
        
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, doc in scored_docs[:top_k]:
            d = doc.copy()
            d["relevance_score"] = float(score)
            results.append(d)
        return results

    def get_all_documents(self) -> List[Dict[str, Any]]:
        return self.documents
