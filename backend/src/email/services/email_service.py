"""Brevo HTTP API email service for sending emails."""

import logging
from typing import Any

import httpx

from src.email.models.email_models import EmailMessage

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailService:
    """Service for sending emails via Brevo HTTP API.

    Uses HTTP API instead of SMTP to avoid port 587/465 blocking
    by ISPs, firewalls, or Docker networking issues.
    """

    def __init__(
        self,
        api_key: str,
        sender_email: str,
        sender_name: str,
    ):
        self._api_key = api_key
        self._sender_email = sender_email
        self._sender_name = sender_name

    def send_email(self, message: EmailMessage) -> bool:
        """Send an email via Brevo HTTP API.

        Returns True if sent successfully, False otherwise.
        """
        if not self._api_key:
            logger.error("Brevo API key not configured")
            return False

        payload: dict[str, Any] = {
            "sender": {
                "name": self._sender_name,
                "email": self._sender_email,
            },
            "to": [{"email": message.to_email}],
            "subject": message.subject,
            "htmlContent": message.html_content,
        }

        if message.text_content:
            payload["textContent"] = message.text_content

        headers = {
            "accept": "application/json",
            "api-key": self._api_key,
            "content-type": "application/json",
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    BREVO_API_URL,
                    json=payload,
                    headers=headers,
                )

            if response.status_code in (200, 201):
                logger.info(f"Email sent successfully to {message.to_email}")
                return True
            else:
                logger.error(
                    f"Failed to send email to {message.to_email}: "
                    f"HTTP {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to send email to {message.to_email}: {e}")
            return False
