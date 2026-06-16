import smtplib
import os
import sys
from email.mime.text import MIMEText


def send_alert(workflow_name: str, run_id: str) -> None:
    msg = MIMEText(f"Workflow '{workflow_name}' failed.\nRun ID: {run_id}")
    msg["Subject"] = f"[SLC Deals] Workflow failure: {workflow_name}"
    msg["From"]    = os.environ["DIGEST_SENDER_EMAIL"]
    msg["To"]      = "reurichards@gmail.com"
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.environ["DIGEST_SENDER_EMAIL"], os.environ["DIGEST_SENDER_APP_PASSWORD"])
        s.sendmail(msg["From"], [msg["To"]], msg.as_string())


if __name__ == "__main__":
    send_alert(sys.argv[1], sys.argv[2])
