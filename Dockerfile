FROM python:3.12-slim

WORKDIR /srv
# DejaVu gives the PDF export Unicode glyphs (curly quotes, arrows, non-Latin text)
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --no-cache-dir uv && uv pip install --system --no-cache -r pyproject.toml

COPY app app
COPY seed seed

# Render and similar hosts pass PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
