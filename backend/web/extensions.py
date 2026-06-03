"""
web/extensions.py

Centralized Flask extensions and infrastructure services.
"""

from __future__ import annotations

import logging
from os import getenv
from typing import Optional, Set

from dotenv import load_dotenv
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# Environment
# ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Flask Extensions
# ──────────────────────────────────────────────────────────────

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_moment import Moment
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_jwt_extended import JWTManager
from authlib.integrations.flask_client import OAuth
from faker import Faker

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
moment = Moment()
bcrypt = Bcrypt()
cors = CORS()
cache = Cache()
csrf = CSRFProtect()
jwt = JWTManager()
oauth = OAuth()
fake = Faker()

# ──────────────────────────────────────────────────────────────
# In-Memory Token Blocklist (Fallback when Redis unavailable)
# ──────────────────────────────────────────────────────────────

class MemoryBlocklist:
    """
    Thread-safe(ish) in-memory token blocklist.
    Falls back to this when Redis is not available.
    """
    def __init__(self):
        self._blacklist: Set[str] = set()
    
    def sadd(self, key: str, *members) -> int:
        """Add members to a set. Returns number added."""
        if key != "blacklist":
            return 0
        added = 0
        for member in members:
            if member not in self._blacklist:
                self._blacklist.add(member)
                added += 1
        return added
    
    def sismember(self, key: str, member: str) -> bool:
        """Check if member is in set."""
        if key != "blacklist":
            return False
        return member in self._blacklist
    
    def srem(self, key: str, *members) -> int:
        """Remove members from set."""
        if key != "blacklist":
            return 0
        removed = 0
        for member in members:
            if member in self._blacklist:
                self._blacklist.discard(member)
                removed += 1
        return removed
    
    def scard(self, key: str) -> int:
        """Get set cardinality."""
        if key != "blacklist":
            return 0
        return len(self._blacklist)
    
    def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set key with expiry (no-op for memory, just store)."""
        # Simple storage without expiry tracking
        setattr(self, f"_store_{key}", value)
        return True
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return getattr(self, f"_store_{key}", None)
    
    def delete(self, *keys) -> int:
        """Delete keys."""
        deleted = 0
        for key in keys:
            attr = f"_store_{key}"
            if hasattr(self, attr):
                delattr(self, attr)
                deleted += 1
        return deleted


# ──────────────────────────────────────────────────────────────
# Redis Configuration with Graceful Fallback
# ──────────────────────────────────────────────────────────────

from redis import Redis
from redis.exceptions import RedisError

REDIS_URL = (
    getenv("REDIS_URL")
    or getenv("REDIS_URI")
    or getenv("REDIS_CONNECTION_STRING")
)

redis_client: Optional[Redis] = None
memory_blocklist = MemoryBlocklist()


def create_redis_client() -> Optional[Redis]:
    """
    Create and validate Redis connection safely.
    Falls back to in-memory blocklist if Redis is unavailable.
    """

    global redis_client

    if redis_client is not None:
        return redis_client

    if not REDIS_URL:
        logger.warning("Redis URL not configured. Using in-memory fallback.")
        return None

    try:
        redis_client = Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        redis_client.ping()
        logger.info("Redis connected successfully.")
        return redis_client

    except RedisError as exc:
        logger.warning(
            "Redis unavailable. Using in-memory fallback. Error: %s",
            exc,
        )
        redis_client = None
        return None

    except Exception as exc:
        logger.exception(
            "Unexpected Redis initialization error: %s",
            exc,
        )
        redis_client = None
        return None


# Create Redis connection safely
# redis = create_redis_client()

# Unified interface: always returns a working client (Redis or memory fallback)
def get_redis_or_memory():
    """
    Returns Redis client if available, otherwise in-memory fallback.
    Use this for all Redis-like operations.
    """
    return redis_client if redis_client is not None else memory_blocklist

redis = get_redis_or_memory()

# ──────────────────────────────────────────────────────────────
# Rate Limiting
# ──────────────────────────────────────────────────────────────

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter_storage_uri = REDIS_URL if REDIS_URL else "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
        "1 per second",
        "5 per minute",
    ],
    storage_uri=limiter_storage_uri,
    strategy="fixed-window",
)

# ──────────────────────────────────────────────────────────────
# App Configuration
# ──────────────────────────────────────────────────────────────


def config_app(app, config_name: str) -> None:
    from web.config import app_config
    app.config.from_object(app_config[config_name])
    logger.info("Application configured using '%s' config.", config_name)


# ──────────────────────────────────────────────────────────────
# Extension Initialization
# ──────────────────────────────────────────────────────────────


def init_ext(app) -> None:
    """
    Initialize Flask extensions.
    """
    # Core
    db.init_app(app)
    migrate.init_app(app, db)

    # Security/Auth
    bcrypt.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)

    # Utilities
    mail.init_app(app)
    moment.init_app(app)
    oauth.init_app(app)
    cache.init_app(app)

    # Rate Limiting
    limiter.init_app(app)

    # CORS
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "https://simplylovely.ng/",
                    "https://simplylovely.ng",
                    "https://www.simplylovely.ng/",
                    "https://www.simplylovely.ng",
                    "http://localhost:5002",
                    "http://localhost:5001",
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "Client-Callback-Url",
                    "X-Requested-With",
                    "Accept",
                    "Origin",
                ],
                "expose_headers": ["Content-Type", "X-Request-ID"],
                "supports_credentials": True,
                "max_age": 86400,
            }
        },
    )

    logger.info("Flask extensions initialized successfully.")


# ──────────────────────────────────────────────────────────────
# Shared Metadata
# ──────────────────────────────────────────────────────────────


def make_available() -> dict:
    products_links = {
        "salesnet_link": "https://salesnet.techa.tech",
        "barman_link": "https://barman.techa.tech",
        "paysafe_link": "https://paysafe.techa.tech",
        "intellect_link": "https://intellect.techa.tech",
        "workforce_link": "https://workforce.techa.tech",
    }

    app_data = {
        "app_name": "Salesnet",
        "hype": "Your Digital Learning Companion.",
        "app_desc": (
            "Elite software engineering team with special interest "
            "in artificial intelligence, data and cybersecurity."
        ),
        "app_desc_long": (
            "Salesnet empowers people and businesses to stay "
            "relevant with evolving technologies and innovation."
        ),
        "app_location": "Lekki, Lagos, Nigeria",
        "app_email": "hi@techa.tech",
        "app_logo": getenv("LOGO_URL"),
        "site_logo": getenv("LOGO_URL"),
        "site_link": "https://www.techa.tech",
        "whatsapp_link": "https://www.techa.tech",
        "terms_link": "https://www.techa.tech/terms",
        "policy_link": "https://www.techa.tech/policy",
        "cookie_link": "https://www.techa.tech/cookie",
        "github_link": "https://github.com/russiantech",
        "fb_link": "https://www.facebook.com/RussianTechs",
        "x_link": "https://twitter.com/chris_jsmes",
        "instagram_link": "https://www.instagram.com/chrisjsmz/",
        "linkedin_link": "https://www.linkedin.com/in/chrisjsm",
        "youtube_link": "https://www.youtube.com/@russian_developer",
    }

    return {
        **app_data,
        **products_links,
    }