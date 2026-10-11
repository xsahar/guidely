Guidely
Preliminary
Does the project follow the structure described in the subject Project Repository Structure section?

YES

NO
Does the requirements.txt file include all required Python libraries (FastAPI, OpenAI, FAISS or equivalent, pandas, numpy, etc.)?

YES

NO
Are all key directories and files present (frontend/, backend/, routes/, models/, data/sample-docs/)?

YES

NO
Does the project run locally without errors when following setup steps?

YES

NO
Frontend (React / Vite)
Does the user interface contain two main views?

YES

NO
Ask a Question: Users can type a question, see the generated answer, and view the referenced documents.

Manage Documents: Admins can upload, edit, or re-index documents.

Are loading states and error messages displayed properly?

YES

NO
Does each answer clearly show the sources (file names, snippets, or document titles)?

YES

NO
Is the UI clean, functional, and responsive?

YES

NO
Backend (FastAPI)
Does the backend expose working endpoints for:

YES

NO
Uploading and storing documents

Generating embeddings and persisting them to the vector database

Retrieving stored embeddings for similarity search operations

Handling a user query (embedding → search → LLM answer → references)

Returning clear JSON responses with relevant metadata

Are these specific error cases handled gracefully?

YES

NO
Empty or missing query input

Missing or invalid API key

Corrupted document files

No results found in vector search

Model timeout or API errors

Does each error case return appropriate HTTP status codes (4xx/5xx) with clear error messages?

YES

NO
Does the UI display friendly error states for failed requests?

YES

NO
AI & Processing
Are documents converted to text and split into manageable chunks before embedding?

YES

NO
Are embeddings generated using OpenAI or a compatible model and stored in a vector database (FAISS, Pinecone, Weaviate, etc.)?

YES

NO
Is caching implemented to prevent re-embedding unchanged files?

YES

NO
Does the system retrieve relevant chunks before generating the answer?

YES

NO
Are retrieved chunks and question passed to an LLM for contextual response generation?

YES

NO
Does the final response include document references or source citations?

YES

NO
Are automated metrics logged in the backend?

YES

NO
Latency (response times with median and p95 calculations)

Cache effectiveness (cache hits vs. new embeddings generated)

Failure cases (error types and counts)

Dataset
Are at least five example documents included in data/sample-docs/?

YES

NO
Are document contents realistic and varied (e.g., policy, guide, FAQ)?

YES

NO
Are long files chunked correctly for embedding?

YES

NO
Code Quality
Is the backend organized into logical folders (routes/, models/, data/)?

YES

NO
Are reusable utility functions (chunking, embedding, search) properly modularized?

YES

NO
Is the code clean, commented, and readable?

YES

NO
Is sensitive data secured using .env files or system environment variables?

YES

NO
Evaluation and Metrics
Does the project include a metrics table in README.md showing test results for all required metrics?

YES

NO
Does the README clearly explain:

YES

NO
The project's objective and purpose

How embeddings, retrieval, and answer generation work

How to run both the backend and frontend

The Testing & Metrics implementation and results

Are the following metrics documented with test results?

YES

NO
Retrieval@k (relevant document appears in top-3 results) - Target: ≥ 80%

Answer reference coverage (answers include at least one correct source) - Target: ≥ 90%

Latency (median < 3s, p95 < 5s with cached embeddings)

Embedding cache effectiveness (100% cache hits for unchanged docs)

Failure handling (proper error responses for specific test cases)

Source precision (≥ 80% correct snippet alignment if highlighting is implemented)

Is cache effectiveness demonstrated through logs?

YES

NO
Logs show 100% cache hit rate for repeated queries with unchanged documents, OR

Startup logs show loading of cached embeddings from disk/database

Are test results realistic and reproducible?

YES

NO
Is the overall search relevance above 80% and reference accuracy above 90%?

YES

NO