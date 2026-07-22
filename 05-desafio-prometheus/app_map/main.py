from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app
from .api.endpoints import router as item_router

app = FastAPI()

app.include_router(item_router)


metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.mount('/', StaticFiles(directory="statics", html=True), name="static")
