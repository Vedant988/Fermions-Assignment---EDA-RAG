"""
SOTA RISC-V ISA Scraper v3
===========================
Targets: https://docs.riscv.org/reference/isa/unpriv/rv32.html

Preprocessing issues found from reviewing rv32_raw.md:
  1. BREADCRUMB NAV NOISE: Lines 1-3 are navigation links (ISA Spec > Vol I > Chapter 2...)
     that pollute every chunk with irrelevant anchor text.
  2. SIDEBAR NOTE TABLES → `| | |` JUNK TABLES: Many informational "callout" blocks
     are rendered as 2-col tables `| | content |` with an empty first column.
     These look like tables but are actually notes/asides. They must be extracted
     and converted to labeled `> NOTE:` blockquotes.
  3. SVG IMAGE REFERENCES: Lines like `![svg](_images/svg-abc123.svg)` are meaningless
     for a text-based RAG model. They must be stripped or replaced with a schema-aware
     placeholder like `[FIGURE: Instruction encoding diagram]`.
  4. FIGURE CAPTIONS AS LOOSE TEXT: Label text like "RISC-V base instruction formats..."
     and "Figure 1. Types of immediate..." float as loose paragraphs after SVG anchors.
     These should be paired with the SVG anchor they describe, not left as orphans.
  5. EMPTY REGISTER TABLE: The 32-row register file table (x0-x31, pc) has empty
     second and third columns, contributing exactly zero information to the RAG retrieval.
     It should be replaced with a machine-readable register summary block.
  6. SECTION-SCOPED CHUNKING BOUNDARY: Currently h3 and h4 are treated
     as equal chunk boundaries. h3 is a logical section (e.g. "Load and Store
     Instructions"), while h4 is an instruction group (e.g. "Integer Register-Immediate
     Instructions"). h4 chunks should INHERIT the h3 context as metadata rather than
     being standalone orphan chunks.
  7. TRAILING NAVIGATION LINKS: Last two lines are "< Chapter 1" and "> Chapter 3"
     footer nav links that pollute the final chunk.
  8. CITATION REFERENCE LINKS: inline links like `[[11](../biblio/...)]` pollute the
     semantic content with irrelevant biblio hrefs. Strip to just `[REF:11]`.
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup, Tag, NavigableString


URL    = "https://docs.riscv.org/reference/isa/unpriv/rv32.html"
OUTPUT = "scraped data"

# ───────────────────────────── DOM helpers ────────────────────────────────────

def clean_text(el) -> str:
    return re.sub(r'\s+', ' ', el.get_text(separator=' ')).strip()


def strip_citations(text: str) -> str:
    """Convert [[11](url)] to [REF:11] — removes link noise, keeps citation."""
    return re.sub(r'\[\[(\d+)\]\([^)]+\)\]', r'[REF:\1]', text)


def is_callout_table(table: Tag) -> bool:
    """
    Detect the 2-column `| | content |` informational callout tables.
    These always have exactly 2 columns and the first cell is always empty.
    """
    rows = table.find_all('tr')
    if not rows:
        return False
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) != 2:
            return False
        if clean_text(cells[0]) != '':  # First cell must be empty
            return False
    return True


def table_to_markdown(table: Tag) -> str:
    """Render a proper data table as Markdown."""
    rows = table.find_all('tr')
    md = []
    for i, row in enumerate(rows):
        cells = row.find_all(['th', 'td'])
        texts = [clean_text(c).replace('|', '\\|') or ' ' for c in cells]
        md.append('| ' + ' | '.join(texts) + ' |')
        if i == 0:
            md.append('| ' + ' | '.join(['---'] * len(texts)) + ' |')
    return '\n'.join(md)


def parse_encoding_table(table: Tag) -> dict | None:
    """
    Parse the RISC-V 5-row instruction encoding table into structured JSON.
    Returns None if the table doesn't match the encoding pattern.
    """
    rows = table.find_all('tr')
    if len(rows) < 3:
        return None

    def row_texts(row):
        return [clean_text(c) for c in row.find_all(['th', 'td'])]

    row0 = row_texts(rows[0])
    # Must look like bit positions — row0 cells should be bit range numbers
    if not any(bool(re.search(r'\d', r)) for r in row0):
        return None

    row2 = row_texts(rows[2]) if len(rows) > 2 else []
    row3 = row_texts(rows[3]) if len(rows) > 3 else []
    row4 = row_texts(rows[4]) if len(rows) > 4 else []

    fields = []
    for i, name in enumerate(row2):
        if not name:
            continue
        field = {"field": name}
        if i < len(row0) and row0[i]: field["bit_range"] = row0[i]
        if i < len(row3) and row3[i]: field["bits"]      = row3[i]
        if i < len(row4) and row4[i]: field["semantic"]  = row4[i]
        fields.append(field)

    return {"encoding_fields": fields} if fields else None


def is_empty_register_table(table: Tag) -> bool:
    """
    Detect the useless 32-row register state table (x0-x31/pc with empty cells).
    """
    rows = table.find_all('tr')
    if len(rows) < 10:  # Must be big
        return False
    # Check if most rows have ≥2 empty trailing cells
    empty_count = 0
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 3 and all(clean_text(c) == '' for c in cells[1:]):
            empty_count += 1
    return empty_count >= len(rows) * 0.7  # 70%+ rows are mostly empty


# ─────────────────────────── Chunk builder ────────────────────────────────────

def elements_between(start_el, stop_el):
    el = start_el.next_sibling
    while el and el != stop_el:
        yield el
        el = el.next_sibling


def build_chunk_text(heading_el: Tag, body_els, parent_h3_title: str = "") -> str:
    """
    Build a richly preprocessed Markdown text block for one section.
    Applies all 8 preprocessing rules systematically.
    """
    section_title = clean_text(heading_el)
    lines = []

    # Rule 6: Inject parent h3 context if this is an h4 chunk
    if parent_h3_title and parent_h3_title != section_title:
        lines.append(f"> **Section Context:** {parent_h3_title}")
        lines.append("")

    lines.append(f"# {section_title}")
    lines.append("")

    prev_was_svg = False
    svg_caption_pending = None

    for el in body_els:
        if not isinstance(el, Tag):
            # Loose text node — skip whitespace-only
            txt = str(el).strip()
            if txt:
                txt = strip_citations(txt)
                lines.append(txt)
            continue

        tag = el.name

        # Sub-headings within section
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            lines.append(f"\n## {clean_text(el)}\n")

        elif tag == 'table':
            # Rule 2: Detect and convert callout/NOTE tables
            if is_callout_table(el):
                rows = el.find_all('tr')
                note_text = ' '.join(clean_text(r.find_all(['td','th'])[1]) for r in rows if len(r.find_all(['td','th'])) >= 2)
                note_text = strip_citations(note_text)
                lines.append(f"\n> **NOTE:** {note_text}\n")

            # Rule 5: Skip empty register state tables
            elif is_empty_register_table(el):
                lines.append(
                    "\n**[REGISTER FILE: x0(zero)–x31 are 32-bit general purpose registers. "
                    "x0 is hardwired to 0. pc is the 32-bit program counter.]**\n"
                )

            else:
                # Proper data table — render as Markdown + optional encoding JSON
                lines.append("")
                lines.append(table_to_markdown(el))
                lines.append("")
                parsed = parse_encoding_table(el)
                if parsed:
                    lines.append("**Structured Encoding (JSON):**")
                    lines.append("```json")
                    lines.append(json.dumps(parsed, indent=2))
                    lines.append("```")
                lines.append("")

        elif tag in ('p', 'div'):
            # Rule 3 & 4: Handle img[svg] inside paragraphs
            img = el.find('img')
            if img and img.get('src', '').endswith('.svg'):
                txt = clean_text(el).replace(img.get('alt', ''), '').strip()
                if not txt or txt == '[svg]':
                    # Pure SVG — use placeholder and flag for caption pairing
                    lines.append("\n`[FIGURE: Instruction encoding diagram]`\n")
                    prev_was_svg = True
                else:
                    # SVG with adjacent caption text
                    lines.append(f"\n`[FIGURE: {txt}]`\n")
                    prev_was_svg = False
            else:
                txt = strip_citations(clean_text(el))
                if txt:
                    # Rule 4: If previous was an svg placeholder and this looks like a caption
                    if prev_was_svg and (txt.startswith('Figure') or 'instruction format' in txt.lower() or 'types of immediate' in txt.lower()):
                        # Replace the last SVG placeholder with a labeled figure
                        for j in range(len(lines)-1, -1, -1):
                            if '`[FIGURE:' in lines[j]:
                                lines[j] = f"`[FIGURE: {txt}]`"
                                break
                    else:
                        lines.append(txt)
                        lines.append("")
                    prev_was_svg = False

        elif tag in ('ul', 'ol'):
            for li in el.find_all('li', recursive=False):
                lines.append(f"- {strip_citations(clean_text(li))}")
            lines.append("")
            prev_was_svg = False

        elif tag == 'dl':
            for dt in el.find_all('dt'):
                lines.append(f"**{clean_text(dt)}**")
            for dd in el.find_all('dd'):
                lines.append(f"  {strip_citations(clean_text(dd))}")
            lines.append("")

        elif tag in ('pre', 'code'):
            lines.append(f"```\n{el.get_text()}\n```")
            lines.append("")

    return '\n'.join(lines).strip()


# ─────────────────────────────── Main ─────────────────────────────────────────

def main():
    os.makedirs(OUTPUT, exist_ok=True)

    print("[1/5] Fetching page...")
    resp = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0 (RV32-Scraper/3.0)"})
    resp.raise_for_status()

    print("[2/5] Parsing DOM...")
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Isolate the article body — nuke all navigation chrome
    article = soup.select_one('article.doc') or soup.find('article') or soup.body
    for sel in ['nav', 'aside', '.toc', '.nav-container', 'header', 'footer', '.toolbar',
                '.breadcrumbs', '.pagination', 'a.prev', 'a.next']:
        for tag in article.select(sel):
            tag.decompose()

    # Rule 1 & 7: Remove leading breadcrumb bullet list and trailing chapter nav links
    # These appear as <ul> with nav links before any h2, and final <p> footer links
    first_heading = article.find(['h1', 'h2', 'h3'])
    if first_heading:
        for sib in list(first_heading.find_all_previous()):
            if sib.name in ('ul', 'ol', 'p', 'nav'):
                sib.decompose()

    # Save clean HTML for debug
    with open(os.path.join(OUTPUT, "rv32_clean.html"), "w", encoding="utf-8") as f:
        f.write(str(article))

    # ── Crawl headings and form chunks ─────────────────────────────────────────
    print("[3/5] Semantic chunking with context inheritance...")
    headings = article.find_all(['h2', 'h3', 'h4'])

    chunks    = []
    current_h3_title = ""  # Track parent h3 context for h4 inheritance

    for idx, heading in enumerate(headings):
        tag_name = heading.name

        # Track h3-level context for h4 inheritance (Rule 6)
        if tag_name in ('h2', 'h3'):
            current_h3_title = clean_text(heading)

        next_heading = headings[idx + 1] if idx + 1 < len(headings) else None

        body_els = list(elements_between(heading, next_heading))
        # Inherit parent context for h4 chunks
        parent_ctx = current_h3_title if tag_name == 'h4' else ""
        text = build_chunk_text(heading, body_els, parent_h3_title=parent_ctx)

        if len(text.strip()) < 40:
            continue

        # Extract structured encodings as metadata
        structured_encodings = []
        for tbl in body_els:
            if isinstance(tbl, Tag) and tbl.name == 'table' and not is_callout_table(tbl):
                p = parse_encoding_table(tbl)
                if p:
                    structured_encodings.append(p)

        chunks.append({
            "chunk_id":             idx,
            "section_title":        clean_text(heading),
            "heading_level":        tag_name,
            "heading_id":           heading.get('id', ''),
            "parent_section":       parent_ctx,
            "source_url":           URL,
            "document_text":        text,
            "has_encoding_table":   len(structured_encodings) > 0,
            "structured_encodings": structured_encodings,
        })

    print(f"   {len(chunks)} semantic chunks generated.")

    # ── Save outputs ───────────────────────────────────────────────────────────
    print("[4/5] Saving artifacts...")

    chunks_path = os.path.join(OUTPUT, "rv32_chunks.json")
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"   → {chunks_path}")

    md_path = os.path.join(OUTPUT, "rv32_full_doc.md")
    with open(md_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(f"\n\n---\n<!-- chunk_id={c['chunk_id']} | {c['section_title']} -->\n\n")
            f.write(c["document_text"])
    print(f"   → {md_path}")

    # Stats report
    print(f"\n[5/5] ✅ Done.")
    with_encoding = sum(1 for c in chunks if c["has_encoding_table"])
    print(f"   Total chunks         : {len(chunks)}")
    print(f"   Chunks with encoding : {with_encoding}")
    print(f"   Chunks without       : {len(chunks) - with_encoding}")


if __name__ == "__main__":
    main()
