"""Maintenance commands (replace the old public /insert-* and /populate endpoints).

    flask --app app seed            # roles, service catalogue, delivery areas (idempotent)
    flask --app app create-admin    # prompts for email / username / password
"""
import click
from flask.cli import with_appcontext

from web.apis.models.roles import Role
from web.apis.models.services import Area, Service, ServiceCategory
from web.apis.models.users import User
from web.apis.utils.get_or_create import get_or_create
from web.extensions import db

AREAS = {"Ajah": 2000, "VGC": 4000, "Chevron": 3000, "Lekki": 4000, "LBS": 10000, "Sangotedo": 13000, "Awoyaya": 11000}

SERVICES = {
    "Laundry": [
        ("Dry Cleaning", "./static/img/laundry/services/dry-cleaning.png", "Professional dry cleaning service.", None),
        ("Stain Removal", "./static/img/laundry/services/stain-remover.png", "Remove tough stains from your clothes.", None),
        ("Iron Only", "./static/img/laundry/services/ironing.png", "Ironing service for your clothes.", "fi-dresser"),
        ("Wash & Iron", "./static/img/laundry/services/iron-board.png", "Wash and ironing services combined.", "fi-package"),
        ("Volume Subscription (Enjoy-discount)", "./static/img/laundry/services/transaction.png", "Get a discount with volume subscriptions.", "fi-gift"),
        ("Adjustment & Alterations", "./static/img/laundry/services/sewing-machine.png", "Alterations and adjustments for your clothes.", "fi-scissors"),
        ("Pick-up & Delivery", "./static/img/laundry/services/pickup.png", "Convenient pick-up and delivery service.", "fi-bicycle"),
    ],
    "Fashion": [
        ("Men's Ankaras", "./static/img/fashion/02.jpg", "Stylish men's Ankaras.", None),
        ("Women Ankaras", "./static/img/fashion/services/women_native.jpg", "Elegant women's Ankaras.", None),
        ("Children Natives", "./static/img/fashion/03.jpg", "Traditional outfits for children.", None),
        ("Men's Native Clothes", "./static/img/fashion/02.jpg", "Classic men's native attire.", None),
    ],
}


def seed_reference_data():
    for name in ("user", "admin", "dev"):
        get_or_create(db.session, Role, {"description": f"{name} role"}, name=name)
    for area, price in AREAS.items():
        get_or_create(db.session, Area, {"price": price}, name=area)
    for category_name, items in SERVICES.items():
        category, _ = get_or_create(db.session, ServiceCategory, {}, name=category_name)
        link = f"./{category_name.lower()}"
        for name, image, description, icon in items:
            get_or_create(db.session, Service, {"image": image, "description": description, "link": link, "icon": icon}, name=name, category_id=category.id)
    db.session.commit()


@click.command("seed")
@with_appcontext
def seed_command():
    seed_reference_data()
    click.echo("Reference data is in place.")


@click.command("create-admin")
@click.option("--email", prompt=True)
@click.option("--username", prompt=True)
@click.option("--phone", prompt=True)
@click.password_option()
@with_appcontext
def create_admin_command(email, username, phone, password):
    seed_reference_data()
    user = User.get_user(email=email) or User(email=email.lower(), username=username, phone=phone)
    user.set_password(password)
    user.email_verified = True
    admin = Role.query.filter_by(name="admin").one()
    if admin not in user.roles:
        user.roles.append(admin)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Admin ready: {user.email}")


def register_cli(app):
    app.cli.add_command(seed_command)
    app.cli.add_command(create_admin_command)
