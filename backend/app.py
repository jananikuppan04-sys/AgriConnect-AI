import os
import re
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="AgriConnect AI Backend")

# Configure CORS for frontend app port
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------
# DATA MODELS
# ----------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., description="Message from the user")

# ----------------------------------------------------------------------
# LOCAL KNOWLEDGE RETRIEVAL SETUP
# ----------------------------------------------------------------------
KB_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")

# Standard stop words to filter out before word scoring
STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", 
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", 
    "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", 
    "theirs", "themselves", "what", "which", "who", "whom", "this", "that", 
    "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", 
    "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", 
    "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", 
    "at", "by", "for", "with", "about", "against", "between", "into", "through", 
    "during", "before", "after", "above", "below", "to", "from", "up", "down", 
    "in", "out", "on", "off", "over", "under", "again", "further", "then", 
    "once", "here", "there", "when", "where", "why", "how", "all", "any", 
    "both", "each", "few", "more", "most", "other", "some", "such", "no", 
    "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", 
    "t", "can", "will", "just", "don", "should", "now"
}

def clean_and_tokenize(text: str) -> list[str]:
    """
    Cleans text: converts to lowercase, strips punctuation, 
    splits into words, and removes common stop words.
    """
    cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
    words = cleaned.split()
    return [w for w in words if w not in STOP_WORDS]

def load_knowledge_base() -> list[dict]:
    """
    Loads all markdown files from knowledge_base directory and 
    splits them into chunks (paragraphs/sections) with metadata.
    """
    kb_chunks = []
    if not os.path.exists(KB_DIR):
        return kb_chunks

    for filename in os.listdir(KB_DIR):
        if filename.endswith(".md"):
            file_path = os.path.join(KB_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Split content by double newlines into logical sections/paragraphs
                raw_paragraphs = content.split("\n\n")
                
                for p in raw_paragraphs:
                    p_clean = p.strip()
                    if not p_clean:
                        continue
                    
                    # Store paragraph text, tokens for matching, and the file source
                    kb_chunks.append({
                        "text": p_clean,
                        "tokens": clean_and_tokenize(p_clean),
                        "source": filename
                    })
            except Exception as e:
                print(f"Error loading file {filename}: {e}")
                
    return kb_chunks

# ----------------------------------------------------------------------
# ENDPOINTS
# ----------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "AgriConnect backend is running"
    }

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    # 7. Reject empty messages with a validation error
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message field cannot be empty."
        )

    user_message = request.message.strip()
    query_tokens = clean_and_tokenize(user_message)
    
    # If no meaningful query words are left (e.g. user input only stop words or symbols)
    if not query_tokens:
        return {
            "answer": "I do not have verified information about that yet.",
            "sources": []
        }

    # Load RAG knowledge base chunks dynamically to pick up any text changes
    chunks = load_knowledge_base()
    
    best_chunk = None
    max_score = 0

    # Keyword word-sharing scoring algorithm
    for chunk in chunks:
        # Count matching unique tokens between query and knowledge base paragraph
        matching_words = set(query_tokens).intersection(set(chunk["tokens"]))
        score = len(matching_words)
        
        # Select the chunk with the highest overlap score
        if score > max_score:
            max_score = score
            best_chunk = chunk

    # Minimum threshold of 1 matching meaningful keyword
    if max_score > 0 and best_chunk:
        # Prepend verified information context wrapper
        answer = f"Based on AgriConnect AI verified platform information:\n\n{best_chunk['text']}"
        return {
            "answer": answer,
            "sources": [best_chunk["source"]]
        }
    
    # 6. Default response when no matching information is found
    return {
        "answer": "I do not have verified information about that yet.",
        "sources": []
    }
