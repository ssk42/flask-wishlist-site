"""Tests for CLI commands (send-reminders and update-prices)."""
import datetime
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner


def test_send_reminders_command_success(app):
    """Test send-reminders CLI command executes successfully."""
    from app import app as flask_app

    runner = CliRunner()

    # Patch the import inside the CLI command
    with patch('tasks.send_event_reminders') as mock_send:
        mock_send.return_value = {
            'events_processed': 2,
            'emails_sent': 5,
            'errors': 0
        }

        with flask_app.app_context():
            result = runner.invoke(flask_app.cli.commands['send-reminders'])

        assert result.exit_code == 0
        assert 'Events processed: 2' in result.output
        assert 'Emails sent: 5' in result.output
        assert 'Errors: 0' in result.output


def test_send_reminders_command_with_errors(app):
    """Test send-reminders CLI command exits with error when there are failures."""
    from app import app as flask_app

    runner = CliRunner()

    with patch('tasks.send_event_reminders') as mock_send:
        mock_send.return_value = {
            'events_processed': 2,
            'emails_sent': 3,
            'errors': 2
        }

        with flask_app.app_context():
            result = runner.invoke(flask_app.cli.commands['send-reminders'])

        assert result.exit_code == 1
        assert 'Errors: 2' in result.output


def test_update_prices_command_success(app):
    """Test update-prices CLI command executes successfully."""
    from app import app as flask_app

    runner = CliRunner()

    with patch('price_service.update_stale_prices') as mock_update:
        mock_update.return_value = {
            'items_processed': 10,
            'prices_updated': 5,
            'price_drops': 2,
            'errors': 0
        }

        with flask_app.app_context():
            result = runner.invoke(flask_app.cli.commands['update-prices'])

        assert result.exit_code == 0
        assert 'Items processed: 10' in result.output
        assert 'Prices updated: 5' in result.output
        assert 'Price drops detected: 2' in result.output


def test_update_prices_command_with_force_flag(app):
    """Test update-prices CLI command with --force flag."""
    from app import app as flask_app

    runner = CliRunner()

    with patch('price_service.update_stale_prices') as mock_update:
        mock_update.return_value = {
            'items_processed': 20,
            'prices_updated': 15,
            'price_drops': 3,
            'errors': 0
        }

        with flask_app.app_context():
            result = runner.invoke(flask_app.cli.commands['update-prices'], ['--force'])

        assert result.exit_code == 0
        assert 'Force updating ALL prices' in result.output
        mock_update.assert_called_once()
        # Verify force_all=True was passed
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs.get('force_all') is True
