# LLM vs RAG Comparison

A complete, lightweight, and modern project comparing factual accuracy between a **Plain LLM** and a **RAG-based System (Retrieval-Augmented Generation)** using the exact same questions.

Built with a **Kotlin Android Frontend** and a **Python FastAPI Backend** utilizing **Sentence Transformers** and **FAISS**.

---

## 🎨 UI Design & Palette

- **Theme**: Dark Navy (`#0B132B`, `#1C2541`), Primary Teal (`#00B4D8`), and Energetic Orange (`#FF6B35`).
- **Style**: Modern, clean, mobile-friendly interface with card elevations, custom badge pills, side-by-side comparison displays, and visual accuracy comparison progress indicators.

---

## 🚀 Key Features

1. **Modern Home Screen**:
   - Live accuracy overview cards for Plain LLM vs RAG System.
   - Real-time Backend Connection Status indicator & API Key alert banner.
   - Quick action shortcuts to start benchmarking.

2. **Question Input & Benchmark Screen**:
   - Custom question input field with one-tap preset benchmark chips.
   - Evaluates domain-specific questions against both standard LLM and RAG system.

3. **Side-by-Side Comparison & Evaluation**:
   - Labeled output cards showing Plain LLM vs RAG System responses along with query latency (ms).
   - **Expandable FAISS Knowledge Context Accordion**: Inspect exact document snippets and FAISS cosine similarity scores retrieved from the vector index.
   - Interactive user feedback buttons (**✓ Correct** / **✗ Incorrect**) to evaluate factual accuracy.

4. **Dynamic Accuracy Analytics**:
   - Dynamic factual accuracy percentage calculation based on actual evaluation ratings.
   - Visual progress bar chart comparing Plain LLM vs RAG System performance.

5. **API Key Setup & Fallback Handling**:
   - If `GROQ_API_KEY` is not present, the app displays a clear setup message and operates in interactive benchmark mode so you can test the system right out of the box.

---

## 📁 Repository Structure

```
.
├── backend/
│   ├── main.py                # FastAPI REST API endpoints
│   ├── rag_engine.py          # Sentence Transformers & FAISS vector search
│   ├── llm_client.py          # Groq / Gemini / OpenAI API integration
│   ├── knowledge_base.json    # Sample domain dataset (Tech, Space, Biochemistry, Policies)
│   ├── requirements.txt       # Backend dependencies
│   ├── .env                   # Environment file containing GROQ_API_KEY
│   └── test_backend.py        # Backend unit tests
├── app/
│   └── src/main/
│       ├── java/com/example/harish333c/
│       │   ├── models/        # Kotlin Data Models
│       │   ├── network/       # Retrofit & OkHttp API Client
│       │   ├── ui/            # DashboardFragment, CompareFragment, StatsFragment
│       │   └── MainActivity.kt
│       └── res/               # Layouts, colors, themes, drawables, menus
├── build.gradle.kts           # Gradle configuration
├── gradle.properties
├── settings.gradle.kts
├── .gitignore                 # GitHub clean gitignore
└── README.md
```

---

## 🛠️ Instructions to Run the Project

### 1. Run the Python Backend Server

1. Open a terminal in the project directory and navigate to `backend/`:
   ```bash
   cd backend
   ```

2. (Optional) Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your LLM API Key:
   - Ensure `GROQ_API_KEY` is set in `backend/.env`:
     ```env
     GROQ_API_KEY=your_groq_api_key_here
     ```

5. Run unit tests to verify:
   ```bash
   python -m unittest test_backend.py
   ```

6. Start the FastAPI server:
   ```bash
   python main.py
   # Or using uvicorn directly:
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

   The server will run at `http://localhost:8000`. You can inspect the interactive docs at `http://localhost:8000/docs`.

---

### 2. Run the Kotlin Android Frontend App

1. Open the root project directory in **Android Studio**.
2. Sync the project with Gradle files.
3. Launch an **Android Emulator** or connect a physical device.
4. Build & Run the app (`app`).
5. **Backend URL Settings**:
   - On **Android Emulator**, the app automatically connects to `http://10.0.2.2:8000/`.
   - On **Physical Devices**, tap the **Settings** gear icon in the top right corner of the app and enter your computer's local IP address (e.g. `http://192.168.1.5:8000`), then tap **Test Connection** & **Save**.

---

## 🧹 GitHub Cleanliness

The project `.gitignore` excludes:
- `venv`, `.venv`, `.env`
- `.gradle`, `build`, `app/build`, `.idea`
- Python `__pycache__`, `.pytest_cache`
- Model weights, model caches, binary assets

---

## 📄 License
MIT License.
