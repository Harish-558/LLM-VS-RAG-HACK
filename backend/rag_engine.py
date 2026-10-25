import json
import os
import io
import re
import math
from typing import List, Dict, Any, Optional

try:
    import numpy as np
except ImportError:
    np = None

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


MAX_PDF_PAGES = 50
MAX_TOTAL_CHUNKS = 500

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once",
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she",
    "should", "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "will", "with", "would", "you", "your", "yours", "yourself"
}


def tokenize_text(text: str) -> List[str]:
    """Extracts alphanumeric word tokens of length >= 2, converted to lowercase, excluding stopwords."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def extract_text_from_pdf(pdf_bytes: bytes, max_pages: int = MAX_PDF_PAGES) -> List[Dict[str, Any]]:
    """
    Extracts text page by page from raw PDF bytes up to max_pages to protect against memory spikes.
    """
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_data = []
    total_pages = min(len(reader.pages), max_pages)
    for idx in range(total_pages):
        page = reader.pages[idx]
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
        self.active_pdf_name: Optional[str] = None
        self.use_faiss = False
        self.retrieval_mode = "bm25_sparse"

        # Remote embeddings state
        self.dense_embeddings = None
        self.faiss_index = None

        # BM25 sparse index state
        self.doc_tokens: List[List[str]] = []
        self.doc_lens: List[int] = []
        self.avgdl: float = 0.0
        self.idf_dict: Dict[str, float] = {}

        self.load_knowledge_base()
        self.init_index()

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

    def init_index(self):
        """
        Builds the retrieval index using:
        1. Remote API embeddings (Gemini/OpenAI) if keys are configured.
        2. Fast, lightweight Okapi BM25 sparse index (<2 MB RAM) when using Groq or default.
        Never loads heavy PyTorch or local Transformer models at startup.
        """
        if not self.documents:
            self.use_faiss = False
            self.retrieval_mode = "empty"
            return

        texts = [f"Title: {doc['title']}\nContent: {doc['content']}" for doc in self.documents]

        # 1. Check if remote embedding provider is available (Gemini or OpenAI)
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        if gemini_key:
            remote_success = self._try_init_gemini_embeddings(texts, gemini_key)
            if remote_success:
                return

        if openai_key:
            remote_success = self._try_init_openai_embeddings(texts, openai_key)
            if remote_success:
                return

        # 2. Lightweight Okapi BM25 Sparse Index (Default for Groq / Zero memory overhead)
        self._init_bm25_index()

    def _init_bm25_index(self):
        """
        Builds an in-memory Okapi BM25 index with inverted term frequencies and IDF.
        Runs in <5ms, requires 0 external dependencies and uses < 2 MB RAM.
        """
        self.doc_tokens = []
        for doc in self.documents:
            combined_text = f"{doc.get('title', '')} {doc.get('content', '')}"
            self.doc_tokens.append(tokenize_text(combined_text))

        N = len(self.doc_tokens)
        self.doc_lens = [len(dt) for dt in self.doc_tokens]
        self.avgdl = sum(self.doc_lens) / max(N, 1)

        # Document frequency
        df: Dict[str, int] = {}
        for dt in self.doc_tokens:
            for term in set(dt):
                df[term] = df.get(term, 0) + 1

        # Smooth Okapi BM25 IDF
        self.idf_dict = {}
        for term, freq in df.items():
            self.idf_dict[term] = math.log(1.0 + (N - freq + 0.5) / (freq + 0.5))

        self.use_faiss = False
        self.retrieval_mode = "bm25_sparse"
        print(f"[RAGEngine] Initialized lightweight Okapi BM25 index with {N} documents (Memory: < 2 MB).")

    def _try_init_gemini_embeddings(self, texts: List[str], api_key: str) -> bool:
        """Attempts to fetch remote embeddings via Google Gemini text-embedding-004 API."""
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key={api_key}"
            payload = {
                "requests": [
                    {
                        "model": "models/text-embedding-004",
                        "content": {"parts": [{"text": t[:2000]}]}
                    }
                    for t in texts
                ]
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                embeddings_list = [item["values"] for item in data.get("embeddings", [])]
                if embeddings_list and len(embeddings_list) == len(texts):
                    self._setup_vector_index(embeddings_list, mode_name="remote_semantic_gemini")
                    return True
        except Exception as e:
            print(f"[RAGEngine] Gemini remote embedding notice (falling back to BM25): {e}")
        return False

    def _try_init_openai_embeddings(self, texts: List[str], api_key: str) -> bool:
        """Attempts to fetch remote embeddings via OpenAI text-embedding-3-small API."""
        try:
            import requests
            url = "https://api.openai.com/v1/embeddings"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "text-embedding-3-small",
                "input": [t[:2000] for t in texts]
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                embeddings_list = [item["embedding"] for item in data.get("data", [])]
                if embeddings_list and len(embeddings_list) == len(texts):
                    self._setup_vector_index(embeddings_list, mode_name="remote_semantic_openai")
                    return True
        except Exception as e:
            print(f"[RAGEngine] OpenAI remote embedding notice (falling back to BM25): {e}")
        return False

    def _setup_vector_index(self, embeddings_list: List[List[float]], mode_name: str):
        """Indexes dense vectors using FAISS if available, or normalized NumPy cosine similarity."""
        if np is not None:
            vecs = np.array(embeddings_list, dtype=np.float32)
            # L2 normalize for cosine similarity
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            vecs = vecs / norms

            if FAISS_AVAILABLE:
                try:
                    dim = vecs.shape[1]
                    self.faiss_index = faiss.IndexFlatIP(dim)
                    self.faiss_index.add(vecs)
                    self.use_faiss = True
                except Exception as fe:
                    print(f"[RAGEngine] FAISS init notice: {fe}")
                    self.faiss_index = None
                    self.use_faiss = False
            else:
                self.faiss_index = None
                self.use_faiss = False

            self.dense_embeddings = vecs
            self.retrieval_mode = mode_name
            print(f"[RAGEngine] Initialized {mode_name} (FAISS={self.use_faiss}) with {len(self.documents)} docs.")

    def index_pdf(self, filename: str, pdf_bytes: bytes, replace_existing: bool = True) -> Dict[str, Any]:
        """
        Extracts text from PDF, chunks it with limits to prevent memory spikes, and updates the index.
        """
        pages_data = extract_text_from_pdf(pdf_bytes, max_pages=MAX_PDF_PAGES)
        if not pages_data:
            raise ValueError("No readable text found in the uploaded PDF. Please make sure the PDF contains text.")

        pdf_docs = []
        for p in pages_data:
            chunks = chunk_page_text(p["text"], p["page"], filename)
            pdf_docs.extend(chunks)
            if len(pdf_docs) >= MAX_TOTAL_CHUNKS:
                pdf_docs = pdf_docs[:MAX_TOTAL_CHUNKS]
                print(f"[RAGEngine] Capped PDF indexing at {MAX_TOTAL_CHUNKS} chunks for memory safety.")
                break

        if replace_existing:
            self.documents = pdf_docs
        else:
            self.documents.extend(pdf_docs)
            if len(self.documents) > MAX_TOTAL_CHUNKS:
                self.documents = self.documents[:MAX_TOTAL_CHUNKS]

        self.active_pdf_name = filename
        self.init_index()

        return {
            "filename": filename,
            "pages_count": len(pages_data),
            "chunks_count": len(pdf_docs),
            "documents_total": len(self.documents)
        }

    def reset_to_default_knowledge_base(self):
        """Restores the built-in preset knowledge base."""
        self.active_pdf_name = None
        self.load_knowledge_base()
        self.init_index()

    def search(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Searches documents using either:
        1. Dense vector similarity (if remote embeddings active).
        2. High-precision Okapi BM25 ranking (default / Groq mode).
        Returns genuine relevance scores and matching document chunks.
        """
        if not self.documents:
            return []

        top_k = min(top_k, len(self.documents))

        # Mode 1: Remote Dense Vector Search
        if self.retrieval_mode.startswith("remote_semantic") and self.dense_embeddings is not None:
            dense_results = self._search_dense_vector(query, top_k)
            if dense_results:
                return dense_results

        # Mode 2: Okapi BM25 Sparse Search (High-precision term frequency / IDF)
        return self._search_bm25(query, top_k)

    def _search_bm25(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Computes genuine Okapi BM25 relevance scores for each document."""
        q_tokens = tokenize_text(query)
        if not q_tokens:
            q_tokens = query.lower().split()

        k1 = 1.5
        b = 0.75
        scored_docs = []

        for idx, (doc, dt) in enumerate(zip(self.documents, self.doc_tokens)):
            score = 0.0
            dl = self.doc_lens[idx] if idx < len(self.doc_lens) else len(dt)
            tf_dict: Dict[str, int] = {}
            for w in dt:
                tf_dict[w] = tf_dict.get(w, 0) + 1

            for qw in q_tokens:
                if qw in tf_dict:
                    tf = tf_dict[qw]
                    w_idf = self.idf_dict.get(qw, 0.5)
                    denom = tf + k1 * (1.0 - b + b * (dl / max(self.avgdl, 1.0)))
                    score += w_idf * ((tf * (k1 + 1.0)) / denom)

            # Smoothly normalize raw BM25 score to [0.0, 1.0] for meaningful display
            norm_score = round(score / (score + 3.0), 4) if score > 0 else 0.0
            scored_docs.append((norm_score, score, doc))

        # Sort descending by relevance score
        scored_docs.sort(key=lambda x: (x[0], x[1]), reverse=True)

        results = []
        for norm_score, raw_score, doc in scored_docs[:top_k]:
            d = doc.copy()
            d["relevance_score"] = float(norm_score)
            results.append(d)
        return results

    def _search_dense_vector(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Queries remote embedding provider and computes vector similarity."""
        try:
            import requests
            query_vector = None
            if "gemini" in self.retrieval_mode:
                gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={gemini_key}"
                resp = requests.post(url, json={"content": {"parts": [{"text": query}]}}, timeout=8)
                if resp.status_code == 200:
                    query_vector = resp.json().get("embedding", {}).get("values")
            elif "openai" in self.retrieval_mode:
                openai_key = os.getenv("OPENAI_API_KEY", "").strip()
                url = "https://api.openai.com/v1/embeddings"
                resp = requests.post(url, headers={"Authorization": f"Bearer {openai_key}"}, json={"model": "text-embedding-3-small", "input": query}, timeout=8)
                if resp.status_code == 200:
                    query_vector = resp.json().get("data", [{}])[0].get("embedding")

            if query_vector is not None and np is not None:
                q_vec = np.array([query_vector], dtype=np.float32)
                q_norm = np.linalg.norm(q_vec)
                if q_norm > 0:
                    q_vec = q_vec / q_norm

                if self.use_faiss and self.faiss_index is not None:
                    scores, indices = self.faiss_index.search(q_vec, top_k)
                    results = []
                    for s, i in zip(scores[0], indices[0]):
                        if 0 <= i < len(self.documents):
                            d = self.documents[i].copy()
                            d["relevance_score"] = round(float(s), 4)
                            results.append(d)
                    return results
                else:
                    # NumPy cosine similarity fallback
                    sims = np.dot(self.dense_embeddings, q_vec.T).flatten()
                    top_indices = np.argsort(sims)[::-1][:top_k]
                    results = []
                    for i in top_indices:
                        d = self.documents[i].copy()
                        d["relevance_score"] = round(float(sims[i]), 4)
                        results.append(d)
                    return results
        except Exception as e:
            print(f"[RAGEngine] Dense search notice (falling back to BM25): {e}")
        return []

    def get_all_documents(self) -> List[Dict[str, Any]]:
        return self.documents
