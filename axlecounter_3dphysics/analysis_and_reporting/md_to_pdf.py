"""Render a Markdown document (with LaTeX display math) to a PDF.

Used to build the project's PDF deliverables from their Markdown sources, so
the .md and the .pdf can never drift apart -- the PDF is always regenerated
from the same text.

There is no LaTeX engine on this machine, so display equations written as

    $$ ... $$

are rendered by matplotlib's mathtext engine into small transparent PNGs and
embedded as images. Everything else is laid out with ReportLab's platypus.

Supported Markdown subset (deliberately small and predictable):
    # / ## / ###      headings
    paragraphs        with **bold**, *italic*, `code`
    - / * bullets     and 1. numbered lists
    | tables |        with a --- separator row
    ```fenced```      code blocks
    > blockquotes
    ---               horizontal rule
    $$display math$$  on its own line(s)

INLINE math is NOT rendered as an image -- write inline symbols directly as
Unicode in the source (mu, Phi, omega and friends). This keeps line-breaking
and text flow correct, which inline images would break.

Usage:
    py -3 md_to_pdf.py input.md output.pdf ["Document Title"]
"""
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, Image,
                                ListFlowable, ListItem, PageBreak, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table,
                                TableStyle)

# --- palette ---------------------------------------------------------------
INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#5b6570")
ACCENT = colors.HexColor("#1f5fa8")
RULE = colors.HexColor("#c8d0d8")
BOXBG = colors.HexColor("#eef3f8")
CODEBG = colors.HexColor("#f4f6f8")

# --- fonts ------------------------------------------------------------------
# ReportLab's built-in Helvetica only covers Latin-1, so characters like the
# much-greater-than sign render as a black box. matplotlib ships DejaVu Sans,
# which has full coverage, so register it and use it when available.
BODY_FONT, BOLD_FONT, ITAL_FONT = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    _fdir = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    _faces = {"DejaVu": "DejaVuSans.ttf", "DejaVu-Bold": "DejaVuSans-Bold.ttf",
              "DejaVu-Obl": "DejaVuSans-Oblique.ttf"}
    if all(os.path.exists(os.path.join(_fdir, v)) for v in _faces.values()):
        for name, fn in _faces.items():
            pdfmetrics.registerFont(TTFont(name, os.path.join(_fdir, fn)))
        pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                                      italic="DejaVu-Obl", boldItalic="DejaVu-Bold")
        BODY_FONT, BOLD_FONT, ITAL_FONT = "DejaVu", "DejaVu-Bold", "DejaVu-Obl"
except Exception:
    pass   # fall back to Helvetica; only exotic glyphs are affected

_ss = getSampleStyleSheet()
S = {
    "h1": ParagraphStyle("h1", parent=_ss["Heading1"], fontName=BOLD_FONT,
                         fontSize=18, leading=23, spaceBefore=16, spaceAfter=9,
                         textColor=ACCENT),
    "h2": ParagraphStyle("h2", parent=_ss["Heading2"], fontName=BOLD_FONT,
                         fontSize=13.5, leading=17, spaceBefore=13, spaceAfter=6,
                         textColor=INK),
    "h3": ParagraphStyle("h3", parent=_ss["Heading3"], fontName=BOLD_FONT,
                         fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=4,
                         textColor=INK),
    "body": ParagraphStyle("body", parent=_ss["BodyText"], fontName=BODY_FONT,
                           fontSize=9.6, leading=14, spaceAfter=6,
                           alignment=TA_LEFT, textColor=INK),
    "quote": ParagraphStyle("quote", parent=_ss["BodyText"], fontName=BODY_FONT,
                            fontSize=9.3, leading=13.5, leftIndent=9,
                            spaceBefore=3, spaceAfter=3, textColor=INK),
    "cell": ParagraphStyle("cell", parent=_ss["BodyText"], fontName=BODY_FONT,
                           fontSize=8.3, leading=11, spaceAfter=0, textColor=INK),
    "cellh": ParagraphStyle("cellh", parent=_ss["BodyText"], fontName=BOLD_FONT,
                            fontSize=8.3, leading=11, spaceAfter=0, textColor=colors.white),
    "foot": ParagraphStyle("foot", parent=_ss["BodyText"], fontName=BODY_FONT,
                           fontSize=7.6, leading=9.5, textColor=MUTED),
}

