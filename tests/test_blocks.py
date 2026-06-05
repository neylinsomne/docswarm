from docswarm.orchestration import blocks


def test_emphasis_becomes_marks_not_characters():
    doc = blocks.build_document("s", "d", "This is **bold** and *italic* text.")
    runs = doc["blocks"][0]["runs"]
    texts = [r.get("text") for r in runs]
    assert "bold" in texts and "italic" in texts
    # asterisks never survive into the text
    assert all("*" not in (t or "") for t in texts)
    bold = next(r for r in runs if r.get("text") == "bold")
    assert "bold" in bold["marks"]


def test_table_parsed_with_columns_and_rows():
    md = "| A | B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |"
    doc = blocks.build_document("s", "d", md)
    table = next(b for b in doc["blocks"] if b["type"] == "table")
    assert table["columns"] == ["A", "B"]
    assert table["rows"] == [["1", "2"], ["3", "4"]]


def test_ref_and_citation_runs():
    doc = blocks.build_document("s", "d", "See [ref:tbl-x] and [FRAG #42].")
    runs = doc["blocks"][0]["runs"]
    assert any(r.get("type") == "ref" and r.get("anchor_id") == "tbl-x" for r in runs)
    assert any(r.get("type") == "citation" and "42" in r.get("source", "") for r in runs)


def test_assign_anchor_binds_first_unanchored_table():
    doc = blocks.build_document("s", "d", "| A | B |\n| --- | --- |\n| 1 | 2 |")
    blocks.assign_anchor(doc, ["tbl-x"])
    table = next(b for b in doc["blocks"] if b["type"] == "table")
    assert table["anchor_id"] == "tbl-x"
    summary = blocks.anchor_summary(doc, "tbl-x")
    assert summary and "cols" in summary
