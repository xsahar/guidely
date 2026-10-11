# Guidely Project Audit

This document answers each audit question with the current implementation and test evidence. Results are based on the checked-in project, manual checks reported during the audit, and the reproducible local evaluator. Metrics from the small sample corpus do not guarantee general or live-LLM performance.

## Preliminary

1. **Does the project follow the repository structure described in the project requirements?**
   The repository has separate `frontend/` and `backend/` applications, with backend routes, models, services, and sample data organized in their own directories.

2. **Does `requirements.txt` include the required Python libraries (FastAPI, OpenAI, FAISS or equivalent, pandas, NumPy, etc.)?**
   It includes FastAPI, the OpenAI SDK, FAISS, pandas, NumPy, Sentence Transformers, Groq, and the other backend dependencies. Groq is the configured answer-generation provider; Sentence Transformers supplies compatible local embeddings.

3. **Are the key directories and files present (`frontend/`, `backend/`, `routes/`, `models/`, `data/sample-docs/`)?**
   The frontend, backend, backend routes and models, and `backend/data/sample-docs/` are present.

4. **Does the project run locally without errors when following the setup steps?**
   The user confirmed that the app works when both the backend and frontend development servers are running. The earlier “Failed to fetch” happened after the backend terminal was closed.

## Frontend (React / Vite)

5. **Does the UI contain two main views?**
   It has an Ask a Question view and a Manage Documents view.

6. **Can users type a question, see the generated answer, and view referenced documents in Ask a Question?**
   Users can submit questions and see the answer and returned source filenames. A tested PTO question displayed `pto_policy.txt`.

7. **Can admins upload, edit, or re-index documents in Manage Documents?**
   The UI supports uploading or replacing `.txt` files and re-indexing saved files. It does not provide an in-app text editor; edit a file outside the app and then re-index it.

8. **Are loading states and error messages displayed?**
   Search, document loading, upload, and re-index operations display progress states. API errors are shown in the UI.

9. **Does each answer clearly show sources (filenames, snippets, or document titles)?**
   Returned source filenames are displayed. The UI change also ensures it does not hide returned citations just because an answer includes a partial uncertainty statement. Citations identify documents, not highlighted snippets.

10. **Is the UI clean, functional, and responsive?**
    The user successfully used the interface. Responsive styles adapt the navigation, search form, and document table for narrow screens.

## Backend (FastAPI)

11. **Does the backend expose working endpoints for the document, indexing, search, query, and JSON-response flows?**
    The API provides document listing/upload/re-indexing and query endpoints; manual checks and automated tests exercise these flows.

12. **Can the backend upload and store documents?**
    `POST /documents/upload` stores valid UTF-8 `.txt` files, replaces a file with the same name, and indexes the result immediately.

13. **Can the backend generate embeddings and persist them to the vector database?**
    Text chunks are embedded and stored in FAISS; the index and metadata are cached on disk.

14. **Can the backend retrieve stored embeddings for similarity search?**
    The FAISS index supports similarity search over normalized embeddings. Search results are filtered to avoid weak matches.

15. **Can the backend handle a query through embedding, search, LLM answer generation, and references?**
    `POST /query` follows that flow. Swagger returned a supported PTO answer with `pto_policy.txt`.

16. **Does the backend return clear JSON responses with relevant metadata?**
    `/query` returns `answer` and `sources`; `/documents` returns filenames and byte sizes; `/documents/reindex` reports document/chunk counts and cache details. The query response does not expose similarity scores or snippets.

17. **Are the listed error cases handled gracefully?**
    The tested cases return explicit errors or a no-result abstention. The UI displays backend responses and now gives recovery instructions when it cannot connect to the backend.

18. **Is empty or missing query input handled?**
    An empty query returns HTTP 400 with `Query string cannot be empty.` A missing `query` field returns HTTP 422 request validation.

19. **Are missing or invalid API keys handled?**
    A missing key makes the answer service unavailable and queries return HTTP 503. A temporary invalid key was tested on a separate server: Groq rejected it with 401 and the API returned HTTP 502. The real key was not changed or exposed.

20. **Are corrupted document files handled?**
    Invalid UTF-8 uploads are rejected with HTTP 400 and a clear message. During directory indexing, unreadable/corrupt UTF-8 files are logged and skipped; automated tests cover this behavior.

21. **Is an empty vector-search result handled?**
    An out-of-scope cafeteria question returned HTTP 200 with an abstention answer and an empty `sources` list.

22. **Are model timeouts and API errors handled?**
    Provider timeouts map to HTTP 504 and other Groq provider errors map to HTTP 502. Automated tests cover these mappings; an invalid-key provider error was also checked manually.

23. **Do error cases return appropriate HTTP status codes and clear messages?**
    Observed responses include HTTP 400 for an empty query and invalid UTF-8 upload, HTTP 422 for a missing field, HTTP 502 for an invalid provider key, and HTTP 200 with no citations for no-result retrieval. Tests cover HTTP 504 for provider timeout and HTTP 503 when the answer service is unavailable.

24. **Does the UI display friendly error states for failed requests?**
    Backend-provided errors appear in a visible error box. Network failures now explain that the backend at `http://127.0.0.1:8000` is unreachable and tell the user how to start it with `uvicorn backend.main:app --reload`. The frontend lint/build checks pass.

## AI & Processing

25. **Are documents converted to text and split into manageable chunks before embedding?**
    Supported UTF-8 `.txt` documents are read and split into overlapping word chunks before embedding. PDF and Word conversion are not implemented.

26. **Are embeddings generated with OpenAI or a compatible model and stored in a vector database?**
    Sentence Transformers (`all-MiniLM-L6-v2`) generates local embeddings, which are stored and searched in FAISS. This meets the audit’s “OpenAI or compatible model” wording without requiring OpenAI embeddings.