_EQ_CACHE = {}
_EQ_DIR = None


def _render_math(tex, fontsize=13):
    """Render a LaTeX display equation to a transparent PNG via mathtext.

    Returns (path, width_px, height_px), or None if the expression cannot be
    parsed (a malformed equation must not abort the whole document).
    """
    key = (tex, fontsize)
    if key in _EQ_CACHE:
        return _EQ_CACHE[key]
    # mathtext understands a useful subset of LaTeX but not full environments;
    # strip the delimiters and a few constructs it cannot parse.
    body = tex.strip()
    body = re.sub(r"\\(?:label|tag)\{[^}]*\}", "", body)
    body = body.replace(r"\begin{aligned}", "").replace(r"\end{aligned}", "")
    body = body.replace(r"\displaystyle", "").replace("&", "")
    body = body.replace(r"\\", " ")           # no multi-line in one image
    body = body.replace(r"\text{", r"\mathrm{").replace(r"\textbf{", r"\mathbf{")
    body = body.replace(r"\boxed{", r"\mathbf{")
    body = re.sub(r"\s+", " ", body).strip()
    if not body:
        return None
    fig = plt.figure(figsize=(0.01, 0.01))
    try:
        t = fig.text(0, 0, f"${body}$", fontsize=fontsize, color="#1a1a1a")
        fig.canvas.draw()
        bb = t.get_window_extent(fig.canvas.get_renderer())
        w_in = max(bb.width / fig.dpi, 0.05)
        h_in = max(bb.height / fig.dpi, 0.05)
        fig.set_size_inches(w_in + 0.10, h_in + 0.10)
        t.set_position((0.05 / (w_in + 0.10), 0.05 / (h_in + 0.10)))
        path = os.path.join(_EQ_DIR, f"eq_{abs(hash(key)) % (10 ** 12)}.png")
        fig.savefig(path, dpi=260, transparent=True,
                    bbox_inches="tight", pad_inches=0.02)
        from PIL import Image as PILImage
        with PILImage.open(path) as im:
            px = im.size
        _EQ_CACHE[key] = (path, px[0], px[1])
        return _EQ_CACHE[key]
    except Exception as exc:
        print(f"   [math skipped] {body[:60]}... ({exc})")
        return None
    finally:
        plt.close(fig)


def _inline(text):
    """Convert inline Markdown emphasis to ReportLab inline markup."""
    text = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    text = re.sub(r"`([^`]+)`",
                  r'<font face="Courier" size="8.6" color="#8a3ffc">\1</font>', text)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"<i>\1</i>", text)
    # strip any leftover single-$ inline math delimiters
    text = re.sub(r"\$([^$]+)\$", r"<i>\1</i>", text)
    return text


def _eq_flowable(tex, avail_w):
    """Build a centred Image flowable for one display equation."""
    r = _render_math(tex)
    if not r:
        return Paragraph(_inline(f"`{tex.strip()[:90]}`"), S["body"])
    path, pw, ph = r
    scale = 0.62                      # px -> pt at 260 dpi, tuned for 9.6pt body
    w, h = pw * scale * 72 / 260, ph * scale * 72 / 260
    if w > avail_w:                   # shrink oversized equations to fit
        h *= avail_w / w
        w = avail_w
    img = Image(path, width=w, height=h)
    img.hAlign = "CENTER"
    return img


