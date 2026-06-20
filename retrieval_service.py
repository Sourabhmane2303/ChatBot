from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import Chroma
from config import embeddings, CHROMA_PATH

def retrieve_chunks(queries, collection_name, all_chunks):

    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
        collection_name=collection_name
    )

    bm25_retriever = BM25Retriever.from_documents(all_chunks)
    bm25_retriever.k = 4

    all_docs = []
    for query in queries:
        # Semantic search
        semantic_docs = vectorstore.similarity_search(query, k=4)
        # BM25 search
        bm25_docs = bm25_retriever.invoke(query)

        all_docs.extend(semantic_docs)
        all_docs.extend(bm25_docs)

    # Deduplicate
    seen = set()
    unique_docs = []
    for doc in all_docs:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique_docs.append(doc)

    print(f"[Service 3]  Retrieved {len(unique_docs)} unique chunks")
    return unique_docs
