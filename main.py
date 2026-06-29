import os
import re
import shutil
import fitz
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import chromadb

from config import embeddings, CHROMA_PATH, UPLOAD_DIR

# ── Import all 5 services ─────────────────────────────────────
from services.query_service     import validate_query
from services.rewrite_service   import rewrite_query
from services.retrieval_service import retrieve_chunks
from services.reranking_service import rerank_chunks, compress_chunks
from services.generation_service import generate_answer


# ── In-memory chunk store (for BM25) ─────────────────────────
# Stores chunks per collection so BM25 can access them
chunk_store: dict[str, list] = {}



# ── FastAPI App ───────────────────────────────────────────────
app = FastAPI(title="OrgIQ RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def load_existing_chunks():
    """On server start → reload all chunks from ChromaDB into chunk_store"""
    try:
        client      = chromadb.PersistentClient(path=CHROMA_PATH)
        collections = client.list_collections()

        if not collections:
            print("⚠️  No collections found in ChromaDB")
            return

        for col in collections:
            collection = client.get_collection(col.name)
            results    = collection.get()

            # Rebuild Document objects from stored data
            docs = []
            for text, meta in zip(results["documents"], results["metadatas"]):
                docs.append(Document(page_content=text, metadata=meta or {}))

            chunk_store[col.name] = docs
            print(f"✅ Loaded '{col.name}' → {len(docs)} chunks")

        print(f"\n✅ Startup complete → {len(collections)} collections loaded")

    except Exception as e:
        print(f"⚠️  Startup load failed: {e}")

# ── Request Models ────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str
    pdf_name: str = "default"


# ── Ingest Helpers ────────────────────────────────────────────
def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    raw = ""
    for page in doc:
        raw += page.get_text()
    return raw


def clean_text(text: str) -> str:
    text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def split_by_headings(text: str) -> list:
    pattern  = r'\n([A-Z][A-Z\s\&\-]{3,})\n'
    parts    = re.split(pattern, text)
    sections = []

    if len(parts) == 1:
        return [{"heading": "GENERAL", "content": text.strip()}]

    if parts[0].strip():
        sections.append({"heading": "INTRODUCTION", "content": parts[0].strip()})

    for i in range(1, len(parts) - 1, 2):
        heading = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if content:
            sections.append({"heading": heading, "content": content})

    return sections


def chunk_sections(sections: list, source: str) -> list:
    splitter   = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "]
    )
    all_chunks = []
    for section in sections:
        sub = splitter.create_documents(
            texts=[section["content"]],
            metadatas=[{"source": source, "section": section["heading"], "type": "hybrid"}]
        )
        all_chunks.extend(sub)
    return all_chunks


def get_collection_name(pdf_name: str) -> str:
    return pdf_name.replace(".pdf", "").replace(" ", "_").lower()


# ── Routes ────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message"  : "OrgIQ RAG API Running 🚀",
        "endpoints": {
            "POST /ingest": "Upload + process PDF",
            "POST /ask"   : "Ask a question",
            "GET  /pdfs"  : "List all PDFs"
        }
    }


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    """
    Upload PDF → Extract → Clean → Split by headings
    → Chunk → Embed → Store in ChromaDB
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    # Save file
    pdf_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        # Process
        raw      = extract_text(pdf_path)
        cleaned  = clean_text(raw)
        sections = split_by_headings(cleaned)
        chunks   = chunk_sections(sections, source=file.filename)

        # Store in ChromaDB
        collection_name = get_collection_name(file.filename)
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_PATH,
            collection_name=collection_name
        )

        # Keep chunks in memory for BM25
        chunk_store[collection_name] = chunks

        print(f"✅ Ingested '{file.filename}' → {len(chunks)} chunks")

        return {
            "message"        : f"'{file.filename}' ingested successfully",
            "total_chunks"   : len(chunks),
            "sections_found" : len(sections),
            "pdf_name"       : file.filename
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
def ask(body: AskRequest):
    """
    Pipeline:
    Service 1 → Validate query
    Service 2 → Rewrite query (LLM)
    Service 3 → Hybrid retrieval (BM25 + Semantic)
    Service 4 → Rerank + compress chunks
    Service 5 → Generate final answer (LLM)
    """

    print(f"\n{'='*50}")
    print(f"New query: {body.question}")
    print(f"{'='*50}")

    collection_name = get_collection_name(body.pdf_name)

    # Check PDF was ingested
    if collection_name not in chunk_store:
        raise HTTPException(
            status_code=404,
            detail=f"'{body.pdf_name}' not found. Please ingest it first via POST /ingest"
        )

    # ── Service 1: Validate ───────────────────────────────────
    question = validate_query(body.question)

    # ── Service 2: Rewrite ────────────────────────────────────
    queries = rewrite_query(question)

    # ── Service 3: Retrieve ───────────────────────────────────
    chunks = retrieve_chunks(
        queries=queries,
        collection_name=collection_name,
        all_chunks=chunk_store[collection_name]
    )

    if not chunks:
        return {"answer": "No relevant information found.", "section": "", "source": ""}

    # ── Service 4: Rerank + Compress ─────────────────────────
    top_chunks = rerank_chunks(question, chunks, top_n=4)
    context    = compress_chunks(top_chunks)

    # ── Service 5: Generate ───────────────────────────────────
    result = generate_answer(question, context, top_chunks)

    print(f"\n✅ Pipeline complete")
    return result


@app.get("/pdfs")
def list_pdfs():
    pdfs = list(chunk_store.keys())
    return {"pdfs": pdfs, "total": len(pdfs)}


# ── Run ───────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
