FROM python:3.12-slim

WORKDIR /srv

# Install dependencies first so the layer is cached across code changes.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# The app and the committed January 2026 snapshot (DATA_DIR defaults to ../data relative to the app).
COPY backend/app ./backend/app
COPY data ./data

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
