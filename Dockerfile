# ===== BUILDER STAGE — compile the Vite/Tailwind frontend to static assets =====
FROM node:20-slim AS builder

WORKDIR /app/frontend

# Install deps first (cached unless package files change), then build.
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build   # → /app/frontend/dist

# ===== RUNTIME STAGE — python API + nginx (static + proxy), run by supervisor =====
FROM python:3.12-slim

ARG DEV_MODE=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx supervisor curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (cached unless requirements change).
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Application code.
COPY backend/ ./backend/

# Built frontend → nginx web root.
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

# nginx + supervisor config (dev supervisor uses uvicorn --reload).
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisor/supervisord.conf /tmp/supervisord.prod.conf
COPY supervisor/supervisord.dev.conf /tmp/supervisord.dev.conf
RUN if [ "$DEV_MODE" = "true" ]; then \
        cp /tmp/supervisord.dev.conf /etc/supervisor/conf.d/supervisord.conf; \
    else \
        cp /tmp/supervisord.prod.conf /etc/supervisor/conf.d/supervisord.conf; \
    fi

ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
