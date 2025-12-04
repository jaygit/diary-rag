import chromadb
import ollama
import datetime
import os
import re
from chromadb.config import Settings

OLLAMA_HOST = "http://ollama:11434"
MODEL = "phi3"

# Updated: Use PersistentClient instead of deprecated Client with Settings
client = chromadb.PersistentClient(path="/rag_db")
client_ollama = ollama.Client(host=OLLAMA_HOST)
collection = client.get_or_create_collection("notes")

def embed_text(text):
    """Generate embeddings using Ollama Python library"""
    response = client_ollama.embeddings(model=MODEL, prompt=text)
    return response['embedding']

def query_ollama(prompt, context):
    prompt = f"""
    Only use the following context from my notes collection.
    Do not invent. If nothing matches, say 'Not found in collection'.

    Context:
    {context}

    Question:
    {prompt}
    """
    # Use the client's generate method (client_ollama is a client object,
    # not a callable). Stream responses if supported by the client.
    stream = client_ollama.generate(model=MODEL, prompt=prompt, stream=True)
    for chunk in stream:
        # Support multiple possible chunk shapes: dict, object with attributes,
        # or raw text. Try to extract the user-facing text field.
        text = None
        if isinstance(chunk, dict):
            text = chunk.get('response') or chunk.get('text') or chunk.get('content')
        else:
            # Some client libraries return small objects / dataclasses
            # with attributes like `response` or `text`.
            for attr in ('response', 'text', 'content'):
                if hasattr(chunk, attr):
                    text = getattr(chunk, attr)
                    break
        if text is None:
            # Fallback to str() for unknown shapes
            text = str(chunk)
        print(text, end='', flush=True)
    print()

def filter_by_date(metadatas, documents, start, end):
    """Filter documents by date range in metadata"""
    filtered_docs = []
    for meta, doc in zip(metadatas, documents):
        note_date = meta.get("date")
        if note_date: 
            try:
                d = datetime.date.fromisoformat(note_date)
                if start <= d <= end:
                    filtered_docs.append(doc)
            except Exception:
                pass
    return filtered_docs 


def format_context_from_pairs(metadatas, documents, max_docs=5, max_chars=1000):
    """Build a safe, truncated context string from metadata/document pairs.

    Each document is prefixed by its filename to help the model ground answers
    and avoid hallucination. Returns the top `max_docs` items.
    """
    pairs = []
    for meta, doc in zip(metadatas, documents):
        pairs.append((meta.get('file', '<unknown>'), doc))

    # take the first max_docs (caller should pre-filter/score as needed)
    parts = []
    for fname, doc in pairs[:max_docs]:
        # normalize doc to a single string
        if isinstance(doc, list):
            doc_text = "\n".join(doc)
        else:
            doc_text = str(doc)
        # truncate to avoid huge prompts
        if len(doc_text) > max_chars:
            doc_text = doc_text[:max_chars] + "\n...[truncated]"
        parts.append(f"--- FILE: {fname} ---\n{doc_text}\n")
    return "\n".join(parts)

