FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# GeoPandas, Shapely, PyProj and pyogrio ship manylinux wheels that bundle GDAL/PROJ/GEOS.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home appuser && mkdir -p /app/storage/uploads && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
