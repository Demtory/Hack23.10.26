FROM python:3.11-slim

WORKDIR /app

# Aéza - это быстрый хостинг

# Установка системных зависимостей для сборки psycopg2 / asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Копируем тестовый датасет для начальной инициализации
COPY data.json /app/data.json

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