def repl():
    print("📔 Diary LLM REPL (Ollama PH3 + ChromaDB)")
    print("Type 'quit' to exit.")
    while True:
        query = input("> ").strip()
        if query.lower() in ["quit", "exit"]:
            break

        # --- Command Mode ---
        if query == "list notes":
            results = collection.get()
            print("Indexed Notes:")
            for meta in results['metadatas']:
                print(meta["file"])
            continue

        if query.startswith("show note "):
            note_id = query[len("show note "):].strip()
            # Try exact id first
            results = collection.get(ids=[note_id])
            if results and results.get('documents') and any(results.get('documents')):
                print(f"Content of {note_id}:\n")
                doc = results['documents'][0]
                if isinstance(doc, list):
                    print("\n".join(doc))
                else:
                    print(doc)
                continue

            # No exact match: first try substring search on filenames in metadata
            all_results = collection.get()
            metadatas = all_results.get('metadatas', [])
            documents = all_results.get('documents', [])
            matches = []
            needle = note_id.lower()
            for meta, doc in zip(metadatas, documents):
                fname = meta.get('file', '')
                if needle in fname.lower():
                    matches.append((meta, doc))

            # If substring matches exist, offer them first
            if matches:
                if len(matches) == 1:
                    meta, doc = matches[0]
                    fname = meta.get('file')
                    print(f"Content of {fname}:\n")
                    if isinstance(doc, list):
                        print("\n".join(doc))
                    else:
                        print(doc)
                    continue

                print(f"Multiple notes match '{note_id}': (compact list)")
                for i, (meta, doc) in enumerate(matches, start=1):
                    fname = meta.get('file', '<unknown>')
                    date = meta.get('date') or ''
                    display = f"{i}. {fname}"
                    if date:
                        display += f" ({date})"
                    print(display)

                choice = input("Enter number to show, 'p<number>' to preview, 's' to run semantic search, or 'c' to cancel: ").strip()
                if choice.lower() == 'c' or not choice:
                    continue
                if choice.lower() == 's':
                    # fall through to semantic search below
                    pass
                else:
                    # allow preview command like 'p2'
                    if choice.lower().startswith('p'):
                        maybe = choice[1:]
                        try:
                            idx = int(maybe) - 1
                            if 0 <= idx < len(matches):
                                meta, doc = matches[idx]
                                fname = meta.get('file')
                                print(f"\n=== Preview: {fname} ===\n")
                                if isinstance(doc, list):
                                    print("\n".join(doc)[:1000])
                                else:
                                    print(str(doc)[:1000])
                                # let user choose again
                                continue
                        except Exception:
                            print("Invalid preview command — falling back to semantic search.")
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(matches):
                            meta, doc = matches[idx]
                            fname = meta.get('file')
                            print(f"\n=== {fname} ===\n")
                            if isinstance(doc, list):
                                print("\n".join(doc))
                            else:
                                print(doc)
                            continue
                        else:
                            print("Invalid selection — falling back to semantic search.")
                    except ValueError:
                        print("Invalid input — falling back to semantic search.")

            # Semantic search fallback / option: use embeddings to find notes by meaning
            try:
                q_emb = embed_text(note_id)
                sem_results = collection.query(query_embeddings=[q_emb], n_results=6)
                # results for single query are lists at index 0
                sem_ids = sem_results.get('ids', [[]])[0]
                sem_docs = sem_results.get('documents', [[]])[0]
                sem_metas = sem_results.get('metadatas', [[]])[0]
            except Exception as e:
                print(f"Semantic search failed: {e}")
                continue

            if not sem_ids:
                print(f"No semantic matches found for '{note_id}'.")
                continue

            # Present semantic matches with optional score info if present
            print(f"Semantic matches for '{note_id}':")
            sem_matches = []
            for i, (sid, meta, doc) in enumerate(zip(sem_ids, sem_metas, sem_docs), start=1):
                fname = meta.get('file') if isinstance(meta, dict) else str(meta)
                preview = ''
                if isinstance(doc, list):
                    preview = '\n'.join(doc)[:240]
                else:
                    preview = str(doc)[:240]
                safe_preview = preview.replace("\n", " ")
                print(f"{i}. {fname} -- {safe_preview[:140]}")
                sem_matches.append((sid, fname, doc))

            choice = input("Enter number to show, or 'c' to cancel: ").strip()
            if choice.lower() == 'c' or not choice:
                continue
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(sem_matches):
                    sid, fname, doc = sem_matches[idx]
                    print(f"\n=== {fname} ({sid}) ===\n")
                    if isinstance(doc, list):
                        print("\n".join(doc))
                    else:
                        print(doc)
                else:
                    print("Invalid selection")
            except ValueError:
                print("Invalid input — expected a number or 'c'.")
            continue

        if query == "stats":
            count = collection.count()
            print(f"Total indexed notes: {count}")
            continue
       # --- Date-aware Queries ---
        results = collection.get()
        metadatas = results["metadatas"]
        documents = results["documents"]

        # --- Yesterday quick view ---
        if "yesterday" in query.lower() or query.lower().startswith("show notes from yesterday"):
            today = datetime.date.today()
            yesterday = today - datetime.timedelta(days=1)
            found = False
            for meta, doc in zip(metadatas, documents):
                note_date = meta.get("date")
                if note_date:
                    try:
                        d = datetime.date.fromisoformat(note_date)
                        if d == yesterday:
                            print(f"--- {meta.get('file')} ---")
                            if isinstance(doc, list):
                                print("\n".join(doc))
                            else:
                                print(doc)
                            print()
                            found = True
                    except Exception:
                        pass
            if not found:
                print("No notes found for yesterday.")
            continue

        if "last week" in query.lower():
            today = datetime.date.today()
            start = today - datetime.timedelta(days=7)
            end = today
            # Keep the matched pairs so we can format context with filenames
            pairs = []
            for meta, doc in zip(metadatas, documents):
                note_date = meta.get("date")
                if note_date:
                    try:
                        d = datetime.date.fromisoformat(note_date)
                        if start <= d <= end:
                            pairs.append((meta, doc))
                    except Exception:
                        pass
            context = format_context_from_pairs([p[0] for p in pairs], [p[1] for p in pairs])
            if not context:
                print("No notes found for last week.")
            else:
                query_ollama(query, context)
            continue

        match = re.search(r"between (\d{4}-\d{2}-\d{2}) and (\d{4}-\d{2}-\d{2})", query.lower())
        if match:
            start = datetime.date.fromisoformat(match.group(1))
            end = datetime.date.fromisoformat(match.group(2))
            pairs = []
            for meta, doc in zip(metadatas, documents):
                note_date = meta.get("date")
                if note_date:
                    try:
                        d = datetime.date.fromisoformat(note_date)
                        if start <= d <= end:
                            pairs.append((meta, doc))
                    except Exception:
                        pass
            context = format_context_from_pairs([p[0] for p in pairs], [p[1] for p in pairs])
            if not context:
                print("No notes found for that date range.")
            else:
                query_ollama(query, context)
            continue
 
        # --- Default Semantic Search ---
        q_emb = embed_text(query)
        results = collection.query(query_embeddings=[q_emb], n_results=5)
        context = "\n\n".join(results["documents"][0]) if results["documents"] else ""
        query_ollama(query, context)

if __name__ == "__main__":
    repl()
