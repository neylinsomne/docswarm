from docswarm.orchestration import blackboard


def test_publish_and_filtered_view():
    bid = blackboard.create_board({"company": "ACME"})
    try:
        blackboard.publish_anchor(bid, "tbl-x", type="table", section_id="a",
                                  title="X", summary="3 rows")
        blackboard.publish_anchor(bid, "tbl-y", type="table", section_id="b",
                                  title="Y", summary="5 rows")
        view = blackboard.get_view(bid, ["tbl-x"])
        assert set(view) == {"tbl-x"}
        assert view["tbl-x"]["summary"] == "3 rows"
        assert blackboard.get_facts(bid)["company"] == "ACME"
        assert set(blackboard.get_view(bid)) == {"tbl-x", "tbl-y"}
    finally:
        blackboard.clear_board(bid)


def test_missing_board_is_safe():
    assert blackboard.get_facts("nope") == {}
    assert blackboard.get_view("nope") == {}
