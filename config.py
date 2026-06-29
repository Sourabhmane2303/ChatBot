import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHROMA_PATH  = os.getenv("CHROMA_PATH", "./chroma_db")
UPLOAD_DIR   = os.getenv("UPLOAD_DIR",  "./pdfs")

os.makedirs(CHROMA_PATH, exist_ok=True)
os.makedirs(UPLOAD_DIR,  exist_ok=True)

# ── Models (loaded once, reused everywhere) ────────────────────
print("⏳ Loading embedding model...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
print("✅ Embedding model ready")

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY)
print("✅ Groq LLM ready")
