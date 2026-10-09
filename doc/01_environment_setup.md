# 01. Environment & System Setup

## Overview
Full system setup for **Guidely**—a Retrieval-Augmented Generation (RAG) knowledge assistant running on WSL (Ubuntu) with a FastAPI backend.

---

## Architecture & File Locations
* **Project Root:** `/mnt/c/Projects/guidely` (Windows filesystem mounted in WSL).
* **Virtual Environment:** `~/.venv_guidely` (Native Linux home directory).
  * *Why native Linux?* Avoids cross-OS file translation freezes between Windows and WSL when loading heavy packages.

---

## Core Dependencies & Installation
* **Python Version:** Python 3.12+
* **CPU-only PyTorch:** Installed via lightweight wheel URL (`--index-url https://download.pytorch.org/whl/cpu`) to save ~2 GB storage and speed up loads.
* **Key Packages:**
  * `fastapi` & `uvicorn` — Web server & API routing.
  * `sentence-transformers` — Generating text embeddings.
  * `faiss-cpu` — Fast vector similarity index.
  * `groq` — LLM provider API.
  * `python-dotenv` — Environment variable management.

---

## Configuration (`.env`)
* Located at project root: `/mnt/c/Projects/guidely/.env`
* Key format:
  ```env
  GROQ_API_KEY=gsk_your_groq_key_here

Environment Verification
Run python3 test_env.py from root to verify imports and environment key loading:

Confirms ~/.venv_guidely is active (which python3).

Confirms GROQ_API_KEY is detected by dotenv.