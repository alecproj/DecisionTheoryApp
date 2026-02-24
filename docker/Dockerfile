FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .

COPY app /app/app

COPY frontend/src /app/frontend
COPY frontend/mocks /app/frontend/mocks

ENV FLASK_APP=app
ENV PYTHONUNBUFFERED=1

ENV FRONTEND_MODE=real
ENV API_BASE=""

EXPOSE 8000

CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:create_app()"]
