# syntax=docker/dockerfile:1

# ---- Stage 1: build dependencies into a self-contained venv ----
FROM python:3.10-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---- Stage 2: runtime ----
FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# Bring in the prebuilt venv (all deps + the streamlit console script)
COPY --from=builder /opt/venv /opt/venv

# App code (respecting .dockerignore)
COPY . .

# Run as a non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
ENV HOME=/home/appuser

EXPOSE 8501

# slim has no curl — probe the health endpoint with the stdlib instead.
# Honor $PORT (set by hosts like Render); fall back to 8501 locally.
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD python -c "import os,urllib.request,sys; p=os.getenv('PORT','8501'); sys.exit(0 if urllib.request.urlopen('http://localhost:%s/_stcore/health' % p).status==200 else 1)"

# Bind to $PORT when the platform provides one (Render, etc.), else 8501.
# Shell form so ${PORT} expands; `exec` makes streamlit PID 1 for clean signals.
ENTRYPOINT ["sh", "-c", "exec streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true"]
