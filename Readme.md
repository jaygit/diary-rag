
# 🧠 Diary RAG Assistant with Ollama + ChromaDB

This project turns your Obsidian vault into a queryable, context-aware AI assistant using a local LLM (PH3 via Ollama) and a Retrieval-Augmented Generation (RAG) pipeline powered by ChromaDB.

## 📦 Architecture Overview

- **Ollama**: Runs the PH3 model locally via Docker.
- **Diary REPL**: Python container that ingests notes, stores embeddings in ChromaDB, and provides a REPL interface for querying.
- **Obsidian Vault**: Mounted into the REPL container for ingestion.
- **Gitea CI/CD**: Automatically rebuilds and redeploys the stack on code changes.

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/jaydocker/diary-rag.git
cd diary-rag
```

### 2. Configure your vault mount

By default, the Obsidian vault is mounted from:

```yaml
volumes:
  - ./obsidian-vault:/vault:ro
```

To change this, edit `docker-compose.yml`:

```yaml
diary-repl:
  volumes:
    - /absolute/path/to/your/vault:/vault:ro
```

### 3. Configure PH3 model location (optional)

Ollama stores models in:

```
ollama-data:/root/.ollama
```

To preserve or relocate this volume:

- Change the volume mount in `docker-compose.yml`
- Or use a bind mount:

```yaml
volumes:
  - /path/to/ollama/models:/root/.ollama
