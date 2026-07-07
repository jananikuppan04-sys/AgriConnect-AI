# AgriConnect AI Backend

FastAPI backend server for the AgriConnect AI smart agriculture platform.
Version 2 uses **local semantic retrieval** via ChromaDB + sentence-transformers.

---

## How Semantic Retrieval Works (Plain Language)

Instead of counting matching keywords, the chatbot now understands *meaning*:

1. **Chunking** – Every Markdown file in `knowledge_base/` is split into
   overlapping windows of ~300 words.
2. **Embedding** – The `all-MiniLM-L6-v2` model converts each chunk into a
   384-number vector that captures its meaning (not just its words).
3. **Storage** – All vectors are saved locally in `backend/vector_store/`
   using ChromaDB. They are only generated once and reloaded on subsequent
   restarts (fast).
4. **Query** – When a user asks a question, the same model embeds it, and
   ChromaDB finds the closest chunk by cosine similarity.
5. **Answer** – The nearest chunk is returned as the answer with its source
   filename. Chunks that are too distant trigger the fallback response.

This means "Can I borrow a tractor?" will correctly match rental content
even though the word "borrow" never appears in the Markdown files.

---

## Windows PowerShell Setup Instructions

### 1. Create a Python Virtual Environment
```powershell
python -m venv venv
```

### 2. Activate the Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install All Dependencies
```powershell
pip install -r requirements.txt
```
> ⚠ `sentence-transformers` downloads the embedding model (~90 MB) on first
> run. Subsequent runs load it from the local cache instantly.

### 4. Run the Development Server
```powershell
uvicorn app:app --reload
```

### 5. Verify the Server
Open **[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)**

Expected response:
```json
{"status":"ok","message":"AgriConnect backend is running"}
```

---

## Interactive API Documentation

**[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** — Swagger UI

Use the `POST /chat` panel to run test queries directly in the browser.

---

## Test Questions

| Question | Expected result |
|---|---|
| Can I borrow a tractor? | Answer from `rental_policy.md` |
| I want to put vegetables for sale. | Answer from `seller_guidelines.md` |
| How can I contact the person selling a product? | Answer from `platform_faq.md` |
| What should I do about a fake listing? | Answer from `platform_faq.md` |
| What is the weather tomorrow? | Fallback: *"I do not have verified information about that yet."* |

---

## Startup Terminal Logs

When the server starts you will see:

```
INFO │ ============================================================
INFO │ AgriConnect AI  –  RAG Engine starting up …
INFO │ ============================================================
INFO │ 🤖 Loading embedding model: all-MiniLM-L6-v2 …
INFO │ ✅ Embedding model loaded.
INFO │ 📂 Markdown files discovered: ['platform_faq.md', 'rental_policy.md', 'seller_guidelines.md']
INFO │ ✅ Total chunks created: N
INFO │ ✅ Vector store ready – N vectors indexed.
INFO │ ============================================================
INFO │ RAG Engine ready. Listening for queries.
INFO │ ============================================================
```
