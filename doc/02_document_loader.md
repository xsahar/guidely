### File 2: `docs/02_document_loader.md`

```markdown
# 02. Document Loader & Chunking Pipeline

## Overview
Module for ingesting text documents and splitting them into chunks for LLM context retrieval.

* **File Location:** `backend/services/document_loader.py`
* **Input Directory:** `backend/data/sample-docs/` (`.txt` files)

---

## Core Logic & Functions

### 1. `load_text_files(data_dir)`
* Reads all `.txt` policy files (`pto_policy.txt`, `remote_work_policy.txt`, etc.).
* Returns a list of dictionaries with raw file text and filenames.

### 2. `chunk_text(text, chunk_size=200, overlap=30)`
* **Sliding Window Strategy:** Splits text into ~200-word segments.
* **Overlap (30 words):** Shares 30 words between consecutive chunks so sentences and key context are not severed at boundaries.

### 3. `process_documents()`
* Ingests files and chunks them while attaching structured metadata:
  ```python
  {
      "id": 0,
      "filename": "pto_policy.txt",
      "chunk_index": 0,
      "text": "Guidely Inc. PTO and Leave Policy..."
  }

Quick Recall Summary
Input: Raw .txt files.

Output: List of metadata-tagged text snippets (~200 words each).