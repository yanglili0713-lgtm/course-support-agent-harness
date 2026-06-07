from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_mapping(path: Path) -> dict[str, Any]:
    """Load a project config file without requiring PyYAML.

    The examples are stored with .yaml extensions for readability, but their
    content is JSON-compatible YAML. JSON is valid YAML, so this keeps configs
    dependency-free while preserving the existing file names.
    """

    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data

