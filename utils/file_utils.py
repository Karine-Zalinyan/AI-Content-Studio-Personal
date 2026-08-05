"""
General-purpose file utilities.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_text(path: Path | str, encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding)


def write_text(path: Path | str, content: str, encoding: str = "utf-8") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding=encoding)


def read_json(path: Path | str) -> Any:
    return json.loads(read_text(path))


def write_json(path: Path | str, data: Any, indent: int = 2) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=indent))
