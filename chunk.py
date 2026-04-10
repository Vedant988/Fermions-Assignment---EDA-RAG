"""
Universal Chunker — chunk.py
=============================
Produces {slug}_chunks.json and {slug}_full_doc.md from ANY URL.

Supports these source types (auto-detected):
  HTML_DOC   — Technical documentation pages (like docs.riscv.org)
               Strategy: heading-based semantic chunking (h2/h3/h4),
               callout-table conversion, SVG stripping, citation cleanup.
               Mirrors chunk_isa.py logic, fully generalised.

  VERILOG    — Raw .v / .sv files from GitHub or any CDN
               Strategy: module/always/function-level chunking.
               Each module/block = one parent. Inline comments preserved.

  ASM        — RISC-V assembly .S files (riscv-tests style)
               Strategy: RVTEST_CODE_BEGIN → per-macro block chunking.
               Parses TEST_*_OP calls into structured JSON vectors.

  GITHUB_DIR — A GitHub directory URL (api.github.com or github.com/…/tree/…)
               Strategy: recursively fetch all files, route each file
               through the correct single-file handler above.

  MARKDOWN   — Raw .md files
               Strategy: heading-based chunking on # / ## / ###.

Usage:
  python chunk.py <url> [--output <dir>] [--slug <name>]

Examples:
  python chunk.py https://docs.riscv.org/reference/isa/unpriv/rv32.html
  python chunk.py https://github.com/YosysHQ/picorv32/blob/master/picorv32.v
  python chunk.py https://github.com/YosysHQ/picorv32/tree/master
  python chunk.py https://raw.githubusercontent.com/riscv-software-src/riscv-tests/master/isa/rv64ui/add.S
"""

import io
import os
import re
import sys
import json
import hashlib
import argparse
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
try:
    import fitz  # PyMuPDF — pip install pymupdf
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_OUTPUT = "scraped data"
GITHUB_API     = "https://api.github.com/repos"
GITHUB_RAW     = "https://raw.githubusercontent.com"
REQUEST_HDR    = {"User-Agent": "UniversalChunker/1.0", "Accept": "application/vnd.github.v3+json"}

# Verilog parent boundary keywords
VERILOG_PARENT_RE = re.compile(
    r'^(module|endmodule|always\s*@|always_ff|always_comb|always_latch'
    r'|initial|function|task|generate|`define)',
    re.MULTILINE | re.IGNORECASE
)

# riscv-tests macro pattern (reused from chunk_tests.py)
RISCV_TEST_MACRO_RE = re.compile(
    r'(TEST_\w+)\(\s*(\d+)\s*,\s*[\w.]+\s*,\s*([^)]+)\)',
    re.MULTILINE
)


# ──────────────────────────────────────────────────────────────────────────────
# 1. URL Type Detection
# ──────────────────────────────────────────────────────────────────────────────

def detect_source_type(url: str) -> str:
    """
    Heuristically classify the URL into one of:
      HTML_DOC | VERILOG | ASM | GITHUB_DIR | MARKDOWN | PDF | SKIP

    SKIP is returned for binary/non-text files that should be silently ignored
    (images, compiled objects, archives, fonts, SVG diagrams, etc.).
    """
    SKIP_EXTENSIONS = {
        '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp',
        '.bin', '.elf', '.o', '.a', '.so', '.hex', '.mem',
        '.gz', '.zip', '.tar', '.ttf', '.woff', '.woff2',
        '.core', '.pcf', '.lds', '.ld', '.h', '.c', '.cpp',
        '.py', '.yml', '.yaml', '.toml', '.json', '.gitignore',
    }
    p = urlparse(url)
    path_lower = p.path.lower()
    ext = '.' + path_lower.rsplit('.', 1)[-1] if '.' in path_lower.split('/')[-1] else ''
    if ext in SKIP_EXTENSIONS:
        return "SKIP"
    path_lower = p.path.lower()

    if p.netloc == "api.github.com":
        return "GITHUB_DIR"

    if "github.com" in p.netloc:
        # github.com/user/repo/tree/... → directory listing
        if "/tree/" in p.path:
            return "GITHUB_DIR"
        # github.com/user/repo/blob/... → single file — detect by extension
        if "/blob/" in p.path:
            url = github_blob_to_raw(url)  # normalise to raw
            path_lower = urlparse(url).path.lower()

    if path_lower.endswith((".v", ".sv", ".vh")):
        return "VERILOG"
    if path_lower.endswith(".s"):
        return "ASM"
    if path_lower.endswith(".md"):
        return "MARKDOWN"
    if path_lower.endswith(".pdf"):
        return "PDF"
    if path_lower.endswith(".html") or path_lower.endswith(".htm"):
        return "HTML_DOC"

    # Content-type sniff for ambiguous URLs
    try:
        head = requests.head(url, timeout=10, headers=REQUEST_HDR, allow_redirects=True)
        ct = head.headers.get("Content-Type", "")
        if "pdf" in ct:
            return "PDF"
        if "html" in ct:
            return "HTML_DOC"
        if "markdown" in ct or "plain" in ct:
            return "MARKDOWN"
    except Exception:
        pass

    return "HTML_DOC"  # safe fallback


