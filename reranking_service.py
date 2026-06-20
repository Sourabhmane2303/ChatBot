# ── SERVICE 4: RERANKING SERVICE ─────────────────────────────
# Responsibility: Rerank retrieved chunks by relevance to query
#                 Keep only top N most relevant chunks

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import llm


def rerank_chunks(question: str, chunks: list, top_n: int = 4) -> list:
    """
    Takes original question + retrieved chunks
    Scores each chunk for relevance to question
    Returns top N most relevant chunks
    """

    if not chunks:
        return []

    # If few chunks, no need to rerank
    if len(chunks) <= top_n:
        print(f"[Service 4]  Skipped reranking (only {len(chunks)} chunks)")
        return chunks

    # ── LLM based reranking ────────────────────────────────────
    prompt = ChatPromptTemplate.from_template("""
    Score how relevant this text chunk is to the question.
    Return ONLY a number from 0 to 10. Nothing else.

    Question: {question}
    Chunk: {chunk}

    Score (0-10):
    """)

    chain = prompt | llm | StrOutputParser()

    scored = []
    for chunk in chunks:
        try:
            score_str = chain.invoke({
                "question": question,
                "chunk"   : chunk.page_content[:500]
            })
            score = float(score_str.strip().split()[0])
        except Exception:
            score = 0.0

        scored.append((score, chunk))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    top_chunks = [chunk for _, chunk in scored[:top_n]]

    print(f"[Service 4] Reranked → kept top {len(top_chunks)} chunks")
    for score, chunk in scored[:top_n]:
        section = chunk.metadata.get("section", "unknown")
        print(f"            → Score: {score:.1f} | Section: {section}")

    return top_chunks


def compress_chunks(chunks: list) -> str:
    """
    Compress chunks into clean context string
    Includes section metadata for citation
    """
    parts = []
    for chunk in chunks:
        section = chunk.metadata.get("section", "")
        content = chunk.page_content.strip()
        if section:
            parts.append(f"[{section}]\n{content}")
        else:
            parts.append(content)

    context = "\n\n---\n\n".join(parts)
    print(f"[Service 4]  Context compressed → {len(context)} characters")
    return context
