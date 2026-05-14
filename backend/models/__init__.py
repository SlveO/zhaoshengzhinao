from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session

async def init_db():
    # Import all models so Base.metadata knows about them
    from . import college       # noqa: F401
    from . import admission     # noqa: F401
    from . import user          # noqa: F401
    from . import profile       # noqa: F401
    from . import recommendation # noqa: F401
    from . import industry      # noqa: F401
    from . import mapping       # noqa: F401
    from . import recommendation_feedback  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
