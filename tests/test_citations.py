from src.citations.validator import validate_document

def test_valid_citation():
    source = {"cells":[{"cell_id":1,"language":"python","code":"a=1\nb=2"}]}
    result = validate_document("Claim [Cell 1, lines 1-2].", source)
    assert len(result["valid"]) == 1
    assert not result["invalid"]

def test_invalid_citation():
    source = {"cells":[{"cell_id":1,"language":"python","code":"a=1"}]}
    result = validate_document("[Cell 1, lines 1-3]", source)
    assert len(result["invalid"]) == 1

def test_single_line_and_dash_variants():
    source = {"cells":[{"cell_id":1,"language":"python","code":"a=1\nb=2\nc=3"}]}
    doc = "A [Cell 1, line 2]. B [Cell 1, lines 1–3]. C [Cell 1, lines 2—3]."
    result = validate_document(doc, source)
    assert len(result["valid"]) == 3
    assert not result["invalid"]
    assert result["valid"][0]["start"] == result["valid"][0]["end"] == 2

def test_multiple_citations_in_one_bracket():
    source = {"cells":[{"cell_id":1,"language":"python","code":"a=1\nb=2"},
                       {"cell_id":2,"language":"python","code":"c=3"}]}
    result = validate_document("Claim [Cell 1, line 2; Cell 2, lines 1-4].", source)
    assert len(result["valid"]) == 1
    assert len(result["invalid"]) == 1
    assert result["invalid"][0]["cell"] == 2

def test_missing_cell_is_invalid():
    source = {"cells":[{"cell_id":1,"language":"python","code":"a=1"}]}
    result = validate_document("[Cell 9, line 1]", source)
    assert len(result["invalid"]) == 1

def test_unbracketed_mentions_are_ignored():
    source = {"cells":[{"cell_id":1,"language":"python","code":"a=1"}]}
    result = validate_document("Cell 1, line 5 is described in prose.", source)
    assert result["count"] == 0

def test_cell_without_line_number_is_invalid():
    source = {"cells":[{"cell_id":1,"language":"python","code":"a=1"}]}
    result = validate_document("Risky [Cell 7, Risk]. Open [Cell 1, Hypotheses].", source)
    assert len(result["invalid"]) == 2
    assert {i["reason"] for i in result["invalid"]} == {"no line number"}
    assert result["invalid"][0]["citation"] == "Cell 7, Risk"

def test_mixed_group_flags_only_the_bad_part():
    source = {"cells":[{"cell_id":1,"language":"python","code":"a=1\nb=2"}]}
    result = validate_document("Claim [Cell 1, line 2; Cell 7, Testing Recommendations].", source)
    assert len(result["valid"]) == 1
    assert len(result["invalid"]) == 1 and result["invalid"][0]["cell"] == 7
