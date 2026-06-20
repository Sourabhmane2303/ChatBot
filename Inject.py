
# STEP 1: PDF INGESTION
# Extract → Clean → Heading Split → Semantic Chunk → Store


# ── CELL 1: INSTALL ─────────────────────────────────────────
# !pip install langchain-core \
#              langchain-community \
#              langchain-text-splitters \
#              langchain-experimental \
#              langchain-huggingface \
#              langchain-groq \
#              chromadb \
#              pymupdf \
#              sentence-transformers \
#              rank_bm25



# ── CELL 3: IMPORTS ─────────────────────────────────────────
import os
import re
import fitz
import chromadb
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ── CELL 4: CONFIG ───────────────────────────────────────────
# Save to Google Drive so chunks persist after Colab restarts
CHROMA_PATH = "./chroma_db"
PDF_PATH    = "./bank.pdf"   # ← your uploaded PDF
os.makedirs(CHROMA_PATH, exist_ok=True)

# ── CELL 5: LOAD EMBEDDING MODEL ────────────────────────────
print(" Loading embedding model...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
print(" Embedding model ready")


# ── CELL 6: FUNCTIONS ────────────────────────────────────────

# 1. Extract text + page numbers from PDF
def extract_text(pdf_path: str):
    doc      = fitz.open(pdf_path)
    pages    = []
    full_text = ""
    for i, page in enumerate(doc):
        text = page.get_text()
        pages.append({"page": i + 1, "text": text})
        full_text += text
    print(f" Extracted  → {len(full_text)} characters | {len(pages)} pages")
    return full_text, pages


# 2. Clean extracted text
def clean_text(text: str) -> str:
    text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    print(f" Cleaned    → {len(text.strip())} characters")
    return text.strip()


# 3. Split by headings
def split_by_headings(text: str) -> list:
    pattern  = r'\n([A-Z][A-Z\s\&\-]{3,})\n'
    parts    = re.split(pattern, text)
    sections = []

    # No headings found
    if len(parts) == 1:
        sections.append({"heading": "GENERAL", "content": text.strip()})
        print(f"  No headings found → treating as 1 section")
        return sections

    # Content before first heading
    if parts[0].strip():
        sections.append({
            "heading": "INTRODUCTION",
            "content": parts[0].strip()
        })

    # Heading + content pairs
    for i in range(1, len(parts) - 1, 2):
        heading = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if content:
            sections.append({"heading": heading, "content": content})

    print(f" Sections   → {len(sections)} headings detected")
    for s in sections:
        print(f"   → [{s['heading']}] {len(s['content'])} chars")
    return sections


# 4. Fixed size chunk each section (stable, no extra packages)
def chunk_sections(sections: list, source: str) -> list:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter   = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "]
    )
    all_chunks = []

    for section in sections:
        heading = section["heading"]
        content = section["content"]

        sub_chunks = splitter.create_documents(
            texts=[content],
            metadatas=[{
                "source" : source,
                "section": heading,     # ← which heading this belongs to
                "type"   : "hybrid"     # ← heading split + fixed size chunk
            }]
        )
        all_chunks.extend(sub_chunks)
        print(f"    [{heading}] → {len(sub_chunks)} chunks")

    print(f"\n Total      → {len(all_chunks)} chunks")
    return all_chunks


# 5. Embed + Store in ChromaDB
def embed_and_store(chunks: list,
                    collection_name: str = "org_knowledge") -> Chroma:
    print(f"\n Embedding {len(chunks)} chunks...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH,
        collection_name="org_knowledge"
    )

    vectorstore.persist()
    
    print(f" Stored     → {len(chunks)} chunks in ChromaDB")
    return vectorstore


# 6. View stored chunks
def view_chunks(collection_name: str = "org_knowledge"):
    client     = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(collection_name)
    results    = collection.get()
    total      = len(results["ids"])

    print(f"\n Collection : '{collection_name}'")
    print(f" Total chunks: {total}")
    print("=" * 60)
    for i, (doc, meta) in enumerate(
            zip(results["documents"], results["metadatas"])):
        print(f"\n🔹 Chunk {i+1}/{total}")
        print(f"   Section : {meta.get('section', 'unknown')}")
        print(f"   Source  : {meta.get('source',  'unknown')}")
        print(f"   Content : {doc[:250]}{'...' if len(doc) > 250 else ''}")
        print("-" * 60)


# ── CELL 7: RUN PIPELINE ─────────────────────────────────────
print("\n STEP 1: PDF Ingestion Pipeline")
print("=" * 60)

# Extract
raw_text, pages = extract_text(PDF_PATH)

# Clean
cleaned = clean_text(raw_text)

# Split by headings
sections = split_by_headings(cleaned)

# Chunk each section
chunks = chunk_sections(sections, source=os.path.basename(PDF_PATH))

# Embed + Store
vectorstore = embed_and_store(chunks)

# View
view_chunks()

print("\n STEP 1 COMPLETE!")
print(f"   Chunks stored in: {CHROMA_PATH}")
print(f"   Total chunks    : {len(chunks)}")
print("\n Ready for Step 2 → React Frontend")
