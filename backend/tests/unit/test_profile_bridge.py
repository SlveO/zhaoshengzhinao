"""Unit tests for profile_bridge — pure logic, no I/O, no DB.

Test names follow the required naming convention:
test_<method>_<scenario>_<expected_result>
"""

import os

# Prevent numpy BLAS FPE crash on Windows when langchain_openai imports torch
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import pytest
from unittest.mock import AsyncMock, patch

from services.profile_bridge import should_extract


# ---------------------------------------------------------------------------
# Override conftest.py's autouse setup_db fixture — NO database needed
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_db():
    """Override the conftest.py setup_db — pure unit tests, no DB required."""
    yield


# ===========================================================================
# should_extract — gate controlling profile extraction frequency
# ===========================================================================


@pytest.mark.asyncio
async def test_should_extract_0_messages_returns_false():
    """0 user messages -> False (count must be > 0 and divisible by 3)."""
    # Arrange
    with patch(
        "services.profile_bridge.get_chat_message_count",
        new_callable=AsyncMock,
        return_value=0,
    ):
        # Act
        result = await should_extract("test-session-id")

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_should_extract_3_messages_returns_true():
    """3 user messages -> True (3 > 0 and 3 % 3 == 0)."""
    # Arrange
    with patch(
        "services.profile_bridge.get_chat_message_count",
        new_callable=AsyncMock,
        return_value=3,
    ):
        # Act
        result = await should_extract("test-session-id")

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_should_extract_4_messages_returns_false():
    """4 user messages -> False (4 % 3 != 0)."""
    # Arrange
    with patch(
        "services.profile_bridge.get_chat_message_count",
        new_callable=AsyncMock,
        return_value=4,
    ):
        # Act
        result = await should_extract("test-session-id")

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_should_extract_6_messages_returns_true():
    """6 user messages -> True (6 > 0 and 6 % 3 == 0)."""
    # Arrange
    with patch(
        "services.profile_bridge.get_chat_message_count",
        new_callable=AsyncMock,
        return_value=6,
    ):
        # Act
        result = await should_extract("test-session-id")

    # Assert
    assert result is True
