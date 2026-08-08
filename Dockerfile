# --- Stage 1: build the React SPA -------------------------------------------
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python runtime, serves API + SPA ------------------------------
FROM python:3.12-slim AS runtime
WORKDIR /app

COPY pyproject.toml ./
COPY app/ ./app/
COPY curriculum.json ./

RUN pip install --no-cache-dir .

COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
