from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

class Base(DeclarativeBase):
    pass

_engine = None
_async_session = None


def _init_engine():
    global _engine, _async_session
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine


class _LazyEngine:
    """Proxy that defers engine creation until first method call."""
    def __getattr__(self, name):
        return getattr(_init_engine(), name)


class _LazySessionMaker:
    """Proxy that defers engine creation until first session is created."""
    def __call__(self):
        _init_engine()
        return _async_session()


engine = _LazyEngine()
async_session = _LazySessionMaker()


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    from . import college       # noqa: F401
    from . import admission     # noqa: F401
    from . import user          # noqa: F401
    from . import profile       # noqa: F401
    from . import recommendation # noqa: F401
    from . import industry      # noqa: F401
    from . import mapping       # noqa: F401
    from . import recommendation_feedback  # noqa: F401
    from . import consult_session  # noqa: F401
    from . import chat_message    # noqa: F401
    import tenants.models          # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
