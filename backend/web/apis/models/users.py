
from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from web.apis.models.pages import users_pages
from web.apis.models.roles import users_roles
from web.extensions import db

ADMIN_ROLES = ("admin", "dev")

products_users = db.Table(
    "products_users",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("product_id", db.Integer, db.ForeignKey("products.id")),
)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300))
    avatar = db.Column(db.String(300))
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    valid_email = db.Column(db.Boolean(), index=True, nullable=False, default=False)
    phone = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(512), nullable=False)
    about_me = db.Column(db.String(300))
    oauth_providers = db.Column(db.String(300)) # google, github, email etc.
    ip = db.Column(db.String(50), nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)
    is_guest = db.Column(db.Boolean, default=False)
    
    
    
    online_status = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    comments = db.relationship(
        'Comment',
        foreign_keys='Comment.user_id',
        back_populates='user',
        lazy='dynamic', 
        cascade='all, delete-orphan',  # SQLAlchemy cascades
        passive_deletes=True           # Enable database-level ON DELETE CASCADE
    )
    
    roles = db.relationship('Role', secondary=users_roles, back_populates='users')
    
    subscriptions = db.relationship('Subscription', back_populates='user', lazy=True, cascade="all, delete-orphan")
    usage = db.relationship('Usage', back_populates='user', lazy=True, cascade="all, delete-orphan")
    
    favorites = db.relationship('Favorite', back_populates='users')
    baskets = db.relationship('Basket', back_populates='users')
    pages = db.relationship('Page', secondary=users_pages, lazy='dynamic', back_populates='users')
    products = db.relationship('Product', secondary=products_users, lazy='dynamic', back_populates='users')
    transactions = db.relationship('Transaction', back_populates='user', lazy='dynamic')

    # ------------------------------------------------------------ lookups
    @staticmethod
    def get_user(user_id=None, username=None, email=None):
        query = User.query
        if user_id is not None:
            return query.filter_by(id=user_id).first()
        if username is not None:
            return query.filter(func.lower(User.username) == str(username).lower()).first()
        if email is not None:
            return query.filter(func.lower(User.email) == str(email).lower()).first()
        return None

    @staticmethod
    def find_by_identifier(identifier):
        """Resolve an email, phone number or username (case-insensitive) to a user."""
        ident = str(identifier or "").strip().lower()
        if not ident:
            return None
        return User.query.filter(
            User.is_deleted.is_(False),
            (func.lower(User.email) == ident) | (func.lower(User.username) == ident) | (User.phone == ident),
        ).first()

    # ----------------------------------------------------------- password
    def set_password(self, password: str) -> None:
        if not password:
            raise ValueError("Password cannot be empty")
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return bool(self.password) and bool(password) and check_password_hash(self.password, password)

    # -------------------------------------------------------------- roles
    def get_roles(self):
        return [r.name for r in self.roles]

    @property
    def is_admin(self):
        """True for admin/dev users. (A property: ``user.is_admin``, never ``user.is_admin()``.)"""
        return any(role in ADMIN_ROLES for role in self.get_roles())

    # Several modules/templates used these names; keep one source of truth.
    @property
    def email_verified(self):
        return bool(self.valid_email)

    @email_verified.setter
    def email_verified(self, value):
        self.valid_email = bool(value)

    # ------------------------------------------------------------- tokens
    def make_token(self, token_type="access"):
        """Issue a JWT. Claims feed the frontend sidebar (name, roles) so they must stay."""
        claims = {
            "token_type": token_type,
            "username": self.username,
            "name": self.name or self.username,
            "email": self.email,
            "roles": self.get_roles(),
        }
        if token_type == "access":
            return create_access_token(identity=self.id, additional_claims=claims)
        if token_type == "refresh":
            return create_refresh_token(identity=self.id, additional_claims={"token_type": "refresh"})
        raise ValueError(f"Unknown token type: {token_type}")

    # ------------------------------------------------------------ summary
    def get_summary(self, include_products=False, include_roles=False, include_pages=False):
        data = {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "about_me": self.about_me,
            "avatar": self.avatar,
            "email_verified": self.email_verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "subscriptions": [
                {
                    "id": sub.id,
                    "status": sub.status,
                    "total_units": sub.total_units,
                    "name": sub.plan.name if sub.plan else None,
                    "created_at": sub.created_at,
                }
                for sub in self.subscriptions
                if not sub.is_deleted
            ],
        }
        if include_pages:
            data["pages"] = [page.get_summary() for page in self.pages]
        if include_roles:
            data["roles"] = self.get_roles()
        if include_products:
            data["products"] = [product.get_summary() for product in self.products]
        return data

    def __repr__(self):
        return f"<User {self.username}>"
