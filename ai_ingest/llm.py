from __future__ import annotations

import json
from itertools import islice
from typing import Iterable, Iterator

from litellm import completion

from ai_ingest.models import RawItem, RankedItem


SYSTEM_PROMPT = """You are an ML/AI signal filter.

Your job:
- find the items that matter to an ML/AI engineer or job seeker
- ignore fluff, low-signal opinion, repeated announcements, and irrelevant content
- prefer practical tools, production techniques, platform changes, hiring signals, and concrete implementation details

Return strict JSON only. No markdown fences. No explanation.
"""


RANK_PROMPT = """Review these candidate items and keep only the useful ones.

Return JSON with this exact shape:
{{
  "items": [
    {{
      "id": "candidate-id",
      "relevance_score": 8,
      "one_line": "one sentence summary under 120 chars",
      "key_takeaway": "1-2 sentences on why it matters",
      "skills": ["skill a", "skill b"],
      "category": "tooling"
    }}
  ]
}}

Allowed categories: tooling, technique, research, jobs, platform, industry, other
Use relevance_score 1-10.
Drop items below {score_threshold}/10 instead of returning them.

Candidates:
{payload}
"""


SYNTHESIS_PROMPT = """Create a concise daily digest from these ranked items.

Return JSON with this exact shape:
{{
  "summary": "3 short paragraphs, plain text, under 220 words"
}}

Requirements:
- lead with the most actionable developments
- mention repeat skill themes if job posts appear
- end with one concrete action for this week

Ranked items:
{payload}
"""


def chunked(items: Iterable[RawItem], size: int) -> Iterator[list[RawItem]]:
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def rank_items(items: list[RawItem], model: str, batch_size: int, score_threshold: int) -> list[RankedItem]:
    ranked: list[RankedItem] = []
    for batch in chunked(items, batch_size):
        ranked.extend(_rank_batch(batch, model=model, score_threshold=score_threshold))
    ranked.sort(key=lambda item: item.relevance_score, reverse=True)
    return ranked


def synthesize(items: list[RankedItem], model: str, top_n: int) -> str:
    payload = json.dumps([item.compact() for item in items[:top_n]], ensure_ascii=True)
    content = _completion_text(
        model=model,
        prompt=SYNTHESIS_PROMPT.format(payload=payload),
        max_tokens=700,
    )
    try:
        parsed = _parse_json(content)
        summary = str(parsed.get("summary", "")).strip()
        if summary:
            return summary
    except Exception:
        pass
    return _fallback_summary(items[:top_n])


def _completion_text(model: str, prompt: str, max_tokens: int) -> str:
    response = completion(
        model=model,
        temperature=0,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    message = response.choices[0].message
    content = message.content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                parts.append(str(part.get("text", "")))
                continue
            text = getattr(part, "text", None)
            if text:
                parts.append(str(text))
        return "".join(parts)
    return str(content)


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        chunks = cleaned.split("```")
        cleaned = chunks[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


def _fallback_summary(items: list[RankedItem]) -> str:
    if not items:
        return "No ranked items were available for this run."

    top = items[:3]
    leads = []
    for item in top:
        leads.append(f"{item.title} ({item.source_label}) stands out: {item.key_takeaway or item.one_line}")

    skills: list[str] = []
    for item in items:
        for skill in item.skills:
            if skill not in skills:
                skills.append(skill)
            if len(skills) >= 6:
                break
        if len(skills) >= 6:
            break

    skill_line = ""
    if skills:
        skill_line = f"\n\nRecurring skill signals: {', '.join(skills)}."

    action = f"\n\nThis week: read {top[0].title} and decide whether it changes your current tooling or workflow."
    return " ".join(leads) + skill_line + action


def _rank_batch(batch: list[RawItem], model: str, score_threshold: int) -> list[RankedItem]:
    payload = json.dumps([item.compact() for item in batch], ensure_ascii=True)
    try:
        content = _completion_text(
            model=model,
            prompt=RANK_PROMPT.format(score_threshold=score_threshold, payload=payload),
            max_tokens=1800,
        )
        parsed = _parse_json(content)
    except Exception:
        if len(batch) > 1:
            midpoint = len(batch) // 2
            return _rank_batch(batch[:midpoint], model=model, score_threshold=score_threshold) + _rank_batch(
                batch[midpoint:], model=model, score_threshold=score_threshold
            )
        fallback = _fallback_rank(batch[0])
        return [fallback] if fallback.relevance_score >= score_threshold else []

    ranked: list[RankedItem] = []
    by_id = {item.id: item for item in batch}
    for result in parsed.get("items", []):
        original = by_id.get(result.get("id", ""))
        if not original:
            continue
        score = int(result.get("relevance_score", 0))
        if score < score_threshold:
            continue
        ranked.append(
            RankedItem(
                id=original.id,
                source=original.source,
                source_label=original.source_label,
                title=original.title,
                url=original.url,
                summary=original.summary,
                published=original.published,
                relevance_score=score,
                one_line=str(result.get("one_line", "")).strip(),
                key_takeaway=str(result.get("key_takeaway", "")).strip(),
                skills=[str(skill).strip() for skill in result.get("skills", []) if str(skill).strip()],
                category=str(result.get("category", "other")).strip() or "other",
            )
        )
    return ranked


def _fallback_rank(item: RawItem) -> RankedItem:
    text = f"{item.title} {item.summary}".lower()
    keywords = {
        "rag",
        "embedding",
        "rerank",
        "agent",
        "llm",
        "voice",
        "multimodal",
        "evaluation",
        "fine-tuning",
        "rlhf",
        "dpo",
        "deployment",
        "serving",
        "transformer",
        "benchmark",
        "open weights",
        "inference",
    }
    score = 3
    for keyword in keywords:
        if keyword in text:
            score += 1
    score = min(score, 8)
    return RankedItem(
        id=item.id,
        source=item.source,
        source_label=item.source_label,
        title=item.title,
        url=item.url,
        summary=item.summary,
        published=item.published,
        relevance_score=score,
        one_line=item.title[:120],
        key_takeaway=(item.summary[:220] or item.title[:220]).strip(),
        skills=[],
        category="other",
    )
