# E2E test configuration — override parent async fixtures to avoid event loop
# conflicts with sync Playwright.
import pytest

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture(autouse=True)
def setup_db():
    """Override parent's autouse async setup_db.
    
    E2E tests use sync Playwright and don't need per-test DB cleanup.
    Making this a sync no-op prevents pytest-asyncio from creating an
    event loop context that would conflict with Playwright's Runner.run().
    """
    pass
