import os
import re
import fitz
import chromadb
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

GROQ_API_KEY = ""                          
CHROMA_PATH  = "/content/chroma_db"
PDF_PATH     = "/content/bank.pdf"        


print("Loading embedding model...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
print(" Embedding model ready")


llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY)
print(" Groq LLM ready")



def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    raw = ""
    for page in doc:
        raw += page.get_text()
    print(f" Extracted  → {len(raw)} characters")
    return raw



def clean_text(text):
    text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)  
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)                          
    text = re.sub(r'\n{3,}', '\n\n', text)                                   
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)                             
    text = re.sub(r' {2,}', ' ', text)                                      
    print(f" Cleaned    → {len(text.strip())} characters")
    return text.strip()



def chunk_text(text, source):
    print(" Semantic chunking in progress (uses embedding model)")

    splitter = SemanticChunker(
        embeddings=embeddings,                         
        breakpoint_threshold_type="percentile",         
        breakpoint_threshold_amount=90                  
    )

    chunks = splitter.create_documents(
        texts=[text],
        metadatas=[{"source": source}]
    )
    print(f" Chunked    → {len(chunks)} semantic chunks")
    return chunks



def embed_and_store(chunks):
    print(f" Embedding {len(chunks)} chunks locally...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    )
    print(f" Stored     → {len(chunks)} chunks in ChromaDB")
    return vectorstore


def view_chunks():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collections = client.list_collections()
    if not collections:
        print("  No collections found.")
        return
    collection = client.get_collection(collections[0].name)
    results = collection.get()
    total = len(results["ids"])
    print(f"\n Total chunks stored: {total}")
    print("=" * 60)
    for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
        print(f"\n Chunk {i+1}/{total}")
        print(f"   Source  : {meta.get('source', 'unknown')}")
        print(f"   Content : {doc[:300]}{'...' if len(doc) > 300 else ''}")
        print("-" * 60)

def ask(question):
    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    prompt = ChatPromptTemplate.from_template("""
    Answer the question based only on the context below.
    If the answer is not in the context, say "I don't know".

    Context: {context}

    Question: {question}

    Answer:
    """)

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    answer = chain.invoke(question)
    print(f"\n Question : {question}")
    print(f" Answer   : {answer}")
    return answer


print("\n Starting RAG Pipeline with Semantic Chunking")
print("=" * 60)

raw         = extract_text(PDF_PATH)
cleaned     = clean_text(raw)
chunks      = chunk_text(cleaned, source=os.path.basename(PDF_PATH))
vectorstore = embed_and_store(chunks)

print("\n Viewing stored chunks...")
view_chunks()

print("\n Pipeline complete!")


ask("What is this document about?")
