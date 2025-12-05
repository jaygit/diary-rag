"""Central logging setup for the project.

Usage:
  from logging_setup import get_logger
  logger = get_logger(__name__)

Configuration order:
- If environment variable `LOG_CONFIG_FILE` is set and points to a JSON or YAML file, it will be loaded.
- Otherwise, environment variables control logging:
  - `LOG_LEVEL` (default: INFO)
  - `LOG_TO` (one of `console`, `file`, `both`; default: console)
  - `LOG_FILE` (default: diary-rag.log)

This module uses `logging.config.dictConfig` and ensures configuration runs only once.
"""
from __future__ import annotations

import json
import logging
import logging.config
import os
from typing import Any, Dict

_configured = False


def _build_default_config() -> Dict[str, Any]:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    to = os.getenv("LOG_TO", "console").lower()
    logfile = os.getenv("LOG_FILE", "diary-rag.log")

    handlers: Dict[str, Any] = {}
    handler_names = []
    if to in ("console", "both"):
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": level,
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        }
        handler_names.append("console")
    if to in ("file", "both"):
        handlers["file"] = {
            "class": "logging.FileHandler",
            "level": level,
            "formatter": "standard",
            "filename": logfile,
            "encoding": "utf-8",
        }
        handler_names.append("file")

    if not handler_names:
        # fallback to console
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": level,
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        }
        handler_names.append("console")

    cfg = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": handlers,
        "root": {
            "level": level,
            "handlers": handler_names,
        },
    }
    return cfg


def _load_config_file(path: str) -> Dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
            text = text.strip()
            if not text:
                return None
            # try json first
            try:
                return json.loads(text)
            except Exception:
                # try yaml if available
                try:
                    import yaml  # type: ignore

                    return yaml.safe_load(text)
                except Exception:
                    return None
    except Exception:
        return None


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    cfg_file = os.getenv("LOG_CONFIG_FILE", "logging.yaml")
    cfg = _load_config_file(cfg_file)
    if not cfg:
        cfg = _build_default_config()

    try:
        logging.config.dictConfig(cfg)
    except Exception:
        # last-resort basicConfig
        logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    _configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
