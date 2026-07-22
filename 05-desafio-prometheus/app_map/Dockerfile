FROM python:3.12-slim


WORKDIR /code/app_map

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/code

EXPOSE 8000

# Comando de la doc oficial de client_python (FastAPI + Gunicorn)
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app_map.main:app", "-k", "uvicorn.workers.UvicornWorker"]
