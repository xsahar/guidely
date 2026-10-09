
```markdown
# Guidely — Local Development Setup Guide (WSL / Linux)

Follow these steps in **WSL (Ubuntu/Linux terminal)** to set up and run the project locally.

---

## 1. Prerequisites

Ensure you have the following installed in your WSL environment:

- **Python:** 3.10+ (Recommended: Python 3.12)
- **Node.js & npm:** Node.js v18.19+ (Required for the React / Vite frontend)
- **Git:** Configured for repository tracking
- **Groq API Key:** Required for LLM answer generation

---

## 2. Virtual Environment Setup

The virtual environment is maintained in your user home directory to keep project repository tracking clean:

```bash
# Activate the existing virtual environment
source ~/.venv_guidely/bin/activate

```

*(You will see `(.venv_guidely)` at the beginning of your terminal prompt when activated).*

> **First-time setup (if configuring on a new machine):**
> ```bash
> python3 -m venv ~/.venv_guidely
> source ~/.venv_guidely/bin/activate
> 
> ```
> 
> 

---

## 3. Install Backend Dependencies

With `(.venv_guidely)` active, install all required project packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt

```

---

## 4. Configure Environment Variables

Create a `.env` file in your project root directory (`guidely/`):

```bash
touch .env

```

Open `.env` and add your Groq API key:

```env
GROQ_API_KEY=your_actual_groq_api_key_here

```

> **Security Note:** `.env` is listed in `.gitignore` and will never be committed to Git.

---

## 5. Run the Backend Server (Terminal 1)

In your root project directory, start the FastAPI development server:

```bash
uvicorn backend.main:app --reload

```

* **API Base URL:** `http://127.0.0.1:8000`
* **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`

---

## 6. Run the Frontend Application (Terminal 2)

Open a second terminal tab, navigate to the `frontend` folder, install dependencies, and start the Vite development server:

```bash
cd frontend
npm install
npm run dev

```

* **Guidely UI Interface:** `http://localhost:5173`

```

```