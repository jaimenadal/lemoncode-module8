FROM python:3.12-slim

# La app es un paquete Python (app_map) con imports relativos y
# StaticFiles(directory="statics") relativo al CWD. Por eso:
#   - el código vive en /code/app_map
#   - el WORKDIR es /code/app_map (para que "statics" resuelva)
#   - PYTHONPATH=/code (para que "app_map.main:app" sea importable)
WORKDIR /code/app_map

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/code

EXPOSE 8000

# Comando de la doc oficial de client_python (FastAPI + Gunicorn)
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app_map.main:app", "-k", "uvicorn.workers.UvicornWorker"]
