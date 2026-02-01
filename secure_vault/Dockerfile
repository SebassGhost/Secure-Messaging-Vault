FROM python:3.11-slim

# Evitar buffers raros
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

# Puerto FastAPI
EXPOSE 8000

CMD ["uvicorn", "server.api:app", "--host", "0.0.0.0", "--port", "8000"]
