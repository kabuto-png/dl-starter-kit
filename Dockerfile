FROM python:3.13-slim
WORKDIR /app

# Layer caching: install deps before app code (rebuild on requirements.txt change only)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application (selective — not COPY . .)
COPY akc/ ./akc/
COPY main.py .

# Non-root user security (DEPLOY-01)
RUN useradd -r -u 1001 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app
USER appuser

# Python runtime optimization
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Volume for pattern persistence (DEPLOY-02)
VOLUME ["/app/data"]

EXPOSE 8080

# ASGI entry point (uvicorn, not python main.py)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