def github_blob_to_raw(url: str) -> str:
    """Convert a github.com blob URL to a raw.githubusercontent.com URL."""
    # https://github.com/user/repo/blob/branch/path
    # → https://raw.githubusercontent.com/user/repo/branch/path
    return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")


def url_to_slug(url: str) -> str:
    """Create a safe filesystem slug from a URL."""
    p = urlparse(url)
    # Use the last meaningful path component
    parts = [x for x in p.path.split("/") if x]
    name = parts[-1] if parts else p.netloc
    # Strip extension
    name = re.sub(r'\.(html?|md|v|sv|S)$', '', name, flags=re.IGNORECASE)
    # Sanitise
    name = re.sub(r'[^\w\-]', '_', name)
    return name[:60] or "doc"


# ──────────────────────────────────────────────────────────────────────────────
# 2. Shared Utilities (from chunk_isa.py, generalised)
# ──────────────────────────────────────────────────────────────────────────────

def fetch(url: str) -> str | None:
    """Fetch URL content, following redirects, with a sensible UA."""
    try:
        r = requests.get(url, timeout=30, headers=REQUEST_HDR, allow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  [ERROR] Could not fetch {url}: {e}")
        return None


def clean_text(el) -> str:
    return re.sub(r'\s+', ' ', el.get_text(separator=' ')).strip()


def strip_citations(text: str) -> str:
    """[[11](url)] → [REF:11]"""
    return re.sub(r'\[(\d+)\]\([^)]+\)', r'[REF:\1]', text)


def rough_token_count(text: str) -> int:
    return int(len(text.split()) * 1.3)


# ──────────────────────────────────────────────────────────────────────────────
# 3. HTML_DOC Handler  (generalised chunk_isa.py)
# ──────────────────────────────────────────────────────────────────────────────

def is_callout_table(table: Tag) -> bool:
    rows = table.find_all('tr')
    if not rows:
        return False
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) != 2 or clean_text(cells[0]) != '':
            return False
    return True


def is_empty_register_table(table: Tag) -> bool:
    rows = table.find_all('tr')
    if len(rows) < 10:
        return False
    empty = sum(
        1 for row in rows
        if len(row.find_all(['td', 'th'])) >= 3
        and all(clean_text(c) == '' for c in row.find_all(['td', 'th'])[1:])
    )
    return empty >= len(rows) * 0.7


def table_to_markdown(table: Tag) -> str:
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
    rows = table.find_all('tr')
    if len(rows) < 3:
        return None
    def row_texts(r): return [clean_text(c) for c in r.find_all(['th', 'td'])]
    row0 = row_texts(rows[0])
    if not any(bool(re.search(r'\d', r)) for r in row0):
        return None
    row2 = row_texts(rows[2]) if len(rows) > 2 else []
    row3 = row_texts(rows[3]) if len(rows) > 3 else []
    row4 = row_texts(rows[4]) if len(rows) > 4 else []
    fields = []
    for i, name in enumerate(row2):
        if not name:
            continue
        f = {"field": name}
        if i < len(row0) and row0[i]: f["bit_range"] = row0[i]
        if i < len(row3) and row3[i]: f["bits"]      = row3[i]
        if i < len(row4) and row4[i]: f["semantic"]  = row4[i]
        fields.append(f)
    return {"encoding_fields": fields} if fields else None


def elements_between(start_el, stop_el):
    el = start_el.next_sibling
    while el and el != stop_el:
        yield el
        el = el.next_sibling


