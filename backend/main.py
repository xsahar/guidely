from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Guidely Knowledge Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "online", "message": "Guidely API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "docs_count": 0, "chunks_count": 0, "queries_served": 0}

