from fastapi import APIRouter, HTTPException, Request
from backend.models.schemas import QueryRequest, QueryResponse

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def handle_query(request_data: QueryRequest, request: Request):
    llm_chain = request.app.state.llm_chain
    if not llm_chain:
        raise HTTPException(status_code=500, detail="LLM Chain is not initialized.")
    if not request_data.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    result = llm_chain.generate_response(request_data.query)
    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"]
    )