27. **Is caching implemented to prevent re-embedding unchanged files?**
    A content/model/dimension fingerprint validates the persisted FAISS index. An unchanged reload reuses the cache; the evaluator measured 0 of 7 chunks re-embedded.

28. **Does the system retrieve relevant chunks before generating an answer?**
    FAISS search runs first. Only retrieved chunks that pass relevance filtering are sent to the answer-generation step.

29. **Are retrieved chunks and the question passed to an LLM for contextual response generation?**
    The answer prompt contains the retrieved document context and the user’s question, and instructs the provider to answer only from that context.

30. **Does the final response include document references or citations?**
    Successful query JSON includes source filenames, which the UI displays. No-result or abstention responses have no source citations.

31. **Are automated metrics logged in the backend?**
    `GET /metrics` reports request count, query latency, failure counts by status/type, and embedding-cache state.

32. **Are response latencies recorded with median and p95 calculations?**
    The backend calculates observed median and p95 query latency. The values depend on the machine and answer provider.

33. **Is cache effectiveness recorded?**
    Metrics and startup logs report cache-hit status and the number of chunks re-embedded on the latest index load.

34. **Are failure types and counts recorded?**
    The metrics endpoint reports query failures by HTTP status and categorized failure type.

## Dataset

35. **Are at least five example documents included in `data/sample-docs/`?**
    Seven `.txt` files are present, including PTO, IT, remote-work, security, conduct, and WSL/API notes.

36. **Are the document contents realistic and varied?**
    The policy samples cover leave, IT, remote work, security, and workplace conduct. A short WSL/API configuration note is also included.

37. **Are long files chunked correctly for embedding?**
    An automated test checks chunk count and overlap on a 400-word input. The current sample policies are short, so this test supplies the long-input evidence.

## Code Quality

38. **Is the backend organized into logical folders such as routes, models, and data?**
    Routes, schemas/models, services, and data are separated into backend subdirectories.

39. **Are reusable utilities such as chunking, embedding, and search modularized?**
    Document loading/chunking, vector embedding/search/cache, LLM orchestration, and HTTP routes are separated into modules.

40. **Is the code clean, commented, and readable?**
    The project uses focused modules, descriptive names, and docstrings. Python compilation, backend tests, frontend lint, and frontend build have passed. Comments are used where they clarify behavior rather than on every line.

41. **Is sensitive data secured through `.env` files or environment variables?**
    The Groq key is read from `GROQ_API_KEY`; `.env` is ignored by Git. The user confirmed that the file named `api-key (cursor).txt` contains WSL settings, not a key, though renaming it would reduce confusion.

## Evaluation and Metrics

42. **Does `README.md` include a metrics table with results for the required metrics?**
    The README now includes results for retrieval, citation coverage, source precision, cached local latency, cache reuse, live latency observation, and failure handling.

43. **Does the README explain the project’s objective and purpose?**
    It describes Guidely as an internal RAG knowledge assistant for company policy documents.

44. **Does the README explain embeddings, retrieval, and answer generation?**
    It documents the local Sentence Transformers embeddings, FAISS search, and Groq-backed grounded answer generation.

45. **Does the README explain how to run both the backend and frontend?**
    It links to `SETUP.md`, which gives separate terminal instructions for both development servers.

46. **Does the README explain testing, metrics implementation, and results?**
    It documents the evaluator and unit-test commands, describes the metrics endpoint, and includes current measured results with their limitations.

47. **Does Retrieval@k meet the target of at least 80% relevant documents in the top three?**
    The current labeled evaluation measured 9/9 (100%) on this small sample set.

48. **Does answer reference coverage meet the target of at least 90%?**
    The offline evaluator measured 9/9 (100%) responses with at least one labeled-correct source. It uses a stub answer generator, so it verifies citation propagation, not live LLM factuality.

49. **Does latency meet median-under-3-seconds and p95-under-5-seconds targets with cached embeddings?**
    The 45-run cached local pipeline benchmark, with an offline answer stub, measured 15.99 ms median and 21.40 ms p95. A separate live `/metrics` snapshot measured 8.25 ms median and 747.77 ms p95 across seven requests. Live performance varies with runtime and provider.

50. **Does unchanged-document embedding cache effectiveness meet the 100% target?**
    A repeated unchanged-index load reused all embeddings: 0 of 7 chunks were re-embedded.

51. **Does failure handling return the expected responses for the tested cases?**
    Automated tests and manual API checks cover empty/missing queries, unavailable service, invalid provider key, provider timeout, invalid UTF-8, and no-result retrieval.

52. **Does source precision meet the target of at least 80%?**
    The labeled offline evaluation measured 10/10 citations matching the labeled source sets. This is file-level citation precision on a small hand-labeled sample; it does not measure highlighted-snippet alignment or broad live-answer quality.

53. **Is cache effectiveness demonstrated through logs?**
    Startup logs report when cached embeddings are loaded, and `/metrics` exposes whether the most recent index load was a hit and how many chunks were re-embedded.

54. **Do logs show repeated-query cache hits, or do startup logs show cached embeddings loaded from storage?**
    Startup logs show cached embeddings loaded from disk. The cache applies to index/embedding reuse, not to repeated query answers.

55. **Are test results realistic and reproducible?**
    The evaluator uses the project’s local documents, real embeddings and FAISS search, labeled query/source pairs, a cache reload, and timed warmed runs. It is reproducible offline; the answer generator is stubbed, and the small dataset limits generalization.

56. **Is overall search relevance above 80% and reference coverage above 90%?**
    Both targets are exceeded on the current labeled sample: Retrieval@3 is 100% (9/9), and offline citation coverage is 100% (9/9). These results do not establish live LLM factual accuracy across broader questions.
