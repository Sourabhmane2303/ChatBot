# ── SERVICE 2: QUERY REWRITE SERVICE ─────────────────────────
# Responsibility: Use LLM to rewrite the query in multiple ways
#                 Solves: "aims" vs "objectives" synonym problem

from config import llm
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

def rewrite_query(question: str) -> list[str]:
    """
    Takes original query
    LLM rewrites it 3 different ways
    Returns all 4 versions (original + 3 rewrites)
    Solves semantic mismatch problem
    """

    prompt = ChatPromptTemplate.from_template("""
    You are a query rewriting assistant.
    Generate 3 different ways to ask the same question.
    Use synonyms and different phrasings.
    Return ONLY the 3 questions, one per line.
    No numbering, no explanations, no extra text.

    Original question: {question}
    """)

    chain = prompt | llm | StrOutputParser()

    try:
        result    = chain.invoke({"question": question})
        rewrites  = [q.strip() for q in result.strip().split("\n") if q.strip()]
        rewrites  = rewrites[:3]  # take max 3

        all_queries = [question] + rewrites

        print(f"[Service 2]  Query rewritten into {len(all_queries)} versions:")
        for i, q in enumerate(all_queries):
            print(f"           {i+1}. {q}")

        return all_queries

    except Exception as e:
        # If rewrite fails, just use original query
        print(f"[Service 2]   Rewrite failed, using original: {e}")
        return [question]
