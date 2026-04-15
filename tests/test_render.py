from ai_ingest.models import RankedItem
from ai_ingest.render import render_markdown


def test_render_markdown_groups_by_source() -> None:
    items = [
        RankedItem(
            id="1",
            source="huggingface",
            source_label="Hugging Face",
            title="Post A",
            url="https://example.com/a",
            summary="sum",
            relevance_score=9,
            one_line="One line",
            key_takeaway="Takeaway",
            skills=["rag", "evals"],
            category="tooling",
        ),
        RankedItem(
            id="2",
            source="huggingface",
            source_label="Hugging Face",
            title="Post B",
            url="https://example.com/b",
            summary="sum",
            relevance_score=7,
            one_line="Another",
            key_takeaway="Another takeaway",
            skills=[],
            category="technique",
        ),
    ]

    output = render_markdown("April 14, 2026", "Short summary", items)

    assert "# AI Ingest - April 14, 2026" in output
    assert "### Hugging Face" in output
    assert "skills: rag, evals" in output
