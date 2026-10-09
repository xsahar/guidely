```markdown
# Local Setup Guide (Windows)

Follow these steps in order using **PowerShell** to set up the project on a new computer.

### Step 1: Allow PowerShell Scripts
Run this command to allow local virtual environment scripts to run in your current shell session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

```

### Step 2: Create & Activate Virtual Environment

Inside your project folder (`C:\Projects\guidely`), create the isolated `.venv` folder and activate it:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1

```

*(You will see `(.venv)` at the beginning of your command line when activated).*

### Step 3: Install Packages

Run this command to install all required libraries inside the virtual environment:

```powershell
python -m pip install fastapi uvicorn openai faiss-cpu python-dotenv pydantic python-multipart

```

### Step 4: Configure API Key

Create a `.env` file in the main `guidely/` folder and paste your key:

```env
OPENAI_API_KEY=your_actual_key_here

```

### Step 5: Run the Server

Start the backend development server:

```powershell
python -m uvicorn backend.main:app --reload

```

View the live API in your browser at: `http://127.0.0.1:8000/docs`

```

---

