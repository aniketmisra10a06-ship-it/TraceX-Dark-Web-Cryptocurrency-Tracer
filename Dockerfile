FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TRACEX_CACHE_DIR=/tmp/tracex-cache
RUN useradd --create-home --uid 10001 tracex
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
USER 10001
ENTRYPOINT ["tracex"]
CMD ["--help"]
