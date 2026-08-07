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
FROM python:3.11-slim AS backend-builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Create a robust cmake wrapper to forcefully override any parallel build (-j) flags 
# that dlib's setup.py tries to use. This guarantees it will only use 1 core and 
# avoid the 8GB+ OOM errors on Render.
RUN cat << 'EOF' > /usr/local/bin/cmake
#!/bin/bash
is_build=0
new_args=()
for arg in "$@"; do
    if [[ $arg == "--build" ]]; then
        is_build=1
    fi
    if [[ $arg == -j* ]]; then
        continue
    fi
    new_args+=("$arg")
done
if [[ $is_build -eq 1 ]]; then
    new_args+=("-j1")
fi
exec /usr/bin/cmake "${new_args[@]}"
EOF
RUN chmod +x /usr/local/bin/cmake

COPY backend/requirements.txt .
# Remove Windows-specific dlib-binary and replace with standard dlib
RUN sed -i 's/dlib-binary==19.24.1/dlib==19.24.1/' requirements.txt

# We must install setuptools and wheel first when using --no-build-isolation
# Do NOT install cmake via pip as it would overwrite our wrapper
RUN pip install --no-cache-dir setuptools wheel
# Install dlib explicitly with --no-build-isolation. This prevents pip from downloading
# a fresh copy of cmake, forcing it to use our wrapper in /usr/local/bin/cmake
RUN pip install --no-cache-dir --prefix=/install --no-build-isolation dlib==19.24.1

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
RUN pip install --no-cache-dir --prefix=/install --no-deps face_recognition==1.3.0

# ---------- Stage 3: Final runtime image ----------
FROM python:3.11-slim AS runtime

# Runtime libs for compiled dlib + nginx + supervisord
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    liblapack3 \
    libx11-6 \
    libgtk-3-0 \
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