"""Task scheduler for file distribution — polls for due tasks and executes them."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from models import async_session
from distribution.models import DistributionTask

scheduler = AsyncIOScheduler()
POLL_INTERVAL_SECONDS = 30


def compute_next_run(schedule_type: str, schedule_config: dict) -> datetime | None:
    """Compute the next run time for a recurring task. Returns datetime or None."""
    now = datetime.now(timezone.utc)

    if schedule_type == "daily":
        hour = schedule_config.get("hour", 9)
        minute = schedule_config.get("minute", 0)
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run

    elif schedule_type == "weekly":
        days = schedule_config.get("days", [0])  # 0=Monday, ..., 6=Sunday
        hour = schedule_config.get("hour", 9)
        minute = schedule_config.get("minute", 0)
        weekday = now.weekday()
        # Find next matching day
        for offset in range(8):
            candidate_day = (weekday + offset) % 7
            candidate_date = now.date() + timedelta(days=offset)
            if candidate_day in days:
                candidate = datetime(
                    candidate_date.year, candidate_date.month, candidate_date.day,
                    hour, minute, 0, 0, tzinfo=timezone.utc
                )
                if candidate > now:
                    return candidate
        return None

    elif schedule_type == "monthly":
        day = schedule_config.get("day", 1)
        hour = schedule_config.get("hour", 9)
        minute = schedule_config.get("minute", 0)
        # Try this month
        try:
            candidate = now.replace(day=min(day, 28), hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            candidate = now.replace(day=28, hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            # Next month
            if now.month == 12:
                candidate = candidate.replace(year=now.year + 1, month=1)
            else:
                candidate = candidate.replace(month=now.month + 1)
        return candidate

    return None


async def _poll_and_execute():
    """Main polling job: find tasks due for execution and run them."""
    async with async_session() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(DistributionTask).where(
                DistributionTask.status == "active",
                DistributionTask.scheduled_at <= now,
                DistributionTask.deleted_at.is_(None),
            ).limit(10)  # Max 10 tasks per poll cycle
        )
        tasks = list(result.scalars().all())

    if not tasks:
        return

    from distribution.service import execute_task

    for task in tasks:
        try:
            await execute_task(task.id)
        except Exception:
            # Log but don't crash the poll loop
            pass


def start_scheduler():
    """Start the APScheduler with the polling job."""
    if scheduler.running:
        return
    scheduler.add_job(
        _poll_and_execute,
        "interval",
        seconds=POLL_INTERVAL_SECONDS,
        id="distribution_poll",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()


def shutdown_scheduler():
    """Shut down the APScheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
