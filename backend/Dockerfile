FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código backend
COPY main.py .

# Copiar frontend
COPY ../frontend ./frontend

# Exponer puerto
EXPOSE 8000

# Variables de entorno (se pueden override con docker run -e)
ENV SHOPPING_FILE_PATH=/data/SHOPPING.md
ENV ALLOWED_USER_ID=

# Crear directorio para datos
RUN mkdir -p /data

# Comando
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
