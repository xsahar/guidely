# Guidely — Frontend Architecture & Data Flow Guide

This document explains the inner workings of Guidely's React + Vite frontend, how it boots, how state management functions, and how data flows across the full stack to the FastAPI backend.

---

## 1. Stack Overview

- **Framework:** React 18 (using Functional Components & Hooks)
- **Build Tool / Dev Server:** Vite 5 (providing instant server start and HMR)
- **Networking:** Native JavaScript `fetch` API for asynchronous HTTP requests
- **Architecture:** Single Page Application (SPA) decoupled from the backend

---

## 2. Boot Sequence: How Vite Loads React

When running `npm run dev`, Vite launches a local server at `http://localhost:5173`. The application boots in a 3-step chain:

```
index.html  ──►  src/main.jsx  ──►  src/App.jsx
(HTML Shell)      (React Bridge)      (UI Engine)
```

1. **`index.html` (The HTML Shell):**
   The single static HTML file served to the browser. It contains an empty container element:
   ```html
   <div id="root"></div>
   <script type="module" src="/src/main.jsx"></script>
   ```

2. **`src/main.jsx` (The React Bridge):**
   The JavaScript entry point executed by Vite. It initializes React, binds to `<div id="root">`, and renders the root component:
   ```jsx
   ReactDOM.createRoot(document.getElementById('root')).render(<App />)
   ```

3. **`src/App.jsx` (The UI Engine):**
   Contains the core user interface, form controls, state handlers, and API connection logic. Updating `App.jsx` immediately updates what appears on screen.

---

## 3. Developer Experience: Hot Module Replacement (HMR)

When editing and saving `src/App.jsx`, the browser updates instantly without requiring a full page refresh:

- Vite maintains a persistent WebSocket connection between the terminal dev server and the browser.
- File changes are detected instantly, recompiled in memory, and pushed over the WebSocket.
- React swaps out the modified component in the virtual DOM while preserving the rest of the application state.

---

## 4. End-to-End Data Lifecycle

When a user submits a query in the Guidely UI, data travels through four distinct phases across the full stack:

```
[ User Form Submission ] 
          │
          ▼
[ React State (query) ] ──── (fetch POST) ────► [ FastAPI Backend ]
                                                       │
                                                       ▼
                                            [ Vector Embedding & FAISS ]
                                                       │
                                                       ▼
                                            [ Groq LLM Generation ]
                                                       │
                                                       ▼
[ Dynamic UI Render ] ◄──── (JSON Payload) ────────────┘
```

### Phase A: Component State Capture (`useState`)
React manages UI variables using state hooks:
- `query`: Stores the string typed into the search bar.
- `loading`: Boolean flag disabling the submission button during active network requests.
- `result`: Stores the JSON object returned from the FastAPI backend (`{ answer, sources }`).
- `error`: Stores error messages if the server is unreachable.

### Phase B: Asynchronous HTTP Request (`fetch`)
Submitting the form invokes `handleSearch`:
1. `setLoading(true)` updates UI state to indicate progress.
2. `fetch('http://127.0.0.1:8000/query', { method: 'POST', ... })` transmits the query payload to the backend.

### Phase C: Backend Processing & CORS Validation
1. FastAPI's `CORSMiddleware` checks the `Origin: http://localhost:5173` header and allows the request.
2. The query is converted into an embedding using `all-MiniLM-L6-v2`.
3. FAISS retrieves the top relevant text chunks.
4. Groq generates a grounded answer strictly using the context chunks.
5. FastAPI returns a `200 OK` JSON response:
   ```json
   {
     "answer": "**Guidely Inc. Remote Work Policy**...",
     "sources": ["security_policy.txt", "remote_work_policy.txt"]
   }
   ```

### Phase D: Dynamic Conditional Rendering
1. `response.json()` parses the incoming payload.
2. `setResult(data)` triggers a micro-re-render in React.
3. React evaluates the conditional rendering block:
   ```jsx
   {result && (
     <div>
       <p>{result.answer}</p>
       {result.sources.map((src, i) => <span key={i}>{src}</span>)}
     </div>
   )}
   ```
4. DOM elements are generated on the fly, rendering the answer text and source badges.