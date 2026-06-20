# ── SERVICE 1: QUERY SERVICE ──────────────────────────────────
# Responsibility: Receive query from frontend, validate it,
#                 pass to next service

from fastapi import HTTPException

def validate_query(question: str) -> str:
    """
    Receives raw query from frontend
    Validates it is not empty or too short
    Returns cleaned query
    """
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    question = question.strip()

    if len(question) < 3:
        raise HTTPException(status_code=400, detail="Question too short")

    if len(question) > 1000:
        raise HTTPException(status_code=400, detail="Question too long (max 1000 chars)")

    print(f"\n[Service 1]  Query received: {question[:80]}...")
    return question
