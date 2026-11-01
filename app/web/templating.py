from pathlib import Path
from urllib.parse import urlparse

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def favicon(url: str) -> str:
    host = urlparse(url if "//" in url else f"https://{url}").netloc
    return f"https://www.google.com/s2/favicons?domain={host}&sz=32"


templates.env.filters["favicon"] = favicon
templates.env.filters["host"] = lambda url: urlparse(url).netloc.removeprefix("www.")
