"""Service for sending verification emails."""

from src.email.models.email_models import EmailMessage, VerificationEmailData
from src.email.services.email_service import EmailService


class VerificationEmailService:
    """Service for sending email verification emails."""

    def __init__(
        self,
        email_service: EmailService,
        frontend_url: str,
        expires_in_hours: int,
    ):
        self._email_service = email_service
        self._frontend_url = frontend_url
        self._expires_in_hours = expires_in_hours

    def send_verification_email(
        self,
        to_email: str,
        user_name: str | None,
        verification_token: str,
    ) -> bool:
        """Send a verification email to the user.

        Returns True if sent successfully, False otherwise.
        """
        verification_url = f"{self._frontend_url}/verify-email?token={verification_token}"

        data = VerificationEmailData(
            user_name=user_name or to_email,
            verification_url=verification_url,
            expires_in_hours=self._expires_in_hours,
        )

        html_content = self._render_html_template(data)
        text_content = self._render_text_template(data)

        message = EmailMessage(
            to_email=to_email,
            to_name=user_name,
            subject="Verify your email address - LLM Hero",
            html_content=html_content,
            text_content=text_content,
        )

        return self._email_service.send_email(message)

    def _render_html_template(self, data: VerificationEmailData) -> str:
        """Render HTML email template."""
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #1f2937;">Welcome to LLM Hero!</h1>
    <p>Hi {data.user_name},</p>
    <p>Thank you for signing up. Please verify your email address by clicking the button below:</p>
    <p style="text-align: center; margin: 30px 0;">
        <a href="{data.verification_url}"
           style="background-color: #1f2937; color: white; padding: 12px 24px;
                  text-decoration: none; border-radius: 6px; display: inline-block;">
            Verify Email Address
        </a>
    </p>
    <p>Or copy and paste this link into your browser:</p>
    <p style="word-break: break-all; color: #6b7280;">{data.verification_url}</p>
    <p><strong>This link expires in {data.expires_in_hours} hours.</strong></p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
    <p style="color: #6b7280; font-size: 12px;">
        If you didn't create an account, you can safely ignore this email.
    </p>
</body>
</html>"""

    def _render_text_template(self, data: VerificationEmailData) -> str:
        """Render plain text email template."""
        return f"""Welcome to LLM Hero!

Hi {data.user_name},

Thank you for signing up. Please verify your email address by visiting:

{data.verification_url}

This link expires in {data.expires_in_hours} hours.

If you didn't create an account, you can safely ignore this email.
"""
