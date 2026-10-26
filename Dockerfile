FROM python:3.14-slim

# WeasyPrint renders PDFs with Pango; the fonts stand in for Georgia/Times.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
        fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Everything that changes (database, photos, scans, uploaded PDFs) lives in
# /data, which the NAS mounts from a shared folder.
ENV RECIPES_DATA_DIR=/data \
    RECIPES_PDF_DIR=/data/pdf \
    RECIPES_HOST=0.0.0.0 \
    RECIPES_PORT=8000 \
    PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 8000

CMD ["python", "run.py"]
