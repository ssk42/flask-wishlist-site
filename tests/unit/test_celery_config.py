"""Tests for the Celery beat schedule and task time limits.

These guard the two failure modes that left prices stale for three weeks on
the production box: nothing ever dispatched the refresh task (no beat
schedule), and the worker's 5-minute default time limit would have killed
the catch-up batch even if it had been dispatched.
"""
import pytest

from celery_app import celery_app


class TestBeatSchedule:
    """Tests for the periodic price-refresh schedule."""

    def test_beat_schedule_dispatches_stale_price_updates(self):
        """Beat must dispatch the stale-price task; otherwise prices never refresh."""
        schedule = celery_app.conf.beat_schedule
        assert 'update-stale-prices' in schedule
        entry = schedule['update-stale-prices']
        assert entry['task'] == 'services.celery_tasks.update_stale_prices_async'
        # Runs at minute 0 every 6 hours (celery expands */6 to {0,6,12,18})
        assert entry['schedule'].minute == {0}
        assert entry['schedule'].hour == {0, 6, 12, 18}

    def test_stale_price_task_runs_at_least_daily(self):
        """Every-6h cadence means at most 6h past the 7-day staleness window."""
        schedule = celery_app.conf.beat_schedule['update-stale-prices']
        hours = schedule['schedule'].hour
        assert len(hours) >= 4  # 4 dispatch times per day


class TestTaskTimeLimits:
    """Tests for per-task time limits."""

    def test_stale_price_task_survives_catch_up_batches(self):
        """A post-gap batch (150+ items, sequential Amazon stealth fetches)
        runs inside one task and must not hit the worker's 300s default."""
        from services import celery_tasks
        task = celery_tasks.update_stale_prices_async
        assert task.time_limit >= 600
        assert task.soft_time_limit >= 600

    def test_small_tasks_keep_default_limits(self):
        """Event reminders and push are quick; they keep the worker default."""
        from services import celery_tasks
        assert celery_tasks.send_event_reminders_async.time_limit is None
        assert celery_tasks.send_push_task.time_limit is None