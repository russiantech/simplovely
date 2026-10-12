from datetime import datetime

from sqlalchemy import func

from web.extensions import db


class RevokedToken(db.Model):
    """Blocklist of signed-out JWTs. Stored in the DB so every worker process agrees."""

    __tablename__ = "revoked_tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), unique=True, index=True, nullable=False)
    token_type = db.Column(db.String(16), nullable=False, default="access")
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())

    @staticmethod
    def is_revoked(jti):
        return bool(jti) and db.session.query(RevokedToken.id).filter_by(jti=jti).first() is not None

    @staticmethod
    def purge_expired():
        RevokedToken.query.filter(RevokedToken.expires_at < datetime.utcnow()).delete()
