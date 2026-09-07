FROM python:3.10-slim

WORKDIR /app

COPY . /app
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -e '.[dev]'

EXPOSE 8000 8765

CMD ["openclaw-mesh", "gateway", "--host", "0.0.0.0", "--port", "8000"]
