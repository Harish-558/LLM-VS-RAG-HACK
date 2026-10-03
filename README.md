# LLM vs RAG Comparison

A project comparing factual accuracy between a Plain LLM and a RAG-based system using the same questions.

Built with a Kotlin Android frontend and a Python FastAPI backend using Sentence Transformers and FAISS.

## Key Features

- Compare answers from a plain LLM and a RAG system.
- Submit questions and view responses side by side.
- Retrieve relevant information from a knowledge base using FAISS.
- Evaluate factual accuracy with user feedback.
- View performance and accuracy statistics.
- Connect the Android app to the Python backend.

## Project Structure

- `app/` — Kotlin Android application
- `backend/` — Python FastAPI backend
- `knowledge_base.json` — Sample knowledge dataset
- `requirements.txt` — Python dependencies
- `.gitignore` — Files excluded from Git

## Running the Backend

1. Open CMD in the backend folder:

   ```cmd
   cd backend