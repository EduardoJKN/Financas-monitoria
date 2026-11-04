FROM python:3.11-slim

WORKDIR /app

# A camada de negócio reaproveitada vive em finance_app/ — ver
# app/core/financas_path.py. O build precisa copiar as duas pastas.
COPY backend/requirements.txt ./backend/requirements.txt
COPY finance_app/requirements.txt ./finance_app/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY finance_app ./finance_app
COPY backend ./backend

WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
