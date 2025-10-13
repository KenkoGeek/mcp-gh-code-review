FROM python:3.14-slim AS base
ENV PYTHONUNBUFFERED=1
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

FROM base AS runtime
USER app
CMD ["python", "-m", "mcp_server.cli", "--stdio"]
