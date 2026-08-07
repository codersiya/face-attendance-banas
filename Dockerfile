# ---------- Stage 1: Frontend build ----------
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

# Frontend calls the backend via a relative /api path (see nginx.conf proxy
# below), so no absolute backend URL needs to be baked in at build time.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build


# ---------- Stage 2: Backend dependency build ----------
FROM python:3.11-slim-bookworm AS backend-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY backend/requirements.txt .
# Completely remove dlib from pip requirements. We will install it via apt-get in the runtime stage.
RUN sed -i '/dlib/d' requirements.txt

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
# Install face_recognition without dependencies so it doesn't try to compile dlib!
RUN pip install --no-cache-dir --prefix=/install --no-deps face_recognition==1.3.0


# ---------- Stage 3: Final runtime image ----------
FROM python:3.11-slim-bookworm AS runtime

# Install python3-dlib via apt to get the PRECOMPILED dlib! No compilation needed.
# This prevents the Out of Memory error on Render completely.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dlib \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Backend ---
COPY --from=backend-builder /install /usr/local
COPY backend/ /app/backend

# --- Frontend (built static files served by nginx) ---
COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html

# --- nginx: serves frontend, proxies /api/* to uvicorn on localhost:8000 ---
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

# --- supervisord: runs both nginx and uvicorn as child processes ---
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 80 = frontend (and API proxy)
EXPOSE 80

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]