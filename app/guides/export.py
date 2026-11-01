"""Real PDF and DOCX files without a sandbox: one outline of the guide, two small renderers."""

import io
from pathlib import Path

from docx import Document
from fpdf import FPDF

from app.guides.schemas import Guide

FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")  # installed in the Docker image for Unicode


def outline(g: Guide, url: str) -> list[tuple]:
    """(kind, payload) blocks: h1/h2/h3, p, bullets, table."""
    cite = lambda ids: f" [{', '.join(ids)}]" if ids else ""
    blocks = [("h1", f"{g.app}: OAuth app setup & approval guide"),
              ("p", f"Difficulty: {g.difficulty} · Hands-on: {g.hands_on_time} · Approval wait: {g.approval_wait} · "
                    f"Production: {g.time_to_production}"),
              ("p", g.headline), ("p", g.summary), ("h2", "The path")]
    for i, s in enumerate(g.stages, 1):
        blocks += [("h3", f"{i}. {s.name} ({s.duration}){' · blocking' if s.blocking else ''}"),
                   ("bullets", [f"[{st.owner}] {st.title}: {st.detail}{cite(st.source_ids)}" for st in s.steps])]
    blocks += [("h2", "What an agent can do"), ("bullets", g.agent_can),
               ("h2", "Where you take over"), ("bullets", g.you_must)]
    if g.permissions:
        blocks += [("h2", "Permissions your agent needs"),
                   ("table", [["Action", "Scopes", "Review impact"]] +
                    [[p.action, f"{', '.join(p.scopes)} ({p.status})", p.review_impact] for p in g.permissions])]
    for title, claims in (("Requirements", g.requirements), ("Gotchas", g.gotchas), ("Evidence", g.key_claims)):
        blocks += [("h2", title), ("bullets", [f"({c.status}) {c.text}{cite(c.source_ids)}" for c in claims])]
    if g.assumptions:
        blocks += [("h2", "Assumptions and estimates"), ("bullets", g.assumptions)]
    blocks += [("h2", "If you get stuck"), ("bullets", [f"{b.issue} — {b.how_to_proceed}" for b in g.blockers])]
    if g.probes:
        blocks += [("h2", "Live probes"), ("bullets", [f"{p.request} → {p.result}" for p in g.probes])]
    blocks += [("h2", "Sources"), ("bullets", [f"[{s.id}] {s.title} — {s.url}" for s in g.sources]),
               ("p", f"Generated {g.generated_at[:10]} · {url}")]
    return blocks


def to_docx(g: Guide, url: str) -> bytes:
    doc = Document()
    for kind, data in outline(g, url):
        if kind in ("h1", "h2", "h3"):
            doc.add_heading(data, level=int(kind[1]))
        elif kind == "p":
            doc.add_paragraph(data)
        elif kind == "bullets":
            for item in data:
                doc.add_paragraph(item, style="List Bullet")
        else:
            table = doc.add_table(rows=0, cols=len(data[0]), style="Table Grid")
            for row in data:
                for cell, text in zip(table.add_row().cells, row):
                    cell.text = text
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def to_pdf(g: Guide, url: str) -> bytes:
    pdf = FPDF()
    pdf.set_margins(18, 18)
    pdf.add_page()
    family = "DejaVu" if FONT.exists() else "Helvetica"
    if FONT.exists():
        pdf.add_font("DejaVu", fname=str(FONT))
        pdf.add_font("DejaVu", style="B", fname=str(FONT.with_name("DejaVuSans-Bold.ttf")))  # table headings are bold
    sizes = {"h1": 17, "h2": 13.5, "h3": 11.5}
    write = lambda text, size, gap=1: (pdf.set_font(family, size=size), pdf.multi_cell(0, size * 0.55, text), pdf.ln(gap))
    for kind, data in outline(g, url):
        if kind in sizes:
            pdf.ln(2)
            write(data, sizes[kind], 1)
        elif kind == "p":
            write(data, 10, 2)
        elif kind == "bullets":
            for item in data:
                write(f"•  {item}", 10)
        else:
            pdf.set_font(family, size=9)
            with pdf.table(col_widths=(30, 30, 40)) as table:
                for row in data:
                    table.row(row)
            pdf.ln(2)
    return bytes(pdf.output())
