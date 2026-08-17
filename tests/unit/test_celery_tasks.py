"""Tests for Celery task wrapping and configuration (AUTO-TSK-007/008/009)."""

import pytest
from unittest.mock import patch, MagicMock

from kombu import Connection


class TestCeleryAppConfig:
    """AUTO-TSK-008: rediss brokers carry ssl_cert_reqs=none for TLS."""

    def test_rediss_broker_appends_ssl_cert_reqs(self, monkeypatch):
        monkeypatch.setenv("CELERY_BROKER_URL", "rediss://:pass@redis.example:6379/0")
        monkeypatch.delenv("REDIS_URL", raising=False)

        from celery_app import make_celery

        app = make_celery()
        broker = app.conf.broker_url or ""
        # kombu normalized the URL; the appended query is consumed into the
        # Connection.ssl dict (CERT_NONE == disable cert verification).
        conn = Connection(broker)
        ssl = conn.ssl or {}
        assert ssl.get("ssl_cert_reqs") is not None
        assert ssl["ssl_cert_reqs"].name == "CERT_NONE"

    def test_plain_redis_broker_untouched(self, monkeypatch):
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        monkeypatch.delenv("REDIS_URL", raising=False)

        from celery_app import make_celery

        app = make_celery()
        conn = Connection(app.conf.broker_url or "")
        assert not conn.ssl


class TestCeleryTaskWrapping:
    """AUTO-TSK-009: wrappers build a fresh app and retry with countdown=60."""

    def test_event_reminder_success_returns_result(self):
        from services.celery_tasks import send_event_reminders_async

        with patch("app.create_app") as mock_create, \
             patch("services.tasks.send_event_reminders", return_value={"ok": True}) as mock_send:
            mock_create.return_value = MagicMock()
            result = send_event_reminders_async.run()

        assert result == {"ok": True}
        mock_send.assert_called_once()
        mock_create.assert_called()  # wrapper builds a fresh app context

    def test_event_reminder_retries_with_countdown_60_on_failure(self):
        from services.celery_tasks import send_event_reminders_async

        with patch("app.create_app"), \
             patch("services.tasks.send_event_reminders", side_effect=RuntimeError("db down")), \
             patch.object(send_event_reminders_async, "retry") as mock_retry:
            mock_retry.side_effect = RuntimeError("retried")
            with pytest.raises(RuntimeError, match="retried"):
                send_event_reminders_async.run()

        mock_retry.assert_called_once()
        assert mock_retry.call_args[1]["countdown"] == 60

    def test_update_stale_prices_retries_on_failure(self):
        from services.celery_tasks import update_stale_prices_async

        with patch("app.create_app"), \
             patch("services.price_service.update_stale_prices", side_effect=RuntimeError("scraper down")), \
             patch.object(update_stale_prices_async, "retry") as mock_retry:
            mock_retry.side_effect = RuntimeError("retried")
            with pytest.raises(RuntimeError, match="retried"):
                update_stale_prices_async.run(force_all=True)

        mock_retry.assert_called_once()
        assert mock_retry.call_args[1]["countdown"] == 60


class TestTaskBoundConfig:
    """AUTO-TSK-007: tasks declared with max_retries=3."""

    def test_event_reminder_task_has_max_retries_three(self):
        from services.celery_tasks import send_event_reminders_async
        assert send_event_reminders_async.max_retries == 3

    def test_stale_prices_task_has_max_retries_three(self):
        from services.celery_tasks import update_stale_prices_async
        assert update_stale_prices_async.max_retries == 3