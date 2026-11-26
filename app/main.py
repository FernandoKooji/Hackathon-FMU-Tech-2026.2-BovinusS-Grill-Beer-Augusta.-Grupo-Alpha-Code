from fastapi import FastAPI

app = FastAPI(
    title="Smart Buffet Analytics",
    description="API de monitoramento e consumo de alimentos.",
    version="1.0.0"
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