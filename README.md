# AgriConnect AI

Smart agricultural marketplace with a RAG-powered AI assistant chatbot.  
Supports English and Tamil queries grounded in a verified knowledge base.

## Architecture

```
frontend/  (React + Vite)  ──  /chat  ──►  backend/  (FastAPI)
                                              │
                                         rag_engine.py   ── ChromaDB (vector_store/)
                                         llm_service.py  ── Gemini API
                                         knowledge_base/  ── .md files (source of truth)
```

| Component | Technology |
|-----------|-----------|
| Frontend | React 19, Vite, React Router |
| Backend | FastAPI, Uvicorn |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers) |
| Vector store | ChromaDB (local persistent) |
| LLM | Gemini (primary), OpenRouter (backup) |
| Auth | Supabase |

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Rebuild vector store (first time or after knowledge base changes)
python rebuild_vectors.py

# Start the server
uvicorn app:app --reload
```

The backend runs at `http://127.0.0.1:8000`.

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env if needed (defaults work for local development)

# Start dev server
npm run dev
```

The frontend runs at `http://localhost:5173`.

### Running Tests

```bash
cd backend

# Mode A: Deterministic retrieval tests (no LLM required after vectors built)
python test_rag.py

# Mode A + B: Include live Gemini integration tests
python test_rag.py --live
```

## Deployment: Railway (Backend) + Vercel (Frontend)

### Railway Backend

1. **Push to GitHub** (ensure `.gitignore` excludes `.env`, `venv/`, `vector_store/`).

2. **Create a Railway project** and connect your GitHub repository.

3. **Set the root directory** to `backend` in Railway's service settings.

4. **Add environment variables** in Railway dashboard:
   ```
   GEMINI_API_KEY=your_key_here
   GEMINI_MODEL=gemini-2.5-flash
   FRONTEND_ORIGINS=https://your-app.vercel.app
   ```

5. **Add a Railway volume** (recommended):
   - Mount path: `/app/vector_store`  
     Persists the ChromaDB vector store across deploys.
   - Mount path: `/root/.cache/huggingface`  
     Caches the embedding model (~500 MB) so it isn't re-downloaded on every deploy.

   Without persistent volumes the system still works — the vector store auto-rebuilds
   from `knowledge_base/` at startup (~5 seconds), and the model re-downloads
   from Hugging Face (~30 seconds). Persistent volumes just make cold starts faster.

6. **Procfile** is already configured:
   ```
   web: uvicorn app:app --host 0.0.0.0 --port $PORT
   ```

7. Railway will auto-detect the `requirements.txt` and deploy.

### Vercel Frontend

1. **Create a Vercel project** and connect your GitHub repository.

2. **Set the root directory** to `frontend`.

3. **Add environment variables** in Vercel dashboard:
   ```
   VITE_API_BASE_URL=https://your-railway-backend.up.railway.app
   VITE_SUPABASE_URL=your_supabase_url
   VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

4. Vercel auto-detects Vite and deploys.

### Post-Deployment Checklist

- [ ] Backend `/health` endpoint returns `{"status": "ok"}`
- [ ] Frontend loads and chatbot UI renders
- [ ] English query "What is AgriConnect AI?" returns an answer with `platform_faq.md` source
- [ ] Tamil query returns a complete Tamil answer
- [ ] Weather query returns the safe fallback with no sources
- [ ] CORS allows requests from your Vercel domain

## Stale-Index Detection

The vector store automatically rebuilds when any of these change:
- **Embedding model** (`EMBEDDING_MODEL` in `rag_engine.py`)
- **Index version** (`INDEX_VERSION` — bump when chunking params change)
- **Knowledge base content** (SHA-256 fingerprint of all `knowledge_base/*.md` files)

No manual rebuild needed after editing knowledge base files — just restart the server.

## Project Structure

```
AgriConnect-AI/
├── .gitignore
├── README.md
├── backend/
│   ├── .env.example
│   ├── Procfile
│   ├── requirements.txt
│   ├── app.py              # FastAPI routes, Tamil rewrite, CORS
│   ├── rag_engine.py        # Embeddings, ChromaDB, retrieval
│   ├── llm_service.py       # Gemini/OpenRouter answer generation
│   ├── rebuild_vectors.py   # Manual vector store rebuild
│   ├── test_rag.py          # Automated test script
│   └── knowledge_base/
│       ├── platform_faq.md
│       ├── rental_policy.md
│       └── seller_guidelines.md
└── frontend/
    ├── .env.example
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── pages/
        │   ├── Assistant.jsx   # AI chatbot UI
        │   ├── Home.jsx
        │   ├── Marketplace.jsx
        │   ├── Login.jsx
        │   └── Signup.jsx
        ├── components/
        └── lib/
```
