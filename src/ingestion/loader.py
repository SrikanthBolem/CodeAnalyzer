import json
from pathlib import Path

def _cell(cell_id, language, code):
    return {"cell_id": cell_id, "language": language, "code": code.rstrip("\n")}

def load_source(filename: str, raw: bytes) -> dict:
    suffix = Path(filename).suffix.lower()
    text = raw.decode("utf-8-sig")
    cells = []
    if suffix == ".ipynb":
        notebook = json.loads(text)
        for idx, item in enumerate(notebook.get("cells", []), start=1):
            source = item.get("source", [])
            code = "".join(source) if isinstance(source, list) else str(source)
            if item.get("cell_type") == "code":
                cells.append(_cell(idx, "python", code))
            else:
                cells.append(_cell(idx, "markdown", code))
    elif suffix == ".py":
        # Databricks source exports commonly separate cells with COMMAND markers.
        chunks, current = [], []
        for line in text.splitlines():
            if line.strip().startswith("# COMMAND ----------"):
                chunks.append("\n".join(current))
                current = []
            else:
                current.append(line)
        chunks.append("\n".join(current))
        for idx, chunk in enumerate(chunks, start=1):
            if chunk.strip():
                cells.append(_cell(idx, "python", chunk))
    elif suffix == ".sql":
        cells = [_cell(1, "sql", text)]
    else:
        cells = [_cell(1, "text", text)]
    if not cells:
        raise ValueError("No readable cells found.")
    return {
        "filename": filename,
        "cells": cells,
        "line_count": sum(len(c["code"].splitlines()) for c in cells),
    }
