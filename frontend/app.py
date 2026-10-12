from os import getenv

from web import create_app

app = create_app()  # APP_ENV / FLASK_ENV select the config; defaults to production

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(getenv("PORT", 5002)), debug=app.config["DEBUG"])
