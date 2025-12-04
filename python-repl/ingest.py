import os
import json
import argparse
import chromadb
from chromadb.config import Settings
import ollama
import datetime

OLLAMA_HOST = "http://ollama:11434"
MODEL = "phi3"
VAULT_DIR = "/vault"
INJESTED_JSON = "ingested_notes.json"

# Configure Ollama client
client_ollama = ollama.Client(host=OLLAMA_HOST)

# Use PersistentClient for ChromaDB
client_chroma = chromadb.PersistentClient(path="/rag_db")
collection = client_chroma.get_or_create_collection("notes")

def load_ingested():
    """Load ingested notes from JSON file, or create if missing"""
    if not os.path.exists(INJESTED_JSON):
        with open(INJESTED_JSON, "w") as f:
            json.dump({}, f)
    with open(INJESTED_JSON, "r") as f:
        data = json.load(f)
        # Support older format where we stored a list of note ids.
        if isinstance(data, list):
            return {k: None for k in data}
        if isinstance(data, dict):
            return data
        return {}
def save_ingested(ingested):
    """Save ingested notes to JSON file"""
    with open(INJESTED_JSON, "w") as f:
        json.dump(ingested, f, indent=2)

def embed_text(text):
    """Generate embeddings using Ollama Python library"""
    response = client_ollama.embeddings(model=MODEL, prompt=text)
    return response['embedding']

def ingest():
    """Ingest markdown files from vault into ChromaDB"""
    ingested = load_ingested()

    for root, _, files in os.walk(VAULT_DIR):
        for f in files:
            if not f.endswith(".md"):
                continue

            path = os.path.join(root, f)
            note_id = os.path.relpath(path, VAULT_DIR)

            # Extract date from filename if present
            try:
                note_date = datetime.datetime.strptime(f[:10], "%Y-%m-%d").date().isoformat()
            except Exception:
                note_date = None

            now = datetime.datetime.now().isoformat()

            if note_id not in ingested:
                # New note -> embed + add
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
                
                emb = embed_text(text)
                collection.add(
                    documents=[text],
                    metadatas=[{"file": path, "date": note_date, "ingested_at": now}],
                    ids=[note_id],
                    embeddings=[emb]
                )
                print(f"✅ Added new note: {note_id}")

            else:
                # Existing note -> update metadata only
                collection.update(
                    ids=[note_id],
                    metadatas=[{"file": path, "date": note_date, "ingested_at": now}]
                )
                print(f"🔄Update metadata for: {note_id}")

            
            ingested[note_id] = now

    save_ingested(ingested)

def injest_metadata_only():
    """Update metadata for all ingested notes without re-embedding"""
    ingested = load_ingested()
    now = datetime.datetime.now().isoformat()

    for root, _, files in os.walk(VAULT_DIR):
        for f in files:
            if not f.endswith(".md"):
                continue

            path = os.path.join(root, f)
            note_id = os.path.relpath(path, VAULT_DIR)
            
            try:
                note_date = datetime.datetime.strptime(f[:10], "%Y-%m-%d").date().isoformat()
            except Exception:
                note_date = None

                collection.update(
                    ids=[note_id],
                    metadatas=[{"file": path, "date": note_date, "ingested_at": now}]
                )
                print(f"🔄 Metadata refresh for: {note_id}")

                ingested[note_id] = now
    save_ingested(ingested)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest markdown notes into ChromaDB")
    parser.add_argument("-m", "--metadata-only", action="store_true", help="Only update metadata without re-embedding")

    args = parser.parse_args()
    if args.metadata_only:
        injest_metadata_only()
    else:
        ingest()
