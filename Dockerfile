FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY echobite ./echobite
RUN useradd --create-home --uid 10001 bot && mkdir /app/data && chown bot:bot /app/data
USER bot
CMD ["python", "-m", "echobite"]
