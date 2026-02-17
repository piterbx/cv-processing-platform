from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(title="CVPP Core")

app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}