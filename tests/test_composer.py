from docswarm.orchestration import blocks, composer


def _section(section_id, order, title, content, produces=None):
    doc = blocks.build_document(section_id, "d", content)
    if produces:
        blocks.assign_anchor(doc, produces)
    return {"section_id": section_id, "order_key": order, "title": title,
            "document": doc}


def test_numbering_and_cross_reference_resolution():
    producer = _section(
        "metrics", 100, "Metrics",
        "| Metric | Value |\n| --- | --- |\n| A | 1 |",
        produces=["tbl-metrics"])
    consumer = _section(
        "analysis", 200, "Analysis",
        "As shown in [ref:tbl-metrics] the trend is clear.")

    out = composer.compose_document([consumer, producer])  # order intentionally swapped

    # late binding numbers the table and resolves the ref regardless of input order
    assert out["anchors"]["tbl-metrics"]["label"] == "Table 1"
    assert "Table 1" in out["markdown"]
    assert "[pending reference]" not in out["markdown"]
    assert out["section_order"] == ["metrics", "analysis"]


def test_missing_reference_is_flagged_not_crashed():
    consumer = _section("analysis", 100, "Analysis", "See [ref:ghost].")
    out = composer.compose_document([consumer])
    assert any("ghost" in w for w in out["warnings"])
    assert "[pending reference]" in out["markdown"]
