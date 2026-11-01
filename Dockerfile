FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.lock ./
RUN python -m pip install --no-cache-dir -r requirements.lock \
    && useradd --create-home --uid 10001 bot

COPY bot.py ./
COPY minerbot/ ./minerbot/
COPY asset/ ./asset/

RUN mkdir -p /app/data && chown bot:bot /app/data && chmod 700 /app/data

USER bot
CMD ["python", "bot.py"]