```

---

## 🛠️ Makefile Commands

```bash
make build     # Build Docker images
make up        # Start the stack
make down      # Stop and remove containers
make logs      # View REPL logs
make ingest    # Run ingestion script to embed notes into ChromaDB
make metadata  # Run ingestion to update only the metadata in ChromaDB
make repl      # start the REPL query prompt
make install   # run install checks and create required files
make check     # run environment consistency checks
make healthcheck  # run detailed healthcheck script (healthcheck.py)
```

---

## 🧹 Docker Volume Management

### To preserve volumes:

```bash
docker volume ls
docker volume inspect diary-rag_ollama-data
```

### To remove volumes:

```bash
docker-compose down -v
docker volume rm diary-rag_ollama-data
docker volume rm diary-rag_rag_db
```
### ingest metadata file

The injest metadata file is `ingestion_notes.json`. This file is stored in the local filesystem
if you delete it you can recreate it be 

```bash
make metadata
```
---

## 🤖 Using the REPL

```bash
docker exec -it diary-repl python repl.py
```

Once the prompt appears you can use several search modes. The REPL supports substring filename search, semantic (embedding) search, and date-aware filters. Below are the most useful commands and examples.

- `list notes`
  - Prints all indexed filenames.

- `show note <term>`
  - Primary command to open a note. `<term>` can be a full filename, a partial filename, or a short query phrase.
  - Behavior:
    - If `<term>` exactly matches a note id, that note is shown.
    - Otherwise the REPL first looks for case-insensitive substring matches in filenames and shows a compact numbered list (filename + date).
      - Enter a number to open the full note.
      - Enter `p<number>` to preview the first ~1000 characters of that note (e.g. `p2`).
      - Enter `s` to run a semantic (embedding) search if substring results are ambiguous.
    - If substring search yields no useful matches (or you press `s`), the REPL runs a semantic search using embeddings and presents a compact list of top matches for you to pick.

  - Examples:
    - `show note ssh wsl2` — finds notes whose filenames contain `ssh`/`wsl2` or are semantically related (e.g., "configuring SSH in WSL2").
    - `show note slides` — quick substring match on filenames.

- `show notes from yesterday` / `show notes from <YYYY-MM-DD>`
  - Lists files (and contents) whose metadata `date` equals yesterday (or the given date). Metadata `date` must be in ISO format (`YYYY-MM-DD`).

- `last week` or `summarize last week`
  - Date-aware semantic query: the REPL gathers notes from the past 7 days, builds a compact context (filename + truncated content) and asks the model to summarize or answer your question grounded on that context.

- `between YYYY-MM-DD and YYYY-MM-DD`
  - Date-range query: retrieves notes whose metadata `date` falls in the given inclusive range, and uses those notes as the model context.

- Free-form queries (default semantic search)
  - If your input doesn't match any of the special commands above, the REPL will compute an embedding for your query and run a semantic (vector) search against ChromaDB. The top K documents are passed to the model as context.

Tips
- If you want fast filename-only navigation, use `list notes` and then `show note <short-unique-fragment>`.
- Semantic search works best when the note content has been embedded (run `make ingest` to embed your vault).
- If a date-based search returns nothing, verify that your notes' metadata include a `date` field in ISO format (the ingester sets `date` when filenames start with `YYYY-MM-DD`).
- If you prefer only filenames (no content) for date queries, ask and I can add a `--preview` toggle.

Examples

```
> list notes
> show note ssh wsl2
Multiple notes match 'ssh wsl2': (compact list)
1. obsidian/notes/configuring-ssh-wsl2.md (2025-11-30)
2. obsidian/notes/ssh-troubleshooting.md (2025-10-12)
Enter number to show, 'p<number>' to preview, 's' to run semantic search, or 'c' to cancel: p1
=== Preview: obsidian/notes/configuring-ssh-wsl2.md ===
...
> show notes from yesterday
--- obsidian/notes/2025-12-03 - Meeting.md ---
<full content>
```

## 🛠️ Troubleshooting & Tips

If something doesn't behave as expected, these quick checks usually help.

- Verify embeddings/ingestion
  - Ensure your notes are embedded in ChromaDB: run `make ingest` (or `make metadata` to refresh metadata only).
  - Inspect the first few metadatas to confirm dates/filenames:
    ```python
    import chromadb
    c = chromadb.PersistentClient(path="/rag_db")
    col = c.get_or_create_collection("notes")
    res = col.get()
    print(res['metadatas'][:10])
    ```

- Check `ingested_notes.json`
  - The ingester stores a map of ingested notes in `ingested_notes.json`. If you see unexpected behavior, back it up and inspect it:
    ```bash
    cp ingested_notes.json ingested_notes.json.bak
    cat ingested_notes.json
    ```

- Ollama / model issues
  - Confirm Ollama is running and the model is available:
    ```bash
    docker compose ps
    docker compose logs ollama --follow
    docker compose exec -it ollama ollama list
    ```
  - If embeddings or generation fail, check Ollama logs for errors and restart the container.

- ChromaDB issues
  - If queries return empty results, inspect the Chroma DB files under `rag_db/` and check the REPL logs.

- Metadata dates and formats
  - Date-aware commands rely on a `date` field in metadata (ISO `YYYY-MM-DD`). The ingester sets `date` from filenames that start with `YYYY-MM-DD`.
  - If you want different metadata extraction, update `python-repl/ingest.py` to parse date from frontmatter or file contents.

- Make searches faster and less noisy
  - Use `list notes` plus `show note <short-fragment>` for quick filename navigation.
  - Use semantic search for meaning-based queries (e.g., `show note ssh wsl2`) when filenames don't contain the phrase.


---

## 🔁 Gitea CI/CD Integration

### 1. Push changes to Gitea

```bash
git add .
git commit -m "Update REPL logic"
git push origin main
```

### 2. Gitea workflow (`.gitea/workflows/build.yml`)

```yaml
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: docker
    steps:
      - uses: actions/checkout@v3
      - run: make build
      - run: make up
```

This rebuilds and redeploys your stack automatically.

---

## 📂 Project Structure

```
project-root/
├── docker-compose.yml
├── Makefile
├── ingested_notes.yaml       # YAML map of ingested notes (created by install/ingest)
├── ingested_notes.json       # legacy/alternate format used by older tooling
├── rag_db/                   # Local Chroma DB files
│   └── chroma.sqlite3
├── obsidian-vault/           # Your notes
├── python-repl/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── ingest.py             # Embeds notes into ChromaDB
│   └── repl.py               # Interactive REPL
└── .gitea/
  └── workflows/
    └── build.yml         # CI/CD pipeline
```

---

## 🧠 Powered By

- [Ollama](https://ollama.com/)
- [ChromaDB](https://www.trychroma.com/)
- [Gitea](https://gitea.io/)
- [Obsidian](https://obsidian.md/)

---

## 📬 Questions or Contributions?

Feel free to open issues or contribute via pull requests. This project is built for curious tinkerers and note-powered thinkers.

```

