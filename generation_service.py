# ── SERVICE 5: GENERATION SERVICE ────────────────────────────
# Responsibility: Take compressed context + question
#                 Generate final answer using LLM
#                 Return answer + source metadata

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import llm


def generate_answer(question: str,
                    context : str,
                    chunks  : list) -> dict:
    """
    Takes question + compressed context
    Generates final answer using LLM
    Returns answer + section + source metadata
    """

    prompt = ChatPromptTemplate.from_template("""
    You are a helpful assistant for an organization.
    Answer the question based ONLY on the context provided below.
    If the answer is not found in the context, say "I don't know based on the provided documents."
    Be concise, accurate, and helpful.

    Context:
    {context}

    Question: {question}

    Answer:
    """)

    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "question": question,
        "context" : context
    })

    # Extract metadata from top chunk
    section = ""
    source  = ""
    if chunks:
        section = chunks[0].metadata.get("section", "")
        source  = chunks[0].metadata.get("source",  "")

    print(f"[Service 5]  Answer generated ({len(answer)} chars)")
    print(f"            → Section : {section}")
    print(f"            → Source  : {source}")

    return {
        "answer" : answer.strip(),
        "section": section,
        "source" : source
    }