def build_html_chunk_text(heading_el, body_els, parent_context: str = "", source_url: str = "") -> str:
    """Generalised version of chunk_isa.py build_chunk_text."""
    section_title = clean_text(heading_el)
    lines = []
    if parent_context and parent_context != section_title:
        lines += [f"> **Section Context:** {parent_context}", ""]
    lines += [f"# {section_title}", ""]

    prev_was_svg = False

    for el in body_els:
        if not isinstance(el, Tag):
            txt = str(el).strip()
            if txt:
                lines.append(strip_citations(txt))
            continue

        tag = el.name

        if tag in ('h1','h2','h3','h4','h5','h6'):
            lines.append(f"\n## {clean_text(el)}\n")

        elif tag == 'table':
            if is_callout_table(el):
                rows = el.find_all('tr')
                note = ' '.join(
                    clean_text(r.find_all(['td','th'])[1])
                    for r in rows if len(r.find_all(['td','th'])) >= 2
                )
                lines.append(f"\n> **NOTE:** {strip_citations(note)}\n")
            elif is_empty_register_table(el):
                lines.append(
                    "\n**[REGISTER FILE: x0(zero)–x31 are 32-bit general purpose registers. "
                    "x0 is hardwired to 0. pc is the 32-bit program counter.]**\n"
                )
            else:
                lines += ["", table_to_markdown(el), ""]
                parsed = parse_encoding_table(el)
                if parsed:
                    lines += ["**Structured Encoding (JSON):**", "```json",
                               json.dumps(parsed, indent=2), "```"]
                lines.append("")

        elif tag in ('p', 'div'):
            img = el.find('img')
            if img and img.get('src', '').endswith('.svg'):
                txt = clean_text(el).replace(img.get('alt', ''), '').strip()
                if not txt or txt == '[svg]':
                    lines.append("\n`[FIGURE: Instruction encoding diagram]`\n")
                    prev_was_svg = True
                else:
                    lines.append(f"\n`[FIGURE: {txt}]`\n")
                    prev_was_svg = False
            else:
                txt = strip_citations(clean_text(el))
                if txt:
                    if prev_was_svg and (
                        txt.startswith('Figure') or
                        'instruction format' in txt.lower() or
                        'types of immediate' in txt.lower()
                    ):
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
            lines += [f"```\n{el.get_text()}\n```", ""]

    return '\n'.join(lines).strip()


def chunk_html(url: str, slug: str) -> list[dict]:
    print(f"  [HTML_DOC] Fetching {url}")
    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')

    # Isolate article body — strip nav chrome
    article = soup.select_one('article.doc') or soup.find('article') or soup.body
    if article is None:
        # SVG, XML, or unrecognised binary that slipped past SKIP detection
        print(f"  [SKIP] No HTML body found in {url} — skipping")
        return []
    for sel in ['nav', 'aside', '.toc', '.nav-container', 'header', 'footer',
                '.toolbar', '.breadcrumbs', '.pagination', 'a.prev', 'a.next']:
        for tag in article.select(sel):
            tag.decompose()

    # Remove pre-heading nav lists and footer nav links
    first_heading = article.find(['h1', 'h2', 'h3'])
    if first_heading:
        for sib in list(first_heading.find_all_previous()):
            if sib.name in ('ul', 'ol', 'p', 'nav'):
                sib.decompose()

    headings = article.find_all(['h2', 'h3', 'h4'])
    chunks = []
    current_h3_title = ""

    for idx, heading in enumerate(headings):
        tag_name = heading.name
        if tag_name in ('h2', 'h3'):
            current_h3_title = clean_text(heading)

        next_heading = headings[idx + 1] if idx + 1 < len(headings) else None
        body_els = list(elements_between(heading, next_heading))
        parent_ctx = current_h3_title if tag_name == 'h4' else ""
        text = build_html_chunk_text(heading, body_els, parent_context=parent_ctx, source_url=url)

        if len(text.strip()) < 40:
            continue

        structured = []
        for tbl in body_els:
            if isinstance(tbl, Tag) and tbl.name == 'table' and not is_callout_table(tbl):
                p = parse_encoding_table(tbl)
                if p:
                    structured.append(p)

        chunks.append({
            "chunk_id":             idx,
            "section_title":        clean_text(heading),
            "heading_level":        tag_name,
            "heading_id":           heading.get('id', ''),
            "parent_section":       parent_ctx,
            "source_url":           url,
            "document_type":        "html_doc",
            "has_encoding_table":   len(structured) > 0,
            "structured_encodings": structured,
            "document_text":        text,
        })

    return chunks


