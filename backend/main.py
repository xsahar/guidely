import os
import logging
from contextlib import asynccontextmanager
from statistics import median
from threading import Lock
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.services.document_loader import process_documents
from backend.services.vector_store import VectorStore
from backend.services.llm_chain import LLMChain
from backend.routes.query import router as query_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    docs_path = os.path.join(os.path.dirname(__file__), "data", "sample-docs")
    chunks = process_documents(docs_path)
    application.state.vector_store.load_or_build_index(chunks)
    try:
        application.state.llm_chain = LLMChain(
            vector_store=application.state.vector_store, model="openai/gpt-oss-20b"
        )
    except ValueError as exc:
        logger.error("Answer service is unavailable: %s", exc)
    logger.info(
        "Guidely initialized: %d documents, %d chunks, embedding cache %s.",
        len({chunk["filename"] for chunk in chunks}),
        len(chunks),
        "hit" if application.state.vector_store.cache_hit else "miss",
    )
    yield


app = FastAPI(title="Guidely API", version="1.0.0", lifespan=lifespan)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store instances on app state
app.state.vector_store = VectorStore()
app.state.llm_chain = None
app.state.metrics = {
    "request_count": 0,
    "failure_counts": {},
    "failure_types": {},
    "durations_ms": [],
    "lock": Lock(),
}


@app.middleware("http")
async def collect_request_metrics(request, call_next):
    started = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logger.exception("Unhandled request error for %s %s", request.method, request.url.path)
        raise
    finally:
        if request.url.path == "/query":
            metrics = request.app.state.metrics
            duration_ms = (perf_counter() - started) * 1000
            with metrics["lock"]:
                metrics["request_count"] += 1
                metrics["durations_ms"].append(duration_ms)
                del metrics["durations_ms"][:-1000]
                if status_code >= 400:
                    key = str(status_code)
                    metrics["failure_counts"][key] = metrics["failure_counts"].get(key, 0) + 1
                    failure_type = {
                        400: "invalid_query",
                        422: "request_validation",
                        502: "provider_error",
                        503: "answer_service_unavailable",
                        504: "provider_timeout",
                    }.get(status_code, "server_error" if status_code >= 500 else "client_error")
                    metrics["failure_types"][failure_type] = (
                        metrics["failure_types"].get(failure_type, 0) + 1
                    )
            logger.info(
                "Query completed with status %d in %.2f ms.",
                status_code,
                duration_ms,
            )


@app.get("/")
def read_root():
    return {"message": "Guidely API is running!"}


@app.get("/metrics")
def read_metrics():
    metrics = app.state.metrics
    with metrics["lock"]:
        durations = sorted(metrics["durations_ms"])
        count = len(durations)
        p95_index = max(0, int(count * 0.95 + 0.999) - 1)
        request_count = metrics["request_count"]
        latency = {
            "sample_count": count,
            "median_ms": round(median(durations), 2) if durations else None,
            "p95_ms": round(durations[p95_index], 2) if durations else None,
        }
        failures = dict(metrics["failure_counts"])
        failure_types = dict(metrics["failure_types"])

    vector_store = app.state.vector_store
    return {
        "query_requests": request_count,
        "query_failures_by_status": failures,
        "query_failures_by_type": failure_types,
        "query_latency": latency,
        "embedding_cache": {
            "last_load_was_hit": vector_store.cache_hit,
            "chunks_reembedded_on_last_load": vector_store.embedded_chunks,
        },
    }


# Include routes
app.include_router(query_router)