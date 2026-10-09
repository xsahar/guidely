import os
from dotenv import load_dotenv
import fastapi
import faiss
import sentence_transformers
import groq

load_dotenv()

key = os.getenv("GROQ_API_KEY")

if key:
    print("\nSUCCESS: All libraries and Groq key loaded successfully!")
else:
    print("\nWARNING: All libraries imported, but GROQ_API_KEY was not found in your .env file.")