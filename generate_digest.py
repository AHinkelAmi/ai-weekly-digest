"""
Weekly AI Digest Generator
--------------------------
Liest RSS-Feeds aus feeds.yaml, filtert Artikel der letzten 7 Tage und
erzeugt ein PDF mit KI-generierten Zusammenfassungen via Claude API.

Aufruf: python generate_digest.py
Ergebnis: output/AI_Digest_<YYYY-MM-DD>.pdf
"""

import os
import re
import html
import datetime as dt
from pathlib import Path

import anthropic
import feedparser
import yaml
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable
)

FEEDS_FILE = Path(__file__).parent / "feeds.yaml"
OUTPUT_DIR = Path(__file__).parent / "output"
LOOKBACK_DAYS = 7
MAX_ITEMS_PER_SOURCE = 5


def keyword_matches(haystack: str, keywords: list) -> bool:
    for kw in keywords:
        pattern = r"\b" + re.escape(kw.strip()) + r"\b"
        if re.search(pattern, haystack):
            return True
    return False


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_entry_date(entry) -> dt.datetime | None:
    for field in ("published_parsed", "updated_parsed"):
        value = getattr(entry, field, None)
        if value:
            return dt.datetime(*value[:6])
    return None


def load_feeds():
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("feeds", [])


def summarise(client: anthropic.Anthropic, title: str, raw_text: str) -> str:
    """Summarise a single article in 2–3 sentences using Claude."""
    if not raw_text.strip():
        return "(No description available.)"

    prompt = (
        f"Article title: {title}\n\n"
        f"Article description: {raw_text}\n\n"
        "Write a clear, informative 2–3 sentence summary of this article "
        "for an AI/tech newsletter. Be concrete and specific. "
        "Do not start with 'The article' or repeat the title. "
        "Write in English."
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def collect_items(feeds, client: anthropic.Anthropic):
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=LOOKBACK_DAYS)
    sources = []

    for feed in feeds:
        name, url = feed["name"], feed["url"]
        keywords = [k.lower() for k in feed.get("keywords", [])]
        result = {"name": name, "url": url, "items": [], "error": None}

        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                result["error"] = str(parsed.bozo_exception) or "feed unreachable or empty"
            else:
                candidates = []
                for entry in parsed.entries:
                    pub_date = parse_entry_date(entry)
                    if pub_date and pub_date < cutoff:
                        continue
                    title = clean_text(getattr(entry, "title", "Untitled"))
                    raw_summary = clean_text(getattr(entry, "summary", ""))

                    if keywords:
                        haystack = f"{title} {raw_summary}".lower()
                        if not keyword_matches(haystack, keywords):
                            continue

                    candidates.append({
                        "title": title,
                        "raw": raw_summary,
                        "link": getattr(entry, "link", ""),
                        "date": pub_date.strftime("%Y-%m-%d") if pub_date else "n/a",
                    })

                for item in candidates[:MAX_ITEMS_PER_SOURCE]:
                    print(f"  Summarising: {item['title'][:60]}…")
                    summary = summarise(client, item["title"], item["raw"])
                    result["items"].append({
                        "title": item["title"],
                        "summary": summary,
                        "link": item["link"],
                        "date": item["date"],
                    })

        except Exception as exc:
            result["error"] = str(exc)

        sources.append(result)

    return sources


def build_pdf(sources, output_path: Path, week_label: str):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="DigestTitle", fontSize=20, leading=24, spaceAfter=4,
        textColor=colors.HexColor("#1a1a2e"),
    ))
    styles.add(ParagraphStyle(
        name="DigestSubtitle", fontSize=10, leading=14,
        textColor=colors.HexColor("#555555"), spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        name="SourceHeading", fontSize=13, leading=16, spaceBefore=14, spaceAfter=6,
        textColor=colors.HexColor("#0f4c81"),
    ))
    styles.add(ParagraphStyle(
        name="ItemTitle", fontSize=10.5, leading=13, spaceAfter=1,
        textColor=colors.HexColor("#111111"),
    ))
    styles.add(ParagraphStyle(
        name="ItemMeta", fontSize=8, leading=10,
        textColor=colors.HexColor("#888888"), spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="ItemSummary", fontSize=9.5, leading=13,
        textColor=colors.HexColor("#333333"), spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="NoItems", fontSize=9.5, leading=13, spaceAfter=8,
        textColor=colors.HexColor("#999999"), fontName="Helvetica-Oblique",
    ))
    styles.add(ParagraphStyle(
        name="ErrorNote", fontSize=8.5, leading=11, spaceAfter=8,
        textColor=colors.HexColor("#b02a2a"), fontName="Helvetica-Oblique",
    ))

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        topMargin=20 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )

    story = [
        Paragraph("Weekly AI Digest", styles["DigestTitle"]),
        Paragraph(
            f"Curated update covering {week_label}. Sources: official lab "
            f"announcements, MIT-affiliated reporting, and specialist AI press. "
            f"Summaries generated by Claude.",
            styles["DigestSubtitle"],
        ),
        HRFlowable(width="100%", color=colors.HexColor("#cccccc"), thickness=0.8),
    ]

    total_items = 0
    for source in sources:
        story.append(Paragraph(source["name"], styles["SourceHeading"]))

        if source["error"]:
            story.append(Paragraph(
                f"Could not retrieve this feed ({source['error']}). "
                f"Check the URL in feeds.yaml.",
                styles["ErrorNote"],
            ))
            continue

        if not source["items"]:
            story.append(Paragraph(
                "No new items in the last 7 days.", styles["NoItems"]
            ))
            continue

        for item in source["items"]:
            total_items += 1
            title_link = f'<link href="{item["link"]}">{item["title"]}</link>'
            story.append(Paragraph(title_link, styles["ItemTitle"]))
            story.append(Paragraph(item["date"], styles["ItemMeta"]))
            story.append(Paragraph(item["summary"], styles["ItemSummary"]))

    if total_items == 0:
        story.append(Paragraph(
            "No items were found across any source this week. "
            "This usually means the feed URLs need to be re-checked.",
            styles["ErrorNote"],
        ))

    doc.build(story)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Error: ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    OUTPUT_DIR.mkdir(exist_ok=True)
    feeds = load_feeds()

    print("Collecting and summarising articles…")
    sources = collect_items(feeds, client)

    today = dt.date.today()
    week_start = today - dt.timedelta(days=LOOKBACK_DAYS)
    week_label = f"{week_start.strftime('%b %d')}–{today.strftime('%b %d, %Y')}"

    output_path = OUTPUT_DIR / f"AI_Digest_{today.isoformat()}.pdf"
    build_pdf(sources, output_path, week_label)
    print(f"Digest written to {output_path}")


if __name__ == "__main__":
    main()
