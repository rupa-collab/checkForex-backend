from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.settings import settings


def send_verification_email(to_email: str, verify_url: str) -> None:
    message = Mail(
        from_email=settings.SENDGRID_FROM,
        to_emails=to_email,
        subject="Verify your email",
        html_content=f"<p>Please verify your email:</p><p><a href='{verify_url}'>Verify Email</a></p>",
    )
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    sg.send(message)