def _table(rows, avail_w):
    """Build a styled Table from parsed Markdown rows (first row = header)."""
    head, body = rows[0], rows[1:]
    ncol = max(len(r) for r in rows)
    data = []
    for i, r in enumerate(rows):
        r = list(r) + [""] * (ncol - len(r))
        style = S["cellh"] if i == 0 else S["cell"]
        data.append([Paragraph(_inline(c), style) for c in r])
    t = Table(data, colWidths=[avail_w / ncol] * ncol, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t


def parse_markdown(md, avail_w):
    """Turn a Markdown string into a list of ReportLab flowables."""
    out = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if not s:
            i += 1
            continue

        # explicit page break marker
        if s == "<!--pagebreak-->":
            out.append(PageBreak()); i += 1; continue

        # fenced code block
        if s.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            if buf:
                pre = Preformatted("\n".join(buf),
                                   ParagraphStyle("code", fontName="Courier",
                                                  fontSize=8.2, leading=10.5,
                                                  textColor=INK, backColor=CODEBG,
                                                  borderPadding=5, leftIndent=2))
                out.append(Spacer(1, 3)); out.append(pre); out.append(Spacer(1, 5))
            continue

        # display math (may span multiple lines until closing $$)
        if s.startswith("$$"):
            body = s[2:]
            if body.strip().endswith("$$"):
                body = body.strip()[:-2]
            else:
                i += 1
                while i < len(lines) and "$$" not in lines[i]:
                    body += "\n" + lines[i]; i += 1
                if i < len(lines):
                    body += "\n" + lines[i].split("$$")[0]
            i += 1
            out.append(Spacer(1, 5))
            out.append(_eq_flowable(body, avail_w))
            out.append(Spacer(1, 6))
            continue

        # image on its own line:  ![caption](path)
        m = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", s)
        if m:
            i += 1
            cap, src_path = m.group(1), m.group(2)
            if os.path.exists(src_path):
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(src_path) as im:
                        iw, ih = im.size
                    w = min(avail_w, avail_w * 0.86)
                    h = w * ih / iw
                    max_h = 175 * mm            # keep one image to a page
                    if h > max_h:
                        w *= max_h / h; h = max_h
                    img = Image(src_path, width=w, height=h)
                    img.hAlign = "CENTER"
                    out.append(Spacer(1, 5)); out.append(img)
                    if cap:
                        out.append(Spacer(1, 2))
                        out.append(Paragraph(_inline(cap),
                                             ParagraphStyle("cap", parent=S["body"],
                                                            fontSize=8.2, leading=11,
                                                            textColor=MUTED,
                                                            alignment=1, spaceAfter=8)))
                    else:
                        out.append(Spacer(1, 8))
                except Exception as exc:
                    print(f"   [image skipped] {src_path} ({exc})")
            else:
                print(f"   [image missing] {src_path}")
            continue

        # horizontal rule
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", s):
            out.append(Spacer(1, 5))
            out.append(HRFlowable(width="100%", thickness=0.6, color=RULE))
            out.append(Spacer(1, 5)); i += 1; continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            key = "h1" if lvl == 1 else ("h2" if lvl == 2 else "h3")
            out.append(Paragraph(_inline(m.group(2)), S[key]))
            if lvl == 1:
                out.append(HRFlowable(width="100%", thickness=1.1, color=ACCENT,
                                      spaceBefore=1, spaceAfter=6))
            i += 1; continue

        # table
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                raw = lines[i].strip().strip("|")
                if not re.match(r"^[\s:|-]+$", raw):
                    rows.append([c.strip() for c in raw.split("|")])
                i += 1
            out.append(Spacer(1, 4)); out.append(_table(rows, avail_w))
            out.append(Spacer(1, 7)); continue

        # blockquote (callout box)
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip()); i += 1
            para = Paragraph(_inline(" ".join(b for b in buf if b)), S["quote"])
            box = Table([[para]], colWidths=[avail_w], hAlign="LEFT")
            box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), BOXBG),
                ("LINEBEFORE", (0, 0), (0, -1), 2.4, ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            out.append(Spacer(1, 4)); out.append(box); out.append(Spacer(1, 6))
            continue

        # Lists. The bullet/number is rendered as an explicit prefix inside the
        # paragraph rather than via ListFlowable: ReportLab's auto-numbering
        # feeds an int into the text engine and raises inside stringWidth.
        if re.match(r"^([-*+]|\d+\.)\s+", s):
            numbered = not re.match(r"^[-*+]\s+", s)
            n = 0
            while i < len(lines) and re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i]):
                txt = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", lines[i])
                i += 1
                # absorb indented continuation lines
                while (i < len(lines) and lines[i].strip()
                       and not re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i])
                       and lines[i].startswith(("  ", "\t"))
                       and not lines[i].strip().startswith("$$")):
                    txt += " " + lines[i].strip(); i += 1
                n += 1
                mark = f"{n}." if numbered else "&bull;"
                out.append(Paragraph(f"{mark}&nbsp;&nbsp;{_inline(txt)}",
                                     ParagraphStyle(f"li{n}", parent=S["body"],
                                                    leftIndent=13, firstLineIndent=-13,
                                                    spaceAfter=2.5)))
            out.append(Spacer(1, 4)); continue

        # plain paragraph: gather until a blank line or a block-level marker
        buf = [s]; i += 1
        while (i < len(lines) and lines[i].strip()
               and not re.match(r"^(#{1,6}\s|\||>|```|\$\$|[-*+]\s|\d+\.\s|-{3,}$)",
                                lines[i].strip())):
            buf.append(lines[i].strip()); i += 1
        out.append(Paragraph(_inline(" ".join(buf)), S["body"]))
    return out


