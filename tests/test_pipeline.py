from src.analysis.pipeline import _source_block, build_analysis_prompt, build_document_prompt
from src.citations.validator import validate_document
from src.ingestion.loader import load_source

SAMPLE = b"""# Databricks notebook source
x = 1

# COMMAND ----------

clean = (
    raw.dropDuplicates(["order_id"])
)
"""


def test_lines_are_numbered_including_leading_blank_line():
    source = load_source("s.py", SAMPLE)
    block = _source_block(source)
    # Cell 2 starts with a blank line, so the dropDuplicates line is line 3.
    assert "3 |     raw.dropDuplicates" in block
    assert "1 | " in block.split("===== CELL 2")[1].splitlines()[1]


def test_numbering_matches_validator():
    source = load_source("s.py", SAMPLE)
    cell2 = next(c for c in source["cells"] if c["cell_id"] == 2)
    last = len(cell2["code"].splitlines())
    numbered = _source_block(source).split("===== CELL 2")[1].strip().splitlines()[1:]
    assert numbered[-1].lstrip().startswith(f"{last} |")
    result = validate_document(f"[Cell 2, lines 1-{last}]", source)
    assert len(result["valid"]) == 1


def test_prompts_explain_the_line_prefix():
    source = load_source("s.py", SAMPLE)
    assert "do not count lines yourself" in build_analysis_prompt(source)
    for audience in ("business", "developer", "agent"):
        assert "do not count lines yourself" in build_document_prompt(source, "analysis", audience)


def test_viewer_numbering_survives_streamlit_strip():
    from streamlit.string_util import clean_text  # what st.code applies to its body
    from src.generators.render import number_lines_for_display
    source = load_source("s.py", SAMPLE)
    cell2 = next(c for c in source["cells"] if c["cell_id"] == 2)
    shown = clean_text(number_lines_for_display(cell2["code"])).splitlines()
    # The leading blank line is still line 1, and line 3 is the dropDuplicates call.
    assert len(shown) == len(cell2["code"].splitlines())
    assert shown[0].startswith("1 |")
    assert shown[2].startswith("3 |") and "dropDuplicates" in shown[2]


def test_viewer_numbering_aligns_past_nine_lines():
    from streamlit.string_util import clean_text
    from src.generators.render import number_lines_for_display
    shown = clean_text(number_lines_for_display("\n".join(f"x{i}" for i in range(1, 12)))).splitlines()
    assert shown[0] == "1  | x1" and shown[10] == "11 | x11"


def test_invalid_citation_list():
    from src.generators.render import format_invalid_citations
    from src.citations.validator import validate_document
    source = {"cells": [{"cell_id": 1, "language": "python", "code": "a=1\nb=2"}]}
    doc = "x [Cell 7, Risk]. y [Cell 1, lines 1-9]. z [Cell 3, line 1]. again [Cell 7, Risk]."
    md = format_invalid_citations(validate_document(doc, source)["invalid"])
    assert md.splitlines() == [
        "- `Cell 7, Risk`: no line number (×2)",
        "- `Cell 1, lines 1-9`: line range outside the cell",
        "- `Cell 3, line 1`: cell does not exist",
    ]


def test_invalid_citation_list_is_capped():
    from src.generators.render import format_invalid_citations
    items = [{"citation": f"Cell {i}, x", "reason": "no line number"} for i in range(25)]
    md = format_invalid_citations(items, limit=20).splitlines()
    assert len(md) == 21 and md[-1] == "- …and 5 more"
