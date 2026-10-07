FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /app

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y gcc g++ \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY kundli.py compatibility.py .
COPY jyotish_api ./jyotish_api
COPY mcp_servers ./mcp_servers

EXPOSE 8741 8742 8743 8744 8745
CMD ["python", "-m", "jyotish_api.serve_all"]
