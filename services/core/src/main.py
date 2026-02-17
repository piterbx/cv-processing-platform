from fastapi import FastAPI
from src.api.routes import router
from src.db.models import Base
from src.db.session import engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CVPP Core")

app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}