# ──────────────────────────────────────────────────────────────────────────────
# 4. VERILOG Handler
# ──────────────────────────────────────────────────────────────────────────────

def chunk_verilog(url: str, slug: str) -> list[dict]:
    """
    Chunk a Verilog file into parent blocks at module/always/function/task boundaries.
    Each parent = one logical hardware block. Lines preceding the first keyword
    are included in chunk 0 as file-level declarations.
    """
    raw_url = github_blob_to_raw(url) if "github.com" in url and "/blob/" in url else url
    print(f"  [VERILOG] Fetching {raw_url}")
    source = fetch(raw_url)
    if not source:
        return []

    lines = source.splitlines(keepends=True)
    # Find boundary line numbers
    boundaries = [0]
    for i, line in enumerate(lines):
        if VERILOG_PARENT_RE.match(line.strip()):
            if i > 0 and i not in boundaries:
                boundaries.append(i)
    boundaries.append(len(lines))

    chunks = []
    for idx in range(len(boundaries) - 1):
        start = boundaries[idx]
        end   = boundaries[idx + 1]
        block_lines = lines[start:end]
        block_text  = ''.join(block_lines).strip()

        if len(block_text) < 20:
            continue

        # Extract first non-empty, non-comment line as title
        title_line = next(
            (l.strip() for l in block_lines if l.strip() and not l.strip().startswith('//')),
            f"Block at line {start+1}"
        )
        title = title_line[:80]

        # Collect `// comment` lines immediately before this block as context
        leading_comment = []
        for l in reversed(block_lines[:min(5, len(block_lines))]):
            if l.strip().startswith('//'):
                leading_comment.insert(0, l.strip()[2:].strip())
            else:
                break
        comment_str = ' '.join(leading_comment)

        doc_text = (
            f"# Verilog Block: `{title}`\n\n"
            + (f"> **Block Comment:** {comment_str}\n\n" if comment_str else "")
            + f"> **Source:** `{raw_url}` | Lines {start+1}–{end}\n\n"
            + f"```verilog\n{block_text}\n```"
        )

        chunks.append({
            "chunk_id":       f"{slug}_{idx}",
            "section_title":  title,
            "source_url":     raw_url,
            "document_type":  "verilog_rtl",
            "start_line":     start + 1,
            "end_line":       end,
            "block_comment":  comment_str,
            "document_text":  doc_text,
        })

    return chunks


# ──────────────────────────────────────────────────────────────────────────────
# 5. ASM Handler  (generalised chunk_tests.py)
# ──────────────────────────────────────────────────────────────────────────────

def parse_asm_vectors(source: str) -> list[dict]:
    """Extract TEST_*_OP macro calls into structured JSON (from chunk_tests.py)."""
    vectors = []
    for m in RISCV_TEST_MACRO_RE.finditer(source):
        macro   = m.group(1).strip()
        test_id = int(m.group(2))
        args    = [a.strip() for a in m.group(3).split(',') if a.strip()]
        vec     = {"test_id": test_id, "macro": macro, "args": args}
        vectors.append(vec)
    return vectors


def chunk_asm(url: str, slug: str) -> list[dict]:
    """
    Chunk an assembly file. If it's a thin wrapper (#include only), attempt to
    fetch the canonical body from rv64ui/ mirror. Falls back to the raw source.
    """
    raw_url = github_blob_to_raw(url) if "github.com" in url and "/blob/" in url else url
    print(f"  [ASM] Fetching {raw_url}")
    source = fetch(raw_url)
    if not source:
        return []

    # Detect thin rv32ui wrapper → try rv64ui canonical body
    if source.count('\n') < 10 and '#include' in source:
        canonical_url = raw_url.replace('/rv32ui/', '/rv64ui/')
        if canonical_url != raw_url:
            alt = fetch(canonical_url)
            if alt:
                print(f"  [ASM] Using canonical rv64ui body from {canonical_url}")
                source = alt

    vectors = parse_asm_vectors(source)
    instruction = slug.upper()

    doc_text = (
        f"# Assembly Test: `{instruction}`\n\n"
        f"> **Source:** `{raw_url}`\n\n"
        f"## Parsed Test Vectors ({len(vectors)} total)\n\n"
        "```json\n"
        + json.dumps(vectors, indent=2)
        + "\n```\n\n"
        "## Raw Assembly Source\n\n"
        f"```asm\n{source.strip()}\n```"
    )

    return [{
        "chunk_id":         f"{slug}_asm",
        "section_title":    f"Assembly Test: {instruction}",
        "instruction":      instruction,
        "source_url":       raw_url,
        "document_type":    "asm_test",
        "total_test_cases": len(vectors),
        "test_vectors":     vectors,
        "document_text":    doc_text,
    }]


