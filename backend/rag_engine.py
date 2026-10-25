import json
import os
import io
import numpy as np
from typing import List, Dict, Any, Optional

def extract_text_from_pdf(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extracts text page by page from raw PDF bytes.
    """
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_data = []
    for idx, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if text:
            pages_data.append({"page": idx + 1, "text": text})
    return pages_data

def chunk_page_text(text: str, page_num: int, filename: str, max_chunk_chars: int = 800, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Splits text into manageable chunks with page number tracking for RAG citations.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chunk_chars:
        return [{
            "id": f"pdf-{page_num}-1",
            "title": f"{filename} (Page {page_num})",
            "category": "PDF Document",
            "content": text,
            "page": page_num,
            "source": filename
        }]
    chunks = []
    start = 0
    chunk_idx = 1
    while start < len(text):
        end = min(start + max_chunk_chars, len(text))
        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append({
                "id": f"pdf-{page_num}-{chunk_idx}",
                "title": f"{filename} (Page {page_num}, Sec {chunk_idx})",
                "category": "PDF Document",
                "content": chunk_content,
                "page": page_num,
                "source": filename
            })
            chunk_idx += 1
        if end == len(text):
            break
        start += (max_chunk_chars - overlap)
    return chunks

class RAGEngine:
    def __init__(self, knowledge_base_path: str = "knowledge_base.json"):
        self.knowledge_base_path = knowledge_base_path
        self.documents: List[Dict[str, Any]] = []
        self.texts: List[str] = []
        self.use_faiss = False
        self.index = None
        self.model = None
        self.active_pdf_name: Optional[str] = None

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
        if not self.texts:
            self.index = None
            self.use_faiss = False
            return
        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            # Cache model instance so re-indexing PDFs is fast
            if self.model is None:
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

    def index_pdf(self, filename: str, pdf_bytes: bytes, replace_existing: bool = True) -> Dict[str, Any]:
        """
        Extracts text from PDF, chunks it, and indexes it into FAISS.
        If replace_existing is True, questions are answered strictly from the uploaded PDF.
        """
        pages_data = extract_text_from_pdf(pdf_bytes)
        if not pages_data:
            raise ValueError("No readable text found in the uploaded PDF. Please make sure the PDF contains text.")

        pdf_docs = []
        for p in pages_data:
            chunks = chunk_page_text(p["text"], p["page"], filename)
            pdf_docs.extend(chunks)

        if replace_existing:
            self.documents = pdf_docs
        else:
            self.documents.extend(pdf_docs)

        self.active_pdf_name = filename
        self.texts = [f"Title: {doc['title']}\nContent: {doc['content']}" for doc in self.documents]
        self.init_embeddings_and_index()

        return {
            "filename": filename,
            "pages_count": len(pages_data),
            "chunks_count": len(pdf_docs),
            "documents_total": len(self.documents)
        }

    def reset_to_default_knowledge_base(self):
        """
        Restores the built-in preset knowledge base.
        """
        self.active_pdf_name = None
        self.load_knowledge_base()
        self.init_embeddings_and_index()

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
