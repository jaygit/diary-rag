#!/usr/bin/env python3
"""healthcheck.py

Quick environment health check for the Diary RAG project.

Checks performed:
- docker presence
- docker compose availability
- ollama container running
- phi3 model listed in Ollama (if container running)
- presence of `rag_db/chroma.sqlite3`
- presence and basic validity of `ingested_notes.json`
- presence of `python-repl/requirements.txt`

Usage:
  python3 healthcheck.py [--json]

Returns non-zero exit code if any critical errors are found.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any
from logging_setup import get_logger

logger = get_logger(__name__)


def run_cmd(cmd: List[str], timeout: int = 10) -> Dict[str, Any]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return {"rc": p.returncode, "out": p.stdout.strip(), "err": p.stderr.strip()}
    except Exception as e:
        return {"rc": 127, "out": "", "err": str(e)}


def check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    checks: List[Dict[str, Any]] = []

    # Check docker
    docker_ok = check_tool("docker")
    checks.append({"id": "docker", "ok": docker_ok, "severity": "error" if not docker_ok else "info", "msg": "Docker available" if docker_ok else "docker not found in PATH"})

    # Check docker compose availability (try `docker compose` or binary `docker-compose`)
    compose_ok = False
    compose_method = None
    if docker_ok:
        r = run_cmd(["docker", "compose", "version"])
        if r["rc"] == 0:
            compose_ok = True
            compose_method = "docker compose"
        elif check_tool("docker-compose"):
            compose_ok = True
            compose_method = "docker-compose"
    else:
        if check_tool("docker-compose"):
            compose_ok = True
            compose_method = "docker-compose"

    checks.append({"id": "compose", "ok": compose_ok, "severity": "warn" if not compose_ok else "info", "msg": f"Docker compose available ({compose_method})" if compose_ok else "docker compose / docker-compose not available"})

    # Check ollama container running
    ollama_running = False
    ollama_list_out = ""
    if docker_ok:
        # Try to find container named 'ollama' via docker ps
        r = run_cmd(["docker", "ps", "--filter", "name=ollama", "--format", "{{.Names}}"])
        if r["rc"] == 0 and r["out"]:
            ollama_running = True
        else:
            # try docker compose ps to see service
            r2 = run_cmd(["docker", "compose", "ps", "--services", "--filter", "status=running"]) if compose_ok and compose_method == "docker compose" else {"rc": 1, "out": ""}
            if r2.get("rc") == 0 and "ollama" in r2.get("out", ""):
                ollama_running = True

    checks.append({"id": "ollama_running", "ok": ollama_running, "severity": "warn", "msg": "Ollama container running" if ollama_running else "Ollama container not running"})

    # If running, check model list for phi3
    phi3_present = False
    if ollama_running and compose_ok:
        # Try docker compose exec first
        r = run_cmd(["docker", "compose", "exec", "-T", "ollama", "ollama", "list"]) if compose_method == "docker compose" else {"rc": 1, "out": ""}
        if r.get("rc") != 0:
            # try docker exec (container name may be "ollama")
            r = run_cmd(["docker", "exec", "ollama", "ollama", "list"])
        ollama_list_out = r.get("out", "") or r.get("err", "")
        if "phi3" in ollama_list_out:
            phi3_present = True

    checks.append({"id": "phi3_model", "ok": phi3_present, "severity": "warn", "msg": "phi3 model available in Ollama" if phi3_present else "phi3 model not listed in Ollama (or Ollama not running)"})

    # Check rag_db files
    rag_db = Path("rag_db")
    chroma_file = rag_db / "chroma.sqlite3"
    rag_db_ok = rag_db.exists() and chroma_file.exists()
    checks.append({"id": "rag_db", "ok": rag_db.exists(), "severity": "warn", "msg": "rag_db directory exists" if rag_db.exists() else "rag_db directory missing"})
    checks.append({"id": "chroma_file", "ok": chroma_file.exists(), "severity": "warn", "msg": "chroma.sqlite3 exists" if chroma_file.exists() else "chroma.sqlite3 not found in rag_db"})

    # ingested_notes.json
    ingested = Path("ingested_notes.json")
    ingested_ok = False
    ingested_valid = False
    ingested_content = None
    if ingested.exists():
        ingested_ok = True
        try:
            with ingested.open("r", encoding="utf-8") as f:
                ingested_content = json.load(f)
                # accept list or dict
                if isinstance(ingested_content, (list, dict)):
                    ingested_valid = True
        except Exception as e:
            ingested_valid = False

    checks.append({"id": "ingested_present", "ok": ingested_ok, "severity": "warn", "msg": "ingested_notes.json present" if ingested_ok else "ingested_notes.json missing"})
    checks.append({"id": "ingested_valid", "ok": ingested_valid, "severity": "warn", "msg": "ingested_notes.json valid JSON" if ingested_valid else "ingested_notes.json invalid or unreadable"})

    # requirements file
    req = Path("python-repl/requirements.txt")
    checks.append({"id": "requirements", "ok": req.exists(), "severity": "warn", "msg": "requirements.txt present" if req.exists() else "python-repl/requirements.txt missing"})

    # Summarize
    result = {"checks": checks}

    errors = [c for c in checks if c["severity"] == "error" and not c["ok"]]
    warns = [c for c in checks if c["severity"] == "warn" and not c["ok"]]

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for c in checks:
            status = "OK" if c["ok"] else ("WARN" if c["severity"] == "warn" else "ERROR")
            if status == "OK":
                logger.info("%s: %s", c['id'], c['msg'])
            elif status == "WARN":
                logger.warning("%s: %s", c['id'], c['msg'])
            else:
                logger.error("%s: %s", c['id'], c['msg'])
        # Additional info snippets
        if ollama_list_out:
            logger.info("Ollama list output (truncated):\n%s", ollama_list_out[:2000])

    # exit non-zero if any critical errors
    if errors:
        return 2
    if warns:
        # still success but warn exit code 1
        return 1
    return 0


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
