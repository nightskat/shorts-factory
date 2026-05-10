FROM python:3.11-slim

# ffmpeg for video rendering
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .
COPY shorts/ shorts/

RUN pip install --no-cache-dir ".[web,cli]"

EXPOSE 8765
CMD ["shorts-factory", "serve"]
