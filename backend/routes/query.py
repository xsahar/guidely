import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from groq import APITimeoutError, GroqError
from backend.models.schemas import QueryRequest, QueryResponse
from backend.services.document_loader import process_documents
from backend.services.llm_chain import LLMChain
from backend.services.vector_store import VectorStore

router = APIRouter()
logger = logging.getLogger(__name__)
DOCUMENTS_DIR = Path(__file__).resolve().parents[1] / "data" / "sample-docs"
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024

@router.post("/query", response_model=QueryResponse)
def handle_query(payload: QueryRequest, request: Request):
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    llm_chain = request.app.state.llm_chain
    if not llm_chain:
        raise HTTPException(status_code=503, detail="Answer service is unavailable. Check the GROQ_API_KEY configuration.")

    try:
        result = llm_chain.generate_response(query_text, top_k=5)
    except APITimeoutError as exc:
        logger.exception("Groq request timed out.")
        raise HTTPException(status_code=504, detail="The answer provider timed out. Please retry.") from exc
    except GroqError as exc:
        logger.exception("Groq request failed.")
        raise HTTPException(status_code=502, detail="The answer provider could not complete the request.") from exc
    return QueryResponse(answer=result["answer"], sources=result["sources"])


@router.get("/documents")
def list_documents():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "documents": [
            {"name": path.name, "size": path.stat().st_size}
            for path in sorted(DOCUMENTS_DIR.iterdir())
            if path.is_file() and path.suffix.lower() == ".txt"
        ]
    }


def rebuild_services(request: Request) -> dict:
    chunks = process_documents(str(DOCUMENTS_DIR))
    vector_store = VectorStore()
    vector_store.load_or_build_index(chunks)
    request.app.state.vector_store = vector_store

    try:
        request.app.state.llm_chain = LLMChain(
            vector_store=vector_store,
            model="openai/gpt-oss-20b",
        )
    except ValueError as exc:
        request.app.state.llm_chain = None
        logger.error("Unable to initialize answer service after re-index: %s", exc)

    return {
        "documents": len({chunk["filename"] for chunk in chunks}),
        "chunks": len(chunks),
        "cache_hit": vector_store.cache_hit,
        "chunks_reembedded": vector_store.embedded_chunks,
    }


@router.post("/documents/reindex")
def reindex_documents(request: Request):
    try:
        return rebuild_services(request)
    except (OSError, ValueError, RuntimeError) as exc:
        logger.exception("Document re-indexing failed.")
        raise HTTPException(status_code=500, detail="Could not re-index the documents.") from exc


@router.post("/documents/upload")
async def upload_document(request: Request, file: UploadFile = File(...)):
    filename = Path((file.filename or "").replace("\\", "/")).name
    if not filename or filename in {".", ".."} or Path(filename).suffix.lower() != ".txt":
        raise HTTPException(status_code=400, detail="Upload a file with a .txt extension.")

    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Text files must be 2 MB or smaller.")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="The uploaded file must be valid UTF-8 text.") from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="The uploaded text file is empty.")

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    destination = DOCUMENTS_DIR / filename
    previous_content = destination.read_bytes() if destination.exists() else None
    temporary = destination.with_name(f".{filename}.tmp")
    temporary.write_bytes(content)
    temporary.replace(destination)

    try:
        result = rebuild_services(request)
    except (OSError, ValueError, RuntimeError) as exc:
        if previous_content is None:
            destination.unlink(missing_ok=True)
        else:
            destination.write_bytes(previous_content)
        logger.exception("Failed to index uploaded document %s.", filename)
        raise HTTPException(status_code=500, detail="The document could not be indexed.") from exc
    return {"filename": filename, **result}
