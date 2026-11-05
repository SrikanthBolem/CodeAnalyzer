from src.ingestion.loader import load_source

def test_python_databricks_cells():
    raw = b"x = 1\n# COMMAND ----------\ny = 2\n"
    parsed = load_source("sample.py", raw)
    assert len(parsed["cells"]) == 2
    assert parsed["cells"][1]["code"] == "y = 2"

def test_sql_file():
    parsed = load_source("query.sql", b"select 1")
    assert parsed["cells"][0]["language"] == "sql"
