import os

def load_text_files(data_dir: str = "backend/data/sample-docs"):
    """Reads all .txt files from the sample documents directory."""
    documents = []
    
    # Handle path flexibility whether running from root or backend folder
    if not os.path.exists(data_dir):
        data_dir = "data/sample-docs"

    if not os.path.exists(data_dir):
        print(f"Directory not found: {data_dir}")
        return []

    for filename in os.listdir(data_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(data_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                documents.append({
                    "filename": filename,
                    "content": content
                })
    return documents


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 30):
    """
    Splits text into word chunks with overlapping boundaries.
    chunk_size: max words per chunk
    overlap: words shared between adjacent chunks
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_str = " ".join(chunk_words)
        chunks.append(chunk_str)
        
        # Advance by (chunk_size - overlap)
        start += (chunk_size - overlap)
        if start >= len(words) and len(words) > 0 and len(chunks) == 0:
            break

    return chunks


def process_documents(data_dir: str = "backend/data/sample-docs"):
    """
    Loads all documents and returns a list of chunk dictionaries with metadata attached.
    """
    docs = load_text_files(data_dir)
    processed_chunks = []
    global_chunk_id = 0

    for doc in docs:
        raw_chunks = chunk_text(doc["content"])
        for idx, snippet in enumerate(raw_chunks):
            processed_chunks.append({
                "id": global_chunk_id,
                "filename": doc["filename"],
                "chunk_index": idx,
                "text": snippet
            })
            global_chunk_id += 1

    return processed_chunks