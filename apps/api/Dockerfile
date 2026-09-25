FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock pyproject.toml ./
RUN sed '/^-e /d' requirements.lock > /tmp/deps.txt && pip install --no-cache-dir -r /tmp/deps.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"]
