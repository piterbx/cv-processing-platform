from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=5, max_overflow=5
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, autoflush=False
)
