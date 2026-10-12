"""Page routes. One table instead of one copy-pasted function per page."""
from flask import render_template

PUBLIC_PAGES = {
    "/": "index.html",
    "/index": "index.html",
    "/laundry": "laundry.html",
    "/fashion": "fashion.html",
    "/contact": "contact.html",
    "/signin": "auth/signin.html",
    "/signup": "auth/signup.html",
    "/verify-email": "auth/verify_email.html",
    "/reset-password": "auth/forgot.html",
    "/reset-password/confirm": "auth/reset.html",
}

# Signed-in pages. Access is enforced by the API; the page script redirects visitors to /signin.
DASHBOARD_PAGES = {
    "/account": "users/account.html",
    "/plans": "users/plans.html",
    "/usage": "users/usage.html",
    "/transactions": "users/transactions.html",
    "/settings": "users/settings.html",
    "/addresses": "users/addresses.html",
    "/fashion-crud": "users/fashion_manager.html",
    "/users": "users/users.html",
}


def _page(template):
    def view():
        return render_template(template)

    return view


def register_pages(app):
    for rule, template in {**PUBLIC_PAGES, **DASHBOARD_PAGES}.items():
        app.add_url_rule(rule, endpoint=rule.strip("/").replace("/", "_") or "home", view_func=_page(template))
