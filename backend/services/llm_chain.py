import os
import re
from dotenv import load_dotenv
from groq import Groq
from backend.services.vector_store import VectorStore

# Load environment variables from .env
load_dotenv()

NO_ANSWER_MESSAGE = "I could not generate an answer from the available documentation."

ABSTENTION_PATTERNS = (
    "i could not find",
    "i couldn't find",
    "could not generate an answer",
    "couldn't generate an answer",
    "can't find",
    "cannot find",
    "no relevant documentation",
    "not have enough information",
    "don't have enough information",
    "do not have enough information",
    "don't have the information",
    "do not have the information",
    "not enough information",
    "insufficient information",
    "not sure",
    "don't know",
    "do not know",
    "i'm sorry",
    "i am sorry",
    "unable to answer",
    "cannot answer",
    "can't answer",
    "don't have that information",
    "do not have that information",
    "not mentioned in",
    "context does not contain",
    "context doesn't contain",
    "no information",
)


def is_abstention(answer: str | None) -> bool:
    normalized = re.sub(r"\s+", " ", (answer or "").lower().replace("’", "'"))
    return not normalized or any(phrase in normalized for phrase in ABSTENTION_PATTERNS)


class LLMChain:

    def __init__(
        self,
        vector_store: VectorStore,
        model: str = "openai/gpt-oss-20b",  # <-- Updated model ID
    ):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set in the environment variables."
            )

        self.client = Groq(api_key=api_key)
        self.vector_store = vector_store
        self.model = model

    def generate_response(self, query: str, top_k: int = 3) -> dict:
        """Searches the vector store for context and generates an LLM response."""
        # 1. Retrieve matching chunks from FAISS
        retrieved_chunks = self.vector_store.search(query, top_k=top_k)

        if not retrieved_chunks:
            return {
                "answer": "I could not find any relevant documentation to answer your question.",
                "sources": [],
            }

        # 2. Format context and collect source filenames
        context_text = "\n\n".join(
            [f"--- Document: {c['filename']} ---\n{c['text']}" for c in retrieved_chunks]
        )
        sources = list(dict.fromkeys(c["filename"] for c in retrieved_chunks))

        # 3. Construct system and user prompt
        system_prompt = (
            "You are Guidely, an internal company knowledge assistant.\n"
            "Answer the user's question accurately using ONLY the provided context snippets below.\n"
            "If the provided context does not contain enough information to answer the question, "
            "politely state that you do not have that information in the company documentation.\n"
            "Do not make up facts or use outside knowledge."
        )

        user_prompt = f"Context:\n{context_text}\n\nQuestion: {query}"

        # 4. Query Groq API
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        answer = (completion.choices[0].message.content or "").strip()
        if not answer:
            answer = NO_ANSWER_MESSAGE
        if is_abstention(answer):
            sources = []

        return {
            "answer": answer,
            "sources": sources,
            "retrieved_chunks": retrieved_chunks,
        }


if __name__ == "__main__":
    print("Initializing VectorStore & LLMChain...")
    store = VectorStore()

    if not os.path.exists("backend/data/sample-docs"):
        print("Sample docs folder not found.")
    else:
        from backend.services.document_loader import process_documents

        chunks = process_documents("backend/data/sample-docs")
        store.build_index(chunks)

        chain = LLMChain(vector_store=store)

        test_query = "How many PTO days do employees get per year?"
        print(f"\nTesting Query: '{test_query}'")
        res = chain.generate_response(test_query)

        print("\n--- Answer ---")
        print(res["answer"])
        print("\n--- Sources ---")
        print(res["sources"])