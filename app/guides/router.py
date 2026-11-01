from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app.guides import service
from app.guides.export import to_docx, to_pdf
from app.web.templating import templates

router = APIRouter(tags=["guides"])
CSS = (Path(__file__).parents[1] / "web" / "static" / "style.css").read_text()
EXPORTS = {"md": "text/markdown", "html": "text/html", "json": "application/json", "pdf": "application/pdf",
           "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


@router.get("/api/guides")
async def list_guides(q: str = ""):
    rows = await service.list_guides(q)
    return [{"slug": r.slug, "name": r.name, "difficulty": r.difficulty, "website": r.data["website"],
             "headline": r.data["headline"], "approval_wait": r.data["approval_wait"]} for r in rows]


@router.get("/api/guides/{slug}")
async def get_guide(slug: str):
    if not (guide := await service.get(slug)):
        raise HTTPException(404, "Guide not found")
    return guide


@router.get("/g/{slug}.{fmt}")
async def export_guide(slug: str, fmt: str, request: Request):
    """Download a guide as PDF, Word (.docx), Markdown, standalone HTML or JSON."""
    if fmt not in EXPORTS or not (guide := await service.get(slug)):
        raise HTTPException(404, "Not found")
    name = f'attachment; filename="{slug}-oauth-guide.{fmt}"'
    if fmt == "json":
        return JSONResponse(guide.model_dump(), headers={"Content-Disposition": name})
    url = str(request.url_for("guide_page", slug=slug))
    if fmt in ("pdf", "docx"):
        body = to_pdf(guide, url) if fmt == "pdf" else to_docx(guide, url)
        return Response(body, media_type=EXPORTS[fmt], headers={"Content-Disposition": name})
    tpl = "guide.md" if fmt == "md" else "export.html"
    body = templates.get_template(tpl).render(g=guide, url=url, css=CSS, request=request)
    return Response(body, media_type=EXPORTS[fmt], headers={"Content-Disposition": name})
