from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):

    init_db()

    yield


app = FastAPI(
    title="Smart Buffet Analytics",
    description="API de monitoramento e consumo de alimentos.",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
def root():
    return {
        "projeto": "Smart Buffet Analytics",
        "status": "online"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }