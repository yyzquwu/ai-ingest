from __future__ import annotations

from collections import defaultdict
from html import escape
from pathlib import Path

from ai_ingest.models import RankedItem


def write_outputs(output_dir: Path, date_label: str, summary: str, articles: list[RankedItem]) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "latest.md"
    html_path = output_dir / "latest.html"
    json_path = output_dir / "latest.json"

    markdown_path.write_text(render_markdown(date_label, summary, articles))
    html_path.write_text(render_html(date_label, summary, articles))
    json_path.write_text(render_json(summary, articles))
    return markdown_path, html_path, json_path


def render_markdown(date_label: str, summary: str, articles: list[RankedItem]) -> str:
    sections: dict[str, list[RankedItem]] = defaultdict(list)
    for article in articles:
        sections[article.source_label].append(article)

    lines = [
        f"# AI Ingest - {date_label}",
        "",
        "## Top Picks",
        "",
        summary.strip(),
        "",
        "## Ranked Items",
        "",
    ]
    for source, items in sections.items():
        lines.extend([f"### {source}", ""])
        for item in items:
            skills = f" | skills: {', '.join(item.skills)}" if item.skills else ""
            lines.append(
                f"- [{item.title}]({item.url}) ({item.relevance_score}/10, {item.category})"
            )
            lines.append(f"  {item.one_line}")
            lines.append(f"  {item.key_takeaway}{skills}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_html(date_label: str, summary: str, articles: list[RankedItem]) -> str:
    sections: dict[str, list[RankedItem]] = defaultdict(list)
    for article in articles:
        sections[article.source_label].append(article)

    section_html: list[str] = []
    for source, items in sections.items():
        cards = []
        for item in items:
            skills = ""
            if item.skills:
                tags = "".join(f"<span class='tag'>{escape(skill)}</span>" for skill in item.skills)
                skills = f"<div class='tags'>{tags}</div>"
            cards.append(
                f"""
                <article class="card">
                  <div class="meta">{item.relevance_score}/10 · {escape(item.category)}</div>
                  <h3><a href="{escape(item.url)}">{escape(item.title)}</a></h3>
                  <p>{escape(item.one_line)}</p>
                  <p class="takeaway">{escape(item.key_takeaway)}</p>
                  {skills}
                </article>
                """
            )
        section_html.append(
            f"""
            <section>
              <h2>{escape(source)}</h2>
              {''.join(cards)}
            </section>
            """
        )

    summary_html = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in summary.strip().split("\n\n"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Ingest</title>
  <style>
    body {{ background: #f6f7fb; color: #0f172a; font-family: Arial, sans-serif; margin: 0; }}
    main {{ max-width: 880px; margin: 0 auto; padding: 32px 16px 48px; }}
    header {{ background: #0f172a; color: #fff; border-radius: 16px; padding: 24px; }}
    section {{ margin-top: 28px; }}
    .card {{ background: #fff; border: 1px solid #dbe2ea; border-radius: 14px; padding: 16px; margin-top: 12px; }}
    .meta {{ color: #475569; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .takeaway {{ color: #334155; }}
    a {{ color: #0f172a; }}
    .tag {{ display: inline-block; background: #e2e8f0; border-radius: 999px; font-size: 12px; margin: 8px 8px 0 0; padding: 3px 8px; }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>AI Ingest</div>
      <h1>{escape(date_label)}</h1>
      <div>{len(articles)} ranked items</div>
    </header>
    <section>
      <h2>Top Picks</h2>
      {summary_html}
    </section>
    {''.join(section_html)}
  </main>
</body>
</html>
"""


def render_json(summary: str, articles: list[RankedItem]) -> str:
    import json

    payload = {
        "summary": summary,
        "articles": [article.compact() for article in articles],
    }
    return json.dumps(payload, indent=2)
