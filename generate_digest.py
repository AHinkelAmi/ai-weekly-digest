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
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
)
from reportlab.platypus import Frame, PageTemplate
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

FEEDS_FILE = Path(__file__).parent / "feeds.yaml"
OUTPUT_DIR = Path(__file__).parent / "output"
LOOKBACK_DAYS = 7
MAX_ITEMS_PER_SOURCE = 5

# Brand colours
C_DARK    = colors.HexColor("#0d1b2a")
C_BLUE    = colors.HexColor("#1565c0")
C_BLUE_L  = colors.HexColor("#e8f0fe")
C_ACCENT  = colors.HexColor("#0288d1")
C_GRAY    = colors.HexColor("#546e7a")
C_LGRAY   = colors.HexColor("#eceff1")
C_TEXT    = colors.HexColor("#212121")
C_MUTED   = colors.HexColor("#78909c")
C_ERROR   = colors.HexColor("#c62828")
C_WHITE   = colors.white


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
        return ""

    prompt = (
        f"Article title: {title}\n\n"
        f"Article description: {raw_text}\n\n"
        "Write a clear, informative 2–3 sentence summary of this article "
        "for an AI/tech newsletter. Be concrete and specific. "
        "Do not start with 'The article', do not repeat the title, "
        "do not use markdown formatting, do not use hashtags or headings. "
        "Write plain prose only. Write in English."
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    # Strip any accidental markdown headings Claude might add
    text = message.content[0].text.strip()
    text = re.sub(r"^#+\s+\S[^\n]*\n*", "", text).strip()
    return text


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
                seen_titles = set()
                for entry in parsed.entries:
                    pub_date = parse_entry_date(entry)
                    if pub_date and pub_date < cutoff:
                        continue
                    title = clean_text(getattr(entry, "title", "Untitled"))
                    # Deduplicate near-identical titles
                    title_key = re.sub(r"\W+", "", title.lower())
                    if title_key in seen_titles:
                        continue
                    seen_titles.add(title_key)

                    raw_summary = clean_text(getattr(entry, "summary", ""))

                    if keywords:
                        haystack = f"{title} {raw_summary}".lower()
                        if not keyword_matches(haystack, keywords):
                            continue

                    candidates.append({
                        "title": title,
                        "raw": raw_summary,
                        "link": getattr(entry, "link", ""),
                        "date": pub_date.strftime("%b %d, %Y") if pub_date else "n/a",
                    })

                for item in candidates[:MAX_ITEMS_PER_SOURCE]:
                    print(f"  Summarising: {item['title'][:70]}…")
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


def make_styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        base.add(ParagraphStyle(name=name, **kw))

    add("DigestTitle",
        fontSize=26, leading=30, spaceAfter=2,
        textColor=C_WHITE, fontName="Helvetica-Bold")
    add("DigestSubtitle",
        fontSize=9, leading=13, spaceAfter=0,
        textColor=colors.HexColor("#bbdefb"))
    add("WeekLabel",
        fontSize=8, leading=10,
        textColor=colors.HexColor("#90caf9"), spaceAfter=0,
        alignment=TA_RIGHT)
    add("SectionHeading",
        fontSize=13, leading=16, spaceBefore=18, spaceAfter=8,
        textColor=C_BLUE, fontName="Helvetica-Bold",
        borderPad=0)
    add("ArticleTitle",
        fontSize=10, leading=13, spaceAfter=1,
        textColor=C_DARK, fontName="Helvetica-Bold")
    add("ArticleMeta",
        fontSize=7.5, leading=10, spaceAfter=3,
        textColor=C_MUTED)
    add("ArticleBody",
        fontSize=9, leading=13, spaceAfter=0,
        textColor=C_TEXT)
    add("NoItems",
        fontSize=9, leading=12, spaceAfter=6,
        textColor=C_MUTED, fontName="Helvetica-Oblique")
    add("ErrorNote",
        fontSize=8, leading=11, spaceAfter=6,
        textColor=C_ERROR, fontName="Helvetica-Oblique")
    add("Footer",
        fontSize=7, leading=9,
        textColor=C_MUTED, alignment=TA_CENTER)

    return base


def header_footer(canvas, doc):
    """Draw the cover band on page 1 and a slim rule + footer on all pages."""
    canvas.saveState()
    W, H = A4

    if doc.page == 1:
        # Dark header band
        band_h = 52 * mm
        canvas.setFillColor(C_DARK)
        canvas.rect(0, H - band_h, W, band_h, fill=1, stroke=0)
        # Accent stripe
        canvas.setFillColor(C_ACCENT)
        canvas.rect(0, H - band_h - 3, W, 3, fill=1, stroke=0)

    # Footer rule + text on every page
    canvas.setStrokeColor(C_LGRAY)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 13 * mm, W - 18 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(C_MUTED)
    canvas.drawCentredString(W / 2, 9 * mm,
        f"Weekly AI Digest  ·  Summaries generated by Claude  ·  Page {doc.page}")

    canvas.restoreState()


def build_pdf(sources, output_path: Path, week_label: str, date_label: str):
    styles = make_styles()

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        topMargin=58 * mm,   # leave room for header band on page 1
        bottomMargin=20 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )

    story = []

    # ── Header content (sits inside the dark band via negative spacer trick) ──
    # We use an absolute-positioned canvas draw in header_footer; here we just
    # add the title text as normal flowables that land in the top margin area.
    # Because topMargin=58mm and the band is also 52mm, we push content up
    # with a negative spacer to place it inside the band.
    story.append(Spacer(1, -46 * mm))
    story.append(Paragraph("Weekly AI Digest", styles["DigestTitle"]))
    story.append(Paragraph(
        f"AI & Technology · {week_label}",
        styles["DigestSubtitle"]))
    story.append(Spacer(1, 44 * mm))  # back down past the band

    total_items = 0
    active_sources = [s for s in sources if s["items"] or s["error"]]

    for source in sources:
        has_content = bool(source["items"]) or bool(source["error"])

        story.append(Paragraph(source["name"], styles["SectionHeading"]))
        story.append(HRFlowable(width="100%", color=C_BLUE_L, thickness=1, spaceAfter=6))

        if source["error"]:
            story.append(Paragraph(
                f"Feed unavailable: {source['error']}",
                styles["ErrorNote"]))
            continue

        if not source["items"]:
            story.append(Paragraph("No new items this week.", styles["NoItems"]))
            continue

        for i, item in enumerate(source["items"]):
            total_items += 1
            title_text = f'<link href="{item["link"]}" color="#1565c0">{item["title"]}</link>'
            block = [
                Paragraph(title_text, styles["ArticleTitle"]),
                Paragraph(item["date"], styles["ArticleMeta"]),
            ]
            if item["summary"]:
                block.append(Paragraph(item["summary"], styles["ArticleBody"]))

            story.append(KeepTogether(block))

            # Thin divider between articles, not after the last one
            if i < len(source["items"]) - 1:
                story.append(Spacer(1, 6))
                story.append(HRFlowable(
                    width="100%", color=C_LGRAY, thickness=0.5, spaceAfter=6))

        story.append(Spacer(1, 4))

    if total_items == 0:
        story.append(Paragraph(
            "No items were found this week. Check feed URLs in feeds.yaml.",
            styles["ErrorNote"]))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)


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
    week_label = f"{week_start.strftime('%b %d')} – {today.strftime('%b %d, %Y')}"
    date_label = today.isoformat()

    output_path = OUTPUT_DIR / f"AI_Digest_{date_label}.pdf"
    build_pdf(sources, output_path, week_label, date_label)
    print(f"Digest written to {output_path}")


if __name__ == "__main__":
    main()
