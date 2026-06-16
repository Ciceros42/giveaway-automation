import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import config


def send_smtp(html: str, subject: str) -> None:
    """Send the digest HTML email via Gmail SMTP using account 1 app password."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = config.DIGEST_EMAIL
    msg["To"]      = config.DIGEST_TARGET
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(config.DIGEST_EMAIL, config.DIGEST_APP_PASSWORD)
        s.sendmail(config.DIGEST_EMAIL, [config.DIGEST_TARGET], msg.as_string())
    print(f"[INFO] Digest sent to {config.DIGEST_TARGET}")


def forward_win(original_msg, inbox_email: str) -> None:
    """
    Forward a win email to FORWARD_TO.
    Defined here so monitoring/inbox.py can import from digest.sender.
    """
    fwd = MIMEMultipart()
    fwd["Subject"] = f"[WIN DETECTED] {original_msg.get('Subject', '(no subject)')}"
    fwd["From"]    = config.DIGEST_EMAIL
    fwd["To"]      = config.FORWARD_TO

    body = (
        f"Win email detected in: {inbox_email}\n"
        f"Subject: {original_msg.get('Subject', '')}\n"
        f"From: {original_msg.get('From', '')}\n\n"
        "--- Original ---\n"
    )
    if original_msg.is_multipart():
        for part in original_msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body += part.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    pass
                break
    else:
        try:
            body += original_msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except Exception:
            pass

    fwd.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(config.DIGEST_EMAIL, config.DIGEST_APP_PASSWORD)
        s.sendmail(config.DIGEST_EMAIL, [config.FORWARD_TO], fwd.as_string())
