# Research Worker — FastAPI + vendored research-pipeline
# Needs Node for the DOCX exporter (export-docx.mjs).

FROM python:3.11-slim

# Node 20 for DOCX export
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI (used by claude-agent-sdk)
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

# Install Python deps for the worker
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Python deps for the MCP server (bundled with the pipeline)
COPY pipeline/mcp-server/requirements.txt pipeline/mcp-server/requirements.txt
RUN pip install --no-cache-dir -r pipeline/mcp-server/requirements.txt

# Install Node deps for the DOCX exporter
COPY pipeline/package.json pipeline/package.json
RUN cd pipeline && npm install --omit=dev

# Copy the rest
COPY . .

ENV PYTHONUNBUFFERED=1 \
    WORKER_OUTPUT_DIR=/data/output

RUN mkdir -p /data/output

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
