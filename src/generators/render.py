def render_document(document, source):
    # Keep the source citation text visible. The source viewer below provides
    # the complete cell; line-level highlighting can be added in a later iteration.
    return document


def number_lines_for_display(code):
    """Prefix each line with its citation line number, for the source viewer.

    Numbering matches the citation validator (1-based over code.splitlines(), blank
    lines included). Numbers are left-aligned so no line starts with whitespace:
    st.code strips leading/trailing whitespace, which would otherwise drop a leading
    blank line and shift every number, or misalign the first line.
    """
    lines = code.splitlines() or [""]
    width = len(str(len(lines)))
    return "\n".join(f"{i:<{width}} | {line}" for i, line in enumerate(lines, start=1))


MAX_LISTED_CITATIONS = 20

def format_invalid_citations(invalid, limit=MAX_LISTED_CITATIONS):
    """Markdown bullet list of citations that failed validation, with the reason for each.

    Repeated identical failures are listed once with a count.
    """
    counts = {}
    for item in invalid:
        key = (item["citation"].replace("`", "'"), item.get("reason", "could not be verified"))
        counts[key] = counts.get(key, 0) + 1
    lines = []
    for (citation, reason), n in list(counts.items())[:limit]:
        suffix = f" (×{n})" if n > 1 else ""
        lines.append(f"- `{citation}`: {reason}{suffix}")
    if len(counts) > limit:
        lines.append(f"- …and {len(counts) - limit} more")
    return "\n".join(lines)