# ──────────────────────────────────────────────────────────────────────────────
# 6. MARKDOWN Handler
# ──────────────────────────────────────────────────────────────────────────────

def chunk_markdown(url: str, slug: str) -> list[dict]:
    """
    Split a raw Markdown file at heading boundaries (# ## ###).
    Each heading section = one parent chunk.
    """
    raw_url = github_blob_to_raw(url) if "github.com" in url and "/blob/" in url else url
    print(f"  [MARKDOWN] Fetching {raw_url}")
    source = fetch(raw_url)
    if not source:
        return []

    # Split on headings, keep the heading line with its block
    heading_re = re.compile(r'^(#{1,6})\s+(.+)', re.MULTILINE)
    positions  = [(m.start(), m.group(1), m.group(2)) for m in heading_re.finditer(source)]

    if not positions:
        # No headings — treat whole file as one chunk
        return [{
            "chunk_id":      f"{slug}_0",
            "section_title": slug,
            "source_url":    raw_url,
            "document_type": "markdown",
            "document_text": source.strip(),
        }]

    chunks = []
    parent_h2 = ""
    for idx, (pos, level, title) in enumerate(positions):
        end_pos = positions[idx + 1][0] if idx + 1 < len(positions) else len(source)
        block   = source[pos:end_pos].strip()

        if level in ('#', '##'):
            parent_h2 = title

        parent_ctx = parent_h2 if level not in ('#', '##') else ""
        context_line = f"> **Section Context:** {parent_ctx}\n\n" if parent_ctx else ""

        doc_text = context_line + block
        if len(doc_text.strip()) < 40:
            continue

        chunks.append({
            "chunk_id":       f"{slug}_{idx}",
            "section_title":  title.strip(),
            "heading_level":  level,
            "parent_section": parent_ctx,
            "source_url":     raw_url,
            "document_type":  "markdown",
            "document_text":  doc_text,
        })

    return chunks


# ──────────────────────────────────────────────────────────────────────────────
# 6b. PDF Handler  (requires: pip install pymupdf)
# ──────────────────────────────────────────────────────────────────────────────

