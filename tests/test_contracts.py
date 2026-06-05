from docswarm.config import plan_from_dict
from docswarm.orchestration.contracts import build_contracts

PLAN = {
    "title": "T",
    "sections": [
        {"id": "a", "agent": "x", "order": 1,
         "produces": [{"anchor_id": "tbl", "type": "table", "title": "T",
                       "schema": ["C1", "C2"]}]},
        {"id": "b", "agent": "y", "order": 2, "consumes": ["tbl"]},
        {"id": "c", "agent": "z", "order": 3, "consumes": ["ghost"]},
    ],
}


def test_build_contracts_from_dict_and_config_equivalent():
    from_dict = build_contracts(PLAN)
    from_cfg = build_contracts(plan_from_dict(PLAN))
    assert set(from_dict) == set(from_cfg) == {"a", "b", "c"}


def test_consumes_kept_only_if_produced():
    c = build_contracts(PLAN)
    assert c["b"].consumes == ["tbl"]      # produced by 'a' → kept
    assert c["c"].consumes == []           # 'ghost' produced by nobody → dropped


def test_order_key_from_order():
    c = build_contracts(PLAN)
    assert c["a"].order_key < c["b"].order_key < c["c"].order_key


def test_prompt_block_mentions_produce_and_cite():
    c = build_contracts(PLAN)
    assert "tbl" in c["a"].prompt_block()
    assert "[ref:tbl]" in c["b"].prompt_block()
