"""Tests for email service with mocked SMTP."""
import pytest
from unittest.mock import patch, MagicMock


class TestEmailService:
    """Tests for email sending functionality."""

    def test_init_mail(self, app):
        """Should initialize mail with app."""
        from services.email_service import init_mail, mail
        
        # init_mail is already called in app factory, just verify it doesn't fail
        with app.app_context():
            init_mail(app)
            # Mail object should be usable
            assert mail is not None

    @patch('services.email_service.mail.send')
    @patch('services.email_service.render_template')
    def test_send_email_success(self, mock_render, mock_send, app):
        """Should send email successfully."""
        from services.email_service import send_email
        
        mock_render.return_value = "<html>Test</html>"
        
        with app.app_context():
            result = send_email(
                to="test@example.com",
                subject="Test Subject",
                template_name="event_reminder",
                user_name="Test User"
            )
            
            assert result is True
            mock_send.assert_called_once()
            # Verify template was rendered for both HTML and text
            assert mock_render.call_count == 2

    @patch('services.email_service.mail.send')
    @patch('services.email_service.render_template')
    def test_send_email_failure(self, mock_render, mock_send, app):
        """Should handle email send failure gracefully."""
        from services.email_service import send_email
        
        mock_render.return_value = "<html>Test</html>"
        mock_send.side_effect = Exception("SMTP Error")
        
        with app.app_context():
            result = send_email(
                to="test@example.com",
                subject="Test Subject",
                template_name="event_reminder",
                user_name="Test User"
            )
            
            assert result is False

    @patch('services.email_service.send_email')
    def test_send_event_reminder(self, mock_send_email, app):
        """Should send event reminder with correct parameters."""
        from services.email_service import send_event_reminder
        import datetime
        
        mock_send_email.return_value = True
        
        with app.app_context():
            result = send_event_reminder(
                user_email="user@example.com",
                user_name="Test User",
                event_name="Christmas",
                event_date=datetime.date(2025, 12, 25),
                claimed_items=["Gift 1", "Gift 2"]
            )
            
            assert result is True
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args
            assert call_args.kwargs['to'] == "user@example.com"
            assert "Christmas" in call_args.kwargs['subject']
            assert call_args.kwargs['template_name'] == "event_reminder"
