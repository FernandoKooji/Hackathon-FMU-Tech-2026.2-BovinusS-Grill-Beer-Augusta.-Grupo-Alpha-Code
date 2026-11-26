from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import init_db
from app.routers.leitura_router import router as leitura_router


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

# Origens do desenvolvimento local. Revise esta lista antes de implantar em produção.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)
app.include_router(leitura_router)


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
