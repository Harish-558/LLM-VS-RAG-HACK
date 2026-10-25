import os
import sys
import time
import uuid
from typing import List, Dict, Any, Optional

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag_engine import RAGEngine
from llm_client import LLMClient

app = FastAPI(
    title="LLM vs RAG Comparison API",
    description="Backend API comparing Plain LLM vs RAG-augmented LLM accuracy using Sentence Transformers and FAISS",
    version="1.0.0"
)

# Enable CORS for Android emulator, local dev, devices
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG Engine and LLM Client
rag_engine = RAGEngine(knowledge_base_path="knowledge_base.json")
llm_client = LLMClient()

# In-memory Evaluation Database
evaluations_db: List[Dict[str, Any]] = []

# Models
class CompareRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Question to send to both models")

class RetrievedDoc(BaseModel):
    id: Optional[str] = None
    title: str
    category: Optional[str] = "General"
    content: str
    relevance_score: float
    page: Optional[int] = None

class CompareResponse(BaseModel):
    id: str
    question: str
    plain_llm_answer: str
    plain_llm_latency_ms: int
    rag_answer: str
    rag_latency_ms: int
    retrieved_docs: List[RetrievedDoc]
    api_key_configured: bool

class EvaluateRequest(BaseModel):
    comparison_id: str
    question: str
    plain_llm_correct: bool
    rag_correct: bool

class StatsResponse(BaseModel):
    total_evaluated: int
    plain_llm_correct_count: int
    rag_correct_count: int
    plain_llm_accuracy_pct: float
    rag_accuracy_pct: float
    accuracy_improvement_pct: float

# Routes
@app.get("/")
def read_root():
    return {
        "service": "LLM vs RAG Comparison API",
        "status": "online",
        "api_key_configured": llm_client.is_api_key_configured(),
        "docs_count": len(rag_engine.get_all_documents()),
        "faiss_active": rag_engine.use_faiss,
        "retrieval_mode": rag_engine.retrieval_mode
    }

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "api_key_configured": llm_client.is_api_key_configured(),
        "documents_count": len(rag_engine.get_all_documents()),
        "faiss_active": rag_engine.use_faiss,
        "active_pdf": rag_engine.active_pdf_name,
        "retrieval_mode": rag_engine.retrieval_mode,
        "message": "API key configured successfully!" if llm_client.is_api_key_configured() else "API key missing. Add GROQ_API_KEY to Render Environment Variables or backend/.env file."
    }

@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")

    try:
        result = rag_engine.index_pdf(filename=file.filename, pdf_bytes=content, replace_existing=True)
        return {
            "status": "success",
            "filename": result["filename"],
            "pages_count": result["pages_count"],
            "chunks_count": result["chunks_count"],
            "documents_total": result["documents_total"],
            "message": f"Successfully indexed {result['chunks_count']} sections from {result['filename']} ({result['pages_count']} pages)."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.post("/api/reset-knowledge-base")
def reset_knowledge_base():
    rag_engine.reset_to_default_knowledge_base()
    return {
        "status": "online",
        "api_key_configured": llm_client.is_api_key_configured(),
        "documents_count": len(rag_engine.get_all_documents()),
        "faiss_active": rag_engine.use_faiss,
        "active_pdf": None,
        "retrieval_mode": rag_engine.retrieval_mode,
        "message": "Reset to default knowledge base successfully."
    }

@app.get("/api/sample-questions")
def get_sample_questions():
    return [
        {
            "id": "q1",
            "category": "Technology",
            "question": "What is the exact qubit count and gate fidelity of the Quantum Nova-X Processor?"
        },
        {
            "id": "q2",
            "category": "Aeronautics",
            "question": "What is the maximum payload and flight range of the Aetheris Drone AAMD-4?"
        },
        {
            "id": "q3",
            "category": "Policy",
            "question": "How many days do Apex software customers have to request a 100% refund?"
        },
        {
            "id": "q4",
            "category": "Space",
            "question": "What primary spectrometer instrument does the Helios-9 Mars Rover carry and how deep can it inspect?"
        },
        {
            "id": "q5",
            "category": "Biochemistry",
            "question": "What exact reaction temperature and incubation duration are needed for BioMed Synth-7?"
        }
    ]

@app.post("/api/compare", response_model=CompareResponse)
def compare_llm_vs_rag(req: CompareRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    comparison_id = f"cmp_{uuid.uuid4().hex[:8]}"

    # 1. Plain LLM Query
    start_llm = time.time()
    plain_answer = llm_client.query_plain_llm(question)
    llm_latency_ms = int((time.time() - start_llm) * 1000)

    # 2. RAG Retrieval & Query
    start_rag = time.time()
    retrieved_docs_raw = rag_engine.search(question, top_k=2)
    rag_answer = llm_client.query_rag_llm(question, retrieved_docs_raw)
    rag_latency_ms = int((time.time() - start_rag) * 1000)

    formatted_docs = [
        RetrievedDoc(
            id=doc.get("id"),
            title=doc.get("title", "Untitled Document"),
            category=doc.get("category", "General"),
            content=doc.get("content", ""),
            relevance_score=round(doc.get("relevance_score", 0.0), 4),
            page=doc.get("page")
        )
        for doc in retrieved_docs_raw
    ]

    return CompareResponse(
        id=comparison_id,
        question=question,
        plain_llm_answer=plain_answer,
        plain_llm_latency_ms=llm_latency_ms,
        rag_answer=rag_answer,
        rag_latency_ms=rag_latency_ms,
        retrieved_docs=formatted_docs,
        api_key_configured=llm_client.is_api_key_configured()
    )

@app.post("/api/evaluate", response_model=StatsResponse)
def submit_evaluation(eval_req: EvaluateRequest):
    evaluations_db.append({
        "id": eval_req.comparison_id,
        "question": eval_req.question,
        "plain_llm_correct": eval_req.plain_llm_correct,
        "rag_correct": eval_req.rag_correct,
        "timestamp": time.time()
    })
    return compute_stats()

@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    return compute_stats()

@app.get("/api/knowledge-base")
def get_knowledge_base():
    return rag_engine.get_all_documents()

def compute_stats() -> StatsResponse:
    total = len(evaluations_db)
    if total == 0:
        return StatsResponse(
            total_evaluated=0,
            plain_llm_correct_count=0,
            rag_correct_count=0,
            plain_llm_accuracy_pct=0.0,
            rag_accuracy_pct=0.0,
            accuracy_improvement_pct=0.0
        )

    plain_correct = sum(1 for e in evaluations_db if e["plain_llm_correct"])
    rag_correct = sum(1 for e in evaluations_db if e["rag_correct"])

    plain_acc = round((plain_correct / total) * 100.0, 1)
    rag_acc = round((rag_correct / total) * 100.0, 1)
    improvement = round(rag_acc - plain_acc, 1)

    return StatsResponse(
        total_evaluated=total,
        plain_llm_correct_count=plain_correct,
        rag_correct_count=rag_correct,
        plain_llm_accuracy_pct=plain_acc,
        rag_accuracy_pct=rag_acc,
        accuracy_improvement_pct=improvement
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
