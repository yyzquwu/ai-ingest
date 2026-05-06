from pathlib import Path
import sys

import pytest

from ai_ingest.config import Settings
from ai_ingest.models import RankedItem, RawItem


@pytest.mark.parametrize("has_ranked_item", [True, False])
def test_dry_run_does_not_save_seen_items(monkeypatch, tmp_path: Path, has_ranked_item: bool) -> None:
    import ai_ingest.main as main_module

    raw_item = RawItem(
        id="item-1",
        source="test",
        source_label="Test Source",
        title="Useful AI update",
        url="https://example.com/item-1",
        summary="A useful update.",
    )
    ranked_item = RankedItem(
        id=raw_item.id,
        source=raw_item.source,
        source_label=raw_item.source_label,
        title=raw_item.title,
        url=raw_item.url,
        summary=raw_item.summary,
        relevance_score=8,
        one_line="Useful AI update",
        key_takeaway="Worth reading.",
        skills=["testing"],
        category="tooling",
    )
    settings = Settings(
        model="test/model",
        batch_size=12,
        max_items=60,
        top_n=10,
        score_threshold=5,
        subject_prefix="AI Ingest",
        sources_file=tmp_path / "sources.toml",
        output_dir=tmp_path / "out",
        seen_file=tmp_path / "state" / "seen_ids.json",
        smtp_host="smtp.example.com",
        smtp_port=465,
        smtp_use_starttls=False,
        smtp_username="sender@example.com",
        smtp_password="password",
        smtp_from="sender@example.com",
        ingest_to="recipient@example.com",
    )

    async def fake_fetch_candidates(specs, seen_ids, max_items):
        return [raw_item]

    def fake_write_outputs(output_dir, date_label, summary, items):
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = output_dir / "latest.md"
        html_path = output_dir / "latest.html"
        json_path = output_dir / "latest.json"
        markdown_path.write_text("# Digest\n")
        html_path.write_text("<h1>Digest</h1>\n")
        json_path.write_text("{}\n")
        return markdown_path, html_path, json_path

    saved_seen_ids = []
    sent_emails = []

    monkeypatch.setattr(sys, "argv", ["ai-ingest", "--dry-run"])
    monkeypatch.setattr(main_module, "load_settings", lambda: settings)
    monkeypatch.setattr(main_module, "load_source_specs", lambda path: [])
    monkeypatch.setattr(main_module, "load_seen_ids", lambda path: {"already-seen"})
    monkeypatch.setattr(main_module, "fetch_candidates", fake_fetch_candidates)
    monkeypatch.setattr(main_module, "rank_items", lambda **kwargs: [ranked_item] if has_ranked_item else [])
    monkeypatch.setattr(main_module, "synthesize", lambda items, model, top_n: "Summary")
    monkeypatch.setattr(main_module, "write_outputs", fake_write_outputs)
    monkeypatch.setattr(main_module, "render_markdown", lambda date_label, summary, items: "# Digest\n")
    monkeypatch.setattr(main_module, "save_seen_ids", lambda path, ids: saved_seen_ids.append(set(ids)))
    monkeypatch.setattr(main_module, "send_email", lambda **kwargs: sent_emails.append(kwargs))

    main_module.main()

    assert saved_seen_ids == []
    assert sent_emails == []
