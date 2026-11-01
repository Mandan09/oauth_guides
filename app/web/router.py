from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.guides import service
from app.web.templating import templates

router = APIRouter(include_in_schema=False)


@router.get("/")
async def chat(request: Request):
    rows = await service.list_guides()
    return templates.TemplateResponse(request, "chat.html", {"rows": rows})


@router.get("/g/{slug}", name="guide_page")
async def guide_page(request: Request, slug: str):
    if not (guide := await service.get(slug)):
        raise HTTPException(404, "Guide not found")
    return templates.TemplateResponse(request, "guide.html", {"g": guide})


@router.get("/g/{slug}/fragment")
async def guide_fragment(request: Request, slug: str):
    if not (guide := await service.get(slug)):
        raise HTTPException(404, "Guide not found")
    return templates.TemplateResponse(request, "_guide.html", {"g": guide})


@router.get("/runs/{run_id}")
async def run_page(run_id: str):
    return RedirectResponse(f"/?run={run_id}")