def build_pdf(md_path, pdf_path, title=None, subtitle=None, footer=None):
    """Render `md_path` to `pdf_path`. Returns the page count."""
    global _EQ_DIR
    _EQ_DIR = os.path.join(os.path.dirname(os.path.abspath(pdf_path)), "_eq_tmp")
    os.makedirs(_EQ_DIR, exist_ok=True)

    with open(md_path, encoding="utf-8") as f:
        md = f.read()

    page_w, page_h = A4
    lm = rm = 17 * mm
    tm, bm = 17 * mm, 16 * mm
    avail_w = page_w - lm - rm

    doc = BaseDocTemplate(pdf_path, pagesize=A4,
                          leftMargin=lm, rightMargin=rm,
                          topMargin=tm, bottomMargin=bm,
                          title=title or os.path.basename(md_path),
                          author=footer or "")
    frame = Frame(lm, bm, avail_w, page_h - tm - bm, id="body",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def decorate(canvas, d):
        canvas.saveState()
        canvas.setFont(BODY_FONT, 7.4)
        canvas.setFillColor(MUTED)
        if footer:
            canvas.drawString(lm, bm - 9.5, footer)
        canvas.drawRightString(page_w - rm, bm - 9.5, f"Page {canvas.getPageNumber()}")
        canvas.setStrokeColor(RULE); canvas.setLineWidth(0.4)
        canvas.line(lm, bm - 5, page_w - rm, bm - 5)
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=decorate)])

    story = []
    if title:
        story.append(Spacer(1, 8))
        story.append(Paragraph(_inline(title),
                               ParagraphStyle("title", fontName=BOLD_FONT,
                                              fontSize=21, leading=26,
                                              textColor=ACCENT, spaceAfter=4)))
        if subtitle:
            story.append(Paragraph(_inline(subtitle),
                                   ParagraphStyle("sub", fontName=BODY_FONT,
                                                  fontSize=10, leading=14,
                                                  textColor=MUTED, spaceAfter=8)))
        story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT))
        story.append(Spacer(1, 9))

    story += parse_markdown(md, avail_w)
    doc.build(story)

    # tidy the rendered-equation scratch images
    try:
        for f in os.listdir(_EQ_DIR):
            os.remove(os.path.join(_EQ_DIR, f))
        os.rmdir(_EQ_DIR)
    except OSError:
        pass

    from pypdf import PdfReader
    return len(PdfReader(pdf_path).pages)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    _title = sys.argv[3] if len(sys.argv) > 3 else None
    _sub = sys.argv[4] if len(sys.argv) > 4 else None
    _foot = sys.argv[5] if len(sys.argv) > 5 else None
    n = build_pdf(sys.argv[1], sys.argv[2], _title, _sub, _foot)
    print(f"Wrote {sys.argv[2]} ({n} pages)")
