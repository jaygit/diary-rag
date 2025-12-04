.PHONY: build up down logs ingest metadata repl install check healthcheck

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f diary-repl

ingest:
	docker-compose run --rm diary-repl python ingest.py

metadata:
	docker-compose run --rm diary-repl python ingest.py --metadata-only

repl:
	docker-compose run --rm diary-repl python repl.py

install:
	@echo "Running install checks..."
	# Ensure ingested_notes.json exists (create empty dict if missing)
	@if [ ! -f ingested_notes.json ]; then \
		echo "{}" > ingested_notes.json && echo "Created ingested_notes.json"; \
	else \
		echo "Found ingested_notes.json"; \
	fi

	# Ensure ingested_notes.yaml exists (create empty mapping if missing)
	@if [ ! -f ingested_notes.yaml ]; then \
		echo "{}" > ingested_notes.yaml && echo "Created ingested_notes.yaml"; \
	else \
		echo "Found ingested_notes.yaml"; \
	fi

	@echo "Install checks completed."

check:
	@echo "Running environment checks..."
	# Check Docker / docker-compose
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "[ERROR] docker not found in PATH"; exit 1; \
	fi
	@if ! command -v docker-compose >/dev/null 2>&1 && ! command -v docker >/dev/null 2>&1; then \
		echo "[WARN] docker-compose not found; try 'docker compose' if using newer Docker"; \
	fi

	# Check Docker volumes (common names used by this project)
	@echo "Checking for expected Docker volumes: ollama-data, diary-rag_rag_db"
	@if docker volume ls | grep -E "ollama-data|diary-rag_rag_db" >/dev/null 2>&1; then \
		echo "Found one or more expected volumes"; \
	else \
		echo "[WARN] Expected volumes not found (ollama-data, diary-rag_rag_db). They will be created when you run 'make up'"; \
	fi

	# Check rag_db existence
	@if [ -d rag_db ]; then \
		echo "Found rag_db directory"; \
		if [ -f rag_db/chroma.sqlite3 ]; then \
			echo "Found rag_db/chroma.sqlite3"; \
		else \
			echo "[WARN] rag_db/chroma.sqlite3 not found. Run ingestion to create the DB (make ingest)"; \
		fi \
	else \
		echo "[WARN] rag_db directory not found"; \
	fi

	# Check Ollama model availability (requires container up)
	@if docker compose ps --services --filter "status=running" | grep -q "ollama"; then \
		echo "Ollama container running, checking model list..."; \
		docker compose exec -T ollama ollama list || echo "[WARN] 'ollama list' failed"; \
		if docker compose exec -T ollama ollama list 2>/dev/null | grep -q "phi3"; then \
			echo "Found phi3 model in Ollama"; \
		else \
			echo "[WARN] phi3 model not listed in Ollama. Pull or install the model before usage"; \
		fi \
	else \
		echo "[WARN] Ollama container not running. Start the stack with 'make up' and then re-run 'make check'"; \
	fi

	# Check ingested_notes.json
	@if [ -f ingested_notes.json ]; then \
		echo "Found ingested_notes.json"; \
	else \
		echo "[WARN] ingested_notes.json missing (install target creates it)."; \
	fi

	@echo "Environment checks finished. Address WARN/ERROR messages above before using the REPL."

healthcheck:
	@python3 healthcheck.py || true