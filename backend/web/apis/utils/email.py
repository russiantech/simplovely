"""Transactional email. Sending never raises into a request: failures are logged and reported as False."""
import logging
from threading import Thread

from flask import current_app, render_template
from flask_mail import Message

from web.extensions import mail

log = logging.getLogger("web")


def mail_configured():
    cfg = current_app.config
    return bool(cfg.get("MAIL_USERNAME") and cfg.get("MAIL_PASSWORD"))


def _deliver(app, message):
    with app.app_context():
        try:
            mail.send(message)
            log.info("Email sent to %s", message.recipients)
        except Exception:  # noqa: BLE001
            log.exception("Email delivery to %s failed", message.recipients)


def send_email(subject, recipients, text_body="", html_body="", sender=None, background=True):
    """Queue an email. Returns False (and logs) if mail is unconfigured or the message is invalid."""
    if not recipients:
        return False
    if not mail_configured() and not current_app.config.get("MAIL_SUPPRESS_SEND"):
        log.warning("Email '%s' to %s not sent: MAIL_USERNAME/MAIL_PASSWORD are not configured.", subject, recipients)
        return False
    message = Message(subject, recipients=list(recipients), sender=sender or current_app.config["MAIL_DEFAULT_SENDER"])
    message.body, message.html = text_body, html_body
    if current_app.config.get("MAIL_SUPPRESS_SEND") or not background:
        _deliver(current_app._get_current_object(), message)
    else:
        Thread(target=_deliver, args=(current_app._get_current_object(), message), daemon=True).start()
    return True


def _context(user, **extra):
    cfg = current_app.config
    return {"user": user, "logo_url": f"{cfg['FRONTEND_URL']}/static/img/logo_11.png", **extra}


def send_verification_email(user, link):
    ctx = _context(user, link=link)
    return send_email(
        "[SimplyLovely] Verify your email address",
        [user.email],
        render_template("email/verify.txt", **ctx),
        render_template("email/verify.html", **ctx),
    )


def send_reset_email(user, link):
    ctx = _context(user, link=link)
    return send_email(
        "[SimplyLovely] Reset your password",
        [user.email],
        render_template("email/forgot.txt", **ctx),
        render_template("email/forgot.html", **ctx),
    )
