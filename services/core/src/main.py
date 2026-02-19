from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text

from src.db.session import engine 
from src.services.storage import storage_service
from src.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n[SYSTEM CHECK] Starting services")
    
    # health check S3
    try:
        await storage_service.ensure_bucket_exists()
        print("S3 Connection: OK")
    except Exception as e:
        print(f"S3 Connection: FAILED | {e}")

    # health check database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("Database Connection: OK")
    except Exception as e:
        print(f"Database Connection: FAILED | {e}")
    
    print("[SYSTEM CHECK] Complete\n")
    
    yield # app starts
    
    print("Shutting down... Cleaning up connections.")
    await engine.dispose()


app = FastAPI(title="CVPP Core", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}