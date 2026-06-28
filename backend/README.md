# AgriConnect AI Backend

FastAPI backend server for the AgriConnect AI smart agriculture platform.

## Windows PowerShell Setup Instructions

Follow these exact steps in your Windows PowerShell terminal:

### 1. Create a Python Virtual Environment
Navigate to the backend directory and initialize the virtual environment:
```powershell
python -m venv venv
```

### 2. Activate the Virtual Environment
Activate the environment to isolate dependencies:
```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Required Dependencies
Install the packages declared in `requirements.txt`:
```powershell
pip install -r requirements.txt
```

### 4. Run the Development Server
Launch the FastAPI app with Uvicorn with auto-reload enabled:
```powershell
uvicorn app:app --reload
```

### 5. Verify the Server
Check that the server is running by visiting the health check page:
* Open your browser or tool to: **[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)**
* Expected response:
  ```json
  {"status":"ok","message":"AgriConnect backend is running"}
  ```

---

## Interactive OpenAPI Documentation

Once the server is running, you can explore, test, and run active requests against all API endpoints by visiting:
* **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** (Swagger UI interface)

---

## Chatbot Testing Examples

Here are 5 representative queries you can send to test the FAQ retrieval engine via the `/docs` UI or custom client requests:

1. **"What is AgriConnect AI?"**
   * *Target Source*: `platform_faq.md`
   * *Expected match*: Explains the general purpose of the platform.

2. **"How can I sell tomatoes?"**
   * *Target Source*: `seller_guidelines.md` or `platform_faq.md`
   * *Expected match*: Outlines listing guidelines or general crop selling FAQ steps.

3. **"How do I rent a tractor?"**
   * *Target Source*: `rental_policy.md`
   * *Expected match*: Matches the rental flow and terms steps.

4. **"How do I contact a seller?"**
   * *Target Source*: `platform_faq.md`
   * *Expected match*: Returns guidelines on reaching sellers.

5. **"What happens if I see a suspicious listing?"**
   * *Target Source*: `platform_faq.md`
   * *Expected match*: Instructs users on listing verification policies and support actions.
