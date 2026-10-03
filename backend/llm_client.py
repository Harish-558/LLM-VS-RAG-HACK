import os
import requests
import json
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.active_groq_model: Optional[str] = None

    def is_api_key_configured(self) -> bool:
        return bool(self.groq_key or self.gemini_key or self.openai_key)

    def query_plain_llm(self, question: str) -> str:
        """
        Sends the question to Plain LLM without context.
        """
        system_instruction = (
            "You are a standard AI assistant answering general questions based on general pre-training data. "
            "Answer concisely. Do not guess internal proprietary corporate specs, metrics, or undisclosed dates."
        )
        prompt = f"Question: {question}\nAnswer:"

        if self.groq_key:
            return self._call_groq_api(
                system_instruction=system_instruction,
                prompt=prompt
            )
        elif self.gemini_key:
            return self._call_gemini_api(
                system_instruction=system_instruction,
                prompt=prompt
            )
        elif self.openai_key:
            return self._call_openai_api(
                system_instruction=system_instruction,
                prompt=prompt
            )
        else:
            return (
                "⚠️ API Key Not Configured. (Add GROQ_API_KEY to backend/.env)\n\n"
                f"[Plain LLM standard response]: I don't have real-time or proprietary internal data regarding '{question}'. "
                "Without ground-truth context, standard LLMs may provide generic answers or hallucinate exact model numbers and dates."
            )

    def query_rag_llm(self, question: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        Sends the question + retrieved context to LLM.
        """
        context_text = "\n\n".join([
            f"--- Document #{i+1}: {doc['title']} ---\n{doc['content']}"
            for i, doc in enumerate(retrieved_docs)
        ])

        prompt = (
            f"Context Information:\n{context_text}\n\n"
            f"Question: {question}\n\n"
            "Instruction: Answer the question strictly using the provided context information above. "
            "Include specific figures, dates, and names mentioned in the context. "
            "If the context does not contain the answer, state that clearly."
        )

        system_instruction = "You are a precise RAG assistant. Rely ONLY on the provided context to answer the question accurately."

        if self.groq_key:
            return self._call_groq_api(
                system_instruction=system_instruction,
                prompt=prompt
            )
        elif self.gemini_key:
            return self._call_gemini_api(
                system_instruction=system_instruction,
                prompt=prompt
            )
        elif self.openai_key:
            return self._call_openai_api(
                system_instruction=system_instruction,
                prompt=prompt
            )
        else:
            if retrieved_docs:
                top_doc = retrieved_docs[0]
                return (
                    "⚠️ API Key Not Configured. (Add GROQ_API_KEY to backend/.env)\n\n"
                    f"[RAG System Response grounded in '{top_doc['title']}']:\n"
                    f"{top_doc['content']}"
                )
            else:
                return (
                    "⚠️ API Key Not Configured. (Add GROQ_API_KEY to backend/.env)\n\n"
                    "[RAG System Response]: No relevant documents were retrieved from knowledge base for this query."
                )

    def _call_groq_api(self, system_instruction: str, prompt: str) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.groq_key}"
        }

        # Priority list of model candidates
        candidates = []
        custom_model = os.getenv("GROQ_MODEL", "").strip()
        if custom_model:
            candidates.append(custom_model)
        if self.active_groq_model:
            candidates.append(self.active_groq_model)
        
        default_candidates = [
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]
        for m in default_candidates:
            if m not in candidates:
                candidates.append(m)

        last_error = ""
        for model_name in candidates:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 500
            }
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        self.active_groq_model = model_name
                        return choices[0].get("message", {}).get("content", "").strip()
                last_error = f"Error from Groq API ({resp.status_code}): {resp.text}"
            except Exception as e:
                last_error = f"Failed to connect to Groq API: {str(e)}"

        return last_error

    def _call_gemini_api(self, system_instruction: str, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [{"text": f"{system_instruction}\n\n{prompt}"}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 500
            }
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
            return f"Error from Gemini API ({resp.status_code}): {resp.text}"
        except Exception as e:
            return f"Failed to connect to Gemini API: {str(e)}"

    def _call_openai_api(self, system_instruction: str, prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key}"
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 500
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
            return f"Error from OpenAI API ({resp.status_code}): {resp.text}"
        except Exception as e:
            return f"Failed to connect to OpenAI API: {str(e)}"