def chunk_pdf(url: str, slug: str) -> list[dict]:
    """
    Download a PDF and split it into semantic parent chunks using font-size
    heuristics to detect section headings.

    Strategy:
      - Download the PDF bytes into memory (no temp file written to disk).
      - Iterate every page block. Blocks whose font size is noticeably larger
        than the median body font size are treated as HEADING boundaries — they
        start a new parent chunk.
      - Each chunk = heading line + all body text until the next heading.
      - Minimum chunk size of 60 characters; trivial fragments are discarded.

    Why PyMuPDF (fitz) over pdfplumber:
      - Lower memory footprint (no Pillow dependency).
      - Block-level font metadata available directly.
      - Works on CPU-only systems without poppler.
    """
    if not HAS_FITZ:
        print("  [ERROR] PyMuPDF not installed. Run: pip install pymupdf")
        return []

    print(f"  [PDF] Fetching {url}")
    try:
        resp = requests.get(url, timeout=60, headers=REQUEST_HDR, stream=True)
        resp.raise_for_status()
        pdf_bytes = resp.content
    except Exception as e:
        print(f"  [ERROR] Could not download PDF: {e}")
        return []

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        print(f"  [ERROR] PyMuPDF could not open PDF: {e}")
        return []

    # ── Pass 1: collect all text blocks with font sizes ────────────────────
    all_blocks: list[dict] = []  # {text, size, page}
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:   # 0 = text block
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    txt = span["text"].strip()
                    if txt:
                        all_blocks.append({
                            "text":  txt,
                            "size":  span["size"],
                            "page":  page_num + 1,
                        })

    if not all_blocks:
        print("  [WARN] No text blocks found in PDF.")
        return []

    # ── Pass 2: compute median body font size ──────────────────────────────
    sizes = sorted(b["size"] for b in all_blocks)
    median_size = sizes[len(sizes) // 2]
    # Heading threshold: any block whose font is at least 10% larger than median
    heading_threshold = median_size * 1.10

    # ── Pass 3: group blocks into chunks at heading boundaries ─────────────
    chunks: list[dict] = []
    current_title  = f"{slug} — Introduction"
    current_lines: list[str] = []
    current_page   = 1
    chunk_idx      = 0

    def flush_chunk(title: str, lines: list[str], page: int, idx: int):
        text = " ".join(lines).strip()
        text = re.sub(r'\s+', ' ', text)
        if len(text) < 60:
            return None
        return {
            "chunk_id":      f"{slug}_{idx}",
            "section_title": title,
            "source_url":    url,
            "document_type": "pdf",
            "page_start":    page,
            "document_text": (
                f"# {title}\n\n"
                f"> **Source:** `{url}` | Starting page {page}\n\n"
                + text
            ),
        }

    for block in all_blocks:
        is_heading = block["size"] >= heading_threshold

        if is_heading:
            # Flush the previous chunk
            if current_lines:
                c = flush_chunk(current_title, current_lines, current_page, chunk_idx)
                if c:
                    chunks.append(c)
                    chunk_idx += 1
            # Start a new chunk
            current_title = block["text"][:120]  # cap heading length
            current_lines = []
            current_page  = block["page"]
        else:
            current_lines.append(block["text"])

    # Flush the final chunk
    if current_lines:
        c = flush_chunk(current_title, current_lines, current_page, chunk_idx)
        if c:
            chunks.append(c)

    doc.close()
    print(f"  [PDF] {len(doc.page_count if hasattr(doc, 'page_count') else range(1))} pages → {len(chunks)} chunks  (median font: {median_size:.1f}pt, heading threshold: {heading_threshold:.1f}pt)")
    return chunks


# ──────────────────────────────────────────────────────────────────────────────
# 7. GITHUB_DIR Handler — recursively dispatch each file
# ──────────────────────────────────────────────────────────────────────────────

def github_url_to_api(url: str) -> str:
    """
    Convert a github.com/user/repo/tree/branch/path URL
    to api.github.com/repos/user/repo/contents/path?ref=branch
    """
    # Already an API url
    if "api.github.com" in url:
        return url

    # Extract parts: github.com/{user}/{repo}/tree/{branch}/{path}
    m = re.match(
        r'https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(/(.*))?',
        url
    )
    if m:
        user, repo, branch, _, path = m.groups()
        path = path or ""
        api  = f"{GITHUB_API}/{user}/{repo}/contents/{path}?ref={branch}"
        return api

    # Fallback - just point at root
    m2 = re.match(r'https?://github\.com/([^/]+)/([^/]+)', url)
    if m2:
        user, repo = m2.groups()
        return f"{GITHUB_API}/{user}/{repo}/contents"

    return url


def chunk_github_dir(url: str, slug: str, _depth: int = 0) -> list[dict]:
    """Recurse through a GitHub dir and dispatch each file to the right handler."""
    if _depth > 4:   # Safety cap
        return []

    api_url = github_url_to_api(url)
    print(f"  [GITHUB_DIR] Listing {api_url}")
    try:
        r = requests.get(api_url, timeout=20, headers=REQUEST_HDR)
        # If the user passed /master but the repo uses /main, the API 404s. Fallback!
        if r.status_code == 404 and "?ref=" in api_url:
            fallback_url = api_url.split("?")[0]
            print(f"  [WARN] 404 branch not found. Retrying default branch: {fallback_url}")
            r = requests.get(fallback_url, timeout=20, headers=REQUEST_HDR)
        r.raise_for_status()
        items = r.json()
    except Exception as e:
        print(f"  [ERROR] GitHub API: {e}")
        return []

    if not isinstance(items, list):
        print(f"  [WARN] Unexpected GitHub API response")
        return []

    chunks = []
    for item in items:
        name      = item.get("name", "")
        item_type = item.get("type", "")
        dl_url    = item.get("download_url") or item.get("html_url", "")
        html_url  = item.get("html_url", "")

        if item_type == "dir":
            sub_slug = f"{slug}_{name}"
            sub_url  = html_url  # recurse with github.com/…/tree/… URL
            chunks.extend(chunk_github_dir(sub_url, sub_slug, _depth + 1))

        elif item_type == "file":
            file_slug  = re.sub(r'[^\w\-]', '_', name.rsplit('.', 1)[0])[:40]
            full_slug  = f"{slug}_{file_slug}"
            raw_url    = item.get("download_url") or dl_url
            src_type   = detect_source_type(raw_url or name)

            if src_type == "SKIP":
                continue   # silently ignore binaries, SVGs, C files, etc.
            elif src_type == "VERILOG":
                chunks.extend(chunk_verilog(raw_url, full_slug))
            elif src_type == "ASM":
                chunks.extend(chunk_asm(raw_url, full_slug))
            elif src_type == "MARKDOWN":
                chunks.extend(chunk_markdown(raw_url, full_slug))
            elif src_type == "HTML_DOC":
                chunks.extend(chunk_html(raw_url, full_slug))
            elif src_type == "PDF":
                chunks.extend(chunk_pdf(raw_url, full_slug))

    return chunks


# ──────────────────────────────────────────────────────────────────────────────
# 8. Output Writers
# ──────────────────────────────────────────────────────────────────────────────

def write_outputs(chunks: list[dict], slug: str, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    # ── {slug}_chunks.json ────────────────────────────────────────────────────
    json_path = os.path.join(output_dir, f"{slug}_chunks.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"\n  → {json_path}  ({len(chunks)} chunks)")

    # ── {slug}_full_doc.md ────────────────────────────────────────────────────
    # Uses the same <!-- chunk_id=N | Title --> divider format as chunk_isa.py
    # so that rag_test.py's load_isa_children_from_full_doc() can parse it.
    md_path = os.path.join(output_dir, f"{slug}_full_doc.md")
    with open(md_path, "w", encoding="utf-8") as f:
        for c in chunks:
            cid   = c.get("chunk_id", "?")
            title = c.get("section_title", "Untitled")
            f.write(f"\n\n---\n<!-- chunk_id={cid} | {title} -->\n\n")
            f.write(c.get("document_text", ""))
    print(f"  → {md_path}")


def print_stats(chunks: list[dict]) -> None:
    by_type: dict[str, int] = {}
    total_tokens = 0
    for c in chunks:
        dt = c.get("document_type", "unknown")
        by_type[dt] = by_type.get(dt, 0) + 1
        total_tokens += rough_token_count(c.get("document_text", ""))

    print(f"\n  Total chunks      : {len(chunks)}")
    print(f"  Est. total tokens : {total_tokens:,}")
    print(f"\n  By document type:")
    for t, cnt in sorted(by_type.items()):
        print(f"    {t:<25}: {cnt}")


# ──────────────────────────────────────────────────────────────────────────────
# 9. Main Entry Point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Universal chunker — produces {slug}_chunks.json + {slug}_full_doc.md from any URL."
    )
    parser.add_argument("url",    help="URL to process (HTML doc, Verilog file, GitHub dir, etc.)")
    parser.add_argument("--output",  default=DEFAULT_OUTPUT,  help="Output directory (default: 'scraped data')")
    parser.add_argument("--slug",    default=None,            help="Override the output filename slug")
    args = parser.parse_args()

    url  = args.url
    slug = args.slug or url_to_slug(url)

    print(f"\n[chunk.py] URL   : {url}")
    print(f"           Slug  : {slug}")
    print(f"           Output: {args.output}")

    # ── Detect and dispatch ───────────────────────────────────────────────────
    src_type = detect_source_type(url)
    print(f"\n[1/3] Detected source type: {src_type}")

    dispatch = {
        "HTML_DOC":   chunk_html,
        "VERILOG":    chunk_verilog,
        "ASM":        chunk_asm,
        "MARKDOWN":   chunk_markdown,
        "GITHUB_DIR": chunk_github_dir,
        "PDF":        chunk_pdf,
    }
    handler = dispatch.get(src_type, chunk_html)

    print(f"\n[2/3] Chunking...")
    chunks = handler(url, slug)

    if not chunks:
        print("\n  [WARN] No chunks produced. Check URL or network access.")
        sys.exit(1)

    # ── Write outputs ─────────────────────────────────────────────────────────
    print(f"\n[3/3] Saving artifacts...")
    write_outputs(chunks, slug, args.output)
    print_stats(chunks)
    print(f"\n✅ Done. Plug '{slug}_chunks.json' into rag_test.py to start retrieving.")


if __name__ == "__main__":
    main()
