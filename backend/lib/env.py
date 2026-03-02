"""Minimal dotenv loader used by backend startup."""

from __future__ import annotations

import os


def load_dotenv(path: str) -> None:
    """Load KEY=VALUE pairs from a file into os.environ.

    Existing environment variables are preserved.
    """
    if not path or not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue

            parsed = value.strip()
            if len(parsed) >= 2 and parsed[0] == parsed[-1] and parsed[0] in {'"', "'"}:
                parsed = parsed[1:-1]

            os.environ[key] = parsed
