FROM python:3.12-slim

WORKDIR /app

# Системные зависимости (минимум)
RUN pip install --no-cache-dir --upgrade pip

# Устанавливаем зависимости
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .

# Копируем код
COPY app /app/app

# Flask
ENV FLASK_APP=app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Gunicorn для нормального запуска
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:create_app()"]
