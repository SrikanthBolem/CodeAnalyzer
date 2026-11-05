import re

# A bracketed group mentioning at least one cell, e.g. "[Cell 4, line 6; Cell 5, lines 3–5]".
BRACKET = re.compile(r"\[([^\[\]]*\bCell\s+\d+[^\[\]]*)\]", re.I)
# One citation inside a group: "line N" or "lines X-Y", with a hyphen, en dash or em dash.
CITATION = re.compile(r"\bCell\s+(\d+)\s*,\s*lines?\s+(\d+)(?:\s*[-–—]\s*(\d+))?", re.I)
# Any mention of a cell inside a group, well-formed or not.
CELL_MENTION = re.compile(r"\bCell\s+(\d+)", re.I)

def validate_document(document, source):
    by_id = {int(c["cell_id"]): c for c in source["cells"]}
    valid, invalid = [], []
    for group in BRACKET.finditer(document):
        text = group.group(1)
        cited_at = set()
        for match in CITATION.finditer(text):
            cited_at.add(match.start())
            cell_id, start = int(match.group(1)), int(match.group(2))
            end = int(match.group(3)) if match.group(3) else start
            cell = by_id.get(cell_id)
            max_line = len(cell["code"].splitlines()) if cell else 0
            item = {"citation": match.group(0), "cell": cell_id, "start": start, "end": end}
            if cell and start >= 1 and end >= start and end <= max_line:
                valid.append(item)
            else:
                item["reason"] = "cell does not exist" if not cell else "line range outside the cell"
                invalid.append(item)
        # A cell named without a usable line reference (e.g. "[Cell 7, Risk]") cannot be verified.
        for mention in CELL_MENTION.finditer(text):
            if mention.start() not in cited_at:
                piece = re.split(r"[;\]]", text[mention.start():], maxsplit=1)[0].strip()
                invalid.append({"citation": piece, "cell": int(mention.group(1)), "start": None, "end": None,
                                "reason": "no line number"})
    return {"valid": valid, "invalid": invalid, "count": len(valid) + len(invalid)}
