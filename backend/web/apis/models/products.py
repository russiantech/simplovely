from slugify import slugify
from sqlalchemy import event, func
from sqlalchemy.orm import relationship

from web.extensions import db
from web.apis.models.users import products_users
from web.apis.models.categories import products_categories
from web.apis.models.tags import products_tags
from web.apis.models.pages import products_pages

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    # slug = db.Column(db.String, index=True, unique=True)
    slug = db.Column(db.String(255), unique=True, index=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False)

    publish_on = db.Column(db.DateTime, index=True, default=func.now())
    is_deleted = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    users = db.relationship('User', secondary=products_users, lazy='dynamic', back_populates='products')
    pages = db.relationship('Page',  secondary=products_pages, lazy='dynamic', back_populates='products')
    tags = relationship('Tag', secondary=products_tags, back_populates='products')
    categories = relationship('Category', secondary=products_categories, back_populates='products')
    comments = relationship('Comment', back_populates='product', lazy='dynamic')
    images = relationship('ProductImage', back_populates='product', lazy='dynamic')
    
    def __repr__(self):
        return '<Product %r>' % self.name
    
    @staticmethod
    def get_product(identifier, include_deleted=False):
        """Fetch by numeric id OR slug (never both: MySQL would cast '2-piece' to the id 2)."""
        if identifier is None or str(identifier).strip() == "":
            raise ValueError("Identifier cannot be empty")
        ident = str(identifier).strip()
        query = Product.query.filter(Product.id == int(ident)) if ident.isdigit() else Product.query.filter(Product.slug == ident)
        if not include_deleted:
            query = query.filter(Product.is_deleted.is_(False))
        return query.first()

    def get_summary(self, include_user=False, include_page=False):
        images = self.images.filter_by(is_deleted=False).all()
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'price': self.price,
            'stock': self.stock,
            'is_deleted': self.is_deleted,
            'comments_count': self.comments.count(),
            'tags': [{'id': t.id, 'name': t.name} for t in self.tags],
            'categories': [{'id': c.id, 'name': c.name} for c in self.categories],
            'image_urls': [str(i.file_path).replace('\\', '/') for i in images] or None,
            'images': [{'id': i.id, 'url': str(i.file_path).replace('\\', '/')} for i in images],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
        if include_user and self.users.count():
            data['users'] = [user.get_summary() for user in self.users]
        if include_page and self.pages.count():
            data['pages'] = [page.get_summary() for page in self.pages]
        return data


@event.listens_for(Product.name, 'set')
def generate_product_slug(target, value, oldvalue, initiator):
    if not value or (target.slug and value == oldvalue):
        return
    base = slugify(value) or "product"
    candidate, counter = base, 1
    with db.session.no_autoflush:
        while Product.query.filter(Product.slug == candidate, Product.id != (target.id or 0)).first():
            candidate = f"{base}-{counter}"
            counter += 1
    target.slug = candidate
