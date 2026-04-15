from ai_ingest.models import RawItem
from ai_ingest.sources import _balance_candidates, strip_html


def test_strip_html_removes_markup() -> None:
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_keeps_plain_text() -> None:
    assert strip_html("plain text") == "plain text"


def test_balance_candidates_round_robins_sources() -> None:
    groups = [
        [
            RawItem(id="hf-1", source="hf", source_label="HF", title="A1", url="https://a1", summary=""),
            RawItem(id="hf-2", source="hf", source_label="HF", title="A2", url="https://a2", summary=""),
            RawItem(id="hf-3", source="hf", source_label="HF", title="A3", url="https://a3", summary=""),
        ],
        [
            RawItem(id="ls-1", source="ls", source_label="LS", title="B1", url="https://b1", summary=""),
            RawItem(id="ls-2", source="ls", source_label="LS", title="B2", url="https://b2", summary=""),
        ],
        [
            RawItem(id="sw-1", source="sw", source_label="SW", title="C1", url="https://c1", summary=""),
        ],
    ]

    balanced = _balance_candidates(groups, max_items=6)

    assert [item.id for item in balanced] == ["hf-1", "ls-1", "sw-1", "hf-2", "ls-2", "hf-3"]
