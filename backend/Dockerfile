# Образ сервера API для PaaS (Render/Railway). Сборка: docker build -t vocabdeck-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app

# Без root: процесс не сможет изменить файлы образа
RUN useradd --create-home api
USER api

EXPOSE 8000
# Миграции применяются при старте контейнера, затем запускается ASGI-сервер
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
